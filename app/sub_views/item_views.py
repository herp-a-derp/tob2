from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask import g
from flask_babel import gettext
from app import app

from app.models import Tags
from app.models import Author

from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import datetime


def load_series_data(sid):
	series       =       Series.query

	# Adding these additional joinedload values, while they /should/
	# help, since the relevant content is then loaded during rendering
	# if they're not already loaded, somehow manages to COMPLETELY
	# tank the query performance.
	# series = series.options(joinedload('tags'))
	# series = series.options(joinedload('covers'))

	series = series.options(joinedload('author'))
	series = series.options(joinedload('alternatenames'))
	series = series.options(joinedload('illustrators'))
	series = series.options(joinedload('tags'))
	series = series.options(joinedload('releases.translators'))

	series = series.filter(Series.id==sid)

	series = series.first()

	if g.user.is_authenticated():
		watch      =       Watches.query.filter(Watches.series_id==sid)     \
		                                  .filter(Watches.user_id==g.user.id) \
		                                  .scalar()

		# This is *relatively* optimized, since the query
		# planner is smart enough to apply the filter before the distinct.
		# May become a performance issue if the watches table gets large
		# enough, but I think the performance ceiling will actually
		# be the number of watches a user has, rather then the
		# overall table size.
		watchlists = Watches                                 \
					.query                                   \
					.filter(Watches.user_id == g.user.id)    \
					.distinct(Watches.listname)              \
					.all()
		watchlists = [watchitem.listname for watchitem in watchlists]
		# print(watchlists)
	else:
		watch = False
		watchlists = False



	total_watches =       Watches.query.filter(Watches.series_id==sid).count()

	if series is None:
		return None

	releases = series.releases
	releases.sort(reverse=True, key=getSort)


	latest      = get_latest_release(releases)
	latest_dict = build_progress(latest)
	most_recent = get_most_recent_release(releases)
	latest_str  = format_latest_release(latest)

	if watch:
		progress    = build_progress(watch)
	else:
		progress    = latest_dict

	series.covers.sort(key=get_cover_sorter())

	rating = get_rating(sid)

	if series.tags:
		similar_series = get_similar_by_tags(sid, series.tags)
	else:
		similar_series = []


	return series, releases, watch, watchlists, progress, latest, latest_dict, most_recent, latest_str, rating, total_watches, similar_series

def get_author(sid):
	author = Author.query.filter(Author.id==sid).first()
	if not author:
		return None, None

	items = Author.query.filter(Author.name==author.name).all()
	ids = []
	for item in items:
		ids.append(item.series)

	series = Series.query.filter(Series.id.in_(ids)).order_by(Series.title)

	return author, series


def get_tag_id(sid, page=1):

	tag = Tags.query.filter(Tags.id==sid).first()

	if tag is None:
		return None, None


	items = Tags.query.filter(Tags.tag==tag.tag).all()
	ids = []
	for item in items:
		ids.append(item.series)

	series = Series.query.filter(Series.id.in_(ids)).order_by(Series.title)
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

	return render_template('search_results.html',
						   sequence_item   = series_entries,
						   page            = page,
						   name_key        = "title",
						   page_url_prefix = 'series-id',
						   searchTarget    = 'Authors',
						   searchValue     = author.name,
						   wiki            = wiki_views.render_wiki("Author", author.name)
						   )


@app.route('/tag-id/<sid>/<int:page>')
@app.route('/tag-id/<sid>/')
def renderTagId(sid, page=1):

	tag, series = get_tag_id(sid)

	if tag is None:
		flash(gettext('Tag not found? This is probably a error!'))
		return redirect(url_for('renderTagTable'))

	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return render_template('search_results.html',
						   sequence_item   = series_entries,
						   page            = page,
						   name_key        = "title",
						   page_url_prefix = 'series-id',
						   searchTarget    = 'Tags',
						   searchValue     = tag.tag,
						   wiki            = wiki_views.render_wiki("Tag", tag.tag)
						   )
