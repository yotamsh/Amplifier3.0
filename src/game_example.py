#!/usr/bin/env python3
"""
Game System Integration Example

This example shows how to use the new game state machine system
with your existing button and LED infrastructure.
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
    from game_system import GameController
    from game_system.config import GameConfig, ButtonConfig, LedStripConfig, AudioConfig
    from audio_system import Schedule, DailyScheduleEntry, SpecialScheduleEntry, Collection, SongLibrary
    from hybridLogger import HybridLogger
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi with required libraries installed")
    sys.exit(1)


def create_default_config() -> GameConfig:
    """Create default configuration for development/testing"""
    
    button_config = ButtonConfig(
        pins=[
            4, 
            # 5, 
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
        csv_output_path="AmplifierSongCodes.csv",
        daily_schedule=[
            DailyScheduleEntry(time(0, 0), {Collection.PARTY}),
            DailyScheduleEntry(time(2, 0), Collection.get_all_discovered()),
            DailyScheduleEntry(time(4, 0), {Collection.CLASSIC}),
            DailyScheduleEntry(time(7, 0), {Collection.MORNING}),
            DailyScheduleEntry(time(10, 0), Collection.get_all_discovered()),
            DailyScheduleEntry(time(14, 0), {Collection.TV}),
            DailyScheduleEntry(time(16, 0), {Collection.TV, Collection.GENERAL, Collection.DISNEY, Collection.PARTY, Collection.MORNING}),
            DailyScheduleEntry(time(17, 0), {Collection.GENERAL, Collection.PARTY}),
            DailyScheduleEntry(time(20, 0), {Collection.DISNEY}),
            DailyScheduleEntry(time(20, 30), {Collection.GENERAL, Collection.DISNEY, Collection.PARTY}),
        ],
        special_schedule=[
            # Example special schedule entry
            SpecialScheduleEntry(
                start=datetime(2024, 12, 25, 16, 0),
                end=datetime(2024, 12, 25, 18, 0),
                collections={Collection.CLASSIC}
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


def create_game_system():
    """
    Create and configure the complete game system.
    
    Returns:
        GameController: Configured game controller ready to run
    """
    # Create and validate configuration
    config = create_default_config()
    config.validate()
    
    # Initialize logging
    main_logger = HybridLogger("GameSystem")
    game_logger = main_logger.get_class_logger("GameController", logging.DEBUG)
    button_logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
    audio_logger = main_logger.get_class_logger("SongLibrary", logging.INFO)
    
    try:
        # Initialize button reader
        button_reader = ButtonReader(
            button_pins=config.button_config.pins,
            logger=button_logger,
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
            special_schedule=config.audio_config.special_schedule
        )
        
        # Create song library with validated schedule
        song_library = SongLibrary(
            songs_folder=config.audio_config.songs_folder,
            schedule=schedule,
            logger=audio_logger
        )
        
        # Create game controller (starts with IdleState by default)
        game_controller = GameController(
            button_reader=button_reader,
            led_strips=led_strips,
            logger=game_logger,
            song_library=song_library,
            frame_duration_ms=int(config.frame_duration_ms),
            sequence_timeout_ms=config.sequence_timeout_ms
        )
        
        game_logger.info("Game system initialized successfully")
        game_logger.info(f"Configuration: {config.button_count} buttons, {config.strip_count} LED strips, {config.frame_duration_ms}ms frame duration")
        game_logger.info(f"Audio system: {song_library.get_stats()}")
        
        return game_controller, main_logger
        
    except Exception as e:
        main_logger.get_main_logger().error(f"Failed to initialize game system: {e}", exception=e)
        raise


def main():
    """
    Main function - sets up and runs the game system.
    """
    # Get actual config to show correct info
    config = create_default_config()
    active_pins = [pin for pin in config.button_config.pins]
    
    print("🎮 INTERACTIVE GAME SYSTEM")
    print("=" * 50)
    print("States implemented:")
    print("  • IdleState: Dim blue breathing animation")
    print("  • AmplifyState: Rainbow per pressed button") 
    print("  • TestState: Static colors for testing")
    print("  • Audio System: Song management with scheduled collections")
    print()
    print("Controls:")
    print("  • Any button press: Idle → Amplify")
    print("  • All buttons released: Amplify → Idle")
    print(f"  • Button {len(active_pins)-1} (GPIO {active_pins[-1]}) pressed 3x: Any state → Test")
    print("  • Any button in Test: Test → Idle")
    print()
    print("Hardware configuration:")
    print(f"  • {len(active_pins)} buttons on GPIO: {', '.join(map(str, active_pins))}")
    print(f"  • LED strip 1: {config.led_strips[0].led_count} LEDs on GPIO {config.led_strips[0].gpio_pin}")
    print(f"  • LED strip 2: {config.led_strips[1].led_count} LEDs on GPIO {config.led_strips[1].gpio_pin}")
    print("  • External 5V power for LED strips")
    print()
    print("Game settings:")
    print(f"  • Frame duration: {config.frame_duration_ms}ms ({config.target_fps:.1f} FPS)")
    print(f"  • Button sample rate: {config.button_config.sample_rate_hz}Hz")
    print(f"  • Sequence timeout: {config.sequence_timeout_ms}ms")
    print()
    print("Audio settings:")
    print(f"  • Songs folder: {config.audio_config.songs_folder}")
    print(f"  • Daily schedule entries: {len(config.audio_config.daily_schedule)}")
    print(f"  • Special schedule entries: {len(config.audio_config.special_schedule)}")
    print()
    
    input("Press Enter when hardware is ready...")
    print()
    
    try:
        # Create game system
        game_controller, logger = create_game_system()
        
        print("🚀 Starting game system...")
        print("Press Ctrl+C to stop")
        print()
        
        # Run the game with automatic frame limiting
        game_controller.run_game_loop()
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Game stopped by user")
    except Exception as e:
        print(f"\n❌ Game system error: {e}")
        raise
    finally:
        # Cleanup will be handled by GameController.stop()
        print("✅ Game system shut down")
        if 'logger' in locals():
            logger.cleanup()


if __name__ == "__main__":
    main()
