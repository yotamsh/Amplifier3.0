"""
Game System - State machine based interactive game controller

This module provides the core architecture for a state-machine-based
interactive game with dynamic LED animations and button input.
"""

from .base_classes import GameState, Animation
from .sequence_detector import SequenceDetector
from .game_controller import GameController
from .states import IdleState, AmplifyState, TestState
from .animations import RainbowAnimation, BreathingAnimation, StaticColorAnimation

__all__ = [
    # Base classes
    "GameState",
    "Animation", 
    "SequenceDetector",
    "GameController",
    # States
    "IdleState",
    "AmplifyState", 
    "TestState",
    # Animations
    "RainbowAnimation",
    "BreathingAnimation",
    "StaticColorAnimation"
]
