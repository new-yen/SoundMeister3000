# SPDX-License-Identifier: MIT

import math
import board
import audiomp3
import audiobusio
import time

from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware

# --- Audio Setup (I2S) ---
# These pins match the primary Adafruit "Pico I2S MP3" guide.
# https://learn.adafruit.com/mp3-playback-rp2040/pico-i2s-mp3
I2S_BCLK_PIN = board.GP0    # Bit Clock
I2S_LRC_PIN = board.GP1     # Left-Right Clock (Word Select)
I2S_DIN_PIN = board.GP2     # Data In

# --- Create a single, persistent audio object ---
# This object will be used for all audio playback.
# By creating it once, we can stop and start playback without reinitializing the hardware.
audio = audiobusio.I2SOut(I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DIN_PIN)

# Define the folder where your audio files are located
AUDIO_FOLDER = "audio_files/" # Make sure this folder exists on your CIRCUITPY drive!

# Define your audio files here.
# The index corresponds to the key number (0-15).
# These filenames will be combined with the AUDIO_FOLDER path.
AUDIO_FILES = [
    "ape.mp3",
    "auto.mp3",
    "baaa.mp3",
    "ambulance.mp3",
    "dodooo.mp3",
    "enea.mp3",
    "huhuh.mp3",
    "fire_lego.mp3",
    "muh.mp3",
    "nonna.mp3",
    "nonno.mp3",
    "fire_bruder.mp3",
    "mao.mp3",
    "tata.mp3",
    "torta.mp3",
    "biip.mp3",
]

# --- Keypad Setup ---
keybow = PMK(Hardware())

# BRIGHTNESS CONTROL: Set the maximum desired value for any R, G, or B component (0-255).
MAX_LED_VALUE = 50 # Example: Cap R, G, B at 50
# Calculate the scaling factor for the 'Value' component in HSV (0.0 to 1.0).
BRIGHTNESS_SCALING_FACTOR = MAX_LED_VALUE / 255.0

keys = keybow.keys

# List to store the static rainbow colors for each key
static_key_colors = [None] * 16

def set_static_rainbow_colors():
    """Calculates and sets a static rainbow pattern on the keypad LEDs.
    The colors are also stored in static_key_colors for later use."""
    for i in range(16):
        x, y = number_to_xy(i)
        # Calculate hue based on key position for a static rainbow spread
        # The divisor (e.g., 7.0) can be adjusted to change the color spread.
        hue = (x + y) / 7.0
        # Ensure hue is between 0.0 and 1.0
        hue = hue - math.floor(hue)
        # Apply brightness scaling via the 'value' (v) parameter in HSV
        r, g, b = hsv_to_rgb(hue, 1, BRIGHTNESS_SCALING_FACTOR)
        keys[i].set_led(r, g, b)
        # Store the set color for this key (though not strictly necessary without blinking)
        static_key_colors[i] = (r, g, b)

# Initialize the keypad with the static rainbow pattern at startup
set_static_rainbow_colors()
keybow.update() # Apply the initial colors

print("Pico RGB Keypad Base project started! (Using I2S Audio - Interruptible)")

while True:
    # Always update the keypad state and LEDs in the main loop.
    keybow.update()

    for key_index in range(16):
        key = keys[key_index]
        if key.pressed:
            print(f"\n--- Key {key_index} pressed! ---")

            # --- Play audio file ---
            if key_index < len(AUDIO_FILES):
                full_audio_path = AUDIO_FOLDER + AUDIO_FILES[key_index]
                try:
                    # Stop any currently playing audio before starting the new one.
                    audio.stop()
                    print("Audio stopped (if playing).")

                    # Open the new MP3 file and start playing it.
                    decoder = audiomp3.MP3Decoder(open(full_audio_path, "rb"))
                    audio.play(decoder)
                    print(f"Playing {full_audio_path}")

                    # The 'while audio.playing' loop is intentionally removed.
                    # This makes the program non-blocking, allowing it to immediately
                    # detect another key press while the sound is still playing.

                except Exception as e:
                    print(f"!!! ERROR playing {full_audio_path}: {e} !!!")
            else:
                print(f"No audio file defined for key {key_index}.")
