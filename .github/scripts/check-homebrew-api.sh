#!/usr/bin/env bash
# A fresh API-mode runner must not acquire either official tap during the test.
set -euo pipefail
[[ -z "${HOMEBREW_NO_INSTALL_FROM_API:-}" ]] || {
  echo 'Homebrew API mode must remain enabled' >&2; exit 1;
}
repository="$(brew --repo)"
for tap in core cask; do
  [[ ! -e "${repository}/Library/Taps/homebrew/homebrew-${tap}" ]] || {
    echo "Unexpected homebrew/${tap} checkout" >&2; exit 1;
  }
done
echo 'Homebrew API mode enabled; official tap checkouts absent.'
