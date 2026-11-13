from flask import Flask, render_template, request, redirect, session
from sqlalchemy.orm import sessionmaker
from models import User, Report, engine, Base
from ai import analyze_resume_with_ai
import pdfplumber
import docx
import json

app = Flask(__name__)
app.secret_key = "your_secret_key"
Base.metadata.create_all(bind=engine)

# ================= HEADING 1: DB CONNECTION =================
def get_db():
    DBSession = sessionmaker(bind=engine)
    return DBSession()

# ================= HEADING 2: HOME =================
@app.route('/')
def home():
    if "user" in session:
        return redirect('/dashboard')
    return redirect('/login')

# ================= HEADING 3: SIGNUP =================
@app.route('/signup', methods=["GET", "POST"])
def signup():
    db = get_db()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if db.query(User).filter_by(email=email).first():
            db.close()
            return "User already exists. <a href='/login'>Go to login</a>"
        db.add(User(email=email, password=password))
        db.commit()
        db.close()
        session["user"] = email
        return redirect('/dashboard')
    db.close()
    return render_template('signup.html')

# ================= HEADING 4: LOGIN =================
@app.route('/login', methods=["GET", "POST"])
def login():
    db = get_db()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.query(User).filter_by(email=email, password=password).first()
        db.close()
        if user:
            session["user"] = user.email
            return redirect('/dashboard')
        return "Invalid email or password. <a href='/login'>Try again</a>"
    db.close()
    return render_template('login.html')

# ================= HEADING 5: DASHBOARD =================
@app.route('/dashboard', methods=["GET"])
def dashboard():
    if "user" not in session:
        return redirect('/login')
    return render_template('dashboard.html')

# ================= HEADING 6: ANALYZE - MAIN LOGIC =================
@app.route('/analyze', methods=["POST"])
@app.route('/analyse', methods=["POST"])
def analyze():
    if "user" not in session:
        return redirect('/login')
    db = get_db()
    user = db.query(User).filter_by(email=session["user"]).first()
    if not user:
        db.close()
        session.pop("user", None)
        return redirect('/login')

    role = request.form.get("role")
    pasted_text = request.form.get("resume_text", "")
    file = request.files.get("file")
    resume_text = ""

    if pasted_text and pasted_text.strip() != "":
        resume_text = pasted_text
    elif file and file.filename != '':
        try:
            file.seek(0)
            if file.filename.lower().endswith('.pdf'):
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        resume_text += (page.extract_text() or "") + "\n"
            elif file.filename.lower().endswith('.docx'):
                doc = docx.Document(file)
                for para in doc.paragraphs:
                    resume_text += para.text + "\n"
            else:
                db.close()
                return "Only pdf or docx allowed. <a href='/dashboard'>Go back</a>"
        except Exception as e:
            db.close()
            return "Could not read file: " + str(e) + " <br><a href='/dashboard'>Go back</a>"
    else:
        db.close()
        return "Please paste text OR upload file. <a href='/dashboard'>Go back</a>"

    if not resume_text.strip():
        db.close()
        return "Could not extract text from PDF (scanned). Please paste manually. <a href='/dashboard'>Go back</a>"

    try:
        ai_response = analyze_resume_with_ai(resume_text, role)
        ai_response = ai_response.strip().replace("```json", "").replace("```", "")
        parsed_result = json.loads(ai_response)
        
        # Yahan f-string hata kar safe concatenation kiya gaya hai
        if "error" in parsed_result:
            db.close()
            error_msg = parsed_result["error"]
            return "<script>alert('" + error_msg + "'); window.location.href='/dashboard';</script>"

    except Exception as e:
        db.close()
        return "AI Error: " + str(e) + " <br><a href='/dashboard'>Go back</a>"

    report = Report(user_id=user.id, resume_text=resume_text[:5000], role=role, result=json.dumps(parsed_result))
    db.add(report)
    db.commit()
    db.close()
    return render_template('result.html', result=parsed_result, role=role)

# ================= HEADING 7: HISTORY & REPORT & LOGOUT =================
@app.route('/history')
def history():
    if "user" not in session:
        return redirect('/login')
    db = get_db()
    user = db.query(User).filter_by(email=session["user"]).first()
    reports = db.query(Report).filter_by(user_id=user.id).order_by(Report.id.desc()).all()
    db.close()
    return render_template('history.html', reports=reports)

@app.route('/report/<int:report_id>')
def view_report(report_id):
    if "user" not in session:
        return redirect('/login')
    db = get_db()
    user = db.query(User).filter_by(email=session["user"]).first()
    report = db.query(Report).filter_by(id=report_id, user_id=user.id).first()
    db.close()
    if not report:
        return "Report not found! <a href='/history'>Go Back</a>"
    return render_template('result.html', result=json.loads(report.result), role=report.role)

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect('/login')

@app.route('/forgot-password', methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        db = get_db()
        user = db.query(User).filter_by(email=email).first()
        db.close()
        if user:
            return redirect('/reset-password/' + email)
        return render_template('forgot_password.html', error="Email not found!")
    return render_template('forgot_password.html')

@app.route('/reset-password/<email>', methods=["GET", "POST"])
def reset_password(email):
    if request.method == "POST":
        if request.form.get("new_password") != request.form.get("confirm_password"):
            return render_template('reset_password.html', email=email, error="Passwords do not match!")
        db = get_db()
        user = db.query(User).filter_by(email=email).first()
        if user:
            user.password = request.form.get("new_password")
            db.commit()
        db.close()
        return redirect('/login')
    return render_template('reset_password.html', email=email)

# ================= HEADING 8: DELETE REPORT =================
@app.route('/delete/<int:report_id>')
def delete_report(report_id):
    if "user" not in session:
        return redirect('/login')
    db = get_db()
    user = db.query(User).filter_by(email=session["user"]).first()
    # Ensure user owns this report before deleting
    report = db.query(Report).filter_by(id=report_id, user_id=user.id).first()
    if report:
        db.delete(report)
        db.commit()
    db.close()
    return redirect('/history')

if __name__ == "__main__":
    app.run(debug=True, port=5000)