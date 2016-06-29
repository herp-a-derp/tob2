

from settings import DATABASE_IP            as C_DATABASE_IP
from settings import DATABASE_DB_NAME       as C_DATABASE_DB_NAME
from settings import DATABASE_USER          as C_DATABASE_USER
from settings import DATABASE_PASS          as C_DATABASE_PASS
from settings import SECRET_KEY             as C_SECRET_KEY
from settings import WTF_CSRF_SECRET_KEY    as C_WTF_CSRF_SECRET_KEY
from settings import SECURITY_PASSWORD_SALT as C_SECURITY_PASSWORD_SALT
from settings import COVER_PATH             as C_COVER_PATH

import os
import sys
if len(sys.argv) > 1 and "debug" in sys.argv:
	SQLALCHEMY_ECHO = True


basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig(object):

	SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{passwd}@{host}:5432/{database}'.format(user=C_DATABASE_USER, passwd=C_DATABASE_PASS, host=C_DATABASE_IP, database=C_DATABASE_DB_NAME)
	SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

	CSRF_ENABLED = True
	WTF_CSRF_ENABLED = True

	COVER_DIR_BASE = os.path.abspath(os.path.join(basedir, C_COVER_PATH))


	# administrator list
	ADMINS = ['you@example.com']

	# slow database query threshold (in seconds)
	DATABASE_QUERY_TIMEOUT = 0.5

	SEND_FILE_MAX_AGE_DEFAULT = 60*60*12

	# pagination
	TAGS_PER_PAGE = 50
	GENRES_PER_PAGE = 50
	SERIES_PER_PAGE = 50

	POSTS_PER_PAGE = 50
	MAX_SEARCH_RESULTS = 50

	DATABASE_IP            = C_DATABASE_IP
	DATABASE_DB_NAME       = C_DATABASE_DB_NAME
	DATABASE_USER          = C_DATABASE_USER
	DATABASE_PASS          = C_DATABASE_PASS
	SECRET_KEY             = C_SECRET_KEY
	WTF_CSRF_SECRET_KEY    = C_WTF_CSRF_SECRET_KEY

	SECURITY_PASSWORD_SALT = C_SECURITY_PASSWORD_SALT

	# mail settings
	MAIL_SERVER = 'smtp.googlemail.com'
	MAIL_PORT = 465
	MAIL_USE_TLS = False
	MAIL_USE_SSL = True


	ADMIN_USERID  = 2
	SYSTEM_USERID = 1


	# flask-assets
	# ------------
	ASSETS_DEST = 'app/static'


	SQLALCHEMY_TRACK_MODIFICATIONS = False
