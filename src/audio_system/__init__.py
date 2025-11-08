"""
Audio System Module

Provides song management, collection scheduling, and code generation
for the Amp3 interactive game system.
"""

from .collections import Collection, Schedule, DailyScheduleEntry, SpecialScheduleEntry, ALL_COLLECTIONS
from .song_library import SongLibrary
from .code_generator import CodeGeneratorHelper

__all__ = [
    'Collection',
    'ALL_COLLECTIONS',
    'Schedule', 
    'DailyScheduleEntry',
    'SpecialScheduleEntry',
    'SongLibrary',
    'CodeGeneratorHelper'
]
