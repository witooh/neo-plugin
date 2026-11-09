import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ASSETS = Path(__file__).resolve().parent
GOOD = ASSETS / "testdata" / "good"
BC = ASSETS / "brunocheck.py"
bc = load_module("brunocheck", BC)

INFO = "info:\n  name: Create Account\n  type: http\n  seq: 10\n\n"


def mutated(*edits):
    tmp = Path(tempfile.mkdtemp()) / "col"
    shutil.copytree(GOOD, tmp)
    for rel, old, new in edits:
        p = tmp / rel
        text = p.read_text(encoding="utf-8")
        assert old in text, f"{old!r} not in {rel}"
        p.write_text(text.replace(old, new), encoding="utf-8")
    return tmp


def rules(findings, level="ERROR"):
    return {f[1] for f in findings if f[0] == level}


class BrunoCheckTests(unittest.TestCase):
    def test_good_fixture_has_no_errors(self):
        self.assertEqual(rules(bc.check(GOOD)), set())

    def test_norm_path(self):
        self.assertEqual(bc.norm_path("{{baseUrl}}/v1/a/:id/b/{{x}}/"), "/v1/a/{}/b/{}")
        self.assertEqual(bc.norm_path("/v1/a/{id}"), "/v1/a/{}")

    def test_k1_missing_settings(self):
        root = mutated(("account/create-account.yml", "settings:\n  encodeUrl: true\n\n", ""))
        self.assertIn("K1", rules(bc.check(root)))

    def test_k1_info_after_docs(self):
        root = mutated(("account/create-account.yml", INFO, ""))
        p = root / "account/create-account.yml"
        p.write_text(p.read_text() + "\n" + INFO)
        self.assertIn("K1", rules(bc.check(root)))

    def test_k1_missing_opencollection_does_not_crash(self):
        root = mutated()
        (root / "opencollection.yml").unlink()
        found = bc.check(root)
        self.assertTrue(any(f[:3] == ("ERROR", "K1", "opencollection.yml") for f in found))

    def test_k1_undecodable_file_does_not_crash(self):
        root = mutated()
        (root / "account/get-account.yml").write_bytes(b"\xff\xfe\x00bad")
        found = bc.check(root)
        self.assertTrue(any(f[:3] == ("ERROR", "K1", "account/get-account.yml") for f in found))

    def test_k2_method_mismatch(self):
        root = mutated(("account/create-account.yml", "`POST /v1/accounts`", "`PUT /v1/accounts`"))
        self.assertIn("K2", rules(bc.check(root)))

    def test_k2_missing_heading(self):
        root = mutated(("account/get-account.yml", "### Auth", "### Authz"))
        self.assertIn("K2", rules(bc.check(root)))

    def test_k3_param_missing_from_http_params(self):
        root = mutated(("account/get-account.yml", "type: path", "type: query"))
        self.assertIn("K3", rules(bc.check(root)))

    def test_k3_var_style_path_param_is_accepted(self):
        root = mutated(("account/get-account.yml", '/v1/accounts/:accountId"', '/v1/accounts/{{accountId}}"'))
        found = rules(bc.check(root))
        self.assertNotIn("K3", found)
        self.assertNotIn("K2", found)

    def test_k7_no_status_test(self):
        root = mutated(("account/create-account.yml", "res.status", "res.body"))
        self.assertIn("K7", rules(bc.check(root)))

    def test_k8_undefined_var(self):
        root = mutated(("account/create-account.yml", "{{customerId}}", "{{nope}}"))
        self.assertIn("K8", rules(bc.check(root)))

    def test_k8_secret_with_value(self):
        env = "environments/local.yml"
        root = mutated((env, "00000000-0000-0000-0000-000000000002\n",
                        '00000000-0000-0000-0000-000000000002\n  - name: auth_token\n    value: "abc"\n'),
                       ("account/create-account.yml", "  auth: inherit\n",
                        '  headers:\n    - name: X-Token\n      value: "{{auth_token}}"\n  auth: inherit\n'))
        self.assertIn("K8", rules(bc.check(root)))

    def test_k8_pii_with_value_is_note(self):
        root = mutated(("environments/local.yml", "value: http://localhost:8080\n",
                        'value: http://localhost:8080\n  - name: citizenId\n    value: "1234"\n'))
        found = bc.check(root)
        self.assertIn("K8", rules(found, "NOTE"))
        self.assertNotIn("K8", rules(found))

    def test_k8_credential_words_match_whole_segments(self):
        root = mutated(("environments/local.yml", "value: http://localhost:8080\n",
                        'value: http://localhost:8080\n  - name: rootPath\n    value: "/x"\n'
                        '  - name: apiKey\n    value: "k"\n'))
        errs = [f for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K8"]
        self.assertEqual(len(errs), 1)
        self.assertIn("apiKey", errs[0][3])

    def test_k1_docs_not_a_string(self):
        root = mutated()
        p = root / "account/get-account.yml"
        text = p.read_text()
        p.write_text(text[:text.index("docs:")] + "docs:\n  a: 1\n")
        found = bc.check(root)
        self.assertTrue(any(f[:3] == ("ERROR", "K1", "account/get-account.yml") for f in found))

    def test_query_var_in_url_gives_no_k2_k3(self):
        root = mutated(("account/create-account.yml", '/v1/accounts"', '/v1/accounts?x={{customerId}}"'))
        found = rules(bc.check(root))
        self.assertNotIn("K2", found)
        self.assertNotIn("K3", found)

    def test_k9_missing_folder_yml(self):
        root = mutated()
        (root / "account/folder.yml").unlink()
        self.assertIn("K9", rules(bc.check(root)))

    def test_k9_duplicate_seq(self):
        root = mutated(("account/get-account.yml", "seq: 20", "seq: 10"))
        self.assertIn("K9", rules(bc.check(root)))

    def test_cli_exit_codes(self):
        ok = subprocess.run([sys.executable, BC, str(GOOD)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertTrue(ok.stdout.strip().endswith("PASS: 0 error(s)"))
        root = mutated(("account/create-account.yml", "res.status", "res.body"))
        bad = subprocess.run([sys.executable, BC, str(root)], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("FAIL: ", bad.stdout.strip().splitlines()[-1])

CA = "account/create-account.yml"


class ContentRuleTests(unittest.TestCase):
    def test_k4_bad_mandatory(self):
        root = mutated((CA, "| customerId | String | Yes |", "| customerId | String | M |"))
        self.assertIn("K4", rules(bc.check(root)))

    def test_k4_orphan_child(self):
        root = mutated((CA, "| data | Object | Yes | Payload | see below |\n", ""))
        self.assertIn("K4", rules(bc.check(root)))

    def test_k5_example_key_not_in_table(self):
        root = mutated((CA, '"accountType": "SA", "items"', '"accountType": "SA", "ghost": 1, "items"'))
        self.assertIn("K5", rules(bc.check(root)))

    def test_k5_body_data_key_set_differs(self):
        root = mutated((CA, '"accountType": "SA",\n', ""))
        self.assertIn("K5", rules(bc.check(root)))

    def test_k5_unquoted_var_in_body_data(self):
        root = mutated((CA, '"accountType": "SA",\n', '"accountType": {{accountType}},\n'),
                       ("environments/local.yml", "variables:\n", "variables:\n  - name: accountType\n    value: SA\n"))
        self.assertNotIn("K5", rules(bc.check(root)))

    def test_k5_required_child_of_absent_optional_parent(self):
        root = mutated((CA, ', "items": [{"code": "X1"}]}', "}"),
                       (CA, ',\n        "items": [{"code": "X1"}]', ""))
        self.assertNotIn("K5", rules(bc.check(root)))

    def test_k5_response_example_missing_required_field(self):
        root = mutated((CA, '{"status": "Success", "data": {"accountId": "uuid-v4"}}', '{"status": "Success"}'))
        self.assertIn("K5", rules(bc.check(root)))

    def test_k6_wrong_status_for_response_code(self):
        root = mutated((CA, "| 400 | 001 | FIX-1002 |", "| 422 | 001 | FIX-1002 |"))
        self.assertIn("K6", rules(bc.check(root)))

    def test_k6_missing_response_code(self):
        root = mutated((CA, "| 400 | 001 | FIX-1002 |", "| 400 |  | FIX-1002 |"))
        self.assertIn("K6", rules(bc.check(root)))

    def test_k6_common_error_header(self):
        root = mutated(("opencollection.yml", "| Status | Response Code | Error Code |", "| Status | Code | Error Code |"))
        self.assertIn("K6", rules(bc.check(root)))

    def test_k10_internal_path_and_ticket(self):
        root = mutated((CA, "1. Validate, then create.", "1. See internal/handler/a.go:12 (AC-001)."))
        self.assertIn("K10", rules(bc.check(root)))

    def test_k10_unknown_key_is_note(self):
        root = mutated((CA, "Open an account.", "Open an account (GI-3467)."))
        self.assertIn("K10", rules(bc.check(root), level="NOTE"))
        self.assertNotIn("K10", rules(bc.check(root)))

    def test_k11_missing_error_body(self):
        root = mutated(("opencollection.yml", "## Error Response Body", "## Something Else"))
        self.assertIn("K11", rules(bc.check(root)))

    def test_k8_api_key_and_acronym_names(self):
        env = "environments/local.yml"
        root = mutated((env, "value: http://localhost:8080\n",
                        'value: http://localhost:8080\n  - name: STRIPE_API_KEY\n    value: "k"\n'
                        '  - name: APIToken\n    value: "t"\n  - name: apikey\n    value: "a"\n'
                        '  - name: APIKEY\n    value: "b"\n  - name: rootPath\n    value: "/x"\n'))
        errs = [f for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K8"]
        self.assertEqual(len(errs), 4, errs)
        self.assertTrue(any("STRIPE_API_KEY" in f[3] for f in errs))
        self.assertTrue(any("APIToken" in f[3] for f in errs))
        self.assertTrue(any("`apikey`" in f[3] for f in errs))
        self.assertTrue(any("`APIKEY`" in f[3] for f in errs))

    def test_k8_request_runtime_variables(self):
        runtime_vars = ('runtime:\n  variables:\n    - name: reqCustomer\n      value: "{{customerId}}"\n'
                        '    - name: req_token\n      value: "abc"\n  scripts:')
        root = mutated((CA, '"{{customerId}}"', '"{{reqCustomer}}"'), (CA, "runtime:\n  scripts:", runtime_vars),
                       (CA, "  auth: inherit\n", '  headers:\n    - name: X-Token\n      value: "{{req_token}}"\n'
                                                '  auth: inherit\n'))
        errs = [f for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K8"]
        self.assertEqual([f[2:] for f in errs], [(CA, "secret-like variable `req_token` has a committed value")])
        root = mutated((CA, '"{{customerId}}"', '"{{reqVar}}"'),
                       (CA, "runtime:\n  scripts:", 'runtime:\n  variables:\n    - name: other\n      value: ""\n  scripts:'))
        self.assertIn("K8", rules(bc.check(root)))

    def test_k4_top_level_array_body(self):
        rows = [("| customerId |", "| [].customerId |"), ("| accountType |", "| [].accountType |"),
                ("| items |", "| [].items |"), ("| items[].code |", "| [].items[].code |")]
        example = '{"customerId": "uuid-v4", "accountType": "SA", "items": [{"code": "X1"}]}'
        root = mutated(*[(CA, old, new) for old, new in rows], (CA, example, f"[{example}]"),
                       (CA, "data: |-\n      {\n", "data: |-\n      [{\n"),
                       (CA, '[{"code": "X1"}]\n      }\n', '[{"code": "X1"}]\n      }]\n'))
        self.assertEqual(rules(bc.check(root)), set())
        orphan = dp_rows(["[].b.c"])
        self.assertEqual(bc._check_field_table("Body (JSON)", orphan), ["Body (JSON): `[].b.c` has no parent row `[].b`"])

    def test_k2_duplicate_status_section(self):
        root = mutated((CA, "### Error Responses", "### HTTP Status: 201\n\n  Created again.\n\n  ### Error Responses"))
        self.assertEqual(bc.dp.parse_request(root / CA)["docs"]["duplicate_statuses"], [201])
        errs = [f for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K2"]
        self.assertEqual([f[2:] for f in errs], [(CA, "duplicate `### HTTP Status: 201`")])

    def test_k10_internal_segment_of_http_path_is_not_a_leak(self):
        root = mutated((CA, '/v1/accounts"', '/v1/internal/x"'), (CA, "`POST /v1/accounts`", "`POST /v1/internal/x`"))
        self.assertNotIn("K10", rules(bc.check(root)))
        root = mutated((CA, "1. Validate, then create.", "1. See `internal/adapters/foo.go`."))
        self.assertIn("K10", rules(bc.check(root)))

    def test_k5_body_data_without_body_table_or_example(self):
        text = (GOOD / CA).read_text(encoding="utf-8")
        both = text[text.index("  ### Body (JSON)"):text.index("  ## Response")]
        example = text[text.index("  ### Example"):text.index("  ## Response")]
        for label, block in (("no table, no Example", both), ("no Example", example)):
            with self.subTest(label):
                errs = [f for f in bc.check(mutated((CA, block, ""))) if f[0] == "ERROR" and f[1] == "K5"]
                self.assertIn((CA, "http.body.data is sent but docs has no `### Body (JSON)` table "
                                   "followed by an `### Example`"), [f[2:] for f in errs])

    def test_k2_no_success_status_section(self):
        for label, new in (("no status section", ""), ("error status only", "  ### HTTP Status: 404\n\n")):
            with self.subTest(label):
                root = mutated(("account/get-account.yml", "  ### HTTP Status: 200\n\n", new))
                errs = [f for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K2"]
                self.assertEqual([f[2:] for f in errs],
                                 [("account/get-account.yml", "no success `### HTTP Status: N` section (N < 400)")])

    def test_k8_process_env_value_is_not_committed(self):
        root = mutated((CA, "  auth: inherit\n",
                        '  headers:\n    - name: Authorization\n      value: "Bearer {{auth_token}}"\n  auth: inherit\n'),
                       (CA, "runtime:\n  scripts:",
                        'runtime:\n  variables:\n    - name: auth_token\n      value: "{{process.env.AUTH_TOKEN}}"\n'
                        '  scripts:'),
                       ("environments/local.yml", "value: http://localhost:8080\n",
                        'value: http://localhost:8080\n  - name: api_token\n    value: "{{process.env.API_TOKEN}}"\n'))
        self.assertNotIn("K8", rules(bc.check(root)))

    def test_k10_scans_folder_docs(self):
        root = mutated(("account/folder.yml", "  auth: none\n",
                        "  auth: none\n\ndocs: |-\n  Accounts. See `internal/handler/account.go`.\n"))
        found = bc.check(root)
        self.assertIn(("ERROR", "K10", "account/folder.yml"), [f[:3] for f in found])

    def test_k11_placeholder_error_body_is_note(self):
        text = (GOOD / "opencollection.yml").read_text(encoding="utf-8")
        table = text[text.index("  | Field Name"):text.index("  ## Common Error Responses")]
        root = mutated(("opencollection.yml", table, "  Not documented in the source spec.\n\n"))
        found = bc.check(root)
        self.assertIn("K11", rules(found, "NOTE"))
        self.assertNotIn("K11", rules(found))
        r = subprocess.run([sys.executable, BC, str(root)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("NOTE K11 opencollection.yml: ", r.stdout)
        self.assertIn("— needs fresh-eyes", [l for l in r.stdout.splitlines() if "NOTE K11" in l][0])

    def test_k5_empty_array_has_no_element_to_check(self):
        root = mutated((CA, '"items": [{"code": "X1"}]\n', '"items": []\n'),
                       (CA, '"items": [{"code": "X1"}]}', '"items": []}'))
        self.assertNotIn("K5", rules(bc.check(root)))
        root = mutated((CA, "| items[].code | String | Yes | Item code | `\"X1\"` |\n",
                        "| items[].code | String | Yes | Item code | `\"X1\"` |\n"
                        "  | items[].note | String | No | Note | `\"n\"` |\n"),
                       (CA, '"items": [{"code": "X1"}]\n', '"items": [{"note": "n"}]\n'),
                       (CA, '"items": [{"code": "X1"}]}', '"items": [{"note": "n"}]}'))
        errs = [f[3] for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K5"]
        self.assertEqual(errs, ["request Example: required field `items[].code` is missing from the Example"])

    def test_k7_status_text_alone_is_not_a_status_test(self):
        root = mutated((CA, "expect(res.status).to.equal(201)", 'expect(res.statusText).to.equal("Created")'))
        self.assertIn("K7", rules(bc.check(root)))

    def test_k8_bruno_dynamic_variables(self):
        headers = '  headers:\n    - name: X-Request-Id\n      value: "{{$guid}}"\n' \
                  '    - name: X-At\n      value: "{{$timestamp}}"\n'
        root = mutated((CA, "  auth: inherit\n", headers + "  auth: inherit\n"))
        self.assertNotIn("K8", rules(bc.check(root)))
        root = mutated((CA, "  auth: inherit\n", headers.replace("$guid", "$uuid") + "  auth: inherit\n"))
        errs = [f[3] for f in bc.check(root) if f[0] == "ERROR" and f[1] == "K8"]
        self.assertEqual(errs, ["`{{$uuid}}` is not defined in environments/"])


def dp_rows(names):
    return [{"name": n, "type": "String", "mandatory": "Yes", "description": "", "possible": ""} for n in names]


if __name__ == "__main__":
    unittest.main()
