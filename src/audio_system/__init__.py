"""
Audio System Module

Provides song management, collection scheduling, and code generation
for the HumanAmplifier interactive game system.
"""

from audio_system.collections import Collection, Schedule, DailyScheduleEntry, SpecialScheduleEntry, ALL_COLLECTIONS
from audio_system.song_library import SongLibrary
from audio_system.code_generator import CodeGeneratorHelper
from audio_system.sound_controller import SoundController, GameSounds

__all__ = [
    'Collection',
    'ALL_COLLECTIONS',
    'Schedule', 
    'DailyScheduleEntry',
    'SpecialScheduleEntry',
    'SongLibrary',
    'CodeGeneratorHelper',
    'SoundController',
    'GameSounds'
]
