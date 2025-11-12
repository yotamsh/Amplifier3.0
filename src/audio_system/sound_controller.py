"""
Sound Controller - Manages audio playback for the game system
"""

import enum
import os
import random
import pygame
from datetime import datetime
from typing import Optional


# Constants
SOUNDS_FOLDER = "sounds/"
CODE_INPUT_MUSIC_PATH = SOUNDS_FOLDER +"sheshtus_long_voice.mp3"


class GameSounds(enum.Enum):
    """Game sound effects - stores file paths, loads sounds when needed"""
    WIN_SOUND = "win.mp3"
    CODE_SOUND = "code.mp3"
    INTRO_SOUND = "one_two_three.mp3"
    QUITE_SOUND = "quite.mp3"
    BOOM_SOUND = "boom.mp3"
    
    # Individual fail sounds
    FAIL_SOUND_1 = "fail1.mp3"
    FAIL_SOUND_2 = "fail2.mp3"
    FAIL_SOUND_3 = "fail3.mp3"
    FAIL_SOUND_4 = "fail4.mp3"
    
    def get_sound_path(self) -> str:
        """Get the full path to the sound file"""
        return SOUNDS_FOLDER + self.value


class SoundController:
    """
    Controls all audio playback for the game system.
    
    Manages background music, sound effects, and volume control
    based on button interactions.
    """
    
    def __init__(self, song_library, num_buttons: int):
        """
        Initialize sound controller with pygame mixer and validate sound files.
        
        Args:
            song_library: SongLibrary instance for music management
            num_buttons: Number of buttons for volume calculation
            
        Raises:
            FileNotFoundError: If any required sound files are missing
            pygame.error: If sound files fail to load
        """
        self.song_library = song_library
        self.num_buttons = num_buttons
        self.current_song: Optional[str] = None
        
        # Initialize pygame mixer
        # Force quit any existing mixer to release audio locks from crashed sessions
        self.mixer = pygame.mixer
        self.mixer.quit()  # Release any existing audio device locks
        self.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        self.mixer.init()
        
        # Load and validate all sound files (strict - fail if any missing)
        self._sound_objects = {}
        self._load_and_validate_sounds()
        
        # Stop any existing music and load first song
        self.mixer.music.stop()
        self.load_next_song()
    
    def _load_and_validate_sounds(self) -> None:
        """
        Load and validate all required sound files in one step.
        
        Validates file existence first, then loads pygame Sound objects.
        Fails immediately if any sound file is missing or cannot be loaded.
        
        Raises:
            FileNotFoundError: If any sound files are missing
            pygame.error: If sound files fail to load
        """
        # First check that all required files exist
        missing_files = []
        
        # Check game sound files
        for sound_enum in GameSounds:
            sound_path = sound_enum.get_sound_path()
            if not os.path.exists(sound_path):
                missing_files.append(sound_path)
        
        # Check code input music file
        if not os.path.exists(CODE_INPUT_MUSIC_PATH):
            missing_files.append(CODE_INPUT_MUSIC_PATH)
        
        # Fail fast if any files are missing
        if missing_files:
            raise FileNotFoundError(f"Required sound files not found: {missing_files}")
        
        # Load all sound objects (files are guaranteed to exist)
        for sound_enum in GameSounds:
            sound_path = sound_enum.get_sound_path()
            try:
                self._sound_objects[sound_enum] = pygame.mixer.Sound(sound_path)
            except pygame.error as e:
                raise pygame.error(f"Failed to load sound {sound_enum.name} from {sound_path}: {e}")
    
    def load_next_song(self) -> None:
        """Load a random song from the song library into the mixer"""
        self.current_song = self.song_library.get_random_song()
        if self.current_song:
            self.mixer.music.load(self.current_song)
    
    def set_music_volume_by_buttons(self, total_clicked_buttons: int) -> None:
        """
        Set music volume based on number of clicked buttons.
        
        Volume formula: ((clicked + 2) / (total_buttons + 2))^2
        
        Args:
            total_clicked_buttons: Number of currently pressed buttons
        """
        volume = pow((total_clicked_buttons + 2) / (self.num_buttons + 2), 2)
        self.mixer.music.set_volume(volume)
    
    def start_loaded_song(self) -> None:
        """Start playing the currently loaded song"""
        self.mixer.music.play()
    
    def stop_music(self) -> None:
        """Stop the currently playing music"""
        self.mixer.music.stop()
    
    def is_song_playing(self) -> bool:
        """
        Check if music is currently playing.
        
        Returns:
            True if music is playing, False otherwise
        """
        return self.mixer.music.get_busy()
    
    def handle_code(self, code: str) -> bool:
        """
        Check if a code is supported by the song library.
        
        Args:
            code: 5-digit song code to check
            
        Returns:
            True if code is supported, False otherwise
        """
        return self.song_library.is_code_supported(code)
    
    def update_schedule(self, current_time: datetime) -> None:
        """
        Update the song library's collection schedule based on current time.
        
        Args:
            current_time: Current datetime for schedule evaluation
        """
        self.song_library.update_collection_schedule(current_time)
    
    def play_sound_with_volume(self, sound: GameSounds, volume: float) -> None:
        """
        Play a game sound with specified volume.
        
        Args:
            sound: GameSounds enum value to play
            volume: Volume level (0.0 to 1.0)
        """
        sound_obj = self._sound_objects[sound]
        sound_obj.set_volume(volume)
        sound_obj.play()
    
    def play_random_fail_sound(self, volume: float = 1.0) -> None:
        """
        Play a random fail sound with specified volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        fail_sounds = [
            GameSounds.FAIL_SOUND_1,
            GameSounds.FAIL_SOUND_2, 
            GameSounds.FAIL_SOUND_3,
            GameSounds.FAIL_SOUND_4
        ]
        random_fail_sound = random.choice(fail_sounds)
        self.play_sound_with_volume(random_fail_sound, volume)
