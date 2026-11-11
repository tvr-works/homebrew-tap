#!/usr/bin/env python3
"""Validate Frame's archive layout and metadata before extracting any code."""
import argparse
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import struct
import zipfile


def verify(archive_path, version, destination):
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ValueError("Frame requires a stable v-prefixed version")
    root = f"Frame-{version}"
    app = f"{root}/Frame.app/Contents"
    with zipfile.ZipFile(archive_path) as archive:
        names = set()
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if (member.filename in names or path.is_absolute() or ".." in path.parts
                    or "\\" in member.filename or not path.parts or path.parts[0] != root
                    or member.filename.rstrip("/") != str(path)
                    or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode))):
                raise ValueError(f"Unexpected, duplicate, or linked archive entry: {member.filename}")
            names.add(member.filename)
        required = [f"{root}/LICENSE", f"{root}/licenses/HotKey", f"{root}/licenses/TOMLKit",
                    f"{root}/bin/frame", f"{app}/MacOS/Frame", f"{app}/Info.plist",
                    f"{app}/_CodeSignature/CodeResources", f"{app}/Resources/default-config.toml",
                    f"{app}/Resources/AppIcon.icns", f"{app}/Resources/Assets.car", f"{app}/PkgInfo"]
        for name in required:
            if name not in names or not stat.S_ISREG(archive.getinfo(name).external_attr >> 16):
                raise ValueError(f"Missing regular release file: {name}")
        info = plistlib.loads(archive.read(f"{app}/Info.plist"))
        expected = {"CFBundleIdentifier": "com.frame.app", "CFBundleExecutable": "Frame",
                    "CFBundleShortVersionString": version[1:], "LSMinimumSystemVersion": "13.0"}
        for key, value in expected.items():
            if info.get(key) != value:
                raise ValueError(f"Unexpected Frame metadata: {key}")
        for name in (f"{root}/bin/frame", f"{app}/MacOS/Frame"):
            member = archive.getinfo(name)
            if not (member.external_attr >> 16) & 0o111:
                raise ValueError(f"Release executable has no executable permission: {name}")
            data = archive.read(name)
            if len(data) < 48 or data[:4] != b"\xca\xfe\xba\xbe":
                raise ValueError(f"Expected a universal Mach-O executable: {name}")
            count = struct.unpack_from(">I", data, 4)[0]
            architectures = {struct.unpack_from(">I", data, 8 + index * 20)[0]
                             for index in range(count)} if count == 2 else set()
            if architectures != {0x01000007, 0x0100000C}:
                raise ValueError(f"Expected exactly x86_64 and arm64: {name}")
        destination.mkdir()
        archive.extractall(destination)
        for member in archive.infolist():
            (destination / member.filename).chmod((member.external_attr >> 16) & 0o777)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("version")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        verify(args.archive, args.version, args.destination)
    except (ValueError, OSError, zipfile.BadZipFile, plistlib.InvalidFileException) as error:
        parser.exit(1, f"Invalid Frame archive: {error}\n")
