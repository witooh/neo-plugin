import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ASSETS = Path(__file__).resolve().parent
LEGACY = ASSETS / "testdata" / "legacy"
MG = ASSETS / "migrate.py"
dp = load_module("docsparse", ASSETS / "docsparse.py")
bc = load_module("brunocheck", ASSETS / "brunocheck.py")
mg = load_module("migrate", MG)


class MigrateTests(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base)
        self.tmp = base / "repo"
        shutil.copytree(LEGACY, self.tmp)
        self.api, self.bruno = self.tmp / "docs/api", self.tmp / "bruno"

    def errors(self):
        return {f[1] for f in bc.check(self.bruno) if f[0] == "ERROR"}

    def replace_runtime(self, runtime_text):
        p = self.bruno / "account/create.yml"
        blocks = [(k, t) for k, t in mg.split_top_level(p.read_text()) if k != "runtime"]
        if runtime_text:
            blocks.append(("runtime", runtime_text))
        p.write_text(mg.join_blocks(blocks))
        return dict(mg.split_top_level(p.read_text()))["http"]

    def edit_spec(self, rel, change):
        p = self.api / rel
        data = yaml.safe_load(p.read_text())
        change(data)
        p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    def root_error_body(self):
        docs = yaml.safe_load((self.bruno / "opencollection.yml").read_text())["docs"]
        return dp.parse_root_docs(docs)["error_body"]

    def old_envelope(self, status):
        return {"status": status, "description": "Error", "fields": [
            {"name": "type", "description": "Error type", "type": "String", "mandatory": "M", "example": "Error"},
            {"name": "message", "description": "Message", "type": "String", "mandatory": "M", "example": "bad"},
            {"name": "errors", "description": "Details", "type": "Array", "mandatory": "O", "object": "ErrorItem"}],
            "objects": {"ErrorItem": [
                {"name": "field", "description": "Field", "type": "String", "mandatory": "M", "example": "x"}]},
            "example": '{"type": "Error", "message": "bad", "errors": [{"field": "x"}]}'}

    def drop_common_lib(self, data):
        """Legacy envelope: no common-lib code anywhere, old error body on create's 400."""
        data["errors"] = [{"status": 400, "code": "INVALID_FIELD", "message": "Invalid field", "description": "Bad"}]
        data["responses"][1] = self.old_envelope(400)
        self.edit_spec("_meta.yaml", lambda d: d.update(common_errors=[
            {"status": 400, "code": "INVALID_REQUEST", "message": "Invalid", "description": "Bad request"}]))

    def root_error_section(self):
        docs = yaml.safe_load((self.bruno / "opencollection.yml").read_text())["docs"]
        return next(sec["body"] for sec in dp.split_sections(docs) if sec["title"] == "Error Response Body")

    def test_migrated_collection_passes_brunocheck(self):
        mg.migrate(self.api, self.bruno)
        self.assertEqual(mg.roundtrip(self.api, self.bruno), [])
        self.assertEqual(self.errors(), set())

    def test_http_and_runtime_kept_byte_identical(self):
        before = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))
        mg.migrate(self.api, self.bruno)
        after = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))
        self.assertEqual(after["http"], before["http"])
        self.assertEqual(after["runtime"], before["runtime"])
        self.assertIn("X-Trace", after["http"])

    def test_missing_endpoint_is_created(self):
        report = mg.migrate(self.api, self.bruno)
        self.assertTrue((self.bruno / "account/get.yml").exists())
        self.assertIn("account/get.yml", report["created"])
        self.assertEqual(report["updated"].count("account/create.yml"), 1)

    def test_integer_becomes_number(self):
        mg.migrate(self.api, self.bruno)
        body = dp.parse_request(self.bruno / "account/create.yml")["docs"]["tables"]["body"]
        self.assertEqual({f["name"]: f["type"] for f in body}["count"], "Number")

    def test_nested_objects_flatten_and_covers_ac_dropped(self):
        mg.migrate(self.api, self.bruno)
        d = dp.parse_request(self.bruno / "account/create.yml")
        names = [f["name"] for f in d["docs"]["tables"]["body"]]
        self.assertIn("items[].code", names)
        self.assertIn("data.accountId", [f["name"] for f in d["docs"]["responses"][201]["fields"]])
        self.assertNotIn("AC-001", d["docs_raw"])
        self.assertNotIn(400, d["docs"]["responses"])

    def test_roundtrip_catches_dropped_row_and_keeps_source(self):
        mg.migrate(self.api, self.bruno)
        p = self.bruno / "account/create.yml"
        p.write_text(p.read_text().replace("| customerId |", "| renamed |"))
        self.assertTrue(mg.roundtrip(self.api, self.bruno))
        r = subprocess.run([sys.executable, MG, str(self.api), str(self.bruno), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(self.api.exists())

    def test_request_without_runtime_gets_status_test(self):
        http_before = self.replace_runtime(None)
        mg.migrate(self.api, self.bruno)
        after = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))
        self.assertEqual(after["http"], http_before)
        self.assertIn('test("status is 201"', after["runtime"])
        self.assertEqual(self.errors(), set())

    def test_runtime_without_scripts_keeps_its_lines(self):
        runtime = "runtime:\n  variables:\n    - name: trace\n      value: keep-me\n\n"
        self.replace_runtime(runtime)
        mg.migrate(self.api, self.bruno)
        after = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))
        self.assertTrue(after["runtime"].startswith(runtime.rstrip("\n")))
        self.assertIn('test("status is 201"', after["runtime"])
        self.assertEqual(self.errors(), set())

    def test_extra_endpoint_orphan_and_openapi_reported(self):
        orphan = self.bruno / "account/ping.yml"
        orphan.write_text('info:\n  name: Ping\n  type: http\n  seq: 30\n\nhttp:\n  method: GET\n'
                          '  url: "{{baseUrl}}/v1/ping"\n')
        report = mg.migrate(self.api, self.bruno)
        self.assertIn("health/get-health.yml", report["created"])
        self.assertIn("health/folder.yml", report["created"])
        self.assertEqual(report["orphans"], ["account/ping.yml"])
        self.assertTrue(any("openapi.yaml" in w for w in report["warnings"]))
        self.assertTrue(any("account/ping.yml" in w for w in report["warnings"]))
        self.assertIn("/v1/ping", orphan.read_text())

    def test_request_body_object_is_resolved(self):
        def move_item(data):
            data["request_body"]["objects"] = {"Item": data["responses"][0]["objects"].pop("Item")}
        self.edit_spec("account/create.yaml", move_item)
        mg.migrate(self.api, self.bruno)
        body = dp.parse_request(self.bruno / "account/create.yml")["docs"]["tables"]["body"]
        self.assertIn("items[].code", [f["name"] for f in body])
        self.assertEqual(mg.roundtrip(self.api, self.bruno), [])

    def test_unreferenced_object_fails_roundtrip(self):
        def add_orphan(data):
            data["request_body"]["objects"] = {"BranchEntry": [
                {"name": "branchCode", "description": "Branch", "type": "String", "mandatory": "M", "example": "001"}]}
        self.edit_spec("account/create.yaml", add_orphan)
        mg.migrate(self.api, self.bruno)
        problems = mg.roundtrip(self.api, self.bruno)
        self.assertEqual(len(problems), 1)
        self.assertIn("BranchEntry", problems[0])

    def test_root_error_body_is_trio_with_real_code(self):
        report = mg.migrate(self.api, self.bruno)
        rows = self.root_error_body()
        self.assertEqual([r["name"] for r in rows], ["responseCode", "errorCode", "errorMessage"])
        self.assertEqual(rows[1]["possible"], '`"LEG-1001"`')
        self.assertFalse([w for w in report["warnings"] if "Error Response Body" in w])

    def test_root_error_body_is_set_shared_by_two_endpoint_files(self):
        self.edit_spec("account/create.yaml", self.drop_common_lib)
        self.edit_spec("account/get.yaml", lambda d: d["responses"].append(self.old_envelope(404)))
        report = mg.migrate(self.api, self.bruno)
        self.assertEqual([r["name"] for r in self.root_error_body()], ["type", "message", "errors", "errors[].field"])
        self.assertTrue([w for w in report["warnings"] if "Error Response Body" in w and "2 endpoint files" in w])

    def test_root_error_body_not_documented(self):
        variants = {"no error body": lambda d: (self.drop_common_lib(d), d["responses"].pop(1)),
                    "body in one file only": self.drop_common_lib}
        for label, change in variants.items():
            with self.subTest(label):
                self.setUp()
                self.edit_spec("account/create.yaml", change)
                report = mg.migrate(self.api, self.bruno)
                self.assertEqual(self.root_error_section().strip(), "Not documented in the source spec.")
                self.assertEqual(self.root_error_body(), [])
                self.assertTrue([w for w in report["warnings"] if "Error Response Body" in w and "not documented" in w])
                self.assertFalse({"K4", "K11"} & self.errors())

    def test_scripts_without_tests_entry_get_status_test(self):
        before_request = ("runtime:\n  scripts:\n    - type: before-request\n      code: |-\n"
                          "        req.setHeader(\"X-A\", \"1\");\n  variables:\n    - name: trace\n"
                          "      value: keep-me\n")
        for runtime in (before_request, "runtime:\n  scripts: []\n"):
            with self.subTest(runtime=runtime):
                self.setUp()
                self.replace_runtime(runtime)
                mg.migrate(self.api, self.bruno)
                req = dp.parse_request(self.bruno / "account/create.yml")
                scripts = req["runtime"]["scripts"]
                self.assertEqual(scripts[-1]["type"], "tests")
                self.assertIn('test("status is 201"', scripts[-1]["code"])
                if runtime is before_request:
                    self.assertEqual(scripts[0]["type"], "before-request")
                    self.assertEqual(req["runtime"]["variables"], [{"name": "trace", "value": "keep-me"}])
                    after = dict(mg.split_top_level((self.bruno / "account/create.yml").read_text()))["runtime"]
                    self.assertTrue(after.startswith(before_request.split("  variables:")[0]))
                self.assertEqual(self.errors(), set())

    def test_possible_value_keeps_thai(self):
        rows = mg.flatten_fields([{"name": "accountNameTH", "type": "String", "mandatory": "M",
                                   "example": "บัญชีออมทรัพย์"}], {})
        self.assertEqual(rows[0]["possible"], '`"บัญชีออมทรัพย์"`')

    def test_array_example_prefixes_unprefixed_rows(self):
        variants = {"unprefixed": lambda d: None,
                    "already prefixed": lambda d: [f.update(name="[]." + f["name"]) for f in d["responses"][0]["fields"]]}
        for label, rename in variants.items():
            with self.subTest(label):
                self.setUp()
                self.edit_spec("account/get.yaml", lambda d: (rename(d), d["responses"][0].update(
                    example='[{"status": "Success", "data": {"accountId": "uuid-v4"}}]')))
                self.edit_spec("account/create.yaml", lambda d: d["request_body"].update(
                    example='[{"customerId": "uuid-v4", "count": 1, "items": [{"code": "X1"}]}]'))
                p = self.bruno / "account/create.yml"
                p.write_text(p.read_text().replace('data: |-\n      {\n', 'data: |-\n      [{\n')
                             .replace('[{"code": "X1"}]\n      }\n', '[{"code": "X1"}]\n      }]\n'))
                mg.migrate(self.api, self.bruno)
                get = dp.parse_request(self.bruno / "account/get.yml")["docs"]
                self.assertEqual([f["name"] for f in get["responses"][200]["fields"]],
                                 ["[].status", "[].data", "[].data.accountId"])
                create = dp.parse_request(self.bruno / "account/create.yml")["docs"]
                self.assertEqual([f["name"] for f in create["tables"]["body"]],
                                 ["[].customerId", "[].count", "[].items", "[].items[].code"])
                self.assertEqual(create["responses"][201]["fields"][0]["name"], "status")
                self.assertEqual(mg.roundtrip(self.api, self.bruno), [])
                self.assertEqual(self.errors(), set())

    def test_permission_scopes_warn_and_render_nothing(self):
        self.edit_spec("account/create.yaml", lambda d: d.update(permission_scopes=["core:read", "core.balances:read"]))
        report = mg.migrate(self.api, self.bruno)
        self.assertIn("account/create.yaml: permission_scopes not rendered: core:read, core.balances:read",
                      report["warnings"])
        self.assertNotIn("core:read", (self.bruno / "account/create.yml").read_text())

    def test_cli_migrates_and_exits_zero(self):
        r = subprocess.run([sys.executable, MG, str(self.api), str(self.bruno)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_headers_render_and_roundtrip(self):
        self.edit_spec("account/create.yaml", lambda d: d.update(headers=[
            {"name": "X-User-Id", "description": "Acting officer", "type": "String", "mandatory": "M",
             "example": "officer.somchai", "remark": "Propagated by the BFF."}]))
        mg.migrate(self.api, self.bruno)
        docs = dp.parse_request(self.bruno / "account/create.yml")["docs"]
        self.assertEqual(docs["tables"]["headers"], [{"name": "X-User-Id", "type": "String", "mandatory": "Yes",
                                                      "description": "Acting officer Propagated by the BFF.",
                                                      "possible": '`"officer.somchai"`'}])
        self.assertIn("Headers", docs["headings"])
        self.assertEqual(mg.roundtrip(self.api, self.bruno), [])
        self.assertEqual(self.errors(), set())
        p = self.bruno / "account/create.yml"
        p.write_text(p.read_text().replace("| X-User-Id |", "| X-Other |"))
        self.assertTrue(any("headers:" in m for m in mg.roundtrip(self.api, self.bruno)))

    def test_keys_outside_the_allowlist_fail_roundtrip(self):
        def legacy_shapes(d):
            d.update(response_body=[{"name": "status", "type": "String"}], permission_scopes=["core:read"])
            d["request_body"].update(content_type="application/json", is_array=False, schema="x")
            d["responses"][0]["headers"] = [{"name": "Content-Type"}]
        self.edit_spec("account/create.yaml", legacy_shapes)
        self.edit_spec("account/get.yaml", lambda d: d.update(parameters={"query": [{"name": "page"}]}))
        mg.migrate(self.api, self.bruno)
        self.assertEqual(sorted(mg.roundtrip(self.api, self.bruno)), [
            "account/create.yaml: key request_body.schema not migrated",
            "account/create.yaml: key response_body not migrated",
            "account/create.yaml: key responses[].headers not migrated",
            "account/get.yaml: key parameters not migrated"])
        r = subprocess.run([sys.executable, MG, str(self.api), str(self.bruno), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISMATCH account/get.yaml: key parameters not migrated", r.stdout)

    def test_unreadable_or_non_endpoint_files_fail_roundtrip(self):
        (self.api / "account/close.yaml").write_text("a: b: c\n")
        (self.api / "account/patch.yaml").write_text("foo: bar\n")
        mg.migrate(self.api, self.bruno)
        self.assertEqual(sorted(mg.roundtrip(self.api, self.bruno)), [
            "account/close.yaml: unreadable, or not an endpoint (no method/path); not migrated",
            "account/patch.yaml: unreadable, or not an endpoint (no method/path); not migrated"])
        r = subprocess.run([sys.executable, MG, str(self.api), str(self.bruno)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        (self.api / "account/close.yaml").unlink()
        (self.api / "account/patch.yaml").unlink()
        (self.api / "_meta.yaml").write_text("- a\n- b\n")
        r = subprocess.run([sys.executable, MG, str(self.api), str(self.bruno)], capture_output=True, text=True)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("MISMATCH _meta.yaml: unreadable, or not a mapping; not migrated", r.stdout)

    def test_cli_without_meta_or_endpoints_exits_2_and_writes_nothing(self):
        before = sorted(p.relative_to(self.tmp) for p in self.tmp.rglob("*"))
        r = subprocess.run([sys.executable, MG, str(self.bruno), str(self.api)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("_meta.yaml not found", r.stderr)
        self.assertIn("usage: migrate.py", r.stderr)
        self.assertEqual(sorted(p.relative_to(self.tmp) for p in self.tmp.rglob("*")), before)
        empty = self.tmp / "empty-api"
        empty.mkdir()
        (empty / "_meta.yaml").write_text("title: Nothing\n")
        for extra in ([], ["--check"]):
            r = subprocess.run([sys.executable, MG, str(empty), str(self.tmp / "out"), *extra],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("no endpoint", r.stderr)
            self.assertFalse((self.tmp / "out").exists())


if __name__ == "__main__":
    unittest.main()
