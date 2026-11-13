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


class FrameArchiveTests(unittest.TestCase):
    def check_archive(self, failure=None, version="3.2.0"):
        prefix = f"Frame-v{version}"
        app = f"{prefix}/Frame.app/Contents"
        bundled = version == "3.3.0"
        app_executable = "FrameApp" if bundled else "Frame"
        cli = f"{app}/MacOS/frame" if bundled else f"{prefix}/bin/frame"
        alias = f"{prefix}/bin/frame"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            archive_path = directory / "Frame.zip"
            universal = struct.pack(">II", 0xCAFEBABE, 2) + b"".join(
                struct.pack(">IIIII", cpu, 0, 48, 1, 0) for cpu in [0x01000007, 0x0100000C]) + b"x"
            info = {"CFBundleIdentifier": "com.frame.app", "CFBundleExecutable": app_executable,
                    "CFBundleShortVersionString": version, "LSMinimumSystemVersion": "13.0"}
            if failure in ("identity", "version", "minimum_os"):
                key = {"identity": "CFBundleIdentifier", "version": "CFBundleShortVersionString",
                       "minimum_os": "LSMinimumSystemVersion"}[failure]
                info[key] = "unexpected"
            files = {f"{prefix}/LICENSE": b"license", f"{prefix}/licenses/HotKey": b"license",
                     f"{prefix}/licenses/TOMLKit": b"license", cli: universal,
                     f"{app}/MacOS/{app_executable}": universal, f"{app}/Info.plist": plistlib.dumps(info),
                     f"{app}/_CodeSignature/CodeResources": b"signature fixture",
                     f"{app}/Resources/default-config.toml": b"config",
                     f"{app}/Resources/AppIcon.icns": b"icon", f"{app}/Resources/Assets.car": b"assets",
                     f"{app}/PkgInfo": b"APPL????"}
            if bundled:
                files[alias] = b"../Frame.app/Contents/MacOS/frame"
                if failure == "alias_absolute": files[alias] = b"/tmp/frame"
                if failure == "alias_escape": files[alias] = b"../../frame"
                if failure == "alias_missing": files.pop(alias)
                if failure == "link_child": files[alias + "/child"] = b"unexpected"
                if failure == "case_collision": files[f"{app}/MacOS/Frame"] = universal
            if failure == "missing_resource":
                files.pop(f"{app}/Resources/default-config.toml")
            if failure == "traversal":
                files[f"{prefix}/../escape"] = b"escape"
            if failure == "extra_root":
                files["outside/fixture"] = b"outside"
            if failure == "noncanonical":
                files[f"{prefix}/./LICENSE"] = b"alias"
            if failure == "architecture":
                files[cli] = b"not universal"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, data in files.items():
                    member = zipfile.ZipInfo(name)
                    executable = name in (cli, f"{app}/MacOS/{app_executable}")
                    mode = 0o755 if executable else 0o644
                    if failure == "permissions" and executable:
                        mode = 0o644
                    kind = stat.S_IFLNK if failure == "symlink" and executable else stat.S_IFREG
                    if bundled and name == alias and failure != "alias_regular": kind = stat.S_IFLNK
                    if failure == "other_link" and name.endswith("LICENSE"): kind = stat.S_IFLNK
                    member.external_attr = (kind | mode) << 16
                    archive.writestr(member, data)
            destination = directory / "extracted"
            result = subprocess.run(["python3", str(ROOT / ".github/scripts/verify-frame-archive.py"),
                                     str(archive_path), f"v{version}", str(destination)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, failure is None, result.stderr)
            self.assertEqual(destination.exists(), failure is None)
            if failure is None:
                self.assertTrue(os.access(destination / cli, os.X_OK))
                if bundled:
                    self.assertTrue((destination / alias).is_symlink())
                    self.assertEqual(os.readlink(destination / alias), "../Frame.app/Contents/MacOS/frame")
                    self.assertEqual((destination / alias).resolve(), (destination / cli).resolve())
            self.assertFalse((directory / "escape").exists())

    def test_complete_archive(self):
        self.check_archive()

    def test_bundled_archive_and_compatibility_alias(self):
        self.check_archive(version="3.3.0")

    def test_rejects_invalid_bundled_archive_before_extraction(self):
        for failure in ["identity", "version", "minimum_os", "missing_resource", "traversal",
                        "extra_root", "noncanonical", "architecture", "permissions", "symlink",
                        "alias_absolute", "alias_escape", "alias_missing", "alias_regular", "link_child",
                        "case_collision", "other_link"]:
            with self.subTest(failure=failure):
                self.check_archive(failure, "3.3.0")

    def test_rejects_invalid_archive_before_extraction(self):
        for failure in ["identity", "version", "minimum_os", "missing_resource", "traversal",
                        "extra_root", "noncanonical", "architecture", "permissions", "symlink"]:
            with self.subTest(failure=failure):
                self.check_archive(failure)


if __name__ == "__main__":
    unittest.main()
