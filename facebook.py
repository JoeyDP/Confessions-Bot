import requests
import json
from urllib.parse import urljoin
from util import *
from database import Page
from flask import url_for

BASE_URL = "https://graph.facebook.com/v2.9/"
FB_URL = "https://www.facebook.com/"
PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
APP_ID = os.environ["APP_ID"]


def makeRequest(endpoint, **parameters):
    url = urljoin(BASE_URL, endpoint)
    r = requests.get(url, params=parameters)
    if r.status_code == 200:
        return json.loads(r.text)
    else:
        log("Failed to query {}".format(url))
        log(r.text)
        return None


def queryFacebook(endpoint, accessToken, fields):
    return makeRequest(endpoint, access_token=accessToken, fields=",".join(fields))


def getClientTokenFromCode(sender, code):
    redirect = loginRedirectURI(sender)
    data = makeRequest("oauth/access_token", client_id=APP_ID, redirect_uri=redirect, client_secret=CLIENT_SECRET, code=code)
    if not data:
        return None

    return data.get("access_token")


def listManagedPages(clientToken):
    # TODO: paging
    response = queryFacebook("me/accounts", clientToken, ["access_token", "name", "id"])
    debug("pages data:" + str(response))
    if response:
        return response.get("data")
    return None


def getPageProfilePictureUrl(pageID, clientToken):
    response = queryFacebook(str(pageID) + "picture", clientToken, ["url"])
    if response:
        return response.get("url")


def pageUrl(pageID):
    return urljoin(FB_URL, str(pageID))


def loginUrl(sender, scopes):
    url = "https://www.facebook.com/v2.9/dialog/oauth"
    url += "?display=popup&redirect_uri={}&client_id={}&scope={}".format(loginRedirectURI(sender), APP_ID, scopes)
    return url


def loginRedirectURI(sender):
    return url_for("login_redirect", sender=sender, _external=True)