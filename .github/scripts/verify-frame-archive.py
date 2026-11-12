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
    bundled = tuple(map(int, version[1:].split("."))) >= (3, 3, 0)
    cli = f"{app}/MacOS/frame" if bundled else f"{root}/bin/frame"
    app_executable = "FrameApp" if bundled else "Frame"
    alias = f"{root}/bin/frame"
    alias_target = "../Frame.app/Contents/MacOS/frame"
    with zipfile.ZipFile(archive_path) as archive:
        names = set()
        folded_names = set()
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            compatibility_link = bundled and member.filename == alias and stat.S_ISLNK(mode)
            if (member.filename in names or str(path).casefold() in folded_names
                    or path.is_absolute() or ".." in path.parts
                    or "\\" in member.filename or not path.parts or path.parts[0] != root
                    or member.filename.rstrip("/") != str(path)
                    or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode) or compatibility_link)):
                raise ValueError(f"Unexpected, duplicate, or linked archive entry: {member.filename}")
            if compatibility_link and archive.read(member) != alias_target.encode():
                raise ValueError("Invalid archive CLI compatibility link")
            names.add(member.filename)
            folded_names.add(str(path).casefold())
        if bundled and (alias not in names or not stat.S_ISLNK(archive.getinfo(alias).external_attr >> 16)
                        or any(name.startswith(alias + "/") for name in names)):
            raise ValueError("Missing or invalid archive CLI compatibility link")
        required = [f"{root}/LICENSE", f"{root}/licenses/HotKey", f"{root}/licenses/TOMLKit",
                    cli, f"{app}/MacOS/{app_executable}", f"{app}/Info.plist",
                    f"{app}/_CodeSignature/CodeResources", f"{app}/Resources/default-config.toml",
                    f"{app}/Resources/AppIcon.icns", f"{app}/Resources/Assets.car", f"{app}/PkgInfo"]
        for name in required:
            if name not in names or not stat.S_ISREG(archive.getinfo(name).external_attr >> 16):
                raise ValueError(f"Missing regular release file: {name}")
        info = plistlib.loads(archive.read(f"{app}/Info.plist"))
        expected = {"CFBundleIdentifier": "com.frame.app", "CFBundleExecutable": app_executable,
                    "CFBundleShortVersionString": version[1:], "LSMinimumSystemVersion": "13.0"}
        for key, value in expected.items():
            if info.get(key) != value:
                raise ValueError(f"Unexpected Frame metadata: {key}")
        for name in (cli, f"{app}/MacOS/{app_executable}"):
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
        # Validate every entry first, extract only regular files/directories,
        # then create the one fixed internal alias. Never extract arbitrary links.
        archive.extractall(destination, members=[member for member in archive.infolist()
                                                if not stat.S_ISLNK(member.external_attr >> 16)])
        for member in archive.infolist():
            if not stat.S_ISLNK(member.external_attr >> 16):
                (destination / member.filename).chmod((member.external_attr >> 16) & 0o777)
        if bundled:
            (destination / alias).parent.mkdir(parents=True, exist_ok=True)
            (destination / alias).symlink_to(alias_target)


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
