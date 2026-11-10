cask "key@beta" do
  version "v0.3.0-beta.1"
  sha256 "3f21f2edee96dd4867ef2634e72377e5220aa8021bb029ab40d2f7563bbbb6b0"

  url "https://github.com/tvr-works/key/releases/download/#{version}/Key-Preview-#{version}.zip"
  name "Key Preview"
  desc "CLI password manager backed by Secure Enclave"
  homepage "https://github.com/tvr-works/key"

  livecheck do
    skip "Homebrew updates are published manually"
  end

  conflicts_with cask: ["key@alpha", "key@rc"]
  depends_on macos: :tahoe

  app "Key Preview.app"
  binary "#{appdir}/Key Preview.app/Contents/MacOS/key-preview", target: "key-preview"

  caveats <<~EOS
    Open Key Preview.app once after install so it can register Key Preview Agent with macOS before you use the key-preview CLI.
  EOS
end
