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
    from led_system import PixelStripAdapter
    from game_system import GameController, IdleState
    from hybridLogger import HybridLogger
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi with required libraries installed")
    sys.exit(1)


def create_game_system():
    """
    Create and configure the complete game system.
    
    Returns:
        GameController: Configured game controller ready to run
    """
    # Configuration (adjust these for your setup)
    BUTTON_PINS = [22, 23, 24, 25, 26, 27, 28, 29, 30, 31]  # 10 buttons
    LED_STRIP_1_GPIO = 18
    LED_STRIP_2_GPIO = 21
    LED_COUNT = 300
    LED_BRIGHTNESS = 26  # 10% brightness for testing
    TARGET_FPS = 30
    
    # Initialize logging
    main_logger = HybridLogger("GameSystem")
    game_logger = main_logger.get_class_logger("GameController", logging.INFO)
    button_logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
    
    try:
        # Initialize button reader
        button_reader = ButtonReader(
            button_pins=BUTTON_PINS,
            logger=button_logger,
            pull_mode=GPIO.PUD_OFF  # Assuming external pull circuits
        )
        
        # Initialize LED strips
        led_strips = []
        
        # Strip 1
        strip1 = PixelStripAdapter(
            led_count=LED_COUNT,
            gpio_pin=LED_STRIP_1_GPIO,
            freq_hz=800000,
            dma=10,
            invert=False,
            brightness=LED_BRIGHTNESS,
            channel=0
        )
        led_strips.append(strip1)
        
        # Strip 2  
        strip2 = PixelStripAdapter(
            led_count=LED_COUNT,
            gpio_pin=LED_STRIP_2_GPIO,
            freq_hz=800000,
            dma=5,
            invert=False,
            brightness=LED_BRIGHTNESS,
            channel=0
        )
        led_strips.append(strip2)
        
        # Clear strips initially
        from led_system.pixel import Pixel
        black = Pixel(0, 0, 0)
        for strip in led_strips:
            strip[:] = black
            strip.show()
        
        # Create game controller
        game_controller = GameController(
            button_reader=button_reader,
            led_strips=led_strips,
            target_fps=TARGET_FPS,
            logger=game_logger
        )
        
        game_logger.info("Game system initialized successfully")
        game_logger.info(f"Configuration: {len(BUTTON_PINS)} buttons, {len(led_strips)} LED strips, {TARGET_FPS} FPS")
        
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
        game_controller.run_with_frame_limiting()
        
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
