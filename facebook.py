import re
import requests
import json
from urllib.parse import urljoin
from util import *
from database import Page, Confession
from flask import url_for

BASE_URL = "https://graph.facebook.com/v2.9/"
FB_URL = "https://www.facebook.com/"
PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
APP_ID = os.environ["APP_ID"]


def makeRequest(endpoint, method="GET", access_token=None, **parameters):
    url = urljoin(BASE_URL, endpoint)
    if access_token:
        parameters['access_token'] = access_token

    if method == "GET":
        r = requests.get(url, params=parameters)
    elif method == "POST":
        r = requests.post(url, data=parameters)
    else:
        raise RuntimeError("Unknown request method: " + str(method))
    if r.status_code == 200:
        debug("Url: " + str(url))
        debug("Params: " + str(parameters))
        printCap = 640
        printText = str(r.text)[:printCap]
        if len(r.text) > printCap:
            printText += " ..."
        debug("Response: " + printText)
        return json.loads(r.text)
    else:
        log("Failed to query {}".format(url))
        log("with params: " + str(parameters))
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
    url += "?redirect_uri={}&client_id={}&scope={}".format(loginRedirectURI(sender), APP_ID, scopes)
    return url


def loginRedirectURI(sender):
    return url_for("login_redirect", sender=sender, _external=True)


class FBObject:
    def __init__(self, id):
        self.id = id
        self.token = None

    def query(self, endpoint="", fields=list(), **parameters):
        return queryFacebook(str(self.id) + "/" + endpoint, self.token, fields, **parameters)

    def post(self, endpoint="", **parameters):
        return postFacebook(str(self.id) + "/" + endpoint, self.token, **parameters)


class FBPost(FBObject):
    def __init__(self, id, text=None, token=None):
        super().__init__(id)
        self.text = text
        self.token = token

    def fetchText(self):
        response = self.query()
        log(response)
        if response:
            self.text = response.get("message")
            return self.text is not None

    def getIndex(self):
        if not self.text:
            status = self.fetchText()
            if not status:
                return None

        result = re.search(r'^\#(\d+)\s', self.text)
        if result:
            index = result.group(1)
            return int(index)

    def addComment(self, message):
        response = self.post("comments", message=message)
        if response:
            return response.get("id")


class FBPage(FBObject):
    def __init__(self, page):
        super().__init__(page.fb_id)
        self.token = page.token

    def getName(self):
        data = self.query()
        if data:
            return data.get("name")

    def getProfilePictureUrl(self):
        data = self.query("picture", redirect=False)
        if data:
            return data["data"].get("url")

    def getCoverPictureUrl(self):
        data = self.query(fields=["cover"],)
        if data:
            cover = data.get("cover")
            if cover:
                return cover.get("source")

    def getRecentPosts(self):
        data = self.query("posts", limit=10)
        if data:
            posts = list()
            for postData in data.get("data"):
                if "message" in postData:
                    post = FBPost(postData["id"], postData["message"])
                    posts.append(post)
            return posts

    def getLastConfessionIndex(self):
        posts = self.getRecentPosts()
        if posts:
            for post in posts:
                index = post.getIndex()
                if index:
                    return index

    def postConfession(self, confession):
        referencedConfession = confession.getReferencedConfession()
        if not referencedConfession:
            lastIndex = self.getLastConfessionIndex()
            debug("Last index: " + str(lastIndex))
            if lastIndex:
                index = lastIndex + 1
            else:
                index = Confession.getLastIndex(self.id) + 1

            message = "#{} {}".format(str(index), confession.text)
            response = self.post("feed", message=message)
            if response:
                return response.get("id"), index
        else:
            post = FBPost(referencedConfession.fb_id, token=self.token)
            id = post.addComment(confession.text)
            if id:
                return id, None


