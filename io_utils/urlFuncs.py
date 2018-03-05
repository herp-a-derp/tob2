
import re
import urllib.parse
import unshortenit

# All tags you need to look into to do link canonization
# source: http://stackoverflow.com/q/2725156/414272
# "These aren't necessarily simple URLs ..."
urlContainingTargets = [
	(False, 'a',          'href'),
	(False, 'applet',     'codebase'),
	(False, 'area',       'href'),
	(False, 'base',       'href'),
	(False, 'blockquote', 'cite'),
	(False, 'body',       'background'),
	(False, 'del',        'cite'),
	(False, 'form',       'action'),
	(False, 'frame',      'longdesc'),
	(False, 'frame',      'src'),
	(False, 'head',       'profile'),
	(False, 'iframe',     'longdesc'),
	(False, 'iframe',     'src'),
	(False, 'input',      'src'),
	(False, 'input',      'usemap'),
	(False, 'ins',        'cite'),
	(False, 'link',       'href'),
	(False, 'object',     'classid'),
	(False, 'object',     'codebase'),
	(False, 'object',     'data'),
	(False, 'object',     'usemap'),
	(False, 'q',          'cite'),
	(False, 'script',     'src'),
	(False, 'audio',      'src'),
	(False, 'button',     'formaction'),
	(False, 'command',    'icon'),
	(False, 'embed',      'src'),
	(False, 'html',       'manifest'),
	(False, 'input',      'formaction'),
	(False, 'source',     'src'),
	(False, 'video',      'poster'),
	(False, 'video',      'src'),
	(True,  'img',        'longdesc'),
	(True,  'img',        'src'),
	(True,  'img',        'usemap'),
]




def trimGDocUrl(rawUrl):
	# if "docs.google.com" in rawUrl:
	# 	print("Trimming URL: ", rawUrl)

	url = rawUrl.split("#")[0]


	urlParam = urllib.parse.urlparse(url)

	# Short circuit so we don't munge non-google URLs
	if not 'google.com' in urlParam.netloc:
		return rawUrl

	qArr = urllib.parse.parse_qs(urlParam.query)
	if urlParam.query and 'google.com' in urlParam.netloc:
		qArr.pop('usp', None)
		qArr.pop('pli', None)
		qArr.pop('authuser', None)
		if qArr:
			queryStr = urllib.parse.urlencode(qArr, doseq=True)
		else:
			queryStr = ''
	else:
		# Unfortunately, parsing and re-encoding can reorder the parameters in the URL.
		# Since there is some idiot-checking to see if the url has changed if it /shouldn't/
		# and reodering would break that, we don't just use urlencode by default, unless it's
		# actually changed anything.
		queryStr = urlParam.query

	# This trims off any fragment, and re-adds the query-string(if present) with any google keys removed
	# print(urlParam, (queryStr, ''))
	params = urlParam[:4] + (queryStr, '')
	# print("Params", params)
	url = urllib.parse.urlunparse(params)

	# If the url has 'preview/' on the end, chop that off (but only for google content)
	if 'docs.google.com' in urlParam.netloc:
		strip = [
			"/preview/",
			"/preview",
			"/edit",
			"/view",
			"/mobilebasic",
			"/mobilebasic?viewopt=127",
			"?embedded=true",
			"?embedded=false",
			]

		gdocBaseRe = re.compile(r'(https?://docs.google.com/document/d/[-_0-9a-zA-Z]+(?:/pub)?)(.*)$')
		simpleCheck = gdocBaseRe.search(url)
		if simpleCheck:
			if any([item in simpleCheck.group(2) for item in strip]):
				url = simpleCheck.group(1)

		for ending in strip:
			if url.endswith(ending):
				url = url[:-len(ending)]

	# if "docs.google.com" in url:
	# 	print("Trimmed URL: ", url)

	# if url.endswith("/pub"):
	# 	url = url[:-3]


	return url

def isGdocUrl(url):
	gdocBaseRe = re.compile(r'(https?://docs.google.com/document/d/[-_0-9a-zA-Z]+)')
	simpleCheck = gdocBaseRe.search(url)
	if simpleCheck and not url.endswith("/pub"):
		# return True, simpleCheck.group(1)
		return True, trimGDocUrl(url)

	return False, url


def isGFileUrl(url):

	gFileBaseRe = re.compile(r'(https?://docs.google.com/file/d/[-_0-9a-zA-Z]+)')
	simpleCheck = gFileBaseRe.search(url)
	if simpleCheck and not url.endswith("/pub"):
		return True, trimGDocUrl(url)

	scheme, netloc, path, params, query, fragment = urllib.parse.urlparse(url)

	if netloc == 'drive.google.com' and path == '/folderview':
		query = urllib.parse.parse_qsl(query)
		query = [item for item in query if item[0] != "usp"]
		query.sort()
		query = urllib.parse.urlencode(query)

		url = urllib.parse.urlunparse((scheme, netloc, path, params, query, fragment))
		return True, url

	return False, url


##############################################################################################################
##############################################################################################################
##############################################################################################################
##############################################################################################################


def cleanUrl(url):
	# Fucking tumblr redirects.
	if url.startswith("https://www.tumblr.com/login"):
		return None

	url, status = unshortenit.unshorten_only(url)
	#assert (status == 200)

	return url


##############################################################################################################
##############################################################################################################
##############################################################################################################
##############################################################################################################

def rebaseUrl(url, base):
	"""Rebase one url according to base"""

	parsed = urllib.parse.urlparse(url)
	if parsed.scheme == '' or parsed.netloc == '':
		return urllib.parse.urljoin(base, url)
	else:
		return url

def canonizeUrls(soup, pageUrl):
	# print("Canonizing for page: ", pageUrl)
	for (dummy_isimg, tag, attr) in urlContainingTargets:
		for link in soup.findAll(tag):
			try:
				url = link[attr]
			except KeyError:
				pass
			else:
				link[attr] = rebaseUrl(url, pageUrl)

	return soup

def extractUrls(soup, pageUrl, truncate_fragment=False):
	# print("Canonizing for page: ", pageUrl)
	urls = set()
	for (dummy_isimg, tag, attr) in urlContainingTargets:
		for link in soup.findAll(tag):
			try:
				url = link[attr]
			except KeyError:
				pass
			else:

				if url.startswith("javascript"):
					continue
				if url.startswith("data:"):
					continue
				if url.startswith("ios-app:"):
					continue
				if url.startswith("clsid:"):
					continue
				if url.startswith("mailto:"):
					continue
				fixed = rebaseUrl(url, pageUrl)
				assert fixed.startswith("http"), "Wat?: '%s', '%s', '%s'" % (url, pageUrl, fixed)
				urls.add(fixed)
	if truncate_fragment:
		ret = set()
		for url in urls:
			split = urllib.parse.urlsplit(url)
			if split.fragment:
				fixed = urllib.parse.urlunsplit(split[:4] + ("", ) + split[5:])
				# print("Fixed: ", fixed)
				ret.add(fixed)
			else:
				ret.add(url)
		return ret
	return urls


def hasDuplicatePathSegments(url):

		parsed = urllib.parse.urlsplit(url)
		netloc = parsed.netloc
		if not netloc:
			print("Wat? No netloc for URL: %s" % url)
			return True

		pathchunks = parsed.path.split("/")
		pathchunks = [chunk for chunk in pathchunks if chunk]
		querychunks = parsed.path.split("/")
		querychunks = [chunk for chunk in querychunks if chunk]

		# http://www.spcnet.tv/forums/showthread.php/21185-mobile-suit-gundam-the-second-century-(part-2-the-second-century)/images/icons/images/misc/showthread.php/21185-Mobile-Suit-Gundam-The-Second-Century-(Part-2-The-Second-Century)/page10
		if netloc == 'www.spcnet.tv' or netloc == 'www.eugenewoodbury.com':
			# Yeah, special case stuff because spcnet is garbage.

			# Block instances where there are multiple known-bad segments.
			disallow_multiple = [
				'images',
				'avatars',
				'smilies',
				]
			if any([pathchunks.count(i) > 1 for i in disallow_multiple]):
				return True

			# Block a url where multiple instances of the php page is present.
			disalow_several = [
				'cron.php',
				'external.php',
				'forumdisplay.php',
				'member.php',
				'register.php',
				'showthread.php',

				'angel',
				'biblio',
				'essays',
				'foxwolf',
				'image',
				'kasho',
				'paradise',
				'path',
				'serpent',
				'wind',
			]

			if sum([pathchunks.count(i) for i in disalow_several]) > 1:
				return True

		if 'www.wastedtalent.ca' in url:
			bulkchunks = url.split("/")
			bulkchunks = [chunk for chunk in bulkchunks if chunk]
			bduplicates = list(set([(i, bulkchunks.count(i)) for i in bulkchunks if bulkchunks.count(i) > 1]))

			if any([cnt > 3 for (item, cnt) in bduplicates]):
				print("Bulk duplicates issue: %s - %s" % (url, (pathchunks, set(pathchunks))))
				return True




		if len(set(pathchunks)) == len(pathchunks):
			return False

		duplicates = list(set([(i, pathchunks.count(i)) for i in pathchunks if pathchunks.count(i) > 1]))
		qduplicates = list(set([(i, querychunks.count(i)) for i in querychunks if querychunks.count(i) > 1]))

		if any([cnt > 3 for (item, cnt) in duplicates]):
			print("Pathchunks issue: %s - %s" % (url, (pathchunks, set(pathchunks))))
			return True
		if any([cnt > 3 for (item, cnt) in qduplicates]):
			print("Query chunks issue: %s - %s" % (url, (pathchunks, set(pathchunks))))
			return True
		if len(duplicates) > 3:
			print("Pathchunks issue: %s - %s" % (url, (pathchunks, set(pathchunks))))
			return True

		return False



def urlClean(url):
	assert url != None
	# Google docs can be accessed with or without the '/preview' postfix
	# We want to remove this if it's present, so we don't duplicate content.
	url = trimGDocUrl(url)
	url = cleanUrl(url)

	while True:
		url2 = urllib.parse.unquote(url)
		url2 = url2.split("#")[0]
		if url2 == url:
			break
		url = url2

	# Clean off whitespace.
	url = url.strip()

	return url

def getNetLoc(url):
	parsed = urllib.parse.urlparse(url)
	if not parsed.netloc:
		raise ValueError("No netloc in url: '{}'".format(url))
	return parsed.netloc

if __name__ == "__main__":

	print(isGFileUrl('https://drive.google.com/folderview?id=0B_mXfd95yvDfQWQ1ajNWZTJFRkk&usp=drive_web'))
	print(urlClean('http://inmydaydreams.com/?p=6128&share=tumblr'))
	print(urlClean('http://inmydaydreams.com/?p=6091&share=tumblr'))
