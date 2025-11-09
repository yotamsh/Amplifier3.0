#!/usr/bin/env python3
"""
HumanAmplifier Interactive Game System

Main application for the HumanAmplifier interactive LED and audio game system.
Provides a state-machine-based game with button input, LED animations,
and scheduled audio playback.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from button_system import ButtonReader
    from led_system import PixelStripAdapter, Pixel
    from game_system import GameManager
    from game_system.config import GameConfig, ButtonConfig, LedStripConfig, AudioConfig
    from audio_system import Schedule, DailyScheduleEntry, SpecialScheduleEntry, Collection, SongLibrary, SoundController, ALL_COLLECTIONS
    from hybridLogger import HybridLogger
    import RPi.GPIO as GPIO
except ImportError as e:
    import traceback
    print(f"❌ Import error: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("\nMake sure you're running this on a Raspberry Pi with required libraries installed")
    sys.exit(1)


def create_amplifier_config() -> GameConfig:
    """Create default configuration for development/testing"""
    
    button_config = ButtonConfig(
        pins=[
            4, 
            5, 
            # 6, 
            # 16, 
            # 17, 
            # 20, 
            22, 
            # 23, 
            # 24, 
            # 25
            ],  # 10 buttons - tested GPIO pins
        pull_mode=GPIO.PUD_OFF,
        sample_rate_hz=200
    )
    
    led_strips = [
        LedStripConfig(
            gpio_pin=18,
            led_count=300,
            dma=10,
            brightness=26,  # 10% brightness for testing
            channel=0
        ),
        LedStripConfig(
            gpio_pin=21, 
            led_count=300,
            dma=5,
            brightness=26,  # 10% brightness for testing
            channel=0
        )
    ]
    
    # Audio configuration with default schedule
    audio_config = AudioConfig(
        songs_folder="songs",
        daily_schedule=[
            DailyScheduleEntry(time(0, 0), ALL_COLLECTIONS),
            DailyScheduleEntry(time(2, 0), ALL_COLLECTIONS),
            # DailyScheduleEntry(time(4, 0), {Collection.CLASSIC}),
            # DailyScheduleEntry(time(7, 0), {Collection.MORNING}),
            # DailyScheduleEntry(time(10, 0), ALL_COLLECTIONS),
            # DailyScheduleEntry(time(14, 0), {Collection.TV}),
            # DailyScheduleEntry(time(16, 0), {Collection.TV, Collection.GENERAL, Collection.DISNEY, Collection.PARTY, Collection.MORNING}),
            # DailyScheduleEntry(time(17, 0), {Collection.GENERAL, Collection.PARTY}),
            # DailyScheduleEntry(time(20, 0), {Collection.DISNEY}),
            # DailyScheduleEntry(time(20, 30), {Collection.GENERAL, Collection.DISNEY, Collection.PARTY}),
        ],
        special_schedule=[
            # Example special schedule entry
            SpecialScheduleEntry(
                start=datetime(2024, 12, 25, 16, 0),
                end=datetime(2024, 12, 25, 18, 0),
                collections=ALL_COLLECTIONS
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
    game_manager_logger = amplifier_logger.create_class_logger("GameManager", logging.DEBUG)
    button_reader_logger = amplifier_logger.create_class_logger("ButtonReader", logging.INFO)
    song_library_logger = amplifier_logger.create_class_logger("SongLibrary", logging.INFO)
    
    try:
        # Initialize button reader
        button_reader = ButtonReader(
            button_pins=config.button_config.pins,
            logger=button_reader_logger,
            pull_mode=config.button_config.pull_mode
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
            logger=song_library_logger
        )
        
        # Create sound controller with song library
        sound_controller = SoundController(
            song_library=song_library,
            num_buttons=config.button_count
        )
        
        # Create game manager (starts with IdleState by default)
        game_manager = GameManager(
            button_reader=button_reader,
            led_strips=led_strips,
            logger=game_manager_logger,
            sound_controller=sound_controller,
            frame_duration_ms=int(config.frame_duration_ms),
            sequence_timeout_ms=config.sequence_timeout_ms
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
    
    input("Press Enter when hardware is ready...")
    
    try:
        # Create game system using the configured values
        game_manager = create_game_system(config, amplifier_logger)
        
        # Log post-initialization details (new information calculated during init)
        audio_stats = game_manager.sound_controller.song_library.get_stats()
        
        amplifier_logger.info("✅ System initialized successfully!")
        amplifier_logger.info(f"Hardware status: {game_manager.button_reader.get_button_count()} buttons, {len(game_manager.led_strips)} LED strips")
        for i, strip in enumerate(game_manager.led_strips):
            amplifier_logger.info(f"  Strip {i+1}: {strip.num_pixels()} LEDs active")
        amplifier_logger.info(f"Audio system: {audio_stats['total_codes']} song codes, {len(game_manager.sound_controller._sound_objects)} sound effects")
        amplifier_logger.info(f"Available collections: {', '.join(audio_stats['all_collections'])}")
        
        amplifier_logger.info("🚀 Starting HumanAmplifier system...")
        
        # Run the game with automatic frame limiting
        game_manager.run_game_loop()
        
    except KeyboardInterrupt:
        amplifier_logger.info("⏹️  HumanAmplifier stopped by user")
    except Exception as e:
        amplifier_logger.error(f"HumanAmplifier system error: {e}", exception=e)
        raise
    finally:
        # Cleanup will be handled by GameManager.stop()
        amplifier_logger.info("✅ HumanAmplifier system shut down")
        main_logger.cleanup()


if __name__ == "__main__":
    main()
