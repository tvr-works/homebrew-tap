#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 4 ]] || { echo "usage: $0 <archive> <v-version> <commit> <extract-dir>" >&2; exit 1; }
archive="$1"
version="$2"
commit="$3"
destination="$4"
python3 "$(dirname "$0")/verify-frame-archive.py" "$archive" "$version" "$destination"
app="$destination/Frame-$version/Frame.app"
app_executable="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist")"
if [[ "$app_executable" == FrameApp ]]; then
  cli="$app/Contents/MacOS/frame"
else
  cli="$destination/Frame-$version/bin/frame"
fi

# Preserve the current publisher identity. Ad-hoc or other-team signatures do
# not qualify. This is signature validation, not a notarization/Gatekeeper claim.
requirement='anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] exists and certificate leaf[field.1.2.840.113635.100.6.1.13] exists and certificate leaf[subject.OU] = "9Q355KSV85"'
codesign --verify --deep --strict -R "=$requirement and identifier \"com.frame.app\"" "$app"
codesign --verify --strict -R "=$requirement and identifier \"frame\"" "$cli"
if [[ "$app_executable" == FrameApp ]]; then
  xcrun stapler validate "$app"
  for target in "$app" "$cli"; do
    for arch in arm64 x86_64; do
      metadata="$(codesign -d --verbose=4 --arch "$arch" "$target" 2>&1)"
      grep -Eq '^CodeDirectory .*flags=.*[(,]runtime[,) ]' <<< "$metadata"
      grep -Eq '^Timestamp=.+$' <<< "$metadata"
      codesign --verify --strict --arch "$arch" --check-notarization -R '=notarized' "$target"
    done
  done
  spctl --assess --type execute --verbose=2 "$app"
fi
app_version="$("$app/Contents/MacOS/$app_executable" --version)"
cli_version="$("$cli" --version)"
[[ "$app_version" == "$cli_version" && "$cli_version" == "${version#v}+"* ]] || {
  echo "Frame app and CLI versions do not match the release" >&2; exit 1;
}
short_commit="${cli_version#*+}"
[[ "$short_commit" =~ ^[0-9a-f]{7,40}$ && "$commit" == "$short_commit"* ]] || {
  echo "Frame binaries do not match the release tag commit" >&2; exit 1;
}
echo "Verified Frame archive, publisher signatures, universal app/CLI and release versions."
