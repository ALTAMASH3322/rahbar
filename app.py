from flask import Flask
from flask_login import LoginManager, UserMixin
import mysql.connector
from config import Config as c  # Import your config

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

    # Flask-Login required methods
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
    #print(f"Loading user with ID: {user_id}")  # Debugging
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user from the database
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_dict = cursor.fetchone()

    cursor.close()
    conn.close()

    if user_dict:
        #print(f"User found: {user_dict}")  # Debugging
        return User(user_dict)
    #print("User not found")  # Debugging
    return None  # Return None if the user is not found

def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object('config.Config')

    # Set a secret key for session management
    import os

    app.secret_key = os.urandom(24).hex()  # Replace with a strong secret key

    # Initialize extensions
    login_manager.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = 'auth.login'  # Redirect to login page if unauthorized
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'error'

    # Debugging: #print current_user for every request
    @app.before_request
    def before_request():
        from flask_login import current_user
        #print(f"Current User: {current_user}")  # Debugging

    # Import and register Blue#prints
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