

import os
import os.path
import markdown
import natsort
import WebRequest
import logging
import traceback
import subprocess
import ftfy
import bs4
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

from . import HtmlProcessor

from util import webFunctions
from datauri import DataURI

class HtmlGenerator():

	def __init__(self, target_tag):
		self.tag = target_tag

		self.input_tmp_dir  = os.path.abspath("./conv_temp/in")
		self.proc_tmp_dir  = os.path.abspath("./conv_temp/mid")
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

			ret = []
			for story in stories:
				auth_l = story.author
				assert len(auth_l) == 1
				author = story.author[0].name
				story_dat = {
						'id'          : story.id,
						'title'       : story.title,
						'author'      : author,
						'description' : story.description,
						'orig_lang'   : story.orig_lang,
						'chapter'     : story.chapter,
						'pub_date'    : story.pub_date,
						'srcfname'    : story.srcfname,
						'fspath'      : story.fspath,
						'hash'        : story.hash,
					}
				ret.append(story_dat)

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
			if ".pages" in file_path:
				continue

			fctnt = fileCtnt.read()
			if file_path.lower().endswith(".jpg"):
				continue
			if file_path.lower().endswith(".png"):
				continue


			file_name = file_path.split("/")[-1]
			files.append((file_name, file_path, fctnt))

		return files


	def _conv_int(self, in_p, tmp_p, out_p, force_pre_conv=False):

		if in_p.endswith(".html") or in_p.endswith(".htm"):
			# For HTML files, just use my parser directly. It's better in general anyways.
			with open(in_p, "rb") as fp:
				raw_b = fp.read()
				decoded = bs4.UnicodeDammit(raw_b).unicode_markup
				html_in = ftfy.fix_text(decoded)

			proc = HtmlProcessor.HtmlPageProcessor(in_p, html_in)
			out_dat = proc.extractContent()


			return out_dat['contents']

		if in_p.lower().endswith(".doc"):
			bad_in = in_p
			in_p = tmp_p + ".rtf"
			subprocess.run(["unoconv", "-f", "rtf", "-o", in_p, bad_in], check=True, stdout=subprocess.PIPE)

		if in_p.lower().endswith(".wps"):
			bad_in = in_p
			in_p = tmp_p + ".rtf"
			subprocess.run(["unoconv", "-f", "rtf", "-o", in_p, bad_in], check=True, stdout=subprocess.PIPE)

		if force_pre_conv:
			bad_in = in_p
			in_p = tmp_p + ".rtf"
			subprocess.run(["unoconv", "-f", "rtf", "-o", in_p, bad_in], check=True, stdout=subprocess.PIPE)

		tmp_f_1 = tmp_p + "_mid.rtf"

		subprocess.run(["ebook-convert", in_p, tmp_f_1], check=True, stdout=subprocess.PIPE)
		subprocess.run(["unoconv", "-f", "html", "-o", tmp_p + ".html", tmp_f_1], check=True, stdout=subprocess.PIPE)

		with open(tmp_p + ".html") as fp:
			html_in = fp.read()

		proc = HtmlProcessor.HtmlPageProcessor(in_p, html_in)
		out_dat = proc.extractContent()


		return "<div>\n" + out_dat['contents'] + "</div>\n"


	def convert(self, fname, content):
		in_p      = os.path.join(self.input_tmp_dir, fname)
		out_p     = os.path.join(self.output_tmp_dir, fname)
		tmp_p     = os.path.join(self.proc_tmp_dir, fname)
		out_p, _  = os.path.splitext(out_p)
		out_p    += ".rtf"

		in_p  = in_p.replace(" ", "_")
		out_p = out_p.replace(" ", "_")

		with open(in_p, "wb") as fp:
			fp.write(content)

		try:
			return self._conv_int(in_p, tmp_p, out_p)
		except Exception:
			print("error processing %s. Forcing intermediate rtf step." % fname)
			return self._conv_int(in_p, tmp_p, out_p, force_pre_conv=True)


	def bulk_convert(self, files):
		os.makedirs(self.input_tmp_dir,  exist_ok=True)
		os.makedirs(self.proc_tmp_dir,   exist_ok=True)
		os.makedirs(self.output_tmp_dir, exist_ok=True)

		for story_key, story_params in tqdm.tqdm(files.items()):
			for file_dict in story_params['files'].values():
				try:
					ret = self.convert(file_dict['fname'], file_dict['fcont'])
					file_dict['content_div'] = ret
					# file_dict['content_div'] = "wat"

				except Exception:
					traceback.print_exc()
					print("Failure converting %s (%s)!" % (file_dict['fname'], story_params['title']))

	def make_overall_file(self, files):
		header = '''

Assorted Stories
---

Table of Contents:

[TOC]

<div style="width:500px" markdown="1">

'''
		footer = '''

</div>
		'''

		skeys = list(files.keys())
		skeys = natsort.natsorted(skeys, key=lambda x: (x[0].lower(), x[1].lower()))

		tocstr = ""
		tocstr += header
		for story_key in skeys:
			for fpath, file_dict in files[story_key]['files'].items():
				if len(files[story_key]) == 1:
					tocstr += "%s: by %s\n" % (story_key[1], story_key[0])
				else:
					tocstr += "%s (%s): by %s\n" % (story_key[1], file_dict['fname'], story_key[0])
				tocstr += "------\n"
				tocstr += "\n"
				tocstr += "<div id='%s'></div>\n" % abs(hash(story_key + (file_dict['fname'], )))
				tocstr += "\n"
				tocstr += "\n"

		tocstr += footer

		formatted = markdown.markdown(tocstr, extensions=["toc", 'extra'])

		soup = WebRequest.as_soup(formatted)
		for story_key in tqdm.tqdm(skeys):
			for fpath, file_dict in files[story_key]['files'].items():
				shash = abs(hash(story_key + (file_dict['fname'], )))
				tgt_divs = soup.find_all("div", id=str(shash))
				assert len(tgt_divs) == 1
				tgt_div = tgt_divs[0]

				tgt_div.string = file_dict['content_div']


		out = soup.prettify()

		with open("Aggregate file for %s.html" % (self.tag, ), 'w') as fp:
			fp.write(out)

		print("Resulting file size: %s" % len(out))
		# print("Markdown output:")
		# print(formatted)
		# print("Markdowned")

	def go(self):
		stories = self.load_stories_for_tag(self.tag)

		agg_files = {}
		for story in stories:
			ret = self.load_story(story)
			for fname, fpath, fcont in ret:
				story['files'] = {}
				story['files'][fpath] = {}
				story['files'][fpath]['fpath'] = fpath
				story['files'][fpath]['fcont'] = fcont
				story['files'][fpath]['fname'] = fname

			agg_files[(story['author'], story['title'])] = story

		self.bulk_convert(agg_files)

		self.make_overall_file(agg_files)

		print("Selected archives extracted to %s individual files" % len(agg_files))
		# print(list(agg_files.keys()))
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
