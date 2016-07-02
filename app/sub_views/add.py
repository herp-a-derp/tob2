from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask import g
from flask_babel import gettext
from werkzeug.urls import url_fix
# from guess_language import guess_language
from app import db
import datetime
import bleach
import markdown
from sqlalchemy import and_
from app.forms import PostForm
from app import app
import datetime




def add_release(form):
	print("Add_release call")
	chp = int(form.data['chapter'])   if form.data['chapter']   and int(form.data['chapter'])   >= 0 else None
	vol = int(form.data['volume'])    if form.data['volume']    and int(form.data['volume'])    >= 0 else None
	sid = int(form.data['series_id']) if form.data['series_id'] and int(form.data['series_id']) >= 0 else None
	sub = int(form.data['subChap'])   if form.data['subChap']   and int(form.data['subChap'])   >= 0 else None
	group = int(form.data['group'])

	itemurl = url_fix(form.data['release_pg'])

	oel = False
	if form.data['is_oel'] == 'oel':
		oel = True
		group = None

	pubdate = form.data['releasetime']
	postfix = bleach.clean(form.data['postfix'], strip=True)

	# Limit publication dates to now to prevent post-dating.
	if pubdate > datetime.datetime.now():
		pubdate = datetime.datetime.now()

	# Sub-chapters are packed into the chapter value.
	# I /may/ change this

	assert form.data['is_oel'] in ['oel', 'translated']

	flt = [(Releases.series == sid), (Releases.srcurl == itemurl)]
	if sub:
		flt.append((Releases.fragment == sub))
	if chp:
		flt.append((Releases.chapter == chp))
	if vol:
		flt.append((Releases.chapter == vol))

	if not any((vol, chp, postfix)):
		flash(gettext('Releases without content in any of the chapter, volume or postfix are not valid.'))
		return redirect(url_for('renderSeriesId', sid=sid))

	have = Releases.query.filter(and_(*flt)).all()

	if have:
		flash(gettext('That release appears to already have been added.'))
		return redirect(url_for('renderSeriesId', sid=sid))

	series = Series.query.filter(Series.id==sid).scalar()
	if not series:
		flash(gettext('Invalid series-id in add call? Are you trying something naughty?'))
		return redirect(url_for('index'))

	group = Translators.query.filter(Translators.id==group).scalar()
	if oel:
		groupid = None
	elif group:
		groupid = group.id
	else:
		flash(gettext('Invalid group-id in add call? Are you trying something naughty?'))
		return redirect(url_for('index'))

	# Everything has validated, add the new item.
	new = Releases(
		tlgroup   = groupid,
		series    = series.id,
		published = pubdate,
		volume    = vol,
		chapter   = chp,
		fragment  = sub,
		postfix   = postfix,
		srcurl    = itemurl,
		changetime = datetime.datetime.now(),
		changeuser = g.user.id,
		include    = True,
		)
	db.session.add(new)
	db.session.commit()
	flash(gettext('New release added. Thanks for contributing!'))
	flash(gettext('If the release you\'re adding has a RSS feed, you can ask for it to be added to the automatic feed system on the forum!'))
	return redirect(url_for('renderSeriesId', sid=sid))

def add_story(form):
	flash(gettext('New post added.'))
	return redirect(url_for('renderNews'))
	pass

def add_post(form):
	title   = bleach.clean(form.data['title'], tags=[], strip=True)
	content = markdown.markdown(bleach.clean(form.data['content'], strip=True))
	new = News_Posts(
			title     = title,
			body      = content,
			timestamp = datetime.datetime.now(),
			user_id   = g.user.id,
		)
	db.session.add(new)
	db.session.commit()
	flash(gettext('New post added.'))
	return redirect(url_for('renderReleasesTable'))


def preset(cls):
	return lambda : cls(NewReleaseForm=datetime.datetime.now())

dispatch = {
# 	'group'   : (NewGroupForm,   add_group,   ''),
# 	'release' : (NewReleaseForm, add_release, ''),
	'story'   : (None,           None,        ''),
	'post'    : (PostForm,       add_post,    ''),
}


@app.route('/add/<add_type>/<int:sid>/', methods=('GET', 'POST'))
@app.route('/add/<add_type>/', methods=('GET', 'POST'))
def addNewItem(add_type, sid=None):

	if not add_type in dispatch:
		flash(gettext('Unknown type of content to add!'))
		return redirect(url_for('index'))
	if add_type == 'release' and sid == None:
		flash(gettext('Adding a release must involve a series-id. How did you even do that?'))
		return redirect(url_for('index'))

	form_class, callee, message = dispatch[add_type]
	have_auth = g.user.is_authenticated()

	if form_class:
		form = form_class()
		if form.validate_on_submit():
			print("Post request. Validating")
			if have_auth:
				print("Validation succeeded!")
				return callee(form)
			else:
				flash(gettext('You must be logged in to make changes!'))

		if add_type == 'post':
			return render_template(
					'add-post.html',
					form=form,
					)

	print("Trying to validate")
	# print(form.validate_on_submit())

	# else:
	# 	if not have_auth:
	# 		flash(gettext('You do not appear to be logged in. Any changes you make will not be saved!'))



	if add_type == 'story':
		return render_template(
				'add-story.html',
				add_name = add_type,
				)
