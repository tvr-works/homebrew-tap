#!/usr/bin/env bash
# Runner images may include official taps even when setup skips fetching them.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && -n "${RUNNER_TEMP:-}" ]] || {
  echo 'API-only preparation requires a disposable Actions runner' >&2; exit 1;
}
[[ -z "${HOMEBREW_NO_INSTALL_FROM_API:-}" ]] || {
  echo 'Homebrew API mode must remain enabled' >&2; exit 1;
}
for tap in homebrew/core homebrew/cask; do
  if brew tap | grep -Fqx "${tap}"; then
    echo "Preparing API-only baseline: untapping inherited ${tap}"
    brew untap --force "${tap}"
  fi
done
"$(dirname "$0")/check-homebrew-api.sh"
