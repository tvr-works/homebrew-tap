# TVR Works Homebrew tap

Install Frame, Key, or xkcdpass from the organization’s tap:

```sh
brew install --cask tvr-works/tap/key
brew install --cask tvr-works/tap/frame
brew install tvr-works/tap/xkcdpass
```

Preview channels are opt-in and can coexist with Stable:

```sh
brew install --cask tvr-works/tap/key@alpha
brew install --cask tvr-works/tap/key@beta
```

Alpha, beta, and release-candidate casks share the Preview app identity, so install one Preview channel at a time. The release-candidate cask is created when the first verified rc release is published.

## Existing personal-tap installations

The personal tap migration entries direct existing tokens to `tvr-works/tap`. Run `brew update` and add the destination tap with `brew tap tvr-works/tap`, then use the fully qualified organization package for future upgrades. Retain the personal tap for its compatibility forwarding entries. This repository migration does not change Key’s application identity or vault data. Frame's cask receipt behavior is recorded below.

## Publishing updates

Key publishes a signed, verified GitHub release before proposing a cask update. Dispatch the tap’s workflow on `main`:

```sh
gh workflow run publish-package.yml \
  --repo tvr-works/homebrew-tap \
  --ref main \
  -f package=key \
  -f version=vX.Y.Z
```

Stable tags update `key`; numbered alpha, beta, and rc tags update the corresponding Preview cask. The workflow verifies exact assets, archive checksums and GitHub digests, audits the candidate, and proposes one cask change through a pull request. Historical releases without `checksums.txt` do not satisfy this newer publication contract; publish a new qualified version rather than replacing their assets.

Before dispatching publication, allow GitHub Actions to create pull requests in the organization’s Actions settings, then enable the repository setting **Allow GitHub Actions to create and approve pull requests** for the proposal job. Keep the default workflow token permission read-only. Workflow-generated PR checks require manual approval before running.

Publication and installation tests retain Homebrew's API mode with `core: false` and `cask: false` in setup-homebrew. Fully qualified names select this tap's checked-out definitions while official dependencies and removal metadata remain available through the API. Setting `HOMEBREW_NO_INSTALL_FROM_API=1` here instead forces official tap checkouts; the v3.2.1 publisher log showed a core clone before Frame removal, with a resulting checkout footprint of 1.5 GB. That figure is not a measurement of transferred bytes, and the log does not identify the exact internal call that initiated the clone.

The publisher and PR CI use the same install/runtime-test/remove script. It verifies the selected tap and the local Ruby definition's path and SHA-256, then checks selected version, archive URL and checksum, installed receipt origin/version, and ordinary removal. The publisher also compares the rendered candidate to the independently verified release metadata. Disposable-runner preparation first untaps any official repositories inherited from the runner image; `core: false` and `cask: false` skip setup fetches but do not remove preinstalled checkouts. Each integration path then checks that API mode remains enabled and neither official tap checkout appears. Install, runtime test, and uninstall preparation have separate log labels; dependency checks and automatic removal remain enabled. Frame's migration test retains its explicit updates, unavailable-destination preservation, same-version receipt recovery and clean destination installation. These checks run only in disposable Actions environments and refuse to replace an existing installed package.

Casks and publication tooling originated in [tvanreenen/homebrew-tap](https://github.com/tvanreenen/homebrew-tap/tree/d7067814958c452aaa55442f1a74cb9cf22ec6bb) and are maintained here for Frame, Key, and xkcdpass.

## Frame publication and migration

Frame keeps its existing `frame` token, `com.frame.app` app identifier, app/CLI archive layout, signing team `9Q355KSV85`, and published release bytes. The initial organization cask uses the existing `v3.2.0` ZIP with SHA-256 `840da5ded27fc57505b1c92d23e2826fb42103c3a7661699fb74e09bb718978d`. Source releases remain owned by `tvr-works/frame`; this tap owns verification, cask updates, and proposal PRs. Future publication is still manually dispatched with `package=frame` and a published stable v-prefixed version.

The Frame verifier requires the canonical release owner and tag, published non-prerelease state, exactly the ZIP and `checksums.txt`, matching API digests and manifest, safe archive paths, executable permissions, the expected metadata/resources, universal app and CLI, matching binary/tag versions, and valid Developer ID signatures from the existing signing team. Historical Frame releases are not GitHub-enforced immutable releases; the verifier does not copy xkcdpass's `immutable=true` requirement or replace existing assets to satisfy it. Cask updates use the existing state check and Homebrew renderer, so inconsistent same-version metadata and version regressions are rejected before proposal.

The required macOS audit job also exercises the preserved release and real Homebrew installation/receipt behavior in a disposable runner. It models the personal tap through a local Git fixture, tests an unavailable destination without changing installed bytes, resolves the legacy token through migration metadata, records same-version receipt behavior, exercises explicit receipt recovery when needed, and performs a clean destination install. It never starts the window-manager daemon. These tests do not change the maintainer's installed app or receipts.

The destination cask uses Homebrew's default quarantine handling. It does not copy the old personal cask's quarantine-removal workaround. The current release is not qualified as notarized; fresh-download first-launch Gatekeeper acceptance, Accessibility/login continuity, and a future genuinely newer-version upgrade remain separate distribution/device qualifications. CI signature checks and `--version` execution do not establish them.

Keep the personal Frame cask until the destination checks and source dispatch route are integrated. Only then add `frame` to the personal tap's existing migration metadata and retire its old Frame publisher. Existing users should run `brew update`, add `tvr-works/tap`, approve tap trust if their Homebrew version requests it, and use `brew upgrade --cask tvr-works/tap/frame`. In [disposable macOS qualification](https://github.com/tvr-works/homebrew-tap/actions/runs/43119476695/attempts/2), the legacy token resolved to the organization cask, but the already-current `3.2.0` install retained its personal-tap receipt. An explicit same-version reinstall refreshed the receipt to `tvr-works/tap` and preserved app/CLI hashes; a fresh destination install also passed. Existing users can retain their current app until a genuine future upgrade instead of reinstalling solely to change receipt metadata. Reinstallation and first-launch acceptance must be considered separately on a real device; no uninstall or data deletion is part of the migration instructions.

## xkcdpass updates and migration

The xkcdpass formula uses the existing immutable `v0.2.1` release from `tvr-works/xkcdpass`. Its macOS ARM64 and Linux AMD64 archive checksums are unchanged by the repository transfer. CI installs and tests the published binary on both platforms; the macOS job also verifies canonical release metadata and both downloaded archive digests. `--build-from-source` instructs Homebrew to use the formula's archive rather than look for a Homebrew bottle; this formula installs the prebuilt executable.

Future updates use the same manually dispatched workflow with `package=xkcdpass`. The verifier requires the canonical organization release URL, immutable published state, exactly two platform archives and the checksum file, matching manifest and API digests, expected archive layout, and native macOS version execution. The updater changes both platform URLs and checksums together. The read-only verify job audits and tests the candidate before the write-enabled proposal job can create a pull request. The workflow never releases source artifacts or merges its proposed change.

Integrate this destination formula and pass both native installation jobs before removing the personal-tap formula or adding its migration entry. Integrate the source project's updated tap dispatch next. Only then integrate `xkcdpass` in the personal tap's `tap_migrations.json`; keep Frame and the existing Key migration entries. Existing users can then run `brew update`, `brew tap tvr-works/tap`, and `brew upgrade tvr-works/tap/xkcdpass`. Homebrew updates installed package receipts to the destination tap during migration, without replacing release bytes.

Linux Blacksmith images include a Homebrew prefix owned by a different image user. The installation job repairs ownership of `/home/linuxbrew/.linuxbrew` inside its disposable VM before the pinned setup action updates Homebrew. macOS jobs do not need that step. Installation keeps Homebrew's core API available instead of forcing an implicit full core Git clone. An explicit formula-origin check confirms that the fully qualified package still comes from this tap before installing and testing its published archive. The personal tap remains on GitHub-hosted runners because Blacksmith does not support personal-account repositories.
