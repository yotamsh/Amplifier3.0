#!/usr/bin/env python3
"""
Code Generator - CLI utility for managing song codes in ID3 tags
"""

import csv
import os
import random
from typing import Set

try:
    import eyed3
    # Suppress eyed3 logging noise for CLI usage
    eyed3.log.setLevel("ERROR")
except ImportError:
    eyed3 = None

from .collections import Collection


class CodeGeneratorHelper:
    """
    Static helper class for generating and managing song codes.
    
    Provides CLI functionality to:
    - Generate missing 5-digit codes for songs
    - Update ID3 album tags with codes  
    - Create CSV database of all songs and codes
    - Avoid duplicate codes and preserve existing ones
    """
    
    CODE_LENGTH = 5
    
    @staticmethod
    def generate_missing_codes(songs_folder: str = "songs", 
                              csv_output_path: str = "AmplifierSongCodes.csv") -> None:
        """
        Generate codes for songs missing them and create CSV database.
        
        Process:
        1. Scan all audio files to collect existing codes
        2. Generate new unique codes for files without valid codes
        3. Update ID3 album tags with new codes
        4. Create/overwrite CSV database with all songs
        
        Args:
            songs_folder: Path to songs directory
            csv_output_path: Path for CSV output file
        """
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
        
        # Discover collections
        Collection.initialize_discovered_folders(songs_folder)
        discovered_collections = Collection.get_all_discovered()
        
        if not discovered_collections:
            print("⚠️  No valid collection folders found")
            return
        
        print(f"📂 Found collections: {[c.name for c in discovered_collections]}")
        print()
        
        # Statistics tracking
        num_new_songs = 0
        num_collides = 0
        num_errors = 0
        existing_codes: Set[str] = set()
        
        # Create CSV file
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Collection", "Song Name", "Code"])
            
            # Phase 1: Collect all existing codes
            print("🔍 Phase 1: Scanning existing codes...")
            for collection in discovered_collections:
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
                                    print(f"\n    ❌ Error: Duplicate code '{existing_code}' in {song_path}")
                                else:
                                    existing_codes.add(existing_code)
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
            for collection in discovered_collections:
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
                                existing_codes.add(new_code)
                                audio_file.tag.save(version=eyed3.id3.tag.ID3_V2_3)
                                
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
    
    print("🎵 Amp3 Song Code Generator")
    print("=" * 40)
    
    # Simple CLI interface (can be enhanced later with argparse)
    songs_folder = "songs"
    csv_output = "AmplifierSongCodes.csv"
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        songs_folder = sys.argv[1]
    if len(sys.argv) > 2:
        csv_output = sys.argv[2]
    
    try:
        CodeGeneratorHelper.generate_missing_codes(songs_folder, csv_output)
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
