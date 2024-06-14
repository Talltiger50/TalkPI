import json
import pyttsx3
import speech_recognition as sr
import asyncio
import requests as re
#ollama model
model="phi3:mini"
#wake word 
name="Phi"

# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 200)  # Speed of speech
tts_engine.setProperty('volume', 1)  # Volume level (0.0 to 1.0)
voices = tts_engine.getProperty('voices')

# Initialize speech recognizer
recognizer = sr.Recognizer()
messages=[{"role": "system","content": "you are a voice assistant called Phil shorten and simplfiy what you say"}]
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
    
    response = re.post("http://localhost:11434/api/chat", json=data, stream=True)
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
async def main():
    while True:
        # Step 1: Get voice input
        
        user_prompt = get_voice_input()
        lastword=""
        if user_prompt and "Phil" in user_prompt:
            
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
                    if len(output.split(" "))>=1 and lastword!=output.split(" ")[-2]:
                        tts_engine.say(output.split(" ")[-2])
                        tts_engine.runAndWait()
                        
                        lastword=output.split(" ")[-2]
            tts_engine.say(output.split(" ")[-1])
            tts_engine.runAndWait()
            
            messages.append({"role": "assistant","content": output})
        elif user_prompt and not "Thank you.":
            tts_engine.say("Please try again.")
            tts_engine.runAndWait()
        

if __name__ == "__main__":
    asyncio.run(main())
