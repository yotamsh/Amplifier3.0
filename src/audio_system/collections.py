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
    
    Hardcoded collection definitions.
    """
    # GENERAL = "general"
    MORNING = "morning"
    # PARTY = "party"
    # TV = "tv"
    # CLASSIC = "classic"
    # DISNEY = "disney"
    SPANISH = "spanish"


# Constant with all collections
ALL_COLLECTIONS = set(Collection)


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
                 special_schedule: Optional[List[SpecialScheduleEntry]] = None,
                 songs_folder: str = "songs"):
        """
        Initialize schedule with validation.
        
        Args:
            daily_schedule: List of daily recurring schedule entries
            special_schedule: Optional list of special date-specific entries
            songs_folder: Path to songs directory for validation
        """
        self.daily_schedule = daily_schedule or []
        self.special_schedule = special_schedule or []
        self._validate_schedule(songs_folder)
    
    def _validate_schedule(self, songs_folder: str = "songs") -> None:
        """
        Validate schedule entries and collection folder existence.
        
        Validates (strict - raises exceptions for any issues):
        - Daily schedule times are monotonically increasing
        - Special schedule entries have start < end
        - All referenced collection folders exist in songs directory
        
        Args:
            songs_folder: Path to songs directory for validation
            
        Raises:
            ValueError: If schedule configuration is invalid
            FileNotFoundError: If referenced collection folders don't exist
        """
        # Validate daily schedule monotonic ordering
        for i in range(1, len(self.daily_schedule)):
            prev_time = self.daily_schedule[i-1].time
            curr_time = self.daily_schedule[i].time
            if prev_time >= curr_time:
                raise ValueError(
                    f"Daily schedule times must be monotonically increasing. "
                    f"Entry {i-1}: {prev_time} >= Entry {i}: {curr_time}"
                )
        
        # Validate special schedule start < end
        for i, entry in enumerate(self.special_schedule):
            if entry.start >= entry.end:
                raise ValueError(
                    f"Special schedule entry {i} has invalid time range: "
                    f"start {entry.start} >= end {entry.end}"
                )
        
        # Check daily schedule collection folders (strict)
        missing_collections = []
        for entry in self.daily_schedule:
            for collection in entry.collections:
                collection_path = os.path.join(songs_folder, collection.value)
                if not os.path.exists(collection_path):
                    missing_collections.append(f"{collection.value} (daily schedule)")
        
        # Check special schedule collection folders (strict)
        for entry in self.special_schedule:
            for collection in entry.collections:
                collection_path = os.path.join(songs_folder, collection.value)
                if not os.path.exists(collection_path):
                    missing_collections.append(f"{collection.value} (special schedule)")
        
        # Fail if any collections are missing
        if missing_collections:
            raise FileNotFoundError(
                f"Schedule references missing collection folders: {missing_collections}. "
                f"Create these folders in {songs_folder}/ or update schedule configuration."
            )
    
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
        # Find the active daily schedule entry
        schedule_index = 0
        current_time_only = current_time.time()
        
        # Find the latest schedule entry that's still before current time
        while (schedule_index < len(self.daily_schedule) - 1 and 
               current_time_only >= self.daily_schedule[schedule_index + 1].time):
            schedule_index += 1
        
        # Return scheduled collections, or all collections as fallback
        if schedule_index < len(self.daily_schedule):
            return self.daily_schedule[schedule_index].collections
        else:
            # Fallback to all collections if no schedule found
            return ALL_COLLECTIONS
