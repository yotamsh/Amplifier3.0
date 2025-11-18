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

from .audio_collections import AudioCollection, Schedule, ALL_COLLECTIONS
from utils import OnceInMs


class SongLibrary:
    """
    Runtime song library for managing audio collections and code-based song access.
    
    Provides methods for:
    - Getting songs by 5-digit codes
    - Getting random songs from current active collections
    - Validating codes
    - Updating available collections based on schedule
    """
    
    def __init__(self, songs_folder: str, schedule: Schedule, code_length: int, logger):
        """
        Initialize song library with strict validation and collection loading.
        
        Args:
            songs_folder: Path to songs directory
            schedule: Schedule instance for time-based collection management (already validated)
            code_length: Required length of song codes (e.g., 3 for testing, 5 for production)
            logger: ClassLogger instance for logging
            
        Raises:
            ImportError: If eyed3 library not available
            FileNotFoundError: If songs folder doesn't exist
            ValueError: If no songs are available after initialization
        """
        # Validate critical dependencies first
        if eyed3 is None:
            raise ImportError(
                "eyed3 library not available - required for song code management. "
                "Install with: pip install eyed3"
            )
            
        if not os.path.exists(songs_folder):
            raise FileNotFoundError(f"Songs folder not found: {songs_folder}")
        
        self.songs_folder = songs_folder
        self.schedule = schedule  # Pre-validated by caller
        self.code_length = code_length
        self.logger = logger
        
        # Current active collections and song basket
        self.current_collections: Set[AudioCollection] = set()
        self.current_songs_basket: List[str] = []
        
        # Code to filepath mapping
        self.codes_dict: Dict[str, str] = {}
        
        # Schedule updater - check once per minute
        self._schedule_updater = OnceInMs(60000)
        
        # Initialize the system with validation
        self._initialize_system()
        
        # Validate that we have songs available
        self._validate_songs_available()
    
    # ============================================================================
    # PUBLIC METHODS
    # ============================================================================
    
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
                
                # Collection folders already validated by Schedule, but double-check for safety
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
    
    def update_schedule_if_needed(self) -> None:
        """
        Update collection schedule if enough time has passed.
        
        Checks schedule at most once per minute. Call this from game loop
        to automatically update available collections based on time of day.
        
        This method is safe to call every frame - it internally throttles
        the actual schedule update to once per minute.
        """
        if self._schedule_updater.should_execute():
            self.update_collection_schedule(datetime.now())
    
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
    
    # ============================================================================
    # PRIVATE METHODS
    # ============================================================================
    
    def _initialize_system(self) -> None:
        """Initialize code dictionary and collection schedule"""
        # Load code dictionary from ID3 tags (eyed3 guaranteed available)
        self._create_codes_dict()
        
        # Initialize collection schedule using throttled method
        # This ensures we don't update twice on initialization
        self.update_schedule_if_needed()
    
    def _validate_songs_available(self) -> None:
        """
        Validate that songs are available after initialization.
        
        Raises:
            ValueError: If no songs available in any collections
        """
        if not self.current_songs_basket:
            available_collections = [c.name for c in self.current_collections]
            raise ValueError(
                f"No songs available in current collections: {available_collections}. "
                f"Add audio files to collection folders or check schedule configuration."
            )
    
    def _create_codes_dict(self) -> None:
        """
        Create mapping from codes to song file paths by reading ID3 tags.
        
        Logs warnings for missing collections and duplicate codes.
        eyed3 availability already validated in __init__.
        """
        self.logger.info("Creating song codes dictionary")
        
        # Process all hardcoded collections (folders already validated by Schedule)
        for collection in ALL_COLLECTIONS:
            collection_path = os.path.join(self.songs_folder, collection.value)
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
        Validate that a code meets the required digit length requirements.
        
        Args:
            code: Code string to validate
            
        Returns:
            True if code is valid (self.code_length digits, not starting with 0)
        """
        return (
            code is not None and
            isinstance(code, str) and
            len(code) == self.code_length and
            code.isdigit() and
            code[0] != '0'
        )
