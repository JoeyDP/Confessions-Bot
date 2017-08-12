import requests
import json

from util import *

from flask_babel import gettext, lazy_gettext, _, LazyString

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
        jsonData = json.dumps(data, cls=CustomEncoder)
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
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.buttons = list()

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

    def addButton(self, text, payload):
        if len(self.buttons) == 3:
            raise RuntimeError("ButtonMessage can only have 3 options.")
        self.buttons.append(Button(text, payload))


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

        # "image_url":"https://petersfancybrownhats.com/company_image.png",
        # "subtitle":"We\'ve got the right hat for everyone.",
        # "default_action": {
        #                       "type": "web_url",
        #                       "url": "https://peterssendreceiveapp.ngrok.io/view?item=103",
        #                       "messenger_extensions": true,
        #                       "webview_height_ratio": "tall",
        #                       "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
        #                   },

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

    def addButton(self, text, payload):
        if len(self.buttons) == 3:
            raise RuntimeError("Element can only have 3 options.")
        self.buttons.append(Button(text, payload))


class AttributeMessage(ButtonMessage):
    def __init__(self, attribute, text, *options, sendNext=True):
        super().__init__(text)
        if len(options) > 3:
            raise RuntimeError("ButtonMessage can only have 3 options.")
        for option in options:
            if isinstance(option, str):
                option = Option(option)
            self.buttons.append(AttributeButton(attribute, option, sendNext=sendNext))


class Option:
    def __init__(self, text, value=None):
        self.text = lazy_gettext(text)
        self.value = value
        if not self.value:
            self.value = text


class Button:
    def __init__(self, text, payload):
        self.text = text
        self.payload = payload
        if not self.payload.get("type"):
            self.payload["type"] = "action"

    def getData(self):
        return {
            "type": "postback",
            "title": self.text,
            "payload": json.dumps(self.payload, cls=CustomEncoder)
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


class AttributeButton(Button):
    def __init__(self, attribute, option, sendNext=True):
        super().__init__(
            option.text,
            {
                "type": "attribute",
                "attribute": attribute,
                "value": option.value,
                "sendNext": sendNext,
            }
        )


class AttributeElement(Element):
    def __init__(self, attribute, name, question, *options, sendNext=True):
        super().__init__(
            name,
            question
        )
        if len(options) > 3:
            raise RuntimeError("ButtonMessage can only have 3 options.")
        for option in options:
            if isinstance(option, str):
                option = Option(option)
            self.buttons.append(AttributeButton(attribute, option, sendNext=sendNext))


class ChatMessage(ButtonMessage):
    def __init__(self, sender, message):
        super().__init__("{}: {}".format(sender.fullName, message))
        self.addButton(gettext("Respond"), {"type": "action",
                                                                          "action": "startChat",
                                                                          "contact": sender.fbID,
                                                                          "info": False,
                                                                          })
