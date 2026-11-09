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

    def test_go_route_without_request_is_drift(self):
        go = go_copy("router.go", "}\n", '\tr.DELETE("/v1/accounts/:accountId", h.Delete)\n}\n')
        r = run(DC, GOOD, "--src", go)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("DELETE", r.stdout)

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
        for script in ("driftcheck.py", "brunocheck.py", "migrate.py"):
            r = subprocess.run([sys.executable, str(ASSETS / script), str(GOOD)],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 2, (script, r.stderr))
            self.assertIn("needs PyYAML", r.stderr, script)


if __name__ == "__main__":
    unittest.main()
