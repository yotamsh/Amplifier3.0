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
"""

import os
import sys
import argparse
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
    
    def __init__(self, songs_folder: str = "songs", verbose: bool = False):
        """
        Initialize song validator.
        
        Args:
            songs_folder: Path to songs directory
            verbose: If True, print all files (including valid ones)
        """
        self.songs_folder = songs_folder
        self.verbose = verbose
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
        
        print(f"🔍 Scanning songs in '{self.songs_folder}/'...\n")
        
        # Get all collection folders
        collections = [d for d in os.listdir(self.songs_folder) 
                      if os.path.isdir(os.path.join(self.songs_folder, d))]
        
        if not collections:
            print(f"⚠️  No collection folders found in '{self.songs_folder}/'")
            return
        
        print(f"📁 Found {len(collections)} collection folders\n")
        
        # Validate each collection
        for collection in sorted(collections):
            self._validate_collection(collection)
        
        # Print summary
        self._print_summary()
    
    def _validate_collection(self, collection: str) -> None:
        """Validate all songs in a single collection folder"""
        collection_path = os.path.join(self.songs_folder, collection)
        
        print(f"📂 Collection: {collection}")
        
        # Get all audio files
        audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg')
        files = [f for f in os.listdir(collection_path) 
                if f.lower().endswith(audio_extensions)]
        
        if not files:
            print(f"   ⚠️  No audio files found\n")
            return
        
        collection_corrupted = 0
        
        for filename in sorted(files):
            song_path = os.path.join(collection_path, filename)
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
        
        # Collection summary
        valid_count = len(files) - collection_corrupted
        print(f"   Summary: {valid_count}/{len(files)} valid\n")
    
    def _validate_song(self, song_path: str) -> Tuple[bool, str]:
        """
        Test if a song file can be loaded.
        
        Args:
            song_path: Path to audio file
            
        Returns:
            (is_valid, error_message) tuple
        """
        try:
            pygame.mixer.music.load(song_path)
            return (True, "")
        except pygame.error as e:
            return (False, str(e))
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")
    
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
        '--songs-folder',
        default='songs',
        help='Path to songs directory (default: songs)'
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = SongValidator(
        songs_folder=args.songs_folder,
        verbose=args.verbose
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

