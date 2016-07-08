from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask import g
from flask_babel import gettext
from app import app

from app.models import Tags
from app.models import Author
from app.models import Story
from app.models import Ratings

from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import datetime

from app.forms import ReviewForm


def apply_review(form):
	print("Applying form: ", form)
	return render_template('not-implemented-yet.html')

@app.route('/story-review/<int:story_id>/', methods=('GET', 'POST'))
def rate_story(story_id):

	story = Story.query.filter(Story.id==story_id).scalar()
	if not story:
		flash(gettext('Story not found in database! Wat?'))
		return redirect(url_for('index'))


	form = ReviewForm()
	if form.validate_on_submit():
		print("Post request. Validating")
		# if have_auth:
		if True:
			print("Validation succeeded!")
			return apply_review(form)
		else:
			flash(gettext('You must be logged in to make changes!'))

	return render_template(
		'add-view-reviews.html',
		form=form,
		story=story,
		)


@app.route('/date/')
def stories_by_date():
		return render_template('not-implemented-yet.html')

def get_author(sid):
	author = Author.query.filter(Author.id==sid).first()
	if not author:
		return None, None

	items = Author.query.filter(Author.name==author.name).all()
	ids = []
	for item in items:
		ids.append(item.story)

	series = Story.query.filter(Story.id.in_(ids)).order_by(Story.title)

	return author, series


def get_tag_id(sid, page=1):

	tag = Tags.query.filter(Tags.id==sid).first()

	if tag is None:
		return None, None


	items = Tags.query.filter(Tags.tag==tag.tag).all()
	ids = []
	for item in items:
		ids.append(item.story)

	series = Story.query.filter(Story.id.in_(ids)).order_by(Story.title)
	return tag, series


@app.route('/author-id/<sid>/<int:page>')
@app.route('/author-id/<sid>/')
def renderAuthorId(sid, page=1):
	author, series = get_author(sid)
	# print("Author search result: ", author)

	if author is None:
		flash(gettext('Author not found? This is probably a error!'))
		return redirect(url_for('renderAuthorTable'))

	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)

	return render_template('story-list.html',
						   sequence_item   = series_entries,
						   page            = page,
						   name_key        = "title",
						   page_url_prefix = 'series-id',
						   major_title     = 'Stories by \'{}\''.format(author.name),
						   searchValue     = author.name,
						   letter          = None
						   # wiki            = wiki_views.render_wiki("Author", author.name)
						   )


@app.route('/tag-id/<sid>/<int:page>')
@app.route('/tag-id/<sid>/')
def renderTagId(sid, page=1):

	tag, series = get_tag_id(sid)

	if tag is None:
		flash(gettext('Tag not found? This is probably a error!'))
		return redirect(url_for('renderTagTable'))

	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return render_template('story-list.html',
						   sequence_item   = series_entries,
						   page            = page,
						   name_key        = "title",
						   page_url_prefix = 'series-id',
						   searchTarget    = 'Tags',
						   searchValue     = tag.tag.split("-")[-1],
						   major_title     = 'Stories with tag \'{}\''.format(tag.tag),
						   letter          = None
						   # wiki            = wiki_views.render_wiki("Tag", tag.tag)
						   )
