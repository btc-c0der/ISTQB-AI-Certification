# ISTQB AI Certification Study Portal

An interactive web portal to help you study for the ISTQB AI Testing Certification exam.

## Features

- **User Accounts**: Create a user account to track your study progress
- **Chapter Browser**: Read and navigate through the official syllabus content
- **Search**: Find specific topics and concepts across the entire syllabus with highlighted match terms
- **Interactive Study Roadmap**: Get a structured study plan with chapter breakdowns and progress tracking
- **Progress Checklist**: Mark topics and learning objectives as complete as you study
- **Study Notes**: Add and review your personal notes for each chapter
- **Glossary**: Review key terminology and definitions
- **Quiz**: Test your knowledge with practice questions
- **Settings**: Manage cached content and application settings
- **Admin Panel**: Full CRM system for administrators to manage users and view system statistics

## Database Architecture

The application uses SQLite for data storage with two available database implementations:

1. **Original Implementation** (`db/database.py`): The initial database implementation.
2. **Refactored Implementation** (`db/database_refactored.py`): A DRY, modular implementation with:
   - Data Access Object (DAO) pattern for better organization
   - Transaction handling with decorators
   - Centralized error handling and logging
   - Generic CRUD operations
   - Better schema management

To switch to the refactored implementation, run the migration script:
```bash
python -m db.migrate_database
```

Or to completely replace the original implementation:
```bash
python -m db.migrate_database --replace
```

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ISTQB-AI-Certification.git
   cd ISTQB-AI-Certification
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```
3. The application will automatically download and process the ISTQB AI Testing syllabus PDF the first time it runs.

4. Create a user account using the login form at the top right to track your progress.

5. Use the "Study Roadmap" tab to get a structured study plan and track your progress through the syllabus.

6. Use the "Topic Progress" tab to update your progress by marking topics as complete.

7. Add study notes in the "Study Notes" tab to record important concepts and insights.

8. Use the "Settings" tab to manage the cache if you need to refresh the content.

9. **Admin Access**: Log in with username `admin` to access the Admin panel with full CRM functionality.
4. Use the "Study Roadmap" tab to get a structured study plan.
## Project Structure

```
ISTQB-AI-Certification/
├── app/
│   └── app.py             # Gradio web application
├── data/                  # Processed syllabus data (auto-generated)
│   ├── chapters.json
│   ├── learning_objectives.json
│   ├── sessions/          # User session data
│   ├── syllabus.pdf       # Cached PDF file
│   ├── terms.json
│   └── topics.json
├── db/
│   ├── database.py        # Database interface
│   ├── database_refactored.py # Refactored database interface
│   ├── init_db.py         # Database initialization script
│   └── istqb_portal.db    # SQLite database file (auto-generated)
├── models/                # ISTQB AI Testing models and frameworks
│   ├── istqb_ai_comprehensive_model.md     # Comprehensive ISTQB AI testing model
│   ├── istqb_ai_testing_process.md         # ISTQB AI testing process model
│   └── istqb_ai_database_testing_patterns.md # ISTQB AI database testing patterns
├── tests/
│   ├── features/         # BDD feature files for non-functional testing
│   ├── steps/            # Step definitions for BDD features
│   ├── models/           # Testing models and frameworks
│   └── README.md         # Testing documentation
├── utils/
│   ├── init_data.py       # Data initialization script
│   ├── syllabus_processor.py  # PDF processing utilities
│   └── user.py            # User session management
├── main.py                # Main application entry point
├── README.md
└── requirements.txt       # Project dependencies
```

## Content Source

The content in this portal is based on the official [ISTQB AI Testing Syllabus](https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CT-AI_Syllabus_v1.0_mghocmT.pdf) version 1.0.

## ISTQB AI Testing Models

The project includes comprehensive ISTQB AI testing models that can be used as reference material when studying for the ISTQB AI Testing certification:

1. **Comprehensive AI Testing Model** (`models/istqb_ai_comprehensive_model.md`): A detailed model covering all aspects of AI testing according to ISTQB guidelines.

2. **AI Testing Process Model** (`models/istqb_ai_testing_process.md`): A process-focused model detailing each phase of testing AI systems.

3. **AI Database Testing Patterns** (`models/istqb_ai_database_testing_patterns.md`): Specific patterns for testing databases that support AI systems.

4. **BDD Test Suite**: A complete set of BDD feature files and step definitions demonstrating non-functional testing of database systems to ISTQB standards.

## License

This project is for educational purposes and based on ISTQB content. Please refer to the ISTQB website for their content license terms.
