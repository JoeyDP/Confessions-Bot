import requests
import json
from urllib.parse import urljoin
from util import *
from database import Person

BASE_URL = "https://graph.facebook.com/v2.9/"


def getParams(*fields):
    return {"access_token": os.environ["PAGE_ACCESS_TOKEN"],
            "fields": ",".join(fields),
            }


def getProfile(fbID):
    url = urljoin(BASE_URL, str(fbID))
    r = requests.get(url, params=getParams("gender", "first_name", "last_name", "locale"))
    if r.status_code == 200:
        return json.loads(r.text)
    else:
        log("Failed to query profile for {}".format(fbID))


def getProfieImage(fbID):
    url = urljoin(BASE_URL, str(fbID))
    r = requests.get(url, params=getParams("profile_pic"))
    if r.status_code == 200:
        data = json.loads(r.text)
        return data.get("profile_pic")
    else:
        log("Failed to query profile pic for {}".format(fbID))


def getAppID(fbID):
    url = urljoin(BASE_URL, str(fbID))
    r = requests.get(url, params=getParams("ids_for_apps"))
    if r.status_code == 200:
        data = json.loads(r.text)
        if data.get("ids_for_apps"):
            appID = data["ids_for_apps"]["data"][0]["id"]
            return appID
    else:
        log("Failed to query app_id for {}".format(fbID))
        log(r.text)


def initPerson(fbID):
    person = Person(fbID=fbID)
    data = getProfile(fbID)
    if data:
        log(data, debug=True)
        person.firstName = data.get("first_name")
        person.lastName = data.get("last_name")
        person.locale = data.get("locale")
        gender = data.get("gender")
        if gender:
            person.gender = {"male": "Male", "female": "Female"}.get(gender)

    person.add()
    return person


