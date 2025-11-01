"""
Abstract interfaces for button reading systems
"""

from abc import ABC, abstractmethod
from .button_state import ButtonState

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
