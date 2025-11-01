"""
Button System Package

A clean, type-safe button reading system following SOLID principles.
Supports multiple buttons with edge detection and state tracking.
"""

from .button_state import ButtonState
from .interfaces import IButtonReader
from .button_reader import ButtonReader

__all__ = [
    "ButtonState",
    "IButtonReader", 
    "ButtonReader"
]
