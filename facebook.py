import re
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


def makeRequest(endpoint, method="GET", **parameters):
    url = urljoin(BASE_URL, endpoint)
    if method == "GET":
        r = requests.get(url, params=parameters)
    elif method == "POST":
        r = requests.post(url, data=parameters)
    else:
        raise RuntimeError("Unknown request method: " + str(method))
    if r.status_code == 200:
        debug("Url: " + str(url))
        debug("Response: " + str(r.text))
        return json.loads(r.text)
    else:
        log("Failed to query {}".format(url))
        log(r.text)
        return None


def queryFacebook(endpoint, accessToken, fields, **parameters):
    return makeRequest(endpoint, access_token=accessToken, fields=",".join(fields), **parameters)


def postFacebook(endpoint, accessToken, **parameters):
    return makeRequest(endpoint, method="POST", access_token=accessToken, **parameters)


def getClientTokenFromCode(sender, code):
    redirect = loginRedirectURI(sender)
    data = makeRequest("oauth/access_token", client_id=APP_ID, redirect_uri=redirect, client_secret=CLIENT_SECRET, code=code)
    if not data:
        return None

    return data.get("access_token")


def listManagedPages(clientToken):
    # TODO: paging if needed by someone
    response = queryFacebook("me/accounts", clientToken, ["access_token", "name", "id"])
    if response:
        return response.get("data")
    return None


def getPageProfilePictureUrl(pageID, clientToken):
    response = queryFacebook(str(pageID) + "/picture", clientToken, [], redirect="false")
    if response:
        return response["data"].get("url")


def objectUrl(pageID):
    return urljoin(FB_URL, str(pageID))

pageUrl = objectUrl
postUrl = objectUrl

def loginUrl(sender, scopes):
    url = "https://www.facebook.com/v2.9/dialog/oauth"
    url += "?display=popup&redirect_uri={}&client_id={}&scope={}".format(loginRedirectURI(sender), APP_ID, scopes)
    return url

def loginRedirectURI(sender):
    return url_for("login_redirect", sender=sender, _external=True)


class FBPost:
    def __init__(self, id, text):
        self.id = id
        self.text = text

class FBPage:
    def __init__(self, page):
        self._page = page
        self.id = page.fb_id
        self.token = page.token

    def query(self, endpoint="", fields=list(), **parameters):
        return queryFacebook(str(self.id) + "/" + endpoint, self.token, fields, **parameters)

    def post(self, endpoint="", **parameters):
        return postFacebook(str(self.id) + "/" + endpoint, self.token, **parameters)

    def getName(self):
        data = self.query()
        if data:
            return data.get("name")

    def getRecentPosts(self):
        data = self.query("feed")
        if data:
            posts = list()
            for postData in data.get("data"):
                debug(postData)
                if "message" in postData:
                    post = FBPost(postData["id"], postData["message"])
                    posts.append(post)
            posts.reverse()
            return posts

    def getLastConfessionIndex(self):
        posts = self.getRecentPosts()
        if posts:
            for post in posts:
                result = re.search(r'^\#(\d+)\s', post.text)
                if result:
                    index = result.group(1)
                    return int(index)

    def postConfession(self, index, text):
        message = "#{} {}".format(str(index), text)
        response = self.post("feed", message=message)
        if response:
            data = response.get("data")
            if data:
                return data.get("id")
