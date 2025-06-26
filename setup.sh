#!/bin/bash
set -e  # Exit on any error

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y portaudio19-dev python3-venv python3-pip wget python3

echo "Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing Python packages..."
.venv/bin/pip install -r requirements.txt
echo "Done installing Python packages."

echo "Downloading Piper TTS model..."
mkdir -p piper-tts
cd piper-tts

wget -O en_US-joe-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx?download=true"
wget -O en_US-joe-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json?download=true"

echo "Done downloading model."
cd ..
