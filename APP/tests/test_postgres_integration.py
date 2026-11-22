import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import psycopg

from panelqr import create_app


DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "set TEST_DATABASE_URL to a seeded test database")
class PostgresWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(prefix="panelqr-test-")
        cls.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "integration-test-key",
                "WTF_CSRF_ENABLED": False,
                "DATABASE_URL": DATABASE_URL,
                "UPLOAD_FOLDER": cls.storage.name,
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def _login(self, email):
        client = self.app.test_client()
        response = client.post(
            "/login", data={"email": email, "password": "PanelQR2026!"}
        )
        self.assertEqual(response.status_code, 302)
        return client

    def test_admin_can_view_dashboard_panels_qr_and_audit(self):
        client = self._login("admin@panelqr.local")

        self.assertEqual(client.get("/dashboard").status_code, 200)
        self.assertIn(b"Panel de control", client.get("/dashboard").data)
        self.assertEqual(client.get("/panels").status_code, 200)
        self.assertEqual(client.get("/panel/P-001").status_code, 200)
        qr = client.get("/panel/P-001/qr")
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(qr.mimetype, "image/png")
        self.assertEqual(client.get("/admin/users").status_code, 200)
        self.assertEqual(client.get("/admin/audit").status_code, 200)
        with psycopg.connect(DATABASE_URL) as connection:
            sample_version_id = connection.execute(
                """
                SELECT id_version FROM documento_version
                WHERE ruta_externa = 'demo/ficha-p001-v2.txt'
                """
            ).fetchone()[0]
        sample = client.get(f"/documents/version/{sample_version_id}")
        self.assertEqual(sample.status_code, 200)
        self.assertIn(b"Versi\xc3\xb3n: 1.1", sample.data)
        sample.close()

    def test_technician_is_limited_to_assigned_panels(self):
        client = self._login("tecnico1@panelqr.local")

        self.assertEqual(client.get("/panel/P-001").status_code, 200)
        self.assertEqual(client.get("/panel/P-002").status_code, 404)
        self.assertEqual(client.get("/admin/users").status_code, 403)

    def test_last_active_admin_cannot_be_demoted(self):
        client = self._login("admin@panelqr.local")
        with psycopg.connect(DATABASE_URL) as connection:
            admin_id = connection.execute(
                "SELECT id_usuario FROM usuario WHERE email = 'admin@panelqr.local'"
            ).fetchone()[0]
            technician_role_id = connection.execute(
                "SELECT id_rol FROM rol WHERE nombre = 'TECNICO'"
            ).fetchone()[0]

        response = client.post(
            f"/admin/users/{admin_id}",
            data={
                "nombre": "Administradora Demo",
                "email": "admin@panelqr.local",
                "activo": "on",
                "roles": str(technician_role_id),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Debe quedar al menos una cuenta ADMIN activa", response.data)

    def test_uploaded_document_is_served_only_to_authorized_users(self):
        client = self._login("admin@panelqr.local")
        title = f"Prueba de carga {uuid4().hex}"
        with psycopg.connect(DATABASE_URL) as connection:
            document_type = connection.execute(
                "SELECT id_tipo_documento FROM tipo_documento LIMIT 1"
            ).fetchone()[0]

        response = client.post(
            "/panel/P-001/documents/new",
            data={
                "titulo": title,
                "descripcion": "Documento de prueba",
                "id_tipo_documento": str(document_type),
                "numero_version": "1.0",
                "notas": "Prueba de integración",
                "archivo": (BytesIO(b"%PDF-1.4 test document"), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)

        with psycopg.connect(DATABASE_URL) as connection:
            version_id = connection.execute(
                """
                SELECT v.id_version
                FROM documento_version v
                JOIN documento d ON d.id_documento = v.id_documento
                WHERE d.titulo = %s
                """,
                (title,),
            ).fetchone()[0]

        document = client.get(f"/documents/version/{version_id}")
        self.assertEqual(document.status_code, 200)
        self.assertEqual(document.mimetype, "application/pdf")
        self.assertIn(b"%PDF-1.4", document.data)
        document.close()

        duplicate = client.post(
            "/panel/P-001/documents/new",
            data={
                "titulo": title,
                "descripcion": "Documento duplicado",
                "id_tipo_documento": str(document_type),
                "numero_version": "1.0",
                "archivo": (BytesIO(b"%PDF-1.4 duplicate"), "duplicate.pdf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn(b"ya existe", duplicate.data)
        uploads = list((Path(self.storage.name) / "uploads").iterdir())
        self.assertEqual(len(uploads), 1)

        technician = self._login("tecnico2@panelqr.local")
        self.assertEqual(
            technician.get(f"/documents/version/{version_id}").status_code, 404
        )


if __name__ == "__main__":
    unittest.main()
