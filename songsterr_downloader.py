import subprocess
import sys
import os
import re
import json
import time
import argparse
from urllib.parse import unquote, urlparse

def ensure_packages(include_pdf=False):
    """Ensure all required packages are installed."""
    required = ['selenium', 'webdriver-manager', 'requests']
    if include_pdf:
        required.append('reportlab')
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

ensure_packages()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests


class TabToPDF:
    """Converts JSON tab data to PDF tablature with proper musical notation."""
    
    MIDI_TO_NOTE = {
        28: 'E', 33: 'A', 38: 'D', 43: 'G', 48: 'C',
        40: 'E', 45: 'A', 50: 'D', 55: 'G', 59: 'B', 64: 'e',
        36: 'C', 41: 'F', 46: 'B',
    }
    
    DURATION_SYMBOLS = {
        1: 'w',
        2: 'h',
        4: 'q',
        8: 'e',
        16: 's',
        32: 't',
    }
    
    def __init__(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        self.A4 = A4
        self.mm = mm
        self.page_size = A4
        self.margin = 15 * mm
        self.string_spacing = 3.2 * mm
        self.measures_per_line = 4
        self.line_spacing = 18 * mm
        self.header_height = 25 * mm
        
    def _find_first_content_measure(self, measures):
        """Find the first measure that has actual notes (not just rests)."""
        for i, measure in enumerate(measures):
            if not measure.get('rest', False):
                return max(0, i)
        return 0
    
    def _get_tempo_at_measure(self, automations, measure_idx):
        """Get the tempo (BPM) at a given measure."""
        tempo_changes = automations.get('tempo', [])
        current_bpm = 120
        for tc in tempo_changes:
            if tc.get('measure', 0) <= measure_idx:
                current_bpm = tc.get('bpm', 120)
            else:
                break
        return current_bpm
    
    def _draw_rhythm_stem(self, c, x, y, duration_type, is_beam_start=False, is_beam_stop=False, beam_group=None):
        """Draw rhythm notation below the tab."""
        mm = self.mm
        stem_y = y - 3 * mm
        stem_height = 4 * mm
        
        c.setLineWidth(0.8)
        c.line(x, stem_y, x, stem_y - stem_height)
        
        if duration_type >= 8:
            flag_y = stem_y - stem_height
            if duration_type == 8:
                c.line(x, flag_y, x + 2*mm, flag_y + 1.5*mm)
            elif duration_type == 16:
                c.line(x, flag_y, x + 2*mm, flag_y + 1.5*mm)
                c.line(x, flag_y + 1.2*mm, x + 2*mm, flag_y + 2.7*mm)
            elif duration_type >= 32:
                c.line(x, flag_y, x + 2*mm, flag_y + 1.5*mm)
                c.line(x, flag_y + 1*mm, x + 2*mm, flag_y + 2.5*mm)
                c.line(x, flag_y + 2*mm, x + 2*mm, flag_y + 3.5*mm)
    
    def _draw_time_signature(self, c, x, y, signature, num_strings):
        """Draw time signature at the start of a line."""
        mm = self.mm
        if not signature:
            return
        
        top_num, bottom_num = signature
        center_y = y - (num_strings - 1) * self.string_spacing / 2
        
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x, center_y + 2*mm, str(top_num))
        c.drawCentredString(x, center_y - 4*mm, str(bottom_num))
    
    def _draw_tempo_marking(self, c, x, y, bpm):
        """Draw tempo marking above the staff."""
        mm = self.mm
        c.setFont("Helvetica", 8)
        c.drawString(x, y + 4*mm, f"♩= {bpm}")
        
    def convert(self, json_path, output_path, track_info=None):
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import black, gray, lightgrey, white
        
        mm = self.mm
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        measures = data.get('measures', [])
        if not measures:
            return None
        
        automations = data.get('automations', {})
        
        num_strings = data.get('strings', 6)
        if track_info and track_info.get('tuning'):
            num_strings = len(track_info['tuning'])
        
        tuning = data.get('tuning', track_info.get('tuning') if track_info else None)
        
        is_drums = False
        if track_info:
            is_drums = 'drum' in track_info.get('instrument', '').lower()
        if not is_drums and data.get('instrument'):
            is_drums = 'drum' in data.get('instrument', '').lower()
            
        if is_drums:
            max_string = 0
            for measure in measures[:30]:
                for voice in measure.get('voices', []):
                    for beat in voice.get('beats', []):
                        for note in beat.get('notes', []):
                            s = note.get('string', 0)
                            max_string = max(max_string, int(float(s)) + 1)
            num_strings = max(max_string, 5)
        
        start_measure = self._find_first_content_measure(measures)
        
        c = canvas.Canvas(output_path, pagesize=self.page_size)
        page_width, page_height = self.page_size
        
        y = page_height - self.margin
        
        c.setFont("Helvetica-Bold", 16)
        artist = track_info.get('artist', '') if track_info else ''
        title = track_info.get('title', '') if track_info else ''
        if artist and title:
            c.drawString(self.margin, y, f"{artist} - {title}")
        y -= 7 * mm
        
        c.setFont("Helvetica", 11)
        instrument = track_info.get('instrument', '') if track_info else data.get('instrument', '')
        c.drawString(self.margin, y, instrument)
        y -= 5 * mm
        
        if tuning and not is_drums:
            c.setFont("Helvetica", 9)
            tuning_str = "Tuning: " + " ".join([self.MIDI_TO_NOTE.get(m, '?') for m in reversed(tuning)])
            c.drawString(self.margin, y, tuning_str)
        y -= 8 * mm
        
        initial_bpm = self._get_tempo_at_measure(automations, start_measure)
        
        usable_width = page_width - 2 * self.margin - 15 * mm
        measure_width = usable_width / self.measures_per_line
        
        tab_x_start = self.margin + 15 * mm
        current_x = tab_x_start
        current_y = y
        measure_count = 0
        line_height = num_strings * self.string_spacing + self.line_spacing
        
        current_signature = None
        last_shown_tempo = None
        is_first_line = True
        
        for measure_idx in range(start_measure, len(measures)):
            measure = measures[measure_idx]
            
            if measure_count >= self.measures_per_line:
                measure_count = 0
                current_x = tab_x_start
                current_y -= line_height
                is_first_line = False
                
                if current_y < self.margin + line_height:
                    c.showPage()
                    current_y = page_height - self.margin - 10 * mm
                    is_first_line = True
            
            measure_signature = measure.get('signature', current_signature)
            if measure_signature:
                current_signature = measure_signature
            
            if measure_count == 0:
                c.setFont("Helvetica-Bold", 8)
                c.setFillColor(black)
                if is_drums:
                    drum_labels = ['HH', 'SD', 'BD', 'T1', 'T2', 'CR', 'RD', 'CH']
                    for i in range(num_strings):
                        label = drum_labels[i] if i < len(drum_labels) else str(i+1)
                        c.drawRightString(tab_x_start - 3*mm, current_y - i * self.string_spacing - 2, label)
                elif tuning:
                    for i, midi in enumerate(tuning):
                        label = self.MIDI_TO_NOTE.get(midi, '?')
                        c.drawRightString(tab_x_start - 3*mm, current_y - i * self.string_spacing - 2, label)
                else:
                    for i, label in enumerate(['e', 'B', 'G', 'D', 'A', 'E'][:num_strings]):
                        c.drawRightString(tab_x_start - 3*mm, current_y - i * self.string_spacing - 2, label)
                
                if current_signature and (is_first_line or measure_idx == start_measure):
                    self._draw_time_signature(c, tab_x_start - 10*mm, current_y, current_signature, num_strings)
                
                current_tempo = self._get_tempo_at_measure(automations, measure_idx)
                if current_tempo != last_shown_tempo:
                    self._draw_tempo_marking(c, current_x, current_y, current_tempo)
                    last_shown_tempo = current_tempo
            
            c.setStrokeColor(gray)
            c.setLineWidth(0.5)
            for i in range(num_strings):
                line_y = current_y - i * self.string_spacing
                c.line(current_x, line_y, current_x + measure_width, line_y)
            
            c.setStrokeColor(black)
            c.setLineWidth(1)
            bottom_y = current_y - (num_strings - 1) * self.string_spacing
            c.line(current_x, current_y, current_x, bottom_y)
            
            c.line(current_x + measure_width, current_y, current_x + measure_width, bottom_y)
            
            c.setFont("Helvetica", 7)
            c.setFillColor(gray)
            c.drawString(current_x + 1*mm, current_y + 3*mm, str(measure_idx + 1))
            c.setFillColor(black)
            
            voices = measure.get('voices', [])
            if voices:
                beats = voices[0].get('beats', [])
                if beats:
                    total_duration = sum(b.get('duration', [1,4])[0] / b.get('duration', [1,4])[1] for b in beats)
                    if total_duration == 0:
                        total_duration = 1
                    
                    usable_measure_width = measure_width - 6*mm
                    beat_x = current_x + 3*mm
                    
                    for beat_idx, beat in enumerate(beats):
                        duration = beat.get('duration', [1, 4])
                        duration_ratio = (duration[0] / duration[1]) / total_duration
                        beat_width = usable_measure_width * duration_ratio
                        
                        note_x = beat_x + beat_width * 0.3
                        
                        notes = beat.get('notes', [])
                        has_notes = False
                        
                        for note in notes:
                            if note.get('rest'):
                                continue
                            fret = note.get('fret')
                            string = note.get('string', 0)
                            
                            if fret is not None:
                                has_notes = True
                                string_idx = int(float(string))
                                if string_idx < num_strings:
                                    note_y = current_y - string_idx * self.string_spacing
                                    fret_str = str(fret)
                                    
                                    text_width = c.stringWidth(fret_str, "Courier-Bold", 9)
                                    c.setFillColor(white)
                                    c.rect(note_x - text_width/2 - 1, note_y - 3, text_width + 2, 7, fill=1, stroke=0)
                                    
                                    c.setFillColor(black)
                                    c.setFont("Courier-Bold", 9)
                                    c.drawCentredString(note_x, note_y - 2.5, fret_str)
                        
                        if has_notes:
                            duration_type = beat.get('type', 4)
                            rhythm_y = current_y - (num_strings - 1) * self.string_spacing
                            self._draw_rhythm_stem(c, note_x, rhythm_y, duration_type,
                                                   beat.get('beamStart', False),
                                                   beat.get('beamStop', False))
                        
                        beat_x += beat_width
            
            current_x += measure_width
            measure_count += 1
        
        c.save()
        return output_path


class SongsterrDownloader:
    """Downloads tab data from Songsterr URLs."""
    
    def __init__(self, headless: bool = True, verbose: bool = False, generate_pdf: bool = False):
        """
        Initialize the downloader.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            verbose: Print detailed debug information
            generate_pdf: Generate PDF tabs from downloaded JSON
        """
        self.headless = headless
        self.verbose = verbose
        self.generate_pdf = generate_pdf
        self.driver = None
        self.song_info = {}
        self.track_urls = []
        
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[DEBUG] {message}")
    
    def _setup_driver(self):
        """Set up Chrome WebDriver with network logging."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        self._log("Starting Chrome browser...")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    
    def _extract_song_info(self, page_source: str) -> dict:
        """Extract song metadata from page state."""
        state_match = re.search(r'<script id="state"[^>]*>([^<]+)</script>', page_source)
        
        if not state_match:
            self._log("No state script found in page")
            return {}
        
        try:
            state_json = unquote(state_match.group(1))
            state_data = json.loads(state_json)
            
            if 'meta' in state_data and 'current' in state_data['meta']:
                current = state_data['meta']['current']
                return {
                    'title': current.get('title', 'Unknown'),
                    'artist': current.get('artist', 'Unknown'),
                    'song_id': current.get('songId'),
                    'revision_id': current.get('revisionId'),
                    'tracks': current.get('tracks', []),
                    'default_track': current.get('defaultTrack'),
                }
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse state JSON: {e}")
        
        return {}
    
    def _capture_network_urls(self) -> list:
        """Capture CloudFront JSON URLs from network logs."""
        logs = self.driver.get_log('performance')
        json_urls = set()
        
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                
                if log['method'] in ['Network.requestWillBeSent', 'Network.responseReceived']:
                    if log['method'] == 'Network.requestWillBeSent':
                        url = log['params']['request']['url']
                    else:
                        url = log['params']['response']['url']
                    
                    if 'cloudfront.net' in url and url.endswith('.json'):
                        json_urls.add(url)
                        
            except Exception:
                continue
        
        return sorted(list(json_urls))
    
    def _sanitize_filename(self, name: str) -> str:
        """Create a safe filename from a string."""
        safe = re.sub(r'[^\w\s-]', '', name)
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe.strip('_').lower()
    
    def download(self, url: str, output_dir: str = None) -> dict:
        """
        Download all tabs from a Songsterr URL.
        
        Args:
            url: Songsterr song URL
            output_dir: Output directory (default: ./<artist>_<title>/)
            
        Returns:
            dict with download results
        """
        result = {
            'success': False,
            'song_info': {},
            'files': [],
            'errors': []
        }
        
        try:
            self._setup_driver()
            
            print(f"Loading {url}")
            self.driver.get(url)
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            
            self.song_info = self._extract_song_info(self.driver.page_source)
            result['song_info'] = self.song_info
            
            if not self.song_info:
                result['errors'].append("Could not extract song metadata")
                return result
            
            print(f"{self.song_info['artist']} - {self.song_info['title']} ({len(self.song_info.get('tracks', []))} tracks)")
            
            self.track_urls = self._capture_network_urls()
            self._log(f"Found {len(self.track_urls)} JSON URLs")
            
            if not self.track_urls:
                result['errors'].append("No track URLs found in network logs")
                return result
            
            if output_dir is None:
                artist_safe = self._sanitize_filename(self.song_info['artist'])
                title_safe = self._sanitize_filename(self.song_info['title'])
                output_dir = os.path.join(os.getcwd(), f"{artist_safe}_{title_safe}")
            
            os.makedirs(output_dir, exist_ok=True)
            
            tracks = self.song_info.get('tracks', [])
            track_names = {}
            for i, track in enumerate(tracks):
                name = track.get('title') or track.get('name') or track.get('instrument') or f'track_{i}'
                track_names[i] = f"{i:02d}_{self._sanitize_filename(name)}"
            
            total = len(self.track_urls)
            
            for i, json_url in enumerate(self.track_urls):
                progress = int((i + 1) / total * 30)
                bar = '#' * progress + '-' * (30 - progress)
                print(f"\r[{bar}] {i+1}/{total}", end='', flush=True)
                
                try:
                    match = re.search(r'/(\d+)\.json$', json_url)
                    if match:
                        track_idx = int(match.group(1))
                        track_name = track_names.get(track_idx, f'track_{track_idx}')
                    else:
                        track_name = f'unknown_{len(result["files"])}'
                    
                    response = requests.get(json_url, timeout=30)
                    response.raise_for_status()
                    
                    filename = f"{track_name}.json"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        data = response.json()
                        json.dump(data, f, indent=2)
                    
                    file_size = os.path.getsize(filepath)
                    result['files'].append({
                        'name': filename,
                        'path': filepath,
                        'size': file_size,
                        'track_index': track_idx if match else None,
                        'url': json_url
                    })
                    
                except requests.RequestException as e:
                    result['errors'].append(f"Failed: {json_url}")
                except Exception as e:
                    result['errors'].append(f"Error: {json_url}")
            
            print()
            
            metadata_path = os.path.join(output_dir, 'metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'song_info': self.song_info,
                    'downloaded_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'files': [f['name'] for f in result['files']]
                }, f, indent=2)
            
            result['files'].append({
                'name': 'metadata.json',
                'path': metadata_path,
                'size': os.path.getsize(metadata_path)
            })
            
            result['success'] = len(result['files']) > 1
            
            if self.generate_pdf and result['success']:
                pdf_count = 0
                tracks = self.song_info.get('tracks', [])
                json_files = [f for f in result['files'] if f['name'].endswith('.json') and f['name'] != 'metadata.json']
                
                print("Generating PDFs...", end=' ', flush=True)
                
                for file_info in json_files:
                    try:
                        track_idx = file_info.get('track_index')
                        track_info = None
                        
                        if track_idx is not None and track_idx < len(tracks):
                            track = tracks[track_idx]
                            track_info = {
                                'title': self.song_info.get('title', ''),
                                'artist': self.song_info.get('artist', ''),
                                'instrument': track.get('title') or track.get('instrument', ''),
                                'tuning': track.get('tuning'),
                            }
                        
                        pdf_path = file_info['path'].rsplit('.', 1)[0] + '.pdf'
                        converter = TabToPDF()
                        converter.convert(file_info['path'], pdf_path, track_info)
                        pdf_count += 1
                        
                    except Exception as e:
                        self._log(f"PDF generation failed for {file_info['name']}: {e}")
                
                print(f"{pdf_count} PDFs")
            
            if result['success']:
                total_size = sum(f.get('size', 0) for f in result['files'])
                print(f"Done: {len(result['files']) - 1} tracks, {total_size:,} bytes -> {output_dir}")
            
        except Exception as e:
            result['errors'].append(f"Download failed: {e}")
            print(f"Error: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
        
        return result


def validate_url(url: str) -> bool:
    """Validate that the URL is a valid Songsterr URL."""
    parsed = urlparse(url)
    return (
        parsed.scheme in ('http', 'https') and
        'songsterr.com' in parsed.netloc and
        '/a/wsa/' in parsed.path
    )


def main():
    parser = argparse.ArgumentParser(
        description='Download Guitar Pro tabs from Songsterr as JSON files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27"
  %(prog)s "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27" -o ./downloads
  %(prog)s "https://www.songsterr.com/a/wsa/metallica-enter-sandman-tab-s27" --no-headless
        '''
    )
    
    parser.add_argument(
        'url',
        help='Songsterr song URL (e.g., https://www.songsterr.com/a/wsa/artist-song-tab-s12345)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: ./<artist>_<song>/)',
        default=None
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window (useful for debugging)'
    )
    parser.add_argument(
        '--pdf',
        action='store_true',
        help='Generate PDF tablature files'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose debug output'
    )
    
    args = parser.parse_args()
    
    if args.pdf:
        ensure_packages(include_pdf=True)
    
    if not validate_url(args.url):
        print("Invalid URL. Expected: https://www.songsterr.com/a/wsa/<artist>-<song>-tab-s<id>")
        sys.exit(1)
    
    downloader = SongsterrDownloader(
        headless=not args.no_headless,
        verbose=args.verbose,
        generate_pdf=args.pdf
    )
    
    result = downloader.download(args.url, args.output)
    
    if result['success']:
        sys.exit(0)
    else:
        print("Download failed")
        if args.verbose:
            for error in result['errors']:
                print(f"  {error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
