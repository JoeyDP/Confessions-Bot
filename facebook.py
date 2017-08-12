import requests
import json
from urllib.parse import urljoin
from util import *
from database import Page

BASE_URL = "https://graph.facebook.com/v2.9/"


def getParams(*fields):
    return {"access_token": os.environ["PAGE_ACCESS_TOKEN"],
            "fields": ",".join(fields),
            }


