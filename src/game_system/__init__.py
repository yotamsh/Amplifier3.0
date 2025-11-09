"""
Game System - State machine based interactive game manager

This module provides the core architecture for a state-machine-based
interactive game with dynamic LED animations and button input.
"""

from game_system.states import GameState
from game_system.animations import Animation
from game_system.sequence_detector import SequenceDetector
from game_system.game_manager import GameManager
from game_system.states import IdleState, AmplifyState, PartyState
from game_system.animations import RainbowAnimation, BreathingAnimation, StaticColorAnimation
from game_system.animation_helpers import AnimationHelpers
from game_system.config import GameConfig, LedStripConfig, ButtonConfig

__all__ = [
    # Base classes
    "GameState",
    "Animation", 
    "SequenceDetector",
    "GameManager",
    # States
    "IdleState",
    "AmplifyState", 
    "PartyState",
    # Animations
    "RainbowAnimation",
    "BreathingAnimation",
    "StaticColorAnimation",
    "AnimationHelpers",
    # Configuration
    "GameConfig",
    "LedStripConfig", 
    "ButtonConfig"
]
