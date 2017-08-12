import datetime
from urllib.parse import urljoin

from message import *
from database import *
import facebook
import profile
from attribute import *


from flask_babel import gettext, lazy_gettext, _, force_locale

MINUTES_WAIT = 5
URL = os.environ["URL"]
ADMIN_SENDER_ID = os.environ.get("ADMIN_SENDER_ID")
DISABLED = os.environ.get("DISABLED", 0) == '1'
MAX_MESSAGES = 3
AVAILABLE_TRANSLATIONS = ['en', 'nl']


def initPerson(sender):
    person = facebook.initPerson(sender)
    sendWelcome(person)
    return person


def receivedMessage(sender, recipient, message):
    log("Received message \"{}\" from {}".format(message, sender))
    if sender == ADMIN_SENDER_ID:
        if adminMessage(sender, message):
            return

    if DISABLED:
        response = TextMessage(gettext("I am temporarily offline. Follow the page for updates!"))
        response.send(sender)
        if len(message) > 5 and ADMIN_SENDER_ID:
            person = Person.findByFb(sender)
            if not person:
                person = initPerson(sender)
            report = TextMessage("{} {} ({}):\n\"{}\"".format(person.firstName, person.lastName, sender, message))
            report.send(ADMIN_SENDER_ID)
        return

    person = Person.findByFb(sender)
    if not person:
        person = initPerson(sender)

    if not person.isComplete():
        nextAction(person)

    if person.chatContact:
        sendChatMessage(person, message)
    elif len(message) > 5 and ADMIN_SENDER_ID:
        report = TextMessage("{} {} ({}):\n\"{}\"".format(person.firstName, person.lastName, sender, message))
        report.send(ADMIN_SENDER_ID)


def sendChatMessage(person, message):
    contact = person.chatContact
    if len(message) == 0:
        message = TextMessage(gettext("Can't send that message."))
        message.send(person.fbID)
    elif contact and person.canChatWith(contact, MAX_MESSAGES):
        message = ChatMessage(person, message)
        delivered = message.send(person.chatContactPerson.fbID)
        if delivered:
            person.sentMessageTo(contact)
            person.save()
            acknowledgement = TextMessage(lazy_gettext("Sent."))
            acknowledgement.send(person.fbID)
        else:
            acknowledgement = TextMessage(lazy_gettext("Couldn't contact {}.").format(person.chatContactPerson.fullName))
            acknowledgement.send(person.fbID)
    else:
        message = TextMessage(gettext("You can't send any more messages until {} replies.").format(person.chatContactPerson.fullName))
        message.send(person.fbID)


def nextAction(person):
    if person.isComplete():
        # showMenu(person)
        message = TextMessage(lazy_gettext("You are all set up. Request a match with the button in the menu."))
        message.send(person.fbID)
    else:
        queryAttribute(person)


def sendWelcome(person):
    message = TextMessage(lazy_gettext("Hello {}! I'm glad you decided to use this app. Please answer some questions.").format(person.firstName))
    message.send(person.fbID)


def queryAttribute(person):
    if person.appID is None:
        appID = facebook.getAppID(person.fbID)
        if appID:
            person.appID = appID
            person.save()
        else:
            sendLogin(person)
            return

    missing = person.getMissingValues()[0]
    attribute = requestedInformation[missing]
    question = attribute.getAttributeMessage()
    question.send(person.fbID)


def sendLogin(person):
    loginMessage = ButtonMessage(lazy_gettext("I need access to your public profile. This will be sent to people you match with."))
    redirect = urljoin(URL, "login/" + str(person.fbID))
    loginMessage.buttons.append(URLButton(lazy_gettext("Sign me up"),
                                          "https://www.facebook.com/v2.9/dialog/oauth?redirect_uri={}&client_id={}".format(redirect, os.environ["APP_ID"])))
    loginMessage.send(person.fbID)


def loggedIn(sender):
    person = Person.findByFb(sender)
    if not person:
        person = initPerson(sender)

    nextAction(person)


def receivedPostback(sender, recipient, payload):
    log("Received postback with payload \"{}\" from {}".format(payload, sender))

    if DISABLED:
        response = TextMessage(gettext("I am temporarily offline. Follow the page for updates!"))
        response.send(sender)
        return

    person = Person.findByFb(sender)
    if not person:
        person = initPerson(sender)

    data = json.loads(payload)
    type = data["type"]
    if type == "attribute":
        attributePostback(person, data)
        if data.get("sendNext", True):
            nextAction(person)
    if type == "action":
        actionPostback(person, recipient, data)


def attributePostback(person, data):
    attribute = data["attribute"]
    value = data["value"]
    person.setValue(attribute, value)


def actionPostback(person, recipient, data):
    action = data.get("action")
    if action == "forget":
        forget(person, recipient)
    elif action == "editAttributes":
        editAttributes(person, recipient)
    elif action == "findMatch":
        findMatch(person, recipient)
    elif action == "stopChat":
        stopChat(person)
    elif action == "startChat":
        startChat(person, data)
    elif action == "welcome":
        # welcome already sent in init
        nextAction(person)


def forget(person, recipient):
    person.stopLooking()
    person.save()
    message = TextMessage(lazy_gettext("That's unfortunate. Have a nice day!"))
    message.send(person.fbID)


def editAttributes(person, recipient):
    if not person.isComplete():
        nextAction(person)
        return
    message = GenericMessage()
    for attribute in requestedInformation.values():
        element = attribute.getElement(sendNext=False)
        message.addElement(element)
    message.send(person.fbID)


def findMatch(person, recipient):
    if not person.isComplete():
        message = TextMessage(lazy_gettext("Your profile isn't complete yet."))
        message.send(person.fbID)
        nextAction(person)
        return

    lastMatch = person.getLastMatchTime()
    if lastMatch is not None and datetime.datetime.now() - lastMatch < datetime.timedelta(minutes=MINUTES_WAIT):
        message = TextMessage(lazy_gettext("I already gave you a match within the last {} minutes. You got some stamina ;)").format(MINUTES_WAIT))
        message.send(person.fbID)
        return

    candidates = person.getCandidateMatches()
    for candidate in candidates:
        received = notifyMatch(person, candidate)
        if received:
            candidate.stopLooking()
            candidate.save()
            person.addMatch(candidate)
            person.stopLooking()
            person.save()
            return
        else:
            # candidate can't be reached -> stop looking
            candidate.stopLooking()
            candidate.save()

    # no matches found :(
    if not person.isLooking:
        # subscribe
        person.startLooking()
        person.save()
        message = TextMessage(lazy_gettext("There are no match for you right now. No worries, I'll get back to you soon."))
        message.send(person.fbID)
    else:
        # person was already looking
        message = TextMessage(lazy_gettext("You are already on the waiting list. Hang in there."))
        message.send(person.fbID)

    """
    match = person.getNewMatch()
    if match:
        match.stopLooking()
        match.save()
        person.addMatch(match)
        person.stopLooking()
        person.save()
        notifyMatch(person, match)
    elif not person.isLooking:
        person.startLooking()
        person.save()
        message = TextMessage(lazy_gettext("There are no match for you right now. No worries, I'll get back to you soon."))
        message.send(person.fbID)
    else:
        # person was already looking
        message = TextMessage(lazy_gettext("You are already on the waiting list. Hang in there."))
        message.send(person.fbID)
    """


def notifyMatch(person, candidate):
    def notifyPerson(person, match):
        locale = person.locale[:2] if person.locale[:2] in app.AVAILABLE_TRANSLATIONS else "en"
        with force_locale(locale):
            url = None
            if match.appID:
                url = "www.facebook.com/app_scoped_user_id/{}".format(match.appID)
            profileImage = facebook.getProfieImage(match.fbID)
            element = Element("{} {}".format(match.firstName, match.lastName),
                              gettext("You two have a match! Don't be shy, send a message."),
                              url=url,
                              image=profileImage)
            element.addButton(gettext("Start Chatting"), {"type": "action",
                                                          "action": "startChat",
                                                          "contact": match.fbID,
                                                          "info": True
                                                          })
            message = GenericMessage()
            message.addElement(element)
            return message.send(person.fbID)

    # first send to candidate and see if successfull
    if notifyPerson(candidate, person):
        # if sent to 1 person successfull, assume other successfull to prevent multiple matches with same person.
        notifyPerson(person, candidate)
        return True

    # candidate could not be reached
    return False


def stopChat(person):
    if person.chatContact:
        message = TextMessage(gettext("You are no longer chatting with {}.").format(person.chatContactPerson.fullName))
        person.chatContact = None
        person.save()
        message.send(person.fbID)
    else:
        message = TextMessage(gettext("You weren't chatting with anyone."))
        message.send(person.fbID)


def startChat(person, data):
    contactID = data.get("contact")
    info = data.get("info", False)
    if contactID:
        person.chatContact = contactID
        person.save()
        message = TextMessage(gettext("You are chatting with {}.").format(person.chatContactPerson.fullName))
        message.send(person.fbID)
        if info:
            text = gettext("Messages you send will be forwarded to them. You can only send 3 messages without any response.")
            message = TextMessage(text)
            message.send(person.fbID)


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
