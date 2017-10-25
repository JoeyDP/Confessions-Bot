import os
import traceback

from util import *
from message import *
import chatbot
from form import ConfessionForm
from database import Confession, Page
from facebook import FBPage

from flask import Flask, request, g, render_template, redirect, url_for, abort
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
Bootstrap(app)
csrf = CSRFProtect(app)


VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
app.secret_key = VERIFY_TOKEN

@app.route('/', methods=['GET'])
@csrf.exempt
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return webpage()


def webpage():
    return "Confessions!", 200


adminBot = chatbot.ConfessionsAdminBot()
voterBot = chatbot.ConfessionsVoterBot()

@app.route('/login/<sender>')
def login_redirect(sender):
    """ endpoint for redirect after login. """
    @after_this_request
    def afterLogin():
        code = request.args.get("code")
        if sender and code:
            adminBot.loggedIn(sender, code)

    # TODO: change to a redirect to the page form
    return render_template('login_redirect_landing.html')


@app.route('/confess/<pageID>', methods=('GET', 'POST'))
def confession_form(pageID):
    form = ConfessionForm(request.form)
    if form.validate_on_submit():
        text = form.confession.data
        confession = Confession()
        confession.text = text.strip()
        confession.page_id = pageID
        confession.add()
        if not confession.page.hasPendingConfession():
            adminBot.sendFreshConfession(confession.page)

        return redirect(url_for('confession_success'))
    page = Page.findById(pageID)
    if page:
        fbPage = FBPage(page)
        profilePic = fbPage.getProfilePictureUrl()
        cover = fbPage.getCoverPictureUrl()
        return render_template('confession_form.html', form=form, pageName=page.name, profilePic=profilePic, cover=cover)
    else:
        abort(404)


@app.route('/confess_success')
def confession_success():
    return render_template('confession_success.html')


def after_this_request(func):
    if not hasattr(g, 'call_after_request'):
        g.call_after_request = []
    g.call_after_request.append(func)
    return func


@app.teardown_request
def teardown_request(exception=None):
    if exception is None:
        try:
            for func in getattr(g, 'call_after_request', ()):
                func()
        except Exception as e:
            adminBot.exceptionOccured(e)
            traceback.print_exc()
    else:
        adminBot.exceptionOccured(exception)


@app.route('/', methods=['POST'])
@csrf.exempt
def webhook():
    """ endpoint for processing incoming messaging events. """
    @after_this_request
    def afterWebhook():
        receivedRequest(request)

    return "ok", 200


def receivedRequest(request):
    data = request.get_json()

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                sender = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                recipient = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID

                if messaging_event.get("message"):  # someone sent us a message
                    message = messaging_event["message"].get("text")
                    if not message:
                        log("Received message without text from {}.".format(str(sender)))
                        message = ""
                    receivedMessage(sender, recipient, message)

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    payload = messaging_event["postback"]["payload"]  # the message's text
                    receivedPostback(sender, recipient, payload)


def receivedMessage(sender, recipient, message):
    # log("Received message \"{}\" from {}".format(message, sender))
    if sender != recipient:     # filter messages to self
        adminBot.receivedMessage.delay(sender, recipient, message)


def receivedPostback(sender, recipient, payload):
    # log("Received postback with payload \"{}\" from {}".format(payload, sender))
    adminBot.receivedPostback(sender, recipient, payload)


if __name__ == '__main__':
    app.run(debug=DEBUG)
