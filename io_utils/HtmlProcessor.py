
import bs4
import copy
import re
import time
import webcolors
import urllib.parse
import markdown
import tinycss2
import logging
import WebRequest

from . import urlFuncs as urlFuncs


########################################################################################################################
#
#	##     ##    ###    #### ##    ##     ######  ##          ###     ######   ######
#	###   ###   ## ##    ##  ###   ##    ##    ## ##         ## ##   ##    ## ##    ##
#	#### ####  ##   ##   ##  ####  ##    ##       ##        ##   ##  ##       ##
#	## ### ## ##     ##  ##  ## ## ##    ##       ##       ##     ##  ######   ######
#	##     ## #########  ##  ##  ####    ##       ##       #########       ##       ##
#	##     ## ##     ##  ##  ##   ###    ##    ## ##       ##     ## ##    ## ##    ##
#	##     ## ##     ## #### ##    ##     ######  ######## ##     ##  ######   ######
#
########################################################################################################################




class HtmlPageProcessor():



	loggerPath = "Main.Text.HtmlProc"

	def __init__(self, pageUrl, pgContent):
		self.log = logging.getLogger(self.loggerPath)

		self.log.info("HtmlProc processing HTML content.")

		self.pageUrl = pageUrl
		self.content = pgContent

		self._decompose       = []
		self._decomposeBefore = []
		self.stripTitle       = []
		self.destyle          = []
		self.preserveAttrs    = []
		self.decompose_svg    = False


	def processNewUrl(self, url, baseUrl=None, istext=True):
		return url

	def relink(self, soup):
		return soup

	def processImageLink(self, url, baseUrl):

		# Skip tags with `img src=""`.
		# No idea why they're there, but they are
		if not url:
			return

		# # Filter by domain
		# if not self.allImages and not any([base in url for base in self._fileDomains]):
		# 	return

		# # and by blocked words
		# hadbad = False
		# for badword in self._badwords:
		# 	if badword.lower() in url.lower():
		# 		hadbad = True
		# if hadbad:
		# 	return


		url = urlFuncs.urlClean(url)

		return self.processNewUrl(url, baseUrl=baseUrl, istext=False)

	def extractImages(self, soup, baseUrl):
		ret = []
		for imtag in soup.find_all("img"):
						# Skip empty anchor tags
			try:
				url = imtag["src"]
			except KeyError:
				continue

			item = self.processImageLink(url, baseUrl)
			if item:
				ret.append(item)
		return ret


	def destyleItems(self, soup):
		'''
		using the set of search 2-tuples in `destyle`,
		walk the parse tree and decompose the attributes of any matching
		element.
		'''
		for tagtype, attrs in self.destyle:
			for found in soup.find_all(tagtype, attrs=attrs):
				for key in list(found.attrs):
					del found.attrs[key]

		for fonttag in soup.find_all("font"):
			if not fonttag.get_text(strip=True):
				fonttag.decompose()
			else:
				fonttag.unwrap()

		for p_tag in soup.find_all("p"):
			if not p_tag.get_text(strip=True):
				p_tag.decompose()
			elif "style" in p_tag.attrs and p_tag.attrs['style'].strip() == "":
				p_tag.attrs.pop('style')
			elif "style" in p_tag.attrs and 'font-family' in p_tag.attrs['style']:
				p_tag.attrs.pop('style')

		for span_tag in soup.find_all("span"):
			if not span_tag.get_text(strip=True):
				span_tag.decompose()
			elif "style" in span_tag.attrs and span_tag.attrs['style'].strip() == "":
				span_tag.attrs.pop('style')
			else:
				span_tag.unwrap()

		return soup

	def decomposeItems(self, soup, toDecompose):
		if not soup:
			print("Soup is false? Wat?")

		# print("Decomposing", toDecompose)
		# Decompose all the parts we don't want

		# Use a custom function so we only walk the tree once.
		def searchFunc(tag):
			for candidate in toDecompose:
				matches = []
				for key, value in candidate.items():
					haskey = tag.get(key)
					if haskey:
						vallist = tag.get(key)
						if isinstance(vallist, str):
							vallist = [vallist, ]

						hasval = any([sattr.lower() == value.lower() for sattr in vallist if sattr])
						matches.append(hasval)
				match = any(matches)
				if match:
					return True
			return False


		have = soup.find_all(searchFunc)

		for instance in have:
			# print("Need to decompose for ", key)
			# So.... yeah. At least one blogspot site has EVERY class used in the
			# <body> tag, for no coherent reason. Therefore, *never* decompose the <body>
			# tag, even if it has a bad class in it.
			if instance.name == 'body':
				continue

			instance.decompose()

		return soup

	def decomposeAdditional(self, soup):


		# Clear out all the iframes
		for instance in soup.find_all('iframe'):
			instance.decompose()

		# Clean out any local stylesheets
		for instance in soup.find_all('style', attrs={"type" : "text/css"}):
			instance.decompose()

		# Even if not explicitly tagged as css
		for instance in soup.find_all('style'):
			instance.decompose()

		# And all remote scripts
		for item in soup.find_all("script"):
			item.decompose()

		# Link tags
		for item in soup.find_all("link"):
			item.decompose()

		# Meta tags
		for item in soup.find_all("meta"):
			item.decompose()

		# Comments
		for item in soup.findAll(text=lambda text:isinstance(text, bs4.Comment)):
			item.extract()

		if self.decompose_svg:
			for item in soup.find_all("svg"):
				item.decompose()

		return soup


	def fixCss(self, soup):
		'''
		So, because the color scheme of our interface can vary from the original, we need to fix any cases
		of white text. However, I want to preserve *most* of the color information.
		Therefore, we look at all the inline CSS, and just patch where needed.
		'''


		# Match the CSS ASCII color classes
		hexr = re.compile('((?:[a-fA-F0-9]{6})|(?:[a-fA-F0-9]{3}))')

		def clamp_hash_token(intok, high):
			old = hexr.findall(intok.value)
			for match in old:
				color = webcolors.hex_to_rgb("#"+match)
				mean = sum(color)/len(color)

				if high:
					if mean > 150:
						color = tuple((max(255-cval, 0) for cval in color))
						new = webcolors.rgb_to_hex(color)
						intok.value = intok.value.replace(match, new)
				else:
					if mean < 100:
						color = tuple((min(cval, 100) for cval in color))
						new = webcolors.rgb_to_hex(color).replace("#", "")
						intok.value = intok.value.replace(match, new)
			return intok

		def clamp_css_color(toks, high=True):
			toks = [tok for tok in toks if tok.type != 'whitespace']

			for tok in toks:
				if tok.type == 'hash':
					clamp_hash_token(tok, high)
				if tok.type == 'string':
					tok.value = ""

			return toks

		hascss = soup.find_all(True, attrs={"style" : True})


		initial_keys = [
				'font',
				'font-family'
		]

		empty_keys = [
				'font-size',
				'width',
				'height',
				'display',
				'max-width',
				'max-height',
				'background-image',
				'margin-bottom',
				'line-height',
				'vertical-align',
				'white-space',
				'font-size',
				'box-sizing',
				'cursor',
				'display',
				'height',
				'left',
				'margin-bottom',
				'margin-right',
				'margin',
				'object-fit',
				'overflow',
				'position',
				'right',
				'text-align',
				'top',
				'visibility',
				'width',
				'z-index',

		]

		foreground_color_keys = [
			'color',
		]
		background_color_keys = [
			'background',
			'background-color',
		]

		for item in hascss:
			if item['style']:

				try:
					parsed_style = tinycss2.parse_declaration_list(item['style'])

					for style_chunk in parsed_style:
						if style_chunk.type == 'declaration':

							if any([dec_str == style_chunk.name for dec_str in initial_keys]):
								style_chunk.value = [tinycss2.ast.IdentToken(1, 1, "Sans-Serif")]
							if any([dec_str == style_chunk.name for dec_str in empty_keys]):
								style_chunk.value = []

							if any([dec_str == style_chunk.name for dec_str in foreground_color_keys]):
								style_chunk.value = clamp_css_color(style_chunk.value)
							if any([dec_str == style_chunk.name for dec_str in background_color_keys]):
								style_chunk.value = clamp_css_color(style_chunk.value, high=False)

							# Force overflow to be visible
							if style_chunk.name == "overflow":
								style_chunk.value = [tinycss2.ast.IdentToken(1, 1, "visible")]

					parsed_style = [chunk for chunk in parsed_style if chunk.value]

					item['style'] = tinycss2.serialize(parsed_style)

				except AttributeError:
					# If the parser encountered an error, it'll produce 'ParseError' tokens without
					# the 'value' attribute. This produces attribute errors.
					# If the style is fucked, just clobber it.
					item['style'] = ""

		return soup


	# Methods to allow the child-class to modify the content at various points.
	def extractTitle(self, srcSoup, url):

		if srcSoup.title:
			return srcSoup.title.get_text().strip()

		return "'%s' has no title!" % url

	def cleanHtmlPage(self, soup, url=None):

		soup = self.relink(soup)

		title = self.extractTitle(soup, url)


		if isinstance(self.stripTitle, (list, set)):
			for stripTitle in self.stripTitle:
				title = title.replace(stripTitle, "")
		else:
			title = title.replace(self.stripTitle, "")

		title = title.strip()

		if soup.head:
			soup.head.decompose()

		# Since the content we're extracting will be embedded into another page, we want to
		# strip out the <body> and <html> tags. `unwrap()`  replaces the soup with the contents of the
		# tag it's called on. We end up with just the contents of the <body> tag.
		while soup.body:
			# print("Unwrapping body tag")
			soup.body.unwrap()

		while soup.html:
			# print("Unwrapping html tag")
			soup.html.unwrap()

		for item in soup.children:
			if isinstance(item, bs4.Doctype):
				# print("decomposing doctype")
				item.extract()

		contents = soup.prettify()

		return title, contents



	def removeClasses(self, soup):
		validattrs = [
			'href',
			'src',
			'style',
			'cellspacing',
			'cellpadding',
			'border',
			'colspan',
			'onclick',
			'type',
			'value',
		]

		for item in [item for item in soup.find_all(True) if item]:
			tmp_valid = validattrs[:]
			clean = True
			for name, attr in self.preserveAttrs:
				if item.name == name:
					if attr:
						tmp_valid.append(attr)

					else:
						# Preserve all attributes
						clean = False
			if clean and item.attrs:

				for attr, value in list(item.attrs.items()):
					if attr == 'style' and 'float' in value:
						del item[attr]
					elif attr not in tmp_valid:
						del item[attr]

			# Set the class of tables set to have no borders to the no-border css class for later rendering.
			if item.name == "table" and item.has_attr("border") and item['border'] == "0":
				if not item.has_attr("class"):
					item['class'] = ""
				item['class'] += " noborder"


		return soup


	# Miscellaneous spot-fixes for specific sites.
	def prePatch(self, url, soup):
		return soup


	# Miscellaneous spot-fixes for specific sites.
	def spotPatch(self, soup):

		# Replace <pre> tags on wattpad.
		# wp_div = soup.find_all('div', class_="panel-reading")
		# for item in wp_div:
		# Fukkit, just nuke them in general
		for pre in soup.find_all("pre"):
			pre.name = "div"
			contentstr = pre.encode_contents().decode("utf-8")

			# Don't markdown huge documents.
			if len(contentstr) > 1024 * 500:
				continue
			contentstr = contentstr.replace("	", "\n\n")

			formatted = markdown.markdown(contentstr, extensions=["linkify"])
			formatted = WebRequest.as_soup(formatted)
			if formatted.find("html"):
				formatted.html.unwrap()
				formatted.body.unwrap()
				pre.replace_with(formatted)
			# print(pre)
		return soup




	def preprocessBody(self, soup):
		for link in soup.find_all("a"):
			if link.has_attr("href"):
				if "javascript:if(confirm(" in link['href']:
					qs = urllib.parse.urlsplit(link['href']).query
					link['href'] = "/viewstory.php?{}".format(qs)

		# for pre_segment in soup.find_all("pre"):
		# 	print("Pre segment:", pre_segment)
		# 				contM = markdown.markdown(contC, extensions=["toc"])
		return soup

	def postprocessBody(self, soup):
		return soup

	# Process a plain HTML page.
	# This call does a set of operations to permute and clean a HTML page.
	#
	# First, it decomposes all tags with attributes dictated in the `_decomposeBefore` class variable
	# it then canonizes all the URLs on the page, extracts all the URLs from the page,
	# then decomposes all the tags in the `decompose` class variable, feeds the content through
	# readability, and finally saves the processed HTML into the database
	def extractContent(self):
		self.log.info("Processing '%s' as HTML (size: %s).", self.pageUrl, len(self.content))
		assert self.content
		# print(type(self.content))

		badxmlprefix = '<?xml version="1.0"?>'
		if self.content.strip().lower().startswith(badxmlprefix):
			self.content = self.content[len(badxmlprefix):]


		soup = WebRequest.as_soup(self.content)
		# try:
		# 	soup = WebRequest.as_soup(self.content)
		# except AttributeError as e:
		# 	with open("badpage %s.html" % time.time(), "w") as fp:
		# 		fp.write(self.content)
		# 		raise e


		soup = self.prePatch(self.pageUrl, soup)
		soup = self.spotPatch(soup)

		# Allow child-class hooking
		soup = self.preprocessBody(soup)

		# Clear out any particularly obnoxious content before doing any parsing.
		soup = self.decomposeItems(soup, self._decomposeBefore)

		# Make all the page URLs fully qualified, so they're unambiguous
		soup = urlFuncs.canonizeUrls(soup, self.pageUrl)

		# Do the later cleanup to prep the content for local rendering.
		soup = self.decomposeItems(soup, self._decompose)

		soup = self.decomposeAdditional(soup)
		soup = self.destyleItems(soup)

		# Allow child-class hooking
		soup = self.postprocessBody(soup)

		soup = self.removeClasses(soup)

		soup = self.fixCss(soup)

		# Process page with readability, extract title.
		pgTitle, pgBody = self.cleanHtmlPage(soup, url=self.pageUrl)

		ret = {}

		ret['title']      = pgTitle
		ret['contents']   = pgBody


		return ret

		# self.updateDbEntry(url=url, title=pgTitle, contents=pgBody, mimetype=mimeType, dlstate=2)

