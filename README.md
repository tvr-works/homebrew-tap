# TVR Works Homebrew tap

Install Key from the organization’s tap:

```sh
brew install --cask tvr-works/tap/key
```

Preview channels are opt-in and can coexist with Stable:

```sh
brew install --cask tvr-works/tap/key@alpha
brew install --cask tvr-works/tap/key@beta
```

Alpha, beta, and release-candidate casks share the Preview app identity, so install one Preview channel at a time. The release-candidate cask is created when the first verified rc release is published.

## Existing personal-tap installations

The personal tap migration entries will direct `key`, `key@alpha`, and `key@beta` to `tvr-works/tap`. After that change is merged, run `brew update` and add the destination tap with `brew tap tvr-works/tap`. Use the fully qualified organization cask for future upgrades. Keep the personal tap if you also use Frame or xkcdpass. This repository migration does not change Key’s application identity or vault data.

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

Before dispatching publication, allow GitHub Actions to create pull requests in the organization’s Actions settings, then enable the repository setting **Allow GitHub Actions to create and approve pull requests** for the proposal job. At setup, the inherited organization policy blocked this repository setting; an organization owner must enable it. Keep the default workflow token permission read-only. Workflow-generated PR checks require manual approval before running.

Casks and publication tooling originated in [tvanreenen/homebrew-tap](https://github.com/tvanreenen/homebrew-tap/tree/d7067814958c452aaa55442f1a74cb9cf22ec6bb) and are maintained here for Key.
