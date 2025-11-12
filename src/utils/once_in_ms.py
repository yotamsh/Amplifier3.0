"""
Timing utility for throttling execution in game loops
"""

import time


class OnceInMs:
    """
    Timer for throttling code execution to at most once per interval.
    
    Use this to limit how often expensive operations run in the game loop,
    even though the loop itself runs every frame (e.g., 20ms).
    
    Example:
        # In __init__:
        self.schedule_updater = OnceInMs(60000)  # Once per minute
        
        # In update loop (runs every 20ms):
        if self.schedule_updater.should_execute():
            self.update_schedule()  # Only executes once per minute
    """
    
    def __init__(self, interval_ms: int):
        """
        Initialize timer with interval.
        
        Args:
            interval_ms: Minimum milliseconds between executions
        """
        self.interval_ms = interval_ms
        self.interval = interval_ms / 1000.0
        self.last_execution = 0
    
    def should_execute(self) -> bool:
        """
        Check if enough time has passed and update timer if so.
        
        Returns:
            True if interval has passed (and timer is updated), False otherwise
        """
        current = time.time()
        if current - self.last_execution >= self.interval:
            self.last_execution = current
            return True
        return False
    
    def reset(self):
        """Force next should_execute() call to return True"""
        self.last_execution = 0
    
    def elapsed_ms(self) -> float:
        """Get milliseconds elapsed since last execution"""
        return (time.time() - self.last_execution) * 1000
    
    def remaining_ms(self) -> float:
        """Get milliseconds remaining until next execution (can be negative if overdue)"""
        return self.interval_ms - self.elapsed_ms()

