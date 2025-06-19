#!/usr/bin/env python
import os
import sys
import json

# Add parent directory to path to allow importing from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.syllabus_processor import SyllabusProcessor

def main():
    # URL to the ISTQB AI Testing Syllabus PDF
    syllabus_url = "https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CT-AI_Syllabus_v1.0_mghocmT.pdf"
    
    print("Initializing ISTQB AI Certification syllabus data...")
    processor = SyllabusProcessor(pdf_url=syllabus_url)
    
    try:
        result = processor.process_syllabus()
        print(f"Successfully processed syllabus with:")
        print(f" - {len(result['chapters'])} chapters")
        print(f" - {sum(len(los) for los in result['learning_objectives'].values())} learning objectives")
        print(f" - {len(result['terms'])} key terms")
        print(f" - {len(result['topics'])} indexed topics")
    except Exception as e:
        print(f"Error processing syllabus: {str(e)}")
        sys.exit(1)
    
    print("Initialization complete. Data saved to data/ directory.")

if __name__ == "__main__":
    main()
