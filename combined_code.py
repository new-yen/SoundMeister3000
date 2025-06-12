import math
import board
import time
import audiomp3
import audiobusio
import synthio
import array
import gc

from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware

# --- Global Keypad Setup ---
keybow = PMK(Hardware())
keys = keybow.keys

# --- Global Audio Setup (I2S) ---
I2S_BCLK_PIN = board.GP0     # Bit Clock
I2S_LRC_PIN = board.GP1      # Left-Right Clock (Word Select)
I2S_DIN_PIN = board.GP2      # Data In

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
# Create the MP3Decoder object once at startup.
# It needs a file to initialize, so we use the first one.
# This pre-allocates its large internal buffer.
mp3_decoder = None
try:
    if AUDIO_FILES: # Ensure there's at least one file
        initial_mp3_path = AUDIO_FOLDER + AUDIO_FILES[0]
        mp3_decoder = audiomp3.MP3Decoder(open(initial_mp3_path, "rb"))
        print(f"MP3Decoder initialized with {initial_mp3_path}")
    else:
        print("WARNING: No audio files defined for MP3Decoder initialization.")
except Exception as e:
    print(f"!!! CRITICAL ERROR: Failed to initialize MP3Decoder globally: {e} !!!")
    print("Consider optimizing your MP3 files (smaller bitrate/samplerate) or using a board with more RAM.")
    # In a non-error state, we might still want to print but allow program to continue if possible.
    # For global init, if this fails, MP3 mode won't work, so a clear error is good.

# --- Global Xylophone Waveforms (Generated once) ---
_sine_waveform_full_volume = None
_sine_waveform_overtone_volume = None
# Removed: _sine_waveform_b15_quiet_volume = None

def generate_sine_waveforms_globally():
    global _sine_waveform_full_volume, _sine_waveform_overtone_volume
    # Only generate once
    if _sine_waveform_full_volume is None:
        def _gen_sine(length=512, scale=1.0):
            waveform = array.array("h", [0] * length)
            for i in range(length):
                waveform[i] = int(math.sin(math.pi * 2 * i / length) * (2**15 - 1) * scale)
            return waveform
        _sine_waveform_full_volume = _gen_sine(scale=1.0)
        _sine_waveform_overtone_volume = _gen_sine(scale=0.5)

# Call this function once at program startup
generate_sine_waveforms_globally()

# --- Mode Switching Variables ---
MODE_AUDIO_PLAYER = 0
MODE_XYLOPHONE = 1

current_mode = MODE_AUDIO_PLAYER # Start with the audio player mode

# Button 15 (bottom right key) is key_index 15
BUTTON_SWITCH_KEY_INDEX = 15

# --- Long/Short Press Durations for Button 15 ---
SHORT_PRESS_MAX_DURATION = 0.4 # Seconds - a press shorter than this is considered 'short'
LONG_PRESS_MIN_DURATION = 1  # Seconds - a press longer than this is considered 'long'

# Variables for tracking Button 15's press timing and sound state
b15_press_start_time = 0.0
prev_b15_state = False # Track previous state of button 15
b15_active_synth_notes = None # To track synth notes for B15 if playing
b15_is_playing_mp3 = False # To track if B15 MP3 is currently playing

# --- LED Brightness Control ---
MAX_LED_VALUE_AUDIO = 100 # Max brightness for Audio Player mode
MAX_LED_VALUE_XYLOPHONE = 100 # Max brightness for Xylophone mode

def set_all_leds(r, g, b):
    """Sets all LEDs to a specific color."""
    for i in range(16):
        keys[i].set_led(r, g, b)
    keybow.update()

def flash_leds_white(times, delay):
    """Flashes all LEDs white for visual feedback."""
    original_mode = current_mode # Store current mode to restore colors after flash
    for _ in range(times):
        set_all_leds(255, 255, 255)
        time.sleep(delay)
        set_all_leds(0, 0, 0) # Turn off
        time.sleep(delay)
    # Restore original colors after flash
    set_static_rainbow_colors(original_mode)

def get_brightness_scaling_factor(mode):
    if mode == MODE_AUDIO_PLAYER:
        return MAX_LED_VALUE_AUDIO / 255.0
    elif mode == MODE_XYLOPHONE:
        return MAX_LED_VALUE_XYLOPHONE / 255.0
    return 0.0 # Default

def set_static_rainbow_colors(mode):
    """Calculates and sets a static rainbow pattern on the keypad LEDs
       based on the current mode's brightness setting."""
    brightness_scaling_factor = get_brightness_scaling_factor(mode)
    for i in range(16):
        x, y = number_to_xy(i)
        # Adjust divisor for desired color spread, slightly different for each mode
        hue = (x + y) / (7.0 if mode == MODE_AUDIO_PLAYER else 6.0)
        hue = hue - math.floor(hue)
        r, g, b = hsv_to_rgb(hue, 1, brightness_scaling_factor)
        keys[i].set_led(r, g, b)
    keybow.update()

# --- Code 1: MP3 Audio Player ---
# Global state for audio player mode's key tracking
_audio_player_prev_key_states = [False] * 16

# This function will now only handle keys 0-14
def run_audio_player_other_keys():
    global _audio_player_prev_key_states, mp3_decoder

    set_static_rainbow_colors(MODE_AUDIO_PLAYER)

    for key_index in range(16):
        if key_index == BUTTON_SWITCH_KEY_INDEX: # Skip button 15, it's handled in main loop
            _audio_player_prev_key_states[key_index] = keys[key_index].pressed # Still update its state
            continue

        key = keys[key_index]
        current_pressed_state = key.pressed
        previous_pressed_state = _audio_player_prev_key_states[key_index]

        if current_pressed_state and not previous_pressed_state: # Key was just pressed
            print(f"\n--- Key {key_index} pressed! (Audio Player) ---")

            if key_index < len(AUDIO_FILES):
                full_audio_path = AUDIO_FOLDER + AUDIO_FILES[key_index]
                if mp3_decoder:
                    try:
                        audio.stop()
                        gc.collect()
                        mp3_decoder.file = open(full_audio_path, "rb")
                        audio.play(mp3_decoder)
                        keys[key_index].set_led(255,255,255) # Light up pressed key
                        print(f"Playing {full_audio_path}")
                    except Exception as e:
                        print(f"!!! ERROR playing {full_audio_path}: {e} !!!")
                        # No longer indicate global error state, just print and continue
                else:
                    print("MP3Decoder not initialized, cannot play audio.")
            else:
                print(f"No audio file defined for key {key_index}.")
        elif not current_pressed_state and previous_pressed_state: # Key was just released
            # Restore LED color for the released key
            x, y = number_to_xy(key_index)
            hue = (x + y) / 7.0
            hue = hue - math.floor(hue)
            r, g, b = hsv_to_rgb(hue, 1, get_brightness_scaling_factor(MODE_AUDIO_PLAYER))
            keys[key_index].set_led(r, g, b)

        _audio_player_prev_key_states[key_index] = current_pressed_state
        time.sleep(0.001)


# --- Code 2: Synthio Xylophone ---
_synth = None
_active_notes = {} # Tracks active notes for keys 0-14
_xylophone_prev_key_states = [False] * 16
_static_xylophone_key_colors = [None] * 16

# This function will now only handle keys 0-14
def run_xylophone_other_keys():
    global _synth, _active_notes, _xylophone_prev_key_states, _static_xylophone_key_colors

    # If synth is not initialized or was de-initialized
    if _synth is None:
        try:
            gc.collect()
            _synth = synthio.Synthesizer(channel_count=1, sample_rate=22050)
            audio.play(_synth)
            print("Synthesizer initialized and started playing.")
        except Exception as e:
            print(f"!!! ERROR initializing Synthesizer: {e} !!!")
            # No longer indicate global error state, just print and return from this loop iteration
            return
    else:
        if not audio.playing:
            try:
                audio.play(_synth)
                print("Synthesizer resumed playing.")
            except Exception as e:
                print(f"!!! ERROR resuming Synthesizer: {e} !!!")
                # No longer indicate global error state, just print and return from this loop iteration
                return

    # Envelopes remain local as they are small and tied to note creation
    fundamental_envelope = synthio.Envelope(
        attack_time=0.01, decay_time=0.2, sustain_level=0.1, release_time=0.2,
    )
    overtone_envelope = synthio.Envelope(
        attack_time=0.01, decay_time=0.05, sustain_level=0.0, release_time=0.1,
    )

    MIDI_NOTES = [
        48, 49, 50, 51,
        52, 53, 54, 55,
        56, 57, 58, 59,
        60, 61, 62, 63,
    ]

    def set_xylophone_rainbow_colors():
        brightness_scaling_factor = get_brightness_scaling_factor(MODE_XYLOPHONE)
        for i in range(16):
            x, y = number_to_xy(i)
            hue = (x + y) / 6.0
            hue = hue - math.floor(hue)
            r, g, b = hsv_to_rgb(hue, 1, brightness_scaling_factor)
            keys[i].set_led(r, g, b)
            _static_xylophone_key_colors[i] = (r, g, b)
        keybow.update()

    set_xylophone_rainbow_colors()

    for key_index in range(16):
        if key_index == BUTTON_SWITCH_KEY_INDEX: # Skip button 15, it's handled in main loop
            _xylophone_prev_key_states[key_index] = keys[key_index].pressed # Still update its state
            continue

        key = keys[key_index]
        current_pressed_state = key.pressed
        previous_pressed_state = _xylophone_prev_key_states[key_index]

        if current_pressed_state and not previous_pressed_state: # Key was just pressed (edge detection)
            print(f"\n--- Key {key_index} pressed! (Xylophone) ---")
            if key_index < len(MIDI_NOTES):
                key.set_led(255, 255, 255) # Set LED to white when pressed

                midi_note = MIDI_NOTES[key_index]
                try:
                    note_frequency = 440 * (2**((midi_note - 69) / 12))

                    note_fundamental = synthio.Note(
                        frequency=note_frequency,
                        waveform=_sine_waveform_full_volume, # Using full volume waveform for general keys
                        envelope=fundamental_envelope,
                    )
                    note_overtone1 = synthio.Note(
                        frequency=note_frequency * 2.756,
                        waveform=_sine_waveform_overtone_volume,
                        envelope=overtone_envelope,
                    )
                    notes_to_play = [note_fundamental, note_overtone1]

                    if key_index in _active_notes:
                        _synth.release(_active_notes[key_index])
                    
                    _synth.press(notes_to_play)
                    _active_notes[key_index] = notes_to_play

                    print(f"Playing MIDI note {midi_note} (Key {key_index}), frequency {note_frequency:.2f} Hz")
                except Exception as e:
                    print(f"!!! ERROR playing MIDI note {midi_note} for Key {key_index}: {e} !!!")
                    # No longer indicate global error state, just print and continue
            else:
                print(f"No MIDI note defined for key {key_index}.")

        elif not current_pressed_state and previous_pressed_state: # Key was just released (edge detection)
            print(f"--- Key {key_index} released! (Xylophone) ---")
            r, g, b = _static_xylophone_key_colors[key_index]
            key.set_led(r, g, b)

            if key_index in _active_notes:
                _synth.release(_active_notes[key_index])
                del _active_notes[key_index]
                print(f"Note released for Key {key_index}")
        
        _xylophone_prev_key_states[key_index] = current_pressed_state
        time.sleep(0.001)

# --- Main Program Loop ---
print(f"Starting in Mode: {'Audio Player' if current_mode == MODE_AUDIO_PLAYER else 'Xylophone'}")
flash_leds_white(2, 0.1)

while True:
    keybow.update()

    key_switch_button = keys[BUTTON_SWITCH_KEY_INDEX]
    current_b15_state = key_switch_button.pressed
    
    # --- Button 15 Press Handling (Immediate Sound/Note) ---
    if current_b15_state and not prev_b15_state: # Button 15 was just pressed
        b15_press_start_time = time.monotonic()
        print(f"Button {BUTTON_SWITCH_KEY_INDEX} pressed!")

        # Always light up B15 LED on press
        key_switch_button.set_led(255, 255, 255)

        if current_mode == MODE_XYLOPHONE:
            # IMPORTANT: Ensure synth is initialized if not already (e.g., if just switched from MP3 player)
            if _synth is None:
                try:
                    gc.collect()
                    _synth = synthio.Synthesizer(channel_count=1, sample_rate=22050)
                    audio.play(_synth)
                    print("Synthesizer initialized for B15 press.")
                except Exception as e:
                    print(f"!!! ERROR initializing Synthesizer for B15: {e} !!!")
                    # No longer indicate global error state, just print and continue
                    continue # Skip rest of this loop iteration if synth fails

            # Play Xylophone note immediately
            midi_note = 72 # C6
            note_frequency = 440 * (2**((midi_note - 69) / 12))
            
            # These envelopes are small enough to define here, or could be global if desired
            fundamental_envelope = synthio.Envelope(attack_time=0.01, decay_time=0.2, sustain_level=0.1, release_time=0.2)
            overtone_envelope = synthio.Envelope(attack_time=0.01, decay_time=0.05, sustain_level=0.0, release_time=0.1)

            note_fundamental = synthio.Note(
                frequency=note_frequency,
                waveform=_sine_waveform_full_volume,
                envelope=fundamental_envelope,
            )
            note_overtone1 = synthio.Note(
                frequency=note_frequency * 2.756,
                waveform=_sine_waveform_overtone_volume,
                envelope=overtone_envelope,
            )
            b15_active_synth_notes = [note_fundamental, note_overtone1] # Store for release
            _synth.press(b15_active_synth_notes)
            print(f"Playing B15 MIDI note {midi_note} (on press).")

        elif current_mode == MODE_AUDIO_PLAYER:
            # Play MP3 immediately
            full_audio_path = AUDIO_FOLDER + AUDIO_FILES[BUTTON_SWITCH_KEY_INDEX]
            if mp3_decoder:
                try:
                    audio.stop()
                    gc.collect()
                    mp3_decoder.file = open(full_audio_path, "rb")
                    audio.play(mp3_decoder)
                    b15_is_playing_mp3 = True # Indicate B15 MP3 is active
                    print(f"Playing B15 MP3 (on press): {full_audio_path}")
                except Exception as e:
                    print(f"!!! ERROR playing B15 MP3: {e} !!!")
                    # No longer indicate global error state, just print and continue
            else:
                print("MP3Decoder not initialized, cannot play B15 MP3.")


    # --- Button 15 Release Handling (Stop Sound or Switch Mode) ---
    elif not current_b15_state and prev_b15_state: # Button 15 was just released
        press_duration = time.monotonic() - b15_press_start_time
        print(f"Button {BUTTON_SWITCH_KEY_INDEX} released. Duration: {press_duration:.3f}s")

        # Restore B15 LED color based on current mode
        x, y = number_to_xy(BUTTON_SWITCH_KEY_INDEX)
        current_brightness_factor = get_brightness_scaling_factor(current_mode)
        # Use specific hue based on current mode, similar to set_static_rainbow_colors
        hue = (x + y) / (7.0 if current_mode == MODE_AUDIO_PLAYER else 6.0)
        hue = hue - math.floor(hue)
        r, g, b = hsv_to_rgb(hue, 1, current_brightness_factor)
        key_switch_button.set_led(r, g, b)

        if press_duration >= LONG_PRESS_MIN_DURATION:
            # --- LONG PRESS: SWITCH MODE ---
            print("Long press detected! Switching mode!")
            audio.stop() # Stop any playing audio (including B15's initial sound)
            
            # Clear B15 specific sound states
            b15_active_synth_notes = None
            b15_is_playing_mp3 = False

            # If currently in Xylophone mode, explicitly release notes and de-initialize synth
            if current_mode == MODE_XYLOPHONE:
                if _synth is not None:
                    _synth.release_all() # Release all notes from other keys too
                    _active_notes.clear() # Clear tracking for other keys
                    _synth = None # Force re-initialization of synth
                    print("Synthesizer de-initialized for mode switch.")
            
            flash_leds_white(3, 0.05) # Visual feedback for mode switch

            # Perform the mode switch
            if current_mode == MODE_AUDIO_PLAYER:
                current_mode = MODE_XYLOPHONE
            else:
                current_mode = MODE_AUDIO_PLAYER
            
            time.sleep(0.1) # Small delay after switch
            
        else: # press_duration < SHORT_PRESS_MAX_DURATION
            # --- SHORT PRESS: Manage B15's sound/note (already playing from press) ---
            print("Short press detected! Button 15's sound should have already started.")
            if current_mode == MODE_XYLOPHONE and b15_active_synth_notes is not None:
                _synth.release(b15_active_synth_notes)
                b15_active_synth_notes = None # Clear active note reference
            # For MP3, if it was started, it will continue playing until it finishes
            # or is stopped by another button/mode switch.
            b15_is_playing_mp3 = False # Reset MP3 playing flag for B15


    prev_b15_state = current_b15_state # Update the previous state for the next loop

    # --- Run the currently active mode's code for OTHER keys (0-14) ---
    # These functions are now responsible ONLY for keys 0-14.
    if current_mode == MODE_AUDIO_PLAYER:
        run_audio_player_other_keys()
    elif current_mode == MODE_XYLOPHONE:
        run_xylophone_other_keys()
    
    time.sleep(0.01) # Small sleep to yield to other tasks
