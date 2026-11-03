# PRD — QCMS (Quality Control Management System)

**Konteks:** Studi kasus manufaktur wiring harness (nama perusahaan disamarkan)
**Versi:** 1.0 (implementasi)
**Tanggal:** 3 November 2026
**Stack:** Python 3.12 · Django 6 · SQLite/PostgreSQL 16 · Bootstrap 5 · Chart.js · Docker

---

## 1. Latar Belakang

Pemeriksaan QC rangkaian kabel dicatat manual per shift. Akibatnya rekap
memakan waktu, riwayat per kode produksi sulit ditelusuri, dan analisis jenis
kecacatan harus dibuat ulang di Excel.

**Tujuan:** satu aplikasi web sederhana untuk mencatat hasil pemeriksaan,
menghitung defect rate otomatis, dan menampilkan jenis kecacatan terbanyak
sebagai dasar prioritas perbaikan.

---

## 2. Keputusan yang Dikunci

| # | Topik | Keputusan |
|---|---|---|
| 1 | Kode produksi | Dibuat otomatis: `QC-YYYYMMDD-L<n>-<urut>` |
| 2 | Metode pemeriksaan | Full Inspection **dan** Sampling Inspection |
| 3 | Export laporan | CSV **dan** Excel (.xlsx, openpyxl) |
| 4 | Deployment | Lokal (SQLite) → server kantor (PostgreSQL + Docker) |
| 5 | Multi-defect | Ya, satu unit boleh memiliki beberapa kategori |
| 6 | Pengguna | Admin, Supervisor QC, Petugas QC (hak akses berbeda) |
| 7 | Data pemeriksaan | Per batch **dan** per unit (detail unit opsional) |
| 8 | Bahasa | Bahasa Indonesia |
| 9 | IoT | Tidak ada (di luar ruang lingkup) |

---

## 3. Peran & Hak Akses

| Aksi | Admin | Supervisor QC | Petugas QC |
|---|---|---|---|
| Kelola pengguna | ✅ | ❌ | ❌ |
| Master data (produk, lini, shift, kategori) | ✅ CRUD | 👁 lihat | 👁 lihat |
| Buat batch produksi | ✅ | ✅ | ✅ |
| Input pemeriksaan | ✅ | ✅ | ✅ |
| Koreksi sesi final | ✅ | ✅ | ❌ |
| Void pemeriksaan | ✅ | ✅ | ❌ |
| Dashboard & analisis | ✅ | ✅ | ❌ |
| Laporan & export | ✅ | ✅ | ❌ |
| Jejak audit | ✅ | 👁 | ❌ |

---

## 4. Alur Utama

**S1 — Input pemeriksaan**
Pilih batch (atau buat batch baru) → pilih metode → isi total produksi /
jumlah sampel → isi jumlah unit cacat → (opsional) catat detail unit cacat
dengan satu atau lebih kategori → simpan draft/final.

**S2 — Telusur riwayat**
Cari kode produksi / periode / lini / shift → daftar sesi → detail sesi
(termasuk rincian unit dan kategori kecacatan).

**S3 — Review supervisor**
Dashboard periode terpilih → KPI, tren, Pareto, severity → ambil keputusan
pemeriksaan lanjutan bila melewati ambang.

**S4 — Laporan**
Pilih periode & filter → rekap per sesi → export CSV/XLSX atau cetak.

---

## 5. Aturan Bisnis

1. `qty_pass + qty_fail = qty_inspected` (validasi form + model).
2. `defect_rate = qty_fail / qty_inspected × 100` (2 desimal).
3. `pass_rate = qty_pass / qty_inspected × 100`.
4. `coverage = qty_inspected / total_production × 100`.
5. `DPU = jumlah kejadian cacat / qty_inspected`.
6. Full inspection → `qty_inspected = total_production`.
7. Sampling → `qty_inspected = sample_size`, `sample_size ≤ total_production`.
   Defect rate dihitung dari sampel, bukan total produksi.
8. Kode produksi unik dan tidak dapat diedit; urutan reset per tanggal per lini.
9. Detail unit bersifat opsional, tetapi tidak boleh melebihi jumlah unit cacat
   dan tidak boleh ada kode unit ganda dalam satu sesi.
10. Satu unit tidak boleh memiliki kategori kecacatan yang sama dua kali.
11. Sesi `final` hanya dapat dikoreksi Supervisor/Admin; perubahan masuk audit log.
12. Data tidak dihapus; sesi dapat di-void dengan alasan wajib.
13. Void & draft tidak dihitung dalam dashboard/laporan.
14. Ambang peringatan defect rate default **3,0%** (dapat diubah lewat `.env`).

**Catatan desain:** jumlah unit cacat diisi sebagai angka, sedangkan detail unit
opsional. Tujuannya agar input tetap cepat di lini (mis. 30 unit cacat tidak
wajib diisi 30 baris), sementara analisis Pareto tetap tersedia untuk unit yang
detailnya dicatat. Detail halaman menampilkan berapa unit cacat yang belum
memiliki detail.

---

## 6. Skema Data

```
users(id, username*, password, nama_lengkap, role[admin|supervisor|qc], is_active)

production_lines(id, kode* "L1", nama, is_active)
shifts(id, kode* "1|2|3", nama, jam_mulai, jam_selesai, is_active)
products(id, part_number*, nama, customer, model, is_active)
defect_categories(id, kode*, nama, grup, severity_default[critical|major|minor], is_active)

production_batches(id, kode* "QC-20261103-L1-001", product_id, line_id, shift_id,
                   tanggal_produksi, qty_plan, catatan, created_by, created_at)

qc_inspections(id, batch_id, inspector_id, metode[full|sampling],
               total_production, sample_size, qty_inspected, qty_pass, qty_fail,
               inspected_at, status[draft|final|void], catatan,
               void_reason, voided_by, voided_at, created_at, updated_at)

inspection_units(id, inspection_id, unit_ref, is_pass, catatan)
   UNIQUE(inspection_id, unit_ref)

inspection_defects(id, unit_id, category_id, severity, catatan)
   UNIQUE(unit_id, category_id)

audit_logs(id, user_id, aksi, model_name, object_id, ringkasan, changes JSON, created_at)
```

Relasi: PRODUCT 1:N BATCH 1:N INSPECTION 1:N UNIT 1:N DEFECT N:1 CATEGORY.

---

## 7. Metrik & Contoh Kasus

Contoh 1.000 unit, 970 lolos, 30 cacat:

| Metrik | Nilai |
|---|---|
| Produk diperiksa | 1.000 |
| Produk lolos | 970 |
| Produk cacat | 30 |
| **Defect rate** | **3,00%** |
| Pass rate | 97,00% |

Contoh dashboard agregat 10.000 / 9.500 / 9.200 / 300 → **3,16%**.

Bila 30 unit cacat memiliki total 42 kejadian cacat (sebagian unit punya 2
kategori), maka Pareto memakai angka **42 kejadian**, sedangkan defect rate tetap
memakai **30 unit**.

---

## 8. Kebutuhan Non-Fungsional

| Aspek | Ketentuan |
|---|---|
| Bahasa | Indonesia, tanggal `dd-mm-yyyy`, angka `1.000` dan `3,00%` |
| Zona waktu | `Asia/Jakarta` |
| Perangkat | Desktop & tablet, responsive Bootstrap |
| Keamanan | CSRF, password hashing, proteksi view per role, `DEBUG=False` di produksi |
| Asset | Bootstrap & Chart.js di-vendor lokal (tahan tanpa internet) |
| Performa | Index pada `kode`, `inspected_at`, `status`, `category_id` |
| Backup | `pg_dump` harian (manual/cron) |
| Deployment | Docker Compose (`web` + `db`) |

---

## 9. Halaman & URL

| Halaman | URL |
|---|---|
| Login / Logout | `/login/`, `/logout/` |
| Dashboard | `/dashboard/` |
| Analisis Kualitas | `/analisis/` |
| Laporan | `/laporan/` |
| Export | `/laporan/export/csv/`, `/laporan/export/xlsx/` |
| Pemeriksaan QC | `/pemeriksaan/`, `/pemeriksaan/baru/` |
| Detail / Koreksi / Void | `/pemeriksaan/<id>/`, `.../koreksi/`, `.../void/` |
| Riwayat QC | `/pemeriksaan/riwayat/` |
| Data Produksi | `/produksi/`, `/produksi/baru/` |
| Master | `/master/produk/`, `/master/line/`, `/master/shift/`, `/master/kecacatan/` |
| Manajemen Pengguna | `/akun/` |
| Healthcheck | `/healthz` |

---

## 10. Pengujian (UAT)

- [x] Kasus acuan 1.000 / 970 / 30 → defect rate 3,00%
- [x] Multi-defect: 1 unit 2 kategori → 1 unit cacat, 2 kejadian cacat
- [x] Kode produksi otomatis berurutan per lini dan tanggal
- [x] Sampling menolak jumlah sampel kosong / melebihi total produksi
- [x] Petugas QC tidak dapat membuka dashboard, laporan, dan manajemen pengguna
- [x] Koreksi oleh supervisor menulis ulang detail unit + audit log
- [x] Void wajib alasan dan tidak dihitung di laporan
- [x] Export CSV & XLSX berisi data yang sama dengan tampilan
- [x] `python manage.py test apps` seluruhnya lulus

---

## 11. Pengembangan Lanjutan (di luar v1.0)

- Aturan AQL (Ac/Re, level inspeksi) otomatis
- Integrasi barcode scanner / mesin tester (IoT)
- Notifikasi email/WhatsApp saat defect rate melewati ambang
- Multi-plant dan perbandingan antar pabrik
- SPC / control chart dan analisis akar masalah (5 Why, fishbone)
