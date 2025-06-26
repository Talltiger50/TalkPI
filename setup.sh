#!/bin/bash
echo "Installing..."
sudo apt install portaudio19-dev

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
echo "done installing python packages"
echo "downloading piper tts model"

mkdir piper-tts
cd piper-tts
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx?download=true -O en_us_joe_medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json?download=true -O en_us_joe_medium.onnx
echo "done downloading model"

cd ..
