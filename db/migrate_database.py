"""
ISTQB AI Portal - Database Migration Script

This script helps migrate from the original database implementation to the refactored one.
It updates all necessary imports in application files to use the new database module.
"""

import os
import re
import sys
from pathlib import Path

def print_header(message):
    print("\n" + "=" * 80)
    print(f" {message} ".center(80))
    print("=" * 80 + "\n")

def print_step(message):
    print(f"➤ {message}")

def backup_file(file_path):
    """Create a backup of the original file."""
    backup_path = f"{file_path}.bak"
    with open(file_path, 'r') as f:
        content = f.read()
    
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print_step(f"Created backup at {backup_path}")
    return content

def update_imports(content):
    """Update imports from db.database to db.database_refactored."""
    # Replace direct imports
    updated = re.sub(
        r'from\s+db\.database\s+import',
        'from db.database_refactored import',
        content
    )
    
    # Replace module imports
    updated = re.sub(
        r'import\s+db\.database',
        'import db.database_refactored as db.database',
        updated
    )
    
    return updated

def process_file(file_path):
    """Process a file to update database imports."""
    print_step(f"Processing {file_path}...")
    
    # Read file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if file contains references to database module
    if 'db.database' not in content:
        print_step(f"No database imports found in {file_path}, skipping...")
        return False
    
    # Create backup
    backup_file(file_path)
    
    # Update imports
    updated_content = update_imports(content)
    
    # Write updated content
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print_step(f"Updated imports in {file_path}")
    return True

def rename_database_file():
    """Rename the refactored database file to replace the original."""
    print_step("Renaming database module files...")
    
    db_dir = Path(__file__).parent
    original_file = db_dir / "database.py"
    refactored_file = db_dir / "database_refactored.py"
    
    if not refactored_file.exists():
        print_step("ERROR: Refactored database file not found!")
        return False
    
    # Backup original database.py
    if original_file.exists():
        backup_path = original_file.with_suffix(".py.original")
        original_file.rename(backup_path)
        print_step(f"Original database.py backed up as {backup_path}")
    
    # Rename refactored file to replace original
    refactored_file.rename(original_file)
    print_step("Renamed database_refactored.py to database.py")
    
    return True

def find_python_files():
    """Find all Python files in the workspace that might use the database module."""
    workspace_dir = Path(__file__).parent.parent
    python_files = []
    
    for path in workspace_dir.rglob("*.py"):
        # Skip the database module itself and any backup files
        if path.name in ["database.py", "database_refactored.py"] or path.name.endswith(".bak"):
            continue
        
        # Skip the migration script itself
        if path.name == Path(__file__).name:
            continue
        
        python_files.append(path)
    
    return python_files

def run_migration():
    """Run the database migration process."""
    print_header("ISTQB AI Portal - Database Migration")
    
    print_step("Starting database migration process...")
    
    # Find Python files to update
    python_files = find_python_files()
    print_step(f"Found {len(python_files)} Python files to check for database usage")
    
    # Process each file
    updated_files = 0
    for file_path in python_files:
        if process_file(file_path):
            updated_files += 1
    
    print_step(f"Updated imports in {updated_files} file(s)")
    
    # Rename database file (comment this out if you want to keep both versions)
    # if rename_database_file():
    #     print_step("Database file replacement complete")
    
    print_header("Migration Complete")
    print("The database module has been refactored with the following improvements:")
    print("✓ Removed code duplication (DRY principle)")
    print("✓ Added proper connection handling with decorators")
    print("✓ Organized code into logical Data Access Object (DAO) classes")
    print("✓ Added better error handling and logging")
    print("✓ Improved schema management")
    print("\nYou can now use the refactored database module by importing from 'db.database_refactored'")
    print("or run this script with --replace to completely replace the original module.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--replace":
        run_migration()
        rename_database_file()
    else:
        run_migration()
