"""
Button sequence detection for complex state transitions
"""

import time
from typing import List


class SequenceDetector:
    """
    Detects specific button press sequences with timing constraints.
    
    Used for transitions like "press button 7 three times" or complex input patterns.
    Supports timeout-based sequence reset to handle user delays.
    """
    
    def __init__(self, target_sequence: List[int], max_delay_ms: int = 1000):
        """
        Initialize sequence detector.
        
        Args:
            target_sequence: List of button IDs that form the target sequence
            max_delay_ms: Maximum time between button presses before reset
        """
        self.target_sequence: List[int] = target_sequence
        self.max_delay_ms: int = max_delay_ms
        self.current_sequence: List[int] = []
        self.last_event_time: float = 0.0
    
    def add_event(self, button_id: int) -> bool:
        """
        Add a button press event to the sequence.
        
        Args:
            button_id: ID of the button that was pressed
            
        Returns:
            True if the target sequence was completed, False otherwise
        """
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Reset sequence if too much time has passed
        if current_time - self.last_event_time > self.max_delay_ms:
            self.current_sequence = []
        
        # Add new event
        self.current_sequence.append(button_id)
        self.last_event_time = current_time
        
        # Check if we've completed the target sequence
        if self._matches_target():
            self.reset()
            return True
        
        # Keep only the relevant suffix to avoid unbounded growth
        if len(self.current_sequence) > len(self.target_sequence):
            # Keep only the last N-1 elements where N is target length
            keep_count = len(self.target_sequence) - 1
            self.current_sequence = self.current_sequence[-keep_count:]
        
        return False
    
    def reset(self) -> None:
        """Reset the sequence detector to initial state"""
        self.current_sequence = []
        self.last_event_time = 0.0
    
    def _matches_target(self) -> bool:
        """Check if current sequence matches the target sequence"""
        if len(self.current_sequence) != len(self.target_sequence):
            return False
        
        return self.current_sequence == self.target_sequence
    
    def get_progress(self) -> float:
        """
        Get completion progress as a ratio.
        
        Returns:
            Progress from 0.0 to 1.0, where 1.0 means sequence completed
        """
        if not self.target_sequence:
            return 0.0
        
        # Count how many elements match from the end
        matching_count = 0
        min_len = min(len(self.current_sequence), len(self.target_sequence))
        
        for i in range(min_len):
            current_idx = len(self.current_sequence) - 1 - i
            target_idx = len(self.target_sequence) - 1 - i
            
            if self.current_sequence[current_idx] == self.target_sequence[target_idx]:
                matching_count += 1
            else:
                break
        
        return matching_count / len(self.target_sequence)
