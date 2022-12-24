
from app import db
import app
from app.models import Story
from app.models import Tags
from app.models import Author
# from app.models import Genres
from flask import g
from flask import flash
import markdown
import bleach
import os.path
import os
import hashlib
from datauri import DataURI
from flask_login import current_user
import datetime
import dateutil.parser
# import app.nameTools as nt
import datetime
from app.api_common import getResponse
# import app.series_tools

VALID_KEYS = {
	'description-container'  : 'description',
	'title-container'        : 'title',
	'demographic-container'  : 'demographic',
	'type-container'         : 'type',
	'origin_loc-container'   : 'origin_loc',
	'orig_lang-container'    : 'orig_lang',
	'author-container'       : 'author',
	'illustrators-container' : 'illustrators',
	'tag-container'          : 'tag',
	'genre-container'        : 'genre',
	'altnames-container'     : 'alternate-names',
	'region-container'       : 'region',
	'license_en-container'   : 'license_en',
	'orig_status-container'  : 'orig_status',
	'tl_type-container'      : 'tl_type',
	'website-container'      : 'website',
	'publisher-container'    : 'publisher',
	'pub_date-container'     : 'first_publish_date',
	'watch-container'        : None,

	}

# {
# 	'mode': 'manga-update',
# 	'item-id': '532',
# 	'entries':
# 		[
# 			{
# 				'type': 'combobox',
# 				'key': 'watch-container',
# 				'value': 'no-list'
# 			},
# 			{
# 				'type': 'multiitem',
# 				'key': 'publisher-container',
# 				'value': 'Test'
# 			}
# 		]
# }



def getCurrentUserId():
	'''
	if current_user == None, we're not executing within the normal flask runtime,
	which means we can probably assume that the caller is the system update
	service.
	'''
	if current_user != None:
		return current_user.id
	else:
		return app.app.config['SYSTEM_USERID']


################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################





def getHash(filecont):
	m = hashlib.md5()
	m.update(filecont)
	fHash = m.hexdigest()
	return fHash

def saveFile(filecont, filename):
	fHash = getHash(filecont)
	# use the first 3 chars of the hash for the folder name.
	# Since it's hex-encoded, that gives us a max of 2^12 bits of
	# directories, or 4096 dirs.
	fHash = fHash.upper()
	dirName = fHash[:3]

	dirPath = os.path.join(app.app.config['FILE_BACKEND_PATH'], dirName)
	if not os.path.exists(dirPath):
		os.makedirs(dirPath)

	ext = os.path.splitext(filename)[-1]
	ext   = ext.lower()

	# The "." is part of the ext.
	filename = '{filename}{ext}'.format(filename=fHash, ext=ext)


	# The "." is part of the ext.
	filename = '{filename}{ext}'.format(filename=fHash, ext=ext)

	# Flask config values have specious "/./" crap in them. Since that gets broken through
	# the abspath canonization, we pre-canonize the config path so it compares
	# properly.
	confpath = os.path.abspath(app.app.config['FILE_BACKEND_PATH'])

	fqpath = os.path.join(dirPath, filename)
	fqpath = os.path.abspath(fqpath)

	if not fqpath.startswith(confpath):
		raise ValueError("Generating the file path to save a cover produced a path that did not include the storage directory?")

	locpath = fqpath[len(confpath):]
	if not os.path.exists(fqpath):
		# print("Saving cover file to path: '{fqpath}'!".format(fqpath=fqpath))
		with open(fqpath, "wb") as fp:
			fp.write(filecont)
	else:
		print("File '{fqpath}' already exists!".format(fqpath=fqpath))

	if locpath.startswith("/"):
		locpath = locpath[1:]
	return locpath


# Json request:
#   {
#     'mode': 'add-story',
#     'entry': {
#         'name': 'Asd',
#         'tags': [
#             ['other', 'bond'],
#             ['other', 'hyp'],
#             ['other', 'lac'],
#             ['other', 'nc']
#         ],
#         'fname': 'was.cer',
#         'file': 'data:application/x-x509-ca-cert;base64,<stuff>',
#         'desc': 'asd',
#         'type': 'new-story'
#     }
# }

def addStory(updateDat):
	assert 'story' in updateDat

	story = updateDat['story']
	story['clean_name'] = bleach.clean(story['name'], tags=[], strip=True)

	assert 'name' in story
	assert 'auth' in story
	assert 'fname' in story
	assert 'file' in story
	assert 'desc' in story
	assert 'tags' in story

	data = DataURI(story['file'])

	dathash = getHash(data.data).lower()
	have = Story.query.filter(Story.hash == dathash).scalar()

	if have:
		# print("Have file already!")
		return getResponse("A file with that MD5 hash already exists! Are you accidentally adding a duplicate?", True)

	have = Story.query.filter(Story.title == story['clean_name']).scalar()
	if have:
		orig_name = story['name']
		loop = 2
		while have:
			print("Have story with that name ('%s')!" % story['name'])
			story['name'] = orig_name + " (%s)" % loop
			story['clean_name'] = bleach.clean(story['name'], tags=[], strip=True)
			have = Story.query.filter(Story.title == story['clean_name']).scalar()
			loop += 1

		print("Story added with number in name: '%s'" % story['name'])

	if len(story['name']) > 80:
		return getResponse("Maximum story title length is 80 characters!", True)
	if len(story['name']) < 3:
		return getResponse("Minimum story title length is 3 characters!", True)
	if len(story['auth']) < 5:
		return getResponse("Minimum story author name length is 5 characters!", True)
	if len(story['auth']) > 60:
		return getResponse("Maximum story author name length is 60 characters!", True)
	if len(story['desc']) < 30:
		return getResponse("Minimum story description length is 30 characters!", True)
	if len(story['desc']) > 500:
		return getResponse("Maximum story description length is 500 characters!", True)

	fspath = saveFile(data.data, story['fname'])

	stags = ["-".join(itm_tags.split(" ")) for itm_tags in story['tags']]
	stags = [bleach.clean(tag, tags=[], strip=True) for tag in stags]

	# print("name: ", story['name'])
	# print("clean_name: ", story['clean_name'])
	# print("Author: ", story['auth'])
	# print("stags: ", story['tags'])
	# print("stags: ", stags)

	post_date = datetime.datetime.now()
	if 'ul_date' in story and isinstance(story['ul_date'], datetime.datetime):
		post_date = story['ul_date']

	new = Story(
		title       = story['clean_name'],
		srcfname    = story['fname'],
		description = markdown.markdown(bleach.clean(story['desc'], strip=True)),
		fspath      = fspath,
		hash        = dathash,
		# author      = [story['auth']],
		# tags        = stags,
		pub_date    = post_date
		)

	[new.tags.append(Tags(tag=tag)) for tag in stags]
	new.author.append(Author(name=bleach.clean(story['auth'], tags=[], strip=True)))

	db.session.add(new)
	db.session.commit()

	flash('Your story has been added! Thanks for posting your content!')
	return getResponse("Story added", error=False)
