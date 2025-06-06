# SPDX-FileCopyrightText: 2021 Sandy Macdonald / 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import math
import board
import audiomp3
import audiopwmio
import time

from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware

# --- Audio Setup ---
# Define the audio output pin. Using GP0 as confirmed working.
AUDIO_OUT_PIN = board.GP0 # Make sure this matches your physical connection!

# Define the folder where your audio files are located
AUDIO_FOLDER = "audio_files/" # Make sure this folder exists on your CIRCUITPY drive!

# Define your audio files here.
# The index corresponds to the key number (0-15).
# These filenames will be combined with the AUDIO_FOLDER path.
AUDIO_FILES = [
    "ape.mp3",
    "auto.mp3",
    "baaa.mp3",
    "biip.mp3",
    "dodooo.mp3",
    "enea.mp3",
    "huhuh.mp3",
    "mao.mp3",
    "muh.mp3",
    "nonna.mp3",
    "nonno.mp3",
    "oink.mp3",
    "pfff.mp3",
    "tata.mp3",
    "torta.mp3",
    "vroom.mp3",
]

# --- Keypad Setup ---
keybow = PMK(Hardware())

# BRIGHTNESS CONTROL: Set the maximum desired value for any R, G, or B component (0-255).
MAX_LED_VALUE = 50 # Example: Cap R, G, B at 50
# Calculate the scaling factor for the 'Value' component in HSV (0.0 to 1.0).
BRIGHTNESS_SCALING_FACTOR = MAX_LED_VALUE / 255.0

keys = keybow.keys

# Initial state variables for the rainbow animation
rainbow_step = 0
current_hue_offset = 0.0 # This will store the hue of the last pressed key

# Flag to indicate if the rainbow animation should be active
rainbow_mode = True

def set_key_colors_rainbow(step_value):
    """Sets the keypad LEDs to a continuous rainbow pattern."""
    for i in range(16):
        x, y = number_to_xy(i)
        hue = (x + y + (step_value / 20)) / 8
        hue = hue - int(hue)
        hue = hue - math.floor(hue)
        # Apply brightness scaling via the 'value' (v) parameter in HSV
        r, g, b = hsv_to_rgb(hue, 1, BRIGHTNESS_SCALING_FACTOR)
        keys[i].set_led(r, g, b)

def set_key_colors_offset_hue(start_hue):
    """Sets the keypad LEDs with hues increasing from a starting hue."""
    for i in range(16):
        hue = (start_hue + (i * 0.05)) % 1.0
        # Apply brightness scaling via the 'value' (v) parameter in HSV
        r, g, b = hsv_to_rgb(hue, 1, BRIGHTNESS_SCALING_FACTOR)
        keys[i].set_led(r, g, b)

# Initialize the keypad with the rainbow pattern at startup
set_key_colors_rainbow(rainbow_step)
keybow.update() # Apply the initial colors

print("Pico RGB Keypad Base project started!")

while True:
    keybow.update()

    if rainbow_mode:
        rainbow_step += 1
        set_key_colors_rainbow(rainbow_step)

    for key_index in range(16):
        key = keys[key_index]
        if key.pressed:
            print(f"\n--- Key {key_index} pressed! ---")

            # Stop rainbow mode and activate offset hue mode
            rainbow_mode = False

            # Get the current color of the pressed key to use as the starting hue
            x, y = number_to_xy(key_index)
            hue_at_press = (x + y + (rainbow_step / 20)) / 8
            hue_at_press = hue_at_press - int(hue_at_press)
            hue_at_press = hue_at_press - math.floor(hue_at_press)

            current_hue_offset = hue_at_press
            set_key_colors_offset_hue(current_hue_offset)

            # Play audio file
            if key_index < len(AUDIO_FILES):
                full_audio_path = AUDIO_FOLDER + AUDIO_FILES[key_index]
                try:
                    # Create the PWMAudioOut object *before* playing
                    # This is done here to ensure a fresh audio output instance
                    # and to allow deinitialization after playback for hiss removal.
                    audio = audiopwmio.PWMAudioOut(AUDIO_OUT_PIN)

                    if audio.playing:
                        audio.stop()
                        print("Audio interrupted (pre-play stop).")

                    decoder = audiomp3.MP3Decoder(open(full_audio_path, "rb"))
                    audio.play(decoder)
                    print(f"Playing {full_audio_path}")

                    # Wait for audio to finish playing, keeping LEDs updated
                    while audio.playing:
                        keybow.update() # Keep LED updates going
                        time.sleep(0.01) # Short delay to yield to other processes

                    # Deinitialize the audio output AFTER it has finished playing to eliminate hiss
                    audio.deinit()
                    print("Audio finished, deinitialized.")

                except Exception as e:
                    print(f"!!! ERROR playing {full_audio_path}: {e} !!!")
                    # Ensure deinit() is called even if an error occurs during playback
                    if 'audio' in locals() and audio is not None and hasattr(audio, 'deinit'):
                        audio.deinit()
            else:
                print(f"No audio file defined for key {key_index}.")
