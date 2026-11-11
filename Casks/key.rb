cask "key" do
  version "v0.4.0"
  sha256 "7be4c317eed15e73a79bb8777f4b573797ec25f8f4e00fc5f708c1530f7ad7db"

  url "https://github.com/tvr-works/key/releases/download/#{version}/Key-#{version}.zip"
  name "Key"
  desc "CLI password manager backed by Secure Enclave"
  homepage "https://github.com/tvr-works/key"

  livecheck do
    skip "Homebrew updates are published manually"
  end

  depends_on macos: :tahoe

  app "Key.app"
  binary "#{appdir}/Key.app/Contents/MacOS/key", target: "key"
  zsh_completion "completions/_key"

  caveats <<~EOS
    Open Key.app once after install so it can register Key Agent with macOS before you use the key CLI.
  EOS
end
