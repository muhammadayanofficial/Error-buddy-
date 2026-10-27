import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_service
import app as app_module
import database

GOOD = {"summary": "Fine.", "findings": [{"severity": "HIGH", "title": "Div by zero", "reference": "line 2", "why": "crash", "fix": "guard"}],
        "debug": None, "improved": {"code": "def f(): pass", "changes": ["x"]},
        "tests": {"framework": "unittest", "code": "import unittest", "explanations": [{"name": "t", "checks": "c"}]}}


class NormalizeTests(unittest.TestCase):
    def test_valid_output_is_normalised(self):
        r = ai_service.normalize_result(GOOD)
        self.assertEqual(r["findings"][0]["severity"], "high")
        self.assertIsNone(r["debug"])

    def test_unknown_severity_becomes_info(self):
        r = ai_service.normalize_result({"summary": "s", "findings": [{"severity": "wow", "title": "t"}]})
        self.assertEqual(r["findings"][0]["severity"], "info")

    def test_garbage_is_rejected(self):
        with self.assertRaises(ai_service.AIServiceError):
            ai_service.normalize_result([1, 2])
        with self.assertRaises(ai_service.AIServiceError):
            ai_service.normalize_result({})
        with self.assertRaises(ai_service.AIServiceError):
            ai_service.parse_json_text("not json")

    def test_local_check(self):
        self.assertTrue(ai_service.local_check("x = 1", "Python")["ok"])
        self.assertFalse(ai_service.local_check("def (:", "Python")["ok"])
        self.assertIsNone(ai_service.local_check("x", "Go")["ok"])


class AppTests(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.client = app_module.create_app({"DATABASE": self.db, "TESTING": True}).test_client()

    def tearDown(self):
        os.remove(self.db)

    def test_index_renders(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"PatchLens AI", r.data)

    def test_validation(self):
        self.assertEqual(self.client.post("/api/review", json={"code": "  "}).status_code, 400)
        self.assertEqual(self.client.post("/api/review", json={"code": "x", "mode": "debug"}).status_code, 400)
        self.assertEqual(self.client.post("/api/review", json={"code": "x", "language": "Klingon"}).status_code, 400)

    def test_missing_key_is_honest(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            r = self.client.post("/api/review", json={"code": "print(1)"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("API key", r.get_json()["error"])

    def test_review_history_export_delete(self):
        with mock.patch("ai_service.analyze", return_value=ai_service.normalize_result(GOOD)):
            r = self.client.post("/api/review", json={"code": "def f(): pass", "language": "Python"})
        self.assertEqual(r.status_code, 200)
        rid = r.get_json()["id"]
        self.assertEqual(len(self.client.get("/api/reviews").get_json()["reviews"]), 1)
        self.assertEqual(self.client.get(f"/api/reviews/{rid}").status_code, 200)
        md = self.client.get(f"/api/reviews/{rid}/export")
        self.assertIn(b"Div by zero", md.data)
        self.assertIn(b"have not been executed", md.data)
        self.assertEqual(self.client.delete(f"/api/reviews/{rid}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/reviews/{rid}").status_code, 404)
        self.assertEqual(self.client.get("/api/reviews").get_json()["reviews"], [])

    def test_ai_failure_returns_502_and_saves_nothing(self):
        with mock.patch("ai_service.analyze", side_effect=ai_service.AIServiceError("boom")):
            r = self.client.post("/api/review", json={"code": "x = 1"})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(database.list_reviews(self.db), [])


if __name__ == "__main__":
    unittest.main()
