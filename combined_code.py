import math
import board
import time
import audiomp3
import audiobusio
import synthio
import array
import gc
import digitalio # digitalio is imported but not used for gain control, which is fine

from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware

# --- Global Keypad Setup ---
keybow = PMK(Hardware())
keys = keybow.keys

# --- Global Audio Setup (I2S) ---
I2S_BCLK_PIN = board.GP0      # Bit Clock
I2S_LRC_PIN = board.GP1       # Left-Right Clock (Word Select)
I2S_DIN_PIN = board.GP2       # Data In

audio = audiobusio.I2SOut(I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DIN_PIN)

# --- Define Audio Files and Folder ---
AUDIO_FOLDER = "audio_files/"
AUDIO_FILES = [
    "ape.mp3", "auto.mp3", "baaa.mp3", "ambulance.mp3",
    "dodooo.mp3", "enea.mp3", "huhuh.mp3", "fire_lego.mp3",
    "muh.mp3", "nonna.mp3", "nonno.mp3", "fire_bruder.mp3",
    "mao.mp3", "tata.mp3", "torta.mp3", "biip.mp3", # Button 15 audio
]

# --- GLOBAL MP3 DECODER INSTANCE ---
mp3_decoder = None
try:
    if AUDIO_FILES:
        initial_mp3_path = AUDIO_FOLDER + AUDIO_FILES[0]
        mp3_decoder = audiomp3.MP3Decoder(open(initial_mp3_path, "rb"))
        print(f"MP3Decoder initialized with {initial_mp3_path}")
    else:
        print("WARNING: No audio files defined for MP3Decoder initialization.")
except Exception as e:
    print(f"!!! CRITICAL ERROR: Failed to initialize MP3Decoder globally: {e} !!!")
    print("Consider optimizing your MP3 files (smaller bitrate/samplerate) or using a board with more RAM.")

# --- Global Xylophone Waveforms (Generated once) ---
_sine_waveform_full_volume = None
_sine_waveform_overtone_volume = None

def generate_sine_waveforms_globally():
    global _sine_waveform_full_volume, _sine_waveform_overtone_volume
    if _sine_waveform_full_volume is None:
        def _gen_sine(length=512, scale=1.0):
            waveform = array.array("h", [0] * length)
            for i in range(length):
                waveform[i] = int(math.sin(math.pi * 2 * i / length) * (2**15 - 1) * scale)
            return waveform
        _sine_waveform_full_volume = _gen_sine(scale=1.0)
        _sine_waveform_overtone_volume = _gen_sine(scale=0.5)

generate_sine_waveforms_globally()

# --- NO LONGER NEEDED: Amplifier Gain Control Setup for GP3 ---
# Since gain is hardwired to 12dB, GP3 control is removed.
# You'll physically connect the MAX98357A's GAIN pin to GND.


# --- Mode Switching Variables ---
MODE_AUDIO_PLAYER = 0
MODE_XYLOPHONE = 1

current_mode = MODE_AUDIO_PLAYER # Start with the audio player mode

# --- Special Button Definitions ---
BUTTON_SWITCH_KEY_INDEX = 15 # Bottom right key for mode switch

# A set of all special buttons for easy checking (only B15 remains special)
SPECIAL_BUTTON_INDICES = {
    BUTTON_SWITCH_KEY_INDEX,
}

# --- Long/Short Press Durations ---
SHORT_PRESS_MAX_DURATION = 0.4 # Seconds - a press shorter than this is considered 'short'
LONG_PRESS_MIN_DURATION = 1.0  # Seconds - a press longer than this is considered 'long'

# --- Global Button State Tracking ---
prev_key_states = [False] * 16 # Tracks previous state for ALL keys (for edge detection)

# For special buttons, we also need to track the start time of their press
special_button_press_start_times = {
    idx: 0.0 for idx in SPECIAL_BUTTON_INDICES
}

# --- Global Audio/Synth State for Xylophone Mode ---
_synth = None
_active_notes = {} # Tracks active notes for ALL keys in Xylophone mode

# Variables for tracking Button 15's MP3 sound state
b15_is_playing_mp3 = False # To track if B15 MP3 is currently playing


# --- LED Brightness Control ---
MAX_LED_VALUE_AUDIO = 75 # Max brightness for Audio Player mode
MAX_LED_VALUE_XYLOPHONE = 75 # Max brightness for Xylophone mode

def set_all_leds(r, g, b):
    """Sets all LEDs to a specific color."""
    for i in range(16):
        keys[i].set_led(r, g, b)
    keybow.update()

def flash_leds_white(times, delay):
    """Flashes all LEDs white for visual feedback."""
    for _ in range(times):
        set_all_leds(255, 255, 255)
        time.sleep(delay)
        set_all_leds(0, 0, 0) # Turn off
        time.sleep(delay)
    # Restore colors to reflect the current mode
    set_static_rainbow_colors(current_mode) 

def get_brightness_scaling_factor(mode):
    if mode == MODE_AUDIO_PLAYER:
        return MAX_LED_VALUE_AUDIO / 255.0
    elif mode == MODE_XYLOPHONE:
        return MAX_LED_VALUE_XYLOPHONE / 255.0
    return 0.0 # Default

def get_key_rainbow_color(key_index, mode):
    """Calculates the static rainbow color for a single key based on mode."""
    brightness_scaling_factor = get_brightness_scaling_factor(mode)
    x, y = number_to_xy(key_index)
    hue = (x + y) / (7.0 if mode == MODE_AUDIO_PLAYER else 6.0)
    hue = hue - math.floor(hue)
    r, g, b = hsv_to_rgb(hue, 1, brightness_scaling_factor)
    return r, g, b

def set_static_rainbow_colors(mode):
    """Calculates and sets a static rainbow pattern on the keypad LEDs for ALL keys."""
    for i in range(16):
        r, g, b = get_key_rainbow_color(i, mode)
        keys[i].set_led(r, g, b)
    keybow.update()

def flash_key_green(key_index, times=2, delay=0.05):
    """Flashes a single key green for visual feedback, then restores its original color."""
    original_r, original_g, original_b = get_key_rainbow_color(key_index, current_mode)

    for _ in range(times):
        keys[key_index].set_led(0, 255, 0) # Green
        keybow.update()
        time.sleep(delay)
        keys[key_index].set_led(0, 0, 0) # Off
        keybow.update()
        time.sleep(delay)
    # Restore original color
    keys[key_index].set_led(original_r, original_g, original_b)
    keybow.update()


# --- Main Program Loop ---
print(f"Starting in Mode: {'Audio Player' if current_mode == MODE_AUDIO_PLAYER else 'Xylophone'}")
flash_leds_white(2, 0.1) # Initial feedback
set_static_rainbow_colors(current_mode) # Set initial rainbow colors

while True:
    keybow.update()

    for key_index in range(16):
        current_pressed_state = keys[key_index].pressed
        previous_pressed_state = prev_key_states[key_index]

        # --- Handle Key Press (Edge Detection: Just Pressed) ---
        if current_pressed_state and not previous_pressed_state:
            keys[key_index].set_led(255, 255, 255) # Light up on press (white)
            print(f"\n--- Key {key_index} pressed! ---")
            
            # Store press start time for duration check for special keys
            if key_index in SPECIAL_BUTTON_INDICES:
                special_button_press_start_times[key_index] = time.monotonic()
            
            # --- Play Sound/Note on Press (for all keys, short press behavior) ---
            if current_mode == MODE_AUDIO_PLAYER:
                if key_index < len(AUDIO_FILES):
                    full_audio_path = AUDIO_FOLDER + AUDIO_FILES[key_index]
                    if mp3_decoder:
                        try:
                            audio.stop()
                            gc.collect()
                            mp3_decoder.file = open(full_audio_path, "rb")
                            audio.play(mp3_decoder)
                            if key_index == BUTTON_SWITCH_KEY_INDEX: # For B15 specific flag
                                b15_is_playing_mp3 = True
                            print(f"Playing {full_audio_path}")
                        except Exception as e:
                            print(f"!!! ERROR playing {full_audio_path}: {e} !!!")
                    else:
                        print("MP3Decoder not initialized, cannot play audio.")
                else:
                    print(f"No audio file defined for key {key_index}.")
            
            elif current_mode == MODE_XYLOPHONE:
                # Ensure synth is initialized and playing
                if _synth is None or not audio.playing:
                    try:
                        gc.collect()
                        _synth = synthio.Synthesizer(channel_count=1, sample_rate=22050)
                        audio.play(_synth)
                        print("Synthesizer initialized/resumed playing.")
                    except Exception as e:
                        print(f"!!! ERROR initializing/resuming Synthesizer: {e} !!!")
                        _synth = None # Ensure it's marked as failed
                        continue # Skip playing note if synth failed

                if _synth: # Play note if synth is ready
                    MIDI_NOTES = [
                        48, 49, 50, 51,
                        52, 53, 54, 55,
                        56, 57, 58, 59,
                        60, 61, 62, 63,
                    ]
                    # Specific MIDI note for B15 (mode switch)
                    if key_index == BUTTON_SWITCH_KEY_INDEX:
                        midi_note_to_play = 72 # C6 for B15
                    elif key_index < len(MIDI_NOTES):
                        midi_note_to_play = MIDI_NOTES[key_index]
                    else:
                        print(f"No MIDI note defined for key {key_index}.")
                        continue

                    try:
                        note_frequency = 440 * (2**((midi_note_to_play - 69) / 12))
                        fundamental_envelope = synthio.Envelope(attack_time=0.01, decay_time=0.2, sustain_level=0.1, release_time=0.2)
                        overtone_envelope = synthio.Envelope(attack_time=0.01, decay_time=0.05, sustain_level=0.0, release_time=0.1)
                        note_fundamental = synthio.Note(frequency=note_frequency, waveform=_sine_waveform_full_volume, envelope=fundamental_envelope)
                        note_overtone1 = synthio.Note(frequency=note_frequency * 2.756, waveform=_sine_waveform_overtone_volume, envelope=overtone_envelope)
                        
                        notes_to_play = [note_fundamental, note_overtone1]
                        
                        # Release previous notes for this key if still active
                        if key_index in _active_notes:
                            _synth.release(_active_notes[key_index])
                        
                        _synth.press(notes_to_play)
                        _active_notes[key_index] = notes_to_play # Store for release, for ALL keys
                        print(f"Playing MIDI note {midi_note_to_play} (Key {key_index}), frequency {note_frequency:.2f} Hz")
                    except Exception as e:
                        print(f"!!! ERROR playing MIDI note {midi_note_to_play} for Key {key_index}: {e} !!!")


        # --- Handle Key Release (Edge Detection: Just Released) ---
        elif not current_pressed_state and previous_pressed_state:
            # Restore LED color for the released key
            r, g, b = get_key_rainbow_color(key_index, current_mode)
            keys[key_index].set_led(r, g, b)
            
            # --- Special Button Long Press Detection and Action ---
            if key_index in SPECIAL_BUTTON_INDICES:
                press_duration = time.monotonic() - special_button_press_start_times[key_index]
                print(f"Button {key_index} released. Duration: {press_duration:.3f}s")

                if press_duration >= LONG_PRESS_MIN_DURATION:
                    # --- LONG PRESS ACTION ---
                    print(f"Long press detected for Button {key_index}!")
                    if key_index == BUTTON_SWITCH_KEY_INDEX:
                        print("Switching mode!")
                        audio.stop() # Stop any playing audio
                        # For B15, if it was playing synth, release it (it's in _active_notes now)
                        if current_mode == MODE_XYLOPHONE and key_index in _active_notes:
                            _synth.release(_active_notes[key_index])
                            del _active_notes[key_index]
                        b15_is_playing_mp3 = False # Reset MP3 playing flag

                        # If in Xylophone mode, explicitly release all notes and de-initialize synth
                        if current_mode == MODE_XYLOPHONE:
                            if _synth is not None:
                                _synth.release_all()
                                _active_notes.clear()
                                _synth = None
                                print("Synthesizer de-initialized for mode switch.")
                        
                        flash_leds_white(3, 0.05) # Visual feedback for mode switch

                        # Perform the mode switch
                        if current_mode == MODE_AUDIO_PLAYER:
                            current_mode = MODE_XYLOPHONE
                        else:
                            current_mode = MODE_AUDIO_PLAYER
                        set_static_rainbow_colors(current_mode) # Set new mode's colors
                        time.sleep(0.1) # Small delay after switch
                    
                    # If any of these special keys were playing a synth note (and it was a long press), release it.
                    if current_mode == MODE_XYLOPHONE and key_index in _active_notes:
                        _synth.release(_active_notes[key_index])
                        del _active_notes[key_index]
                        print(f"Note released for Key {key_index} (due to long press).")

                else:
                    # --- SHORT PRESS RELEASE ACTION (for special buttons only) ---
                    # For B15, if it was a short press, handle its Xylophone note release or MP3 flag reset.
                    if key_index == BUTTON_SWITCH_KEY_INDEX:
                        print("Short press detected for B15 (release).")
                        if current_mode == MODE_XYLOPHONE and key_index in _active_notes: # Check if B15 has an active note
                            _synth.release(_active_notes[key_index])
                            del _active_notes[key_index] # Remove from active notes
                            print(f"Note released for Key {key_index}.")
                        b15_is_playing_mp3 = False # Reset MP3 playing flag for B15 (always, regardless of mode)
                    
                    elif current_mode == MODE_XYLOPHONE and key_index in _active_notes:
                        _synth.release(_active_notes[key_index])
                        del _active_notes[key_index]
                        print(f"Note released for Key {key_index}.")
            
            else: # --- Regular Key Release (Keys 0-11) ---
                print(f"--- Key {key_index} released! ---")
                if current_mode == MODE_XYLOPHONE and key_index in _active_notes:
                    _synth.release(_active_notes[key_index])
                    del _active_notes[key_index]
                    print(f"Note released for Key {key_index}")

        # Update the previous state for the next loop iteration
        prev_key_states[key_index] = current_pressed_state
    
    time.sleep(0.01) # Small sleep to yield to other tasks
