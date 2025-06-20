#!/usr/bin/env python
import os
import sys
import pandas as pd
from pathlib import Path
import json
import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define paths for storing LLM evaluations
EVAL_DIR = Path(__file__).parent / "data" / "llm_evals"
EVAL_FILE = EVAL_DIR / "evaluations.json"

# Predefined model types
MODEL_TYPES = [
    "LLM : General",
    "LLM : Chat",
    "LLM : Code",
    "LLM : Instruction",
    "Embedding",
    "Text-to-Image",
    "Text-to-Audio",
    "Text-to-Video",
    "Image-to-Text",
    "Other"
]

# Predefined weight types
WEIGHT_TYPES = [
    "Original",
    "Delta",
    "Adapter",
    "PEFT",
    "LoRA", 
    "QLoRA",
    "GGUF",
    "GGML",
    "Safetensors",
    "Other"
]

# Predefined precision types
PRECISION_TYPES = [
    "float16",
    "float32",
    "bfloat16",
    "int8",
    "int4",
    "int2", 
    "Other"
]

def init_hf_integration():
    """Initialize the HuggingFace integration."""
    # Ensure the evaluation directory exists
    os.makedirs(EVAL_DIR, exist_ok=True)
    
    # Create evaluations file if it doesn't exist
    if not EVAL_FILE.exists():
        with open(EVAL_FILE, 'w') as f:
            json.dump({"evaluations": []}, f)
    
    # Check for HuggingFace API token
    hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    if hf_token and hf_token != "your_huggingface_api_token_here":
        os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
        print("HuggingFace API token loaded successfully")
        return True
    else:
        print("Warning: HuggingFace API token not found or not valid")
        print("Set the HUGGINGFACE_HUB_TOKEN environment variable or add it to .env file")
        # Still return True as local functionality can work without the token
        return True

def get_model_types() -> List[str]:
    """Get the list of available model types."""
    return MODEL_TYPES

def get_weight_types() -> List[str]:
    """Get the list of available weight types."""
    return WEIGHT_TYPES

def get_precision_types() -> List[str]:
    """Get the list of available precision types."""
    return PRECISION_TYPES

def save_llm_evaluation(model_name: str, prompt: str, response: str, rating: int, 
                       model_type: str = "", precision: str = "", weight_type: str = ""):
    """Save an LLM evaluation to the evaluations file."""
    if not EVAL_FILE.exists():
        init_hf_integration()
        
    # Read existing evaluations
    with open(EVAL_FILE, 'r') as f:
        data = json.load(f)
    
    # Add new evaluation
    evaluation = {
        "id": len(data["evaluations"]) + 1,
        "timestamp": datetime.datetime.now().isoformat(),
        "model_name": model_name,
        "model_type": model_type,
        "precision": precision,
        "weight_type": weight_type,
        "prompt": prompt,
        "response": response,
        "rating": rating,
    }
    
    data["evaluations"].append(evaluation)
    
    # Write updated evaluations back to file
    with open(EVAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)
        
    return True

def get_leaderboard_data() -> pd.DataFrame:
    """Get the leaderboard data as a pandas DataFrame."""
    if not EVAL_FILE.exists():
        return pd.DataFrame()
        
    # Read evaluations
    with open(EVAL_FILE, 'r') as f:
        data = json.load(f)
    
    if not data["evaluations"]:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(data["evaluations"])
    
    # Group by model and calculate average rating
    agg_df = df.groupby(['model_name', 'model_type']).agg(
        avg_rating=('rating', 'mean'),
        evaluation_count=('rating', 'count')
    ).reset_index()
    
    # Sort by average rating descending
    agg_df = agg_df.sort_values('avg_rating', ascending=False)
    
    return agg_df

def get_evaluation_history() -> pd.DataFrame:
    """Get the full evaluation history as a pandas DataFrame."""
    if not EVAL_FILE.exists():
        return pd.DataFrame()
    
    # Read evaluations
    with open(EVAL_FILE, 'r') as f:
        data = json.load(f)
    
    if not data["evaluations"]:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(data["evaluations"])
    
    # Sort by timestamp descending (most recent first)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp', ascending=False)
    
    return df

def render_evaluations_table():
    """Render the evaluations as a formatted markdown table."""
    df = get_leaderboard_data()
    
    if df.empty:
        return "No evaluations recorded yet."
    
    # Format the DataFrame as a markdown table
    table = "# LLM Evaluation Leaderboard\n\n"
    table += "| Rank | Model Name | Model Type | Average Rating | Evaluations |\n"
    table += "|------|------------|------------|----------------|------------|\n"
    
    for i, (_, row) in enumerate(df.iterrows(), 1):
        rating = f"{row['avg_rating']:.2f}/5"
        table += f"| {i} | {row['model_name']} | {row['model_type']} | {rating} | {int(row['evaluation_count'])} |\n"
    
    return table

def get_full_evaluation_history():
    """Render the full evaluation history as a markdown table."""
    df = get_evaluation_history()
    
    if df.empty:
        return "No evaluations recorded yet."
    
    # Format the DataFrame as a markdown table
    table = "# LLM Evaluation History\n\n"
    table += "| Date | Model Name | Prompt | Rating |\n"
    table += "|------|------------|--------|--------|\n"
    
    for _, row in df.iterrows():
        date = row['timestamp'].strftime('%Y-%m-%d %H:%M')
        # Truncate long prompts
        prompt = row['prompt'][:50] + "..." if len(row['prompt']) > 50 else row['prompt']
        table += f"| {date} | {row['model_name']} | {prompt} | {row['rating']}/5 |\n"
    
    return table

def test_hf_llm(model_name: str, prompt: str, model_type: str="", precision: str="", weight_type: str=""):
    """Test an LLM with the given parameters."""
    # This is a placeholder function - in a real-world scenario, this would use the HF API
    # to actually query the model. For now, we'll simulate a response.
    
    response = f"This is a simulated response from {model_name} for the prompt: {prompt}"
    
    # In a production environment, you would use something like:
    # response = query_huggingface_model(model_name, prompt, precision, weight_type)
    
    return response
