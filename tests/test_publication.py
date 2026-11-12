"""Exercise release verification with real archives and a local GitHub transport."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import io
import tarfile
import struct
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
    expected = "repos/" + os.environ["REPOSITORY"] + "/releases/tags/" + os.environ["VERSION"]
    assert args[-1] == expected, args
    print((root / "release.json").read_text())
elif args[:2] == ["release", "download"]:
    assert args[args.index("--repo") + 1] == os.environ["REPOSITORY"]
    destination = pathlib.Path(args[args.index("--dir") + 1])
    for index, value in enumerate(args):
        if value == "--pattern":
            shutil.copyfile(root / args[index + 1], destination / args[index + 1])
else:
    raise SystemExit("unexpected GitHub command: " + repr(args))
''')
        gh.chmod(0o755)

    def fixture(self, channel=None):
        self.repository = "tvr-works/key"
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
            "browser_download_url": f"https://github.com/{self.repository}/releases/download/{self.version}/{name}",
            "digest": "sha256:" + hashlib.sha256((self.root / name).read_bytes()).hexdigest(),
        }

    def run_verification(self, package="key"):
        (self.root / "release.json").write_text(json.dumps(self.release))
        output = self.root / "outputs"
        output.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                   FIXTURE=str(self.root), VERSION=self.version, REPOSITORY=self.repository, RUNNER_TEMP=str(self.root))
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

    def xkcdpass_fixture(self):
        self.repository = "tvr-works/xkcdpass"
        self.version = "v0.2.1"
        self.archives = [f"xkcdpass_{self.version}_{target}.tar.gz"
                         for target in ["darwin_arm64", "linux_amd64"]]
        # Minimal real format headers let file(1) inspect both archives. Native
        # execution uses the actual preserved release in the integration check.
        headers = [struct.pack("<IIIIIIII", 0xfeedfacf, 0x100000c, 0, 2, 0, 0, 0, 0),
                   b"\x7fELF\x02\x01\x01\x00" + bytes(8) + struct.pack("<HHI", 2, 62, 1) + bytes(40)]
        for name, header in zip(self.archives, headers):
            with tarfile.open(self.root / name, "w:gz") as archive:
                entry = tarfile.TarInfo(name.removesuffix(".tar.gz") + "/xkcdpass")
                entry.size = len(header)
                entry.mode = 0o755
                archive.addfile(entry, io.BytesIO(header))
        (self.root / "checksums.txt").write_text("".join(
            f"{hashlib.sha256((self.root / name).read_bytes()).hexdigest()}  {name}\n"
            for name in self.archives))
        self.release = {
            "tag_name": self.version, "draft": False, "immutable": True,
            "html_url": f"https://github.com/{self.repository}/releases/tag/{self.version}",
            "published_at": "2026-09-02T00:00:00Z", "prerelease": False,
            "assets": [self.metadata(name) for name in ["checksums.txt", *self.archives]],
        }

    def test_xkcdpass_rejects_bad_release_evidence(self):
        for failure in ["old_owner", "mutable", "extra_asset", "linux_digest",
                        "missing_linux", "duplicate_checksum", "bad_layout", "symlink"]:
            with self.subTest(failure=failure):
                self.xkcdpass_fixture()
                if failure == "old_owner":
                    self.release["html_url"] = self.release["html_url"].replace("tvr-works", "tvanreenen")
                elif failure == "mutable":
                    self.release["immutable"] = False
                elif failure == "extra_asset":
                    self.release["assets"].append(dict(self.release["assets"][0], name="extra"))
                elif failure == "linux_digest":
                    self.release["assets"][2]["digest"] = "sha256:" + "0" * 64
                elif failure == "missing_linux":
                    self.release["assets"].pop()
                else:
                    if failure == "duplicate_checksum":
                        path = self.root / "checksums.txt"
                        path.write_text(path.read_text() * 2)
                    else:
                        name = self.archives[0]
                        with tarfile.open(self.root / name, "w:gz") as archive:
                            entry = tarfile.TarInfo("unexpected" if failure == "bad_layout" else name.removesuffix(".tar.gz") + "/xkcdpass")
                            if failure == "symlink":
                                entry.type = tarfile.SYMTYPE
                                entry.linkname = "/nonexistent-xkcdpass"
                            archive.addfile(entry)
                        (self.root / "checksums.txt").write_text("".join(
                            f"{hashlib.sha256((self.root / name).read_bytes()).hexdigest()}  {name}\n"
                            for name in self.archives))
                    self.release["assets"] = [self.metadata(name) for name in ["checksums.txt", *self.archives]]
                result, output = self.run_verification("xkcdpass")
                self.assertNotEqual(result.returncode, 0, failure)
                self.assertFalse(output.exists())

    def test_xkcdpass_updates_both_platforms(self):
        updater = ROOT / ".github/scripts/update-xkcdpass-formula.rb"
        candidate = self.root / "xkcdpass.rb"
        result = subprocess.run([str(updater), str(ROOT / "Formula/xkcdpass.rb"),
                                 str(candidate), "0.2.2", "a" * 64, "b" * 64],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        contents = candidate.read_text()
        self.assertEqual(contents.count("/releases/download/v0.2.2/"), 2)
        self.assertIn('sha256 "' + "a" * 64 + '"', contents)
        self.assertIn('sha256 "' + "b" * 64 + '"', contents)
        self.assertNotIn("tvanreenen", contents)
        result = subprocess.run([str(updater), str(candidate), str(candidate), "0.2.2",
                                 "a" * 64, "b" * 64], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_other_packages(self):
        self.fixture()
        for package in ["unknown"]:
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

    def test_frame_rejects_bad_release_evidence(self):
        for failure in ["old_owner", "extra_asset", "duplicate_checksum", "digest", "draft", "prerelease"]:
            with self.subTest(failure=failure):
                self.repository = "tvr-works/frame"
                self.version = "v3.2.0"
                self.asset = "Frame-v3.2.0.zip"
                (self.root / self.asset).write_bytes(b"archive fixture")
                digest = hashlib.sha256((self.root / self.asset).read_bytes()).hexdigest()
                (self.root / "checksums.txt").write_text(f"{digest}  {self.asset}\n")
                self.release = {
                    "tag_name": self.version, "draft": False, "prerelease": False,
                    "published_at": "2026-11-11T00:00:00Z", "immutable": False,
                    "html_url": f"https://github.com/{self.repository}/releases/tag/{self.version}",
                    "assets": [self.metadata(n) for n in ["checksums.txt", self.asset]],
                }
                if failure == "old_owner":
                    self.release["html_url"] = self.release["html_url"].replace("tvr-works", "tvanreenen")
                elif failure == "extra_asset":
                    self.release["assets"].append(dict(self.release["assets"][0], name="extra"))
                elif failure == "duplicate_checksum":
                    path = self.root / "checksums.txt"
                    path.write_text(path.read_text() * 2)
                    self.release["assets"][0] = self.metadata("checksums.txt")
                elif failure == "digest":
                    self.release["assets"][1]["digest"] = "sha256:" + "0" * 64
                elif failure == "draft":
                    self.release["draft"] = True
                else:
                    self.release["prerelease"] = True
                result, output = self.run_verification("frame")
                self.assertNotEqual(result.returncode, 0, failure)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
