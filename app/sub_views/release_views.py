from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask_babel import gettext
# from guess_language import guess_language
from app import app
# from app.models import Releases
from app.models import Story
from sqlalchemy import desc
from sqlalchemy.orm import joinedload


def get_releases(page, per_page=app.config['SERIES_PER_PAGE'], order_by=desc(Story.pub_date)):
	releases = Story.query
	releases = releases.order_by(order_by)

	# Join on the series entry. Cuts the total page-rendering queries in half.
	releases = releases.options(joinedload('tags'))
	releases = releases.options(joinedload('author'))
	releases = releases.paginate(page, per_page, False)
	return releases



@app.route('/stories/<letter>/<int:page>')
@app.route('/stories/<int:page>')
@app.route('/stories/')
def renderReleasesTable(letter=None, page=1):

	releases = get_releases(page=page)

	return render_template('story-list.html',
						   sequence_item   = releases,
						   page            = page,
						   letter          = letter,
						   path_name       = "stories",
						   name_key        = "title",
						   page_url_prefix = 'stories',
						   major_title     = 'Stories',
						   )
