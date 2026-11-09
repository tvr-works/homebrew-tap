# TVR Works Homebrew tap

Install Key or xkcdpass from the organization’s tap:

```sh
brew install --cask tvr-works/tap/key
brew install tvr-works/tap/xkcdpass
```

Preview channels are opt-in and can coexist with Stable:

```sh
brew install --cask tvr-works/tap/key@alpha
brew install --cask tvr-works/tap/key@beta
```

Alpha, beta, and release-candidate casks share the Preview app identity, so install one Preview channel at a time. The release-candidate cask is created when the first verified rc release is published.

## Existing personal-tap installations

The personal tap migration entries will direct `key`, `key@alpha`, and `key@beta` to `tvr-works/tap`. After that change is merged, run `brew update` and add the destination tap with `brew tap tvr-works/tap`. Use the fully qualified organization cask for future upgrades. Once xkcdpass migration is integrated, its existing installations also move to `tvr-works/tap`. Keep the personal tap if you use Frame. This repository migration does not change Key’s application identity or vault data.

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

Casks and publication tooling originated in [tvanreenen/homebrew-tap](https://github.com/tvanreenen/homebrew-tap/tree/d7067814958c452aaa55442f1a74cb9cf22ec6bb) and are maintained here for Key and xkcdpass.

## xkcdpass updates and migration

The xkcdpass formula uses the existing immutable `v0.2.1` release from `tvr-works/xkcdpass`. Its macOS ARM64 and Linux AMD64 archive checksums are unchanged by the repository transfer. CI installs and tests the published binary on both platforms; the macOS job also verifies canonical release metadata and both downloaded archive digests. `--build-from-source` instructs Homebrew to use the formula's archive rather than look for a Homebrew bottle; this formula installs the prebuilt executable.

Future updates use the same manually dispatched workflow with `package=xkcdpass`. The verifier requires the canonical organization release URL, immutable published state, exactly two platform archives and the checksum file, matching manifest and API digests, expected archive layout, and native macOS version execution. The updater changes both platform URLs and checksums together. The read-only verify job audits and tests the candidate before the write-enabled proposal job can create a pull request. The workflow never releases source artifacts or merges its proposed change.

Integrate this destination formula and pass both native installation jobs before removing the personal-tap formula or adding its migration entry. Integrate the source project's updated tap dispatch next. Only then integrate `xkcdpass` in the personal tap's `tap_migrations.json`; keep Frame and the existing Key migration entries. Existing users can then run `brew update`, `brew tap tvr-works/tap`, and `brew upgrade tvr-works/tap/xkcdpass`. Homebrew updates installed package receipts to the destination tap during migration, without replacing release bytes.
