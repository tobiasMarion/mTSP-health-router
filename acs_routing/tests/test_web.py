"""End-to-end checks for the browser workflow with a temporary database."""

import csv
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from acs_routing.family_files import MANUAL_HEADERS


@unittest.skipUnless(importlib.util.find_spec("flask"), "install the web extra")
class WebFlowTests(unittest.TestCase):
    def setUp(self):
        from acs_routing.web import create_app

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "app.sqlite3"
        self.app = create_app(self.database)
        self.app.testing = True
        self.client = self.app.test_client()
        self.client.get("/novo")
        with self.client.session_transaction() as session:
            self.csrf = session["csrf_token"]

    def _csv(self):
        rows = []
        for family_id in (1, 2, 3):
            row = {key: "0" for key in MANUAL_HEADERS}
            row.update(id=str(family_id), lat=str(-30 - family_id / 10000),
                       lon="-51", people_per_room="0", last_visit_date="2026-01-01",
                       manual_priority="normal", name=f"Família {family_id}")
            row.update(fixed_day="", fixed_period_weeks="", fixed_phase_weeks="")
            rows.append(row)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode()

    def test_import_plan_and_complete_only_after_visit(self):
        response = self.client.post("/familias/importar", data={
            "csrf_token": self.csrf,
            "file": (io.BytesIO(self._csv()), "familias.csv"),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"3 fam", response.data)

        response = self.client.post("/planos", data={
            "csrf_token": self.csrf, "planning_date": "2026-11-23", "shift_minutes": "360",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request.path, "/planos/1")
        self.assertEqual(response.data.count(b'<details class="route-day">'), 5)
        self.assertIn(b'id="weekly-plan-map"', response.data)
        self.assertIn(b'class="plan-map daily-map"', response.data)
        self.assertIn(b'plan-maps.js', response.data)

        with sqlite3.connect(self.database) as db:
            plan = json.loads(db.execute("SELECT data FROM plans WHERE id = 1").fetchone()[0])
            row = json.loads(db.execute("SELECT data FROM families WHERE id = 1").fetchone()[0])
        self.assertEqual(row["last_visit_date"], "2026-01-01")
        route = next(route for route in plan["routes"] if len(route["sequence"]) > 2)
        family_id = route["sequence"][1]
        self.assertEqual(self.client.get('/planos/1/mapa').status_code, 200)
        gpx = self.client.get(f"/planos/1/rotas/{route['agent']}/{route['day']}.gpx")
        self.assertEqual(gpx.status_code, 200)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(gpx.data)
        points = root.findall('.//{http://www.topografix.com/GPX/1/1}rtept')
        self.assertEqual(len(points), len(route['sequence']))
        family = next(f for f in plan['families'] if f['id'] == family_id)
        self.assertAlmostEqual(float(points[1].attrib['lat']), family['lat'])
        self.assertAlmostEqual(float(points[1].attrib['lon']), family['lon'])
        response = self.client.post(f"/planos/1/visitas/{family_id}", data={
            "csrf_token": self.csrf, "visit_date": route["visit_date"],
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Visita conclu", response.data)
        with sqlite3.connect(self.database) as db:
            row = json.loads(db.execute("SELECT data FROM families WHERE id = ?", (family_id,)).fetchone()[0])
        self.assertEqual(row["last_visit_date"], route["visit_date"])
        self.assertIn(b"agente,dia,ordem", self.client.get("/planos/1/csv").data)

        response = self.client.post('/novo/iniciar', data={'csrf_token': self.csrf}, follow_redirects=True)
        self.assertIn(b'0 fam', response.data)
        self.assertNotIn('Família 1'.encode(), response.data)
        self.assertEqual(self.client.get('/planos/1').status_code, 200)
        response = self.client.post('/planos', data={'csrf_token': self.csrf,
                                    'planning_date': '2026-11-23', 'shift_minutes': '360'},
                                    follow_redirects=True)
        self.assertIn(b'Importe ou cadastre fam', response.data)

    def test_invalid_import_does_not_replace_families(self):
        self.client.post("/familias/importar", data={
            "csrf_token": self.csrf, "file": (io.BytesIO(self._csv()), "familias.csv"),
        })
        response = self.client.post("/familias/importar", data={
            "csrf_token": self.csrf, "file": (io.BytesIO(b"id,lat\n4,-30\n"), "invalido.csv"),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"3 fam", response.data)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM families").fetchone()[0], 3)

    def test_manual_family_accepts_coordinates_selected_by_map(self):
        response = self.client.post('/familias/adicionar', data={
            'csrf_token': self.csrf, 'name': 'Pessoa teste', 'address': 'Rua de teste, 10',
            'lat': '-30.04', 'lon': '-51.16', 'people_per_room': '1',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pessoa teste', response.data)
        with sqlite3.connect(self.database) as db:
            data = json.loads(db.execute('SELECT data FROM families WHERE id = 1').fetchone()[0])
        self.assertEqual((data['lat'], data['lon']), ('-30.04', '-51.16'))

    def test_password_blocks_private_pages_until_login(self):
        from acs_routing.web import create_app

        with patch.dict(os.environ, {"ACS_WEB_PASSWORD": "senha-de-teste",
                                     "ACS_WEB_SECRET_KEY": "segredo-de-teste"}):
            protected = create_app(Path(self.directory.name) / "protected.sqlite3")
        protected.testing = True
        client = protected.test_client()
        response = client.get("/planos")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)
        client.get("/login")
        with client.session_transaction() as session:
            csrf = session["csrf_token"]
        response = client.post("/login", data={"csrf_token": csrf,
                                               "password": "senha-de-teste"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/planos").status_code, 200)
        with client.session_transaction() as session:
            csrf = session["csrf_token"]
        self.assertEqual(client.post("/logout", data={"csrf_token": csrf}).status_code, 302)
        self.assertEqual(client.get("/planos").status_code, 302)


if __name__ == "__main__":
    unittest.main()
