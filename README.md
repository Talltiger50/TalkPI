# TalkPI (Work In Process)

TalkPI is a Python project designed to enable a large language model to interact using voice commands on a Raspberry Pi, utilizing [Ollama](https://ollama.com/) locally.

-now with tool support
-using piper tts

## Installation
Ensure [Ollama](https://ollama.com/) is installed on your Raspberry Pi. (make sure to pull model file in ollama)
### Raspberry Pi
```bash
git clone https://github.com/Talltiger50/TalkPI.git
cd TalkPI
chmod +x ./setup.sh
sudo ./setup.sh
```

## Usage
Simply run with a connected microphone and speaker:
```bash
source .venv/bin/activate
python main.py
```
To change the model, modify the `model` parameter in the Python file to your Ollama model of choice make sure it's downloaded with ollama:
```python
# this example with phi3
model="phi3:mini"
```
To customize the wake word, adjust the `name` parameter:
```python
name="Phi"
```
## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes. For major updates, please open an issue first to discuss what you would like to change.
