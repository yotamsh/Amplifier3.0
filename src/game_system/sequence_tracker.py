"""
Button sequence tracker for pattern detection
"""

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from button_system.button_state import ButtonState


class ButtonsSequenceTracker:
    """
    Tracks button press sequences for pattern detection.
    
    Maintains a rolling window of recently pressed buttons as a string,
    where each character represents the button index.
    - Buttons 0-9 use digits '0'-'9'
    - Buttons 10+ use letters 'A', 'B', etc.
    
    Also tracks timing information to support time-based sequence validation.
    
    Example:
        tracker = ButtonsSequenceTracker(max_length=5)
        # User presses button 2, then 3, then 4
        # Sequence becomes: "234"
        tracker.ends_with("34")  # Returns True
        tracker.get_last_sequence(2)  # Returns "34"
        tracker.get_time_since_first_char()  # Time since '2' was pressed
    """
    
    def __init__(self, max_sequence_length: int):
        """
        Initialize sequence tracker.
        
        Args:
            max_sequence_length: Maximum number of button presses to remember
        """
        self.max_length = max_sequence_length
        self.sequence = ""  # String of button indices, e.g., "23456"
        self.first_char_time: Optional[float] = None  # Timestamp of first character
    
    def update(self, button_state: 'ButtonState') -> None:
        """
        Update sequence with newly pressed buttons.
        
        Detects button press edges (false→true) and appends button indices
        to the sequence. If multiple buttons pressed simultaneously, adds all
        in index order.
        
        Args:
            button_state: ButtonState with edge detection
        """
        current_time = time.time()
        
        # Find all buttons that were just pressed (edge: false→true)
        newly_pressed = []
        for i in range(button_state.get_button_count()):
            if button_state.was_changed[i] and button_state.for_button[i]:
                newly_pressed.append(i)
        
        # Add newly pressed buttons to sequence (in index order)
        for button_index in newly_pressed:
            # Set first_char_time if this is the first character
            if not self.sequence:
                self.first_char_time = current_time
            
            self.sequence += self._button_to_char(button_index)
        
        # Trim sequence to max length (keep most recent)
        if len(self.sequence) > self.max_length:
            self.sequence = self.sequence[-self.max_length:]
            # Note: Trimming loses first_char_time accuracy for very long sequences
    
    def reset(self) -> None:
        """Clear the sequence memory and timing."""
        self.sequence = ""
        self.first_char_time = None
    
    def ends_with(self, pattern: str) -> bool:
        """
        Check if current sequence ends with the given pattern.
        
        Args:
            pattern: String pattern to check (e.g., "234")
            
        Returns:
            True if sequence ends with pattern, False otherwise
            
        Example:
            If sequence is "12234", ends_with("234") returns True
        """
        if not pattern:
            return True  # Empty pattern always matches
        if not self.sequence:
            return False  # Empty sequence doesn't match non-empty pattern
        return self.sequence.endswith(pattern)
    
    def get_last_sequence(self, length: int) -> str:
        """
        Get the last N characters from the sequence.
        
        Args:
            length: Number of characters to retrieve
            
        Returns:
            Last N characters of sequence (or entire sequence if shorter)
            
        Example:
            If sequence is "12345", get_last_sequence(3) returns "345"
            If sequence is "12", get_last_sequence(5) returns "12"
        """
        if length <= 0:
            return ""
        return self.sequence[-length:]
    
    def get_sequence(self) -> str:
        """
        Get the current full sequence.
        
        Returns:
            Current sequence string
        """
        return self.sequence
    
    def get_first_char_time(self) -> Optional[float]:
        """
        Get the timestamp when the first character was added.
        
        Returns:
            Unix timestamp (float) of first character, or None if sequence is empty
        """
        return self.first_char_time
    
    def get_time_since_first_char(self) -> Optional[float]:
        """
        Get seconds elapsed since the first character was added.
        
        Returns:
            Seconds since first character (float), or None if sequence is empty
        """
        if self.first_char_time is None:
            return None
        return time.time() - self.first_char_time
    
    def _button_to_char(self, button_index: int) -> str:
        """
        Convert button index to character.
        
        Args:
            button_index: Button index (0-9 become '0'-'9', 10+ become 'A', 'B', etc.)
            
        Returns:
            Character representation of button
        """
        if button_index < 10:
            return str(button_index)
        else:
            # Button 10 → 'A', 11 → 'B', etc.
            return chr(ord('A') + button_index - 10)
    
    def __str__(self) -> str:
        """Human-readable representation"""
        time_info = ""
        if self.first_char_time is not None:
            elapsed = self.get_time_since_first_char()
            time_info = f", time_since_start={elapsed:.2f}s"
        return f"ButtonsSequenceTracker(sequence='{self.sequence}', max_length={self.max_length}{time_info})"
