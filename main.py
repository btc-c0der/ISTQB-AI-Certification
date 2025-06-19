#!/usr/bin/env python
import os
import sys
import json
from pathlib import Path

# Get the root directory of the project
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

def initialize_data(force_refresh=False):
    """
    Check if data is initialized and initialize if needed.
    
    Args:
        force_refresh (bool): If True, forces a refresh of the data even if it exists.
    """
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Check if the necessary data files exist
    data_files_exist = (DATA_DIR / "chapters.json").exists() and \
                       (DATA_DIR / "learning_objectives.json").exists() and \
                       (DATA_DIR / "terms.json").exists() and \
                       (DATA_DIR / "topics.json").exists()
    
    # Initialize data if it doesn't exist or force_refresh is True
    if force_refresh or not data_files_exist:
        if force_refresh:
            print("Forcing data refresh...")
        else:
            print("Data files not found. Initializing data...")
        
        try:
            # Run the initialization script
            sys.path.append(str(ROOT_DIR))
            from utils.syllabus_processor import SyllabusProcessor
            
            # URL to the ISTQB AI Testing Syllabus PDF
            syllabus_url = "https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CT-AI_Syllabus_v1.0_mghocmT.pdf"
            
            try:
                # Check for cached PDF
                pdf_path = DATA_DIR / "syllabus.pdf"
                if pdf_path.exists() and pdf_path.stat().st_size > 0 and not force_refresh:
                    print(f"Using cached PDF: {pdf_path}")
                    processor = SyllabusProcessor(pdf_path=str(pdf_path))
                else:
                    print("Downloading PDF from URL...")
                    processor = SyllabusProcessor(pdf_url=syllabus_url)
                
                processor.process_syllabus()
                print("Data initialization complete.")
                return True
            except Exception as e:
                print(f"Error processing syllabus: {str(e)}")
                print("Creating placeholder data as fallback...")
                # Create placeholder data files
                create_placeholder_data()
                return True
        except Exception as e:
            print(f"Error during data initialization: {str(e)}")
            print("Creating placeholder data as fallback...")
            # Create placeholder data files
            create_placeholder_data()
            return True
    else:
        print("Data already initialized.")
        return True

def create_placeholder_data():
    """Create placeholder data files for the app to function."""
    # Create placeholder chapters
    chapters = {
        "1. Introduction to AI Testing": "This chapter introduces the concepts of AI testing, including basic principles, objectives, and the need for specialized testing approaches for AI systems.",
        "2. AI Quality Characteristics": "This chapter covers quality attributes specific to AI systems, such as bias, explainability, robustness, and various metrics for measuring AI system quality.",
        "3. Testing AI-Based Systems": "This chapter describes methods for testing AI systems, including black-box testing, data validation, and performance evaluation strategies.",
        "4. AI Testing Methods": "This chapter details specific test methods for AI applications, such as adversarial testing, metamorphic testing, and A/B testing approaches.",
        "5. AI Testing in the SDLC": "This chapter explains how AI testing fits into the software development lifecycle, including challenges and best practices for each phase."
    }
    
    # Create placeholder learning objectives
    learning_objectives = {
        "1. Introduction to AI Testing": [
            "Understand the unique challenges of AI testing",
            "Define the scope and objectives of AI system testing",
            "Identify key differences between traditional software testing and AI testing"
        ],
        "2. AI Quality Characteristics": [
            "Explain important quality attributes for AI systems",
            "Define metrics for measuring AI system quality",
            "Understand potential sources of bias in AI models"
        ],
        "3. Testing AI-Based Systems": [
            "Apply black-box testing techniques to AI systems",
            "Validate training and test data quality",
            "Evaluate AI system performance against defined metrics"
        ],
        "4. AI Testing Methods": [
            "Use adversarial testing to identify vulnerabilities",
            "Apply metamorphic testing principles to AI systems",
            "Implement A/B testing for AI model comparison"
        ],
        "5. AI Testing in the SDLC": [
            "Integrate AI testing throughout the development lifecycle",
            "Address testing challenges in each SDLC phase",
            "Apply best practices for AI testing in agile environments"
        ]
    }
    
    # Create placeholder terms
    terms = {
        "AI Testing": "The process of evaluating AI-based systems for quality, reliability, and correctness.",
        "Machine Learning": "A subset of AI that enables systems to learn from data without explicit programming.",
        "Bias": "Systematic errors in model predictions that lead to unfair outcomes for certain groups.",
        "Explainability": "The ability to understand and interpret how an AI system reaches its decisions.",
        "Robustness": "The ability of an AI system to maintain performance under varying conditions and inputs.",
        "Test Data": "The subset of data used to evaluate the performance of a trained AI model.",
        "Training Data": "The subset of data used to train an AI model.",
        "Validation Data": "The subset of data used to tune hyperparameters during model training.",
        "Adversarial Testing": "Testing that involves deliberately attempting to confuse or trick AI systems.",
        "Model Drift": "The degradation of model performance over time due to changes in data patterns."
    }
    
    # Create placeholder topics
    topics = []
    for chapter, content in chapters.items():
        words = content.split()
        for word in words:
            if len(word) > 5 and word.lower() not in ["chapter", "testing", "system", "systems"]:
                topics.append({
                    "topic": word.lower().strip(",.;:"),
                    "chapter": chapter,
                    "context": content[:100] + "..."
                })
    
    # Save placeholder data
    with open(DATA_DIR / "chapters.json", "w") as f:
        json.dump(chapters, f, indent=2)
    
    with open(DATA_DIR / "learning_objectives.json", "w") as f:
        json.dump(learning_objectives, f, indent=2)
    
    with open(DATA_DIR / "terms.json", "w") as f:
        json.dump(terms, f, indent=2)
    
    with open(DATA_DIR / "topics.json", "w") as f:
        json.dump(topics, f, indent=2)
    
    print("Placeholder data created successfully.")

def main():
    """Main entry point for the application."""
    print("Starting ISTQB AI Certification Study Portal...")
    
    # Ensure data directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DATA_DIR / "sessions", exist_ok=True)
    
    # Ensure database directory exists
    db_dir = ROOT_DIR / "db"
    os.makedirs(db_dir, exist_ok=True)
    
    # Ensure data is initialized
    if not initialize_data():
        print("Failed to initialize data. Exiting.")
        sys.exit(1)
    
    # Import and run the Gradio app
    try:
        from app.app import create_gradio_interface
        app = create_gradio_interface()
        app.launch()
    except Exception as e:
        print(f"Error launching application: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
