from flask import render_template
# from guess_language import guess_language
from app import app
from app.models import Story
from app.models import Ratings

from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from sqlalchemy import func




def get_highest_rated(page):

	ratings = Ratings.query \
		.with_entities(func.count().label("rating_count"), func.avg(Ratings.rating).label("rating"), func.min(Ratings.series_id).label("series_id")) \
		.group_by(Ratings.series_id).subquery()


	have = Story.query.join(ratings, Story.id == ratings.c.series_id) \
		.add_column(ratings.c.rating) \
		.add_column(ratings.c.rating_count) \
		.filter(ratings.c.rating_count > 1) \
		.order_by(desc(ratings.c.rating), Story.title)


	watch_entries = have.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return watch_entries



def get_most_rated(page):

	ratings = Ratings.query \
		.with_entities(func.count().label("rating_count"), func.avg(Ratings.rating).label("rating"), func.min(Ratings.series_id).label("series_id")) \
		.group_by(Ratings.series_id).subquery()


	have = Story.query.join(ratings, Story.id == ratings.c.series_id) \
		.add_column(ratings.c.rating) \
		.add_column(ratings.c.rating_count) \
		.filter(ratings.c.rating_count > 1) \
		.order_by(desc(ratings.c.rating_count), Story.title)


	watch_entries = have.paginate(page, app.config['SERIES_PER_PAGE'], False)
	return watch_entries








@app.route('/most-rated/<page>')
@app.route('/most-rated/<int:page>')
@app.route('/most-rated/')
def renderMostRated(page=1):
	return render_template('popular.html',
						   sequence_item   = get_most_rated(page),
						   page_mode       = "ratings",
						   page            = page,
						   title           = 'Most Watched Stories',
						   footnote        = None,
						   )



@app.route('/highest-rated/<page>')
@app.route('/highest-rated/<int:page>')
@app.route('/highest-rated/')
def renderHighestRated(page=1):

	return render_template('popular.html',
						   sequence_item   = get_highest_rated(page),
						   page_mode       = "ratings",
						   page            = page,
						   title           = 'Highest Rated Stories',
						   footnote        = 'Stories only rated by one person are excluded from this list.',
						   )

