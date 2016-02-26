from flask import Blueprint


# initiates this folder as a blueprint
admin = Blueprint('admin', __name__)

# after the blueprint is created then the view is imported
from . import views, errors, forms, Items_Backup


