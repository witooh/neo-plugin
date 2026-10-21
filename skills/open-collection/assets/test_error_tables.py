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
renderer = load_module("yaml2md", ASSETS / "yaml2md.py")
validator = load_module("apispeccheck", ASSETS.parents[1] / "api-spec/assets/apispeccheck.py")


class ErrorTableTests(unittest.TestCase):
    def error_tables(self, errors):
        endpoint = {"endpoint": "Probe", "domain": "Account", "method": "GET", "path": "/probe", "errors": errors}
        meta = {"title": "Accounts", "version": "1.0", "base_url": "/", "common_errors": errors}
        with tempfile.TemporaryDirectory() as directory:
            return {
                "endpoint": renderer.render_endpoint(endpoint),
                "collection root": renderer.render_index(meta, directory),
                "API spec index": validator.render_index(meta, []),
            }

    def table_cells(self, markdown):
        return [[cell.strip().strip("`") for cell in line.split("|")[1:-1]]
                for line in markdown.splitlines() if line.startswith("|")]

    def test_error_tables_expose_status_and_all_wire_error_details(self):
        error = {"status": 504, "responseCode": "006", "code": "ACC-8001",
                 "message": "Gateway timed out", "description": "The posting outcome is unknown"}
        for surface, markdown in self.error_tables([error]).items():
            with self.subTest(surface=surface):
                rows = self.table_cells(markdown)
                self.assertEqual(["Status", "Response Code", "Error Code", "Error Messages"], rows[0][:4])
                self.assertEqual(["504", "006", "ACC-8001", "Gateway timed out"], rows[2][:4])
                self.assertEqual("The posting outcome is unknown", rows[2][4])

    def test_missing_error_details_stay_blank_without_prose_inference(self):
        error = {"status": 400, "description": "responseCode `001` was reported by the upstream"}
        for surface, markdown in self.error_tables([error]).items():
            with self.subTest(surface=surface):
                rows = self.table_cells(markdown)
                self.assertEqual(["Status", "Response Code", "Error Code", "Error Messages"], rows[0][:4])
                self.assertEqual(["400", "", "", ""], rows[2][:4])
                self.assertEqual(error["description"], rows[2][4])


if __name__ == "__main__":
    unittest.main()
