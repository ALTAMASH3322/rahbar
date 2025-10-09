from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c  # Import config values
from werkzeug.utils import secure_filename
import os

from routes.sponsor import UPLOAD_FOLDER

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

    cursor.execute("SELECT * FROM grantor_grantees WHERE grantor_id = %s", (current_user.user_id,))
    grantor_grantee = cursor.fetchall()

    grantees = []
    for gg in grantor_grantee:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (gg['grantee_id'],))
        grantee = cursor.fetchone()
        grantees.append(grantee)

    status = "unpaid"

    for gg in grantor_grantee:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (gg['grantee_id'],))
        grantee = cursor.fetchone()

        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (gg['grantee_id'],))
        bank_details = cursor.fetchone()

        cursor.execute("SELECT * FROM payments WHERE grantee_id = %s order by payment_date DESC LIMIT 1",
                       (gg['grantee_id'],))
        payments = cursor.fetchall()

        cursor.execute("Select * from payment_schedules")
        payment_schedules = cursor.fetchall()
        frequency = 1
        status = "unpaid"
        print(payments, end=" ")
        print(payment_schedules)
        for i in payment_schedules:
            if payments[0]["amount"] == i["amount"]:
                frequency = i["schedule_id"]

        from datetime import datetime, timedelta

        # Get the current date
        current_date = datetime.now()

        # Initialize status
        status = "unpaid"

        # Define the time periods based on frequency
        if frequency == 1:
            # Check if payment_date is within the last year
            one_year_ago = current_date - timedelta(days=365)
            if payments[0]["payment_date"] >= one_year_ago:
                status = "paid"
        elif frequency == 2:
            # Check if payment_date is within the last 6 months
            six_months_ago = current_date - timedelta(days=180)
            if payments[0]["payment_date"] >= six_months_ago:
                status = "paid"
        elif frequency == 3:
            # Check if payment_date is within the last 3 months
            three_months_ago = current_date - timedelta(days=90)
            if payments[0]["payment_date"] >= three_months_ago:
                status = "paid"
        elif frequency == 4:
            # Check if payment_date is within the last month
            one_month_ago = current_date - timedelta(days=30)
            if payments[0]["payment_date"] >= one_month_ago and payments[0]["payment_date"] >= payment_schedules[3][
                "updated_at"]:
                status = "paid"

    cursor.close()
    conn.close()


    return render_template(
        'convenor/dashboard.html',
        convenor=convenor,
        applications=applications,
        grantees=grantees,
        sponsors=sponsors,
        grantor_grantee=grantor_grantee,
        status=status
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
        order=order,
        user =convenor  # Pass convenor to the template
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
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    convenor = cursor.fetchone()

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
    return redirect(url_for('convenor.view_applications', user =convenor))  # Pass convenor to the template

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

    return redirect(url_for('convenor.convenor_dashboard'))  # Pass convenor to the template

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


@convenor_bp.route('/convenor_payments', methods=['GET', 'POST'])
@login_required
def convenor_payments():
    # --- Authorization and Initial Setup ---
    if current_user.role_id != 4:  # Ensure only convenors can access
        return render_template('convenor/error.html', error="You do not have permission to access this page."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    convenor_id = current_user.user_id

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (convenor_id,))
    convenor = cursor.fetchone()

    # --- POST Method: Handle Payment Form Submission ---
    if request.method == 'POST':
        action = request.form.get('action')
        grantee_id = request.form.get('grantee_id')
        amount = request.form.get('amount')
        receipt = request.files.get('receipt')

        if action == 'pay':
            if not grantee_id or not amount or not receipt:
                flash('Grantee ID, amount, and receipt are required.', 'error')
                return redirect(url_for('convenor.convenor_payments'))

            # Save the receipt file
            filename = secure_filename(receipt.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            receipt.save(filepath)

            # Insert payment record with 'pending' status for convenor
            try:
                cursor.execute(
                    """
                    INSERT INTO payments (grantor_id, grantee_id, amount, payment_date, receipt_url, status)
                    VALUES (%s, %s, %s, NOW(), %s, 'pending')
                    """,
                    (convenor_id, grantee_id, amount, filepath)
                )
                conn.commit()
                flash('Payment recorded and is now pending approval.', 'success')
            except Exception as e:
                print(f"Database Error: {e}")
                conn.rollback()
                flash('An error occurred while processing the payment.', 'error')

        cursor.close()
        conn.close()
        return redirect(url_for('convenor.convenor_payments'))

    # -----------------------------------------------------------------
    # GET Method: Display Page and Prepare Data for JavaScript Frontend
    # -----------------------------------------------------------------

    # 1. Fetch all grantees assigned to this convenor
    cursor.execute("SELECT grantee_id FROM grantor_grantees WHERE grantor_id = %s", (convenor_id,))
    grantor_grantees = cursor.fetchall()
    student_ids = [gg['grantee_id'] for gg in grantor_grantees]

    students_for_dropdown = []
    student_data_map = {}

    # Proceed only if the convenor has assigned students
    if student_ids:
        # Create a placeholder string for the IN clause (e.g., "%s,%s,%s")
        id_placeholders = ','.join(['%s'] * len(student_ids))

        # 2. Fetch all required data in bulk to avoid N+1 query problem
        
        # Get all student user details at once
        cursor.execute(f"SELECT * FROM users WHERE user_id IN ({id_placeholders})", tuple(student_ids))
        all_students = {s['user_id']: s for s in cursor.fetchall()}
        
        # Get all bank details at once
        cursor.execute(f"SELECT * FROM bank_details WHERE user_id IN ({id_placeholders})", tuple(student_ids))
        all_bank_details = {b['user_id']: b for b in cursor.fetchall()}

        # Get all course info at once using a JOIN
        cursor.execute(f"""
            SELECT sic.user_id, sic.assigned_at, c.number_of_semesters, c.fees_per_semester
            FROM student_institution_courses sic
            JOIN courses c ON sic.course_id = c.course_id
            WHERE sic.user_id IN ({id_placeholders})
        """, tuple(student_ids))
        all_course_info = {ci['user_id']: ci for ci in cursor.fetchall()}

        # Get all 'Paid' AND 'pending' records for all students at once
        # This is important so the convenor can see payments they just submitted
        cursor.execute(f"""
            SELECT * FROM payments 
            WHERE grantee_id IN ({id_placeholders}) AND (status = 'Paid' OR status = 'pending')
            ORDER BY payment_date ASC
        """, tuple(student_ids))
        all_payment_records = cursor.fetchall()

        # Organize payments by student for easy lookup
        payments_by_student = {}
        for p in all_payment_records:
            gid = p['grantee_id']
            if gid not in payments_by_student:
                payments_by_student[gid] = []
            payments_by_student[gid].append(p)

        # 3. Assemble the final data structures for the template
        for student_id in student_ids:
            student = all_students.get(student_id)
            if not student:
                continue
            
            students_for_dropdown.append(student) # For the <select> dropdown

            course_info = all_course_info.get(student_id)
            paid_and_pending_records = payments_by_student.get(student_id, [])

            # Convert datetime objects to ISO strings for safe JSON serialization
            if course_info and course_info.get('assigned_at'):
                course_info['assigned_at'] = course_info['assigned_at'].isoformat()
            for record in paid_and_pending_records:
                if record.get('payment_date'):
                    record['payment_date'] = record['payment_date'].isoformat()
            
            # Build the final map for JavaScript
            student_data_map[student_id] = {
                "grantee": student,
                "bank_details": all_bank_details.get(student_id),
                "course_info": course_info,
                "paid_records": paid_and_pending_records # This name is kept for template consistency
            }

    # Fetch past payments for the simple history table at the bottom of the page
    cursor.execute("""
        SELECT p.*, u.name AS grantee_name
        FROM payments p
        JOIN users u ON p.grantee_id = u.user_id
        WHERE p.grantor_id = %s
    """, (convenor_id,))
    past_payments = cursor.fetchall()

    cursor.close()
    conn.close()

    # 4. Render the template with the new, structured data
    return render_template(
        'convenor/payment.html',
        convenor=convenor,
        past_payments=past_payments,
        student_data_map=student_data_map,
        students_for_dropdown=students_for_dropdown
    )