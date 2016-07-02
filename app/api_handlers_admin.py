
from app import db
from app import app
from app.models import Author
from app.models import AuthorChanges
from app.models import Genres
from app.models import GenresChanges
from app.models import Story
from app.models import StoryChanges
from app.models import Tags
from app.models import TagsChanges


from sqlalchemy import or_

from flask import flash
from flask_babel import gettext
from flask_login import current_user

from flask_login import current_user
# import app.series_tools
from app.api_common import getResponse

# import FeedFeeder.FeedFeeder




def fix_escaped_quotes(dummy_data, admin_override=False):
	if admin_override is False and (not current_user.is_mod()):
		return getResponse(error=True, message="You have to have moderator privileges to do that!")

	# SELECT * FROM series WHERE title LIKE E'%\\\'%';
	bad_title = 0
	bad_desc = 0


	q = Story.query.filter(or_(Story.title.like(r"%'%"), Story.title.like(r"%’%"), Story.title.like(r"%‘%"), Story.title.like(r"%“%"), Story.title.like(r"%”%")))
	items = q.all()
	print("Name fixing processing query resulted in %s items" % len(items))
	for item in items:
		old = item.title
		new = old
		while any([r"\"" in new, r"\'" in new, "’" in new, "‘" in new, "“" in new, "”" in new]):
			new = new.replace(r"\'", "'")
			new = new.replace(r'\"', '"')
			new = new.replace(r"’", "'")
			new = new.replace(r"‘", "'")
			new = new.replace(r"“", '"')
			new = new.replace(r"”", '"')

		have = Story.query.filter(Story.title == new).scalar()
		if old != new:
			if have:
				print("Duplicate item!", (old, new), old==new)
				merge_series_ids(have.id, item.id)
			else:
				print("Fixing title.")
				item.title = new
				db.session.commit()
			bad_title += 1


	# FUCK ALL SMART QUOTE BULLSHITS EVER
	q = Story.query.filter(or_(Story.description.like(r"%'%"), Story.description.like(r"%’%"), Story.description.like(r"%‘%"), Story.description.like(r"%“%"), Story.description.like(r"%”%")))

	items = q.all()
	print("Series description processing query resulted in %s items" % len(items))
	for item in items:
		old = item.description
		new = old

		while any([r"\"" in new, r"\'" in new, "’" in new, "‘" in new, "“" in new, "”" in new]):
			new = new.replace(r"\'", "'")
			new = new.replace(r'\"', '"')
			new = new.replace(r"’", "'")
			new = new.replace(r"‘", "'")
			new = new.replace(r"“", '"')
			new = new.replace(r"”", '"')
		if old != new:
			print("Fixing description smart-quotes and over-escapes for series: %s" % item.id)
			item.description = new
			db.session.commit()
			bad_desc += 1

	print("Update complete.")

	return getResponse("%s main titles, %s descriptions required fixing. %s" % (bad_title, bad_desc, conflicts), error=False)


def clean_tags(dummy_data, admin_override=False):
	if admin_override is False and (not current_user.is_mod()):
		return getResponse(error=True, message="You have to have moderator privileges to do that!")
	bad_tags = 0

	bad_tags = db.session.execute('''
		SELECT
			COUNT(*)
		FROM
			tags
		WHERE
			tag IN (
			SELECT tag
			FROM (
				SELECT tag
				FROM tags
				GROUP BY tag
				HAVING COUNT(*) = 1
			) AS ONLY_ONCE
			)
		''')

	bad_tags = list(bad_tags)

	db.session.execute('''
		DELETE
		FROM
			tags
		WHERE
			tag IN (
			SELECT tag
			FROM (
				SELECT tag
				FROM tags
				GROUP BY tag
				HAVING COUNT(*) = 1
			) AS ONLY_ONCE
			)
		;
		''')
	db.session.commit()

	return getResponse("Found %s tags that required patching." % (bad_tags), error=False)

def deleteStory(data):

	if not current_user.is_mod():
		return getResponse(error=True, message="I see what you (tried) to do there!")
	assert 'item-id' in data
	assert 'mode' in data

	delete_id = data["item-id"]
	clean_item = Story.query.filter(Story.id==delete_id).one()


	# !Ordering here matters!
	# Change-tables have to go second.
	delete_from = [
			Author,
			AuthorChanges,
			Tags,
			TagsChanges,
			Genres,
			GenresChanges,
			# Story,
			# StoryChanges,
		]


	for clearTable in delete_from:
		clearTable.query.filter(clearTable.series==clean_item.id).delete()

	Watches.query.filter(Watches.series_id==clean_item.id).delete()
	Story.query.filter(Story.id==clean_item.id).delete()
	StoryChanges.query.filter(StoryChanges.srccol==clean_item.id).delete()
	# db.session.delete(clean_item)
	db.session.commit()

	return getResponse("Story was deleted entirely!", error=False)

