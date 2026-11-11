cask "frame" do
  version "3.2.0"
  sha256 "840da5ded27fc57505b1c92d23e2826fb42103c3a7661699fb74e09bb718978d"

  url "https://github.com/tvr-works/frame/releases/download/v#{version}/Frame-v#{version}.zip"
  name "Frame"
  desc "Keyboard-driven workspace and tiling window manager"
  homepage "https://github.com/tvr-works/frame"

  livecheck do
    skip "Homebrew updates are published manually"
  end

  depends_on macos: :ventura

  app "Frame-v#{version}/Frame.app"
  binary "Frame-v#{version}/bin/frame"
end
