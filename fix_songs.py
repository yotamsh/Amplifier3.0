#!/usr/bin/env python3
"""
Song Repair Script - Re-encodes problematic audio files for pygame compatibility.

This script identifies audio files that pygame can't load and re-encodes them using
ffmpeg to a more compatible format (CBR, standard encoding, cleaned tags).

Requires: ffmpeg (install with: brew install ffmpeg)

Usage:
    python fix_songs.py                              # Scan all songs
    python fix_songs.py --file path/to/song.mp3 --fix  # Fix single file
    python fix_songs.py --folder songs/classic --fix   # Fix folder
    python fix_songs.py --fix-all                      # Fix all problematic files
    python fix_songs.py --verbose                      # Show all files
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict

try:
    import pygame
except ImportError:
    print("❌ Error: pygame not installed")
    print("Install with: pip install pygame")
    sys.exit(1)

try:
    import eyed3
    eyed3.log.setLevel("ERROR")
except ImportError:
    print("⚠️  Warning: eyed3 not installed - ID3 tag preservation disabled")
    eyed3 = None


class SongRepairer:
    """Re-encodes problematic audio files for pygame compatibility"""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize song repairer.
        
        Args:
            verbose: If True, print all files (including valid ones)
        """
        self.verbose = verbose
        self.problematic_songs: List[Tuple[str, str]] = []  # (path, error)
        
        # Initialize pygame mixer
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.init()
        
        # Check ffmpeg/ffprobe availability
        if not self._check_ffmpeg():
            print("❌ Error: ffmpeg/ffprobe not found")
            print("Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
            sys.exit(1)
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg and ffprobe are available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _detect_actual_format(self, file_path: str) -> Optional[Dict]:
        """
        Detect actual audio format using ffprobe (not just extension).
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with format info, or None if detection failed
        """
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                 '-show_format', '-show_streams', file_path],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data
            return None
        except Exception:
            return None
    
    def scan_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Test if a single audio file can be loaded by pygame.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            (is_valid, error_or_format_info) tuple
        """
        filename = os.path.basename(file_path)
        
        # First, detect actual format
        format_info = self._detect_actual_format(file_path)
        if format_info:
            format_name = format_info.get('format', {}).get('format_name', 'unknown')
            if self.verbose:
                print(f"🔍 Detected format: {format_name}")
        
        # Try to load with pygame
        try:
            pygame.mixer.music.load(file_path)
            return (True, "")
        except pygame.error as e:
            error_msg = str(e)
            
            # Enhance error message with format detection
            if format_info:
                format_name = format_info.get('format', {}).get('format_name', 'unknown')
                codec_name = 'unknown'
                if 'streams' in format_info and format_info['streams']:
                    codec_name = format_info['streams'][0].get('codec_name', 'unknown')
                
                error_msg = f"{error_msg} [Detected: {format_name}/{codec_name}]"
            
            return (False, error_msg)
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")
    
    def scan_folder(self, folder_path: str) -> None:
        """Scan all audio files in a folder"""
        if not os.path.exists(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            return
        
        print(f"🔍 Scanning folder: {folder_path}")
        
        audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg')
        files = [f for f in os.listdir(folder_path) 
                if f.lower().endswith(audio_extensions)]
        
        if not files:
            print(f"  ⚠️  No audio files found")
            return
        
        problematic_count = 0
        
        for filename in sorted(files):
            file_path = os.path.join(folder_path, filename)
            is_valid, error = self.scan_file(file_path)
            
            if is_valid:
                if self.verbose:
                    print(f"  ✅ {filename}")
            else:
                problematic_count += 1
                self.problematic_songs.append((file_path, error))
                print(f"  ❌ {filename}")
                print(f"     Issue: {error}")
        
        print(f"  Summary: {len(files) - problematic_count}/{len(files)} valid\n")
    
    def scan_all_collections(self, songs_folder: str = "songs") -> None:
        """Scan all songs in all collection folders"""
        if not os.path.exists(songs_folder):
            print(f"❌ Error: Songs folder not found: {songs_folder}")
            sys.exit(1)
        
        print(f"🔍 Scanning all songs in '{songs_folder}/'...\n")
        
        collections = [d for d in os.listdir(songs_folder) 
                      if os.path.isdir(os.path.join(songs_folder, d))]
        
        if not collections:
            print(f"⚠️  No collection folders found")
            return
        
        print(f"📁 Found {len(collections)} collection folders\n")
        
        for collection in sorted(collections):
            collection_path = os.path.join(songs_folder, collection)
            self.scan_folder(collection_path)
        
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print scan summary"""
        print("=" * 70)
        print("📊 SCAN SUMMARY")
        print("=" * 70)
        print(f"Problematic songs found: {len(self.problematic_songs)}")
        
        if self.problematic_songs:
            print("\n🔧 FILES THAT NEED REPAIR:")
            print("-" * 70)
            for song_path, error in self.problematic_songs:
                print(f"  {song_path}")
                print(f"     Issue: {error[:100]}...")
            print()
    
    def fix_file(self, file_path: str) -> bool:
        """
        Re-encode a single audio file for pygame compatibility.
        
        Strategy:
        - Convert to CBR (Constant Bitrate) MP3
        - Use standard LAME encoder settings
        - Preserve ID3 tags (title, artist, album/code)
        - Overwrite original file (no backup)
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if fixed successfully
        """
        filename = os.path.basename(file_path)
        print(f"🔧 Fixing: {filename}")
        
        # Read original ID3 tags if available
        original_tags = None
        if eyed3:
            try:
                audio_file = eyed3.load(file_path)
                if audio_file and audio_file.tag:
                    original_tags = {
                        'title': audio_file.tag.title,
                        'artist': audio_file.tag.artist,
                        'album': audio_file.tag.album  # This is our song code!
                    }
                    print(f"   📝 Preserving tags (code: {original_tags['album']})")
            except Exception:
                pass
        
        # Create temporary output path
        temp_path = file_path + ".tmp.mp3"
        
        # Re-encode with ffmpeg (CBR, high quality, pygame-compatible)
        # Use error concealment for corrupted files
        ffmpeg_cmd = [
            'ffmpeg',
            '-err_detect', 'ignore_err',  # Ignore decoding errors
            '-i', file_path,              # Input file
            '-y',                          # Overwrite output
            '-acodec', 'libmp3lame',      # MP3 encoder
            '-b:a', '320k',               # 320kbps CBR (high quality)
            '-ar', '44100',               # 44.1kHz sample rate
            '-ac', '2',                   # Stereo
            '-write_xing', '0',           # Disable VBR header (force CBR)
            '-id3v2_version', '3',        # Use ID3v2.3 (more compatible)
            '-loglevel', 'warning',       # Show warnings but continue
            temp_path
        ]
        
        try:
            # Run ffmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode()[:200]
                print(f"   ❌ ffmpeg failed: {error_msg}")
                
                # Try alternative method for severely corrupted files
                print(f"   🔄 Retrying with aggressive error recovery...")
                
                # Alternative command with even more aggressive error handling
                alt_cmd = [
                    'ffmpeg',
                    '-fflags', '+discardcorrupt',  # Discard corrupted packets
                    '-err_detect', 'ignore_err',   # Ignore all errors
                    '-max_error_rate', '1.0',      # Allow 100% error rate
                    '-i', file_path,
                    '-y',
                    '-acodec', 'libmp3lame',
                    '-b:a', '320k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-write_xing', '0',
                    '-id3v2_version', '3',
                    '-loglevel', 'fatal',  # Only fatal errors
                    temp_path
                ]
                
                result = subprocess.run(alt_cmd, capture_output=True, timeout=60)
                
                if result.returncode != 0:
                    print(f"   ❌ Alternative method also failed")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return False
                
                print(f"   ⚠️  Recovered with data loss (some audio may be affected)")
            
            # Verify the new file loads in pygame
            try:
                pygame.mixer.music.load(temp_path)
            except pygame.error as e:
                print(f"   ❌ Fixed file still doesn't load: {e}")
                os.remove(temp_path)
                return False
            
            # Restore ID3 tags if we saved them
            if eyed3 and original_tags:
                try:
                    audio_file = eyed3.load(temp_path)
                    if not audio_file.tag:
                        audio_file.initTag()
                    
                    audio_file.tag.title = original_tags['title']
                    audio_file.tag.artist = original_tags['artist']
                    audio_file.tag.album = original_tags['album']  # Preserve code!
                    audio_file.tag.save()
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not restore ID3 tags: {e}")
            
            # Replace original with fixed version (no backup)
            os.replace(temp_path, file_path)
            
            print(f"   ✅ Fixed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            print(f"   ❌ ffmpeg timeout")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
    
    def fix_all_problematic(self) -> None:
        """Re-encode all problematic songs"""
        if not self.problematic_songs:
            print("✅ No problematic songs to fix")
            return
        
        print(f"🔧 Fixing {len(self.problematic_songs)} problematic files...\n")
        
        fixed = 0
        failed = 0
        
        for song_path, _ in self.problematic_songs:
            if self.fix_file(song_path):
                fixed += 1
            else:
                failed += 1
            print()  # Blank line between files
        
        print("=" * 70)
        print(f"✅ Fixed: {fixed} files")
        print(f"❌ Failed: {failed} files")
        print("=" * 70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Fix audio files that pygame can't load",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--file',
        help='Fix a single file'
    )
    parser.add_argument(
        '--folder',
        help='Scan/fix all files in a specific folder'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Fix the specified file or folder (use with --file or --folder)'
    )
    parser.add_argument(
        '--fix-all',
        action='store_true',
        help='Automatically fix all problematic files found'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show all files including valid ones'
    )
    parser.add_argument(
        '--songs-folder',
        default='songs',
        help='Path to songs directory (default: songs)'
    )
    
    args = parser.parse_args()
    
    # Create repairer
    repairer = SongRepairer(verbose=args.verbose)
    
    # Single file mode
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        
        is_valid, error = repairer.scan_file(args.file)
        
        if is_valid:
            print(f"✅ {args.file} - Already valid")
        else:
            print(f"❌ {args.file}")
            print(f"   Issue: {error}")
            
            if args.fix:
                print()
                repairer.fix_file(args.file)
        
        return
    
    # Folder mode
    if args.folder:
        repairer.scan_folder(args.folder)
        
        if args.fix and repairer.problematic_songs:
            print()
            repairer.fix_all_problematic()
        
        return
    
    # Scan all collections
    repairer.scan_all_collections(args.songs_folder)
    
    # Fix if requested
    if args.fix_all and repairer.problematic_songs:
        print()
        response = input("⚠️  Fix all problematic files? This will OVERWRITE originals [y/N]: ").strip().lower()
        if response == 'y':
            repairer.fix_all_problematic()
        else:
            print("Fix cancelled")


if __name__ == "__main__":
    main()

