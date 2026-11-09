import importlib.util
from pathlib import Path
import unittest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ASSETS = Path(__file__).resolve().parent
GOOD = ASSETS / "testdata" / "good"
dp = load_module("docsparse", ASSETS / "docsparse.py")


class DocsParseTests(unittest.TestCase):
    def test_escaped_pipe_stays_in_one_cell(self):
        hdr, rows = dp.parse_table("| A | B |\n|---|---|\n| `SA` \\| `FD` | x |\n")
        self.assertEqual(rows[0], ["`SA` | `FD`", "x"])

    def test_request_docs_tables_and_examples(self):
        r = dp.parse_request(GOOD / "account/create-account.yml")
        d = r["docs"]
        self.assertEqual(d["endpoint"], ("POST", "/v1/accounts"))
        self.assertEqual([f["name"] for f in d["tables"]["body"]],
                         ["customerId", "accountType", "items", "items[].code"])
        self.assertIn('"customerId"', d["request_example"])
        self.assertEqual(sorted(d["responses"]), [201])
        self.assertEqual(len(d["responses"][201]["fields"]), 3)  # prose after table
        self.assertIn('"accountId"', d["responses"][201]["example"])
        self.assertEqual(d["errors"][0]["response_code"], "001")
        self.assertEqual(d["errors"][0]["status"], 400)
        self.assertEqual(d["free"], ["Business Logic"])

    def test_get_request_path_params(self):
        d = dp.parse_request(GOOD / "account/get-account.yml")["docs"]
        self.assertEqual(d["endpoint"], ("GET", "/v1/accounts/{accountId}"))
        self.assertEqual([f["name"] for f in d["tables"]["path"]], ["accountId"])
        self.assertIsNone(d["request_example"])

    def test_order(self):
        r = dp.parse_request(GOOD / "account/create-account.yml")
        self.assertEqual(r["order"], ["info", "http", "runtime", "settings", "docs"])

    def test_json_with_vars_and_key_paths(self):
        obj = dp.json_with_vars('{"a": {{amount}}, "b": "{{x}}", "items": [{"code": 1}]}')
        self.assertEqual(dp.key_paths(obj), {"a", "b", "items", "items[].code"})

    def test_group_by_parent(self):
        rows = [{"name": "data", "type": "Object"}, {"name": "data.accountId", "type": "String"}]
        self.assertEqual([r["name"] for r in dp.group_by_parent(rows)["data"]], ["accountId"])

    def test_split_sections_ignores_headings_in_fences(self):
        md = "intro\n## A\n```\n## not a heading\n```\n### B\nbody\n"
        secs = dp.split_sections(md)
        self.assertEqual([(s["level"], s["title"]) for s in secs], [(2, "A"), (3, "B")])
        self.assertEqual(secs[0]["line"], 2)


if __name__ == "__main__":
    unittest.main()
