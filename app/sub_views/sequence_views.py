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
						   path_name       = "name",
						   name_key        = "name",
						   page_url_prefix = 'author-id',
						   title           = 'Authors',

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


	return render_template('tag-sequence.html',
						   sequence_item   = get_tag_entries(letter, page),
						   page            = page,
						   letter          = letter,
						   path_name       = 'tags',
						   name_key        = "tag",
						   page_url_prefix = 'tag-id',
						   title           = 'Tags')

# def get_genre_entries(letter, page):
# 	if letter:
# 		series = Genres.query                                \
# 			.filter(Genres.genre.like("{}%".format(letter))) \
# 			.order_by(Genres.genre)                          \
# 			.distinct(Genres.genre)
# 	else:
# 		series = Genres.query       \
# 			.order_by(Genres.genre) \
# 			.distinct(Genres.genre)
# 	series_entries = series.paginate(page, app.config['SERIES_PER_PAGE'], False)
# 	return series_entries

# @app.route('/genres/<letter>/<int:page>')
# @app.route('/genres/<page>')
# @app.route('/genres/<int:page>')
# @app.route('/genres/')
# def renderGenreTable(letter=None, page=1):


# 	return render_template('sequence.html',
# 						   sequence_item   = get_genre_entries(letter, page),
# 						   page            = page,
# 						   letter          = letter,
# 						   path_name       = "genres",
# 						   name_key        = "genre",
# 						   page_url_prefix = 'genre-id',
# 						   title           = 'Genres')
