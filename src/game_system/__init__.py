"""
Game System - State machine based interactive game manager

This module provides the core architecture for a state-machine-based
interactive game with dynamic LED animations and button input.
"""

from .states import GameState
from .animations import Animation
from .sequence_tracker import ButtonsSequenceTracker
from .game_manager import GameManager
from .states import IdleState, AmplifyState, PartyState, CodeModeState, CodeRevealState
from .animations import RainbowAnimation, BreathingAnimation, StaticColorAnimation, CodeModeAnimation, CodeRevealAnimation
from .animation_helpers import AnimationHelpers
from .config import GameConfig, LedStripConfig, ButtonConfig, AudioConfig

__all__ = [
    # Base classes
    "GameState",
    "Animation", 
    "ButtonsSequenceTracker",
    "GameManager",
    # States
    "IdleState",
    "AmplifyState",
    "PartyState",
    "CodeModeState",
    "CodeRevealState",
    # Animations
    "RainbowAnimation",
    "BreathingAnimation",
    "StaticColorAnimation",
    "CodeModeAnimation",
    "CodeRevealAnimation",
    "AnimationHelpers",
    # Configuration
    "GameConfig",
    "LedStripConfig", 
    "ButtonConfig",
    "AudioConfig"
]
