import os

# only UPPERCASE_NAMES are considered as configuration keys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(BASE_DIR, 'db_repository')

CRSF_ENABLED = True
SECRET_KEY = 'change_this_later_please'
