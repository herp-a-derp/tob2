

import tqdm
import os
import os.path
import logging
import json
import urllib.error
import urllib.parse
import datetime
import pytz
import pickle
import dateutil.parser
import WebRequest

import settings
import app.api_handlers
import app

from datauri import DataURI

class Walker():
	sourceurl = "http://overflowingbra.com/ding.htm?dates=%d"

	year_min = 1998
	year_max = 2022

	yearpik_name = "stories_for_year_%s.pik"
	aggpik_name  = "stories_all.pik"

	def __init__(self):
		self.log = logging.getLogger("Main.Scraper")
		self.wg = WebRequest.WebGetRobust()
		self.log.info("Scraper init!")

	def get_story_file(self, filediv):
		link = filediv.a['href']
		link = urllib.parse.urljoin(self.sourceurl, link)
		filectnt, name, mime = self.wg.getFileNameMime(link)
		self.log.info("Retreived %s byte file with name %s.", len(filectnt), name)
		return {
			"file" : filectnt,
			"name" : name,
			"mime" : mime,
		}


	def get_story(self, story_div, year):
		# print("story_div")
		# print(story_div)
		ret = {
			"title"  : None,
			"author" : None,
			"desc" : None,
			"tags" : None,
			"uldate" : None,
			"dlcount" : None,
			# "file" : None,
		}
		ret['title'] = story_div.find("div", class_='storytitle').get_text().strip()
		ret['author'] = story_div.find("div", class_='author').get_text().strip()
		if story_div.find("div", class_='summary'):
			ret['desc'] = story_div.find("div", class_='summary').get_text().strip()
		else:
			ret['desc'] = "No description!"
		if story_div.find("div", class_='downloads'):
			ret['dlcount'] = int(story_div.find("div", class_='downloads').get_text().strip().split(" ")[0])
		else:
			ret['desc'] = "No dlcount!"

		ret['tags'] = [tmp for tmp in story_div.find("div", class_='storycodes').get_text().strip().split(" ") if tmp]
		date_tmp = story_div.find("div", class_='submitdate').get_text().strip()

		if date_tmp:
			ret['uldate'] = dateutil.parser.parse(date_tmp)
		else:
			ret['uldate'] = datetime.datetime(year=year, month=1, day=1)

		try:
			ret['file'] = self.get_story_file(story_div.find("div", class_='storytitle'))
		except urllib.error.URLError:
			return None
		except WebRequest.FetchFailureError:
			return None

		assert all([tmp != None for tmp in ret.values()])
		return ret


	def get_year(self, year):
		url = self.sourceurl % year
		soup = self.wg.getSoup(url)
		storyentries = soup.find_all('div', class_='storybox')

		ret = []
		for entry in storyentries:
			story = self.get_story(entry, year)
			if story:
				ret.append(story)
		return ret

	def get_releases(self):
		for year in range(self.year_min, self.year_max+1):
			pikname = self.yearpik_name % year
			if os.path.exists(pikname):
				self.log.info("Already have stories for year %s", year)
			else:
				year_releases = self.get_year(year)
				with open(pikname, "wb") as fp:
					pickle.dump(year_releases, fp)


	def merge_releases(self):
		releases = []
		if os.path.exists(self.aggpik_name):
			self.log.info("Already constructed aggregated story pack.")
		else:
			for year in range(self.year_min, self.year_max+1):
				pikname = "stories_for_year_%s.pik" % year
				with open(pikname, "rb") as fp:
					items = pickle.load(fp)
					releases.extend(items)

			with open(self.aggpik_name, "wb") as fp:
				pickle.dump(releases, fp)

	def install_releases(self):
		with open(self.aggpik_name, "rb") as fp:
			items = pickle.load(fp)
		print(len(items))
		types = set()
		for item in items:
			types.add(item['file']['mime'])
		print(types)


		for item in tqdm.tqdm(items):
			self.check_add(item)

	def check_add(self, item):

		if not 'file' in item:
			return

		if ';' in item['file']['mime']:
			item['file']['mime'] = item['file']['mime'].split(";")[0]

		story = {
			'name'    : item['title'],
			'auth'    : item['author'],
			'tags'    : item['tags'],
			'desc'    : item['desc'],
			'ul_date' : item['uldate'],

			'fname'   : item['file']['name'],
			'file'    : DataURI.make(mimetype=item['file']['mime'], charset=None, base64=True, data=item['file']['file']),
		}

		# print(item['tags'])
		# print(item['file'])
		assert 'name' in story
		assert 'auth' in story
		assert 'fname' in story
		assert 'file' in story
		assert 'desc' in story
		assert 'tags' in story


		with app.app.test_request_context():
			app.api_handlers.addStory({'story' : story})


def go():
	walker = Walker()
	print(walker)
	walker.get_releases()
	walker.merge_releases()
	walker.install_releases()

if __name__ == "__main__":
	import logSetup
	logSetup.initLogging()
	go()
