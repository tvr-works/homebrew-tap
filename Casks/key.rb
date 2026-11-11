cask "key" do
  version "v0.3.1"
  sha256 "93b5364fbfbfc1caf9e954f5d260b5fc5c8e55a2e583f525424e8cf89f11a131"

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
