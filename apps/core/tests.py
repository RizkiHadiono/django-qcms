from django.test import TestCase
from django.urls import reverse


class HealthzTests(TestCase):
    def test_healthz_mengembalikan_ok(self):
        resp = self.client.get(reverse("healthz"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"ok")


class ErrorPageTests(TestCase):
    """Halaman error kustom harus dipakai saat DEBUG=False (mode produksi)."""

    def test_404_memakai_template_kustom(self):
        resp = self.client.get("/alamat-yang-tidak-ada/")
        self.assertEqual(resp.status_code, 404)
        self.assertTemplateUsed(resp, "errors/404.html")
        self.assertContains(resp, "Halaman Tidak Ditemukan", status_code=404)

    def test_404_menampilkan_nama_aplikasi(self):
        resp = self.client.get("/alamat-yang-tidak-ada/")
        self.assertContains(resp, "QCMS", status_code=404)
