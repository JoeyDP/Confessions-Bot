from urllib.parse import urljoin

from message import *
from database import *
import facebook
import profile
from flask import url_for


URL = os.environ["URL"]
APP_ID = os.environ["APP_ID"]
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

    sendLogin(sender)



def sendLogin(sender):
    redirect = url_for("login_redirect", sender=sender, _external=True)    # TODO might need to set SERVER_NAME var
    scopes = ",".join(["manage_pages", "publish_pages"])
    url = "https://www.facebook.com/v2.9/dialog/oauth?display=popup&redirect_uri={}&client_id={}&scope={}".format(redirect, APP_ID, scopes)
    button = URLButton("Grant access", url)
    loginMessage = ButtonMessage("I need access to your pages.", button)
    loginMessage.send(sender)


def loggedIn(sender):
    log("Login successful!")
    log(sender)


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
        pb = postback.registered.get(action)
        if not pb:
            raise RuntimeError("No postback for action '{}'.".format(action))
        pb(sender)


@postback
def sendWelcome(sender):
    message = TextMessage("Hello! I'm glad you decided to use this app.")
    message.send(sender)
    sendLogin(sender)


@postback
def listPages(sender):
    message = TextMessage("I will now list your pages.")
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
