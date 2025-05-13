from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

    def __repr__(self):
        return f'<User {self.username}>'


class FilmProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    script_filename = db.Column(db.String(200))
    poster_filename = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    owner = db.relationship('User', backref=db.backref('projects', lazy=True))

    def __repr__(self):
        return f'<FilmProject {self.title}>'

class CrewMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('film_project.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    call_time = db.Column(db.DateTime, nullable=False)

    project = db.relationship('FilmProject', backref=db.backref('crew_members', lazy=True))

    def __repr__(self):
        return f'<CrewMember {self.name} - {self.role}>'
