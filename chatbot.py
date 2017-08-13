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
        debug("Client Token: " + str(clientToken))
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
                pageID = page["id"]
                name = page["name"]
                token = page["access_token"]
                url = facebook.pageUrl(pageID)
                imageURL = facebook.getPageProfilePictureUrl(pageID, clientToken)
                element = Element(name, "", url, imageURL)
                element.addButton("Manage", managePage(pageID=pageID, name=name, token=token))
                pagesMessage.addElement(element)
            pagesMessage.send(sender)

    return True


def sendConfession(confession):
    admin = confession.page.admin_messenger_id
    message = ButtonMessage("[{}]: {}".format(confession.page.name, confession.text))
    message.addButton("Post", acceptConfession(confessionID=confession.id))
    message.addButton("Discard", rejectConfession(confessionID=confession.id))
    status = message.send(admin)
    if status:
        confession.setPending()
        confession.save()
    return status


def sendFreshConfession(page):
    fresh = page.getFirstFreshConfession()
    if fresh:
        sendConfession(fresh)


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
def managePage(sender, pageID=None, name=None, token=None):
    page = Page.findById(pageID)
    if page:
        message = TextMessage("I already manage the page " + str(name))
        message.send(sender)
    else:
        page = Page()
        page.fb_id = pageID
        page.name = name
        page.token = token
        page.admin_messenger_id = sender
        page.add()
        message = TextMessage("I am nog managing the page " + str(name))
        message.send(sender)
        message = TextMessage("Confessions need to be submitted to: " + str(url_for("confession_form", pageID=pageID, _external=True)))
        message.send(sender)


@postback
def acceptConfession(sender, confessionID=None):
    debug("Accepted confession")
    confession = Confession.findById(confessionID)
    if confession.status == "posted":
        message = TextMessage("Confession was already posted: {}".format(facebook.postUrl(confession.fb_id)))
        message.send(sender)
        return

    fbPage = facebook.FBPage(confession.page)
    index = fbPage.getLastConfessionIndex()
    postID = fbPage.postConfession(index + 1, confession.text)
    if postID:
        message = TextMessage("Posted confession: {}".format(facebook.postUrl(postID)))
        message.send(sender)
        confession.setPosted(postID)
    else:
        message = TextMessage("Failed to post confession.")
        message.send(sender)
        confession.status = "fresh"     # set status to fresh again, because posting failed
    confession.save()
    sendFreshConfession(confession.page)


@postback
def rejectConfession(sender, confessionID=None):
    debug("Rejected confession")
    confession = Confession.findById(confessionID)
    confession.setRejected()
    confession.save()
    sendFreshConfession(confession.page)


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
