from flask import render_template
# from guess_language import guess_language
from app import app
from app.models import Tags
from app.models import Genres
from app.models import Author
# from app.models import Illustrators
# from app.models import Translators
# from app.models import Feeds
# from app.models import Publishers
# from app.models import FeedTags

from sqlalchemy import desc
from sqlalchemy.orm import joinedload


def get_author_entries(letter, page):

	if letter:
		series = Author.query                                 \
			.filter(Author.name.like("{}%".format(letter))) \
			.order_by(Author.name)                          \
			.distinct(Author.name)
	else:
		series = Author.query       \
			.order_by(Author.name) \
			.distinct(Author.name)
	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return series_entries

@app.route('/authors/<letter>/<int:page>')
@app.route('/authors/<page>')
@app.route('/authors/<int:page>')
@app.route('/authors/')
def renderAuthorTable(letter=None, page=1):
	return render_template('sequence.html',
						   sequence_item   = get_author_entries(letter, page),
						   page            = page,
						   letter          = letter,
						   path_name       = "authors",
						   name_key        = "name",
						   page_url_prefix = 'author-id',
						   title           = 'Authors',
						   )


def get_artist_entries(letter, page):
	if letter:
		series = Illustrators.query                                 \
			.filter(Illustrators.name.like("{}%".format(letter))) \
			.order_by(Illustrators.name)                          \
			.distinct(Illustrators.name)
	else:
		series = Illustrators.query       \
			.order_by(Illustrators.name)\
			.distinct(Illustrators.name)
	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return series_entries


@app.route('/artists/<letter>/<int:page>')
@app.route('/artists/<page>')
@app.route('/artists/<int:page>')
@app.route('/artists/')
def renderArtistTable(letter=None, page=1):


	return render_template('sequence.html',
						   sequence_item   = get_artist_entries(letter, page),
						   page            = page,
						   letter          = letter,
						   path_name       = "artists",
						   name_key        = "name",
						   page_url_prefix = 'artist-id',
						   title           = 'Artists',

						   )


def get_tag_entries(letter, page):
	if letter:
		series = Tags.query                                 \
			.filter(Tags.tag.like("{}%".format(letter))) \
			.order_by(Tags.tag)                          \
			.distinct(Tags.tag)
	else:
		series = Tags.query       \
			.order_by(Tags.tag)\
			.distinct(Tags.tag)

	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return series_entries

@app.route('/tags/<letter>/<int:page>')
@app.route('/tags/<page>')
@app.route('/tags/<int:page>')
@app.route('/tags/')
def renderTagTable(letter=None, page=1):


	return render_template('sequence.html',
						   sequence_item   = get_tag_entries(letter, page),
						   page            = page,
						   letter          = letter,
						   path_name       = 'tags',
						   name_key        = "tag",
						   page_url_prefix = 'tag-id',
						   title           = 'Tags')


def get_publisher_entries(letter, page):
	if letter:
		series = Publishers.query                                 \
			.filter(Publishers.name.like("{}%".format(letter))) \
			.order_by(Publishers.name)                          \
			.distinct(Publishers.name)
	else:
		series = Publishers.query       \
			.order_by(Publishers.name)\
			.distinct(Publishers.name)
	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return series_entries

@app.route('/publishers/<letter>/<int:page>')
@app.route('/publishers/<page>')
@app.route('/publishers/<int:page>')
@app.route('/publishers/')
def renderPublisherTable(letter=None, page=1):


	return render_template('sequence.html',
						   sequence_item   = get_publisher_entries(letter, page),
						   page            = page,
						   letter          = letter,
						   path_name       = 'publishers',
						   name_key        = "name",
						   page_url_prefix = 'publisher-id',
						   title           = 'Publishers')


def get_genre_entries(letter, page):
	if letter:
		series = Genres.query                                \
			.filter(Genres.genre.like("{}%".format(letter))) \
			.order_by(Genres.genre)                          \
			.distinct(Genres.genre)
	else:
		series = Genres.query       \
			.order_by(Genres.genre) \
			.distinct(Genres.genre)
	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return series_entries

@app.route('/genres/<letter>/<int:page>')
@app.route('/genres/<page>')
@app.route('/genres/<int:page>')
@app.route('/genres/')
def renderGenreTable(letter=None, page=1):


	return render_template('sequence.html',
						   sequence_item   = get_genre_entries(letter, page),
						   page            = page,
						   letter          = letter,
						   path_name       = "genres",
						   name_key        = "genre",
						   page_url_prefix = 'genre-id',
						   title           = 'Genres')

def get_groups_entries(letter, page):
	if letter:
		groups = Translators.query       \
			.filter(Translators.name.like("{}%".format(letter))) \
			.order_by(Translators.name)
	else:
		groups = Translators.query       \
			.order_by(Translators.name)

	groups_entries = groups.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return groups_entries

@app.route('/groups/<letter>/<int:page>')
@app.route('/groups/<page>')
@app.route('/groups/<int:page>')
@app.route('/groups/')
def renderGroupsTable(letter=None, page=1):



	return render_template('groups.html',
						   sequence_item   = get_groups_entries(letter, page),
						   page            = page,
						   add_new         = 'group',
						   add_new_text    = 'Add a Group',
						   )

# def get_artist_entries(letter, page):
# 	return series_entries


@app.route('/feeds/<page>')
@app.route('/feeds/<int:page>')
@app.route('/feeds/')
def renderFeedsTable(page=1):

	feeds = Feeds.query       \
		.order_by(desc(Feeds.published))

	feeds = feeds.options(joinedload('tags'))
	feeds = feeds.options(joinedload('authors'))

	feed_entries = feeds.paginate(page, app.config['SERIES_PER_PAGE'], False)

	return render_template('feeds.html',
						   sequence_item   = feed_entries,
						   page            = page,
						   chunk           = True
						   )

# def get_artist_entries(letter, page):
# 	return series_entries


@app.route('/feeds/tag/<tag>/<page>')
@app.route('/feeds/tag/<tag>/<int:page>')
@app.route('/feeds/tag/<tag>/')
def renderFeedsTagTable(tag, page=1):
	query = Feeds.query                      \
			.join(FeedTags)                  \
			.filter(FeedTags.tag == tag)     \
			.order_by(desc(Feeds.published)) \
			.options(joinedload('tags'))     \
			.options(joinedload('authors'))

	feed_entries = query.paginate(page, app.config['SERIES_PER_PAGE'])

	return render_template('feeds.html',
						   subheader = "Tag = '%s'" % tag,
						   sequence_item   = feed_entries,
						   page            = page,
						   chunk           = True
						   )

# def get_artist_entries(letter, page):
# 	return series_entries

@app.route('/feeds/source/<source>/<page>')
@app.route('/feeds/source/<source>/<int:page>')
@app.route('/feeds/source/<source>/')
def renderFeedsSourceTable(source, page=1):
	feeds = Feeds.query                   \
		.filter(Feeds.srcname == source)  \
		.order_by(desc(Feeds.published))


	feeds = feeds.options(joinedload('tags'))
	feeds = feeds.options(joinedload('authors'))

	feed_entries = feeds.paginate(page, app.config['SERIES_PER_PAGE'])

	return render_template('feeds.html',
						   subheader = "Source = '%s'" % source,
						   sequence_item   = feed_entries,
						   page            = page,
						   chunk           = True
						   )

