import os
from flask import Flask
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_babel import Babel, lazy_gettext
from flask_wtf.csrf import CsrfProtect
from flask_debugtoolbar import DebugToolbarExtension
from config import basedir
import datetime
from babel.dates import format_datetime
from flask_assets import Bundle, Environment

import urllib.parse

class AnonUser():
	def is_authenticated(self):
		return False
	def is_active(self):
		return False
	def is_admin(self):
		return False
	def is_mod(self):
		return False
	def is_anonymous(self):
		return True
	def get_id(self):
		return None



app = Flask(__name__, static_folder='static', static_url_path='/static')

import sys
if "debug" in sys.argv:
	print("Flask running in debug mode!")
	app.debug = True
app.config.from_object('config.BaseConfig')
app.jinja_env.add_extension('jinja2.ext.do')
db = SQLAlchemy(app)
lm = LoginManager()
lm.anonymous_user = AnonUser
lm.init_app(app)
lm.login_view = 'login'
lm.login_message = 'Please log in to access this page.'
mail = Mail(app)
babel = Babel(app)
csrf = CsrfProtect(app)

if "debug" in sys.argv:
	print("Installing debug toolbar!")
	toolbar = DebugToolbarExtension(app)

if not app.debug:
	import logging
	from logging.handlers import RotatingFileHandler
	file_handler = RotatingFileHandler('tmp/tob2.log', 'a', 1 * 1024 * 1024, 10)
	file_handler.setLevel(logging.INFO)
	file_handler.setFormatter(logging.Formatter(
		'%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
	app.logger.addHandler(file_handler)
	app.logger.setLevel(logging.INFO)
	app.logger.info('tob2 startup')




from app import views
from app import models
from app import tag_definitions
# from .models import Users, Translators

CACHE_SIZE = 5000
userIdCache = {}
tlGroupIdCache = {}

@app.context_processor
def utility_processor():
	def getUserId(idNo):
		if idNo in userIdCache:
			return userIdCache[idNo]
		user = Users.query.filter_by(id=idNo).one()
		userIdCache[user.id] = user.nickname

		# Truncate the cache if it's getting too large
		if len(userIdCache) > CACHE_SIZE:
			userIdCache.popitem()

		return userIdCache[user.id]

	def getTlGroupId(idNo):
		if idNo in tlGroupIdCache:
			return tlGroupIdCache[idNo]
		group = Translators.query.filter_by(id=idNo).one()
		tlGroupIdCache[group.id] = group.name

		# Truncate the cache if it's getting too large
		if len(tlGroupIdCache) > CACHE_SIZE:
			tlGroupIdCache.popitem()

		return tlGroupIdCache[group.id]


	def format_date(value, format='medium'):
		return format_datetime(value, "EE yyyy.MM.dd")

	def get_tag_list():
		ret = []
		for key, tag_tup in tag_definitions.TAGS.items():
			tag_cat, tag_dict = tag_tup
			tmp = []
			for subkey, definition_tup in tag_dict.items():
				tmp.append((key, subkey, definition_tup[0]))
			tmp.sort()
			ret.append((tag_cat, tmp))
		ret.sort(key=lambda x: (len(x[1]), x[0]))
		return ret

	def get_tag_definition(tagstr):
		taglut = {}
		for key, tag_tup in tag_definitions.TAGS.items():
			tag_cat, tag_dict = tag_tup
			for subkey, definition_tup in tag_dict.items():
				if key+'-'+subkey == tagstr:
					return '%s - %s' % (tag_cat, definition_tup[0])

		return "Unknown tag: '%s'" % tagstr


	def date_now():
		return format_datetime(datetime.datetime.today(), "yyyy/MM/dd, hh:mm:ss")

	def ago(then):
		now = datetime.datetime.now()
		delta = now - then

		d = delta.days
		h, s = divmod(delta.seconds, 3600)
		m, s = divmod(s, 60)
		labels = ['d', 'h', 'm', 's']
		dhms = ['%s %s' % (i, lbl) for i, lbl in zip([d, h, m, s], labels)]
		for start in range(len(dhms)):
			if not dhms[start].startswith('0'):
				break
		for end in range(len(dhms)-1, -1, -1):
			if not dhms[end].startswith('0'):
				break
		return ', '.join(dhms[start:end+1])

	def terse_ago(then):
		now = datetime.datetime.now()
		delta = now - then

		d = delta.days
		h, s = divmod(delta.seconds, 3600)
		m, s = divmod(s, 60)
		labels = ['d', 'h', 'm', 's']
		dhms = ['%s %s' % (i, lbl) for i, lbl in zip([d, h, m, s], labels)]
		for start in range(len(dhms)):
			if not dhms[start].startswith('0'):
				break
		# for end in range(len(dhms)-1, -1, -1):
		# 	if not dhms[end].startswith('0'):
		# 		break
		if d > 0:
			dhms = dhms[:2]
		elif h > 0:
			dhms = dhms[1:3]
		else:
			dhms = dhms[2:]
		return ', '.join(dhms)

	def staleness_factor(then):
		if not then:
			return ""
		now = datetime.datetime.now()
		delta = now - then
		if delta.days <= 14:
			return "updating-current"
		if delta.days <= 45:
			return "updating-stale"
		if delta.days > 700000:
			return "updating-never"
		return "updating-stalled"

	def build_name_qs(keys, items):
		return build_qs(keys, items, lambda x: x.name)

	def build_qs(keys, items, accessor=lambda x: x):
		if isinstance(keys, str):
			tmp = keys
			keys = [tmp for x in range(len(items))]
		args = list(zip(keys, [accessor(item) for item in items]))
		qs = urllib.parse.urlencode(args)
		return qs







	return dict(
			getUserId          = getUserId,
			getTlGroupId       = getTlGroupId,
			format_date        = format_date,
			date_now           = date_now,
			terse_ago          = terse_ago,
			ago                = ago,
			staleness_factor   = staleness_factor,
			build_query_string = build_qs,
			build_name_qs      = build_name_qs,
			get_tag_definition = get_tag_definition,
			get_tag_list       = get_tag_list
			)



