from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.masterdata.models import DefectCategory, Product, ProductionLine, Shift
from apps.production.models import ProductionBatch

from .models import InspectionDefect, InspectionUnit, QcInspection
from .services import validate_units


class BaseInspectionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN
        )
        self.supervisor = User.objects.create_user(
            username="sup1", password="pass12345", role=User.Role.SUPERVISOR
        )
        self.qc = User.objects.create_user(
            username="qc1", password="pass12345", role=User.Role.QC
        )
        self.line = ProductionLine.objects.create(kode="L1", nama="Line 1")
        self.shift = Shift.objects.create(
            kode="1", nama="Pagi", jam_mulai=time(7, 0), jam_selesai=time(15, 0)
        )
        self.product = Product.objects.create(
            part_number="WH-001", nama="Harness Main", customer="Toyota"
        )
        self.cat_crimp = DefectCategory.objects.create(
            kode="C01", nama="Crimp longgar", grup="crimping"
        )
        self.cat_housing = DefectCategory.objects.create(
            kode="K01", nama="Housing rusak", grup="connector"
        )
        self.batch = ProductionBatch.objects.create(
            product=self.product,
            line=self.line,
            shift=self.shift,
            tanggal_produksi=date(2026, 11, 3),
            qty_plan=1000,
        )

    def make_inspection(self, inspected=1000, fail=30, **kwargs):
        return QcInspection.objects.create(
            batch=self.batch,
            inspector=self.qc,
            metode=kwargs.get("metode", QcInspection.Metode.FULL),
            total_production=kwargs.get("total_production", 1000),
            sample_size=kwargs.get("sample_size"),
            qty_inspected=inspected,
            qty_pass=inspected - fail,
            qty_fail=fail,
            status=kwargs.get("status", QcInspection.Status.FINAL),
        )


class ProductionCodeTest(BaseInspectionTest):
    def test_kode_dibuat_otomatis_berurutan(self):
        self.assertEqual(self.batch.kode, "QC-20261103-L1-001")
        second = ProductionBatch.objects.create(
            product=self.product,
            line=self.line,
            shift=self.shift,
            tanggal_produksi=date(2026, 11, 3),
            qty_plan=500,
        )
        self.assertEqual(second.kode, "QC-20261103-L1-002")

    def test_urutan_terpisah_per_lini(self):
        other_line = ProductionLine.objects.create(kode="L2", nama="Line 2")
        batch_l2 = ProductionBatch.objects.create(
            product=self.product,
            line=other_line,
            shift=self.shift,
            tanggal_produksi=date(2026, 11, 3),
            qty_plan=500,
        )
        self.assertEqual(batch_l2.kode, "QC-20261103-L2-001")

    def test_urutan_reset_per_tanggal(self):
        next_day = ProductionBatch.objects.create(
            product=self.product,
            line=self.line,
            shift=self.shift,
            tanggal_produksi=date(2026, 11, 4),
            qty_plan=500,
        )
        self.assertEqual(next_day.kode, "QC-20261104-L1-001")


class InspectionMetricTest(BaseInspectionTest):
    def test_defect_rate_sesuai_contoh_kasus(self):
        inspection = self.make_inspection(inspected=1000, fail=30)
        self.assertAlmostEqual(inspection.defect_rate, 3.0)
        self.assertAlmostEqual(inspection.pass_rate, 97.0)

    def test_multi_defect_satu_unit(self):
        inspection = self.make_inspection(inspected=1000, fail=2)
        unit = InspectionUnit.objects.create(inspection=inspection, unit_ref="UNIT-001")
        InspectionDefect.objects.create(
            unit=unit, category=self.cat_crimp, severity="major"
        )
        InspectionDefect.objects.create(
            unit=unit, category=self.cat_housing, severity="critical"
        )
        self.assertEqual(inspection.units.count(), 1)
        self.assertEqual(inspection.defect_occurrences, 2)
        self.assertAlmostEqual(inspection.defect_rate, 0.2)
        self.assertAlmostEqual(inspection.dpu, 0.002)

    def test_validation_jumlah_tidak_seimbang(self):
        inspection = QcInspection(
            batch=self.batch,
            inspector=self.qc,
            metode=QcInspection.Metode.FULL,
            total_production=1000,
            qty_inspected=1000,
            qty_pass=900,
            qty_fail=30,
        )
        with self.assertRaises(ValidationError):
            inspection.full_clean()

    def test_validate_units_menolak_duplikat(self):
        units = [
            {"unit_ref": "UNIT-001", "categories": []},
            {"unit_ref": "UNIT-001", "categories": []},
        ]
        errors = validate_units(units, qty_fail=5)
        self.assertTrue(any("ganda" in error for error in errors))

    def test_validate_units_menolak_melebihi_cacat(self):
        units = [{"unit_ref": f"UNIT-{i:03d}", "categories": []} for i in range(3)]
        errors = validate_units(units, qty_fail=2)
        self.assertTrue(any("melebihi" in error for error in errors))


class InspectionFormTest(BaseInspectionTest):
    def _payload(self, **overrides):
        data = {
            "batch": self.batch.pk,
            "metode": "full",
            "total_production": 1000,
            "sample_size": "",
            "qty_fail": 2,
            "catatan": "Pemeriksaan shift pagi",
            "unit-TOTAL_FORMS": 2,
            "unit-INITIAL_FORMS": 0,
            "unit-MIN_NUM_FORMS": 0,
            "unit-MAX_NUM_FORMS": 1000,
            "unit-0-unit_ref": "UNIT-001",
            "unit-0-categories": [self.cat_crimp.pk, self.cat_housing.pk],
            "unit-0-severity": "critical",
            "unit-0-catatan": "dua masalah",
            "unit-1-unit_ref": "UNIT-002",
            "unit-1-categories": [self.cat_crimp.pk],
            "unit-1-severity": "major",
            "unit-1-catatan": "",
            "action": "final",
        }
        data.update(overrides)
        return data

    def test_input_pemeriksaan_lengkap(self):
        self.client.force_login(self.qc)
        response = self.client.post(
            reverse("inspection_create_batch", args=[self.batch.pk]), self._payload()
        )
        self.assertEqual(response.status_code, 302)

        inspection = QcInspection.objects.get()
        self.assertEqual(inspection.qty_inspected, 1000)
        self.assertEqual(inspection.qty_fail, 2)
        self.assertEqual(inspection.qty_pass, 998)
        self.assertEqual(inspection.status, QcInspection.Status.FINAL)
        self.assertEqual(inspection.units.count(), 2)
        self.assertEqual(inspection.defect_occurrences, 3)

    def test_sampling_tanpa_jumlah_sampel_ditolak(self):
        self.client.force_login(self.qc)
        payload = self._payload(metode="sampling", sample_size="", qty_fail=1)
        payload["unit-TOTAL_FORMS"] = 0
        payload["unit-0-unit_ref"] = ""
        payload["unit-0-categories"] = []
        payload["unit-1-unit_ref"] = ""
        payload["unit-1-categories"] = []
        payload["unit-TOTAL_FORMS"] = 2
        response = self.client.post(
            reverse("inspection_create_batch", args=[self.batch.pk]), payload
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jumlah sampel wajib diisi")
        self.assertEqual(QcInspection.objects.count(), 0)

    def test_sampling_menghitung_dari_sampel(self):
        self.client.force_login(self.qc)
        payload = self._payload(
            metode="sampling",
            sample_size=100,
            qty_fail=3,
            **{
                "unit-TOTAL_FORMS": 0,
            },
        )
        response = self.client.post(
            reverse("inspection_create_batch", args=[self.batch.pk]), payload
        )
        self.assertEqual(response.status_code, 302)
        inspection = QcInspection.objects.get()
        self.assertEqual(inspection.qty_inspected, 100)
        self.assertEqual(inspection.sample_size, 100)
        self.assertAlmostEqual(inspection.defect_rate, 3.0)

    def test_detail_unit_tidak_boleh_melebihi_cacat(self):
        self.client.force_login(self.qc)
        payload = self._payload(qty_fail=1)
        response = self.client.post(
            reverse("inspection_create_batch", args=[self.batch.pk]), payload
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QcInspection.objects.count(), 0)


class PermissionTest(BaseInspectionTest):
    def test_qc_tidak_bisa_membuka_dashboard(self):
        self.client.force_login(self.qc)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_supervisor_bisa_membuka_dashboard(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_qc_tidak_bisa_mengubah_pemeriksaan_final(self):
        inspection = self.make_inspection()
        self.client.force_login(self.qc)
        response = self.client.get(reverse("inspection_update", args=[inspection.pk]))
        self.assertEqual(response.status_code, 302)

    def test_supervisor_bisa_void_dengan_alasan(self):
        inspection = self.make_inspection()
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("inspection_void", args=[inspection.pk]),
            {"reason": "Salah input unit"},
        )
        self.assertEqual(response.status_code, 302)
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, QcInspection.Status.VOID)
        self.assertEqual(inspection.void_reason, "Salah input unit")

    def test_void_tanpa_alasan_ditolak(self):
        inspection = self.make_inspection()
        self.client.force_login(self.supervisor)
        self.client.post(
            reverse("inspection_void", args=[inspection.pk]), {"reason": ""}
        )
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, QcInspection.Status.FINAL)


class InspectionEditTest(BaseInspectionTest):
    def test_koreksi_oleh_supervisor_menulis_ulang_detail(self):
        inspection = self.make_inspection(inspected=1000, fail=1)
        unit = InspectionUnit.objects.create(inspection=inspection, unit_ref="UNIT-001")
        InspectionDefect.objects.create(
            unit=unit, category=self.cat_crimp, severity="major"
        )
        self.client.force_login(self.supervisor)

        payload = {
            "batch": self.batch.pk,
            "metode": "full",
            "total_production": 1000,
            "sample_size": "",
            "qty_fail": 2,
            "catatan": "Koreksi",
            "unit-TOTAL_FORMS": 2,
            "unit-INITIAL_FORMS": 0,
            "unit-MIN_NUM_FORMS": 0,
            "unit-MAX_NUM_FORMS": 1000,
            "unit-0-unit_ref": "UNIT-001",
            "unit-0-categories": [self.cat_housing.pk],
            "unit-0-severity": "major",
            "unit-0-catatan": "",
            "unit-1-unit_ref": "UNIT-002",
            "unit-1-categories": [self.cat_crimp.pk],
            "unit-1-severity": "minor",
            "unit-1-catatan": "",
            "action": "final",
        }
        response = self.client.post(
            reverse("inspection_update", args=[inspection.pk]), payload
        )
        self.assertEqual(response.status_code, 302)
        inspection.refresh_from_db()
        self.assertEqual(inspection.qty_fail, 2)
        self.assertEqual(inspection.units.count(), 2)
        self.assertEqual(inspection.defect_occurrences, 2)
