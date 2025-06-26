#!/bin/bash
echo "Installing..."
sudo apt install portaudio19-dev

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
echo "done"

