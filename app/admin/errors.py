from flask import render_template
from . import admin


# when there is an error this routes to the different error pages
@admin.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@admin.app_errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500
