"""Exercise release verification with real archives and a local GitHub transport."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text('''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
root = pathlib.Path(os.environ["FIXTURE"])
args = sys.argv[1:]
if args[0] == "api":
    expected = "repos/tvr-works/key/releases/tags/" + os.environ["VERSION"]
    assert args[-1] == expected, args
    print((root / "release.json").read_text())
elif args[:2] == ["release", "download"]:
    assert args[args.index("--repo") + 1] == "tvr-works/key"
    destination = pathlib.Path(args[args.index("--dir") + 1])
    for index, value in enumerate(args):
        if value == "--pattern":
            shutil.copyfile(root / args[index + 1], destination / args[index + 1])
else:
    raise SystemExit("unexpected GitHub command: " + repr(args))
''')
        gh.chmod(0o755)

    def fixture(self, channel=None):
        self.version = "v1.2.3" + (f"-{channel}.1" if channel else "")
        self.asset = f"Key-{'Preview-' if channel else ''}{self.version}.zip"
        with zipfile.ZipFile(self.root / self.asset, "w") as archive:
            archive.writestr("Key.app/Contents/fixture", "synthetic release")
        self.digest = hashlib.sha256((self.root / self.asset).read_bytes()).hexdigest()
        (self.root / "checksums.txt").write_text(f"{self.digest}  {self.asset}\n")
        self.release = {
            "tag_name": self.version, "draft": False,
            "published_at": "2026-10-28T00:00:00Z", "prerelease": bool(channel),
            "assets": [self.metadata(name) for name in ["checksums.txt", self.asset]],
        }

    def metadata(self, name):
        return {
            "name": name, "state": "uploaded",
            "browser_download_url": f"https://github.com/tvr-works/key/releases/download/{self.version}/{name}",
            "digest": "sha256:" + hashlib.sha256((self.root / name).read_bytes()).hexdigest(),
        }

    def run_verification(self, package="key"):
        (self.root / "release.json").write_text(json.dumps(self.release))
        output = self.root / "outputs"
        output.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                   FIXTURE=str(self.root), VERSION=self.version, RUNNER_TEMP=str(self.root))
        result = subprocess.run([str(ROOT / ".github/scripts/prepare-package-update.sh"),
                                 package, self.version, str(output)], env=env,
                                text=True, capture_output=True)
        return result, output

    def test_channels(self):
        for channel in [None, "alpha", "beta", "rc"]:
            with self.subTest(channel=channel):
                self.fixture(channel)
                result, output = self.run_verification()
                self.assertEqual(result.returncode, 0, result.stderr)
                values = dict(line.split("=", 1) for line in output.read_text().splitlines())
                token = "key" + (f"@{channel}" if channel else "")
                self.assertEqual(values["brew_ref"], f"tvr-works/tap/{token}")
                self.assertEqual(values["tap_path"], f"Casks/{token}.rb")
                self.assertEqual(values["sha256"], self.digest)
                self.assertEqual(values["download_url"], self.release["assets"][1]["browser_download_url"])

    def test_rejects_other_packages(self):
        self.fixture()
        for package in ["frame", "xkcdpass"]:
            result, output = self.run_verification(package)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported package", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_bad_release_evidence(self):
        for failure in ["missing_manifest", "wrong_owner", "digest", "checksum", "draft"]:
            with self.subTest(failure=failure):
                self.fixture()
                if failure == "missing_manifest":
                    self.release["assets"].pop(0)
                elif failure == "wrong_owner":
                    self.release["assets"][1]["browser_download_url"] = "https://example.com/Key.zip"
                elif failure == "digest":
                    self.release["assets"][1]["digest"] = "sha256:" + "0" * 64
                elif failure == "checksum":
                    (self.root / "checksums.txt").write_text(f"{'0' * 64}  {self.asset}\n")
                    self.release["assets"][0] = self.metadata("checksums.txt")
                else:
                    self.release["draft"] = True
                result, output = self.run_verification()
                self.assertNotEqual(result.returncode, 0, failure)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
