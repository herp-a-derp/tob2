

import os
import ast
import os.path
import traceback
import subprocess
import bs4
import urllib.error
import urllib.parse
import datetime
import pytz
import pickle
import string
import Levenshtein
import sys
import magic
import dateutil.parser

import ftfy
import markdown
import click
import WebRequest
import spacy
import natsort
import zipfile
from fuzzywuzzy import fuzz
import tqdm
import UniversalArchiveInterface
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor

import WebRequest

from datasketch import MinHash, MinHashLSH
from nltk import ngrams

import settings
import app.api_handlers
import app.models
import app

from . import HtmlProcessor


from datauri import DataURI

def strip_markup(in_str):
	soup = WebRequest.as_soup(in_str)
	out_str = soup.get_text(strip=True)

	out_str = out_str.replace("\r", " ")
	out_str = out_str.replace("\n", " ")
	out_str = out_str.replace("	", " ")
	while "  " in out_str:
		out_str = out_str.replace("  ", " ")
	out_str = "".join([c for c in out_str if c in
		(string.ascii_letters + string.digits + ".,! ")])

	return out_str.strip().lower()


def minhash_str(in_str, perms, gram_sz):
	minhash = MinHash(num_perm=perms)
	for d in ngrams(in_str, gram_sz):
		minhash.update("".join(d).encode('utf-8'))
	return minhash


class HtmlGenerator():

	def __init__(self,
			target_tags=None,
			target_string=None,
			target_author=None,
			target_include_string=None,
			target_exclude_string=None
			):

		print("HTML Generator init!")

		self.tags     = target_tags
		self.str     = target_string
		self.author     = target_author
		self.inc_str = target_include_string
		self.exc_str = target_exclude_string

		self.input_tmp_dir  = os.path.abspath("./conv_temp/in")
		self.proc_tmp_dir  = os.path.abspath("./conv_temp/mid")
		self.output_tmp_dir = os.path.abspath("./conv_temp/out")

	def __unpack_stories(self, stories_list):

		ret = []
		for story in stories_list:
			auth_l = story.author
			assert len(auth_l) == 1
			author = story.author[0].name
			if author == 'Continuous Story' or author == 'continuous story':
				continue
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
		print("Found %s files in %s story bundles" % (len(ret), len(stories_list)))
		return ret


	def load_stories_for_tag(self, tags):
		with app.app.app_context():
			story_count = app.models.Story.query.count()
			# print(stories)
			tag_instances = app.models.Tags.query.filter(app.models.Tags.tag == tags[0]).all()
			if not tag_instances:
				print("No tag instances!")

			stories = [tmp.series_row for tmp in tag_instances if tmp.series_row.fspath]
			print("%s stories matching tag %s" % (len(stories), tags[0]))

			print("Tags = ", stories[0].tags)

			stories = [
					tmp
				for
					tmp
				in
					stories
				if
					all([tag in [tagtag.tag for tagtag in tmp.tags] for tag in tags])
			]

			print("Found %s matching tags, %s/%s matching stories" % (len(tag_instances), len(stories), story_count))

			return self.__unpack_stories(stories)

	def load_stories_for_author(self, author):
		assert isinstance(author, str), "Author must be a string. Passed %s (%s)" % (type(author), author)

		with app.app.app_context():
			story_count = app.models.Story.query.count()
			# print(stories)
			query = app.models.Author.query.filter(app.models.Author.name.ilike("%{}%".format(author)))
			print("Query: '%s'"  % query)
			auth_instances = query.all()
			if not auth_instances:
				print("No tag instances!")

			stories = [tmp.series_row for tmp in auth_instances if tmp.series_row.fspath]
			print("%s stories matching author %s" % (len(stories), author))

			auths = [tmp.name for tmp in stories[0].author]

			print("Author = ", auths)

			print("Found %s matching tags, %s/%s matching stories" % (len(auths), len(stories), story_count))

			return self.__unpack_stories(stories)

	def load_all_stories(self):
		with app.app.app_context():
			story_instances = app.models.Story.query.all()
			if not story_instances:
				print("No stories?")
			stories = [tmp for tmp in story_instances if tmp.fspath]
			print("Found %s matching story_instances, %s matching stories" % (len(story_instances), len(stories)))


			return self.__unpack_stories(stories)

	def load_story(self, item_dict):

		fpath = os.path.join(settings.FILE_BACKEND_PATH, item_dict['fspath'])



		ftype = magic.from_file(fpath, mime=True)
		ftype = ftype.split(";")[0]
		if ftype == 'text/html':
			print("Direct HTML content: '%s'" % fpath)
			with open(fpath, "rb") as fp:
				return [[fpath.split("/")[-1], "", fp.read()]]
		elif ftype == 'application/msword' or \
			ftype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
			print("Direct word content: '%s'" % fpath)
			with open(fpath, "rb") as fp:
				return [[fpath.split("/")[-1], "", fp.read()]]
		elif ftype == 'inode/x-empty':
			return []
		else:
			try:
				zfp = UniversalArchiveInterface.ArchiveReader(fpath)
			except UniversalArchiveInterface.NotAnArchive:
				print("Don't know how to process '%s' file type." % (ftype))
				return []
			except UniversalArchiveInterface.CorruptArchive:
				print("Archive corrupt: '%s'." % (ftype))
				return []

		files = []

		try:
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
				if file_path.lower().endswith(".mp3"):
					continue
				if file_path.lower().endswith(".wav"):
					continue
				if file_path.lower().endswith(".jpeg"):
					continue
				if file_path.lower().endswith(".png"):
					continue
				if file_path.lower().endswith(".gif"):
					continue
				if file_path.lower().endswith(".thmx"):
					continue


				file_name = file_path.split("/")[-1]
				files.append((file_name, file_path, fctnt))

		# Thrown on password protected zips. Apparently.
		except RuntimeError:
			pass
		except (UniversalArchiveInterface.CorruptArchive, zipfile.BadZipFile):
			print("Archive corrupt: '%s'." % (fpath))
			return []

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

				if 'charset=iso-8859-1' in decoded:
					decoded = decoded.replace("charset=iso-8859-1", "charset=UTF-8")
				if 'charset=ISO-8859-1' in decoded:
					decoded = decoded.replace("charset=ISO-8859-1", "charset=UTF-8")

				html_in = ftfy.fix_text(decoded)

			proc = HtmlProcessor.HtmlPageProcessor(in_p, html_in)
			out_dat = proc.extractContent()


			ret_s = "<div>\n" + out_dat['contents'] + "</div>\n"

			print("Direct HTML writing to output cache: %s", cachefile)
			with open(cachefile, "w") as fp:
				fp.write(ret_s)
			return ret_s

		if in_p.lower().endswith(".doc"):
			bad_in = in_p
			in_p = tmp_p + ".rtf"
			subprocess.run(["unoconv", "-f", "rtf", "-o", in_p, bad_in], check=True, timeout=60)

		if in_p.lower().endswith(".wps"):
			bad_in = in_p
			in_p = tmp_p + ".rtf"
			subprocess.run(["unoconv", "-f", "rtf", "-o", in_p, bad_in], check=True, timeout=60)

		if force_pre_conv:
			bad_in = in_p
			in_p = tmp_p + ".rtf"
			subprocess.run(["unoconv", "-f", "rtf", "-o", in_p, bad_in], check=True, timeout=60)

		tmp_f_1 = tmp_p + "_mid.rtf"

		subprocess.run(["ebook-convert", in_p, tmp_f_1, "--enable-heuristics"], check=True, timeout=60)
		subprocess.run(["unoconv", "-f", "html", "-o", tmp_p + ".html", tmp_f_1], check=True, timeout=60)

		with open(tmp_p + ".html") as fp:
			html_in = fp.read()

		html_in = ftfy.fix_text(html_in)

		proc = HtmlProcessor.HtmlPageProcessor(in_p, html_in)
		out_dat = proc.extractContent()


		out_dat['contents'] = ftfy.fix_text(out_dat['contents'])

		ret_s = "<div>\n" + out_dat['contents'] + "</div>\n"

		print("Writing to output cache: %s", cachefile)
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
			try:
				return self._conv_int(in_p, tmp_p, out_p, force_pre_conv=True)
			except Exception:
				print("Failed when processing %s even with rtf step." % fname)
				return ""


	def bulk_convert(self, files):
		os.makedirs(self.input_tmp_dir,  exist_ok=True)
		os.makedirs(self.proc_tmp_dir,   exist_ok=True)
		os.makedirs(self.output_tmp_dir, exist_ok=True)


		print("Doing bulk conversion.")
		with ThreadPoolExecutor(max_workers=4) as exc:
			for story_key in tqdm.tqdm(files.keys(), desc="Converting Files"):
				for f_key in files[story_key]['files'].keys():
					try:
						files[story_key]['files'][f_key]['future'] = exc.submit(self.convert, files[story_key]['files'][f_key]['fname'], files[story_key]['files'][f_key]['fcont'])

					except Exception:
						traceback.print_exc()
						print("Failure converting %s (%s)!" % (files[story_key]['files'][f_key]['fname'], files[story_key]['title']))

			print("All files submitted to executors. Iterating over results.")
			# for story_key, story_params in tqdm.tqdm(files.items(), desc="Loading Results"):
			# 	for file_dict in story_params['files'].values():
			for story_key in tqdm.tqdm(files.keys(), desc="Converting Files"):
				for f_key in files[story_key]['files'].keys():
					try:
						files[story_key]['files'][f_key]['content_div'] = files[story_key]['files'][f_key]['future'].result()
						files[story_key]['files'][f_key]['content_text'] = strip_markup(files[story_key]['files'][f_key]['content_div'])

					except Exception:
						traceback.print_exc()
						print("Failure converting %s (%s)!" % (files[story_key]['files'][f_key]['fname'], files[story_key]['title']))

					if 'future' in files[story_key]['files'][f_key]:
						files[story_key]['files'][f_key].pop('future')

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
		skeys = natsort.natsorted(skeys, key=lambda x: (files[x]['author'].lower(), x[0].lower(), x[1].lower()))

		tocstr = ""
		tocstr += header
		for story_key in skeys:
			fkeys = list(files[story_key]['files'].keys())

			fkeys = natsort.natsorted(fkeys, key=lambda x: x.lower())

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
		for story_key in tqdm.tqdm(skeys, "Building overall file"):
			for fpath, file_dict in tqdm.tqdm(files[story_key]['files'].items(), desc="Processing single input"):
				wat_1 = hash(story_key + (file_dict['fname'], ))
				wat_2 = abs(wat_1)
				shash = str(wat_2)
				tgt_divs = soup.find_all("div", id=shash)
				assert len(tgt_divs) == 1, "Expected 1 div, found %s" % len(tgt_divs)
				tgt_div = tgt_divs[0]
				new_div = WebRequest.as_soup(file_dict['content_div'])

				tgt_div.insert(1, new_div.div)


		out = soup.prettify()
		fout_fname = "Aggregate file %s%s%s%s%s.html" % (
					((" tag %s" % (self.tags, )) if self.tags else ""),
					((" author %s" % (self.author, )) if self.author else ""),
					((" with str %s" % (self.str, )) if self.str else ""),
					((" with inc_str %s" % (self.inc_str, )) if self.inc_str else ""),
					((" with exc_str %s" % (self.exc_str, )) if self.exc_str else ""),
				)
		while "  " in fout_fname:
			fout_fname = fout_fname.replace("  ", " ")

		with open(fout_fname, 'w') as fp:
			fp.write(out)

		print("Resulting file size: %s" % len(out))
		# print("Markdown output:")
		# print(formatted)
		# print("Markdowned")

	def consolidate_dupes(self, agg_files):
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

		perms = 512
		gram_sz = 10
		thresh = 0.5
		lsh = MinHashLSH(threshold=thresh, num_perm=perms)

		print("Loading word hashes")
		minhashes = {}

		with ProcessPoolExecutor(max_workers=10) as ex:
			print("Submitting jobs")
			futures = [(key, ex.submit(minhash_str, content, perms, gram_sz))
					for
						key, content
					in
						smap.items()
				]
			print("Submitted %s jobs. Consuming futures" % len(futures))
			for key, future in tqdm.tqdm(futures, "Hashing"):
				minhash = future.result()
				lsh.insert(key, minhash)
				minhashes[key] = minhash


		lens = {}
		for key, content in smap.items():
			clen = len(content)
			lens.setdefault(clen, [])
			lens[clen].append(key)
		lenl = list(lens.keys())
		lenl.sort()

		print("%s items in file map before dupe elimination" % len(smap))

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
					still_ok = [tmp for tmp in result if tmp in smap]
					if still_ok:
						smap.pop(key)
						akey, fkey = key
						agg_files[akey]['files'].pop(fkey)

					# for res in result:
					# print(key)
					# print("Similar: ", result)

		print("%s items in file map after dupe elimination" % len(smap))

		return agg_files


	def __filter_stories(self, agg_files, filter_str=None, include_str_list=None, exclude_str_list=None):
		for story_key in tqdm.tqdm(list(agg_files.keys())):
			for fkey in list(agg_files[story_key]['files'].keys()):
				story_lower = agg_files[story_key]['files'][fkey]['content_text'].lower()

				if filter_str:
					if not filter_str.lower() in story_lower:
						if fkey in agg_files[story_key]['files']:
							print("Removing file %s from output due to filter_str" % agg_files[story_key]['files'][fkey]['fname'])
							agg_files[story_key]['files'].pop(fkey)

				if include_str_list:
					if not any([tmp.lower() in story_lower for tmp in include_str_list]):
						if fkey in agg_files[story_key]['files']:
							print("Removing file %s from output due to include_str_list" % agg_files[story_key]['files'][fkey]['fname'])
							agg_files[story_key]['files'].pop(fkey)

				if exclude_str_list:
					if any([tmp.lower() in story_lower for tmp in exclude_str_list]):
						if fkey in agg_files[story_key]['files']:
							print("Removing file %s from output due to exclude_str_list" % agg_files[story_key]['files'][fkey]['fname'])
							agg_files[story_key]['files'].pop(fkey)

		return agg_files


	def go(self):
		print("Loading all stories")
		stories = self.load_all_stories()


		pik_name = "loaded_story_cache.pik"
		if os.path.exists(pik_name):
			print("Have cached loaded story file. Using that.")
			with open(pik_name, "rb") as fp:
				agg_files = pickle.load(fp)
		else:
			agg_files = {}
			print("No loaded story file. Regenerating.")
			for story in tqdm.tqdm(stories, desc="Loading Stories"):
				ret = self.load_story(story)
				story['files'] = {}
				for fname, fpath, fcont in ret:
					story['files'][fpath] = {}
					story['files'][fpath]['fpath'] = fpath
					story['files'][fpath]['fcont'] = fcont
					story['files'][fpath]['fname'] = fname

				agg_files[(story['author'], story['title'])] = story

			self.bulk_convert(agg_files)

			print("Dumping loaded story cache file.")
			with open(pik_name, "wb") as fp:
				pickle.dump(agg_files, fp)



		if self.tags:
			print("Loading stories for tag %s" % (self.tags, ))
			stories = self.load_stories_for_tag(self.tags)
			print("Filtering stories. Input: %s, %s" % (len(stories), len(agg_files)))
			wanted_keys = set([
						(story['author'], story['title'])
					for
						story
					in
						stories
				])

			agg_files = {
						key : value
					for
						key, value
					in
						agg_files.items()
					if
						key in wanted_keys
				}
			print("Tag filter output: ", len(agg_files))



		if self.author:
			print("Loading stories for author %s" % (self.author, ))
			for key in agg_files.keys():
				print("Key: ", key)
			agg_files = {
						key : value
					for
						key, value
					in
						agg_files.items()
					if
						self.author.lower() in str(key).lower()
				}
			print("Author filter output: ", len(agg_files))




		if self.str or self.inc_str or self.exc_str:
			agg_files = self.__filter_stories(agg_files      = agg_files,
											filter_str       = self.str,
											include_str_list = self.inc_str,
											exclude_str_list = self.exc_str)

		agg_files = self.consolidate_dupes(agg_files)


		self.make_overall_file(agg_files)

		print("Selected archives extracted to %s individual files" % len(agg_files))
		# print(list(agg_files.keys()))
		# print(stories)

@click.group()
def cli():
	pass


@cli.command()
@click.option('--tag', default=None, multiple=True)
@click.option('--string', default=None)
@click.option('--exclude-strings', default=None)
@click.option('--include-strings', default=None)
def gen(tag, string, exclude_strings, include_strings):
	'''
	Generic generate command
	'''
	if not any((tag, string, exclude_strings, include_strings)):
		print("No args!")
		return 1

	if include_strings:
		include_strings = ast.literal_eval(include_strings)
	if exclude_strings:
		exclude_strings = ast.literal_eval(exclude_strings)

	print("CLI gen:")
	print((tag, string, include_strings, exclude_strings))

	gen = HtmlGenerator(
		target_tags            = tag,
		target_string         = string,
		target_include_string = include_strings,
		target_exclude_string = exclude_strings,
		)
	gen.go()

@cli.command()
@click.argument('tag')
def from_tag(tag):
	'''
	Generate file for a specified tag
	'''

	gen = HtmlGenerator(target_tags=[tag])
	gen.go()


@cli.command()
@click.argument('string')
def from_str(string):
	'''
	Generate file for a specified string
	'''

	gen = HtmlGenerator(target_string=string)
	gen.go()

@cli.command()
@click.argument('author')
def from_author(author):
	'''
	Generate file for a specified author
	'''

	gen = HtmlGenerator(target_author=author)
	gen.go()

@cli.command()
@click.argument('tag')
@click.argument('string')
def from_tag_str(tag, string):
	'''
	Generate file for a specified tag and string
	'''

	gen = HtmlGenerator(target_tags=[tag], target_string=string)
	gen.go()

if __name__ == '__main__':
	cli()


def go():
	print(sys.argv)
	if len(sys.argv) != 2:
		print("You need to pass a tag to generate content for!")
		return



if __name__ == "__main__":
	import logSetup
	logSetup.initLogging()
	print("Startup!")

	go()
