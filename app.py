from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from models import db, User, FilmProject, CrewMember  # Make sure these are correctly defined
from flask import send_from_directory

# -------------------------
# Configuration
# -------------------------
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Use environment variables in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./projects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folders
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'scripts')
app.config['POSTER_FOLDER'] = os.path.join(BASE_DIR, 'posters')
app.config['POSTER_FOLDER'] = os.path.join(app.root_path, 'static', 'posters')


# Allowed file extensions
ALLOWED_SCRIPT_EXTENSIONS = {'txt', 'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# Create folders if they don’t exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['POSTER_FOLDER'], exist_ok=True)

# -------------------------
# Initialize DB & Services
# -------------------------
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------------
# User Loader
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# Helpers
# -------------------------
def allowed_file(filename, filetype='script'):
    ext = filename.rsplit('.', 1)[1].lower()
    if filetype == 'script':
        return '.' in filename and ext in ALLOWED_SCRIPT_EXTENSIONS
    elif filetype == 'poster':
        return '.' in filename and ext in ALLOWED_IMAGE_EXTENSIONS
    return False

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
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'home'))
        flash("Invalid username or password", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

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

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('home'))
    total_projects = FilmProject.query.count()
    total_active_projects = FilmProject.query.filter_by(status='Active').count()
    total_archived_projects = FilmProject.query.filter_by(status='Archived').count()
    total_users = User.query.count()
    recent_projects = FilmProject.query.order_by(FilmProject.id.desc()).limit(5).all()
    return render_template('admin_dashboard.html', **locals())

@app.route('/add_project', methods=['POST'])
@login_required
def add_project():
    title = request.form['title']
    genre = request.form['genre']
    status = request.form['status']
    script = request.files.get('script')
    poster = request.files.get('poster')

    script_filename = None
    poster_filename = None

    if script and allowed_file(script.filename, 'script'):
        script_filename = secure_filename(script.filename)
        script.save(os.path.join(app.config['UPLOAD_FOLDER'], script_filename))

    if poster and allowed_file(poster.filename, 'poster'):
        poster_filename = secure_filename(poster.filename)
        poster.save(os.path.join(app.config['POSTER_FOLDER'], poster_filename))

    new_project = FilmProject(
        title=title,
        genre=genre,
        status=status,
        script_filename=script_filename,
        poster_filename=poster_filename,
        owner_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()
    flash("Project added successfully.", "success")
    return redirect(url_for('home'))

@app.route('/upload_poster/<int:project_id>', methods=['POST'])
@login_required
def upload_poster(project_id):
    project = FilmProject.query.get_or_404(project_id)

    if 'poster' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('project_detail', project_id=project_id))

    poster = request.files['poster']
    if poster.filename == '':
        flash('No selected file', 'warning')
        return redirect(url_for('project_detail', project_id=project_id))

    if poster:
        filename = secure_filename(poster.filename)
        poster_path = os.path.join(app.config['POSTER_FOLDER'], filename)
        poster.save(poster_path)
        project.poster_filename = filename
        db.session.commit()
        flash('Poster uploaded successfully!', 'success')

    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/delete_poster/<int:project_id>', methods=['POST'])
@login_required
def delete_poster(project_id):
    project = FilmProject.query.get_or_404(project_id)

    # Remove the poster file from the server
    if project.poster_filename:
        try:
            poster_path = os.path.join(app.config['POSTER_FOLDER'], project.poster_filename)
            os.remove(poster_path)
            flash('Poster deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting poster: {str(e)}', 'danger')

        # Remove the poster filename from the database
        project.poster_filename = None
        db.session.commit()

    return redirect(url_for('project_detail', project_id=project.id))


@app.route('/project/<project_id>/poster/<filename>')
def view_poster(project_id, filename):
    return send_from_directory('static/posters', filename)

@app.route('/download/poster/<filename>')
def download_poster(filename):
    return send_from_directory('static/posters', filename)

@app.route('/project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def project_detail(project_id):
    project = FilmProject.query.get_or_404(project_id)
    crew_members = CrewMember.query.filter_by(project_id=project_id).all()

    if request.method == 'POST' and 'poster' in request.files:
        poster_file = request.files['poster']
        if poster_file.filename:
            filename = secure_filename(poster_file.filename)
            poster_path = os.path.join('static', 'posters', filename)
            poster_file.save(poster_path)
            project.poster_filename = filename
            db.session.commit()

    poster_url = (
        url_for('static', filename='posters/' + project.poster_filename)
        if project.poster_filename
        else None
    )
    return render_template(
        'project_detail.html',
        project=project,
        crew_members=crew_members,
        poster_url=poster_url
    )

@app.route('/scripts/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
from flask import send_from_directory

@app.route('/posters/<filename>')
def serve_poster(filename):
    return send_from_directory(app.config['POSTER_FOLDER'], filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/add_crew', methods=['POST'])
@login_required
def add_crew():
    try:
        name = request.form['name']
        role = request.form['role']
        call_time = datetime.strptime(request.form['call_time'], "%Y-%m-%dT%H:%M")
        project_id = int(request.form['project_id'])
        new_crew = CrewMember(name=name, role=role, call_time=call_time, project_id=project_id)
        db.session.add(new_crew)
        db.session.commit()
        flash("Crew member added successfully.", "success")
        return redirect(url_for('project_detail', project_id=project_id))
    except Exception as e:
        flash("Invalid crew data submitted.", "danger")
        return redirect(url_for('home'))

@app.route('/delete_crew', methods=['POST'])
@login_required
def delete_crew():
    identifier = request.form.get('user_identifier', '').strip()
    crew_member = CrewMember.query.filter_by(name=identifier).first()

    if not crew_member:
        flash("Crew member not found.", "danger")
        return redirect(url_for('admin_dashboard'))

    project = FilmProject.query.get_or_404(crew_member.project_id)
    if current_user.role != 'admin' and project.owner_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('home'))

    db.session.delete(crew_member)
    db.session.commit()
    flash("Crew member deleted successfully.", "success")
    return redirect(url_for('project_detail', project_id=project.id))
@app.route('/search_crew', methods=['GET'])
@login_required
def search_crew():
    query = request.args.get('query', '').strip()

    results = []
    if query:
        results = CrewMember.query.filter(
            (CrewMember.username.ilike(f"%{query}%")) | (CrewMember.email.ilike(f"%{query}%"))
        ).all()

    return render_template('search_results.html', results=results, query=query)


@app.route('/view_users')
@login_required
def view_users():
    if current_user.role != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('home'))
    users = User.query.all()
    return render_template('view_users.html', users=users)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required  # Assuming you're using Flask-Login to protect the route
# Assuming you have a CrewMember model and Project model
def delete_project(project_id):
    # New project ID to associate the crew members with (optional)
    new_project_id = 2  # Replace with your desired project ID

    # Update the crew members associated with the project
    CrewMember.query.filter_by(project_id=project_id).update({"project_id": new_project_id})

    # Commit the changes to the database
    db.session.commit()

    # Delete the project (if you're deleting it afterward)
    project = FilmProject.query.get(project_id)
    db.session.delete(project)
    db.session.commit()

    return redirect(url_for("index"))
@app.route('/toggle_dark_mode')
def toggle_dark_mode():
    session['dark_mode'] = not session.get('dark_mode', False)
    return redirect(request.referrer or url_for('home'))
@app.route("/")
@login_required
def index():
    return render_template("index.html")  # Or whatever your homepage template is

# -------------------------
# Initialize DB
# -------------------------
with app.app_context():
    db.create_all

# -------------------------
# Run App
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
