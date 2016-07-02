
from flask import jsonify
from flask import render_template
from flask import request
from flask_login import current_user
import wtforms_json
from app import csrf

from app import app

from . import api_handlers
from . import api_handlers_admin
# from . import api_handlers_anon

from app.api_common import getResponse
import traceback

wtforms_json.init()

LOGIN_REQ =  """
API Calls can only be made by a logged in user!<br>
<br>
If you are not logged in, please log in.<br>
<br>
If you do not have an account, you must create one in order to edit things or watch series."""


@csrf.exempt
@app.route('/api', methods=['POST'])
def handleApiPost():
	if not request.json:
		# print("Non-JSON request!")
		js = {
			"error"   : True,
			"message" : "This endpoint only accepts JSON POST requests."
		}
		resp = jsonify(js)
		resp.status_code = 200
		resp.mimetype="application/json"
		return resp

	ret = dispatchApiCall(request.json)

	assert "error"   in ret, ("API Response missing status code!")
	assert "message" in ret, ("API Response missing status message!")

	resp = jsonify(ret)
	resp.status_code = 200
	resp.mimetype="application/json"
	return resp

@csrf.exempt
@app.route('/api', methods=['GET'])
def handleApiGet():
	return render_template('not-implemented-yet.html', message="API Endpoint requires a POST request.")



# call_name : (function_to_call, auth_required_bool, csrf_protect)
# CSRF protection is not needed if
DISPATCH_TABLE = {


	# Logged in stuff
	'add-story'              : (api_handlers.addStory,                          False,  False),

	# Admin API bits
	# 'merge-id'                  : (api_handlers_admin.mergeSeriesItems,          True,  False),
	# 'merge-group'               : (api_handlers_admin.mergeGroupItems,           True,  False),
	'delete-story'              : (api_handlers_admin.deleteStory,              True,  False),
	# 'release-ctrl'              : (api_handlers_admin.alterReleaseItem,          True,  False),
	# 'delete-auto-releases'      : (api_handlers_admin.deleteAutoReleases,        True,  False),

	# 'flatten-series-by-url'     : (api_handlers_admin.flatten_series_by_url,     True,  False),
	# 'delete-duplicate-releases' : (api_handlers_admin.delete_duplicate_releases, True,  False),
	'fix-escapes'               : (api_handlers_admin.fix_escaped_quotes,        True,  False),
	'clean-tags'                : (api_handlers_admin.clean_tags,                True,  False),

	# 'delete-group'              : (api_handlers_admin.deleteGroup,               True,  False),
	# 'delete-auto-from-group'    : (api_handlers_admin.deleteGroupAutoReleases,   True,  False),

}

def dispatchApiCall(reqJson):
	print("Json request:", reqJson)
	if not "mode" in reqJson:
		print("API JSON Request without mode!")
		return getResponse("No mode in API Request!", error=True)

	mode = reqJson["mode"]
	if not mode in DISPATCH_TABLE:
		print("Invalid mode in request: '{mode}'".format(mode=mode))
		return getResponse("Invalid mode in API Request ({mode})!".format(mode=mode), error=True)

	dispatch_method, auth_required, csrf_required = DISPATCH_TABLE[mode]
	try:
		if csrf_required:
			csrf.protect()

		if auth_required and not current_user.is_authenticated():
			return getResponse(LOGIN_REQ, error=True)

		else:
			ret = dispatch_method(reqJson)

	except AssertionError as e:
		traceback.print_exc()
		print(reqJson)
		return getResponse("Error processing API request: '%s'!" % e, error=True)



	return ret


