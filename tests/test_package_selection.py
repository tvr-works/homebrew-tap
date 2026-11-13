"""Check selection failures separately from native Homebrew integration in CI."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackageSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        brew = self.root / "brew"
        brew.write_text("""#!/usr/bin/env python3
import os, pathlib, sys
if sys.argv[1] == 'info':
    print(pathlib.Path(os.environ['PACKAGE_JSON']).read_text())
elif sys.argv[1] == 'ruby':
    print(os.environ['VERSION_COMPARISON'])
else:
    raise SystemExit('unexpected command: ' + repr(sys.argv))
""")
        brew.chmod(0o755)

    def run_selection(self, kind, change=None, exact=True, comparison="-1"):
        package = {"tap": "tvr-works/tap", "version": "1.2.3",
                   "url": "https://example.invalid/package.zip", "sha256": "a" * 64}
        if change:
            package.update(change)
        if kind == "formula":
            package = {"tap": package["tap"], "versions": {"stable": package["version"]},
                       "urls": {"stable": {"url": package["url"], "checksum": package["sha256"]}}}
        fixture = self.root / "package.json"
        fixture.write_text(json.dumps({"casks" if kind == "cask" else "formulae": [package]}))
        output = self.root / "state"
        output.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f"{self.root}:{os.environ['PATH']}",
                   PACKAGE_JSON=str(fixture), VERSION_COMPARISON=comparison)
        result = subprocess.run([str(ROOT / ".github/scripts/check-package-state.sh"),
                                 *(["--exact"] if exact else []), kind, "tvr-works/tap/package",
                                 "1.2.3", "https://example.invalid/package.zip", "a" * 64, str(output)],
                                env=env, text=True, capture_output=True)
        return result, output

    def test_exact_selection(self):
        for kind in ["cask", "formula"]:
            with self.subTest(kind=kind):
                result, output = self.run_selection(kind)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output.read_text(), "current=true\n")

    def test_rejects_wrong_tap_version_url_or_checksum(self):
        for kind in ["cask", "formula"]:
            for change in [{"tap": "homebrew/core"}, {"tap": None}, {"version": "1.2.2"},
                           {"version": "1.2.4"}, {"url": "https://example.invalid/other.zip"},
                           {"sha256": "b" * 64}]:
                with self.subTest(kind=kind, change=change):
                    result, output = self.run_selection(kind, change)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())

    def test_pre_bump_check_still_allows_an_older_version(self):
        for kind in ["cask", "formula"]:
            with self.subTest(kind=kind):
                result, output = self.run_selection(kind, {"version": "1.2.2"}, exact=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output.read_text(), "current=false\n")

    def test_pre_bump_check_still_rejects_regression(self):
        for kind in ["cask", "formula"]:
            with self.subTest(kind=kind):
                result, output = self.run_selection(kind, {"version": "1.2.4"}, exact=False, comparison="1")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
