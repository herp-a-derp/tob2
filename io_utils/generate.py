

import os
import os.path
import logging
import subprocess
import json
import urllib.error
import urllib.parse
import datetime
import pytz
import pickle
import sys
import dateutil.parser

import tqdm
import UniversalArchiveInterface

import settings
import app.api_handlers
import app.models
import app
from util import webFunctions

from datauri import DataURI

class HtmlGenerator():

	def __init__(self, target_tag):
		self.tag = target_tag

		self.input_tmp_dir  = os.path.abspath("./conv_temp/in")
		self.output_tmp_dir = os.path.abspath("./conv_temp/out")


	def load_stories_for_tag(self, tag):
		with app.app.app_context():
			# stories = app.models.Story.query.all()
			# print(stories)
			tag_instances = app.models.Tags.query.filter(app.models.Tags.tag==tag).all()
			if not tag_instances:
				print("No tag instances!")
			stories = [tmp.series_row for tmp in tag_instances if tmp.series_row.fspath]
			print("Found %s matching tags, %s matching stories" % (len(tag_instances), len(stories)))

			ret = [
				{
					'id'          : story.id,
					'title'       : story.title,
					'description' : story.description,
					'orig_lang'   : story.orig_lang,
					'chapter'     : story.chapter,
					'pub_date'    : story.pub_date,
					'srcfname'    : story.srcfname,
					'fspath'      : story.fspath,
					'hash'        : story.hash,
				} for story in stories
			]

			ret.sort(key=lambda x: x['title'])
			return ret

	def load_story(self, item_dict):

		fpath = os.path.join(settings.FILE_BACKEND_PATH, item_dict['fspath'])

		zfp = UniversalArchiveInterface.ArchiveReader(fpath)

		files = []

		for file_path, fileCtnt in zfp:
			if file_path.endswith("Thumbs.db"):
				continue
			if "/__MACOSX/" in file_path or file_path.startswith("__MACOSX/"):
				continue

			if ".DS_Store" in file_path:
				continue

			fctnt = fileCtnt.read()
			if file_path.lower().endswith(".jpg"):
				continue
			if file_path.lower().endswith(".png"):
				continue


			file_name = file_path.split("/")[-1]
			files.append((file_name, file_path, fctnt))

		return files

	def convert(self, fname, content):
		in_p      = os.path.join(self.input_tmp_dir, fname)
		out_p     = os.path.join(self.output_tmp_dir, fname)
		out_p, _  = os.path.splitext(out_p)
		out_p    += ".rtf"

		in_p  = in_p.replace(" ", "_")
		out_p = out_p.replace(" ", "_")

		with open(in_p, "wb") as fp:
			fp.write(content)

		if in_p.lower().endswith(".doc"):
			bad_in = in_p
			in_p = in_p + "x"

			print("Doing doc->docx conversion!")
			proc = subprocess.run(["unoconv", "-f", "docx", "-o", in_p, bad_in], check=True)

		proc = subprocess.run(["ebook-convert", in_p, out_p], check=True)


	def bulk_convert(self, files):
		os.makedirs(self.input_tmp_dir,  exist_ok=True)
		os.makedirs(self.output_tmp_dir, exist_ok=True)

		ret = []
		for fname, fvals in tqdm.tqdm(files.items()):
			_, content = fvals
			ret = self.convert(fname, content)



	def go(self):
		stories = self.load_stories_for_tag(self.tag)

		agg_files = {}
		for story in stories:
			ret = self.load_story(story)
			for fname, fpath, fcont in ret:
				agg_files[fname] = (fpath, fcont)

		converted = self.bulk_convert(agg_files)

		print("Selected archives extracted to %s individual files" % len(agg_files))
		print(list(agg_files.keys()))
		# print(stories)


def go():
	print(sys.argv)
	if len(sys.argv) != 2:
		print("You need to pass a tag to generate content for!")
		return
	tag = sys.argv[1]


	gen = HtmlGenerator(tag)
	print(gen)
	gen.go()

if __name__ == "__main__":
	import logSetup
	logSetup.initLogging()
	go()
