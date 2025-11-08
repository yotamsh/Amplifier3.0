"""
Song Library - Runtime song management for the game system
"""

import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

try:
    import eyed3
    # Suppress eyed3 logging noise
    eyed3.log.setLevel("ERROR")
except ImportError:
    eyed3 = None

from .collections import Collection, Schedule, ALL_COLLECTIONS


class SongLibrary:
    """
    Runtime song library for managing audio collections and code-based song access.
    
    Provides methods for:
    - Getting songs by 5-digit codes
    - Getting random songs from current active collections
    - Validating codes
    - Updating available collections based on schedule
    """
    
    def __init__(self, songs_folder: str, schedule: Schedule, logger):
        """
        Initialize song library with validation and collection loading.
        
        Args:
            songs_folder: Path to songs directory
            schedule: Schedule instance for time-based collection management
            logger: ClassLogger instance for logging
        """
        self.songs_folder = songs_folder
        self.schedule = schedule
        self.logger = logger
        
        # Current active collections and song basket
        self.current_collections: Set[Collection] = set()
        self.current_songs_basket: List[str] = []
        
        # Code to filepath mapping
        self.codes_dict: Dict[str, str] = {}
        
        # Initialize the system
        self._initialize_system()
    
    def _initialize_system(self) -> None:
        """Initialize collections discovery, code dictionary, and schedule"""
        # Load code dictionary from ID3 tags
        self._create_codes_dict()
        
        # Initialize collection schedule
        self.update_collection_schedule(datetime.now())
    
    def _create_codes_dict(self) -> None:
        """
        Create mapping from codes to song file paths by reading ID3 tags.
        
        Logs warnings for missing collections and duplicate codes.
        """
        self.logger.info("Creating song codes dictionary")
        
        if eyed3 is None:
            self.logger.error("eyed3 library not available - cannot load song codes")
            return
        
        # Process all hardcoded collections
        for collection in ALL_COLLECTIONS:
            collection_path = os.path.join(self.songs_folder, collection.value)
            
            if not os.path.exists(collection_path):
                self.logger.warning(f"Collection folder not found: {collection_path}")
                continue
                
            self.logger.debug(f"Processing collection: {collection.name}")
            
            try:
                for filename in os.listdir(collection_path):
                    if not filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
                        continue
                        
                    song_path = os.path.join(collection_path, filename)
                    
                    try:
                        audio_file = eyed3.load(song_path)
                        if not audio_file or not audio_file.tag:
                            continue
                            
                        code = str(audio_file.tag.album) if audio_file.tag.album else None
                        
                        if self._is_valid_code(code):
                            if code in self.codes_dict:
                                self.logger.error(
                                    f"Duplicate code {code} found: '{song_path}' conflicts with '{self.codes_dict[code]}'"
                                )
                            else:
                                self.codes_dict[code] = song_path
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to process song {song_path}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Failed to process collection {collection.value}: {e}")
        
        self.logger.info(f"Loaded {len(self.codes_dict)} song codes from {len(ALL_COLLECTIONS)} collections")
    
    def _is_valid_code(self, code: Optional[str]) -> bool:
        """
        Validate that a code meets the 5-digit requirements.
        
        Args:
            code: Code string to validate
            
        Returns:
            True if code is valid (5 digits, not starting with 0)
        """
        return (
            code is not None and
            isinstance(code, str) and
            len(code) == 5 and
            code.isdigit() and
            code[0] != '0'
        )
    
    def update_collection_schedule(self, current_time: datetime) -> None:
        """
        Update available collections based on schedule.
        
        Args:
            current_time: Current datetime for schedule evaluation
        """
        new_collections = self.schedule.get_collections_by_time(current_time)
        
        if new_collections != self.current_collections:
            self.current_collections = new_collections
            self.logger.info(f"Collections updated: {[c.name for c in self.current_collections]}")
            
            # Rebuild songs basket
            self.current_songs_basket = []
            
            for collection in self.current_collections:
                collection_path = os.path.join(self.songs_folder, collection.value)
                
                if not os.path.exists(collection_path):
                    self.logger.warning(f"Skipping missing collection folder: {collection_path}")
                    continue
                
                try:
                    for filename in os.listdir(collection_path):
                        if filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
                            song_path = os.path.join(collection_path, filename)
                            self.current_songs_basket.append(song_path)
                            
                except Exception as e:
                    self.logger.warning(f"Failed to load songs from {collection_path}: {e}")
            
            self.logger.debug(f"Songs basket updated: {len(self.current_songs_basket)} songs available")
    
    def get_song_by_code(self, code: str) -> Optional[str]:
        """
        Get song file path for a given code.
        
        Args:
            code: 5-digit song code
            
        Returns:
            File path to song if code exists, None otherwise
        """
        return self.codes_dict.get(code)
    
    def get_random_song(self) -> Optional[str]:
        """
        Get a random song from currently available collections.
        
        Returns:
            Random song file path, or None if no songs available
        """
        if not self.current_songs_basket:
            self.logger.warning("No songs available in current collections")
            return None
            
        return random.choice(self.current_songs_basket)
    
    def is_code_supported(self, code: str) -> bool:
        """
        Check if a code exists in the song library.
        
        Args:
            code: 5-digit code to check
            
        Returns:
            True if code exists in library
        """
        return code in self.codes_dict
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get library statistics for debugging.
        
        Returns:
            Dictionary with library statistics including:
            - songs_folder: Path to songs directory
            - all_collections: Names of all available collections
            - total_codes: Number of loaded song codes
            - daily_schedule_entries: Number of daily schedule entries
            - special_schedule_entries: Number of special schedule entries
        """
        return {
            "songs_folder": self.songs_folder,
            "all_collections": [c.name for c in ALL_COLLECTIONS],
            "total_codes": len(self.codes_dict),
            "daily_schedule_entries": len(self.schedule.daily_schedule),
            "special_schedule_entries": len(self.schedule.special_schedule)
        }
