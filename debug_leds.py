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
                # Test 1: Turn on ALL 300 LEDs green
                print(f"🟢 Setting ALL 300 LEDs to GREEN...")
                for i in range(300):
                    strip.setPixelColor(i, Color(0, 255, 0))
                strip.show()
                time.sleep(2)
                
                # Test 2: Turn on ALL 300 LEDs red  
                print(f"🔴 Setting ALL 300 LEDs to RED...")
                for i in range(300):
                    strip.setPixelColor(i, Color(255, 0, 0))
                strip.show()
                time.sleep(2)
                
                # Test 3: White wipe animation from 0 to 299 over 3 seconds
                print(f"⚪ White wipe animation 0→299 (3 seconds)...")
                
                # Wipe animation (overrides red)
                delay_per_led = 3.0 / 300  # 3 seconds / 300 LEDs
                for i in range(300):
                    strip.setPixelColor(i, Color(255, 255, 255))  # White
                    strip.show()
                    time.sleep(delay_per_led)
                
                # Test 4: Turn off all
                print(f"⚫ Turning off all LEDs...")
                for i in range(300):
                    strip.setPixelColor(i, Color(0, 0, 0))
                strip.show()
                
                # Brief pause before repeating (press Ctrl+C to stop, then ENTER for next config)
                time.sleep(0.5)
                
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
        (12, 0, 10),
        (13, 1, 5), 
        (12, 0, 10),         
    ]
    
    for gpio, pwm_ch, dma_ch in test_configs:
        name = f"GPIO {gpio}, PWM {pwm_ch}, DMA {dma_ch}"
        print(f"\n" + "=" * 60)
        success = test_single_strip(gpio, pwm_ch, dma_ch)
        
        if success:
            print(f"✅ {name} - WORKS!")
        else:
            print(f"❌ {name} - FAILED!")
        
if __name__ == "__main__":
    main()
