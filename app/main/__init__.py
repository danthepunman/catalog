from flask import Blueprint


# initiates this folder as a blueprint
main = Blueprint('main', __name__)

# after the blueprint is created then the view is imported
from . import views, errors
