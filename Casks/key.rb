cask "key" do
  version "v0.4.1"
  sha256 "0904ff9bd8ff57f00305cff22176d8677d340e0bfede27b46b72b64cda87476a"

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
