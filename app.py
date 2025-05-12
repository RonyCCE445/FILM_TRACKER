from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from models import db, User, FilmProject, CrewMember

# -------------------------
# Configuration
# -------------------------
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this in production

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./projects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'scripts')
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------------
# Initialize DB and other services
# -------------------------
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -------------------------
# User Loader
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# Routes
# -------------------------
@app.route('/')
def home():
    projects = FilmProject.query.all()
    return render_template('index.html', projects=projects)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully.", "success")
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash("Invalid Credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return "Access Denied", 403
    
    total_projects = FilmProject.query.count()
    total_active_projects = FilmProject.query.filter_by(status='Active').count()
    total_archived_projects = FilmProject.query.filter_by(status='Archived').count()
    total_users = User.query.count()
    recent_projects = FilmProject.query.order_by(FilmProject.id.desc()).limit(5).all()

    return render_template('admin_dashboard.html', 
                           total_projects=total_projects, 
                           total_active_projects=total_active_projects,
                           total_archived_projects=total_archived_projects,
                           total_users=total_users,
                           recent_projects=recent_projects)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash("Registered Successfully", "success")
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/add_project', methods=['POST'])
@login_required
def add_project():
    title = request.form['title']
    genre = request.form['genre']
    status = request.form['status']
    script = request.files['script']

    script_filename = None
    if script and allowed_file(script.filename):
        filename = secure_filename(script.filename)
        script.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        script_filename = filename

    new_project = FilmProject(
        title=title,
        genre=genre,
        status=status,
        script_filename=script_filename,
        owner_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()

    flash("Project added successfully.", "success")
    return redirect(url_for('home'))

@app.route('/scripts/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/add_crew', methods=['POST'])
@login_required
def add_crew():
    name = request.form['name']
    role = request.form['role']
    call_time = datetime.strptime(request.form['call_time'], "%Y-%m-%dT%H:%M")
    project_id = request.form['project_id']

    new_crew = CrewMember(
        name=name,
        role=role,
        call_time=call_time,
        project_id=project_id
    )
    db.session.add(new_crew)
    db.session.commit()

    flash("Crew member added successfully.", "success")
    return redirect(url_for('home'))

@app.route('/delete_project', methods=['POST'])
@login_required
def delete_project():
    project_id = request.form['project_id']
    project = FilmProject.query.get_or_404(project_id)

    if project.owner_id != current_user.id and current_user.role != 'admin':
        flash("You do not have permission to delete this project.", "danger")
        return redirect(url_for('home'))

    CrewMember.query.filter_by(project_id=project.id).delete()

    if project.script_filename:
        script_path = os.path.join(app.config['UPLOAD_FOLDER'], project.script_filename)
        if os.path.exists(script_path):
            os.remove(script_path)

    db.session.delete(project)
    db.session.commit()
    flash("Project deleted successfully.", "success")
    return redirect(url_for('home'))

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = FilmProject.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ✅ New route added to fix BuildError
@app.route('/view_users')
@login_required
def view_users():
    if current_user.role != 'admin':
        return "Access Denied", 403

    users = User.query.all()
    return render_template('view_users.html', users=users)

# -------------------------
# Helper Functions
# -------------------------
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# -------------------------
# Initialize DB
# -------------------------
with app.app_context():
    db.create_all()

# -------------------------
# Run App
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
