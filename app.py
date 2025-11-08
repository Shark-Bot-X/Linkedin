import mysql.connector
from mysql.connector import Error
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os

# after your imports/config
app = Flask(__name__)
app.secret_key = "replace_with_a_secret_key"
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
ALLOWED_EXT = {"pdf", "doc", "docx", "txt"}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_resume_file(file_storage):
    if file_storage and allowed_file(file_storage.filename):
        filename = secure_filename(file_storage.filename)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # if same name exists, append timestamp
        if os.path.exists(full_path):
            import time
            name, ext = filename.rsplit('.', 1)
            filename = f"{name}_{int(time.time())}.{ext}"
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file_storage.save(full_path)
        return full_path
    return None

# Candidate signup (supports file upload)
@app.route('/signup_candidate', methods=['POST'])
def signup_candidate():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone') or None
    exp = request.form.get('experience') or 0
    password = request.form.get('password')

    # handle resume file
    resume_file = request.files.get('resume')
    resume_path = None
    if resume_file and resume_file.filename != '':
        resume_path = save_resume_file(resume_file)

    # check existing
    existing = fetch_all("SELECT * FROM Candidate WHERE email=%s", (email,))
    if existing:
        flash("Candidate already exists! Please login.", "warning")
        return redirect(url_for('index'))

    # NOTE: storing plaintext password is not secure for production.
    execute_query(
        "INSERT INTO Candidate (name, email, phone, resume_link, experience_years, password) VALUES (%s,%s,%s,%s,%s,%s)",
        (name, email, phone, resume_path, int(exp), password)
    )
    flash("Registered! Please login.", "success")
    return redirect(url_for('index'))


# Candidate login (sets session)
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
    return redirect(url_for('candidate_dashboard'))

@app.route('/login_recruiter', methods=['POST'])
def login_recruiter():
    email = request.form['email']; password = request.form['password']
    recruiter = fetch_all("SELECT * FROM Recruiter WHERE email=%s AND password=%s", (email, password))
    if not recruiter:
        flash("Invalid recruiter credentials", "danger"); return redirect(url_for('index'))
    r = recruiter[0]
    session['user_type'] = 'recruiter'
    session['user_id'] = r['recruiter_id']
    session['user_name'] = r['recruiter_name']
    return redirect(url_for('recruiter_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Candidate Dashboard
@app.route('/candidate/dashboard')
def candidate_dashboard():
    if session.get('user_type') != 'candidate': return redirect(url_for('index'))
    cid = session['user_id']
    # candidate profile
    candidate = fetch_all("SELECT * FROM Candidate WHERE candidate_id=%s", (cid,))[0]
    # candidate skills
    skills = fetch_all("""
        SELECT s.skill_name FROM Candidate_Skill_Map m JOIN Skill s ON m.skill_id=s.skill_id
        WHERE m.candidate_id=%s
    """, (cid,))
    # recommended jobs based on skills (job has at least one required skill in candidate skill set)
    rec_jobs = fetch_all("""
        SELECT DISTINCT j.* FROM Job_Post j
        JOIN Job_Skill_Map jm ON j.job_id=jm.job_id
        JOIN Candidate_Skill_Map cm ON cm.skill_id=jm.skill_id
        WHERE cm.candidate_id=%s
        LIMIT 10
    """, (cid,))
    return render_template('candidate_dashboard.html', candidate=candidate, skills=skills, rec_jobs=rec_jobs)


# Update profile (phone, experience, resume update)
@app.route('/candidate/update_profile', methods=['POST'])
def candidate_update_profile():
    if session.get('user_type') != 'candidate': return redirect(url_for('index'))
    cid = session['user_id']
    phone = request.form.get('phone')
    exp = request.form.get('experience')
    resume_file = request.files.get('resume')
    resume_path = None
    if resume_file and resume_file.filename!='':
        resume_path = save_resume_file(resume_file)
    # update
    execute_query("""
        UPDATE Candidate SET phone=COALESCE(%s,phone), resume_link=COALESCE(%s,resume_link), experience_years=COALESCE(%s,experience_years)
        WHERE candidate_id=%s
    """, (phone, resume_path, exp, cid))
    flash("Profile updated.", "success")
    return redirect(url_for('candidate_dashboard'))


# Recruiter Dashboard
@app.route('/recruiter/dashboard')
def recruiter_dashboard():
    if session.get('user_type') != 'recruiter': return redirect(url_for('index'))
    rid = session['user_id']
    jobs = fetch_all("SELECT * FROM Job_Post WHERE recruiter_id=%s", (rid,))
    return render_template('recruiter_dashboard.html', jobs=jobs)

# View all jobs + search filters (skills, location, salary)
@app.route('/jobs')
def jobs_list():
    # filters via query params
    skill = request.args.get('skill')  # skill name
    location = request.args.get('location')
    max_salary = request.args.get('max_salary')

    base = "SELECT DISTINCT j.* FROM Job_Post j"
    joins = ""
    wheres = []
    params = []

    if skill:
        joins += " JOIN Job_Skill_Map jm ON j.job_id=jm.job_id JOIN Skill s ON jm.skill_id=s.skill_id"
        wheres.append("s.skill_name LIKE %s")
        params.append(f"%{skill}%")
    if location:
        wheres.append("j.location LIKE %s"); params.append(f"%{location}%")
    if max_salary:
        wheres.append("j.salary <= %s"); params.append(float(max_salary))

    query = base + joins
    if wheres:
        query += " WHERE " + " AND ".join(wheres)
    jobs = fetch_all(query, tuple(params))
    return render_template('jobs_list.html', jobs=jobs)


# Job details
@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = fetch_all("SELECT * FROM Job_Post WHERE job_id=%s", (job_id,))
    if not job: return "Job not found", 404
    job = job[0]
    skills = fetch_all("SELECT s.skill_name FROM Job_Skill_Map jm JOIN Skill s ON jm.skill_id=s.skill_id WHERE jm.job_id=%s", (job_id,))
    return render_template('job_detail.html', job=job, skills=skills)

@app.route('/apply/<int:job_id>', methods=['POST'])
def apply_for_job(job_id):
    if session.get('user_type') != 'candidate': return redirect(url_for('index'))
    cid = session['user_id']
    # Attempt insert, catch duplicate error
    try:
        execute_query("INSERT INTO Application (candidate_id, job_id, status, applied_date) VALUES (%s,%s,'Applied',%s)", (cid, job_id, date.today()))
        flash("Applied successfully!", "success")
    except Exception as e:
        # If unique constraint violation, show message
        flash("You have already applied for this job.", "warning")
    return redirect(url_for('job_detail', job_id=job_id))

@app.route('/recruiter/post_job', methods=['GET', 'POST'])
def recruiter_post_job():
    if session.get('user_type') != 'recruiter': return redirect(url_for('index'))
    rid = session['user_id']
    if request.method == 'GET':
        skills = fetch_all("SELECT * FROM Skill")
        return render_template('post_job.html', skills=skills)
    # POST
    title = request.form.get('title')
    desc = request.form.get('description')
    location = request.form.get('location')
    salary = request.form.get('salary') or 0
    execute_query("INSERT INTO Job_Post (recruiter_id, title, description, location, salary, post_date) VALUES (%s,%s,%s,%s,%s,%s)",
                  (rid, title, desc, location, float(salary), date.today()))
    # get last job id
    job = fetch_all("SELECT LAST_INSERT_ID() as id")
    job_id = job[0]['id']
    selected_skills = request.form.getlist('skills')  # list of skill_id strings
    for sid in selected_skills:
        execute_query("INSERT INTO Job_Skill_Map (job_id, skill_id) VALUES (%s,%s)", (job_id, int(sid)))
    flash("Job posted.", "success")
    return redirect(url_for('recruiter_dashboard'))

# View applicants for a job
@app.route('/recruiter/job/<int:job_id>/applications')
def recruiter_view_applicants(job_id):
    if session.get('user_type') != 'recruiter': return redirect(url_for('index'))
    apps = fetch_all("""
        SELECT a.app_id, a.status, a.applied_date, c.candidate_id, c.name, c.email, c.resume_link
        FROM Application a JOIN Candidate c ON a.candidate_id=c.candidate_id
        WHERE a.job_id=%s
    """, (job_id,))
    # fetch candidate skills for each
    for row in apps:
        row['skills'] = fetch_all("SELECT s.skill_name FROM Candidate_Skill_Map m JOIN Skill s ON m.skill_id=s.skill_id WHERE m.candidate_id=%s", (row['candidate_id'],))
    return render_template('recruiter_applicants.html', applications=apps, job_id=job_id)

# Update application status
@app.route('/recruiter/application/<int:app_id>/status', methods=['POST'])
def recruiter_update_status(app_id):
    new_status = request.form.get('status')  # Shortlisted/Rejected/Selected
    execute_query("UPDATE Application SET status=%s WHERE app_id=%s", (new_status, app_id))
    flash("Status updated.", "success")
    return redirect(request.referrer or url_for('recruiter_dashboard'))

# Schedule interview
@app.route('/recruiter/application/<int:app_id>/schedule', methods=['POST'])
def recruiter_schedule_interview(app_id):
    interview_date = request.form.get('interview_date')
    mode = request.form.get('mode')
    interviewer = request.form.get('interviewer')
    execute_query("INSERT INTO Interview (app_id, interview_date, interview_mode, interviewer_name) VALUES (%s,%s,%s,%s)", (app_id, interview_date, mode, interviewer))
    # Optionally update status to Shortlisted
    execute_query("UPDATE Application SET status='Shortlisted' WHERE app_id=%s", (app_id,))
    flash("Interview scheduled.", "success")
    return redirect(request.referrer or url_for('recruiter_dashboard'))

# Give feedback
@app.route('/recruiter/interview/<int:interview_id>/feedback', methods=['POST'])
def recruiter_give_feedback(interview_id):
    rating = int(request.form.get('rating'))
    comments = request.form.get('comments')
    execute_query("INSERT INTO Feedback (interview_id, rating, comments, feedback_date) VALUES (%s,%s,%s,%s)", (interview_id, rating, comments, date.today()))
    flash("Feedback submitted.", "success")
    return redirect(request.referrer or url_for('recruiter_dashboard'))


# ------------------------ DATABASE CONNECTION ------------------------

def get_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="#Ks_31102006",  # change this
            database="job_recruitment_portal"
        )
        return connection
    except Error as e:
        print("❌ Error while connecting to MySQL:", e)
        return None


# ------------------------ GENERIC EXECUTION HELPERS ------------------------

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


# ------------------------ CRUD OPERATIONS ------------------------

# ---- Candidate ----
def add_candidate(name, email, phone, resume_link, experience_years):
    query = """
        INSERT INTO Candidate (name, email, phone, resume_link, experience_years)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (name, email, phone, resume_link, experience_years))


def view_candidates():
    query = "SELECT * FROM Candidate"
    return fetch_all(query)


def update_candidate(candidate_id, phone=None, resume_link=None, experience_years=None):
    query = """
        UPDATE Candidate
        SET phone = COALESCE(%s, phone),
            resume_link = COALESCE(%s, resume_link),
            experience_years = COALESCE(%s, experience_years)
        WHERE candidate_id = %s
    """
    execute_query(query, (phone, resume_link, experience_years, candidate_id))


def delete_candidate(candidate_id):
    query = "DELETE FROM Candidate WHERE candidate_id = %s"
    execute_query(query, (candidate_id,))


# ---- Recruiter ----
def add_recruiter(company_name, recruiter_name, email, password):
    query = """
        INSERT INTO Recruiter (company_name, recruiter_name, email, password)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(query, (company_name, recruiter_name, email, password))


def view_recruiters():
    return fetch_all("SELECT * FROM Recruiter")


# ---- Job Posts ----
def add_job_post(recruiter_id, title, description, location, salary):
    query = """
        INSERT INTO Job_Post (recruiter_id, title, description, location, salary, post_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    execute_query(query, (recruiter_id, title, description, location, salary, date.today()))


def view_jobs():
    return fetch_all("SELECT * FROM Job_Post")


def delete_job(job_id):
    execute_query("DELETE FROM Job_Post WHERE job_id = %s", (job_id,))


# ---- Application ----
def apply_job(candidate_id, job_id):
    query = """
        INSERT INTO Application (candidate_id, job_id, status, applied_date)
        VALUES (%s, %s, 'Applied', %s)
    """
    execute_query(query, (candidate_id, job_id, date.today()))


def view_applications():
    query = """
        SELECT a.app_id, c.name AS candidate_name, j.title AS job_title, a.status, a.applied_date
        FROM Application a
        JOIN Candidate c ON a.candidate_id = c.candidate_id
        JOIN Job_Post j ON a.job_id = j.job_id
    """
    return fetch_all(query)


def update_application_status(app_id, status):
    query = "UPDATE Application SET status = %s WHERE app_id = %s"
    execute_query(query, (status, app_id))


# ---- Interview ----
def schedule_interview(app_id, interview_date, mode, interviewer):
    query = """
        INSERT INTO Interview (app_id, interview_date, interview_mode, interviewer_name)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(query, (app_id, interview_date, mode, interviewer))


def view_interviews():
    query = """
        SELECT i.interview_id, a.app_id, c.name AS candidate, j.title AS job, 
               i.interview_date, i.interview_mode, i.interviewer_name
        FROM Interview i
        JOIN Application a ON i.app_id = a.app_id
        JOIN Candidate c ON a.candidate_id = c.candidate_id
        JOIN Job_Post j ON a.job_id = j.job_id
    """
    return fetch_all(query)


# ---- Feedback ----
def add_feedback(interview_id, rating, comments):
    query = """
        INSERT INTO Feedback (interview_id, rating, comments, feedback_date)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(query, (interview_id, rating, comments, date.today()))


def view_feedback():
    query = """
        SELECT f.feedback_id, i.interview_id, c.name AS candidate, j.title AS job, 
               f.rating, f.comments, f.feedback_date
        FROM Feedback f
        JOIN Interview i ON f.interview_id = i.interview_id
        JOIN Application a ON i.app_id = a.app_id
        JOIN Candidate c ON a.candidate_id = c.candidate_id
        JOIN Job_Post j ON a.job_id = j.job_id
    """
    return fetch_all(query)


# ------------------------ SAMPLE USAGE ------------------------
if __name__ == "__main__":
    print("💼 Job Portal Backend Test\n")

    print("All Candidates:")
    for c in view_candidates():
        print(c)

    print("\nAll Jobs:")
    for j in view_jobs():
        print(j)

    print("\nAll Feedback:")
    for f in view_feedback():
        print(f)
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# ------------------ LOGIN & SIGNUP ROUTES ------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup_candidate', methods=['POST'])
def signup_candidate():
    data = request.form
    name = data['name']
    email = data['email']
    phone = data['phone']
    resume = data['resume']
    exp = data['experience']
    password = data['password']  # for simplicity stored with candidate table extension

    # check if already exists
    existing = fetch_all("SELECT * FROM Candidate WHERE email=%s", (email,))
    if existing:
        return "Candidate already exists! Try login."

    add_candidate(name, email, phone, resume, int(exp))
    return "✅ Candidate registered successfully!"

@app.route('/login_candidate', methods=['POST'])
def login_candidate():
    email = request.form['email']
    password = request.form['password']  # (you can ignore password if not in table)
    candidate = fetch_all("SELECT * FROM Candidate WHERE email=%s", (email,))
    if candidate:
        return render_template('candidate_home.html', user=candidate[0])
    else:
        return "❌ Candidate not found! Please sign up first."

# --- Recruiter login/signup ---
@app.route('/signup_recruiter', methods=['POST'])
def signup_recruiter():
    data = request.form
    company = data['company_name']
    name = data['recruiter_name']
    email = data['email']
    password = data['password']

    existing = fetch_all("SELECT * FROM Recruiter WHERE email=%s", (email,))
    if existing:
        return "Recruiter already exists! Try login."

    add_recruiter(company, name, email, password)
    return "✅ Recruiter registered successfully!"

@app.route('/login_recruiter', methods=['POST'])
def login_recruiter():
    email = request.form['email']
    password = request.form['password']

    recruiter = fetch_all("SELECT * FROM Recruiter WHERE email=%s AND password=%s", (email, password))
    if recruiter:
        return render_template('recruiter_home.html', user=recruiter[0])
    else:
        return "❌ Invalid login credentials!"


if __name__ == '__main__':
    app.run(debug=True)
