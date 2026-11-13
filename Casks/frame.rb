cask "frame" do
  version "3.2.1"
  sha256 "53c3f0b806646cd2eadfc4626aceb78782da709d865e854f9575d4de16fd9175"

  url "https://github.com/tvr-works/frame/releases/download/v#{version}/Frame-v#{version}.zip"
  name "Frame"
  desc "Keyboard-driven workspace and tiling window manager"
  homepage "https://github.com/tvr-works/frame"

  livecheck do
    skip "Homebrew updates are published manually"
  end

  depends_on macos: :ventura

  app "Frame-v#{version}/Frame.app"
  if Version.new(version) >= Version.new("3.3.0")
    binary "#{appdir}/Frame.app/Contents/MacOS/frame", target: "frame"
  else
    binary "Frame-v#{version}/bin/frame"
  end
end
