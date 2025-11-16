"""
Button System Package

A clean, type-safe button reading system following SOLID principles.
Supports multiple buttons with edge detection and state tracking.
"""

from .button_state import ButtonState
from .interfaces import IButtonReader, IButtonSampler
from .button_reader import ButtonReader
from .gpio_sampler import GPIOSampler

__all__ = [
    "ButtonState",
    "IButtonReader",
    "IButtonSampler",
    "ButtonReader",
    "GPIOSampler"
]
