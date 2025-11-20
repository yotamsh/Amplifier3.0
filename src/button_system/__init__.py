"""
Button System Package

A clean, type-safe button reading system following SOLID principles.
Supports multiple buttons with edge detection and state tracking.
"""

from .button_state import ButtonState
from .interfaces import IButtonReader, IButtonSampler
from .button_reader import ButtonReader
from .gpio_sampler import GPIOSampler
from .gpio_keyboard_sampler import GPIOWithKeyboardSampler
from .keyboard_sampler import KeyboardSampler, KeyboardSamplerLineMode

__all__ = [
    "ButtonState",
    "IButtonReader",
    "IButtonSampler",
    "ButtonReader",
    "GPIOSampler",
    "GPIOWithKeyboardSampler",
    "KeyboardSampler",
    "KeyboardSamplerLineMode"
]
