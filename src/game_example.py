#!/usr/bin/env python3
"""
Game System Integration Example

This example shows how to use the new game state machine system
with your existing button and LED infrastructure.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from button_system import ButtonReader
    from led_system import PixelStripAdapter, Pixel
    from game_system import GameController
    from game_system.config import GameConfig, ButtonConfig, LedStripConfig
    from hybridLogger import HybridLogger
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi with required libraries installed")
    sys.exit(1)


def create_default_config() -> GameConfig:
    """Create default configuration for development/testing"""
    
    button_config = ButtonConfig(
        pins=[22, 23, 24, 25, 26, 27, 28, 29, 30, 31],  # 10 buttons
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
    
    return GameConfig(
        button_config=button_config,
        led_strips=led_strips,
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
    game_logger = main_logger.get_class_logger("GameController", logging.INFO)
    button_logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
    
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
        
        # Create game controller (starts with IdleState by default)
        game_controller = GameController(
            button_reader=button_reader,
            led_strips=led_strips,
            logger=game_logger,
            frame_duration_ms=int(config.frame_duration_ms),
            sequence_timeout_ms=config.sequence_timeout_ms
        )
        
        game_logger.info("Game system initialized successfully")
        game_logger.info(f"Configuration: {config.button_count} buttons, {config.strip_count} LED strips, {config.frame_duration_ms}ms frame duration")
        
        return game_controller, main_logger
        
    except Exception as e:
        main_logger.get_main_logger().error(f"Failed to initialize game system: {e}", exception=e)
        raise


def main():
    """
    Main function - sets up and runs the game system.
    """
    print("🎮 INTERACTIVE GAME SYSTEM")
    print("=" * 50)
    print("States implemented:")
    print("  • IdleState: Dim breathing animation")
    print("  • AmplifyState: Rainbow per pressed button") 
    print("  • TestState: Static colors for testing")
    print()
    print("Controls:")
    print("  • Any button press: Idle → Amplify")
    print("  • All buttons released: Amplify → Idle")
    print("  • Button 7 pressed 3x: Any state → Test")
    print("  • Any button in Test: Test → Idle")
    print()
    print("Hardware requirements:")
    print("  • 10 buttons on GPIO 22-31")
    print("  • LED strip 1 on GPIO 18")
    print("  • LED strip 2 on GPIO 21") 
    print("  • External 5V power for LED strips")
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
