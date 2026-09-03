# Macan Player Classic

Macan Player Classic is a free and open-source video and audio player for Windows, built as a fork of [Media Player Classic - Home Cinema (MPC-HC)](https://github.com/clsid2/mpc-hc). It is part of the **MacanAngkasa** suite of applications.

This project inherits MPC-HC's lightweight, DirectShow-based playback engine and its clean, no-frills interface, while introducing its own branding, customizations, and ongoing development under the MacanAngkasa umbrella.

## About This Fork

Macan Player Classic builds on top of the mature and stable MPC-HC codebase. The goal of this fork is to continue active development, add new features, and tailor the player to fit the MacanAngkasa ecosystem, while preserving the performance and flexibility that made MPC-HC popular.

Since MPC-HC's upstream development is largely feature-frozen, this fork is a space to:

- Experiment with new features and UI improvements
- Integrate more closely with other MacanAngkasa applications
- Keep dependencies (codecs, renderers, etc.) up to date
- Accept and review community contributions more actively

## Key Features (inherited from MPC-HC)

- Modern GUI theme (Dark or Light), with customizable seekbar and toolbar sizes
- Video preview on the seekbar
- HDR video playback via the built-in MPC Video Renderer or madVR
- Broad format support, including HEVC (H.265), VVC (H.266), and AV1 video, plus AC4 audio
- High-performance subtitle rendering with libass and WebVTT support
- Built-in subtitle search
- Adjustable playback speed with pitch-corrected audio renderers
- Resume playback from the last position
- Quick seeking via Ctrl + Mouse Scroll
- Jump between files in a folder with PageUp/PageDown
- Configurable actions on end-of-file playback
- A-B repeat for looping video segments
- Video rotate/flip/mirror/stretch/zoom controls
- Fully customizable keyboard hotkeys and mouse actions
- Direct streaming from YouTube and other sites via yt-dlp integration

## System Requirements

- Windows 7 / 8 / 8.1 / 10 / 11

## Building

This project follows the same general build process as upstream MPC-HC. Refer to the build instructions in this repository for toolchain and dependency setup.

## Contributing

Contributions are welcome. If you'd like to help improve Macan Player Classic, feel free to open a pull request with your changes.

## Credits

Macan Player Classic is a fork of [MPC-HC](https://github.com/clsid2/mpc-hc), originally maintained by clsid2 and contributors. Huge thanks to the original MPC-HC developers and the maintainers of related upstream projects such as [LAV Filters](https://github.com/Nevcairiel/LAVFilters) for their continued work.

## License

This project is licensed under [GPL v3](COPYING.txt), the same license as upstream MPC-HC.
