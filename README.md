# Audio DeConstruct

Version: v1.0.0.1

Professional Audio Stem Separation & Processing Utility  
Built by Priyanshu

## Features

- GPU-accelerated Demucs stem separation
- Multi-format audio conversion
- Multi-track playback with dual timeline modes
- Minimal DAW-style waveform visualization
- Persistent window state
- Crash logging
- Modern dark UI
- **Convert & Separate require a destination folder** — you must select an output folder before adding tasks; no silent fallbacks.

## Screenshots

(Add screenshots later)

## Installation

### Option 1 — Installer (Recommended)

Download the latest installer from the Releases section and run:

`AudioDeConstructInstaller.exe`

### Option 2 — Portable Build

Download the ZIP release and run:

`Audio DeConstruct.exe`

## Building From Source

1. Clone repository
2. Create virtual environment
3. Install requirements:

   ```bash
   pip install -r requirements.txt
   ```

4. Run:

   ```bash
   python qt_ui/main.py
   ```

## Building Installer

1. Run:

   ```bash
   build_exe.bat
   ```

2. Open `installer.iss` in Inno Setup
3. Click Compile

## Contributing

Pull requests are welcome.  
For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License.  
See LICENSE.txt for details.

## Author

Priyanshu
