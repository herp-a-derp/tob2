from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask import request
from flask import g
from flask import send_file
from flask_login import login_user
from flask_login import logout_user
from flask_login import current_user
from flask_login import login_required
from itsdangerous import URLSafeTimedSerializer
from itsdangerous import BadSignature
from flask_sqlalchemy import get_debug_queries
from flask_babel import gettext
from datetime import datetime

import sqlalchemy.exc
# from guess_language import guess_language
from app import app
from app import db
from app import lm
from app import babel
# from .forms import LoginForm
from .forms import SearchForm
# from .forms import SignupForm
from .models import Users
from .models import News_Posts
from .models import Story
from .models import HttpRequestLog




import os.path
from sqlalchemy.sql.expression import func
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

# These imports /look/ unused, but they cause the installation
# of most of the site routes.
from .sub_views import item_views
from .sub_views import stub_views
from .sub_views import admin_views
from .sub_views import add
from .sub_views import sequence_views
from .sub_views import release_views
from .sub_views import news_view
from .sub_views import popular_views
from .sub_views.search import execute_search

from .apiview import handleApiPost
from .apiview import handleApiGet


import traceback

@lm.user_loader
def load_user(id):
	return Users.query.get(int(id))


@babel.localeselector
def get_locale():
	return 'en'


@app.before_request
def before_request():
	req = HttpRequestLog(
		path           = request.path,
		user_agent     = request.headers.get('User-Agent'),
		referer        = request.headers.get('Referer'),
		forwarded_for  = request.headers.get('X-Originating-IP'),
		originating_ip = request.headers.get('X-Forwarded-For'),
		)
	db.session.add(req)

	g.user = current_user
	g.search_form = SearchForm()
	if g.user.is_authenticated():
		g.user.last_seen = datetime.utcnow()
		db.session.add(g.user)

	db.session.commit()
	g.locale = get_locale()



@app.after_request
def after_request(response):
	for query in get_debug_queries():
		if query.duration >= app.config['DATABASE_QUERY_TIMEOUT']:
			app.logger.warning(
				"SLOW QUERY: %s\nParameters: %s\nDuration: %fs\nContext: %s\n" %
				(query.statement, query.parameters, query.duration,
				 query.context))
	return response


@app.errorhandler(404)
def not_found_error(dummy_error):
	print("404. Wat?")
	return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(dummy_error):
	db.session.rollback()
	print("Internal Error!")
	print(dummy_error)
	print(traceback.format_exc())
	# print("500 error!")
	return render_template('500.html'), 500



def get_random_books():
	# items = Story.query.order_by(func.random()).limit(5)
	items = release_views.get_releases(1, per_page=5, order_by=func.random())
	# print("random items", items)
	return items


def get_news():
	# User ID 2 is the admin acct, as created by the db migrator script
	# Probably shouldn't be hardcoded, works for the moment.
	newsPost = News_Posts.query.filter(News_Posts.user_id == 2).order_by(desc(News_Posts.timestamp)).limit(1).scalar()
	return newsPost

def get_release_feeds():
	items = release_views.get_releases(1, per_page=20)

	return items
	# return q.all()


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
# @login_required
def index():
	return render_template('index.html',
						   title          = 'Home',
						   random_stories = get_random_books(),
						   news           = get_news(),
						   recent_stories = get_release_feeds(),
						   name_key       = "title",
						   )


@app.route('/favicon.ico')
def sendFavIcon():
	return send_file(
		"./static/favicon.ico",
		conditional=True
		)



@app.route('/get-story/<int:cid>/')
def renderStoryContent(cid):
	# TODO: Add a "not found" thing
	story = Story.query.filter(Story.id==cid).scalar()
	if not story:
		flash(gettext('Story not found in database! Wat?'))
		return redirect(url_for('index'))

	while 1:
		try:
			if story.downloads is None:
				story.downloads = 0
			story.downloads += 1
			db.session.commit()
			break
		except sqlalchemy.exc.IntegrityError:
			print("Concurrency issue?")
			db.session.rollback()

	covpath = os.path.join(app.config['FILE_BACKEND_PATH'], story.fspath)
	if not os.path.exists(covpath):
		print("Story found, but backing file seems to be missing! '%s'" % covpath)
		flash(gettext('Story found, but backing file seems to be missing! ! PLEASE ! let an admin know!'))
		return redirect(url_for('index'))

	print("Filename: ", story.srcfname)
	return send_file(
		covpath,
		attachment_filename=story.srcfname,
		conditional=True,
		as_attachment=True,
		)

# @app.route('/edit', methods=['GET', 'POST'])
# @login_required
# def edit():
# 	form = EditForm(g.user.nickname)
# 	if form.validate_on_submit():
# 		g.user.nickname = form.nickname.data
# 		g.user.about_me = form.about_me.data
# 		db.session.add(g.user)
# 		db.session.commit()
# 		flash(gettext('Your changes have been saved.'))
# 		return redirect(url_for('edit'))
# 	elif request.method != "POST":
# 		form.nickname.data = g.user.nickname
# 		form.about_me.data = g.user.about_me
# 	return render_template('edit.html', form=form)





#################################################################################################################################
#################################################################################################################################
#################################################################################################################################
#################################################################################################################################

@app.route('/logout', methods=['GET', 'POST'])
def logout():
	logout_user()
	flash(gettext('You have been logged out.'))
	return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
	if g.user is not None and g.user.is_authenticated():
		flash(gettext('You are already logged in.'))
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = Users.query.filter_by(nickname=form.username.data).first()
		if user.verified:
			login_user(user, remember=bool(form.remember_me.data))
			flash(gettext('You have logged in successfully.'))
			return redirect(url_for('index'))
		else:
			flash(gettext('Please confirm your account first.'))
			return redirect(url_for('index'))


	return render_template('login.html',
						   title='Sign In',
						   form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = SignupForm()
	if form.validate_on_submit():
		user = Users(
			nickname  = form.username.data,
			password  = form.password.data,
			email     = form.email.data,
			verified  = 0
		)
		print("User:", user)
		db.session.add(user)
		db.session.commit()
		send_email(form.email.data,
				"Please confirm your account for TOB2.com",
				render_template('mail.html',
								confirm_url=get_activation_link(user))
				)

		print("Sent")

		return render_template('confirm.html')


		# session['remember_me'] = form.remember_me.data
	return render_template('signup.html',
						   title='Sign In',
						   form=form)



def get_serializer():
	return URLSafeTimedSerializer(app.config['SECRET_KEY'])


def get_activation_link(user):
	s = get_serializer()
	payload = s.dumps(user.id, salt=app.config['SECURITY_PASSWORD_SALT'])
	return url_for('activate_user', payload=payload, _external=True)

@app.route('/users/activate/<payload>')
def activate_user(payload, expiration=60*60*24):
	s = get_serializer()
	try:
		user_id = s.loads(payload, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
		user = Users.query.get(int(user_id))
		if user.verified:
			flash(gettext('Your account has already been activated. Stop that.'))
		else:
			user.verified = 1
			db.session.commit()
			flash(gettext('Your account has been activated. Please log in.'))
		return index(1)

	except BadSignature:
		return render_template('not-implemented-yet.html', message='Invalid activation link.')
