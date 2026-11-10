cask "key" do
  version "v0.3.0"
  sha256 "a54f1cab91afc242000cf51125e2f8597b0552bfcf18a63407b5b068e2763213"

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
