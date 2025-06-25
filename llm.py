import json
import re
import threading
import queue
import time
import numpy as np
import sounddevice as sd
from ollama import chat
from piper import PiperVoice
# SpeechRecognition is only needed if you use the voice input function
# import speech_recognition as sr

# --- Configuration ---
OLLAMA_MODEL = "qwen3:1.7b"
WAKE_WORD = "Phil"
VOICE_MODEL_PATH = "en_us.onnx" # Path to your .onnx voice file

# --- Globals ---
messages = [{"role": "system", "content": f"You are a helpful AI assistant called {WAKE_WORD}."}]
tts_queue = queue.Queue()
speaking_in_progress = False

# --- Load Piper Voice Model ---
print("Loading voice model...")
try:
    voice = PiperVoice.load(VOICE_MODEL_PATH)
    sample_rate = voice.config.sample_rate
    print("Voice model loaded successfully.")
except Exception as e:
    print(f"Error loading voice model: {e}")
    print("Please ensure the model files are downloaded and in the correct path.")
    exit()

# ---------------------------------------------------------------------
# -- NEW FUNCTION TO REMOVE EMOJIS AND UNWANTED SYMBOLS --
# ---------------------------------------------------------------------
def sanitize_text_for_tts(text):
    """
    Removes emojis and other non-speech characters from text before TTS.
    """
    # Comprehensive regex to remove most emojis and symbols
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    # Remove all emojis
    text = emoji_pattern.sub(r'', text)
    # Optional: remove other characters you don't want spoken, like markdown
    text = text.replace('*', '').replace('#', '').replace('_', '')
    return text.strip()

def process_tts_queue():
    """Processes the TTS queue in the main thread."""
    global speaking_in_progress
    if not speaking_in_progress and not tts_queue.empty():
        try:
            text = tts_queue.get_nowait()
            speaking_in_progress = True

            def speak_async(text_to_speak):
                global speaking_in_progress
                try:
                    with sd.OutputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
                        for chunk in voice.synthesize_stream_raw(text_to_speak):
                            stream.write(np.frombuffer(chunk, dtype=np.int16))
                finally:
                    speaking_in_progress = False

            thread = threading.Thread(target=speak_async, args=(text,), daemon=True)
            thread.start()
        except queue.Empty:
            pass

# ---------------------------------------------------------------------
# -- MODIFIED FUNCTION TO USE THE SANITIZER --
# ---------------------------------------------------------------------
def queue_tts(text):
    """Sanitizes text and queues it for TTS playback."""
    clean_text = sanitize_text_for_tts(text)
    if clean_text:
        tts_queue.put(clean_text)

def stream_chat_response(messages_history):
    """Streams the chat response from Ollama."""
    for chunk in chat(model=OLLAMA_MODEL, messages=messages_history, stream=True):
        content = chunk['message']['content']
        if content:
            yield content

def start():
    """Main logic for a single turn of conversation."""
    user_prompt = input("You: ")
    if not user_prompt or WAKE_WORD.lower() not in user_prompt.lower():
        return

    messages.append({"role": "user", "content": user_prompt})
    print(f"{WAKE_WORD}: ", end='', flush=True)

    full_response = ""
    speakable_text_buffer = ""
    has_started_speaking = False
    think_end_token = "</think>"
    
    # --- MODIFIED: Only look for major sentence breaks for smoother speech ---
    sentence_delimiters = ['.', '!', '?']

    for text_chunk in stream_chat_response(messages):
        full_response += text_chunk

        if not has_started_speaking:
            think_end_pos = full_response.find(think_end_token)
            if think_end_pos != -1:
                has_started_speaking = True
                speakable_text_buffer = full_response[think_end_pos + len(think_end_token):]
                print(speakable_text_buffer, end='', flush=True)
            else:
                continue
        else:
            speakable_text_buffer += text_chunk
            print(text_chunk, end='', flush=True)
        
        last_break = -1
        for delim in sentence_delimiters:
            pos = speakable_text_buffer.rfind(delim)
            if pos > last_break:
                last_break = pos

        if last_break != -1:
            text_to_speak = speakable_text_buffer[:last_break + 1]
            queue_tts(text_to_speak)
            speakable_text_buffer = speakable_text_buffer[last_break + 1:]
        
        process_tts_queue()

    if speakable_text_buffer.strip():
        queue_tts(speakable_text_buffer)

    while not tts_queue.empty() or speaking_in_progress:
        process_tts_queue()
        time.sleep(0.05)

    print()
    messages.append({"role": "assistant", "content": full_response})

def main():
    """Main application loop."""
    try:
        while True:
            start()
            # Process queue one last time in case of leftover tasks
            process_tts_queue()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
