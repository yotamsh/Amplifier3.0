"""
Audio System Module

Provides song management, collection scheduling, and code generation
for the Amp3 interactive game system.
"""

from .collections import Collection, Schedule, DailyScheduleEntry, SpecialScheduleEntry
from .song_library import SongLibrary
from .code_generator import CodeGeneratorHelper

__all__ = [
    'Collection',
    'Schedule', 
    'DailyScheduleEntry',
    'SpecialScheduleEntry',
    'SongLibrary',
    'CodeGeneratorHelper'
]
