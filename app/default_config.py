import os
__author__ = 'Daniel'

# Establish path to where the app is in the os storage
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
# Database and migration path
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'catalog.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
# Set to false so when the app is started you don't get a nuisance flag
SQLALCHEMY_TRACK_MODIFICATIONS = False
# For the type of  storage for the log in variables
SESSION_TYPE = 'sqlalchemy'
# Apps secret key
SECRET_KEY = "the_ONE_and_ONLY_ONE"

# The admins email must be changed to the one used with google sign-in
CATALOG_ADMIN = 'admin@admin.com'
# The id and key for using Amazon Api
AWSACCESSKEYID = 'need_key'
AWSSECRETKEY = 'need_key'


# # For the implementation of the oath api, flow from secrets was used instead
# # Google sign in
# GOOGLE_LOGIN_CLIENT_ID = 'need_key'
# GOOGLE_LOGIN_CLIENT_SECRET = 'need_key'
#
#
# OAUTH_CREDENTIALS = {
#     'google': {
#         'id': GOOGLE_LOGIN_CLIENT_ID,
#         'secret': GOOGLE_LOGIN_CLIENT_SECRET
#     },
#     'amazon': {
#         'id': AMAZON_CLIENT_ID,
#         'secret': AMAZON_CLIENT_SECRET
#     }
# }
