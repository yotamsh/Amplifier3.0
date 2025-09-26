import time
from rpi_ws281x import PixelStrip, Color

# Configuration
LED_COUNT = 30        # Number of LEDs
LED_PIN = 18          # GPIO pin (must support PWM)
LED_FREQ_HZ = 800000  # Signal frequency (800kHz)
LED_DMA = 10          # DMA channel
LED_BRIGHTNESS = 255  # 0-255
LED_INVERT = False    # Signal inversion
LED_CHANNEL = 0       # PWM channel

# Initialize
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def color_wipe(strip, color, wait_ms=50):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def test():
    try:
        while True:
            color_wipe(strip, Color(255, 0, 0))    # Red
            color_wipe(strip, Color(0, 255, 0))    # Green  
            color_wipe(strip, Color(0, 0, 255))    # Blue
    except KeyboardInterrupt:
        color_wipe(strip, Color(0, 0, 0), 10)     # Turn off

if __name__ == "__main__":
    test()