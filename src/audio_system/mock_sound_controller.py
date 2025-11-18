"""
Mock Sound Controller - No-op implementation for testing without audio hardware
"""

import time
from datetime import datetime
from typing import Optional


class MockSoundController:
    """
    Mock implementation of SoundController that performs no audio operations.
    
    Simulates song playback state for 2 minutes after start_loaded_song() is called,
    or until stop_music() is called.
    """
    
    def __init__(self, song_library, num_buttons: int, logger):
        """
        Initialize mock sound controller.
        
        Args:
            song_library: SongLibrary instance (used for schedule updates only)
            num_buttons: Number of buttons (unused in mock)
            logger: ClassLogger instance for logging
        """
        self.song_library = song_library
        self.num_buttons = num_buttons
        self.logger = logger
        self.current_song: Optional[str] = None
        
        # Playback simulation state
        self._playback_start_time: Optional[float] = None
        self._playback_duration = 120.0  # 2 minutes in seconds
        
        self.logger.info("🔇 MockSoundController initialized (audio disabled)")
    
    def load_next_song(self) -> None:
        """Mock: Simulate loading a random song"""
        self.current_song = self.song_library.get_random_song()
        if self.current_song:
            self.logger.debug(f"Mock: Loaded song {self.current_song}")
    
    def set_music_volume_by_buttons(self, total_clicked_buttons: int) -> None:
        """Mock: No-op for volume control"""
        pass
    
    def set_music_volume(self, volume: float) -> None:
        """Mock: No-op for volume control"""
        pass
    
    def start_loaded_song(self) -> None:
        """Mock: Start simulated playback (2 minute timer)"""
        self._playback_start_time = time.time()
        if self.current_song:
            self.logger.info(f'Mock: Started playback of "{self.current_song}"')
        else:
            self.logger.info("Mock: Started playback (no song loaded)")
    
    def stop_music(self) -> None:
        """Mock: Stop simulated playback"""
        if self._playback_start_time is not None:
            self.logger.info("Mock: Stopped playback")
        self._playback_start_time = None
    
    def load_and_play_special_music(self, file_path: str, volume: float = 1.0) -> None:
        """Mock: Simulate playing special music"""
        self.current_song = file_path
        self._playback_start_time = time.time()
        self.logger.info(f"Mock: Playing special music {file_path} at volume {volume}")
    
    def is_song_playing(self) -> bool:
        """
        Check if mock playback is active.
        
        Returns True for 2 minutes after start_loaded_song(),
        or until stop_music() is called.
        
        Returns:
            True if simulated playback is active, False otherwise
        """
        if self._playback_start_time is None:
            return False
        
        elapsed = time.time() - self._playback_start_time
        if elapsed >= self._playback_duration:
            # Auto-stop after 2 minutes
            self._playback_start_time = None
            return False
        
        return True
    
    def is_code_supported(self, code: str) -> bool:
        """
        Check if a code is supported by the song library.
        
        Args:
            code: Song code to check
            
        Returns:
            True if code is supported, False otherwise
        """
        return self.song_library.is_code_supported(code)
    
    def play_song_by_code(self, code: str) -> bool:
        """
        Mock: Simulate playing a song by code.
        
        Args:
            code: Song code to play
            
        Returns:
            True if song exists, False otherwise
        """
        try:
            # Get song path from library
            song_path = self.song_library.get_song_by_code(code)
            if not song_path:
                self.logger.error(f"Mock: Song with code {code} not found")
                return False
            
            # Simulate playback
            self.current_song = song_path
            self._playback_start_time = time.time()
            self.logger.info(f'Mock: Playing song by code {code}: "{song_path}"')
            return True
            
        except Exception as e:
            self.logger.error(f"Mock: Failed to play song by code {code}: {e}")
            return False
    
    def update_schedule(self, current_time: datetime) -> None:
        """
        Update the song library's collection schedule.
        
        Args:
            current_time: Current datetime for schedule evaluation
        """
        self.song_library.update_collection_schedule(current_time)
    
    def play_sound_with_volume(self, sound, volume: float):
        """
        Mock: No-op for sound effects.
        
        Args:
            sound: GameSounds enum value (ignored)
            volume: Volume level (ignored)
            
        Returns:
            None (real implementation returns pygame.mixer.Channel)
        """
        self.logger.debug(f"Mock: Playing sound {sound} at volume {volume}")
        return None
    
    def play_random_fail_sound(self, volume: float = 1.0) -> None:
        """
        Mock: No-op for fail sounds.
        
        Args:
            volume: Volume level (ignored)
        """
        self.logger.debug(f"Mock: Playing random fail sound at volume {volume}")

