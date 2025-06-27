#!/usr/bin/env bash
set -euo pipefail # More robust error handling

# --- Configuration ---
VENV_DIR=".venv"
MODEL_DIR="piper-tts"
REQUIREMENTS_FILE="requirements.txt"
# Piper TTS Model details
MODEL_NAME="en_US-joe-medium"
MODEL_BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium"
MODEL_ONNX_FILE="${MODEL_NAME}.onnx"
MODEL_JSON_FILE="${MODEL_NAME}.onnx.json"

# --- Functions ---

# Function to print messages
msg() {
  echo -e "[INFO] $1"
}

# Function to check for required commands
check_command() {
  if ! command -v "$1" &> /dev/null; then
    echo "Error: Command '$1' not found. Please install it and try again."
    exit 1
  fi
}

# Function to install system dependencies (for Debian-based systems)
install_dependencies() {
  msg "Checking for system dependencies..."
  if ! dpkg -s "portaudio19-dev" &> /dev/null; then
    msg "Installing system dependencies (portaudio19-dev, python3-venv, etc.)..."
    sudo apt update
    sudo apt install -y portaudio19-dev python3-venv python3-pip wget python3
  else
    msg "System dependencies already installed."
  fi
}

# Function to set up the Python virtual environment
setup_venv() {
  msg "Setting up Python virtual environment..."
  if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    msg "Virtual environment created at '$VENV_DIR'."
  else
    msg "Virtual environment already exists."
  fi

  msg "Installing Python packages from '$REQUIREMENTS_FILE'..."
  "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
  msg "Done installing Python packages."
}

# Function to download the TTS model
download_model() {
  msg "Downloading Piper TTS model..."
  mkdir -p "$MODEL_DIR"
  cd "$MODEL_DIR"

  if [ ! -f "$MODEL_ONNX_FILE" ]; then
    msg "Downloading model: $MODEL_ONNX_FILE..."
    wget -q --show-progress -O "$MODEL_ONNX_FILE" "${MODEL_BASE_URL}/${MODEL_ONNX_FILE}?download=true"
  else
    msg "Model file $MODEL_ONNX_FILE already exists."
  fi

  if [ ! -f "$MODEL_JSON_FILE" ]; then
    msg "Downloading model config: $MODEL_JSON_FILE..."
    wget -q --show-progress -O "$MODEL_JSON_FILE" "${MODEL_BASE_URL}/${MODEL_JSON_FILE}?download=true"
  else
    msg "Model config file $MODEL_JSON_FILE already exists."
  fi

  cd ..
  msg "Model setup is complete."
}

# --- Main Execution ---
main() {
  # Check for essential commands
  check_command "python3"
  check_command "wget"
  check_command "sudo"
  check_command "apt"

  # Check for requirements.txt
  if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: '$REQUIREMENTS_FILE' not found in the current directory."
    exit 1
  fi

  install_dependencies
  setup_venv
  download_model

  msg "\nSetup complete!"
  msg "To activate the virtual environment, run:"
  msg "source $VENV_DIR/bin/activate"
}

# Run the main function
main
