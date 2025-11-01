#!/usr/bin/env python3
"""
Simple LED debugging script - tests one strip at a time
"""
import time
from rpi_ws281x import PixelStrip, Color
import sys

def test_single_strip(gpio_pin, pwm_channel, dma_channel):
    """Test a single LED strip with specific PWM and DMA channels"""
    name = f"GPIO {gpio_pin}, PWM {pwm_channel}, DMA {dma_channel}"
    print(f"\n🔍 Testing {name}")
    print(f"   GPIO: {gpio_pin} | PWM Channel: {pwm_channel} | DMA Channel: {dma_channel}")
    print("-" * 60)
    
    try:
        # Configuration with specified parameters
        strip = PixelStrip(
            300,           # LED count (ALL 300 LEDs)
            gpio_pin,      # GPIO pin
            800000,        # Frequency
            dma_channel,   # DMA channel (parameter)
            False,         # Invert
            50,            # Brightness (20% for testing)
            pwm_channel    # PWM channel (parameter)
        )
        
        print(f"✅ Strip object created")
        
        # Initialize
        strip.begin()
        print(f"✅ Strip initialized")
        
        try:
            while True:
                # Red wipe animation from 0 to 299
                print(f"🔴 Red wipe animation 0→299...")
                delay_per_led = 0.01  # Fast wipe - 10ms per LED = 3 seconds total
                for i in range(300):
                    strip.setPixelColor(i, Color(255, 0, 0))  # Red
                    strip.show()
                    time.sleep(delay_per_led)
                
                # Green wipe animation from 0 to 299  
                print(f"🟢 Green wipe animation 0→299...")
                for i in range(300):
                    strip.setPixelColor(i, Color(0, 255, 0))  # Green
                    strip.show()
                    time.sleep(delay_per_led)
                
                # No pause - continuous wipe pattern
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Config interrupted, moving to next...")
        
        print(f"✅ {name} test completed!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR with {name}: {e}")
        return False

def main():
    """Main debugging function"""
    print("🚨 PWM/DMA CHANNEL TESTING TOOL 🚨")
    print("=" * 60)
    
    # Test configurations: (gpio, pwm_channel, dma_channel)
    test_configs = [
        (10, 0, 5),
        (12, 0, 5),
        (13, 1, 5),
        (18, 0, 5),   
        (19, 1, 5),  
        (20, 1, 5),
        (21, 0, 5),
    ]
    
    try:
        for gpio, pwm_ch, dma_ch in test_configs:
            name = f"GPIO {gpio}, PWM {pwm_ch}, DMA {dma_ch}"
            print(f"\n" + "=" * 60)
            success = test_single_strip(gpio, pwm_ch, dma_ch)
            
            if success:
                print(f"✅ {name} - WORKS!")
            else:
                print(f"❌ {name} - FAILED!")
        
        # All tests completed normally
        print(f"\n" + "=" * 60)
        print(f"🏁 All GPIO tests completed!")
        print(f"🚪 Exiting debug_leds.py...")
        
    except KeyboardInterrupt:
        print(f"\n\n🛑 Script terminated by user (Ctrl+C)")
        print(f"🚪 Exiting debug_leds.py...")
    
    finally:
        # Force exit regardless of how we got here
        import sys
        import os
        print("🚨 Force killing process...")
        os._exit(0)  # Nuclear exit - bypasses cleanup
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n🛑 Force exit!")
        import sys
        sys.exit(0)
