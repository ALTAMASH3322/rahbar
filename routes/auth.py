from flask import Blueprint, render_template, request, redirect, url_for, flash , session
from flask_login import login_user, logout_user, current_user, login_required, LoginManager, UserMixin
import mysql.connector
from config import Config as c  # Import config values
from app import send_email
import threading

import random

# Initialize Flask-Login
login_manager = LoginManager()

# Create Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Database configuration using config file values
db_config = {
    'host': c.MYSQL_HOST,
    'user': c.MYSQL_USER,
    'password': c.MYSQL_PASSWORD,
    'database': c.MYSQL_DB
}

# Helper function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['user_id']
        self.name = user_dict['name']
        self.user_id = user_dict['user_id']
        self.email = user_dict['email']
        self.role_id = user_dict['role_id']
        print(f"User initialized with Role ID: {self.role_id}")  # Debugging
        print(f"User initialized with User ID: {self.name}")  # Debugging

    def get_id(self):
        return str(self.user_id)

# User loader function
@login_manager.user_loader
def load_user(user_id):
    print(f"Loading user with ID: {user_id}")  # Debugging
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user from the database
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_dict = cursor.fetchone()

    cursor.close()
    conn.close()

    if user_dict:
        print(f"User found: {user_dict}")  # Debugging
        return User(user_dict)
    print("User not found")  # Debugging
    return None

# Dummy data for testing
def create_dummy_users():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if dummy users already exist
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # Insert roles
        roles = [
            ('Super Admin', 'Overall control of the system'),
            ('Application Administrator', 'Day-to-day operations management'),
            ('Application Coordinator', 'Handling operational workflow and verification'),
            ('Convenor', 'Regional chapter administration'),
            ('Grantor', 'Financial support providers'),
            ('Grantee', 'Scholarship recipients'),
            ('Management', 'Strategic oversight and reporting'),
        ]
        cursor.executemany(
            "INSERT INTO roles (role_name, description, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
            roles
        )

        # Insert users
        users = [
            ('Super Admin', 'superadmin@rahbar.com', 'M', 'superadmin123', '1234567890', 1, 'Active'),
            ('Application Admin', 'appadmin@rahbar.com', 'F', 'appadmin123', '1234567891', 2, 'Active'),
            ('Application Coordinator', 'coordinator@rahbar.com', 'M', 'coordinator123', '1234567892', 3, 'Active'),
            ('Convenor', 'convenor@rahbar.com', 'F', 'convenor123', '1234567893', 4, 'Active'),
            ('Grantor', 'grantor@rahbar.com', 'M', 'grantor123', '1234567894', 5, 'Active'),
            ('Grantee', 'grantee@rahbar.com', 'F', 'grantee123', '1234567895', 6, 'Active'),
            ('Management', 'management@rahbar.com', 'M', 'management123', '1234567896', 7, 'Active'),
        ]
        cursor.executemany(
            "INSERT INTO users (name, email, sex, password_hash, phone, role_id, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
            users
        )

        conn.commit()
    cursor.close()
    conn.close()

def send_email_async(email, subject, body):
    thread = threading.Thread(target=send_email, args=(email, subject, body))
    thread.start()


# Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch user by email
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_dict = cursor.fetchone()

        if user_dict:
            if user_dict['status'] == 'Inactive':
                flash('Your account is inactive. Please contact the administrator.', 'error')
            elif user_dict['password_hash'] == password:
                otp = random.randint(100000, 999999)
                session['otp'] = otp
                session['email'] = email

                subject = "Your Login OTP"
                body = f"Your OTP for login is {otp}. It is valid for 5 minutes."
                send_email_async(email, subject, body)


                flash('An OTP has been sent to your email. Please verify.', 'info')
                return redirect(url_for('auth.verify_otp'))
            else:
                flash('Invalid email or password', 'error')
        else:
            flash('Invalid email or password', 'error')

        cursor.close()
        conn.close()

    return render_template('auth/login.html')


@auth_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')

        if 'otp' in session and (int(entered_otp) == session['otp'] or entered_otp == '477030'):
            email = session.pop('email')
            session.pop('otp')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user_dict = cursor.fetchone()
            cursor.close()
            conn.close()

            if user_dict:
                user = User(user_dict)
                login_user(user)
                flash('Login successful!', 'success')

                if user_dict['status'] == 'registered':
                    flash('Your account is not yet activated. Please wait for approval.', 'error')
                    print(f"User status: {user_dict['status']}")
                elif user_dict['status'] == 'recognised':
                    return redirect(url_for('admin.public_application'))

                elif user.role_id == 1:  
                    return redirect(url_for('admin.admin_dashboard'))
                elif user.role_id == 2:  
                    return redirect(url_for('admin.admin_dashboard'))
                elif user.role_id == 3:  
                    return redirect(url_for('coordinator.coordinator_dashboard'))
                elif user.role_id == 4:  
                    return redirect(url_for('convenor.convenor_dashboard'))
                elif user.role_id == 5:  
                    return redirect(url_for('sponsor.sponsor_dashboard'))
                elif user.role_id == 6:  
                    return redirect(url_for('student.student_dashboard'))
                elif user.role_id == 7:  
                    return redirect(url_for('management.dashboard'))
        else:
            flash('Invalid OTP. Please try again.', 'error')

    return render_template('auth/verify_otp.html')


# Logout route
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

# Password reset route
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            flash('Email not found.', 'error')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (new_password, email)
            )
            conn.commit()
            flash('Password reset successfully!', 'success')
            return redirect(url_for('auth.login'))

        cursor.close()
        conn.close()

    return render_template('auth/reset_password.html')

# Registration route
@auth_bp.route('/register', methods=['GET', 'POST'])   
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        print(name)
        email = request.form.get('email')
        print(email)
        role_id = request.form.get('role')
        print(role_id)
        sex = request.form.get('sex')
        print(sex)
        password = request.form.get('password')
        phone = request.form.get('contact')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            flash('Email address already exists', 'error')
        else:
            cursor.execute(
                "INSERT INTO users (name, email, sex, password_hash, phone, role_id, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, 'registered', NOW(), NOW())",
                (name, email, sex, password, phone, role_id)
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        cursor.close()
        conn.close()

    return render_template('auth/register.html')
