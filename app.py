import mysql.connector
from mysql.connector import Error
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
import os

# Flask app configuration
app = Flask(__name__)
app.secret_key = "replace_with_a_secret_key"
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
ALLOWED_EXT = {"pdf", "doc", "docx", "txt"}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_resume_file(file_storage):
    if file_storage and allowed_file(file_storage.filename):
        filename = secure_filename(file_storage.filename)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(full_path):
            import time
            name, ext = filename.rsplit('.', 1)
            filename = f"{name}_{int(time.time())}.{ext}"
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file_storage.save(full_path)
        return filename
    return None

# ------------------------ DATABASE CONNECTION ------------------------

def get_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="#Ks_31102006",
            database="job_recruitment_portal"
        )
        return connection
    except Error as e:
        print("❌ Error while connecting to MySQL:", e)
        return None

def execute_query(query, params=None):
    connection = get_connection()
    if connection is None:
        return None
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        connection.commit()
        print("✅ Query executed successfully.")
    except Error as e:
        print("❌ Error:", e)
    finally:
        cursor.close()
        connection.close()

def fetch_all(query, params=None):
    connection = get_connection()
    if connection is None:
        return []
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        return results
    except Error as e:
        print("❌ Error:", e)
        return []
    finally:
        cursor.close()
        connection.close()

# ------------------------ HELPER FUNCTIONS ------------------------

def check_candidate_profile_complete(candidate_id):
    """Check if candidate has completed their profile (phone, experience, skills)"""
    candidate = fetch_all("SELECT * FROM Candidate WHERE candidate_id=%s", (candidate_id,))[0]
    skills = fetch_all("SELECT * FROM Candidate_Skill_Map WHERE candidate_id=%s", (candidate_id,))
    
    # Check if basic info is complete
    if not candidate.get('phone') or candidate.get('experience_years') is None:
        return False
    # Check if at least one skill is added
    if not skills:
        return False
    return True

def check_recruiter_profile_complete(recruiter_id):
    """Check if recruiter has filled company details"""
    recruiter = fetch_all("SELECT * FROM Recruiter WHERE recruiter_id=%s", (recruiter_id,))[0]
    # Basic validation - can be expanded
    if not recruiter.get('company_name') or not recruiter.get('recruiter_name'):
        return False
    return True

# ------------------------ ROUTES ------------------------

@app.route('/')
def index():
    return render_template('index.html')

# Candidate signup
@app.route('/signup_candidate', methods=['POST'])
def signup_candidate():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    existing = fetch_all("SELECT * FROM Candidate WHERE email=%s", (email,))
    if existing:
        flash("Candidate already exists! Please login.", "warning")
        return redirect(url_for('index'))

    execute_query(
        "INSERT INTO Candidate (name, email, password) VALUES (%s,%s,%s)",
        (name, email, password)
    )
    flash("Registered successfully! Please login to complete your profile.", "success")
    return redirect(url_for('index'))

# Candidate login
@app.route('/login_candidate', methods=['POST'])
def login_candidate():
    email = request.form.get('email')
    password = request.form.get('password')

    user = fetch_all("SELECT * FROM Candidate WHERE email=%s AND password=%s", (email, password))
    if not user:
        flash("Invalid credentials or user not registered.", "danger")
        return redirect(url_for('index'))

    user = user[0]
    session['user_type'] = 'candidate'
    session['user_id'] = user['candidate_id']
    session['user_name'] = user['name']
    
    # Check if profile is complete
    if not check_candidate_profile_complete(user['candidate_id']):
        return redirect(url_for('candidate_onboarding'))
    
    return redirect(url_for('candidate_dashboard'))

# Recruiter signup
@app.route('/signup_recruiter', methods=['POST'])
def signup_recruiter():
    company = request.form.get('company_name')
    name = request.form.get('recruiter_name')
    email = request.form.get('email')
    password = request.form.get('password')

    existing = fetch_all("SELECT * FROM Recruiter WHERE email=%s", (email,))
    if existing:
        flash("Recruiter already exists! Please login.", "warning")
        return redirect(url_for('index'))

    execute_query(
        "INSERT INTO Recruiter (company_name, recruiter_name, email, password) VALUES (%s,%s,%s,%s)",
        (company, name, email, password)
    )
    flash("Registered successfully! Please login.", "success")
    return redirect(url_for('index'))

# Recruiter login
@app.route('/login_recruiter', methods=['POST'])
def login_recruiter():
    email = request.form['email']
    password = request.form['password']
    recruiter = fetch_all("SELECT * FROM Recruiter WHERE email=%s AND password=%s", (email, password))
    if not recruiter:
        flash("Invalid recruiter credentials", "danger")
        return redirect(url_for('index'))
    r = recruiter[0]
    session['user_type'] = 'recruiter'
    session['user_id'] = r['recruiter_id']
    session['user_name'] = r['recruiter_name']
    session['company_name'] = r['company_name']
    return redirect(url_for('recruiter_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

# ------------------------ CANDIDATE ONBOARDING ------------------------

@app.route('/candidate/onboarding', methods=['GET', 'POST'])
def candidate_onboarding():
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    
    cid = session['user_id']
    candidate = fetch_all("SELECT * FROM Candidate WHERE candidate_id=%s", (cid,))[0]
    
    if request.method == 'GET':
        # Get all available skills
        all_skills = fetch_all("SELECT * FROM Skill ORDER BY skill_name")
        return render_template('candidate_onboarding.html', candidate=candidate, all_skills=all_skills)
    
    # POST - Update profile
    phone = request.form.get('phone')
    experience = request.form.get('experience')
    resume_file = request.files.get('resume')
    
    resume_path = save_resume_file(resume_file) if resume_file and resume_file.filename else None
    
    execute_query("""
        UPDATE Candidate 
        SET phone=%s, experience_years=%s, resume_link=COALESCE(%s, resume_link)
        WHERE candidate_id=%s
    """, (phone, int(experience), resume_path, cid))
    
    # Add skills
    selected_skills = request.form.getlist('skills')
    if selected_skills:
        # Clear existing skills first
        execute_query("DELETE FROM Candidate_Skill_Map WHERE candidate_id=%s", (cid,))
        # Add new skills
        for skill_id in selected_skills:
            execute_query(
                "INSERT INTO Candidate_Skill_Map (candidate_id, skill_id) VALUES (%s,%s)",
                (cid, int(skill_id))
            )
    
    flash("Profile completed successfully!", "success")
    return redirect(url_for('candidate_dashboard'))

# ------------------------ CANDIDATE DASHBOARD ------------------------

@app.route('/candidate/dashboard')
def candidate_dashboard():
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    
    cid = session['user_id']
    
    # Check if profile is complete
    if not check_candidate_profile_complete(cid):
        return redirect(url_for('candidate_onboarding'))
    
    candidate = fetch_all("SELECT * FROM Candidate WHERE candidate_id=%s", (cid,))[0]
    skills = fetch_all("""
        SELECT s.skill_name FROM Candidate_Skill_Map m 
        JOIN Skill s ON m.skill_id=s.skill_id
        WHERE m.candidate_id=%s
    """, (cid,))
    
    # Recommended jobs
    rec_jobs = fetch_all("""
        SELECT DISTINCT j.* FROM Job_Post j
        JOIN Job_Skill_Map jm ON j.job_id=jm.job_id
        JOIN Candidate_Skill_Map cm ON cm.skill_id=jm.skill_id
        WHERE cm.candidate_id=%s
        ORDER BY j.post_date DESC
        LIMIT 10
    """, (cid,))
    
    return render_template('candidate_dashboard.html', candidate=candidate, skills=skills, rec_jobs=rec_jobs)

# View candidate applications
@app.route('/candidate/applications')
def candidate_applications():
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    cid = session['user_id']
    
    applications = fetch_all("""
        SELECT a.app_id, a.status, a.applied_date, j.job_id, j.title as job_title, j.location,
               r.company_name
        FROM Application a
        JOIN Job_Post j ON a.job_id = j.job_id
        JOIN Recruiter r ON j.recruiter_id = r.recruiter_id
        WHERE a.candidate_id = %s
        ORDER BY a.applied_date DESC
    """, (cid,))
    
    return render_template('applications.html', applications=applications)

# View candidate interviews
@app.route('/candidate/interviews')
def candidate_interviews():
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    cid = session['user_id']
    
    interviews = fetch_all("""
        SELECT i.interview_id, i.interview_date, i.interview_mode, i.interviewer_name,
               j.title as job_title, j.location, r.company_name, a.status,
               f.rating, f.comments as feedback_comments
        FROM Interview i
        JOIN Application a ON i.app_id = a.app_id
        JOIN Job_Post j ON a.job_id = j.job_id
        JOIN Recruiter r ON j.recruiter_id = r.recruiter_id
        LEFT JOIN Feedback f ON i.interview_id = f.interview_id
        WHERE a.candidate_id = %s
        ORDER BY i.interview_date DESC
    """, (cid,))
    
    return render_template('candidate_interviews.html', interviews=interviews)

# Update profile
@app.route('/candidate/update_profile', methods=['POST'])
def candidate_update_profile():
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    cid = session['user_id']
    phone = request.form.get('phone')
    exp = request.form.get('experience')
    resume_file = request.files.get('resume')
    resume_path = None
    if resume_file and resume_file.filename != '':
        resume_path = save_resume_file(resume_file)
    
    execute_query("""
        UPDATE Candidate 
        SET phone=COALESCE(%s,phone), 
            resume_link=COALESCE(%s,resume_link), 
            experience_years=COALESCE(%s,experience_years)
        WHERE candidate_id=%s
    """, (phone, resume_path, exp, cid))
    flash("Profile updated successfully.", "success")
    return redirect(url_for('candidate_dashboard'))

# Manage skills
@app.route('/candidate/manage_skills', methods=['GET', 'POST'])
def candidate_manage_skills():
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    
    cid = session['user_id']
    
    if request.method == 'GET':
        all_skills = fetch_all("SELECT * FROM Skill ORDER BY skill_name")
        current_skills = fetch_all("""
            SELECT skill_id FROM Candidate_Skill_Map WHERE candidate_id=%s
        """, (cid,))
        current_skill_ids = [s['skill_id'] for s in current_skills]
        return render_template('manage_skills.html', all_skills=all_skills, current_skill_ids=current_skill_ids)
    
    # POST - Update skills
    selected_skills = request.form.getlist('skills')
    execute_query("DELETE FROM Candidate_Skill_Map WHERE candidate_id=%s", (cid,))
    for skill_id in selected_skills:
        execute_query(
            "INSERT INTO Candidate_Skill_Map (candidate_id, skill_id) VALUES (%s,%s)",
            (cid, int(skill_id))
        )
    flash("Skills updated successfully!", "success")
    return redirect(url_for('candidate_dashboard'))

# ------------------------ RECRUITER DASHBOARD ------------------------

@app.route('/recruiter/dashboard')
def recruiter_dashboard():
    if session.get('user_type') != 'recruiter':
        return redirect(url_for('index'))
    rid = session['user_id']
    jobs = fetch_all("SELECT * FROM Job_Post WHERE recruiter_id=%s ORDER BY post_date DESC", (rid,))
    
    # Get application counts for each job
    for job in jobs:
        counts = fetch_all("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status='Applied' THEN 1 ELSE 0 END) as applied,
                   SUM(CASE WHEN status='Shortlisted' THEN 1 ELSE 0 END) as shortlisted,
                   SUM(CASE WHEN status='Selected' THEN 1 ELSE 0 END) as selected
            FROM Application WHERE job_id=%s
        """, (job['job_id'],))[0]
        job['app_counts'] = counts
    
    return render_template('recruiter_dashboard.html', jobs=jobs)

# View all interviews scheduled by recruiter
@app.route('/recruiter/interviews')
def recruiter_interviews():
    if session.get('user_type') != 'recruiter':
        return redirect(url_for('index'))
    rid = session['user_id']
    
    interviews = fetch_all("""
        SELECT i.interview_id, i.interview_date, i.interview_mode, i.interviewer_name,
               c.name as candidate_name, j.title as job_title, a.app_id, a.status as app_status,
               f.feedback_id, f.rating, f.comments
        FROM Interview i
        JOIN Application a ON i.app_id = a.app_id
        JOIN Candidate c ON a.candidate_id = c.candidate_id
        JOIN Job_Post j ON a.job_id = j.job_id
        LEFT JOIN Feedback f ON i.interview_id = f.interview_id
        WHERE j.recruiter_id = %s
        ORDER BY i.interview_date DESC
    """, (rid,))
    
    return render_template('recruiter_interviews.html', interviews=interviews)

# ------------------------ JOB ROUTES ------------------------

# View all jobs with filters
@app.route('/jobs')
def jobs_list():
    skill = request.args.get('skill')
    location = request.args.get('location')
    max_salary = request.args.get('max_salary')

    base = "SELECT DISTINCT j.*, r.company_name FROM Job_Post j JOIN Recruiter r ON j.recruiter_id=r.recruiter_id"
    joins = ""
    wheres = []
    params = []

    if skill:
        joins += " JOIN Job_Skill_Map jm ON j.job_id=jm.job_id JOIN Skill s ON jm.skill_id=s.skill_id"
        wheres.append("s.skill_name LIKE %s")
        params.append(f"%{skill}%")
    if location:
        wheres.append("j.location LIKE %s")
        params.append(f"%{location}%")
    if max_salary:
        wheres.append("j.salary <= %s")
        params.append(float(max_salary))

    query = base + joins
    if wheres:
        query += " WHERE " + " AND ".join(wheres)
    query += " ORDER BY j.post_date DESC"
    jobs = fetch_all(query, tuple(params))
    return render_template('view_jobs.html', jobs=jobs)

# Job details
@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = fetch_all("""
        SELECT j.*, r.company_name, r.recruiter_name 
        FROM Job_Post j 
        JOIN Recruiter r ON j.recruiter_id=r.recruiter_id 
        WHERE j.job_id=%s
    """, (job_id,))
    if not job:
        return "Job not found", 404
    job = job[0]
    skills = fetch_all("""
        SELECT s.skill_name FROM Job_Skill_Map jm 
        JOIN Skill s ON jm.skill_id=s.skill_id 
        WHERE jm.job_id=%s
    """, (job_id,))
    
    # Check if candidate already applied
    already_applied = False
    if session.get('user_type') == 'candidate':
        cid = session['user_id']
        app = fetch_all("SELECT * FROM Application WHERE candidate_id=%s AND job_id=%s", (cid, job_id))
        already_applied = len(app) > 0
    
    return render_template('job_detail.html', job=job, skills=skills, already_applied=already_applied)

# Apply for job
@app.route('/apply/<int:job_id>', methods=['POST'])
def apply_for_job(job_id):
    if session.get('user_type') != 'candidate':
        return redirect(url_for('index'))
    cid = session['user_id']
    try:
        execute_query(
            "INSERT INTO Application (candidate_id, job_id, status, applied_date) VALUES (%s,%s,'Applied',%s)",
            (cid, job_id, date.today())
        )
        flash("Applied successfully!", "success")
    except Exception as e:
        flash("You have already applied for this job.", "warning")
    return redirect(url_for('job_detail', job_id=job_id))

# Post a new job
@app.route('/recruiter/post_job', methods=['GET', 'POST'])
def recruiter_post_job():
    if session.get('user_type') != 'recruiter':
        return redirect(url_for('index'))
    rid = session['user_id']
    
    if request.method == 'GET':
        skills = fetch_all("SELECT * FROM Skill ORDER BY skill_name")
        return render_template('post_job.html', skills=skills)
    
    # POST
    title = request.form.get('title')
    desc = request.form.get('description')
    location = request.form.get('location')
    salary = request.form.get('salary') or 0
    
    execute_query(
        "INSERT INTO Job_Post (recruiter_id, title, description, location, salary, post_date) VALUES (%s,%s,%s,%s,%s,%s)",
        (rid, title, desc, location, float(salary), date.today())
    )
    
    job = fetch_all("SELECT LAST_INSERT_ID() as id")
    job_id = job[0]['id']
    
    selected_skills = request.form.getlist('skills')
    for sid in selected_skills:
        execute_query("INSERT INTO Job_Skill_Map (job_id, skill_id) VALUES (%s,%s)", (job_id, int(sid)))
    
    flash("Job posted successfully.", "success")
    return redirect(url_for('recruiter_dashboard'))

# View applicants for a job
@app.route('/recruiter/job/<int:job_id>/applications')
def recruiter_view_applicants(job_id):
    if session.get('user_type') != 'recruiter':
        return redirect(url_for('index'))
    
    # Get job details
    job = fetch_all("SELECT * FROM Job_Post WHERE job_id=%s", (job_id,))[0]
    
    apps = fetch_all("""
        SELECT a.app_id, a.status, a.applied_date, c.candidate_id, c.name, c.email, 
               c.resume_link, c.experience_years, c.phone
        FROM Application a 
        JOIN Candidate c ON a.candidate_id=c.candidate_id
        WHERE a.job_id=%s
        ORDER BY a.applied_date DESC
    """, (job_id,))
    
    for row in apps:
        row['skills'] = fetch_all("""
            SELECT s.skill_name FROM Candidate_Skill_Map m 
            JOIN Skill s ON m.skill_id=s.skill_id 
            WHERE m.candidate_id=%s
        """, (row['candidate_id'],))
        
        # Check if interview is scheduled
        row['interview'] = fetch_all("""
            SELECT * FROM Interview WHERE app_id=%s
        """, (row['app_id'],))
    
    return render_template('recruiter_applicants.html', applications=apps, job=job)

# Update application status
@app.route('/recruiter/application/<int:app_id>/status', methods=['POST'])
def recruiter_update_status(app_id):
    new_status = request.form.get('status')
    execute_query("UPDATE Application SET status=%s WHERE app_id=%s", (new_status, app_id))
    flash("Status updated successfully.", "success")
    return redirect(request.referrer or url_for('recruiter_dashboard'))

# Schedule interview
@app.route('/recruiter/application/<int:app_id>/schedule', methods=['POST'])
def recruiter_schedule_interview(app_id):
    interview_date = request.form.get('interview_date')
    mode = request.form.get('mode')
    interviewer = request.form.get('interviewer')
    
    # Check if interview already exists
    existing = fetch_all("SELECT * FROM Interview WHERE app_id=%s", (app_id,))
    if existing:
        flash("Interview already scheduled for this application.", "warning")
        return redirect(request.referrer)
    
    execute_query(
        "INSERT INTO Interview (app_id, interview_date, interview_mode, interviewer_name) VALUES (%s,%s,%s,%s)",
        (app_id, interview_date, mode, interviewer)
    )
    execute_query("UPDATE Application SET status='Shortlisted' WHERE app_id=%s", (app_id,))
    flash("Interview scheduled successfully.", "success")
    return redirect(request.referrer or url_for('recruiter_dashboard'))

# Give feedback form
@app.route('/recruiter/interview/<int:interview_id>/feedback_form')
def give_feedback_form(interview_id):
    if session.get('user_type') != 'recruiter':
        return redirect(url_for('index'))
    
    interview = fetch_all("""
        SELECT i.*, c.name as candidate, j.title as job, a.app_id, a.status as app_status
        FROM Interview i
        JOIN Application a ON i.app_id = a.app_id
        JOIN Candidate c ON a.candidate_id = c.candidate_id
        JOIN Job_Post j ON a.job_id = j.job_id
        WHERE i.interview_id = %s
    """, (interview_id,))
    
    if not interview:
        flash("Interview not found.", "danger")
        return redirect(url_for('recruiter_interviews'))
    
    interview = interview[0]
    
    # Check if feedback already exists
    existing_feedback = fetch_all(
        "SELECT * FROM Feedback WHERE interview_id=%s", 
        (interview_id,)
    )
    
    return render_template('feedback.html', 
                         interview=interview, 
                         existing_feedback=existing_feedback[0] if existing_feedback else None)

# Give feedback
@app.route('/recruiter/interview/<int:interview_id>/feedback', methods=['POST'])
def recruiter_give_feedback(interview_id):
    if session.get('user_type') != 'recruiter':
        return redirect(url_for('index'))
    
    rating = int(request.form.get('rating'))
    comments = request.form.get('comments')
    final_decision = request.form.get('final_decision')  # 'Selected' or 'Rejected' or 'Shortlisted'
    
    # Validate rating
    if rating < 1 or rating > 10:
        flash("Rating must be between 1 and 10.", "danger")
        return redirect(url_for('give_feedback_form', interview_id=interview_id))
    
    # Check if feedback already exists
    existing = fetch_all("SELECT * FROM Feedback WHERE interview_id=%s", (interview_id,))
    
    if existing:
        # Update existing feedback
        execute_query(
            "UPDATE Feedback SET rating=%s, comments=%s, feedback_date=%s WHERE interview_id=%s",
            (rating, comments, date.today(), interview_id)
        )
        flash("Feedback updated successfully.", "success")
    else:
        # Insert new feedback
        execute_query(
            "INSERT INTO Feedback (interview_id, rating, comments, feedback_date) VALUES (%s,%s,%s,%s)",
            (interview_id, rating, comments, date.today())
        )
        flash("Feedback submitted successfully.", "success")
    
    # Update application status based on final decision
    if final_decision:
        # Get app_id from interview
        interview = fetch_all("SELECT app_id FROM Interview WHERE interview_id=%s", (interview_id,))[0]
        execute_query("UPDATE Application SET status=%s WHERE app_id=%s", (final_decision, interview['app_id']))
        
        if final_decision == 'Selected':
            flash(f"Candidate has been marked as SELECTED! 🎉", "success")
        elif final_decision == 'Rejected':
            flash(f"Candidate has been marked as REJECTED.", "info")
    
    return redirect(url_for('recruiter_interviews'))

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        flash("Resume file not found. Please upload your resume again.", "warning")
        return redirect(url_for('candidate_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)