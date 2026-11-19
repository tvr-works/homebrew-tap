cask "frame" do
  version "3.4.1"
  sha256 "adb686e9a62fcfb459a3bb3b8b1515caabd25abc5b8c04633525fdc43664fbae"

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
