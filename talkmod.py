import keyboard
import pyaudio
import wave
import speech_recognition as sr

def record_audio(filename="audio.wav"):
    """Records audio while the SPACE key is held and saves it as a WAV file."""
    chunk = 1024  # Bytes per chunk
    samprate = 44100  # Sampling rate
    channels = 1
    format = pyaudio.paInt16  # Audio format

    audio = pyaudio.PyAudio()

    print("\nPress and hold SPACE to start recording... (Press ESC to exit)")
    
    keyboard.wait("space")  # Wait until SPACE is pressed
    print("Recording started... Release SPACE to stop.")

    # Open audio stream
    audio_stream = audio.open(format=format, channels=channels, rate=samprate,
                              input=True, frames_per_buffer=chunk)

    frames = []

    # Record while SPACE is held down
    while keyboard.is_pressed("space"):
        data = audio_stream.read(chunk)
        frames.append(data)

    print("Recording stopped.")

    # Stop and close the stream
    audio_stream.stop_stream()
    audio_stream.close()
    audio.terminate()

    # Save audio to WAV file
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(format))
        wf.setframerate(samprate)
        wf.writeframes(b"".join(frames))

    return filename  # Return the filename for further processing


def transcribe_audio(filename="audio.wav"):
    """Transcribes audio from a WAV file and returns the recognized text."""
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(filename) as source:
            audio_data = recognizer.record(source)
            result = recognizer.recognize_google(audio_data)
            return result  # Return the transcription
    except sr.UnknownValueError:
        return "Speech recognition could not understand the audio."
    except sr.RequestError as e:
        return f"Speech recognition request failed: {e}"


def record_and_transcribe():
    """Records audio and returns the transcribed text."""
    audio_file = record_audio()
    transcript = transcribe_audio(audio_file)
    return transcript

if __name__ == "__main__":
    while True:
        transcript = record_and_transcribe()
        print("Recognized text:", transcript)

        # If speech recognition fails, restart the loop
        if transcript == "Speech recognition could not understand the audio.":
            continue  

        # Save transcript to file
        with open("transcription.txt", "a", encoding="utf-8") as f:
            f.write(transcript + "\n")

        print("Press SPACE to record again, or ESC to exit.")
        
        while True:  # Wait for user input
            if keyboard.is_pressed("esc"):
                print("Exiting...")
                exit()
            elif keyboard.is_pressed("space"):
                break  # Restart the loop