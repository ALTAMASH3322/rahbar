from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c  # Import config values
from werkzeug.utils import secure_filename
import os

# Create Blueprint for convenor routes
convenor_bp = Blueprint('convenor', __name__)

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

# Convenor Dashboard
@convenor_bp.route('/convenor_dashboard', methods=['GET'])
@login_required
def convenor_dashboard():
    # Ensure only Convenors can access this route
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch convenor details including region
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    convenor = cursor.fetchone()

    # Ensure the convenor has a region set
    if not convenor.get('region'):
        flash('Your region is not set. Please update your profile.', 'error')
        return redirect(url_for('convenor.update_profile'))

    # Fetch applications for the convenor's region
    cursor.execute("""
        SELECT a.*, u.name AS applicant_name
        FROM grantee_details a
        JOIN users u ON a.user_id = u.user_id
        WHERE u.region = %s
    """, (convenor['region'],))  # Filter by convenor's region
    applications = cursor.fetchall()

    # Fetch grantees for the convenor's region
    cursor.execute("""
        SELECT u.*
        FROM users u
        JOIN grantee_details gd ON u.user_id = gd.user_id
        WHERE u.region = %s
    """, (convenor['region'],))  # Filter by convenor's region
    grantees = cursor.fetchall()

    # Fetch sponsors for the convenor's region
    cursor.execute("""
        SELECT u.*
        FROM users u
        JOIN grantor_grantees gg ON u.user_id = gg.grantor_id
        JOIN grantee_details gd ON gg.grantee_id = gd.user_id
        WHERE u.region = %s
    """, (convenor['region'],))  # Filter by convenor's region
    sponsors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'convenor/dashboard.html',
        convenor=convenor,
        applications=applications,
        grantees=grantees,
        sponsors=sponsors
    )

# View Applications with Sorting
@convenor_bp.route('/view_applications', methods=['GET'])
@login_required
def view_applications():
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    # Fetch convenor details including region
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    convenor = cursor.fetchone()

    if not convenor.get('region'):
        flash('Your region is not set. Please update your profile.', 'error')
        return redirect(url_for('convenor.update_profile'))

    # Get sorting parameters from the request
    sort_by = request.args.get('sort_by', 'application_id')  # Default sort by application_id
    order = request.args.get('order', 'asc')  # Default order is ascending

    # Validate sort_by and order to prevent SQL injection
    valid_sort_columns = ['application_id', 'applicant_name', 'status', 'date_submitted']
    valid_orders = ['asc', 'desc']

    if sort_by not in valid_sort_columns:
        sort_by = 'application_id'
    if order not in valid_orders:
        order = 'asc'

    # Fetch applications for the convenor's region with sorting
    cursor.execute(f"""
        SELECT a.*, u.name AS applicant_name
        FROM grantee_details a
        JOIN users u ON a.user_id = u.user_id
        WHERE u.region = %s
        ORDER BY {sort_by} {order}
    """, (convenor['region'],))  # Filter by convenor's region
    applications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'convenor/view_applications.html',
        applications=applications,
        sort_by=sort_by,
        order=order
    )

# Approve/Reject Applications
@convenor_bp.route('/update_application_status/<int:application_id>', methods=['POST'])
@login_required
def update_application_status(application_id):
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    status = request.form.get('status')
    comments = request.form.get('comments')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update application status
    cursor.execute("""
        UPDATE grantee_details
        SET status = %s, comments = %s
        WHERE application_id = %s
    """, (status, comments, application_id))
    conn.commit()

    cursor.close()
    conn.close()

    flash('Application status updated successfully!', 'success')
    return redirect(url_for('convenor.view_applications'))

# Manage Sponsors with Sorting
@convenor_bp.route('/manage_sponsors', methods=['GET'])
@login_required
def manage_sponsors():
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    # Fetch convenor details including region
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    convenor = cursor.fetchone()

    if not convenor.get('region'):
        flash('Your region is not set. Please update your profile.', 'error')
        return redirect(url_for('convenor.update_profile'))

    # Get sorting parameters from the request
    sort_by = request.args.get('sort_by', 'user_id')  # Default sort by user_id
    order = request.args.get('order', 'asc')  # Default order is ascending

    # Validate sort_by and order to prevent SQL injection
    valid_sort_columns = ['user_id', 'name', 'email', 'status']
    valid_orders = ['asc', 'desc']

    if sort_by not in valid_sort_columns:
        sort_by = 'user_id'
    if order not in valid_orders:
        order = 'asc'

    # Fetch sponsors for the convenor's region with sorting
    cursor.execute(f"""
        SELECT u.*
        FROM users u
        WHERE u.role_id = 5 AND u.region = %s
        ORDER BY {sort_by} {order}
    """, (convenor['region'],))  # Filter by convenor's region
    sponsors = cursor.fetchall()

    # Fetch non-assigned grantees (assigned to grantor 12)
    cursor.execute("""
        SELECT u.*
        FROM users u
        JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        WHERE gg.grantor_id = 12
    """)
    non_assigned_grantees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'convenor/manage_sponsors.html',
        convenor=convenor,  # Pass convenor to the template
        sponsors=sponsors,
        non_assigned_grantees=non_assigned_grantees,  # Pass non-assigned grantees
        sort_by=sort_by,
        order=order
    )

# Update Sponsor Status (Activate/Deactivate)
@convenor_bp.route('/update_sponsor_status/<int:sponsor_id>/<status>', methods=['GET'])
@login_required
def update_sponsor_status(sponsor_id, status):
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update sponsor status
        cursor.execute("""
            UPDATE users
            SET status = %s
            WHERE user_id = %s
        """, (status, sponsor_id))
        conn.commit()

        # If the sponsor is being deactivated, reassign their grantees to grantor 12
        if status == 'Inactive':
            # Reassign grantees to grantor 12
            cursor.execute("""
                UPDATE grantor_grantees
                SET grantor_id = 12
                WHERE grantor_id = %s
            """, (sponsor_id,))
            conn.commit()

            flash(f'Sponsor status updated to {status}, and grantees reassigned to default grantor (ID: 12).', 'success')
        else:
            flash(f'Sponsor status updated to {status}!', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('convenor.manage_sponsors'))

# Map Students to Sponsor
@convenor_bp.route('/map_students/<int:sponsor_id>', methods=['GET', 'POST'])
@login_required
def map_students(sponsor_id):
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch convenor details including region
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    convenor = cursor.fetchone()

    if not convenor.get('region'):
        flash('Your region is not set. Please update your profile.', 'error')
        return redirect(url_for('convenor.update_profile'))

    if request.method == 'POST':
        # Get selected student IDs
        student_ids = request.form.getlist('student_ids')

        # Map students to the sponsor
        for student_id in student_ids:
            cursor.execute("""
                    UPDATE grantor_grantees
                    SET grantor_id = %s
                    WHERE grantee_id = %s
                """, (sponsor_id, student_id))
        conn.commit()

        flash('Students mapped successfully!', 'success')
        return redirect(url_for('convenor.manage_sponsors'))

    # Fetch all students in the convenor's region
    cursor.execute("""
            SELECT u.*
            FROM users u
            JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
            WHERE gg.grantor_id = %s
        """, (12,))  # Use convenor's region from the database
    students = cursor.fetchall()

    # Fetch students already mapped to the sponsor (with full details)
    cursor.execute("""
        SELECT u.*
        FROM users u
        JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        WHERE gg.grantor_id = %s
    """, (sponsor_id,))
    mapped_students = cursor.fetchall()

    # Extract user IDs from mapped_students
    mapped_student_ids = [student['user_id'] for student in mapped_students]

    # Debugging: Print mapped students and their IDs
    print("Mapped Students:", mapped_students)
    print("Mapped Student IDs:", mapped_student_ids)
    print("All Students:", students)


    cursor.close()
    conn.close()

    return render_template(
        'convenor/map_students.html',
        convenor=convenor,  # Pass convenor to the template
        students=students,
        mapped_students=mapped_students,  # Pass full details of mapped students
        mapped_student_ids=mapped_student_ids,  # Pass only the IDs for comparison
        sponsor_id=sponsor_id
    )

# View Student Progress
@convenor_bp.route('/view_student_progress', methods=['GET'])
@convenor_bp.route('/view_student_progress/<int:grantee_id>', methods=['GET'])
@login_required
def view_student_progress(grantee_id=None):
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch convenor details including region
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    convenor = cursor.fetchone()

    if not convenor.get('region'):
        flash('Your region is not set. Please update your profile.', 'error')
        return redirect(url_for('convenor.update_profile'))

    # Get filter and sort parameters from the request
    grantee_name = request.args.get('grantee_name')
    min_marks = request.args.get('min_marks', type=float)
    max_marks = request.args.get('max_marks', type=float)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    sort_by = request.args.get('sort_by')

    # Base query
    query = """
        SELECT sp.*, u.name AS grantee_name
        FROM student_progress sp
        JOIN users u ON sp.grantee_id = u.user_id
        WHERE u.region = %s
    """
    params = [convenor['region']]

    # Add filters to the query
    if grantee_name:
        query += " AND u.name LIKE %s"
        params.append(f"%{grantee_name}%")
    if min_marks is not None:
        query += " AND sp.marks >= %s"
        params.append(min_marks)
    if max_marks is not None:
        query += " AND sp.marks <= %s"
        params.append(max_marks)
    if start_date:
        query += " AND sp.created_at >= %s"
        params.append(start_date)
    if end_date:
        query += " AND sp.created_at <= %s"
        params.append(end_date)

    # Add sorting to the query
    if sort_by:
        query += f" ORDER BY {sort_by}"
        if sort_by == 'marks':
            query += " DESC"  # Sort marks in descending order by default

    # Execute the query
    cursor.execute(query, params)
    progress_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'convenor/view_student_progress.html',
        progress_data=progress_data,
        grantee_id=grantee_id,
        convenor=convenor
    )

# Upload Files (e.g., Reports)
@convenor_bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if current_user.role_id != 4:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    file = request.files.get('file')
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
        flash('File uploaded successfully!', 'success')
    else:
        flash('No file selected.', 'error')

    return redirect(url_for('convenor.convenor_dashboard'))

# Serve Uploaded Files
@convenor_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# Update Profile (to set region)
@convenor_bp.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        region = request.form.get('region')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET region = %s
            WHERE user_id = %s
        """, (region, current_user.user_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('convenor.convenor_dashboard'))

    return render_template('convenor/update_profile.html')