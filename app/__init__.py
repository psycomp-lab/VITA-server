from flask import Flask
from app.models import db

def create_app():
    app = Flask(__name__,template_folder='../templates',static_folder='../static')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    #secret_key for form validation (csrf_token)
    app.config['SECRET_KEY'] = 'always_a_duck'

    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    app.config['SESSION_PERMANENT'] = False

    db.init_app(app)

    return app

app = create_app()

with app.app_context():
    db.create_all()