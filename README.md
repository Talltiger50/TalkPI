# TalkPI

TalkPI is a Python project designed to enable a large language model to interact using voice commands on a Raspberry Pi, utilizing [Ollama](https://ollama.com/) locally.

## Installation
Ensure [Ollama](https://ollama.com/) is installed on your Raspberry Pi.
### Raspberry pi
```bash
git clone https://github.com/Talltiger50/TalkPI.git
cd TalkPI
python -m venv venv
./venv/bin/pip install -r requirements.txt
```
## Usage
Simply run with a connected microphone and speaker:
```bash
./venv/bin/python main.py
```
To change the model, modify the `model` parameter in the Python file to your Ollama model of choice:
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
