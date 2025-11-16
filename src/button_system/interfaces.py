"""
Abstract interfaces for button reading systems
"""

from abc import ABC, abstractmethod
from typing import List
from .button_state import ButtonState

class IButtonSampler(ABC):
    """
    Abstract interface for sampling individual button states.
    
    Separates the concern of reading hardware state from button state management.
    Allows different implementations: pure GPIO, GPIO+keyboard, mock, network, etc.
    """
    
    @abstractmethod
    def read_button(self, button_index: int) -> bool:
        """
        Read current state of a single button.
        
        Args:
            button_index: Button number (0-based)
            
        Returns:
            True if button is currently pressed, False otherwise
        """
        pass
    
    @abstractmethod
    def get_button_count(self) -> int:
        """
        Get the number of buttons this sampler handles.
        
        Returns:
            int: Number of buttons (0-based indexing)
        """
        pass
    
    @abstractmethod
    def setup(self) -> None:
        """Initialize the sampler hardware/resources"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup sampler resources"""
        pass


class IButtonReader(ABC):
    """
    Abstract interface for button reading systems.
    
    Follows the Interface Segregation Principle - minimal, focused interface.
    Implementations can use GPIO, I2C, SPI, network, or any other method.
    """
    
    @abstractmethod
    def read_buttons(self) -> ButtonState:
        """
        Read current state of all configured buttons and return comprehensive state.
        
        Returns:
            ButtonState: Complete button state with edge detection and aggregates
        """
        pass
    
    @abstractmethod
    def get_button_count(self) -> int:
        """
        Get the number of buttons configured in this reader.
        
        Returns:
            int: Number of buttons (0-based indexing)
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up any resources used by the button reader.
        
        Should be called before program exit to properly release
        hardware resources (GPIO pins, file handles, etc.)
        """
        pass
