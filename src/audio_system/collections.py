"""
Collections and Schedule management for the audio system
"""

import os
from datetime import datetime, time
from dataclasses import dataclass
from enum import Enum
from typing import Set, List, Optional


class Collection(Enum):
    """
    Audio collections - each corresponds to a folder in the songs directory.
    
    Manual definitions allow these to be referenced in schedules.
    """
    GENERAL = "general"
    MORNING = "morning"
    PARTY = "party"
    TV = "tv"
    CLASSIC = "classic"
    DISNEY = "disney"
    
    # Class variable to hold discovered folders (set during initialization)
    _discovered_folders: Set[str] = set()
    
    @classmethod
    def initialize_discovered_folders(cls, songs_folder: str) -> None:
        """
        Discover and store all folders in songs directory.
        
        Args:
            songs_folder: Path to songs directory
        """
        if not os.path.exists(songs_folder):
            cls._discovered_folders = set()
            return
            
        cls._discovered_folders = {
            name for name in os.listdir(songs_folder) 
            if os.path.isdir(os.path.join(songs_folder, name))
        }
    
    @classmethod
    def get_all_discovered(cls) -> Set['Collection']:
        """
        Return all enum values that match discovered folders.
        
        Returns:
            Set of Collection enums that have matching folders
        """
        return {
            collection for collection in cls 
            if collection.value in cls._discovered_folders
        }
    
    @classmethod
    def get_discovered_folder_names(cls) -> Set[str]:
        """
        Get the raw discovered folder names.
        
        Returns:
            Set of folder names found in songs directory
        """
        return cls._discovered_folders.copy()


@dataclass
class DailyScheduleEntry:
    """Entry in the daily schedule defining which collections are available at a specific time"""
    time: time
    collections: Set[Collection]


@dataclass
class SpecialScheduleEntry:
    """Special schedule entry for specific date/time ranges"""
    start: datetime
    end: datetime
    collections: Set[Collection]


class Schedule:
    """
    Time-based schedule for determining which audio collections are available.
    
    Supports both daily recurring schedules and special one-time overrides.
    """
    
    def __init__(self, daily_schedule: List[DailyScheduleEntry], 
                 special_schedule: Optional[List[SpecialScheduleEntry]] = None):
        """
        Initialize schedule with validation.
        
        Args:
            daily_schedule: List of daily recurring schedule entries
            special_schedule: Optional list of special date-specific entries
        """
        self.daily_schedule = daily_schedule or []
        self.special_schedule = special_schedule or []
        self._validate_schedule()
    
    def _validate_schedule(self) -> None:
        """
        Validate that all collections in schedule exist in discovered folders.
        
        This validation happens after Collection.initialize_discovered_folders() is called.
        """
        discovered = Collection.get_discovered_folder_names()
        
        # Check daily schedule
        for entry in self.daily_schedule:
            for collection in entry.collections:
                if collection.value not in discovered:
                    print(f"⚠️  Warning: Collection '{collection.value}' in daily schedule not found in songs folder")
        
        # Check special schedule  
        for entry in self.special_schedule:
            for collection in entry.collections:
                if collection.value not in discovered:
                    print(f"⚠️  Warning: Collection '{collection.value}' in special schedule not found in songs folder")
    
    def get_collections_by_time(self, current_time: datetime) -> Set[Collection]:
        """
        Get available collections for the given time.
        
        Special schedule entries take priority over daily schedule.
        
        Args:
            current_time: The datetime to check
            
        Returns:
            Set of available Collection enums
        """
        # First check special schedule (takes priority)
        for special_entry in self.special_schedule:
            if special_entry.start <= current_time <= special_entry.end:
                return special_entry.collections
        
        # Fall back to daily schedule
        if not self.daily_schedule:
            return set()
        
        # Find the active daily schedule entry
        schedule_index = 0
        current_time_only = current_time.time()
        
        # Find the latest schedule entry that's still before current time
        while (schedule_index < len(self.daily_schedule) - 1 and 
               current_time_only >= self.daily_schedule[schedule_index + 1].time):
            schedule_index += 1
        
        return self.daily_schedule[schedule_index].collections
