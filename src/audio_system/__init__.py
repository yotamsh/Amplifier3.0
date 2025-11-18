"""
Audio System Module

Provides song management, collection scheduling, and code generation
for the HumanAmplifier interactive game system.
"""

from .audio_collections import AudioCollection, Schedule, DailyScheduleEntry, SpecialScheduleEntry, ALL_COLLECTIONS
from .song_library import SongLibrary
from .code_generator import CodeGeneratorHelper
from .sound_controller import SoundController, GameSounds

__all__ = [
    'AudioCollection',
    'ALL_COLLECTIONS',
    'Schedule', 
    'DailyScheduleEntry',
    'SpecialScheduleEntry',
    'SongLibrary',
    'CodeGeneratorHelper',
    'SoundController',
    'GameSounds'
]
