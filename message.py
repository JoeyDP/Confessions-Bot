import requests
import json

from util import *

MESSAGE_URL = "https://graph.facebook.com/v2.9/me/messages"
PARAMS = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
HEADERS = {"Content-Type": "application/json"}


class Message:
    def __init__(self):
        pass

    def getData(self):
        data = dict()
        data["recipient"] = dict()
        data["message"] = dict()
        return data

    def send(self, recipient):
        log("sending message to {}".format(recipient))

        data = self.getData()
        data["recipient"]["id"] = recipient
        jsonData = json.dumps(data)
        r = requests.post(MESSAGE_URL, params=PARAMS, headers=HEADERS, data=jsonData)
        if r.status_code != 200:
            log(r.status_code)
            log(r.text)
            return False
        return True


class TextMessage(Message):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def getData(self):
        data = super().getData()
        data["message"]["text"] = self.text
        return data


class ButtonMessage(Message):
    def __init__(self, text, *buttons):
        super().__init__()
        self.text = text

        if len(buttons) > 3:
            raise RuntimeError("ButtonMessage can only have 3 options.")
        self.buttons = list(buttons)

    def getData(self):
        data = super().getData()
        data["message"] = {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": self.text,
                    "buttons": [button.getData() for button in self.buttons]
                }
            }
        }
        return data

    def addButton(self, text, payload=None, url=None):
        if len(self.buttons) == 3:
            raise RuntimeError("ButtonMessage can only have 3 options.")
        if url is None:
            self.buttons.append(Button(text, payload))
        elif payload is None:
            self.buttons.append(URLButton(text, url))
        else:
            raise RuntimeError("Both url and payload given for button, pick one.")


class GenericMessage(Message):
    def __init__(self):
        super().__init__()
        self.elements = list()

    def getData(self):
        data = super().getData()
        data["message"] = {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "sharable": False,
                    "image_aspect_ratio": "square",
                    "elements": [element.getData() for element in self.elements]
                }
            }
        }
        return data

    def addElement(self, element):
        if len(self.elements) == 10:
            raise RuntimeError("GenericMessage can only have 10 elements.")
        self.elements.append(element)


class Element:
    def __init__(self, title, subtitle, url=None, image=None):
        self.title = title
        self.subtitle = subtitle
        self.url = url
        self.image = image
        self.buttons = list()

    def getData(self):
        data = {
            "title": self.title,
            "subtitle": self.subtitle,
        }
        if len(self.buttons) > 0:
            data["buttons"] = [button.getData() for button in self.buttons]
        if self.image:
            data["image_url"] = self.image
        if self.url:
            data["default_action"] = {
                "type": "web_url",
                "url": self.url,
            }
        return data

    def addButton(self, text, payload=None, url=None):
        if len(self.buttons) == 3:
            raise RuntimeError("Element can only have 3 options.")
        if url is None:
            self.buttons.append(Button(text, payload))
        elif payload is None:
            self.buttons.append(URLButton(text, url))
        else:
            raise RuntimeError("Both url and payload given for button, pick one.")


# def postback(func):
#     """ Decorator """
#     action = func.__name__
#     Postback.registered[action] = func
#     def wrap(**kwargs):
#         return {
#             "type": "action",
#             "action": action,
#             "args": kwargs,
#         }
#     return wrap


class Button:
    def __init__(self, text, data):
        self.text = text
        if type(data) == dict:
            self.payload = data
        else:
            raise RuntimeError("Button payload has unknown type: " + str(type(data)))

    def getData(self):
        return {
            "type": "postback",
            "title": self.text,
            "payload": json.dumps(self.payload)
        }


class URLButton:
    def __init__(self, title, url):
        self.title = title
        self.url = url

    def getData(self):
        return {
            "type": "web_url",
            "title": self.title,
            "url": self.url,
        }