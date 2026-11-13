import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
GOOD = ASSETS / "testdata" / "good"
GO = ASSETS / "testdata" / "go"
DC = ASSETS / "driftcheck.py"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def go_copy(rel=None, old=None, new=None, append=None):
    tmp = Path(tempfile.mkdtemp()) / "go"
    shutil.copytree(GO, tmp)
    if rel:
        p = tmp / rel
        text = p.read_text(encoding="utf-8")
        p.write_text(text.replace(old, new, 1) if old else text + append, encoding="utf-8")
    return tmp


REGISTER = ('package fix\n\nfunc Register(r Router, h *Handler) {\n%s}\n\n'
            'func registerAccounts(r Router, h *Handler) {\n\tr.POST("", h.Create)\n\tr.GET("/:accountId", h.Get)\n}\n')


def go_router(text):
    go = go_copy()
    (go / "router.go").write_text(text, encoding="utf-8")
    return go


class DriftCheckTests(unittest.TestCase):
    def test_good_collection_matches_go(self):
        r = run(DC, GOOD, "--src", GO)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_undocumented_go_field_is_drift(self):
        go = go_copy("dto.go", "Items       []Item",
                     'Nickname string `json:"nickname"`\n\tItems       []Item')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("nickname", r.stdout)

    def test_top_level_array_body_is_compared(self):
        col = Path(tempfile.mkdtemp()) / "col"
        shutil.copytree(GOOD, col)
        p = col / "account/create-account.yml"
        text = p.read_text(encoding="utf-8")
        for name in ("customerId", "accountType", "items", "items[].code"):
            text = text.replace(f"| {name} |", f"| [].{name} |")
        self.assertIn("| [].items[].code |", text)
        p.write_text(text, encoding="utf-8")
        go = go_copy("dto.go", "Items       []Item",
                     'Nickname string `json:"nickname"`\n\tItems       []Item')
        r = run(DC, col, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("nickname", r.stdout)

    def test_nested_module_is_not_scanned(self):
        go = go_copy("dto.go", "Items       []Item",
                     'Nickname string `json:"nickname"`\n\tItems       []Item')
        wt = go / ".claude" / "worktrees" / "wt"
        wt.mkdir(parents=True)
        shutil.copy(GO / "go.mod", wt / "go.mod")
        shutil.copy(GO / "dto.go", wt / "dto.go")
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("nickname", r.stdout)

    def test_inline_closure_route_is_counted(self):
        go = go_copy("router.go", "}\n",
                     '\tr.GET("/health", func(c *gin.Context) {\n\t\tc.JSON(200, nil)\n\t})\n}\n')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("GET /health", r.stdout)

    def test_non_route_closure_is_not_a_route(self):
        go = go_copy("router.go", "}\n",
                     '\tx := cache.Get("key", func(k string) string { return k })\n\t_ = x\n}\n')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_request_field_without_required_is_optional(self):
        go = go_copy("dto.go", '`json:"accountType" binding:"required"`', '`json:"accountType"`')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("`accountType`: Go tags → O but spec says M", r.stdout)

    def test_omitempty_response_field_is_optional(self):
        go = go_copy("dto.go", '`json:"accountId"`', '`json:"accountId,omitempty"`')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("`accountId`: Go tags → O but spec says M", r.stdout)

    def test_duplicate_struct_name_degrades_a_lookalike_match_to_note(self):
        go = go_copy("dto.go", append='\ntype PatchAccountRequest struct {\n'
                                      '\tAccountID *string `json:"accountId,omitempty"`\n}\n')
        (go / "entity").mkdir()
        (go / "entity" / "account.go").write_text(
            'package entity\n\ntype AccountResponse struct {\n'
            '\tAccountID string `json:"accountId"`\n\tSecret    string `json:"secret"`\n}\n',
            encoding="utf-8")
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("AccountResponse is defined more than once", r.stdout)

    def test_tighter_match_is_still_compared_beside_a_duplicate_name(self):
        go = go_copy("dto.go", '`json:"accountId"`', '`json:"accountId,omitempty"`')
        for pkg in ("entity", "store"):
            (go / pkg).mkdir()
            (go / pkg / "account.go").write_text(
                f'package {pkg}\n\ntype Account struct {{\n\tAccountID string `json:"accountId"`\n'
                f'\t{pkg.title()} string `json:"{pkg}"`\n}}\n', encoding="utf-8")
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("`accountId`: Go tags → O but spec says M", r.stdout)

    def test_go_route_without_request_is_drift(self):
        go = go_copy("router.go", "}\n", '\tr.DELETE("/v1/accounts/:accountId", h.Delete)\n}\n')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("DELETE", r.stdout)

    def test_group_prefix_is_resolved(self):
        cases = (("inline group", '\tregisterAccounts(r.Group("/v1/accounts"), h)\n'),
                 ("group variable", '\taccounts := r.Group("/v1/accounts")\n\tregisterAccounts(accounts, h)\n'),
                 ("nested groups", '\tapi := r.Group("/v1")\n\tregisterAccounts(api.Group("/accounts"), h)\n'))
        for label, body in cases:
            with self.subTest(label):
                r = run(DC, GOOD, "--src", go_router(REGISTER % body))
                self.assertEqual(r.returncode, 0, r.stdout)
        with self.subTest("same function"):
            r = run(DC, GOOD, "--src", go_router(
                'package fix\n\nfunc Register(r Router, h *Handler) {\n\tg := r.Group("/v1/accounts")\n'
                '\tg.POST("", h.Create)\n\tg.GET("/:accountId", h.Get)\n}\n'))
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_group_prefix_is_part_of_the_route(self):
        r = run(DC, GOOD, "--src", go_router(REGISTER % '\tregisterAccounts(r.Group("/v2/accounts"), h)\n'))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Go route POST /v2/accounts has no request", r.stdout)

    def test_group_prefix_skips_a_function_name_defined_twice(self):
        go = go_router(REGISTER % '\tregisterAccounts(r.Group("/v1/accounts"), h)\n')
        (go / "other").mkdir()
        (go / "other" / "other.go").write_text("package other\n\nfunc registerAccounts(r Router) {}\n", encoding="utf-8")
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Go route POST / has no request", r.stdout)

    def test_missing_input_exits_2(self):
        empty = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty)
        r = run(DC, empty / "no-bruno", "--src", GO)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("not found: author the collection with the bruno skill first", r.stdout)
        r = run(DC, GOOD, "--src", empty)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("no Go source under --src", r.stdout)


class MissingPyYamlTests(unittest.TestCase):
    def test_all_clis_exit_2_without_pyyaml(self):
        stub = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, stub)
        (stub / "yaml.py").write_text(
            'raise ModuleNotFoundError("No module named \'yaml\'", name="yaml")\n')
        env = {**os.environ, "PYTHONPATH": str(stub)}
        for script in ("driftcheck.py", "brunocheck.py"):
            r = subprocess.run([sys.executable, str(ASSETS / script), str(GOOD)],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 2, (script, r.stderr))
            self.assertIn("needs PyYAML", r.stderr, script)


if __name__ == "__main__":
    unittest.main()
