#!/usr/bin/env python3
"""
Main entry point for HuggingFace Spaces.
This file ensures the app is properly launched in HF Spaces environment.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path so imports work correctly
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import needed modules
import gradio as gr
from app.app import create_gradio_interface
from hf_integration import init_hf_integration

# Initialize HuggingFace integration
init_hf_integration()

# Create and start the Gradio interface
demo = create_gradio_interface()

# Determine the port
port = int(os.environ.get("PORT", 7860))

# Launch the app - HF Spaces prefers share=False and server_port=port
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        debug=False,
        show_error=True
    )
