#!/usr/bin/env bash
# Shared publisher/PR integration check. Never run against a working installation.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && -n "${RUNNER_TEMP:-}" ]] || {
  echo 'Package installation tests require a disposable Actions runner' >&2; exit 1;
}
[[ $# -eq 2 ]] || { echo "usage: $0 <formula|cask> <fully-qualified-ref>" >&2; exit 1; }
kind="$1"
brew_ref="$2"
[[ "${brew_ref}" =~ ^[a-z0-9-]+/[a-z0-9-]+/[a-zA-Z0-9@+._-]+$ ]] || { echo 'Expected a fully qualified package reference' >&2; exit 1; }
token="${brew_ref##*/}"
case "${kind}" in
  cask) definition="Casks/${token}.rb"; selector='.casks'; install_args=(--cask) ;;
  formula) definition="Formula/${token}.rb"; selector='.formulae'; install_args=(--build-from-source) ;;
  *) echo 'Invalid package kind' >&2; exit 1 ;;
esac
scripts="$(cd "$(dirname "$0")" && pwd)"
"${scripts}/check-homebrew-api.sh"
metadata="$(brew info --json=v2 "${brew_ref}" | jq -e "${selector} | select(length == 1) | .[0]")"
source_sha="$(shasum -a 256 "${definition}" | awk '{print $1}')"
jq -e --arg tap "${brew_ref%/*}" --arg path "${definition}" --arg sha "${source_sha}" '
  .tap == $tap and .ruby_source_path == $path and .ruby_source_checksum.sha256 == $sha
' <<<"${metadata}" >/dev/null || { echo 'Selected package does not match the checked-out definition' >&2; exit 1; }
if [[ "${kind}" == cask ]]; then
  version="$(jq -er .version <<<"${metadata}")"
  url="$(jq -er .url <<<"${metadata}")"
  sha="$(jq -er .sha256 <<<"${metadata}")"
  [[ "$(jq -r .installed <<<"${metadata}")" == null ]] || { echo 'Refusing to replace an installed cask' >&2; exit 1; }
else
  version="$(jq -er .versions.stable <<<"${metadata}")"
  url="$(jq -er .urls.stable.url <<<"${metadata}")"
  sha="$(jq -er .urls.stable.checksum <<<"${metadata}")"
  [[ "$(jq '.installed | length' <<<"${metadata}")" == 0 ]] || { echo 'Refusing to replace an installed formula' >&2; exit 1; }
fi
state="$(mktemp "${RUNNER_TEMP}/package-selection.XXXXXX")"
trap 'rm -f "${state}"' EXIT
"${scripts}/check-package-state.sh" --exact "${kind}" "${brew_ref}" "${version}" "${url}" "${sha}" "${state}"
printf 'Selected %s %s\nURL: %s\nSHA-256: %s\n' "${brew_ref}" "${version}" "${url}" "${sha}"
owned_install=false
cleanup() {
  if [[ "${owned_install}" == true ]]; then
    echo "Cleanup: uninstalling ${brew_ref}"
    brew uninstall "${brew_ref}" || true
  fi
  rm -f "${state}"
}
trap cleanup EXIT
owned_install=true
echo "Install: ${brew_ref}"
brew install "${install_args[@]}" "${brew_ref}"
if [[ "${kind}" == cask ]]; then
  receipts="$(find "$(brew --caskroom)/${token}" -name INSTALL_RECEIPT.json -type f)"
  [[ -f "${receipts}" ]]
  jq -e --arg tap "${brew_ref%/*}" --arg version "${version}" \
    '.source.tap == $tap and .source.version == $version' "${receipts}" >/dev/null
else
  jq -e --arg tap "${brew_ref%/*}" '.source.tap == $tap' \
    "$(brew --prefix "${brew_ref}")/INSTALL_RECEIPT.json" >/dev/null
  brew info --json=v2 "${brew_ref}" | jq -e --arg version "${version}" \
    '.formulae[0].installed | any(.version == $version)' >/dev/null
  echo "Runtime test: ${brew_ref}"
  brew test "${brew_ref}"
fi
echo "Uninstall preparation and removal: ${brew_ref}"
brew uninstall "${brew_ref}"
owned_install=false
"${scripts}/check-homebrew-api.sh"
echo "Install, receipt and removal passed: ${brew_ref}"
