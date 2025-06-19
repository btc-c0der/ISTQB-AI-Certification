import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import secrets
import hashlib
from db.database_refactored import get_or_create_user

# Define session directory
SESSION_DIR = Path(__file__).parent.parent / "data" / "sessions"

# Ensure session directory exists
os.makedirs(SESSION_DIR, exist_ok=True)

class UserSession:
    def __init__(self):
        """Initialize user session management."""
        self.current_user = None
        self.session_id = None
        self.session_data = {}
        
    def generate_session_id(self):
        """Generate a random session ID."""
        return secrets.token_urlsafe(32)
    
    def create_session(self, username, email=None):
        """Create a new user session."""
        # Get or create the user in the database
        user_id = get_or_create_user(username, email)
        
        # Create session data
        self.session_id = self.generate_session_id()
        self.current_user = {
            'id': user_id,
            'username': username,
            'email': email
        }
        
        # Save session data
        self.session_data = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        # Write session to file
        session_path = SESSION_DIR / f"{self.session_id}.json"
        with open(session_path, 'w') as f:
            json.dump(self.session_data, f)
        
        return self.session_id
    
    def load_session(self, session_id):
        """Load an existing user session."""
        session_path = SESSION_DIR / f"{session_id}.json"
        
        if not session_path.exists():
            return False
        
        try:
            with open(session_path, 'r') as f:
                self.session_data = json.load(f)
            
            # Check if session is expired
            expires_at = datetime.fromisoformat(self.session_data['expires_at'])
            if datetime.now() > expires_at:
                self.destroy_session(session_id)
                return False
            
            # Set current user
            self.current_user = {
                'id': self.session_data['user_id'],
                'username': self.session_data['username'],
                'email': self.session_data.get('email')
            }
            self.session_id = session_id
            
            return True
        except Exception as e:
            print(f"Error loading session: {str(e)}")
            return False
    
    def destroy_session(self, session_id):
        """Destroy a user session."""
        session_path = SESSION_DIR / f"{session_id}.json"
        
        if session_path.exists():
            try:
                os.remove(session_path)
                
                if self.session_id == session_id:
                    self.session_id = None
                    self.current_user = None
                    self.session_data = {}
                
                return True
            except Exception as e:
                print(f"Error destroying session: {str(e)}")
                return False
        
        return False
    
    def get_current_user(self):
        """Get the current authenticated user."""
        return self.current_user
    
    def get_user_id(self):
        """Get the current user's ID."""
        if self.current_user:
            return self.current_user['id']
        return None
    
    def is_authenticated(self):
        """Check if a user is currently authenticated."""
        return self.current_user is not None
    
    def is_admin(self):
        """Check if the current user is an admin."""
        if not self.is_authenticated():
            return False
        
        from db.database_refactored import is_admin
        return is_admin(self.current_user['username'])
    
    def make_admin(self, username):
        """Grant admin privileges to a user."""
        if not self.is_admin():
            return False, "You need admin privileges to perform this action"
        
        from db.database_refactored import set_admin_status
        success = set_admin_status(username, True)
        
        if success:
            return True, f"Admin privileges granted to {username}"
        else:
            return False, f"Failed to grant admin privileges to {username}"
    
    def revoke_admin(self, username):
        """Revoke admin privileges from a user."""
        if not self.is_admin():
            return False, "You need admin privileges to perform this action"
            
        # Don't allow revoking your own admin rights
        if self.current_user['username'] == username:
            return False, "Cannot revoke your own admin privileges"
        
        from db.database_refactored import set_admin_status
        success = set_admin_status(username, False)
        
        if success:
            return True, f"Admin privileges revoked from {username}"
        else:
            return False, f"Failed to revoke admin privileges from {username}"

# Create a global session instance
session_manager = UserSession()

def get_session_manager():
    """Get the global session manager instance."""
    return session_manager
