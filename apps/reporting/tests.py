from datetime import date, time
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.inspection.models import InspectionDefect, InspectionUnit, QcInspection
from apps.masterdata.models import DefectCategory, Product, ProductionLine, Shift
from apps.production.models import ProductionBatch

from . import services


class ReportingTest(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(
            username="sup", password="pass12345", role=User.Role.SUPERVISOR
        )
        self.qc = User.objects.create_user(
            username="qc", password="pass12345", role=User.Role.QC
        )
        self.line = ProductionLine.objects.create(kode="L1", nama="Line 1")
        self.shift = Shift.objects.create(
            kode="1", nama="Pagi", jam_mulai=time(7, 0), jam_selesai=time(15, 0)
        )
        self.product = Product.objects.create(part_number="WH-001", nama="Harness")
        self.cat_a = DefectCategory.objects.create(kode="C01", nama="Crimp longgar")
        self.cat_b = DefectCategory.objects.create(kode="K01", nama="Housing rusak")

        self.batch = ProductionBatch.objects.create(
            product=self.product,
            line=self.line,
            shift=self.shift,
            tanggal_produksi=date(2026, 11, 3),
            qty_plan=1000,
        )

    def _inspection(self, inspected, fail, status=QcInspection.Status.FINAL):
        return QcInspection.objects.create(
            batch=self.batch,
            inspector=self.qc,
            metode=QcInspection.Metode.FULL,
            total_production=self.batch.qty_plan,
            qty_inspected=inspected,
            qty_pass=inspected - fail,
            qty_fail=fail,
            status=status,
            inspected_at=timezone.now(),
        )

    def test_summary_menghitung_hanya_final(self):
        self._inspection(1000, 30)
        self._inspection(500, 20, status=QcInspection.Status.VOID)
        self._inspection(200, 10)

        qs = services.base_queryset(timezone.localdate(), timezone.localdate(), {})
        data = services.summary(qs)
        self.assertEqual(data["inspected"], 1200)
        self.assertEqual(data["failed"], 40)
        self.assertAlmostEqual(data["defect_rate"], 3.3333, places=3)
        self.assertEqual(data["sessions"], 2)

    def test_pareto_menghitung_kejadian_bukan_unit(self):
        inspection = self._inspection(100, 2)
        unit = InspectionUnit.objects.create(inspection=inspection, unit_ref="UNIT-001")
        InspectionDefect.objects.create(
            unit=unit, category=self.cat_a, severity="major"
        )
        InspectionDefect.objects.create(
            unit=unit, category=self.cat_b, severity="critical"
        )
        unit2 = InspectionUnit.objects.create(
            inspection=inspection, unit_ref="UNIT-002"
        )
        InspectionDefect.objects.create(
            unit=unit2, category=self.cat_a, severity="major"
        )

        qs = services.base_queryset(timezone.localdate(), timezone.localdate(), {})
        rows = services.pareto(qs)
        by_code = {row["category__kode"]: row for row in rows}
        self.assertEqual(by_code["C01"]["total"], 2)
        self.assertEqual(by_code["K01"]["total"], 1)
        self.assertAlmostEqual(by_code["C01"]["pct"], 66.666, places=2)
        self.assertAlmostEqual(by_code["K01"]["cum_pct"], 100.0)

    def test_export_csv_dan_xlsx(self):
        self._inspection(1000, 30)
        self.client.force_login(self.supervisor)

        csv_response = self.client.get(reverse("report_export_csv"))
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response["Content-Type"])
        self.assertIn("Kode Produksi", csv_response.content.decode("utf-8-sig"))

        xlsx_response = self.client.get(reverse("report_export_xlsx"))
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertIn("spreadsheetml", xlsx_response["Content-Type"])

        from openpyxl import load_workbook

        workbook = load_workbook(BytesIO(xlsx_response.content))
        self.assertIn("Laporan QC", workbook.sheetnames)
        sheet = workbook["Laporan QC"]
        self.assertEqual(sheet.cell(row=5, column=1).value, "Kode Produksi")

    def test_qc_tidak_bisa_export(self):
        self.client.force_login(self.qc)
        response = self.client.get(reverse("report_export_csv"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_tampil(self):
        self._inspection(1000, 30)
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Defect Rate")

    def test_trend_mengisi_hari_kosong(self):
        self._inspection(1000, 30)
        dari = timezone.localdate()
        qs = services.base_queryset(dari, dari, {})
        trend = services.daily_trend(qs, dari, dari)
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["inspected"], 1000)
