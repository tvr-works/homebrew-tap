#!/usr/bin/env bash
# Exercise real Homebrew receipts only inside a disposable macOS CI runner.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_OS:-}" == macOS && -n "${RUNNER_TEMP:-}" ]] || {
  echo "Frame installation tests require a disposable macOS Actions runner" >&2; exit 1;
}
[[ ! -e /Applications/Frame.app ]] || { echo "Refusing to replace an existing Frame app" >&2; exit 1; }
if brew list --cask | grep -qx frame; then
  echo "Refusing to change an existing Frame receipt" >&2; exit 1
fi
export HOMEBREW_NO_AUTO_UPDATE=1
export XDG_CONFIG_HOME="$RUNNER_TEMP/frame-migration-config"
mkdir -p "$XDG_CONFIG_HOME/frame"
printf 'migration-config-marker\n' > "$XDG_CONFIG_HOME/frame/.frame.toml"
tap_root="$(pwd)"
scripts="${tap_root}/.github/scripts"
"${scripts}/check-homebrew-api.sh"
fixture="$RUNNER_TEMP/frame-legacy-tap-fixture"
remote="$RUNNER_TEMP/frame-legacy-tap-origin.git"
report="$RUNNER_TEMP/frame-migration-report.txt"
git init --bare --initial-branch=main "$remote"
git clone "$remote" "$fixture"
git -C "$fixture" config user.name 'Frame CI'
git -C "$fixture" config user.email 'frame-ci@example.invalid'
git -C "$fixture" config commit.gpgsign false
mkdir -p "$fixture/Casks"
# Model the legacy package identity, URL and receipt without copying its old
# quarantine-removal workaround into the destination or the test fixture.
sed 's#github.com/tvr-works/frame#github.com/tvanreenen/frame#g' Casks/frame.rb > "$fixture/Casks/frame.rb"
git -C "$fixture" add Casks/frame.rb
git -C "$fixture" commit -m 'Model the legacy Frame tap'
git -C "$fixture" push origin main
brew tap --custom-remote tvanreenen/tap "file://$remote"
if brew command trust >/dev/null 2>&1; then
  brew trust --cask tvanreenen/tap/frame
  brew trust --cask tvr-works/tap/frame
fi
candidate="$(brew info --json=v2 --cask tvr-works/tap/frame)"
version="$(jq -er '.casks[0].version' <<<"${candidate}")"
url="$(jq -er '.casks[0].url' <<<"${candidate}")"
sha="$(jq -er '.casks[0].sha256' <<<"${candidate}")"
assert_destination() {
  "${scripts}/check-package-state.sh" --exact cask tvr-works/tap/frame \
    "${version}" "${url}" "${sha}" "${RUNNER_TEMP}/frame-selected-state"
}
assert_destination
owned_install=false
cleanup() {
  if [[ "$owned_install" == true ]]; then
    brew uninstall --cask frame || true
  fi
}
trap cleanup EXIT
"${scripts}/check-package-state.sh" --exact cask tvanreenen/tap/frame \
  "${version}" "${url/tvr-works/tvanreenen}" "${sha}" "${RUNNER_TEMP}/frame-legacy-state"
echo 'Migration: installing the legacy fixture'
owned_install=true
brew install --cask tvanreenen/tap/frame
receipt="$(find "$(brew --caskroom)/frame" -name INSTALL_RECEIPT.json -type f)"
[[ -f "$receipt" ]]
[[ "$(jq -r '.source.tap' "$receipt")" == tvanreenen/tap ]]
[[ "$(jq -r '.source.version' "$receipt")" == "${version}" ]]
app=/Applications/Frame.app/Contents/MacOS/Frame
cli="$(brew --prefix)/bin/frame"
shasum -a 256 "$app" "$cli" > "$RUNNER_TEMP/frame-before.sha256"

publish_fixture_migration() {
  python3 - "$fixture" "$1" <<'PY'
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
(root / 'Casks/frame.rb').unlink(missing_ok=True)
(root / 'tap_migrations.json').write_text(json.dumps({'frame': sys.argv[2]}) + '\n')
PY
  git -C "$fixture" add -A
  git -C "$fixture" commit -m 'Model Frame tap migration'
  git -C "$fixture" push origin main
}

# An unavailable destination must leave the existing app, CLI and receipt intact.
echo 'Migration: updating to an unavailable destination'
publish_fixture_migration tvr-works/tap/frame-unavailable
brew update > "$RUNNER_TEMP/frame-interrupted-update.log" 2>&1 || true
brew info --json=v2 --cask tvanreenen/tap/frame > "$RUNNER_TEMP/frame-interrupted-resolution.log" 2>&1 || true
shasum -a 256 -c "$RUNNER_TEMP/frame-before.sha256"
[[ "$(jq -r '.source.tap' "$receipt")" == tvanreenen/tap ]]
[[ "$(jq -r '.source.version' "$receipt")" == "${version}" ]]
echo 'Unavailable destination preserved the installed app, CLI and legacy receipt.' > "$report"

echo 'Migration: updating to the real destination'
publish_fixture_migration tvr-works/tap
brew update
brew info --json=v2 --cask tvanreenen/tap/frame > "$RUNNER_TEMP/frame-legacy-resolution.json"
jq -e '.casks | length == 1' "$RUNNER_TEMP/frame-legacy-resolution.json" >/dev/null
jq -e --arg version "${version}" --arg url "${url}" --arg sha "${sha}" '
  .casks[0] | .tap == "tvr-works/tap" and .version == $version and .url == $url and .sha256 == $sha
' "$RUNNER_TEMP/frame-legacy-resolution.json" >/dev/null
assert_destination
echo 'Migration: upgrading the destination'
brew upgrade --cask tvr-works/tap/frame
shasum -a 256 -c "$RUNNER_TEMP/frame-before.sha256"
same_version_tap="$(jq -r '.source.tap' "$receipt")"
printf 'Receipt tap after same-version update/upgrade: %s\n' "$same_version_tap" >> "$report"
if [[ "$same_version_tap" != tvr-works/tap ]]; then
  # Same-token cask moves can retain the old receipt until an actual install.
  # Prove the explicit same-version recovery on the disposable runner too.
  echo 'Migration: recovering the same-version receipt'
  assert_destination
  brew reinstall --cask tvr-works/tap/frame
fi
receipt="$(find "$(brew --caskroom)/frame" -name INSTALL_RECEIPT.json -type f)"
[[ "$(jq -r '.source.tap' "$receipt")" == tvr-works/tap ]]
[[ "$(jq -r '.source.version' "$receipt")" == "${version}" ]]
shasum -a 256 -c "$RUNNER_TEMP/frame-before.sha256"
echo 'Installed receipt now names tvr-works/tap; preserved app/CLI bytes match.' >> "$report"

echo 'Migration: uninstall preparation and removal'
brew uninstall --cask tvr-works/tap/frame
echo 'Migration: fresh destination installation'
assert_destination
owned_install=true
brew install --cask tvr-works/tap/frame
receipt="$(find "$(brew --caskroom)/frame" -name INSTALL_RECEIPT.json -type f)"
[[ "$(jq -r '.source.tap' "$receipt")" == tvr-works/tap ]]
[[ "$(jq -r '.source.version' "$receipt")" == "${version}" ]]
[[ "$(grep -c '^migration-config-marker$' "$XDG_CONFIG_HOME/frame/.frame.toml")" == 1 ]]
shasum -a 256 -c "$RUNNER_TEMP/frame-before.sha256"
[[ "$(git -C "$tap_root" diff --name-only)" == '' ]]
echo 'Fresh destination install passed; configuration marker survived; no GUI/AX daemon was started.' >> "$report"
echo 'Migration: final uninstall preparation and removal'
brew uninstall --cask tvr-works/tap/frame
owned_install=false
"${scripts}/check-homebrew-api.sh"
echo 'API mode remained enabled; no official tap checkout appeared.' >> "$report"
cat "$report"
