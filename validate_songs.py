#!/usr/bin/env python3
"""
Song Validation Script - Finds corrupted audio files in the songs directory.

This script tests loading each audio file with pygame to detect corrupted files
that would cause playback errors in the HumanAmplifier system.

Usage:
    python validate_songs.py
    
    Or with options:
    python validate_songs.py --delete-corrupted  # Delete corrupted files automatically
    python validate_songs.py --verbose           # Show all files (valid and corrupted)
    python validate_songs.py --test-playback     # Test actual playback, not just loading
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Tuple

try:
    import pygame
except ImportError:
    print("❌ Error: pygame not installed")
    print("Install with: pip install pygame")
    sys.exit(1)


class SongValidator:
    """Validates audio files in the songs directory"""
    
    def __init__(self, songs_folder: str = "songs", verbose: bool = False, test_playback: bool = False):
        """
        Initialize song validator.
        
        Args:
            songs_folder: Path to songs directory
            verbose: If True, print all files (including valid ones)
            test_playback: If True, test actual playback (not just loading)
        """
        self.songs_folder = songs_folder
        self.verbose = verbose
        self.test_playback = test_playback
        self.valid_songs: List[str] = []
        self.corrupted_songs: List[Tuple[str, str]] = []  # (path, error)
        
        # Initialize pygame mixer
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.init()
    
    def validate_all_songs(self) -> None:
        """Scan all audio files in songs directory and validate them"""
        if not os.path.exists(self.songs_folder):
            print(f"❌ Error: Songs folder not found: {self.songs_folder}")
            sys.exit(1)
        
        test_mode = "load + playback test" if self.test_playback else "load only"
        print(f"🔍 Scanning songs in '{self.songs_folder}/' (mode: {test_mode})...\n")
        
        # Check if this folder contains audio files directly
        audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg')
        audio_files = [f for f in os.listdir(self.songs_folder) 
                      if os.path.isfile(os.path.join(self.songs_folder, f)) and 
                      f.lower().endswith(audio_extensions)]
        
        if audio_files:
            # This is a single collection folder with audio files
            print(f"📂 Validating collection folder directly\n")
            self._validate_single_folder(self.songs_folder)
        else:
            # This is a parent folder containing collection subfolders
            collections = [d for d in os.listdir(self.songs_folder) 
                          if os.path.isdir(os.path.join(self.songs_folder, d))]
            
            if not collections:
                print(f"⚠️  No audio files or collection folders found in '{self.songs_folder}/'")
                return
            
            print(f"📁 Found {len(collections)} collection folders\n")
            
            # Validate each collection
            for collection in sorted(collections):
                self._validate_collection(collection)
        
        # Print summary
        self._print_summary()
    
    def _validate_single_folder(self, folder_path: str) -> None:
        """Validate all songs directly in a folder (not a collection parent)"""
        audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg')
        files = [f for f in os.listdir(folder_path) 
                if f.lower().endswith(audio_extensions)]
        
        if not files:
            print(f"   ⚠️  No audio files found\n")
            return
        
        collection_corrupted = 0
        
        for filename in sorted(files):
            song_path = os.path.join(folder_path, filename)
            is_valid, error = self._validate_song(song_path)
            
            if is_valid:
                self.valid_songs.append(song_path)
                if self.verbose:
                    print(f"   ✅ {filename}")
            else:
                self.corrupted_songs.append((song_path, error))
                collection_corrupted += 1
                print(f"   ❌ {filename}")
                print(f"      Error: {error}")
        
        # Summary
        valid_count = len(files) - collection_corrupted
        print(f"   Summary: {valid_count}/{len(files)} valid\n")
    
    def _validate_collection(self, collection: str) -> None:
        """Validate all songs in a single collection folder"""
        collection_path = os.path.join(self.songs_folder, collection)
        
        print(f"📂 Collection: {collection}")
        
        # Use the single folder validator
        self._validate_single_folder(collection_path)
    
    def _validate_song(self, song_path: str) -> Tuple[bool, str]:
        """
        Test if a song file can be loaded (and optionally played).
        
        Args:
            song_path: Path to audio file
            
        Returns:
            (is_valid, error_message) tuple
        """
        # Test loading
        try:
            pygame.mixer.music.load(song_path)
        except pygame.error as e:
            return (False, f"Load failed: {e}")
        except Exception as e:
            return (False, f"Load failed ({type(e).__name__}): {e}")
        
        # If test_playback is enabled, also test actual playback
        if self.test_playback:
            try:
                # Play the song
                pygame.mixer.music.play()
                
                # Wait 1 second to catch files that start but fail quickly
                # (some corrupted files play briefly then crash)
                start_time = time.time()
                time.sleep(0.1)  # Initial wait
                
                # Check multiple times over 1 second to catch early failures
                for _ in range(9):  # 9 more checks = total 1 second
                    elapsed = time.time() - start_time
                    
                    # Check if still playing
                    if not pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                        return (False, f"Playing failed: Song stopped after {elapsed:.1f}s (likely corrupted)")
                    
                    time.sleep(0.1)  # Wait 100ms between checks
                
                # Song played for 1+ second successfully
                pygame.mixer.music.stop()
                
            except pygame.error as e:
                pygame.mixer.music.stop()
                return (False, f"Playing failed: {e}")
            except Exception as e:
                pygame.mixer.music.stop()
                return (False, f"Playing failed ({type(e).__name__}): {e}")
        
        return (True, "")
    
    def _print_summary(self) -> None:
        """Print validation summary"""
        total = len(self.valid_songs) + len(self.corrupted_songs)
        
        print("=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Total songs scanned:  {total}")
        print(f"✅ Valid songs:       {len(self.valid_songs)} ({len(self.valid_songs)/total*100:.1f}%)")
        print(f"❌ Corrupted songs:   {len(self.corrupted_songs)} ({len(self.corrupted_songs)/total*100:.1f}%)")
        print()
        
        if self.corrupted_songs:
            print("🗑️  CORRUPTED FILES TO REMOVE:")
            print("-" * 70)
            for song_path, error in self.corrupted_songs:
                print(f"  {song_path}")
            print()
    
    def delete_corrupted_songs(self) -> None:
        """Delete all corrupted song files"""
        if not self.corrupted_songs:
            print("✅ No corrupted songs to delete")
            return
        
        print(f"🗑️  Deleting {len(self.corrupted_songs)} corrupted files...\n")
        
        deleted = 0
        failed = 0
        
        for song_path, _ in self.corrupted_songs:
            try:
                os.remove(song_path)
                deleted += 1
                print(f"  ✅ Deleted: {song_path}")
            except Exception as e:
                failed += 1
                print(f"  ❌ Failed to delete {song_path}: {e}")
        
        print()
        print(f"Summary: {deleted} deleted, {failed} failed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate audio files in the songs directory",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--delete-corrupted',
        action='store_true',
        help='Automatically delete corrupted files'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show all files including valid ones'
    )
    parser.add_argument(
        '--test-playback',
        action='store_true',
        help='Test actual playback (not just loading) - more thorough but slower'
    )
    parser.add_argument(
        '--songs-folder',
        default='songs',
        help='Path to songs directory (default: songs)'
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = SongValidator(
        songs_folder=args.songs_folder,
        verbose=args.verbose,
        test_playback=args.test_playback
    )
    
    # Run validation
    validator.validate_all_songs()
    
    # Delete corrupted files if requested
    if args.delete_corrupted and validator.corrupted_songs:
        print()
        response = input("⚠️  Delete all corrupted files? [y/N]: ").strip().lower()
        if response == 'y':
            validator.delete_corrupted_songs()
        else:
            print("Deletion cancelled")


if __name__ == "__main__":
    main()

