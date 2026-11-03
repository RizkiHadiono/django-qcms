"""Seed data demo untuk QCMS.

Menghasilkan data master, pengguna, batch produksi, dan pemeriksaan QC
selama beberapa hari terakhir sehingga dashboard langsung berisi data.

Contoh: python manage.py seed_demo --days 30
"""

import random
from datetime import time as clock_time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.inspection.models import InspectionDefect, InspectionUnit, QcInspection
from apps.masterdata.models import (
    DefectCategory,
    Product,
    ProductionLine,
    Severity,
    Shift,
)
from apps.production.models import ProductionBatch

LINES = [
    ("L1", "Line 1 - Harness Main"),
    ("L2", "Line 2 - Harness Engine"),
    ("L3", "Line 3 - Harness Panel"),
]

SHIFTS = [
    ("1", "Shift Pagi", "07:00", "15:00"),
    ("2", "Shift Siang", "15:00", "23:00"),
    ("3", "Shift Malam", "23:00", "07:00"),
]

PRODUCTS = [
    ("WH-8A0-001", "Harness Main Room", "Toyota", "Avanza"),
    ("WH-8A0-002", "Harness Engine Room", "Toyota", "Avanza"),
    ("WH-8A0-003", "Harness Panel Dashboard", "Toyota", "Rush"),
    ("WH-8A0-004", "Harness Rear Body", "Daihatsu", "Xenia"),
    ("WH-8A0-005", "Harness Front Door", "Daihatsu", "Terios"),
    ("WH-8A0-006", "Harness ABS", "Mitsubishi", "Xpander"),
    ("WH-8A0-007", "Harness Airbag", "Mitsubishi", "Xpander"),
    ("WH-8A0-008", "Harness Audio", "Honda", "BR-V"),
    ("WH-8A0-009", "Harness Lamp Front", "Honda", "Mobilio"),
    ("WH-8A0-010", "Harness Fuel Pump", "Suzuki", "Ertiga"),
]

CATEGORIES = [
    ("E01", "Continuity fail", "electrical", Severity.CRITICAL),
    ("E02", "Short circuit", "electrical", Severity.CRITICAL),
    ("E03", "Mis-wiring", "electrical", Severity.CRITICAL),
    ("C01", "Crimp longgar", "crimping", Severity.MAJOR),
    ("C02", "Strand terpotong", "crimping", Severity.MAJOR),
    ("C03", "Terminal tidak masuk penuh", "crimping", Severity.MAJOR),
    ("K01", "Housing rusak", "connector", Severity.MAJOR),
    ("K02", "Terminal back-out", "connector", Severity.CRITICAL),
    ("K03", "Salah tipe connector", "connector", Severity.MAJOR),
    ("W01", "Salah warna kabel", "wire", Severity.MINOR),
    ("W02", "Panjang tidak sesuai", "wire", Severity.MINOR),
    ("W03", "Isolasi tergores", "wire", Severity.MAJOR),
    ("T01", "Tape longgar", "taping", Severity.MINOR),
    ("T02", "Tube corrugated hilang", "taping", Severity.MINOR),
    ("R01", "Routing salah", "routing", Severity.MAJOR),
    ("R02", "Clip hilang", "routing", Severity.MINOR),
    ("L01", "Label hilang", "labeling", Severity.MINOR),
    ("L02", "Label salah", "labeling", Severity.MAJOR),
]

# Bobot agar beberapa jenis kecacatan tampak lebih dominan (untuk Pareto).
CATEGORY_WEIGHTS = {
    "E01": 6,
    "E02": 4,
    "E03": 5,
    "C01": 14,
    "C02": 8,
    "C03": 12,
    "K01": 9,
    "K02": 6,
    "K03": 4,
    "W01": 7,
    "W02": 5,
    "W03": 9,
    "T01": 11,
    "T02": 4,
    "R01": 6,
    "R02": 5,
    "L01": 4,
    "L02": 3,
}


class Command(BaseCommand):
    help = "Isi database dengan data demo QC (pengguna, master, batch, pemeriksaan)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Jumlah hari data.")
        parser.add_argument(
            "--force", action="store_true", help="Jalankan walau data batch sudah ada."
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hapus data QC yang ada terlebih dahulu.",
        )

    def handle(self, *args, **options):
        random.seed(20261103)

        if options["reset"]:
            InspectionDefect.objects.all().delete()
            InspectionUnit.objects.all().delete()
            QcInspection.objects.all().delete()
            ProductionBatch.objects.all().delete()
            self.stdout.write(self.style.WARNING("Data QC lama dihapus."))

        if ProductionBatch.objects.exists() and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    "Data batch sudah ada. Gunakan --reset atau --force bila ingin menambah."
                )
            )
            return

        users = self._create_users()
        lines = self._create_lines()
        shifts = self._create_shifts()
        products = self._create_products()
        categories = self._create_categories()

        days = max(options["days"], 1)
        today = timezone.localdate()

        created_sessions = 0
        with transaction.atomic():
            for offset in range(days, 0, -1):
                tanggal = today - timedelta(days=offset)
                for line in lines:
                    for shift in shifts:
                        if random.random() > 0.85:
                            continue
                        product = random.choice(products)
                        self._create_batch_and_session(
                            product=product,
                            line=line,
                            shift=shift,
                            tanggal=tanggal,
                            inspector=users["qc"],
                            categories=categories,
                        )
                        created_sessions += 1

            # Batch contoh hari ini: 1.000 unit, 970 lolos, 30 cacat (3%).
            hero = ProductionBatch.objects.create(
                product=products[0],
                line=lines[0],
                shift=shifts[0],
                tanggal_produksi=today,
                qty_plan=1000,
                catatan="Batch contoh sesuai studi kasus PRD.",
                created_by=users["supervisor"],
            )
            self._create_session(
                batch=hero,
                metode=QcInspection.Metode.FULL,
                inspected=1000,
                fail_count=30,
                inspector=users["qc"],
                categories=categories,
            )
            created_sessions += 1

            # Tambahan batch hari ini untuk lini lain.
            for index, line in enumerate(lines[1:], start=1):
                product = products[index]
                shift = shifts[index]
                batch = ProductionBatch.objects.create(
                    product=product,
                    line=line,
                    shift=shift,
                    tanggal_produksi=today,
                    qty_plan=random.randint(800, 1100),
                    created_by=users["qc"],
                )
                self._create_session(
                    batch=batch,
                    metode=random.choice(
                        [QcInspection.Metode.FULL, QcInspection.Metode.SAMPLING]
                    ),
                    inspected=None,
                    fail_count=None,
                    inspector=users["qc"],
                    categories=categories,
                )
                created_sessions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai. {created_sessions} sesi pemeriksaan, "
                f"{ProductionBatch.objects.count()} batch produksi."
            )
        )
        self.stdout.write("Akun demo:")
        self.stdout.write("  admin / admin123            (Admin)")
        self.stdout.write("  supervisor / supervisor123  (Supervisor QC)")
        self.stdout.write("  qc / qc123                  (Petugas QC)")

    # ------------------------------------------------------------------
    def _create_users(self):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "nama_lengkap": "Administrator Sistem",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "email": "admin@qcms.local",
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
        else:
            admin.is_superuser = True
            admin.is_staff = True
            admin.role = User.Role.ADMIN
            admin.save()

        supervisor, created = User.objects.get_or_create(
            username="supervisor",
            defaults={
                "nama_lengkap": "Budi Santoso",
                "role": User.Role.SUPERVISOR,
            },
        )
        if created:
            supervisor.set_password("supervisor123")
            supervisor.save()

        qc, created = User.objects.get_or_create(
            username="qc",
            defaults={"nama_lengkap": "Siti Aminah", "role": User.Role.QC},
        )
        if created:
            qc.set_password("qc123")
            qc.save()

        return {"admin": admin, "supervisor": supervisor, "qc": qc}

    def _create_lines(self):
        result = []
        for kode, nama in LINES:
            line, _ = ProductionLine.objects.get_or_create(
                kode=kode, defaults={"nama": nama}
            )
            result.append(line)
        return result

    def _create_shifts(self):
        result = []
        for kode, nama, mulai, selesai in SHIFTS:
            jam_mulai = clock_time(*[int(part) for part in mulai.split(":")])
            jam_selesai = clock_time(*[int(part) for part in selesai.split(":")])
            shift, _ = Shift.objects.get_or_create(
                kode=kode,
                defaults={
                    "nama": nama,
                    "jam_mulai": jam_mulai,
                    "jam_selesai": jam_selesai,
                },
            )
            result.append(shift)
        return result

    def _create_products(self):
        result = []
        for part_number, nama, customer, model in PRODUCTS:
            product, _ = Product.objects.get_or_create(
                part_number=part_number,
                defaults={"nama": nama, "customer": customer, "model": model},
            )
            result.append(product)
        return result

    def _create_categories(self):
        result = []
        for kode, nama, grup, severity in CATEGORIES:
            category, _ = DefectCategory.objects.get_or_create(
                kode=kode,
                defaults={
                    "nama": nama,
                    "grup": grup,
                    "severity_default": severity,
                },
            )
            result.append(category)
        return result

    # ------------------------------------------------------------------
    def _create_batch_and_session(
        self, product, line, shift, tanggal, inspector, categories
    ):
        qty_plan = random.randint(750, 1200)
        batch = ProductionBatch.objects.create(
            product=product,
            line=line,
            shift=shift,
            tanggal_produksi=tanggal,
            qty_plan=qty_plan,
            created_by=inspector,
        )
        metode = random.choice(
            [
                QcInspection.Metode.FULL,
                QcInspection.Metode.FULL,
                QcInspection.Metode.SAMPLING,
            ]
        )
        return self._create_session(
            batch=batch,
            metode=metode,
            inspected=None,
            fail_count=None,
            inspector=inspector,
            categories=categories,
        )

    def _create_session(
        self, batch, metode, inspected, fail_count, inspector, categories
    ):
        qty_plan = batch.qty_plan
        if inspected is None:
            if metode == QcInspection.Metode.FULL:
                inspected = qty_plan
            else:
                inspected = min(random.randint(80, 160), qty_plan)

        # Defect rate dasar per lini + variasi harian.
        base_rate = {"L1": 1.6, "L2": 2.6, "L3": 3.6}.get(batch.line.kode, 2.5)
        rate = max(0.2, random.gauss(base_rate, 0.9))

        if fail_count is None:
            fail_count = int(round(inspected * rate / 100))
            fail_count = max(0, min(fail_count, inspected))

        qty_pass = inspected - fail_count

        # Jam pemeriksaan mengikuti shift.
        start_hour = int(batch.shift.jam_mulai.hour)
        inspected_at = timezone.make_aware(
            timezone.datetime.combine(
                batch.tanggal_produksi,
                timezone.datetime.min.time(),
            )
            + timedelta(hours=start_hour, minutes=random.randint(0, 120))
        )

        status = QcInspection.Status.FINAL
        void_reason = ""
        if random.random() < 0.02:
            status = QcInspection.Status.VOID
            void_reason = "Salah input jumlah unit, data diulang pada sesi berikutnya."

        inspection = QcInspection.objects.create(
            batch=batch,
            inspector=inspector,
            metode=metode,
            total_production=qty_plan,
            sample_size=inspected if metode == QcInspection.Metode.SAMPLING else None,
            qty_inspected=inspected,
            qty_pass=qty_pass,
            qty_fail=fail_count,
            inspected_at=inspected_at,
            status=status,
            void_reason=void_reason,
            catatan="",
        )

        if fail_count == 0:
            return inspection

        units = [
            InspectionUnit(
                inspection=inspection,
                unit_ref=f"UNIT-{index:03d}",
                catatan="",
            )
            for index in range(1, fail_count + 1)
        ]
        InspectionUnit.objects.bulk_create(units)

        weights = [CATEGORY_WEIGHTS.get(category.kode, 5) for category in categories]
        defects = []
        for unit in units:
            jumlah = 1
            if random.random() < 0.28:
                jumlah = 2
            jumlah = min(jumlah, len(categories))
            chosen = random.choices(categories, weights=weights, k=jumlah)
            seen = set()
            for category in chosen:
                if category.pk in seen:
                    continue
                seen.add(category.pk)
                defects.append(
                    InspectionDefect(
                        unit=unit,
                        category=category,
                        severity=category.severity_default,
                    )
                )

        InspectionDefect.objects.bulk_create(defects)
        return inspection
