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
    CODE_DIGIT_SOUND = "codeDigit.mp3"
    ONE_TWO_THREE_SOUND = "one_two_three.mp3"
    QUITE_SOUND = "quite.mp3"
    BOOM_SOUND = "boom.mp3"
    APPLAUSE_SOUND = "applauseLoud.mp3"
    AMAZING_SOUND = "amazingLoud.mp3"
    
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
    
    def __init__(self, song_library, num_buttons: int, logger):
        """
        Initialize sound controller with pygame mixer and validate sound files.
        
        Args:
            song_library: SongLibrary instance for music management
            num_buttons: Number of buttons for volume calculation
            logger: ClassLogger instance for logging
            
        Raises:
            FileNotFoundError: If any required sound files are missing
            pygame.error: If sound files fail to load
        """
        self.song_library = song_library
        self.num_buttons = num_buttons
        self.logger = logger
        self.current_song: Optional[str] = None
        
        # Initialize pygame mixer
        # Force quit any existing mixer to release audio locks from crashed sessions
        self.mixer = pygame.mixer
        # self.mixer.quit()  # Release any existing audio device locks
        # self.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
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
    
    def set_music_volume(self, volume: float) -> None:
        """
        Set music volume directly.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.mixer.music.set_volume(volume)
    
    def start_loaded_song(self) -> None:
        """Start playing the currently loaded song"""
        self.mixer.music.play()
        
        # Log song name
        if self.current_song:
            song_name = os.path.basename(self.current_song)
            self.logger.info(f'Song "{song_name}" was randomly started')
    
    def stop_music(self) -> None:
        """Stop the currently playing music"""
        self.mixer.music.stop()
    
    def load_and_play_special_music(self, file_path: str, volume: float = 1.0) -> None:
        """
        Load and play a special music file (like code input music).
        
        Args:
            file_path: Path to music file
            volume: Volume level (0.0 to 1.0)
        """
        self.stop_music()
        self.current_song = file_path
        self.mixer.music.load(file_path)
        self.mixer.music.set_volume(volume)
        self.mixer.music.play()
    
    def is_song_playing(self) -> bool:
        """
        Check if music is currently playing.
        
        Returns:
            True if music is playing, False otherwise
        """
        return self.mixer.music.get_busy()
    
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
        Play a specific song by its code at full volume.
        
        Stops current music, loads the song by code, and plays it at volume 1.0.
        
        Args:
            code: Song code to play
            
        Returns:
            True if song was loaded and started successfully, False on error
        """
        try:
            # Stop current music
            self.stop_music()
            
            # Get song path from library
            song_path = self.song_library.get_song_by_code(code)
            if not song_path:
                self.logger.error(f"Song with code {code} not found")
                return False
            
            # Load and play the song
            self.current_song = song_path
            self.mixer.music.load(song_path)
            self.mixer.music.set_volume(1.0)
            self.mixer.music.play()
            
            # Log success
            song_name = os.path.basename(song_path)
            self.logger.info(f'Playing song by code {code}: "{song_name}"')
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to play song by code {code}: {e}")
            return False
    
    def update_schedule(self, current_time: datetime) -> None:
        """
        Update the song library's collection schedule based on current time.
        
        Args:
            current_time: Current datetime for schedule evaluation
        """
        self.song_library.update_collection_schedule(current_time)
    
    def play_sound_with_volume(self, sound: GameSounds, volume: float) -> pygame.mixer.Channel:
        """
        Play a game sound with specified volume and return the channel.
        
        Args:
            sound: GameSounds enum value to play
            volume: Volume level (0.0 to 1.0)
            
        Returns:
            pygame.mixer.Channel object that can be used to check if sound is still playing
        """
        sound_obj = self._sound_objects[sound]
        sound_obj.set_volume(volume)
        return sound_obj.play()
    
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
