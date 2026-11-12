"""Validate Frame archive boundaries portably; real signatures run on macOS CI."""
import os
from pathlib import Path
import plistlib
import stat
import struct
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "Frame-v3.2.0"
APP = f"{PREFIX}/Frame.app/Contents"


class FrameArchiveTests(unittest.TestCase):
    def check_archive(self, failure=None):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            archive_path = directory / "Frame.zip"
            universal = struct.pack(">II", 0xCAFEBABE, 2) + b"".join(
                struct.pack(">IIIII", cpu, 0, 48, 1, 0) for cpu in [0x01000007, 0x0100000C]) + b"x"
            info = {"CFBundleIdentifier": "com.frame.app", "CFBundleExecutable": "Frame",
                    "CFBundleShortVersionString": "3.2.0", "LSMinimumSystemVersion": "13.0"}
            if failure in ("identity", "version", "minimum_os"):
                key = {"identity": "CFBundleIdentifier", "version": "CFBundleShortVersionString",
                       "minimum_os": "LSMinimumSystemVersion"}[failure]
                info[key] = "unexpected"
            files = {f"{PREFIX}/LICENSE": b"license", f"{PREFIX}/licenses/HotKey": b"license",
                     f"{PREFIX}/licenses/TOMLKit": b"license", f"{PREFIX}/bin/frame": universal,
                     f"{APP}/MacOS/Frame": universal, f"{APP}/Info.plist": plistlib.dumps(info),
                     f"{APP}/_CodeSignature/CodeResources": b"signature fixture",
                     f"{APP}/Resources/default-config.toml": b"config",
                     f"{APP}/Resources/AppIcon.icns": b"icon", f"{APP}/Resources/Assets.car": b"assets",
                     f"{APP}/PkgInfo": b"APPL????"}
            if failure == "missing_resource":
                files.pop(f"{APP}/Resources/default-config.toml")
            if failure == "traversal":
                files[f"{PREFIX}/../escape"] = b"escape"
            if failure == "extra_root":
                files["outside/fixture"] = b"outside"
            if failure == "noncanonical":
                files[f"{PREFIX}/./LICENSE"] = b"alias"
            if failure == "architecture":
                files[f"{PREFIX}/bin/frame"] = b"not universal"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, data in files.items():
                    member = zipfile.ZipInfo(name)
                    executable = name.endswith(("/bin/frame", "/MacOS/Frame"))
                    mode = 0o755 if executable else 0o644
                    if failure == "permissions" and executable:
                        mode = 0o644
                    kind = stat.S_IFLNK if failure == "symlink" and executable else stat.S_IFREG
                    member.external_attr = (kind | mode) << 16
                    archive.writestr(member, data)
            destination = directory / "extracted"
            result = subprocess.run(["python3", str(ROOT / ".github/scripts/verify-frame-archive.py"),
                                     str(archive_path), "v3.2.0", str(destination)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, failure is None, result.stderr)
            self.assertEqual(destination.exists(), failure is None)
            if failure is None:
                self.assertTrue(os.access(destination / PREFIX / "bin/frame", os.X_OK))
            self.assertFalse((directory / "escape").exists())

    def test_complete_archive(self):
        self.check_archive()

    def test_rejects_invalid_archive_before_extraction(self):
        for failure in ["identity", "version", "minimum_os", "missing_resource", "traversal",
                        "extra_root", "noncanonical", "architecture", "permissions", "symlink"]:
            with self.subTest(failure=failure):
                self.check_archive(failure)


if __name__ == "__main__":
    unittest.main()
