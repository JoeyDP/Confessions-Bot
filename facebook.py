import requests
import json
from urllib.parse import urljoin
from util import *
from database import Page

BASE_URL = "https://graph.facebook.com/v2.9/"
FB_URL = "https://www.facebook.com/"

def getParams(*fields):
    return {"access_token": os.environ["PAGE_ACCESS_TOKEN"],
            "fields": ",".join(fields),
            }


def getClientTokenFromCode(code):
    pass
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
