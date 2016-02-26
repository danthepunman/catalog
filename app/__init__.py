# Imports
from flask import Flask, session as login_session
from flask.ext.login import LoginManager
from flask.ext.session import Session
from flask.ext.moment import Moment
from flask.ext.sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CsrfProtect
import default_config

# Gives the imports local variable names
bootstrap = Bootstrap()
moment = Moment()
db = SQLAlchemy()
csrf = CsrfProtect()
lm = LoginManager()
fs = Session()


# Creates the app
def create_app(config_name):
    app = Flask(__name__)
    # Gets the apps globals from config file
    app.config.from_object(default_config)

    # initiates the different modules
    bootstrap.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    csrf.init_app(app)
    lm.init_app(app)
    fs.init_app(app)

    # Establishes the two blueprints used in this app
    from .main import main as main_blueprint
    from .admin import admin as admin_blueprint
    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    return app

