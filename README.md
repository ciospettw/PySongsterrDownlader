# Songsterr Tab Downloader

A Python tool to download Guitar Pro tabs from [Songsterr](https://www.songsterr.com) as JSON files.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Features

- Download all instrument tracks from any Songsterr song
- Generate PDF tablature files (optional)
- Automatic track naming (guitar, bass, drums, etc.)
- Organized output with metadata
- Headless browser mode (no GUI needed)
- Anti-detection measures to avoid blocking

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Chrome browser installed

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/songsterr-downloader.git
   cd songsterr-downloader
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install selenium webdriver-manager requests
   ```

## Usage

### Basic Usage

Download a song by providing its Songsterr URL:

```bash
python songsterr_downloader.py "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27"
```

### Specify Output Directory

```bash
python songsterr_downloader.py "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27" -o ./my_tabs
```

### Show Browser Window (Debugging)

```bash
python songsterr_downloader.py "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27" --no-headless
```

### Verbose Mode

```bash
python songsterr_downloader.py "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27" -v
```

### Generate PDF Tabs

```bash
python songsterr_downloader.py "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27" --pdf
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `url` | Songsterr song URL (required) |
| `-o, --output` | Output directory (default: `./<artist>_<song>/`) |
| `--pdf` | Generate PDF tablature files |
| `--no-headless` | Show browser window |
| `-v, --verbose` | Enable verbose debug output |
| `-h, --help` | Show help message |

## Output

The downloader creates a folder with the following structure:

```
artist_song/
├── metadata.json           # Song info, track list, download timestamp
├── 00_lead_guitar.json     # Track 0 data
├── 01_rhythm_guitar.json   # Track 1 data
├── 02_bass.json            # Track 2 data
└── 03_drums.json           # Track 3 data
```

### Track JSON Format

Each track file contains the full tablature data in JSON format, including:
- Note positions and frets
- Timing information
- Effects (bends, slides, hammer-ons, etc.)
- Tempo and time signature changes

### Metadata JSON

```json
{
  "url": "https://www.songsterr.com/a/wsa/...",
  "song_info": {
    "title": "Enter Sandman",
    "artist": "Metallica",
    "song_id": 27,
    "revision_id": 12345,
    "tracks": [...]
  },
  "downloaded_at": "2024-01-15 14:30:00",
  "files": ["00_lead_guitar.json", "01_rhythm_guitar.json", ...]
}
```

## How It Works

1. **Browser Automation**: Uses Selenium WebDriver to load the Songsterr page
2. **Network Capture**: Monitors network requests to capture CloudFront CDN URLs
3. **Data Extraction**: Extracts song metadata from the page's state script
4. **Download**: Fetches all track JSON files from the CDN
5. **Organization**: Saves files with proper naming and metadata

## Troubleshooting

### Chrome Not Found
Make sure Google Chrome is installed. The `webdriver-manager` package will automatically download the correct ChromeDriver.

### Network Timeout
If downloads are slow or failing, try running with `--no-headless` to see what's happening in the browser.

### No Tracks Found
Some songs may not have all tracks available. Check the metadata.json for available track information.

### Anti-Bot Detection
If you encounter blocking, wait a few minutes before retrying. The script includes anti-detection measures, but excessive usage may trigger rate limiting.

## Legal Notice

This tool is for **personal use only**. Please respect Songsterr's Terms of Service and the rights of music publishers. Downloaded tabs should only be used for personal practice and learning.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Songsterr](https://www.songsterr.com) for providing an amazing tab resource
- [Selenium](https://www.selenium.dev/) for browser automation
- [webdriver-manager](https://github.com/SergeyPirogov/webdriver_manager) for ChromeDriver management
