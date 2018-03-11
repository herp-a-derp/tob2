

import os
import os.path
import markdown
import WebRequest
import json
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
import Levenshtein
import sys
import dateutil.parser

import spacy
import natsort
from fuzzywuzzy import fuzz
import tqdm
import UniversalArchiveInterface
from concurrent.futures import ThreadPoolExecutor



from datasketch import MinHash, MinHashLSH
from nltk import ngrams

import settings
import app.api_handlers
import app.models
import app

from . import HtmlProcessor

from util import webFunctions
from datauri import DataURI

def strip_markup(in_str):
	soup = WebRequest.as_soup(in_str)
	out_str = soup.get_text(strip=True)

	out_str = out_str.replace("\r", " ")
	out_str = out_str.replace("\n", " ")
	out_str = out_str.replace("	", " ")
	while "  " in out_str:
		out_str = out_str.replace("  ", " ")

	return out_str.strip().lower()

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

		try:
			zfp = UniversalArchiveInterface.ArchiveReader(fpath)
		except UniversalArchiveInterface.NotAnArchive:
			return []

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
			if file_path.lower().endswith(".gif"):
				continue


			file_name = file_path.split("/")[-1]
			files.append((file_name, file_path, fctnt))

		return files


	def _conv_int(self, in_p, tmp_p, out_p, force_pre_conv=False):
		cachefile = out_p + ".complete"
		if os.path.exists(cachefile):
			with open(cachefile, "r") as fp:
				cont = fp.read()
			return cont
		print("No cachefile: %s" % cachefile)

		if in_p.endswith(".html") or in_p.endswith(".htm"):
			# For HTML files, just use my parser directly. It's better in general anyways.
			with open(in_p, "rb") as fp:
				raw_b = fp.read()
				decoded = bs4.UnicodeDammit(raw_b).unicode_markup
				html_in = ftfy.fix_text(decoded)

			proc = HtmlProcessor.HtmlPageProcessor(in_p, html_in)
			out_dat = proc.extractContent()


			ret_s = "<div>\n" + out_dat['contents'] + "</div>\n"
			with open(cachefile, "w") as fp:
				fp.write(ret_s)
			return ret_s

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


		ret_s = "<div>\n" + out_dat['contents'] + "</div>\n"
		with open(cachefile, "w") as fp:
			fp.write(ret_s)
		return ret_s


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
					file_dict['content_text'] = strip_markup(ret)

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
			fkeys = list(files[story_key]['files'].keys())

			fkeys = natsort.natsorted(fkeys, key=lambda x: (x[0].lower(), x[1].lower()))

			for fkey in fkeys:

				if len(files[story_key]) == 1:
					tocstr += "%s: by %s\n" % (story_key[1], story_key[0])
				else:
					tocstr += "%s (%s): by %s\n" % (story_key[1], files[story_key]['files'][fkey]['fname'], story_key[0])
				tocstr += "------\n"
				tocstr += "\n"
				tocstr += "<div id='%s'></div>\n" % abs(hash(story_key + (files[story_key]['files'][fkey]['fname'], )))
				tocstr += "\n"
				tocstr += "\n"

		tocstr += footer

		formatted = markdown.markdown(tocstr, extensions=["toc", 'extra'])

		soup = WebRequest.as_soup(formatted)
		for story_key in tqdm.tqdm(skeys):
			for fpath, file_dict in tqdm.tqdm(files[story_key]['files'].items()):
				shash = abs(hash(story_key + (file_dict['fname'], )))
				tgt_divs = soup.find_all("div", id=str(shash))
				assert len(tgt_divs) == 1, "Expected 1 div, found %s" % len(tgt_divs)
				tgt_div = tgt_divs[0]
				new_div = WebRequest.as_soup(file_dict['content_div'])

				tgt_div.insert(1, new_div.div)


		out = soup.prettify()

		with open("Aggregate file for %s.html" % (self.tag, ), 'w') as fp:
			fp.write(out)

		print("Resulting file size: %s" % len(out))
		# print("Markdown output:")
		# print(formatted)
		# print("Markdowned")

	def consolidate_dupes(self, agg_files):
		print("Loading NLP Matcher")
		# nlp, nlp_size = spacy.load('en_core_web_lg'), "large_vec"
		nlp, nlp_size = spacy.load('en_core_web_sm'), "small_vec"
		print("Matcher loaded")

		# Remove short items
		for key, value in agg_files.items():
			for fkey in list(value['files'].keys()):
				# print("File params: ", value['files'][fkey].keys())
				if not 'content_text' in value['files'][fkey]:
					print("Missing file:", key, fkey)
					value['files'].pop(fkey)
				elif len(value['files'][fkey]['content_text']) < 100:
					print("Removing short file: ", (key, fkey))
					value['files'].pop(fkey)

		smap = {}
		for key, value in agg_files.items():
			for fkey in value['files']:
				smap[(key, fkey)] = value['files'][fkey]['content_text']

		# ratios = {}
		# word_vectors = {}
		# bak_file = {}
		# pik_file_name = "matches-%s-%s.pik" % (self.tag, nlp_size)
		# nlp_key = "nlp_%s" % nlp_size
		# if os.path.exists(pik_file_name):
		# 	print("Loading similarity searches from hash file %s." % pik_file_name)
		# 	try:
		# 		with open(pik_file_name, "rb") as fp:
		# 			loaded = pickle.load(fp)
		# 			if "ratios" in loaded:
		# 				print("Current cachefile structure")
		# 				ratios = loaded['ratios']
		# 				bak_file = loaded
		# 				print("Loaded %s cached comparisons" % len([ratios]))
		# 			else:
		# 				print("Old cachefile structure")
		# 				# Allow the old file version
		# 				ratios = loaded
		# 				bak_file = {
		# 					'ratios' : ratios
		# 				}
		# 				print("Loaded %s cached comparisons" % len(ratios))


		# 	except Exception:
		# 		traceback.print_exc()
		# 		print("Pickle file invalid?")
		# 		print("Ignoring")


		# print("Loading word vectors")

		# print("Doing batch req")
		# with ThreadPoolExecutor(max_workers=5) as ex:
		# 	futures = [(key, ex.submit(nlp, content))
		# 			for
		# 				key, content
		# 			in
		# 				smap.items()
		# 			if
		# 				key not in word_vectors
		# 		]

		# 	for key, future in tqdm.tqdm(futures):
		# 		if key not in word_vectors:
		# 			word_vectors[key] = future.result()
		# 		else:
		# 			print("Re-processed %s" % (key, ))
		# 			word_vectors[key] = future.result()

		# print("Vectors loaded. Processing")

		# checks = 0
		# for key, content in tqdm.tqdm(smap.items()):
		# 	for other, other_content in tqdm.tqdm(smap.items()):
		# 		if other == key:
		# 			continue

		# 		kl = [key, other]
		# 		kl.sort()
		# 		kl = tuple(kl)

		# 		ratios.setdefault(kl, {})
		# 		if nlp_key not in ratios[kl]:
		# 			# we want the ratio of the smaller one to the larger one
		# 			larger, smaller  = (word_vectors[key], word_vectors[other]) \
		# 				if len(content) > len(other_content) else               \
		# 				(word_vectors[key], word_vectors[other])

		# 			ratios[kl][nlp_key] = smaller.similarity(larger)
		# 			# print("ratio: %s (%s <-> %s)" % (ratios[kl], key, other))


		# 			checks += 1
		# 			if checks > 30:
		# 				checks = 0
		# 				# print("Dumping file with %s entries" % len(bak_file['ratios']))
		# 				with open(pik_file_name, "wb") as fp:
		# 					bak_file['ratios'] = ratios
		# 					pickle.dump(bak_file, fp)

		# print("Similarity search complete.")
		# with open(pik_file_name, "wb") as fp:
		# 	pickle.dump(bak_file, fp)


		perms = 512
		lsh = MinHashLSH(threshold=0.5, num_perm=perms)

		minhashes = {}
		for key, content in tqdm.tqdm(smap.items()):
			minhash = MinHash(num_perm=perms)
			for d in ngrams(content, 10):
				minhash.update("".join(d).encode('utf-8'))
			lsh.insert(key, minhash)
			minhashes[key] = minhash

		lens = {}
		for key, content in smap.items():
			clen = len(content)
			lens.setdefault(clen, [])
			lens[clen].append(key)
		lenl = list(lens.keys())
		lenl.sort()

		print("%s items in file map before dupe elimination")

		for clen in lenl:
			tgt_keys = lens[clen]
			for key in tgt_keys:
				if key not in smap:
					continue
				if key not in minhashes:
					continue

				result = lsh.query(minhashes[key])
				if key in result:
					result.remove(key)
				if result:
					smap.pop(key)
					# for res in result:
					# print(key)
					# print("Similar: ", result)

		print("%s items in file map after dupe elimination")

		for key in minhashes.keys():
			result = lsh.query(minhashes[key])
			print("Candidates with Jaccard similarity > 0.5 for input", key, ":", result)


	def go(self):
		stories = self.load_stories_for_tag(self.tag)

		agg_files = {}
		for story in stories:
			ret = self.load_story(story)
			story['files'] = {}
			for fname, fpath, fcont in ret:
				story['files'][fpath] = {}
				story['files'][fpath]['fpath'] = fpath
				story['files'][fpath]['fcont'] = fcont
				story['files'][fpath]['fname'] = fname

			agg_files[(story['author'], story['title'])] = story

		self.bulk_convert(agg_files)

		self.consolidate_dupes(agg_files)

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
