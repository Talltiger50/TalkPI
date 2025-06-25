import json
import speech_recognition as sr
import asyncio
from ollama import Client
from ollama import chat
import re
import threading
import queue
import time
import numpy as np
import sounddevice as sd
from piper import PiperVoice

# ollama model
# cl=Client("http://localhost:11434")
model = "qwen3:1.7b"
# wake word
name = "Phil"
# note this has only been tested on phi3
memory = False

memoryPath = "memory.json"

# Load Piper voice (high quality)
voice = PiperVoice.load("en_US-amy-high")  # or path to model file
sample_rate = voice.config.sample_rate

# Initialize speech recognizer
recognizer = sr.Recognizer()

# TTS queue for main thread processing
tts_queue = queue.Queue()
speaking_in_progress = False
speaking_lock = threading.Lock()

if memory:
    with open("MemoryPrompt.txt") as p:
        messages = [{"role": "system", "content": p.read()}]
        p.close()
else:
    messages = [{"role": "system", "content": "you are a helpful a ai called phil"}]


def process_tts_queue():
    """Process TTS queue in main thread - call this periodically"""
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
                            data = np.frombuffer(chunk, dtype=np.int16)
                            stream.write(data)
                finally:
                    speaking_in_progress = False

            thread = threading.Thread(target=speak_async, args=(text,), daemon=True)
            thread.start()

        except queue.Empty:
            pass


def queue_tts(text):
    """Queue text for TTS playback"""
    if text.strip():
        tts_queue.put(text)


def memoryF(message: str):
    if "!save" in message and "!load" in message:
        matches = re.findall(r'!(save|load)\s*({.*?})?', message)

        for match in matches:
            command = match[0]  # Extract command (!save or !load)
            json_data = match[1] if len(match) > 1 else None  # Extract JSON data if present

            if command == 'save' and json_data:
                try:
                    # Parse the JSON data into a Python dictionary
                    data_dict = json.loads(json_data)

                    # Extract the name and value
                    for key, value in data_dict.items():
                        name = key  # This is the name or key in the JSON object
                        val = value  # This is the value associated with the key

                        with open(memoryPath, 'r') as file:
                            data = json.load(file)

                        # Step 2: Append new data to the existing data
                        data.append({name: val})

                        # Step 3: Write back to JSON file
                        with open(memoryPath, 'w') as file:
                            json.dump(data, file, indent=4)

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

            elif command == 'load':
                print("Executing !load command")

            else:
                print(f"Ignoring unknown command: !{command}")


def get_text_input():
    return input(":")


def get_voice_input():
    with sr.Microphone() as source:
        print("Listening for your input...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_whisper(audio)
            print(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            print("Sorry, I could not understand the audio.")
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None


# Asynchronous function to stream chat response
def stream_chat_response(messages):
    for chunk in chat(model=model, messages=messages, stream=True):
        text = chunk.message.content or ""
        # Ollama v0.8.0 may send JSON tool_call blocks or empty thinking messages
        # Skip those
        if not text.strip():
            continue
        # Sometimes uses special markers like "<think>" or "["
        if text.lstrip().startswith(("{", "[", "<")):
            continue
        yield text


def start():
    user_prompt = input(": ")
    if not user_prompt or name not in user_prompt:
        return

    messages.append({"role": "user", "content": user_prompt})
    queue_tts("processing")

    print("Chatbot: ", end='', flush=True)
    output = ""
    word_buffer = []

    # Buffer to collect words before speaking
    MIN_WORDS_TO_SPEAK = 4  # Speak in chunks of at least 4 words

    for text_chunk in stream_chat_response(messages):
        output += text_chunk
        print(text_chunk, end='', flush=True)

        # Process TTS queue while getting chunks
        process_tts_queue()

        # Split current output into words
        current_words = output.strip().split()

        # Check if we have new complete words to speak
        new_word_count = len(current_words)
        if new_word_count >= len(word_buffer) + MIN_WORDS_TO_SPEAK:
            # Get the new words to add to buffer
            words_to_add = current_words[len(word_buffer):]
            word_buffer.extend(words_to_add)

            # If we have enough words, speak some of them
            if len(word_buffer) >= MIN_WORDS_TO_SPEAK:
                # Take most words but leave a few in buffer for smooth continuation
                words_to_speak_count = max(1, len(word_buffer) - 2)
                words_to_speak = word_buffer[:words_to_speak_count]
                text_to_speak = ' '.join(words_to_speak)
                queue_tts(text_to_speak)
                # Remove spoken words from buffer
                word_buffer = word_buffer[words_to_speak_count:]

    # Speak any remaining words
    if word_buffer:
        final_text = ' '.join(word_buffer)
        queue_tts(final_text)
    elif output.strip():
        # Fallback: if no words in buffer but we have output, speak the end
        final_words = output.strip().split()
        if final_words:
            queue_tts(' '.join(final_words[-3:]))  # Speak last few words

    # Continue processing TTS queue until speaking is done
    while not tts_queue.empty() or speaking_in_progress:
        process_tts_queue()
        time.sleep(0.1)

    messages.append({"role": "assistant", "content": output})


def main():
    try:
        while True:
            start()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
