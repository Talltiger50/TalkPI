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
from tools import call_tool,tools

# ollama model make sure to have the model preinstalled to ollama
model = "qwen3:1.7b" #supports tools
# wake word
name = "Phil"

useTools=True



print("Loading voice model...")
voice = PiperVoice.load("piper-tts/en_US-joe-medium.onnx")  # or path to model file
sample_rate = voice.config.sample_rate
print("Voice model loaded.")

# Initialize speech recognizer
recognizer = sr.Recognizer()

# TTS queue for main thread processing
tts_queue = queue.Queue()
speaking_in_progress = False


messages = [{f"role": "system", "content": "you are a helpful a ai named {name} that has tool calls"}]


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
if useTools:
    tools1=tools
else:
    tools1=None
def stream_chat_response(messages):
    # This function remains unchanged
    
    stream=chat(model=model, messages=messages, stream=True,tools=tools1)
    for chunk in stream:
        yield chunk,stream


def start():
    user_prompt = get_voice_input()
    if not user_prompt or name.lower() not in user_prompt.lower():
        return

    messages.append({"role": "user", "content": user_prompt})
    print("Phil: ", end='', flush=True)

    # --- First call to the model to see if it wants to use a tool ---
    response = chat(model=model, messages=messages, stream=False, tools=tools1 if useTools else None)
    
    # Check if the model decided to call a tool
    if response['message'].get('tool_calls'):
        print("Tool call detected. Executing...")
        
        # It's good practice to append the assistant's intent to call a tool
        messages.append(response['message'])
        
        tool_calls = response['message']['tool_calls']
        
        # Execute all tool calls and gather the results
        for tool_call in tool_calls:
            function_name = tool_call['function']['name']
            arguments = tool_call['function']['arguments']
            
            # Your existing function to run the tool
            tool_output = call_tool(function_name, arguments)
            
            # Append the tool's output to the message history
            messages.append({
                "role": "tool",
                "content": json.dumps(tool_output),  # Ensure the output is a JSON string
            })

        # --- Second call to the model with the tool's output ---
        # Now the model will respond based on the tool's results
        final_stream = chat(model=model, messages=messages, stream=True)

        full_response = ""
        speakable_text_buffer = ""
        
        for chunk in final_stream:
            content = chunk['message']['content']
            full_response += content
            speakable_text_buffer += content
            print(content, end='', flush=True)

            # Your existing logic to queue sentences for TTS
            last_break = -1
            for delim in ['.', '!', '?', ',', ';', ':']:
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

    else:
        # --- No tool call, just stream the response directly ---
        # This part handles regular conversation
        full_response = response['message']['content']
        print(full_response)
        queue_tts(full_response)


    # --- Finalize the conversation ---
    # Wait for the last sentence to finish speaking
    while not tts_queue.empty() or speaking_in_progress:
        process_tts_queue()
        time.sleep(0.1)

    print()  # For a new line after the response
    
    # Append the final assistant response to the history
    if 'tool_calls' not in response['message']:
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
