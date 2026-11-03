# Catatan Keputusan Teknis

Dokumen ini mencatat **mengapa** sistem dibangun seperti ini, bukan hanya apa
yang dibangun. Setiap keputusan menyertakan alternatif yang ditolak dan
konsekuensinya.

---

## 1. Defect rate dari unit yang diperiksa, bukan total produksi

**Keputusan.** `defect_rate = qty_fail / qty_inspected × 100`.

**Alternatif yang ditolak.** `qty_fail / total_production`. Lebih sederhana
karena hanya butuh satu angka dari batch.

**Alasan.** Pada metode sampling, keduanya berbeda jauh. Contoh: 1.000 unit
diproduksi, 87 diperiksa, 4 cacat.

| Basis | Perhitungan | Hasil |
|---|---|---|
| Total produksi | 4 / 1.000 | 0,40% |
| Unit diperiksa | 4 / 87 | **4,60%** |

Angka 0,40% menyesatkan: sampel 87 unit dipilih justru untuk mendeteksi masalah,
dan 4,6% adalah estimasi yang benar untuk populasi. Memakai total produksi akan
membuat lini yang bermasalah terlihat sehat.

**Konsekuensi.** `qty_inspected` wajib disimpan terpisah dari
`total_production`, dan form harus memvalidasi `sample_size ≤ total_production`.
Ada tes yang mengunci kasus acuan 1.000 / 970 / 30 → tepat 3,00%.

---

## 2. Model hibrida: agregat header + detail hanya untuk unit cacat

**Keputusan.**

```
QcInspection    → qty_inspected, qty_pass, qty_fail        (selalu)
InspectionUnit  → satu baris per unit yang cacat           (opsional)
InspectionDefect→ satu baris per kategori per unit cacat   (opsional)
```

**Alternatif yang ditolak.**

| Alternatif | Masalah |
|---|---|
| Satu baris per unit untuk semua unit | Batch 1.200 unit → 1.200 baris per pemeriksaan. Input di lantai produksi jadi lambat, database membengkak. |
| Hanya agregat, tanpa detail unit | Tidak bisa menjawab "cacat apa yang terjadi pada unit ini". Pareto kehilangan dasar. |
| Detail wajib untuk setiap unit cacat | Petugas QC memperlambat input hanya untuk memenuhi kelengkapan data yang tidak selalu dibutuhkan. |

**Alasan.** Di lantai produksi, kecepatan input adalah segalanya. Petugas harus
bisa mencatat "30 cacat dari 1.000 diperiksa" dalam hitungan detik, lalu
melengkapi kategori nanti bila ada waktu. Data yang tidak lengkap tetapi dicatat
lebih berguna daripada data lengkap yang tidak pernah diisi.

**Konsekuensi.** Harus ada cara melihat celah. Halaman detail menampilkan jumlah
unit cacat yang belum punya kategori, sehingga kekurangan data terlihat dan bisa
ditindaklanjuti — bukan hilang diam-diam.

---

## 3. Pareto menghitung kejadian; defect rate menghitung unit

**Keputusan.** Dua angka berbeda dari data yang sama, keduanya ditampilkan,
ditambah DPU sebagai jembatan.

**Contoh.** 30 unit cacat, salah satunya punya 2 kategori → 31 kejadian.

| Pertanyaan | Ukuran | Angka |
|---|---|---|
| Berapa unit yang harus dibuang? | unit | 30 |
| Berapa defect rate-nya? | unit / diperiksa | 3,00% |
| Apa yang harus diperbaiki dulu? | kejadian | Pareto 31 |
| Berapa cacat per unit? | kejadian / unit | DPU 0,031 |

**Alasan.** Menjumlahkan unit dan kejadian menghasilkan angka yang tidak berarti.
Jika Pareto memakai unit, cacat yang selalu muncul berpasangan akan terlihat
setengah lebih kecil dari kenyataannya, dan prioritas perbaikan jadi salah.

**Konsekuensi.** Pengguna harus paham perbedaan ini. Karena itu label di UI
menyebut eksplisit "unit" vs "kejadian", bukan sekadar "cacat".

---

## 4. Tidak ada penghapusan — hanya void dengan alasan wajib

**Keputusan.** `status ∈ {draft, final, void}`. Void wajib `void_reason`,
mencatat `voided_by` dan `voided_at`. Baris tetap ada selamanya.

**Alternatif yang ditolak.** `DELETE` biasa. Lebih sederhana, tidak perlu kolom
tambahan.

**Alasan.** Dalam sistem mutu, jejak adalah produk utamanya. Jika pemeriksaan
yang salah bisa hilang tanpa bekas, maka tidak ada cara membedakan "tidak pernah
diperiksa" dari "diperiksa lalu dihapus". Auditor akan menanyakan hal ini.

**Konsekuensi.** Setiap query laporan harus memfilter `status="final"`. Filter
ini terpusat di `reporting/services.base_queryset()`, bukan diulang di setiap
view — kalau tersebar, cepat atau lambat ada satu tempat yang terlewat.

**Aturan tambahan.** Sesi `final` hanya bisa dikoreksi Supervisor/Admin, dan
koreksi menulis `AuditLog`. Petugas QC yang salah input harus melapor, bukan
memperbaiki sendiri — pemisahan tugas yang disengaja.

---

## 5. Kode produksi per lini dan per tanggal, dibuat dalam transaksi

**Keputusan.** Format `QC-YYYYMMDD-L<n>-<urut>`, urutan reset tiap hari per lini.

**Alternatif yang ditolak.**

| Alternatif | Masalah |
|---|---|
| Auto-increment `id` | Tidak informatif. Orang di lantai produksi tidak bisa menyebut "batch 4821". |
| Satu counter global | Kode lini L1 dan L2 bercampur, sulit dibaca saat dicetak di label. |
| UUID | Tidak bisa diucapkan lewat radio atau telepon. |

**Alasan.** Kode dibaca manusia, bukan mesin. Format ini langsung memberi tahu
tanggal, lini, dan urutan.

**Konsekuensi.** Pembuatan kode rawan race condition bila dua petugas menyimpan
bersamaan. Solusinya `select_for_update()` pada baris terakhir dengan prefix sama,
ditambah retry hingga 5 kali pada `IntegrityError`. Alternatifnya — sequence
PostgreSQL — lebih cepat tetapi mengikat ke satu database, sedangkan
pengembangan lokal memakai SQLite.

---

## 6. Export Excel menulis angka asli

**Keputusan.** Kolom numerik ditulis sebagai `int`/`float` dengan format
`#,##0` dan `0.00`.

**Alternatif yang ditolak.** Menulis semuanya sebagai string hasil format
Indonesia (`"1.234"`, `"4,60"`). Tampilan lebih konsisten dengan layar.

**Alasan.** File yang terlihat benar tetapi tidak bisa di-`SUM` adalah jebakan.
Pengguna akan menambah kolom sendiri, mendapatkan `0`, dan menyimpulkan
aplikasinya rusak. Format angka diserahkan ke Excel, bukan ke string Python.

**Konsekuensi.** Tampilan di Excel sedikit berbeda dari layar (pemisah mengikuti
locale Excel pengguna), tetapi datanya bisa dihitung. Ini pertukaran yang benar.

---

## 7. Bootstrap dan Chart.js di-vendor lokal

**Keputusan.** Library disimpan di `static/vendor/`, disajikan WhiteNoise.

**Alternatif yang ditolak.** CDN. Lebih ringan untuk repo.

**Alasan.** Jaringan pabrik sering offline atau memblokir domain luar. Halaman
yang kehilangan CSS saat jaringan bermasalah akan dianggap aplikasi rusak.

**Konsekuensi.** Repo ~450 KB lebih besar, dan pembaruan library manual.

---

## 8. `DEBUG=False` di-hardcode pada container

**Keputusan.** `docker-compose.yml` menetapkan `DEBUG: "False"` secara literal,
bukan `${DEBUG:-False}`.

**Alasan.** Versi sebelumnya memakai `${DEBUG:-False}`, yang tetap menarik
`DEBUG=True` dari `.env` pengembangan. Traceback Django menampilkan potongan
kode, nama variabel, dan pengaturan — tidak boleh muncul di lantai produksi.

**Konsekuensi.** Untuk men-debug container, harus mengubah compose secara
sengaja. Ini disengaja: mode debug di produksi harus keputusan sadar.

---

## 9. Logika bisnis di `services.py`, bukan di view

**Keputusan.** Perhitungan dan mutasi data berada di modul `services.py`;
view hanya menangani HTTP.

**Alasan.** Aturan seperti "total diperiksa harus sama dengan lolos + cacat" dan
"detail unit tidak boleh melebihi jumlah cacat" perlu diuji tanpa membuat request
HTTP. Tes yang menembak endpoint jauh lebih lambat dan rapuh.

**Konsekuensi.** Satu lapisan tambahan. Untuk aplikasi sebesar ini masih
sepadan, karena 27 tes berjalan dalam ~35 detik, bukan menit.

---

## 10. Bahasa Indonesia di UI dan kode

**Keputusan.** UI, komentar, dan dokumentasi internal berbahasa Indonesia.
README tersedia dalam dua bahasa.

**Alasan.** Penggunanya operator dan staf QC pabrik Indonesia. Istilah seperti
"crimp longgar", "terminal back-out", dan "tube corrugated hilang" adalah bahasa
kerja mereka; menerjemahkannya ke Inggris justru menambah beban kognitif.

**Konsekuensi.** Kode kurang mudah ditinjau audiens internasional. Karena itu
README utama berbahasa Inggris dan dokumen ini menjelaskan alasan di baliknya.

---

## Yang sengaja tidak dibuat (v1.0)

| Fitur | Alasan ditunda |
|---|---|
| Aturan AQL otomatis (Ac/Re) | Butuh tabel ISO 2859-1 dan pelatihan pengguna. Nilai tinggi, tetapi bukan penghalang adopsi awal. |
| Integrasi barcode scanner | Perangkat keras belum ada; input manual masih memadai untuk 241 sesi/bulan. |
| Notifikasi email/WhatsApp | Butuh infrastruktur tambahan. Badge ambang di dashboard sudah memberi sinyal. |
| SPC / control chart | Membutuhkan data historis yang stabil dulu. |
| Multi-plant | Belum ada kebutuhan; menambah kompleksitas model tanpa pengguna. |

Menunda fitur ini adalah keputusan, bukan kelalaian.
