import json
import speech_recognition as sr
import re
import threading
import queue
import time
import numpy as np
import sounddevice as sd
from ollama import chat
from piper import PiperVoice

# ollama model
model = "qwen3:1.7b"
# wake word
name = "Phil"
# note this has only been tested on phi3
memory = False

memoryPath = "memory.json"

# Load Piper voice (high quality)
print("Loading voice model...")
voice = PiperVoice.load("en_us.onnx")  # or path to model file
sample_rate = voice.config.sample_rate
print("Voice model loaded.")

# Initialize speech recognizer
recognizer = sr.Recognizer()

# TTS queue for main thread processing
tts_queue = queue.Queue()
speaking_in_progress = False

if memory:
    with open("MemoryPrompt.txt") as p:
        messages = [{"role": "system", "content": p.read()}]
        p.close()
else:
    messages = [{"role": "system", "content": "you are a helpful a ai called phil"}]


def process_tts_queue():
    """Process TTS queue in main thread - call this periodically in the main loop"""
    global speaking_in_progress

    if not speaking_in_progress and not tts_queue.empty():
        try:
            text = tts_queue.get_nowait()
            speaking_in_progress = True

            def speak_async(text_to_speak):
                global speaking_in_progress
                try:
                    # Use a stream for real-time playback
                    with sd.OutputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
                        for chunk in voice.synthesize_stream_raw(text_to_speak):
                            data = np.frombuffer(chunk, dtype=np.int16)
                            stream.write(data)
                finally:
                    speaking_in_progress = False # Signal that speaking is done

            # Run the speaking part in a separate thread to not block the main loop
            thread = threading.Thread(target=speak_async, args=(text,), daemon=True)
            thread.start()

        except queue.Empty:
            pass


def queue_tts(text):
    """Queue text for TTS playback"""
    if text.strip():
        tts_queue.put(text)


def memoryF(message: str):
    # This function remains unchanged
    if "!save" in message and "!load" in message:
        matches = re.findall(r'!(save|load)\s*({.*?})?', message)
        for match in matches:
            command = match[0]
            json_data = match[1] if len(match) > 1 else None
            if command == 'save' and json_data:
                try:
                    data_dict = json.loads(json_data)
                    for key, value in data_dict.items():
                        name = key
                        val = value
                        with open(memoryPath, 'r') as file:
                            data = json.load(file)
                        data.append({name: val})
                        with open(memoryPath, 'w') as file:
                            json.dump(data, file, indent=4)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
            elif command == 'load':
                print("Executing !load command")
            else:
                print(f"Ignoring unknown command: !{command}")


def get_voice_input():
    # This function remains unchanged
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
    # This function remains unchanged
    for chunk in chat(model=model, messages=messages, stream=True):
        yield chunk['message']['content']


# ---------------------------------------------------------------------
# -- THIS IS THE UPGRADED FUNCTION --
# ---------------------------------------------------------------------
def start():
    # user_prompt = get_voice_input() # Or use get_text_input()
    user_prompt = input("You: ")
    if not user_prompt or name.lower() not in user_prompt.lower():
        return

    messages.append({"role": "user", "content": user_prompt})

    print("Phil: ", end='', flush=True)

    full_response = ""
    speakable_text_buffer = ""
    has_started_speaking = False
    think_end_token = "</think>"

    for text_chunk in stream_chat_response(messages):
        full_response += text_chunk

        # If we haven't started speaking yet, wait for the </think> token
        if not has_started_speaking:
            think_end_pos = full_response.find(think_end_token)
            if think_end_pos != -1:
                # We found the end of the thought block.
                has_started_speaking = True
                # The text we can potentially speak starts right after the token
                speakable_text_buffer = full_response[think_end_pos + len(think_end_token):]
                # Print the speakable part to the screen
                print(speakable_text_buffer, end='', flush=True)
            else:
                # Still waiting for </think>, so do nothing else
                continue
        else:
            # We are already past the thought block, so just append the new chunk
            speakable_text_buffer += text_chunk
            print(text_chunk, end='', flush=True)

        # Process the accumulated speakable text for natural sentence breaks
        # Find the last natural break in the buffer
        last_break = -1
        for delim in ['.', '!', '?', ',', ';', ':']:
            pos = speakable_text_buffer.rfind(delim)
            if pos > last_break:
                last_break = pos

        if last_break != -1:
            # We found a sentence break. Queue up the sentence for TTS.
            text_to_speak = speakable_text_buffer[:last_break + 1]
            queue_tts(text_to_speak)

            # Keep the remainder in the buffer for the next iteration
            speakable_text_buffer = speakable_text_buffer[last_break + 1:]

        # Call the queue processor in the loop to handle speaking
        process_tts_queue()

    # After the stream is finished, if there's any text left in the buffer, speak it.
    if speakable_text_buffer.strip():
        queue_tts(speakable_text_buffer)

    # Wait for the last sentence to finish speaking
    while not tts_queue.empty() or speaking_in_progress:
        process_tts_queue()
        time.sleep(0.1)

    print() # for a new line after the response
    messages.append({"role": "assistant", "content": full_response})


def main():
    try:
        while True:
            # The main loop now also needs to process the TTS queue for cleanup
            process_tts_queue()
            start()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
