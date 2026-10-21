import importlib.util
from pathlib import Path
import tempfile
import unittest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ASSETS = Path(__file__).resolve().parent
validator = load_module("apispeccheck", ASSETS / "apispeccheck.py")
renderer = load_module("yaml2md", ASSETS.parents[1] / "open-collection/assets/yaml2md.py")


class ErrorResponseCodeTests(unittest.TestCase):
    def setUp(self):
        validator.errors.clear()
        self.error = {
            "status": 400,
            "responseCode": "002",
            "code": "ACC-2001",
            "message": "Account is closed",
            "description": "The account cannot be changed after closure",
        }

    def test_description_cannot_replace_structured_response_code(self):
        del self.error["responseCode"]
        self.error["description"] = "responseCode `002` — account is closed"
        validator.check_errors([self.error], "endpoint")
        self.assertTrue(any("responseCode" in error for error in validator.errors))

    def test_response_code_rejects_numeric_and_unknown_values(self):
        for value in (1, None, "01", "007"):
            with self.subTest(value=value):
                validator.errors.clear()
                validator.check_errors([{**self.error, "responseCode": value}], "endpoint")
                self.assertTrue(any("responseCode" in error for error in validator.errors))

    def test_response_code_controls_http_status(self):
        validator.check_errors([
            {**self.error, "code": "ACC-8001", "responseCode": "006", "status": 503}
        ], "endpoint")
        self.assertTrue(any("504" in error for error in validator.errors))

    def test_valid_common_lib_and_partner_contracts(self):
        validator.check_errors([
            self.error,
            {**self.error, "code": "ACC-1001", "responseCode": "001"},
            {"status": 422, "responseCode": "021", "code": "021", "description": "Partner rejection"},
            {"status": 404, "message": "Partner resource missing"},
        ], "endpoint")
        self.assertEqual([], validator.errors)

    def assert_response_codes(self, markdown):
        rows = [line.split("|")[1:-1] for line in markdown.splitlines() if line.startswith("|")]
        headers = [cell.strip() for cell in rows[0]]
        self.assertIn("Response Code", headers)
        column = headers.index("Response Code")
        self.assertEqual(["001", "002"], [row[column].strip().strip("`") for row in rows[2:]])
        self.assertEqual(["400", "400"], [row[0].strip() for row in rows[2:]])

    def test_endpoint_and_both_indexes_render_distinct_codes_for_same_status(self):
        rows = [{**self.error, "code": "ACC-1001", "responseCode": "001"}, self.error]
        endpoint = {"endpoint": "Probe", "domain": "Account", "method": "GET", "path": "/probe", "errors": rows}
        meta = {"title": "Accounts", "version": "1.0", "base_url": "/", "common_errors": rows}
        self.assert_response_codes(renderer.render_endpoint(endpoint))
        self.assert_response_codes(validator.render_index(meta, []))
        with tempfile.TemporaryDirectory() as directory:
            self.assert_response_codes(renderer.render_index(meta, directory))



if __name__ == "__main__":
    unittest.main()
