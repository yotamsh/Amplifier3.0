"""
Base classes for the game state machine and animation system
"""

import time
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from button_system.button_state import ButtonState
    from led_system.interfaces import LedStrip
    from led_system.pixel import Pixel
    from hybridLogger import ClassLogger


class GameState(ABC):
    """
    Abstract base class for all game states.
    
    Each state represents a distinct game mode with its own:
    - Button handling logic
    - Animation management 
    - State transition conditions
    """
    
    def __init__(self):
        """Initialize the game state"""
        pass
    
    @abstractmethod
    def update(self, button_state: 'ButtonState') -> Optional['GameState']:
        """
        Update state logic, handle button changes, update animations, and render LEDs.
        
        Args:
            button_state: Current button state with edge detection
            
        Returns:
            New GameState instance if transition needed, None to stay in current state
        """
        pass
    
    def on_enter(self) -> None:
        """Called when entering this state (override if needed)"""
        pass
    
    def on_exit(self) -> None:
        """Called when exiting this state (override if needed)"""
        pass


class Animation(ABC):
    """
    Abstract base class for time-based animations.
    
    Provides non-blocking, time-based animation updates with configurable speed.
    """
    
    def __init__(self, speed_ms: int, name: str = "Animation"):
        """
        Initialize animation with timing control.
        
        Args:
            speed_ms: Update interval in milliseconds
            name: Animation name for debugging
        """
        self.speed_ms: int = speed_ms
        self.name: str = name
        self.last_update: float = time.time()
    
    def should_update(self) -> bool:
        """Check if enough time has passed for next animation frame"""
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        return elapsed_ms >= self.speed_ms
    
    def update(self, dt: float) -> bool:
        """
        Update animation if enough time has passed.
        
        Args:
            dt: Delta time since last frame in seconds
            
        Returns:
            True if animation was updated, False if skipped
        """
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        
        if elapsed_ms >= self.speed_ms:
            self.advance(dt)
            self.last_update = now
            return True
        return False
    
    @abstractmethod
    def advance(self, dt: float) -> None:
        """
        Advance animation by one frame (override in subclasses).
        
        Args:
            dt: Delta time since last frame in seconds
        """
        pass
    
    @abstractmethod
    def render(self, led_strips: List['LedStrip']) -> None:
        """
        Render animation to LED strips (override in subclasses).
        
        Args:
            led_strips: List of LED strip controllers
        """
        pass
