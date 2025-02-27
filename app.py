from flask import Flask, Response
from flask_login import LoginManager, UserMixin
import mysql.connector
from config import Config as c  # Import your config
from flask_talisman import Talisman  # Install with: pip install flask-talisman

# Initialize Flask-Login
login_manager = LoginManager()

# Helper function to get a database connection
def get_db_connection():
    return mysql.connector.connect(
        host=c.MYSQL_HOST,
        user=c.MYSQL_USER,
        password=c.MYSQL_PASSWORD,
        database=c.MYSQL_DB
    )

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_dict):
        self.user_id = user_dict['user_id']
        self.email = user_dict['email']
        self.role_id = user_dict['role_id']

    def get_id(self):
        return str(self.user_id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True  # Assuming all users are active

    @property
    def is_anonymous(self):
        return False

# User loader function
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_dict = cursor.fetchone()

    cursor.close()
    conn.close()

    return User(user_dict) if user_dict else None  # Return User object if found

# Function to create Flask app
def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object('config.Config')

    # Set a strong secret key for session management
    import os
    app.secret_key = os.urandom(24).hex()  

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Redirect to login page if unauthorized
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'error'

    # Content Security Policy (CSP) Configuration
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",  # Allow scripts from the same origin
            "https://cdn.datatables.net",  # Allow DataTables CDN
            "https://code.jquery.com",  # Allow jQuery CDN
            "https://cdnjs.cloudflare.com",  # Allow Bootstrap & FontAwesome
            "'unsafe-inline'"  # Allow inline scripts (if needed)
        ],
        'style-src': [
            "'self'",
            "https://cdn.datatables.net",
            "https://cdnjs.cloudflare.com",
            "'unsafe-inline'"
        ],
    }

    # Apply security policies with Talisman
    Talisman(app, content_security_policy=csp)

    # Import and register Blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.convenor import convenor_bp
    from routes.sponsor import sponsor_bp
    from routes.student import student_bp
    from routes.coordinator import coordinator_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(sponsor_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(convenor_bp)
    app.register_blueprint(coordinator_bp)
    app.register_blueprint(admin_bp)

    return app
