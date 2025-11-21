#!/usr/bin/env python3
"""
HumanAmplifier Interactive Game System

Main application for the HumanAmplifier interactive LED and audio game system.
Provides a state-machine-based game with button input, LED animations,
and scheduled audio playback.
"""

import sys
import os

# # Configure SDL audio before pygame imports (force ALSA to use USB sound card)
os.environ['SDL_AUDIODRIVER'] = 'alsa'
# os.environ['AUDIODEV'] = 'hw:0,0'  # these make us delay!
# os.environ['AUDIODEV'] = 'plughw:0,0'  # these make us delay!

import logging
import signal
import atexit
from pathlib import Path
from datetime import datetime, time

# MOCK AUDIO - Set to True to bypass audio hardware
USE_MOCK_AUDIO = False

# Global logger reference for signal handlers
_global_logger = None

def emergency_flush_and_log(sig=None, frame=None):
    """Emergency handler - flush logs before crash"""
    if _global_logger:
        try:
            if sig:
                _global_logger.critical(f"⚠️  SIGNAL RECEIVED: {sig} - Process terminating")
            _global_logger.critical("Emergency flush triggered")
            _global_logger.flush()
        except:
            pass
    
    # Exit after logging
    if sig == signal.SIGINT:
        # CTRL+C - exit cleanly
        sys.exit(0)
    elif sig:
        # Other signals - exit with error code
        sys.exit(1)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, emergency_flush_and_log)  # Termination signal
signal.signal(signal.SIGHUP, emergency_flush_and_log)   # Hangup signal
signal.signal(signal.SIGINT, emergency_flush_and_log)   # Ctrl+C

# Register exit handler
atexit.register(lambda: emergency_flush_and_log())

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from button_system import ButtonReader, GPIOSampler
    from led_system import PixelStripAdapter, Pixel
    from game_system import GameManager, ButtonsSequenceTracker
    from game_system.config import GameConfig, ButtonConfig, LedStripConfig, AudioConfig
    from audio_system import Schedule, DailyScheduleEntry, SpecialScheduleEntry, AudioCollection, SongLibrary, SoundController, ALL_COLLECTIONS
    from audio_system.mock_sound_controller import MockSoundController
    from utils import HybridLogger
    import RPi.GPIO as GPIO
except ImportError as e:
    import traceback
    print(f"❌ Import error: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("\nMake sure required libraries are installed")
    sys.exit(1)


def create_amplifier_config() -> GameConfig:
    """Create default configuration for development/testing"""
    
    button_config = ButtonConfig(
        pins=[
            6, 
            5, 
            22, 
            17, 
            4, 
            23, 
            24, 
            25,
            16, 
            20, 
            ],  # 10 buttons - tested GPIO pins
        pull_mode=GPIO.PUD_OFF,
        sample_rate_hz=200
    )
    
    led_strips = [
        # Strip 1 - main strip
        LedStripConfig(
            gpio_pin=21, 
            led_count=300,
            dma=5,
            brightness=26,  # 10% brightness for testing
            channel=0
        ),
        # Strip 2 - pyramid strip
        LedStripConfig(
            gpio_pin=18,
            led_count=293,
            dma=10,
            brightness=26,  # 10% brightness for testing
            channel=0
        )
    ]
    
    # Audio configuration with default schedule
    audio_config = AudioConfig(
        songs_folder="songs",
        daily_schedule=[
            DailyScheduleEntry(time(0, 0), {AudioCollection.MAIJAM}),
            DailyScheduleEntry(time(2, 0), {AudioCollection.PARTY, AudioCollection.MAIJAM, AudioCollection.VIRAL, AudioCollection.HAFLA, AudioCollection.FESTIGAL}),
            DailyScheduleEntry(time(3, 0), {AudioCollection.THREE_AT_NIGHT}),
            DailyScheduleEntry(time(3, 5), {AudioCollection.PARTY, AudioCollection.MAIJAM, AudioCollection.VIRAL, AudioCollection.HAFLA, AudioCollection.FESTIGAL}),
            DailyScheduleEntry(time(4, 0), {AudioCollection.FOUR_AT_NIGHT}),
            DailyScheduleEntry(time(4, 5), {AudioCollection.CLASSIC}),
            DailyScheduleEntry(time(6, 0), {AudioCollection.MORNING}),
            DailyScheduleEntry(time(10, 0), ALL_COLLECTIONS),
            DailyScheduleEntry(time(14, 0), {AudioCollection.TV}),
            DailyScheduleEntry(time(16, 0), {AudioCollection.FESTIGAL}),
            DailyScheduleEntry(time(17, 0), {AudioCollection.GENERAL, AudioCollection.PARTY, AudioCollection.MAIJAM, AudioCollection.HAFLA}),
            DailyScheduleEntry(time(20, 0), {AudioCollection.DISNEY}),
            DailyScheduleEntry(time(20, 30), ALL_COLLECTIONS),
            DailyScheduleEntry(time(22, 0), {AudioCollection.VIRAL}),
            DailyScheduleEntry(time(22, 30), {AudioCollection.HAFLA}),
            DailyScheduleEntry(time(23, 0), ALL_COLLECTIONS),
        ],
        special_schedule=[
            # Example special schedule entry
            SpecialScheduleEntry(
                start=datetime(2025, 11, 12, 16, 18),
                end=datetime(2025, 11, 12, 18, 0),
                collections={AudioCollection.MORNING}
            ),
        ]
    )
    
    return GameConfig(
        button_config=button_config,
        led_strips=led_strips,
        audio_config=audio_config,
        frame_duration_ms=20,  # 50 FPS
        sequence_timeout_ms=1500
    )


def create_game_system(config: GameConfig, amplifier_logger):
    """
    Create and configure the complete game system using provided config.
    
    Args:
        config: GameConfig instance with all system configuration
        amplifier_logger: ClassLogger instance for logging initialization steps
        
    Returns:
        GameManager: Configured game manager ready to run
    """
    # Validate the provided configuration
    config.validate()
    
    # Create class loggers for components
    game_manager_logger = amplifier_logger.create_class_logger("GameManager", logging.INFO)
    button_reader_logger = amplifier_logger.create_class_logger("ButtonReader", logging.INFO)
    song_library_logger = amplifier_logger.create_class_logger("SongLibrary", logging.INFO)
    sound_controller_logger = amplifier_logger.create_class_logger("SoundController", logging.INFO)
    sequence_tracker_logger = amplifier_logger.create_class_logger("SequenceTracker", logging.INFO)
    
    try:        
        # Initialize button sampler (GPIO for production)
        button_sampler = GPIOSampler(
            button_pins=config.button_config.pins,
            pull_mode=config.button_config.pull_mode,
            logger=button_reader_logger
        )
        
        # Initialize button reader (state management)
        button_reader = ButtonReader(
            sampler=button_sampler,
            logger=button_reader_logger
        )

                # Create schedule from config (validates collections)
        schedule = Schedule(
            daily_schedule=config.audio_config.daily_schedule,
            special_schedule=config.audio_config.special_schedule,
            songs_folder=config.audio_config.songs_folder
        )
        
        # Create song library with validated schedule
        song_library = SongLibrary(
            songs_folder=config.audio_config.songs_folder,
            schedule=schedule,
            code_length=config.audio_config.code_length,
            logger=song_library_logger
        )
        
        # Create sound controller with song library
        if USE_MOCK_AUDIO:
            amplifier_logger.info("🔇 Using MockSoundController (audio hardware disabled)")
            sound_controller = MockSoundController(
                song_library=song_library,
                num_buttons=config.button_count,
                logger=sound_controller_logger
            )
        else:
            sound_controller = SoundController(
                song_library=song_library,
                num_buttons=config.button_count,
                logger=sound_controller_logger
            )

        
        # Initialize LED strips from configuration
        led_strips = []
        for strip_config in config.led_strips:
            strip = PixelStripAdapter(
                led_count=strip_config.led_count,
                gpio_pin=strip_config.gpio_pin,
                freq_hz=strip_config.freq_hz,
                dma=strip_config.dma,
                invert=strip_config.invert,
                brightness=strip_config.brightness,
                channel=strip_config.channel
            )
            led_strips.append(strip)
        
        # Clear strips initially
        black = Pixel(0, 0, 0)
        for strip in led_strips:
            strip[:] = black
            strip.show()
        
        # Initialize random permutations for each strip
        import random
        from game_system import animation_helpers
        for strip_idx, strip in enumerate(led_strips):
            pixel_count = strip.num_pixels()
            indices = list(range(pixel_count))
            random.shuffle(indices)
            animation_helpers.STRIP_PERMUTATIONS[strip_idx] = indices
        
        
        # Create button sequence tracker with its own ClassLogger at DEBUG level
        sequence_tracker = ButtonsSequenceTracker(max_sequence_length=10, logger=sequence_tracker_logger)
        
        # Create game manager (starts with IdleState by default)
        game_manager = GameManager(
            button_reader=button_reader,
            led_strips=led_strips,
            logger=game_manager_logger,
            sound_controller=sound_controller,
            sequence_tracker=sequence_tracker,
            frame_duration_ms=int(config.frame_duration_ms)
        )
        
        amplifier_logger.info("HumanAmplifier system initialized successfully")
        amplifier_logger.info(f"Hardware: {button_reader.get_button_count()} buttons, {len(led_strips)} LED strips, {config.frame_duration_ms}ms frame duration")
        amplifier_logger.info(f"Audio system: {song_library.get_stats()}")
        amplifier_logger.info("Sound controller initialized successfully")
        
        return game_manager
        
    except Exception as e:
        amplifier_logger.error(f"Failed to initialize HumanAmplifier system: {e}", exception=e)
        raise


def main():
    """
    Main function - sets up and runs the HumanAmplifier system.
    """
    # Initialize main logger first
    main_logger = HybridLogger("HumanAmplifierSystem")
    amplifier_logger = main_logger.get_class_logger("Amplifier")
    
    # Set global logger for signal handlers
    global _global_logger
    _global_logger = amplifier_logger
    
    amplifier_logger.info("🎵 HUMAN AMPLIFIER INTERACTIVE SYSTEM")
    
    # Create configuration
    config = create_amplifier_config()
    
    # Log important configuration details
    amplifier_logger.info(f"Button configuration: {config.button_count} buttons on GPIO {config.button_config.pins}")
    amplifier_logger.info(f"LED configuration: {len(config.led_strips)} strips")
    for i, led_config in enumerate(config.led_strips):
        amplifier_logger.info(f"  Strip {i+1}: {led_config.led_count} LEDs on GPIO {led_config.gpio_pin}")
    amplifier_logger.info(f"Game settings: {config.frame_duration_ms}ms frame duration ({config.target_fps:.1f} FPS)")
    amplifier_logger.info(f"Button sample rate: {config.button_config.sample_rate_hz}Hz")
    amplifier_logger.info(f"Audio folder: {config.audio_config.songs_folder}")
    amplifier_logger.info(f"Schedule: {len(config.audio_config.daily_schedule)} daily, {len(config.audio_config.special_schedule)} special entries")
    
    try:
        # Create game system using the configured values
        game_manager = create_game_system(config, amplifier_logger)
        
        # Log post-initialization details (new information calculated during init)
        audio_stats = game_manager.sound_controller.song_library.get_stats()
        
        amplifier_logger.info("✅ System initialized successfully!")
        amplifier_logger.info(f"Hardware status: {game_manager.button_reader.get_button_count()} buttons, {len(game_manager.led_strips)} LED strips")
        for i, strip in enumerate(game_manager.led_strips):
            amplifier_logger.info(f"  Strip {i+1}: {strip.num_pixels()} LEDs active")
        
        # Get sound effects count (only for real SoundController)
        sound_effects_count = len(getattr(game_manager.sound_controller, '_sound_objects', {}))
        amplifier_logger.info(f"Audio system: {audio_stats['total_codes']} song codes, {sound_effects_count} sound effects")
        amplifier_logger.info(f"Available collections: {', '.join(audio_stats['all_collections'])}")
        
        amplifier_logger.info("===========================")
        amplifier_logger.info("🚀 Starting HumanAmplifier system...")
        
        # Run the game with automatic frame limiting
        game_manager.run_game_loop()
        
    except KeyboardInterrupt:
        amplifier_logger.info("⏹️  HumanAmplifier stopped by user")
        amplifier_logger.flush()
    except Exception as e:
        amplifier_logger.error(f"HumanAmplifier system error: {e}", exception=e)
        # Error already auto-flushes, but be explicit
        amplifier_logger.flush()
        raise
    finally:
        # Cleanup will be handled by GameManager.stop()
        amplifier_logger.info("✅ HumanAmplifier system shut down")
        amplifier_logger.flush()
        main_logger.cleanup()


if __name__ == "__main__":
    main()
