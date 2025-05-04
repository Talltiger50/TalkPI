import json
import pyttsx3
import speech_recognition as sr
import asyncio
import requests as re
import ollama
#ollama model
model="tinyllama"
#wake word 
name="Phil"
#note this has only been tested on phi3
memory=True

memoryPath="memory.json"
# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 200)  # Speed of speech
tts_engine.setProperty('volume', 1)  # Volume level (0.0 to 1.0)
voices = tts_engine.getProperty('voices')

# Initialize speech recognizer
recognizer = sr.Recognizer()
if memory:
    with open("MemoryPrompt.txt") as p:
        messages=[{"role": "system","content": p.read()}]
        p.close()
else:
    with open("prompt.txt") as p:
        messages=[{"role": "system","content": p.read()}]
        p.close()
def memoryF(message:str):
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
                        data.append({name:val})

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

# Function to stream chat response from custom API
def chat(messages: list[dict]):
    data = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    
    response = re.post("http://raspberrypi.local:11434/api/chat", json=data, stream=True)
    return response.iter_content()

# Asynchronous function to stream chat response
async def stream_chat_response(messages):
    response_stream = chat(messages)
    out=""
    for chunk in response_stream:
        if "\n"in out:
            text_chunk = json.loads(out)["message"]["content"]
            out=""
            yield text_chunk
        out=out+chunk.decode('utf-8',errors='ignore')

# Main function to get response and read out loud


ollama.
response = ollama.chat(
    model='llama3.1',
    messages=[{'role': 'user', 'content':
        'What is the weather in Toronto?'}],

		# provide a weather checking tool to the model
    tools=[{
      'type': 'function',
      'function': {
        'name': 'get_current_weather',
        'description': 'Get the current weather for a city',
        'parameters': {
          'type': 'object',
          'properties': {
            'city': {
              'type': 'string',
              'description': 'The name of the city',
            },
          },
          'required': ['city'],
        },
      },
    },
  ],
)

print(response['message']['tool_calls'])

async def main():
    while True:
        # Step 1: Get voice input
        
        user_prompt = get_text_input()
        lastword=""
        if user_prompt and name in user_prompt:
            
            messages.append({"role": "user", "content": user_prompt})
            # Step 2: Get chat response and read out loud
            tts_engine.say("processing")
            tts_engine.runAndWait()
            print("Chatbot: ", end='', flush=True)
            output=""
            async for text_chunk in stream_chat_response(messages):
                if " " !=text_chunk.strip():
                    output=output+text_chunk
                    print(text_chunk, end='', flush=True)
                    if len(output.split(" "))>1:
                        if lastword!=output.split(" ")[-2]:
                            tts_engine.say(output.split(" ")[-2])
                            tts_engine.runAndWait()
                            
                            lastword=output.split(" ")[-2]
            tts_engine.say(output.split(" ")[-1])
            tts_engine.runAndWait()
            
            messages.append({"role": "assistant","content": output})
            if memory:
                pass
                #=memoryF(output)
        elif user_prompt:
            tts_engine.say("Please try again.")
            tts_engine.runAndWait()
        

if __name__ == "__main__":
    asyncio.run(main())
