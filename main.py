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
from tools import available_tools, tools_list


class vllm:
    def __init__(self) -> None:
        # ollama model make sure to have the model preinstalled to ollama
        self.model = "llama3.2:3b" #supports tools
        # wake word
        self.name = "Phil"

        self.useTools=True



        print("Loading voice model...")
        self.voice = PiperVoice.load("piper-tts/en_US-joe-medium.onnx")  # or path to model file
        self.sample_rate = self.voice.config.sample_rate
        print("Voice model loaded.")

        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()

        # TTS queue for main thread processing
        self.tts_queue = queue.Queue()
        self.speaking_in_progress = False

        self.dmessages=[]
        self.messages = [{
            "role": "system",
            "content": (
                f"you are a helpful ai named {self.name} that has tool calls and only uses them when needed"
                if self.useTools
                else f"you are a helpful ai named {self.name}"
            )
        }]
    def start(self):
        """
        Listens for user input, processes it with the Ollama model,
        handles tool calls, and speaks the final response.
        """
        user_prompt = self.get_voice_input()
        if not user_prompt or self.name.lower() not in user_prompt.lower():
            return

        self.messages.append({"role": "user", "content": user_prompt})
        
        print("Phil: ", end='', flush=True)
        
        full_response = ""

        try:
            # --- STEP 1: Make the first call to see if a tool is needed ---
            # We use stream=False because we need the full response to check for tool_calls
            response = chat(
                model=self.model,
                messages=self.messages,
                stream=False,
                tools=tools_list if self.useTools else None
            )

            tool_calls = response['message'].get('tool_calls')

            # --- STEP 2: If a tool is called, execute it ---
            if tool_calls and self.useTools:
                print("Tool call detected. Executing...")
                
                # Append the assistant's decision to use a tool to the message history
                self.messages.append(response['message'])
                
                # Execute all tool calls and gather the results
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    arguments = tool_call['function']['arguments']
                    
                    print(f"  - Calling: {function_name}({arguments})")

                    if function_to_call := available_tools.get(function_name):
                        # Call the actual function from tools.py
                        tool_output = function_to_call(**arguments)
                        
                        # Append the tool's output to the message history
                        self.messages.append({
                            "role": "tool",
                            "content": tool_output, # The output is already a JSON string
                        })
                    else:
                        print(f"Error: Model tried to call unknown tool '{function_name}'")
                        self.messages.append({"role": "tool", "content": f'{{"error": "Tool {function_name} not found."}}'})

                # --- STEP 3: Make the second call to get the final, natural language response ---
                final_response_stream = chat(model=self.model, messages=self.messages, stream=True)

                speakable_text_buffer = ""
                for chunk in final_response_stream:
                    content = chunk.message.content
                    full_response += content
                    speakable_text_buffer += content
                    print(content, end='', flush=True)

                    # Use existing logic to find sentence breaks for natural TTS
                    last_break = -1
                    for delim in ['.', '!', '?', ',', ';', ':']:
                        pos = speakable_text_buffer.rfind(delim)
                        if pos > last_break:
                            last_break = pos

                    if last_break != -1:
                        text_to_speak = speakable_text_buffer[:last_break + 1]
                        self.queue_tts(text_to_speak)
                        speakable_text_buffer = speakable_text_buffer[last_break + 1:]
                    
                    self.process_tts_queue() # Keep the TTS queue running

                # Queue any remaining text in the buffer
                if speakable_text_buffer.strip():
                    self.queue_tts(speakable_text_buffer)

            else:
                # --- NO TOOL CALL: Just stream the direct response ---
                # This handles regular conversation
                full_response = response['message']['content']
                print(full_response)
                
            
            # --- Finalization ---
            # Wait for the TTS queue to finish speaking
            while not self.tts_queue.empty() or speaking_in_progress:
                self.process_tts_queue()
                time.sleep(0.1)

            print()  # Add a newline for clean formatting in the console
            self.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            self.queue_tts("Sorry, I ran into an error.")

    def main(self):
        try:
            while True:
                # The main loop now also needs to process the TTS queue for cleanup
                self.process_tts_queue()
                self.start()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nShutting down...")
    def process_tts_queue(self):
        """Process TTS queue in main thread - call this periodically in the main loop"""
        global speaking_in_progress

        if not speaking_in_progress and not self.tts_queue.empty():
            try:
                text = self.tts_queue.get_nowait()
                speaking_in_progress = True

                def speak_async(text_to_speak):
                    global speaking_in_progress
                    try:
                        # Use a stream for real-time playback
                        with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
                            for chunk in self.voice.synthesize_stream_raw(text_to_speak):
                                data = np.frombuffer(chunk, dtype=np.int16)
                                stream.write(data)
                    finally:
                        speaking_in_progress = False # Signal that speaking is done

                # Run the speaking part in a separate thread to not block the main loop
                thread = threading.Thread(target=speak_async, args=(text,), daemon=True)
                thread.start()

            except queue.Empty:
                pass


    def queue_tts(self,text):
        """Queue text for TTS playback"""
        if text.strip():
            self.tts_queue.put(text)

    def get_voice_input(self):
        # This function remains unchanged
        with sr.Microphone() as source:
            #print("Listening for your input...")
            audio = self.recognizer.listen(source,timeout=2)
            try:
                text = self.recognizer.recognize_whisper(audio)
                #print(f"You said: {text}")
                return text
            except sr.UnknownValueError:
                #print("Sorry, I could not understand the audio.")
                return None
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                return None


if __name__ == "__main__":
    llm=vllm()
    llm.main()
