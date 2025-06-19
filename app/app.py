import os
import json
import re
import gradio as gr
import pandas as pd
import random
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path to enable imports
sys.path.append(str(Path(__file__).parent.parent))
from db.database_refactored import (
    initialize_database, 
    get_or_create_user, 
    update_topic_progress, 
    get_user_progress, 
    get_chapter_completion_stats,
    record_quiz_result,
    add_user_note,
    get_user_notes,
    get_system_statistics,
    get_all_users,
    get_user_details,
    delete_user
)
from utils.user import get_session_manager

# Get the root directory of the project
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

class ISTQBAIPortal:
    def __init__(self):
        """Initialize the ISTQB AI Portal by loading data."""
        # Initialize database
        try:
            initialize_database()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
        
        # Get session manager
        self.session_manager = get_session_manager()
        self.current_user = None
        
        # Load syllabus data
        self.load_data()
        self.user_id = None  # To be set upon user login
        self.session_manager = get_session_manager()
    
    def load_data(self):
        """Load processed syllabus data from JSON files."""
        try:
            with open(DATA_DIR / "chapters.json", "r") as f:
                self.chapters = json.load(f)
            
            with open(DATA_DIR / "learning_objectives.json", "r") as f:
                self.learning_objectives = json.load(f)
            
            with open(DATA_DIR / "terms.json", "r") as f:
                self.terms = json.load(f)
            
            with open(DATA_DIR / "topics.json", "r") as f:
                self.topics = json.load(f)
            
            # Create a dataframe for easier topic searching
            self.topics_df = pd.DataFrame(self.topics)
            return True
        except FileNotFoundError:
            print("Data files not found. Please run utils/init_data.py first to initialize the data.")
            return False
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
    
    def _highlight_text(self, text, query):
        """Highlights the query terms in the text by surrounding them with bold markdown."""
        if not query:
            return text
        
        # Create a pattern to find the query terms (case-insensitive)
        pattern = re.compile(f"({query})", re.IGNORECASE)
        
        # Replace each occurrence with the highlighted version
        highlighted = pattern.sub(r"**\1**", text)
        
        return highlighted
        
    def search_topics(self, query):
        """Search for topics that match the query."""
        if not query:
            return "Please enter a search query."
        
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Search in topics
        matches = self.topics_df[self.topics_df['topic'].str.lower().str.contains(query) | 
                              self.topics_df['context'].str.lower().str.contains(query)]
        
        if len(matches) == 0:
            return "No matches found for your query."
        
        # Remove duplicate contexts and group by chapter
        # First, create a set of unique contexts to remove duplicates
        unique_contexts = set()
        chapter_results = {}
        
        for _, row in matches.iterrows():
            chapter = row['chapter']
            topic = row['topic']
            context = row['context']
            
            # Skip if we've already seen this context
            if context in unique_contexts:
                continue
            
            # Add to set of unique contexts
            unique_contexts.add(context)
            
            # Group by chapter
            if chapter not in chapter_results:
                chapter_results[chapter] = []
            
            # Highlight the query terms in the context
            highlighted_context = self._highlight_text(context, query)
            
            chapter_results[chapter].append({
                'topic': topic,
                'context': highlighted_context
            })
        
        # Format results by chapter
        results = []
        results.append(f"# Search Results for: '{query}'\n\n")
        results.append(f"Found {len(unique_contexts)} unique results in {len(chapter_results)} chapters.\n\n")
        
        for chapter, contexts in chapter_results.items():
            chapter_section = f"## {chapter}\n\n"
            for item in contexts:
                chapter_section += f"**Topic:** {item['topic']}\n\n{item['context']}\n\n---\n\n"
            results.append(chapter_section)
        
        return "\n\n".join(results)
    
    def get_chapter_content(self, chapter_title):
        """Get the content of a specific chapter."""
        if chapter_title == "":
            return "Please select a chapter."
        
        content = self.chapters.get(chapter_title, "Chapter content not found.")
        
        # Format the content for better readability
        formatted_content = f"# {chapter_title}\n\n{content}"
        
        # Add learning objectives if available
        if chapter_title in self.learning_objectives and self.learning_objectives[chapter_title]:
            formatted_content += "\n\n## Learning Objectives\n\n"
            for i, lo in enumerate(self.learning_objectives[chapter_title], 1):
                formatted_content += f"{i}. {lo}\n"
        
        return formatted_content
    
    def get_glossary(self, filter_term=""):
        """Get the glossary of terms, optionally filtered."""
        if not self.terms:
            return "Glossary not available."
        
        # Filter terms if filter_term is provided
        if filter_term:
            filtered_terms = {term: defn for term, defn in self.terms.items() 
                             if filter_term.lower() in term.lower()}
        else:
            filtered_terms = self.terms
        
        if not filtered_terms:
            return f"No terms found matching '{filter_term}'."
        
        # Format glossary
        glossary_text = "# ISTQB AI Testing Glossary\n\n"
        for term, definition in sorted(filtered_terms.items()):
            glossary_text += f"**{term}**: {definition}\n\n"
        
        return glossary_text
    
    def get_quiz_question(self):
        """Get a random quiz question."""
        # In a real implementation, this would load from a questions database
        # or generate questions dynamically from the syllabus content
        questions = [
            {
                "question": "What is the main purpose of the ISTQB AI Testing certification?",
                "options": [
                    "To teach AI development from scratch",
                    "To provide testers with knowledge and skills for testing AI-based systems",
                    "To certify AI developers", 
                    "To replace traditional testing methods with AI"
                ],
                "answer": 1  # 0-indexed, so this refers to the second option
            },
            {
                "question": "Which of the following is a key challenge in AI system testing?",
                "options": [
                    "Deterministic outputs",
                    "Simple algorithms",
                    "Non-deterministic behavior",
                    "Standard testing approaches"
                ],
                "answer": 2
            },
            {
                "question": "What does explainability refer to in the context of AI systems?",
                "options": [
                    "The system's ability to run faster",
                    "How well users can understand how the AI reaches its decisions",
                    "The documentation quality of AI code",
                    "The accuracy of AI predictions"
                ],
                "answer": 1
            },
            {
                "question": "Which testing technique is most suitable for verifying the robustness of AI models?",
                "options": [
                    "Unit testing",
                    "Integration testing",
                    "Adversarial testing",
                    "Regression testing"
                ],
                "answer": 2
            },
            {
                "question": "What is a common way to evaluate the performance of a classification model?",
                "options": [
                    "Memory usage",
                    "Confusion matrix",
                    "Processing speed",
                    "Code complexity"
                ],
                "answer": 1
            }
        ]
        
        return random.choice(questions)
    
    def check_answer(self, question_data, selected_option):
        """Check if the selected answer is correct."""
        if question_data is None:
            return "Please get a question first."
        
        correct_answer_index = question_data["answer"]
        correct_answer = question_data["options"][correct_answer_index]
        
        if selected_option == correct_answer:
            return "✅ Correct! Well done."
        else:
            return f"❌ Incorrect. The correct answer is: {correct_answer}"
    
    def get_study_roadmap(self, username=None):
        """Generate a study roadmap based on the chapters and learning objectives."""
        if not hasattr(self, 'chapters') or not self.chapters:
            return "Study roadmap could not be generated. No chapter data available."
        
        # Check if a user is logged in or provided
        user_logged_in = self.is_authenticated() or username
        user_id = None
        user_progress = {}
        completion_stats = {}
        
        if username and not self.is_authenticated():
            # Auto-login with the provided username
            success, _ = self.login_user(username)
            if not success:
                return "Failed to create user session. Please try again."
        
        if self.is_authenticated():
            user_id = self.get_user_id()
            user_progress = get_user_progress(user_id)
            completion_stats = get_chapter_completion_stats(user_id)
        
        # Create the roadmap content
        roadmap_content = "# ISTQB AI Testing Certification Study Roadmap\n\n"
        
        if self.is_authenticated():
            roadmap_content += f"### Study Progress for: {self.get_current_user()['username']}\n\n"
        else:
            roadmap_content += "### Log in to track your study progress\n\n"
            roadmap_content += "This roadmap will guide you through your ISTQB AI Testing certification journey.\n\n"
        
        # Add estimated study time
        roadmap_content += "## Estimated Study Time\n\n"
        roadmap_content += "- Total study time: 40-60 hours\n"
        roadmap_content += "- Recommended pace: 8-10 hours per week\n"
        roadmap_content += "- Estimated completion time: 4-6 weeks\n\n"
        
        # Overall progress if user is logged in
        if self.is_authenticated():
            total_topics = 0
            completed_topics = 0
            
            for chapter_stats in completion_stats.values():
                total_topics += chapter_stats['total_topics']
                completed_topics += chapter_stats['completed_topics']
            
            overall_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            roadmap_content += f"## Overall Progress: {completed_topics}/{total_topics} topics ({overall_percentage:.1f}%)\n\n"
            
            # Progress bar representation
            progress_bar_length = 30
            filled_length = int(progress_bar_length * overall_percentage / 100)
            bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
            roadmap_content += f"```\n{bar}\n```\n\n"
            
        # Add chapter breakdown with learning objectives
        roadmap_content += "## Chapter Breakdown\n\n"
        
        # Create topics for tracking if user is logged in
        user_topics = {}
        
        for i, (chapter, content) in enumerate(self.chapters.items(), 1):
            # Extract chapter number if available, otherwise use the counter
            chapter_num = chapter.split('.')[0] if '.' in chapter else str(i)
            chapter_id = f"chapter_{chapter_num}"
            
            # Add chapter heading
            roadmap_content += f"### {chapter}\n\n"
            
            # Add progress information if user is logged in
            if self.is_authenticated() and chapter_id in completion_stats:
                stats = completion_stats[chapter_id]
                chapter_percentage = stats['completion_percentage']
                roadmap_content += f"**Progress:** {stats['completed_topics']}/{stats['total_topics']} topics ({chapter_percentage:.1f}%)\n\n"
                
                # Small progress bar
                chapter_bar_length = 20
                chapter_filled = int(chapter_bar_length * chapter_percentage / 100)
                chapter_bar = '█' * chapter_filled + '░' * (chapter_bar_length - chapter_filled)
                roadmap_content += f"```\n{chapter_bar}\n```\n\n"
            
            # Add estimated study time based on content length
            content_length = len(content)
            est_hours = max(1, round(content_length / 2000))  # Rough estimate based on content length
            roadmap_content += f"**Estimated study time:** {est_hours} hours\n\n"
            
            # Add brief description
            description = content[:200] + "..." if len(content) > 200 else content
            roadmap_content += f"**Description:** {description}\n\n"
            
            # Create a checklist of learning objectives if available
            if chapter in self.learning_objectives and self.learning_objectives[chapter]:
                roadmap_content += "**Learning Objectives:**\n\n"
                
                if not self.is_authenticated():
                    roadmap_content += "<small>*Log in to track your progress*</small>\n\n"
                
                for j, lo in enumerate(self.learning_objectives[chapter], 1):
                    topic_id = f"lo_{chapter_num}_{j}"
                    
                    if self.is_authenticated():
                        # Check if this topic is completed
                        is_completed = False
                        if chapter_id in user_progress and topic_id in user_progress[chapter_id]:
                            is_completed = user_progress[chapter_id][topic_id]['is_completed']
                        
                        # Add user-specific tracking for this topic
                        user_topics[f"{chapter_id}|{topic_id}"] = {
                            'chapter': chapter,
                            'topic': lo,
                            'is_completed': is_completed
                        }
                        
                        # Format as a checkbox
                        checkbox = "☑️" if is_completed else "☐"
                        roadmap_content += f"{checkbox} {lo} <small>*(ID: {topic_id})*</small>\n"
                    else:
                        roadmap_content += f"- {lo}\n"
                
                roadmap_content += "\n"
            
            # Add key terms related to this chapter as a checklist
            chapter_terms = {}
            for term, definition in self.terms.items():
                if term.lower() in content.lower() or any(term.lower() in obj.lower() for obj in self.learning_objectives.get(chapter, [])):
                    chapter_terms[term] = definition
            
            if chapter_terms:
                roadmap_content += "**Key Terms to Learn:**\n\n"
                
                if not self.is_authenticated():
                    roadmap_content += "<small>*Log in to track your progress*</small>\n\n"
                
                for j, term in enumerate(list(chapter_terms.keys())[:5], 1):  # Limit to 5 terms per chapter for brevity
                    topic_id = f"term_{chapter_num}_{j}"
                    
                    if self.is_authenticated():
                        # Check if this term is completed
                        is_completed = False
                        if chapter_id in user_progress and topic_id in user_progress[chapter_id]:
                            is_completed = user_progress[chapter_id][topic_id]['is_completed']
                        
                        # Add user-specific tracking for this topic
                        user_topics[f"{chapter_id}|{topic_id}"] = {
                            'chapter': chapter,
                            'topic': term,
                            'is_completed': is_completed
                        }
                        
                        # Format as a checkbox
                        checkbox = "☑️" if is_completed else "☐"
                        roadmap_content += f"{checkbox} {term} <small>*(ID: {topic_id})*</small>\n"
                    else:
                        roadmap_content += f"- {term}\n"
                
                roadmap_content += "\n"
            
            # Add study tips
            roadmap_content += "**Study Tips:**\n"
            roadmap_content += "- Read the chapter material thoroughly\n"
            roadmap_content += "- Make notes on key concepts\n"
            roadmap_content += "- Review related terms in the glossary\n"
            roadmap_content += "- Practice with sample questions\n\n"
            
            # Add separator between chapters
            roadmap_content += "---\n\n"
        
        # Add exam preparation tips at the end
        roadmap_content += "## Exam Preparation Tips\n\n"
        roadmap_content += "1. **Review All Chapters:** Ensure you have a good understanding of each chapter\n"
        roadmap_content += "2. **Focus on Terminology:** The exam will test your knowledge of AI testing terminology\n"
        roadmap_content += "3. **Practice Time Management:** The exam has a time limit, so practice answering questions within time constraints\n"
        roadmap_content += "4. **Take Sample Tests:** Use the Quiz feature to test your knowledge\n"
        roadmap_content += "5. **Join Study Groups:** Consider joining online forums or study groups focused on ISTQB certifications\n\n"
        
        # Add instructions for updating progress if logged in
        if self.is_authenticated():
            roadmap_content += "## Updating Your Progress\n\n"
            roadmap_content += "To mark items as complete or incomplete, use the checkboxes in the Topic Progress tab.\n\n"
            roadmap_content += "Each item has an ID shown in parentheses (e.g., lo_1_1, term_2_3) that you can use to update your progress.\n"
        
        # Store user topics in session for easier access
        if self.is_authenticated():
            self.user_topics = user_topics
        
        return roadmap_content
    
    def manage_cache(self, action="status"):
        """
        Manage the cached files.
        Actions: 
        - "status" (default): Show cache status
        - "clear": Clear all cached files
        """
        data_dir = Path(__file__).parent.parent / "data"
        cache_files = {
            "PDF": data_dir / "syllabus.pdf",
            "Chapters": data_dir / "chapters.json",
            "Learning Objectives": data_dir / "learning_objectives.json",
            "Terms": data_dir / "terms.json",
            "Topics": data_dir / "topics.json"
        }
        
        if action == "status":
            status = "# Cache Status\n\n"
            total_size = 0
            
            for name, file_path in cache_files.items():
                if file_path.exists():
                    size = file_path.stat().st_size
                    total_size += size
                    size_kb = size / 1024
                    size_mb = size_kb / 1024
                    
                    if size_mb >= 1:
                        size_str = f"{size_mb:.2f} MB"
                    else:
                        size_str = f"{size_kb:.2f} KB"
                        
                    modified = file_path.stat().st_mtime
                    modified_date = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
                    
                    status += f"- **{name}**: {size_str} (Last modified: {modified_date})\n"
                else:
                    status += f"- **{name}**: File not found\n"
            
            total_mb = total_size / (1024 * 1024)
            status += f"\n**Total cache size:** {total_mb:.2f} MB"
            return status
            
        elif action == "clear":
            cleared = []
            for name, file_path in cache_files.items():
                if file_path.exists():
                    try:
                        file_path.unlink()
                        cleared.append(name)
                    except Exception as e:
                        pass
                        
            if cleared:
                return f"Cache cleared successfully. Removed: {', '.join(cleared)}\n\nPlease restart the application to regenerate the necessary files."
            else:
                return "No cache files were found or could be removed."
                
        return "Invalid cache action specified."
    
    def login(self, username, password):
        """Log in a user."""
        user = get_or_create_user(username, password)
        self.user_id = user.id
        self.session_manager.set_user(user)
        return f"Logged in as {username}"
    
    def logout(self):
        """Log out the current user."""
        if self.user_id is not None:
            self.session_manager.logout()
            self.user_id = None
            return "Logged out successfully."
        else:
            return "No user is currently logged in."
    
    def get_user_progress(self):
        """Get the user's progress on topics and chapters."""
        if self.user_id is None:
            return "User not logged in."
        
        progress = get_user_progress(self.user_id)
        return progress
    
    def update_progress(self, chapter, topic, status):
        """Update the progress of a specific topic in a chapter."""
        if self.user_id is None:
            return "User not logged in."
        
        update_topic_progress(self.user_id, chapter, topic, status)
        return f"Progress updated for {topic} in {chapter}."
    
    def get_chapter_stats(self, chapter):
        """Get completion statistics for a specific chapter."""
        if self.user_id is None:
            return "User not logged in."
        
        stats = get_chapter_completion_stats(self.user_id, chapter)
        return stats
    
    def record_quiz_result(self, quiz_name, score, total_questions):
        """Record the result of a quiz taken by the user."""
        if self.user_id is None:
            return "User not logged in."
        
        record_quiz_result(self.user_id, quiz_name, score, total_questions)
        return f"Quiz result recorded: {score}/{total_questions} for {quiz_name}."
    
    def add_user_note(self, note):
        """Add a note for the user."""
        if self.user_id is None:
            return "User not logged in."
        
        add_user_note(self.user_id, note)
        return "Note added."
    
    def get_user_notes(self):
        """Get the notes of the user."""
        if self.user_id is None:
            return "User not logged in."
        
        notes = get_user_notes(self.user_id)
        return notes
    
    def login_user(self, username, email=None):
        """Log in a user (create or get existing user)."""
        if not username:
            return False, "Please enter a username"
        
        try:
            # Create session for the user
            session_id = self.session_manager.create_session(username, email)
            self.current_user = self.session_manager.get_current_user()
            
            return True, f"Welcome, {username}! Your study progress will be saved."
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False, f"Error logging in: {str(e)}"
    
    def logout_user(self):
        """Log out the current user."""
        if self.session_manager.session_id:
            self.session_manager.destroy_session(self.session_manager.session_id)
            self.current_user = None
            return "You have been logged out."
        return "No active session to log out from."
    
    def get_current_user(self):
        """Get the current user information."""
        return self.session_manager.get_current_user()
    
    def is_authenticated(self):
        """Check if a user is currently authenticated."""
        return self.session_manager.is_authenticated()
    
    def get_user_id(self):
        """Get the ID of the current user."""
        return self.session_manager.get_user_id()
    
    def update_topic_progress(self, topic_key, is_completed):
        """Update the progress for a specific topic."""
        if not self.is_authenticated():
            return "Please log in first to track your progress."
        
        try:
            # Parse the topic key format: "chapter_id|topic_id"
            if "|" not in topic_key:
                return "Invalid topic key format."
            
            chapter_id, topic_id = topic_key.split("|")
            
            # Update the topic progress in the database
            user_id = self.get_user_id()
            update_success = update_topic_progress(user_id, chapter_id, topic_id, is_completed)
            
            if update_success:
                # Update the in-memory topic list
                if hasattr(self, 'user_topics') and topic_key in self.user_topics:
                    self.user_topics[topic_key]['is_completed'] = is_completed
                
                status = "completed" if is_completed else "marked as incomplete"
                topic_name = self.user_topics.get(topic_key, {}).get('topic', topic_id) if hasattr(self, 'user_topics') else topic_id
                return f"Topic '{topic_name}' {status}."
            else:
                return "Failed to update topic progress."
        except Exception as e:
            print(f"Error updating topic progress: {str(e)}")
            return f"Error: {str(e)}"
    
    def is_admin(self):
        """Check if the current user is an admin."""
        return self.session_manager.is_admin()
    
    def make_admin(self, username):
        """Make a user an admin."""
        return self.session_manager.make_admin(username)
    
    def revoke_admin(self, username):
        """Revoke admin privileges from a user."""
        return self.session_manager.revoke_admin(username)
    
    def get_admin_dashboard(self):
        """Get the admin dashboard content."""
        if not self.is_admin():
            return "# Access Denied\n\nYou need admin privileges to view this dashboard."
        
        stats = get_system_statistics()
        
        dashboard = "# Admin Dashboard\n\n"
        dashboard += f"## System Statistics\n\n"
        dashboard += f"- **Total Users:** {stats['total_users']}\n"
        dashboard += f"- **New Users (Last 7 Days):** {stats['new_users_7_days']}\n"
        dashboard += f"- **Topics Completed:** {stats['total_topics_completed']}\n"
        dashboard += f"- **Study Notes Created:** {stats['total_notes']}\n"
        dashboard += f"- **Quiz Attempts:** {stats['total_quiz_attempts']}\n"
        dashboard += f"- **Average Quiz Score:** {stats['avg_quiz_score']:.2f}%\n\n"
        
        # Most active chapters
        if stats['most_active_chapters']:
            dashboard += "## Most Active Chapters\n\n"
            for idx, chapter in enumerate(stats['most_active_chapters'], 1):
                dashboard += f"{idx}. **{chapter['chapter_id']}** - {chapter['completion_count']} completions\n"
            dashboard += "\n"
        
        dashboard += "Use the User Management tab to view and manage all users.\n"
        
        return dashboard
    
    def get_user_list(self):
        """Get a list of all users for the admin panel."""
        if not self.is_admin():
            return "# Access Denied\n\nYou need admin privileges to view user data."
        
        users = get_all_users()
        
        if not users:
            return "# No Users\n\nNo registered users found in the system."
        
        user_list = "# User Management\n\n"
        user_list += "| ID | Username | Email | Admin | Created | Progress | Notes | Quizzes |\n"
        user_list += "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        
        for user in users:
            created_at = user['created_at'].split('T')[0] if 'T' in user['created_at'] else user['created_at']
            is_admin = "✓" if user['is_admin'] else ""
            
            user_list += f"| {user['id']} | {user['username']} | {user['email']} | {is_admin} | {created_at} | "
            user_list += f"{user['progress_items']} | {user['notes_count']} | {user['quiz_attempts']} |\n"
        
        user_list += "\n\nTo manage a user, enter their user ID in the form below.\n"
        
        return user_list
    
    def get_user_details(self, user_id):
        """Get detailed information about a specific user."""
        if not self.is_admin():
            return "Access Denied. You need admin privileges to view user details."
        
        try:
            user_id = int(user_id)
            user_data = get_user_details(user_id)
            
            if not user_data:
                return f"No user found with ID: {user_id}"
            
            details = f"# User Details: {user_data['username']}\n\n"
            details += f"**User ID:** {user_data['id']}\n"
            details += f"**Email:** {user_data['email']}\n"
            details += f"**Admin:** {'Yes' if user_data['is_admin'] else 'No'}\n"
            details += f"**Created:** {user_data['created_at']}\n\n"
            
            # Progress statistics
            if 'progress' in user_data:
                progress = user_data['progress']
                completion_pct = progress['completion_percentage']
                details += f"## Study Progress\n\n"
                details += f"- **Topics Completed:** {progress['completed_topics']} of {progress['total_topics']}\n"
                details += f"- **Completion Rate:** {completion_pct:.2f}%\n"
                
                # Progress bar
                bar_length = 30
                filled = int(bar_length * completion_pct / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                details += f"\n```\n{bar}\n```\n\n"
            
            # Quiz statistics
            if 'quiz_stats' in user_data:
                quiz = user_data['quiz_stats']
                details += f"## Quiz Performance\n\n"
                details += f"- **Attempts:** {quiz['attempts']}\n"
                details += f"- **Average Score:** {quiz['avg_score']:.2f}%\n\n"
            
            # Study time statistics
            if 'study_stats' in user_data:
                study = user_data['study_stats']
                total_hours = study['total_minutes'] / 60 if study['total_minutes'] else 0
                details += f"## Study Time\n\n"
                details += f"- **Sessions:** {study['sessions']}\n"
                details += f"- **Total Study Time:** {total_hours:.2f} hours\n\n"
            
            # Admin actions
            details += f"## Admin Actions\n\n"
            details += f"Use the User Management section to modify this user's permissions or delete the account."
            
            return details
        except Exception as e:
            return f"Error retrieving user details: {str(e)}"
    
    def update_user_admin_status(self, user_id, make_admin):
        """Grant or revoke admin privileges for a user."""
        if not self.is_admin():
            return "Access Denied. You need admin privileges to change user permissions."
        
        try:
            # Get the username from the user ID
            user_id = int(user_id)
            user_data = get_user_details(user_id)
            
            if not user_data:
                return f"No user found with ID: {user_id}"
            
            username = user_data['username']
            
            # Don't allow changing your own status
            if self.get_current_user()['username'] == username:
                return "You cannot modify your own admin status."
            
            # Update admin status
            if make_admin:
                success, message = self.make_admin(username)
            else:
                success, message = self.revoke_admin(username)
            
            return message
        except Exception as e:
            return f"Error updating admin status: {str(e)}"
    
    def delete_user_account(self, user_id, confirmation):
        """Delete a user account (admin only)."""
        if not self.is_admin():
            return "Access Denied. You need admin privileges to delete user accounts."
        
        if confirmation != "DELETE":
            return "Action canceled. Please type DELETE (all caps) to confirm."
        
        try:
            user_id = int(user_id)
            
            # Don't allow deleting your own account
            if user_id == self.get_user_id():
                return "You cannot delete your own account."
            
            success, message = delete_user(user_id, self.get_user_id())
            
            return message
        except Exception as e:
            return f"Error deleting user: {str(e)}"
    
    def get_topic_progress(self):
        """Generate the topic progress management interface."""
        if not self.is_authenticated():
            return "Please log in first to view and update your progress."
        
        try:
            # Get user progress data
            user_id = self.get_user_id()
            user_progress = get_user_progress(user_id)
            completion_stats = get_chapter_completion_stats(user_id)
            
            # Format the progress management interface
            result = f"# Topic Progress for {self.get_current_user()['username']}\n\n"
            
            # Organize topics by chapter
            chapters = {}
            if hasattr(self, 'user_topics'):
                for topic_key, topic_data in self.user_topics.items():
                    chapter = topic_data['chapter']
                    if chapter not in chapters:
                        chapters[chapter] = []
                    
                    chapters[chapter].append({
                        'key': topic_key,
                        'topic': topic_data['topic'],
                        'is_completed': topic_data['is_completed']
                    })
            
            # Generate the progress table for each chapter
            for chapter, topics in chapters.items():
                result += f"## {chapter}\n\n"
                result += "| Status | Topic | Topic ID |\n"
                result += "| --- | --- | --- |\n"
                
                for topic in topics:
                    checkbox = "☑️" if topic['is_completed'] else "☐"
                    chapter_id, topic_id = topic['key'].split("|")
                    result += f"| {checkbox} | {topic['topic']} | {topic_id} |\n"
                
                result += "\n"
            
            # Add instructions for updating progress
            result += "## How to Update Your Progress\n\n"
            result += "To mark a topic as complete or incomplete, enter the Topic ID and select the status below.\n\n"
            
            return result
        except Exception as e:
            print(f"Error generating topic progress interface: {str(e)}")
            return f"Error: {str(e)}"
        

def create_gradio_interface():
    """Create and launch the Gradio interface."""
    portal = ISTQBAIPortal()
    
    # Get chapter titles for the dropdown
    chapter_titles = list(portal.chapters.keys()) if hasattr(portal, 'chapters') else []
    
    with gr.Blocks(title="ISTQB AI Certification Study Portal") as demo:
        # Header with login/logout area
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("# ISTQB AI Certification Study Portal")
                gr.Markdown("Welcome to the ISTQB AI Certification Study Portal. Use this tool to explore the syllabus, search topics, review terminology, and track your progress.")
            
            # User authentication area
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### User Account")
                    username_input = gr.Textbox(label="Username", placeholder="Enter your username")
                    email_input = gr.Textbox(label="Email (optional)", placeholder="Enter your email")
                    with gr.Row():
                        login_button = gr.Button("Login/Register")
                        logout_button = gr.Button("Logout")
                    auth_message = gr.Markdown()
        
        # Login functionality
        login_button.click(
            fn=portal.login_user,
            inputs=[username_input, email_input],
            outputs=auth_message
        )
        logout_button.click(
            fn=portal.logout_user,
            inputs=[],
            outputs=auth_message
        )
        
        with gr.Tabs():
            # Search tab
            with gr.Tab("Search"):
                with gr.Row():
                    search_input = gr.Textbox(label="Search for topics, keywords, or concepts")
                    search_button = gr.Button("Search")
                search_results = gr.Markdown(label="Search Results")
                search_button.click(fn=portal.search_topics, inputs=search_input, outputs=search_results)
            
            # Study Roadmap tab
            with gr.Tab("Study Roadmap"):
                with gr.Row():
                    with gr.Column(scale=3):
                        roadmap_username = gr.Textbox(label="Username (to load/create progress)", placeholder="Enter username to track progress")
                    with gr.Column(scale=1):
                        roadmap_button = gr.Button("Generate Study Roadmap")
                    with gr.Column(scale=1):
                        view_style = gr.Radio(choices=["Detailed View", "Table View"], value="Detailed View", label="View Style")
                
                roadmap_content = gr.Markdown(label="Study Roadmap")
                
                # Modified function to handle view style
                def generate_roadmap_with_style(username, style):
                    roadmap = portal.get_study_roadmap(username)
                    if style == "Table View" and portal.is_authenticated():
                        # Add table view at the top
                        user_id = portal.get_user_id()
                        completion_stats = get_chapter_completion_stats(user_id)
                        
                        table_view = "# ISTQB AI Study Roadmap: Table View\n\n"
                        table_view += f"## Progress for: {portal.get_current_user()['username']}\n\n"
                        
                        # Chapter summary table
                        table_view += "| Chapter | Progress | Completion | Study Time |\n"
                        table_view += "| --- | --- | --- | --- |\n"
                        
                        for chapter, content in portal.chapters.items():
                            chapter_num = chapter.split('.')[0] if '.' in chapter else "?"
                            chapter_id = f"chapter_{chapter_num}"
                            
                            # Estimate study time
                            content_length = len(content)
                            est_hours = max(1, round(content_length / 2000))
                            
                            if chapter_id in completion_stats:
                                stats = completion_stats[chapter_id]
                                chapter_percentage = stats['completion_percentage']
                                
                                # Mini progress bar
                                mini_bar_length = 15
                                mini_filled = int(mini_bar_length * chapter_percentage / 100)
                                mini_bar = '█' * mini_filled + '░' * (mini_bar_length - mini_filled)
                                
                                table_view += f"| {chapter} | {stats['completed_topics']}/{stats['total_topics']} | {chapter_percentage:.1f}% | ~{est_hours} hours |\n"
                            else:
                                table_view += f"| {chapter} | 0/0 | 0% | ~{est_hours} hours |\n"
                        
                        table_view += "\n\n---\n\n"
                        
                        # Append the original roadmap
                        return table_view + roadmap
                    else:
                        return roadmap
                
                # Connect the button to the function
                roadmap_button.click(
                    fn=generate_roadmap_with_style, 
                    inputs=[roadmap_username, view_style], 
                    outputs=roadmap_content
                )
            
            # Topic Progress tab
            with gr.Tab("Topic Progress"):
                progress_button = gr.Button("Load Topic Progress")
                topic_progress = gr.Markdown(label="Topic Progress")
                
                with gr.Group():
                    gr.Markdown("### Update Topic Progress")
                    with gr.Row():
                        topic_id = gr.Textbox(label="Topic ID", placeholder="e.g., lo_1_2 or term_3_1")
                        topic_status = gr.Radio(choices=["Complete", "Incomplete"], label="Status")
                    update_button = gr.Button("Update Progress")
                    update_message = gr.Markdown()
                
                # Load progress function
                progress_button.click(
                    fn=portal.get_topic_progress,
                    inputs=[],
                    outputs=topic_progress
                )
                
                # Update progress function
                def handle_progress_update(topic_id, status):
                    is_completed = status == "Complete"
                    result = portal.update_topic_progress(topic_id, is_completed)
                    # Refresh the progress display after update
                    progress_display = portal.get_topic_progress()
                    return result, progress_display
                
                update_button.click(
                    fn=handle_progress_update,
                    inputs=[topic_id, topic_status],
                    outputs=[update_message, topic_progress]
                )
            
            # Notes tab
            with gr.Tab("Study Notes"):
                with gr.Group():
                    gr.Markdown("### Add a Note")
                    note_chapter = gr.Dropdown(choices=chapter_titles, label="Select Chapter")
                    note_content = gr.Textbox(label="Note Content", lines=5, placeholder="Enter your study note here...")
                    add_note_button = gr.Button("Add Note")
                    note_message = gr.Markdown()
                
                view_notes_button = gr.Button("View All Notes")
                notes_display = gr.Markdown(label="Your Study Notes")
                
                # Add note function
                add_note_button.click(
                    fn=portal.add_note,
                    inputs=[note_chapter, note_content],
                    outputs=note_message
                )
                
                # View notes function
                view_notes_button.click(
                    fn=portal.get_user_notes,
                    inputs=[],
                    outputs=notes_display
                )
            
            # Chapter Browser tab
            with gr.Tab("Chapter Browser"):
                with gr.Row():
                    chapter_dropdown = gr.Dropdown(choices=chapter_titles, label="Select a chapter")
                chapter_content = gr.Markdown(label="Chapter Content")
                chapter_dropdown.change(fn=portal.get_chapter_content, inputs=chapter_dropdown, outputs=chapter_content)
            
            # Glossary tab
            with gr.Tab("Glossary"):
                with gr.Row():
                    glossary_filter = gr.Textbox(label="Filter terms (optional)")
                    glossary_button = gr.Button("Show Glossary")
                glossary_content = gr.Markdown(label="Glossary")
                glossary_button.click(fn=portal.get_glossary, inputs=glossary_filter, outputs=glossary_content)
            
            # Quiz tab
            with gr.Tab("Quiz"):
                # State for the current question
                question_state = gr.State(None)
                
                with gr.Row():
                    get_question_button = gr.Button("Get a Question")
                
                question_display = gr.Markdown(label="Question")
                
                with gr.Row():
                    options_radio = gr.Radio(choices=[], label="Select your answer")
                    
                with gr.Row():
                    check_answer_button = gr.Button("Submit Answer")
                    
                answer_result = gr.Markdown(label="Result")
                
                # Function to get and display a question
                def display_question():
                    question_data = portal.get_quiz_question()
                    question_text = f"**{question_data['question']}**"
                    return question_data, question_text, question_data["options"]
                
                get_question_button.click(
                    fn=display_question,
                    outputs=[question_state, question_display, options_radio]
                )
                
                # Function to check answer
                check_answer_button.click(
                    fn=portal.check_answer,
                    inputs=[question_state, options_radio],
                    outputs=answer_result
                )
                
            # Settings tab
            with gr.Tab("Settings"):
                gr.Markdown("## Cache Management")
                gr.Markdown("The application caches the syllabus PDF and processed data to improve performance. You can view cache status or clear the cache here.")
                
                with gr.Row():
                    cache_action = gr.Radio(
                        choices=["View cache status", "Clear cache"],
                        value="View cache status",
                        label="Cache Action"
                    )
                    cache_button = gr.Button("Execute")
                
                cache_result = gr.Markdown(label="Cache Results")
                
                # Function to handle cache management
                def handle_cache_action(action):
                    if action == "View cache status":
                        return portal.manage_cache(action="status")
                    elif action == "Clear cache":
                        return portal.manage_cache(action="clear")
                    return "Invalid action"
                
                cache_button.click(
                    fn=handle_cache_action,
                    inputs=cache_action,
                    outputs=cache_result
                )
                
            # Admin tab - only visible to admins
            with gr.Tab("Admin", visible=portal.is_admin()):
                # Admin Dashboard
                gr.Markdown("# Admin Panel")
                gr.Markdown("This panel is only visible to administrators. Here you can view system statistics and manage users.")
                
                # Section tabs within Admin
                with gr.Tabs():
                    # Dashboard tab
                    with gr.Tab("Dashboard"):
                        dashboard_refresh = gr.Button("Refresh Dashboard")
                        admin_dashboard = gr.Markdown(label="Admin Dashboard")
                        
                        # Load the dashboard on refresh
                        dashboard_refresh.click(
                            fn=portal.get_admin_dashboard,
                            inputs=[],
                            outputs=admin_dashboard
                        )
                        
                        # Load dashboard initially
                        admin_dashboard.update(portal.get_admin_dashboard())
                    
                    # User Management tab
                    with gr.Tab("User Management"):
                        user_list_refresh = gr.Button("Refresh User List")
                        user_list = gr.Markdown(label="User List")
                        
                        # Load user list on refresh
                        user_list_refresh.click(
                            fn=portal.get_user_list,
                            inputs=[],
                            outputs=user_list
                        )
                        
                        # Load user list initially
                        user_list.update(portal.get_user_list())
                        
                        # User details section
                        with gr.Group():
                            gr.Markdown("## User Details")
                            user_id_input = gr.Number(label="User ID", precision=0, minimum=1)
                            view_user_button = gr.Button("View User Details")
                            user_details = gr.Markdown(label="User Details")
                            
                            # View user details on button click
                            view_user_button.click(
                                fn=portal.get_user_details,
                                inputs=user_id_input,
                                outputs=user_details
                            )
                        
                        # User management actions
                        with gr.Group():
                            gr.Markdown("## User Management Actions")
                            
                            # Admin status management
                            with gr.Row():
                                admin_user_id = gr.Number(label="User ID", precision=0, minimum=1)
                                admin_action = gr.Radio(choices=["Make Admin", "Revoke Admin"], label="Admin Action")
                            admin_action_button = gr.Button("Update Admin Status")
                            admin_action_result = gr.Markdown(label="Result")
                            
                            def handle_admin_action(user_id, action):
                                make_admin = action == "Make Admin"
                                return portal.update_user_admin_status(user_id, make_admin)
                            
                            admin_action_button.click(
                                fn=handle_admin_action,
                                inputs=[admin_user_id, admin_action],
                                outputs=admin_action_result
                            )
                            
                            # User deletion
                            with gr.Group():
                                gr.Markdown("### Delete User")
                                gr.Markdown("⚠️ **WARNING**: This will permanently delete the user account and all associated data. This action cannot be undone.")
                                
                                with gr.Row():
                                    delete_user_id = gr.Number(label="User ID to Delete", precision=0, minimum=1)
                                    delete_confirmation = gr.Textbox(label="Type DELETE to confirm")
                                
                                delete_button = gr.Button("Delete User", variant="stop")
                                delete_result = gr.Markdown(label="Result")
                                
                                delete_button.click(
                                    fn=portal.delete_user_account,
                                    inputs=[delete_user_id, delete_confirmation],
                                    outputs=delete_result
                                )
        
        # About section
        gr.Markdown("## About this Portal")
        gr.Markdown("""
        This portal is designed to help you prepare for the ISTQB AI Testing Certification.
        
        The content is based on the official ISTQB AI Testing Syllabus v1.0.
        
        For more information, visit [ISTQB's official website](https://www.istqb.org/).
        """)
    
    return demo


if __name__ == "__main__":
    app = create_gradio_interface()
    app.launch()
