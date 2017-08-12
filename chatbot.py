from urllib.parse import urljoin

from message import *
from database import *
import facebook
import profile


URL = os.environ["URL"]
ADMIN_SENDER_ID = os.environ.get("ADMIN_SENDER_ID")
DISABLED = os.environ.get("DISABLED", 0) == '1'


def receivedMessage(sender, recipient, message):
    log("Received message \"{}\" from {}".format(message, sender))
    if sender == ADMIN_SENDER_ID:
        if adminMessage(sender, message):
            return

    if DISABLED:
        response = TextMessage(gettext("I am temporarily offline. Follow the page for updates!"))
        response.send(sender)
        if len(message) > 5 and ADMIN_SENDER_ID:
            report = TextMessage("{}:\n\"{}\"".format(sender, message))
            report.send(ADMIN_SENDER_ID)
        return


def sendWelcome(person):
    message = TextMessage(lazy_gettext("Hello {}! I'm glad you decided to use this app. Please answer some questions.").format(person.firstName))
    message.send(person.fbID)


def sendLogin(person):
    loginMessage = ButtonMessage(lazy_gettext("I need access to your public profile. This will be sent to people you match with."))
    redirect = urljoin(URL, "login/" + str(person.fbID))
    loginMessage.buttons.append(URLButton(lazy_gettext("Sign me up"),
                                          "https://www.facebook.com/v2.9/dialog/oauth?redirect_uri={}&client_id={}".format(redirect, os.environ["APP_ID"])))
    loginMessage.send(person.fbID)


def loggedIn(sender):
    pass


def receivedPostback(sender, recipient, payload):
    log("Received postback with payload \"{}\" from {}".format(payload, sender))

    if DISABLED:
        response = TextMessage(gettext("I am temporarily offline. Follow the page for updates!"))
        response.send(sender)
        return


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
