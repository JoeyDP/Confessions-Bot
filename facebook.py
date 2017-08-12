import requests
import json
from urllib.parse import urljoin
from util import *
from database import Page

BASE_URL = "https://graph.facebook.com/v2.9/"
FB_URL = "https://www.facebook.com/"
PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]


def getParams(accessToken, fields):
    return {"access_token": accessToken,
            "fields": ",".join(fields),
            }


def makeRequest(endpoint, accessToken, fields):
    url = urljoin(BASE_URL, endpoint)
    r = requests.get(url, params=getParams(accessToken, fields))
    if r.status_code == 200:
        return json.loads(r.text)
    else:
        log("Failed to query {}".format(url))
        log(r.text)


def getClientTokenFromCode(code):
    data = makeRequest("access_token")
    # https://graph.facebook.com/v2.10/oauth/access_token?
    # client_id={app-id}
    # &redirect_uri={redirect-uri}
    # &client_secret={app-secret}
    # &code={code-parameter}


def listManagedPages(clientToken):
    pass
    # /me/accounts?fields=...


def pageUrl(pageID):
    return urljoin(FB_URL, str(pageID))
