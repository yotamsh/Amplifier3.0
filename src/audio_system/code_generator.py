#!/usr/bin/env python3
"""
Code Generator - CLI utility for managing song codes in ID3 tags
"""

import csv
import os
import sys
import random
from pathlib import Path
from typing import Set

# Add src to path for imports (needed when running as script)
_src_path = Path(__file__).parent.parent
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

try:
    import eyed3
    # Suppress eyed3 logging noise for CLI usage
    eyed3.log.setLevel("ERROR")
except ImportError:
    eyed3 = None

# Direct imports to avoid loading pygame-dependent modules from __init__.py
import importlib.util
import sys

# Load audio_collections directly without triggering package __init__
collections_spec = importlib.util.spec_from_file_location(
    "audio_collections",
    Path(__file__).parent / "audio_collections.py"
)
collections_module = importlib.util.module_from_spec(collections_spec)
collections_spec.loader.exec_module(collections_module)

AudioCollection = collections_module.AudioCollection
ALL_COLLECTIONS = collections_module.ALL_COLLECTIONS

# Load config module (game_system doesn't have pygame dependencies)
from game_system.config import AudioConfig


class CodeGeneratorHelper:
    """
    Static helper class for generating and managing song codes.
    
    Provides CLI functionality to:
    - Generate missing 5-digit codes for songs
    - Update ID3 album tags with codes  
    - Create CSV database of all songs and codes
    - Avoid duplicate codes and preserve existing ones
    """
    
    CODE_LENGTH = 5  # Production code length (for generating new codes)
    
    @staticmethod
    def generate_missing_codes(audio_config: AudioConfig) -> None:
        """
        Generate codes for songs missing them and create CSV database.
        
        Process:
        1. Scan all audio files to collect existing codes
        2. Generate new unique codes for files without valid codes
        3. Update ID3 album tags with new codes
        4. Create/overwrite CSV database with all songs
        
        Args:
            audio_config: AudioConfig instance with songs_folder and csv_output_path
        """
        songs_folder = audio_config.songs_folder
        csv_output_path = audio_config.csv_output_path
        if eyed3 is None:
            print("❌ Error: eyed3 library not available")
            print("Install with: pip install eyed3")
            return
        
        if not os.path.exists(songs_folder):
            print(f"❌ Error: Songs folder not found: {songs_folder}")
            return
        
        print(f"🎵 Generating missing song codes...")
        print(f"📁 Songs folder: {songs_folder}")
        print(f"📄 CSV output: {csv_output_path}")
        print()
        
        # Use all hardcoded collections
        print(f"📂 Processing collections: {[c.name for c in ALL_COLLECTIONS]}")
        print()
        
        # Safety confirmation prompt
        print(f"⚠️  WARNING: This will keep only {CodeGeneratorHelper.CODE_LENGTH}-digit codes and override the rest!")
        response = input(f"ARE YOU SURE YOU WANT TO KEEP ONLY {CodeGeneratorHelper.CODE_LENGTH}-DIGIT CODES AND OVERRIDE THE REST FOR ALL SONGS? (y/n): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled by user")
            return
        print()
        
        # Statistics tracking
        num_new_songs = 0
        num_collides = 0
        num_errors = 0
        existing_codes: dict[str, str] = {}  # Maps code -> song_path for duplicate detection
        
        # Create CSV file
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Collection", "Song Name", "Code"])
            
            # Phase 1: Collect all existing codes
            print("🔍 Phase 1: Scanning existing codes...")
            for collection in ALL_COLLECTIONS:
                collection_path = os.path.join(songs_folder, collection.value)
                
                print(f"  Scanning {collection.name}...", end=" ", flush=True)
                collection_song_count = 0
                
                try:
                    for filename in os.listdir(collection_path):
                        if not CodeGeneratorHelper._is_audio_file(filename):
                            continue
                            
                        song_path = os.path.join(collection_path, filename)
                        
                        try:
                            audio_file = eyed3.load(song_path)
                            if not audio_file:
                                continue
                                
                            if not audio_file.tag:
                                audio_file.tag = eyed3.id3.tag.Tag()
                            
                            existing_code = audio_file.tag.album
                            
                            if CodeGeneratorHelper._is_valid_code(existing_code):
                                if existing_code in existing_codes:
                                    num_errors += 1
                                    original_song = existing_codes[existing_code]
                                    print(f"\n    ❌ Error: Duplicate code '{existing_code}'")
                                    print(f"       Song 1: {original_song}")
                                    print(f"       Song 2: {song_path}")
                                else:
                                    existing_codes[existing_code] = song_path
                                    writer.writerow([
                                        collection.name, 
                                        CodeGeneratorHelper._get_song_name(filename), 
                                        existing_code
                                    ])
                                    collection_song_count += 1
                        
                        except Exception as e:
                            print(f"\n    ⚠️  Failed to process {filename}: {e}")
                            
                except Exception as e:
                    print(f"\n  ❌ Failed to scan collection {collection.name}: {e}")
                    continue
                
                print(f"({collection_song_count} existing codes)")
            
            print()
            
            # Phase 2: Generate new codes
            print("🔧 Phase 2: Generating new codes...")
            for collection in ALL_COLLECTIONS:
                collection_path = os.path.join(songs_folder, collection.value)
                
                print(f"  Processing {collection.name}...", end=" ", flush=True)
                collection_new_count = 0
                
                try:
                    for filename in os.listdir(collection_path):
                        if not CodeGeneratorHelper._is_audio_file(filename):
                            continue
                            
                        song_path = os.path.join(collection_path, filename)
                        
                        try:
                            audio_file = eyed3.load(song_path)
                            if not audio_file:
                                continue
                                
                            if not audio_file.tag:
                                audio_file.tag = eyed3.id3.tag.Tag()
                            
                            existing_code = audio_file.tag.album
                            
                            if not CodeGeneratorHelper._is_valid_code(existing_code):
                                # Generate new unique code
                                num_new_songs += 1
                                new_code = CodeGeneratorHelper._generate_new_code()
                                
                                # Ensure uniqueness
                                while new_code in existing_codes:
                                    num_collides += 1
                                    new_code = CodeGeneratorHelper._generate_new_code()
                                
                                # Update ID3 tag
                                audio_file.tag.album = new_code
                                existing_codes[new_code] = song_path
                                audio_file.tag.save(version=eyed3.id3.tag.ID3_V2_3)
                                
                                # Update modification time to ensure rsync detects the change
                                os.utime(song_path, None)
                                
                                # Add to CSV
                                writer.writerow([
                                    collection.name,
                                    CodeGeneratorHelper._get_song_name(filename),
                                    new_code
                                ])
                                collection_new_count += 1
                        
                        except Exception as e:
                            print(f"\n    ⚠️  Failed to process {filename}: {e}")
                            
                except Exception as e:
                    print(f"\n  ❌ Failed to process collection {collection.name}: {e}")
                    continue
                
                print(f"({collection_new_count} new codes)")
        
        # Final statistics
        print()
        print("✅ Code generation complete!")
        print(f"📊 Statistics:")
        print(f"  • Total codes: {len(existing_codes)}")
        print(f"  • New songs: {num_new_songs}")
        print(f"  • Code collisions: {num_collides}")
        print(f"  • Errors: {num_errors}")
        print(f"  • CSV file: {csv_output_path}")
    
    @staticmethod
    def _is_audio_file(filename: str) -> bool:
        """Check if filename is an audio file"""
        return filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac'))
    
    @staticmethod
    def _get_song_name(file_path: str) -> str:
        """Extract song name from file path (remove extension)"""
        return os.path.splitext(os.path.basename(file_path))[0]
    
    @staticmethod
    def _generate_new_code() -> str:
        """
        Generate a numeric code with all different digits, not starting with '0'.
        
        Returns:
            5-digit code string
        """
        result = ""
        available_digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
        
        # First digit (can't be 0)
        first_digit = random.choice(available_digits)
        result += first_digit
        available_digits.remove(first_digit)
        available_digits.append('0')  # Now 0 is available for subsequent positions
        
        # Remaining digits
        for _ in range(CodeGeneratorHelper.CODE_LENGTH - 1):
            if not available_digits:
                break
            digit = random.choice(available_digits)
            result += digit
            available_digits.remove(digit)
        
        return result
    
    @staticmethod
    def _is_valid_code(code) -> bool:
        """
        Validate that a code meets requirements.
        
        Args:
            code: Code to validate
            
        Returns:
            True if code is valid (5 digits, not starting with 0)
        """
        return (
            code is not None and
            isinstance(code, str) and
            len(code) == CodeGeneratorHelper.CODE_LENGTH and
            code.isdigit() and
            code[0] != '0'
        )


# CLI Script Entry Point
if __name__ == "__main__":
    import sys
    
    print("🎵 HumanAmplifier Song Code Generator")
    print("=" * 45)
    
    # Simple CLI interface (can be enhanced later with argparse)
    audio_config = AudioConfig()  # Use default config
    
    # Check for command line arguments to override defaults
    if len(sys.argv) > 1:
        audio_config.songs_folder = sys.argv[1]
    if len(sys.argv) > 2:
        audio_config.csv_output_path = sys.argv[2]
    
    try:
        CodeGeneratorHelper.generate_missing_codes(audio_config)
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
