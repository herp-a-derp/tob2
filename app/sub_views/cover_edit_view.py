
from flask import render_template
from app import app
from app.models import Story
from app.sub_views.item_views import get_cover_sorter

@app.route('/series-id/<sid>/edit-covers/')
def renderEditCovers(sid):
	series       =       Story.query.filter(Story.id==sid).first()

	if not series:
		return render_template(
				'not-implemented-yet.html',
				message = "Resulting series for sid: '%s' is none somehow? Wat? This shouldn't happen." % sid
				)


	series.covers.sort(key=get_cover_sorter())

	return render_template(
			'covers-edit.html',
			series       = series,
		)