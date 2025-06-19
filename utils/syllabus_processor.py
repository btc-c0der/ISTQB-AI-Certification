import os
import requests
import pdfplumber
import re
import nltk
import json
import pandas as pd
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Download NLTK resources
nltk.download('punkt')
nltk.download('stopwords')

# Make sure NLTK data is available
try:
    sent_tokenize("This is a test sentence. This is another test sentence.")
    print("NLTK tokenizers loaded successfully.")
except Exception as e:
    print(f"Error with NLTK: {str(e)}")
    # Fallback to more basic tokenization if NLTK fails
    def simple_sent_tokenize(text):
        return text.replace('\n', ' ').split('.')
    def simple_word_tokenize(text):
        return text.split()
    # Replace the NLTK functions with our simple versions
    globals()['sent_tokenize'] = simple_sent_tokenize
    globals()['word_tokenize'] = simple_word_tokenize
    print("Using simple tokenization as fallback.")

class SyllabusProcessor:
    def __init__(self, pdf_url=None, pdf_path=None):
        """
        Initialize the SyllabusProcessor with either a URL to download the PDF from
        or a path to a local PDF file.
        """
        self.pdf_url = pdf_url
        self.pdf_path = pdf_path
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.chapters = {}
        self.topics = []
        self.terms = {}
        self.learning_objectives = {}
        
    def download_pdf(self):
        """
        Download the PDF from the specified URL and save it to the data directory.
        Implements caching to avoid repeated downloads.
        """
        if not self.pdf_url:
            raise ValueError("PDF URL is not provided")
        
        os.makedirs(self.data_dir, exist_ok=True)
        pdf_path = os.path.join(self.data_dir, 'syllabus.pdf')
        
        # Check if PDF already exists (cached)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print(f"Using cached PDF from {pdf_path}")
            self.pdf_path = pdf_path
            return
        
        # If not cached, download the PDF
        try:
            response = requests.get(self.pdf_url)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            
            self.pdf_path = pdf_path
            print(f"PDF downloaded successfully to {pdf_path}")
        except Exception as e:
            print(f"Error downloading PDF: {str(e)}")
            raise
        
    def extract_text(self):
        """
        Extract text from the PDF file.
        """
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            raise FileNotFoundError("PDF file not found")
        
        text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        return text
    
    def parse_chapters(self, text):
        """
        Parse chapters and their content from the extracted text.
        """
        # If we couldn't extract proper chapters, create a simplified structure
        if not text or len(text) < 100:
            print("Warning: Extracted text is too short. Generating placeholder content.")
            self.chapters = {
                "1. Introduction to AI Testing": "This chapter introduces the concepts of AI testing.",
                "2. AI Quality Characteristics": "This chapter covers quality attributes specific to AI systems.",
                "3. Testing AI-Based Systems": "This chapter describes methods for testing AI systems.",
                "4. AI Testing Methods": "This chapter details specific test methods for AI applications.",
                "5. AI Testing in the SDLC": "This chapter explains how AI testing fits into the software development lifecycle."
            }
            return self.chapters
        
        # Try to parse the chapters
        try:
            # Pattern to identify chapter titles (e.g., "1. Introduction to AI Testing" or "1 Introduction to AI Testing")
            chapter_pattern = r'(\d+\.?\s+[A-Z][a-zA-Z\s]+)'
            
            # Split by chapters
            chapter_matches = re.finditer(chapter_pattern, text)
            chapter_positions = [(m.group(0), m.start()) for m in chapter_matches]
            
            # If we couldn't find chapters, create some basic ones from the text
            if not chapter_positions:
                print("Warning: Could not identify chapters. Creating simplified chapters.")
                # Split text into roughly equal parts
                chunk_size = len(text) // 5
                for i in range(5):
                    start = i * chunk_size
                    end = start + chunk_size if i < 4 else len(text)
                    title = f"{i+1}. Chapter {i+1}"
                    self.chapters[title] = text[start:end]
                return self.chapters
            
            # Extract content for each chapter
            for i in range(len(chapter_positions)):
                start_pos = chapter_positions[i][1]
                end_pos = chapter_positions[i+1][1] if i < len(chapter_positions) - 1 else len(text)
                
                chapter_title = chapter_positions[i][0]
                chapter_content = text[start_pos:end_pos]
                
                self.chapters[chapter_title] = chapter_content
        except Exception as e:
            print(f"Error parsing chapters: {str(e)}. Creating placeholder content.")
            self.chapters = {
                "1. Introduction to AI Testing": "This chapter introduces the concepts of AI testing.",
                "2. AI Quality Characteristics": "This chapter covers quality attributes specific to AI systems.",
                "3. Testing AI-Based Systems": "This chapter describes methods for testing AI systems.",
                "4. AI Testing Methods": "This chapter details specific test methods for AI applications.",
                "5. AI Testing in the SDLC": "This chapter explains how AI testing fits into the software development lifecycle."
            }
            
        return self.chapters
    
    def extract_learning_objectives(self):
        """
        Extract learning objectives from each chapter.
        """
        for chapter, content in self.chapters.items():
            # Pattern to identify learning objectives
            lo_pattern = r'LO-\d+\.\d+\.\d+\s+(.+?)(?=LO-|\Z)'
            learning_objectives = re.finditer(lo_pattern, content, re.DOTALL)
            
            chapter_los = []
            for lo in learning_objectives:
                chapter_los.append(lo.group(1).strip())
            
            self.learning_objectives[chapter] = chapter_los
        
        return self.learning_objectives
    
    def extract_key_terms(self):
        """
        Extract key terms and their definitions from the syllabus.
        """
        # This is a simplified approach; actual implementation may need more sophisticated parsing
        term_pattern = r'([A-Z][a-zA-Z\s]+):\s+([^.]+\.)'
        
        for chapter, content in self.chapters.items():
            term_matches = re.finditer(term_pattern, content)
            
            for match in term_matches:
                term = match.group(1).strip()
                definition = match.group(2).strip()
                self.terms[term] = definition
        
        return self.terms
    
    def create_topics_index(self):
        """
        Create an index of topics from the syllabus.
        """
        stop_words = set(stopwords.words('english'))
        
        # Regular expression to identify potential key phrases (e.g., "Machine Learning", "Test Case")
        key_phrase_pattern = r'\b[A-Z][a-zA-Z]*(?:\s+[A-Za-z]+){0,3}\b'
        
        for chapter, content in self.chapters.items():
            sentences = sent_tokenize(content)
            
            for sentence in sentences:
                # Extract potential key phrases (capitalized words or phrases)
                key_phrases = re.findall(key_phrase_pattern, sentence)
                
                # Add key phrases as topics
                for phrase in key_phrases:
                    if len(phrase) > 3 and not all(word.lower() in stop_words for word in phrase.split()):
                        self.topics.append({
                            'topic': phrase,
                            'chapter': chapter,
                            'context': sentence
                        })
                
                # Also extract individual important words as before
                words = [word.lower() for word in word_tokenize(sentence) if word.isalnum() and word.lower() not in stop_words]
                
                for word in words:
                    if len(word) > 4:  # Increased minimum length to 5 characters for individual words
                        self.topics.append({
                            'topic': word,
                            'chapter': chapter,
                            'context': sentence
                        })
        
        # Convert to DataFrame for easier filtering and searching
        topics_df = pd.DataFrame(self.topics)
        # Remove duplicates - consider context as well to avoid duplicate contexts
        topics_df = topics_df.drop_duplicates(subset=['context'])
        # Also remove duplicate topics within the same chapter if they have different contexts
        topics_df = topics_df.sort_values('context', key=lambda x: x.str.len(), ascending=False)
        topics_df = topics_df.drop_duplicates(subset=['topic', 'chapter'])
        
        self.topics = topics_df.to_dict('records')
        return self.topics
    
    def save_processed_data(self):
        """
        Save all processed data to JSON files.
        """
        os.makedirs(self.data_dir, exist_ok=True)
        
        with open(os.path.join(self.data_dir, 'chapters.json'), 'w') as f:
            json.dump(self.chapters, f, indent=2)
        
        with open(os.path.join(self.data_dir, 'learning_objectives.json'), 'w') as f:
            json.dump(self.learning_objectives, f, indent=2)
        
        with open(os.path.join(self.data_dir, 'terms.json'), 'w') as f:
            json.dump(self.terms, f, indent=2)
        
        with open(os.path.join(self.data_dir, 'topics.json'), 'w') as f:
            json.dump(self.topics, f, indent=2)
        
        print("All data saved to JSON files in the data directory")
    
    def process_syllabus(self):
        """
        Process the syllabus PDF by downloading (if needed), extracting text, and parsing content.
        """
        if self.pdf_url and not self.pdf_path:
            self.download_pdf()
        
        text = self.extract_text()
        self.parse_chapters(text)
        self.extract_learning_objectives()
        self.extract_key_terms()
        self.create_topics_index()
        self.save_processed_data()
        
        return {
            'chapters': self.chapters,
            'learning_objectives': self.learning_objectives,
            'terms': self.terms,
            'topics': self.topics
        }


def generate_quiz_questions():
    """
    Generate quiz questions based on the syllabus content.
    This is a placeholder function that would be implemented with actual quiz generation logic.
    """
    # In a real implementation, this would analyze the syllabus content and generate relevant questions
    return [
        {
            "question": "What is the main purpose of ISTQB AI Testing certification?",
            "options": [
                "To teach AI development",
                "To provide testers with knowledge and skills for testing AI-based systems",
                "To certify AI developers",
                "To replace traditional testing methods"
            ],
            "answer": 1
        },
        {
            "question": "Which of the following is a key challenge in AI testing?",
            "options": [
                "Deterministic outputs",
                "Simple algorithms",
                "Non-deterministic behavior",
                "Standard testing approaches"
            ],
            "answer": 2
        }
    ]
