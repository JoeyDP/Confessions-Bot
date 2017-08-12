from urllib.parse import urljoin

from message import *
from database import *
import facebook
import profile
from flask import url_for


URL = os.environ["URL"]
ADMIN_SENDER_ID = os.environ.get("ADMIN_SENDER_ID")
DISABLED = os.environ.get("DISABLED", 0) == '1'


def receivedMessage(sender, recipient, message):
    log("Received message \"{}\" from {}".format(message, sender))
    if sender == ADMIN_SENDER_ID:
        if adminMessage(sender, message):
            return

    if DISABLED:
        response = TextMessage("I am temporarily offline. Follow the page for updates!")
        response.send(sender)
        if len(message) > 5 and ADMIN_SENDER_ID:
            report = TextMessage("{}:\n\"{}\"".format(sender, message))
            report.send(ADMIN_SENDER_ID)
        return

    test = ButtonMessage("This is a test", Button("page 6666", managePage(pageID=6666)))
    test.send(sender)
    sendLogin(sender)



def sendLogin(sender):
    scopes = ",".join(["manage_pages", "publish_pages"])
    url = facebook.loginUrl(sender, scopes)
    button = URLButton("Grant access", url)
    loginMessage = ButtonMessage("I need access to your pages.", button)
    loginMessage.send(sender)


def loggedIn(sender, code):
    log("Login successful!")
    log(sender)

    clientToken = facebook.getClientTokenFromCode(sender, code)
    if clientToken:
        log("Client Token: " + str(clientToken))
        status = actualListPages(sender, clientToken)
        if status:
            return

    message = TextMessage("Couldn't access your pages, please try again:")
    message.send(sender)
    sendLogin(sender)


def actualListPages(sender, clientToken):
    pages = facebook.listManagedPages(clientToken)
    if pages is None:
        return False
    if len(pages) == 0:
        message = TextMessage("Couldn't find any pages that you manage.")
        message.send(sender)
    else:
        message = TextMessage("Found these pages. Select which ones you want me to help manage.")
        message.send(sender)

        # group pages by 10
        for start in range(((len(pages)-1)//10)+1):
            pagesMessage = GenericMessage()
            for i in range(start, min(start+10, len(pages))):
                page = pages[i]
                url = facebook.pageUrl(page.id)
                element = Element(page.name, "", url)
                element.addButton(Button("Manage", managePage(page.id)))
                pagesMessage.addElement(element)
            pagesMessage.send(sender)

    return True


#################
#   Postbacks   #
#################

def receivedPostback(sender, recipient, payload):
    log("Received postback with payload \"{}\" from {}".format(payload, sender))

    if DISABLED:
        response = TextMessage("I am temporarily offline. Follow the page for updates!")
        response.send(sender)
        return

    data = json.loads(payload)
    type = data.get("type")
    if not type:
        raise RuntimeError("No 'type' included in postback.")

    if type == "action":
        action = data["action"]
        pb = Postback.registered.get(action)
        args = data.get("args", dict())
        if not pb:
            raise RuntimeError("No postback for action '{}'.".format(action))
        pb(sender, **args)


@postback
def sendWelcome(sender):
    message = TextMessage("Hello! I'm glad you decided to use this app.")
    message.send(sender)
    sendLogin(sender)


@postback
def listPages(sender):
    """ Doesn't actually list pages. Need permission first. (See actualListPages) """
    sendLogin(sender)


@postback
def managePage(sender, pageID=None):
    message = TextMessage("You want me to manage page: " + str(pageID))
    message.send(sender)


#################
#   Management  #
#################


def exceptionOccured(e):
    log("Exception in request.")
    log(str(e))
    if ADMIN_SENDER_ID:
        notification = TextMessage("Exception:\t{}".format(str(e)))
        notification.send(ADMIN_SENDER_ID)


def adminMessage(sender, message):
    if message == "setup":
        response = TextMessage("Running setup")
        response.send(sender)
        profile.setup()
        return True

    if message.startswith("@all"):
        # text = message[5:]
        # log("sending message to everyone:")
        # log(text)
        # broadcast = TextMessage(text)
        # for person in Person.everyone():
        #     broadcast.send(person.fbID)
        return True

    return False
