import traceback

from util import *
import hmac
import hashlib
from message import *
import chatbot
import facebook
from form import ConfessionForm
from database import Confession, Page, Base
from facebook import FBPage
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from flask import Flask, request, g, render_template, redirect, url_for, abort
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from rq.decorators import job

import worker
rqCon = worker.conn

app = Flask(__name__)
Bootstrap(app)
csrf = CSRFProtect(app)


VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
app.secret_key = VERIFY_TOKEN

app.config.update(PREFERRED_URL_SCHEME='https')

SERVER_NAME = os.environ.get("SERVER_NAME")
if SERVER_NAME:
    app.config.update(SERVER_NAME=SERVER_NAME)
    

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

@app.route('/login')
def login_redirect():
    """ endpoint for redirect after login. """

    sender = request.args.get('sender')
    code = request.args.get("code")
    if sender and code:
        adminBot.loggedIn(sender, code)

    # TODO: change to a redirect to the page form
    return render_template('login_redirect_landing.html')


@app.route('/confess/<pageID>', methods=['GET', 'POST'])
def confession_form(pageID):
    form = ConfessionForm(request.form)
    if form.validate_on_submit():
        text = form.confession.data
        confession = Confession()
        confession.text = text.strip()
        confession.page_id = pageID
        try:
            confession.add()
            if not confession.page.hasPendingConfession():
                adminBot.sendFreshConfession(confession.page)

            log("new confession id: " + str(confession.id))
            return redirect(url_for('confession_status', confessionID=confession.id))
        except IntegrityError as e:
            log(str(e))
            Base.session.rollback()
            form.confession.errors.append("This confession has already been submitted.")
        except SQLAlchemyError as e:
            log(str(e))
            Base.session.rollback()
            form.confession.errors.append("Your confessions is not valid.")
    page = Page.findById(pageID)
    if page:
        fbPage = FBPage(page)
        profilePic = fbPage.getProfilePictureUrl()
        cover = fbPage.getCoverPictureUrl()
        return render_template('confession_form.html', form=form, pageName=page.name, profilePic=profilePic, cover=cover)
    else:
        abort(404)


@app.route('/confession/<confessionID>', methods=['GET'])
def confession_status(confessionID):
    confession = Confession.findById(confessionID)
    if confession is None:
        abort(404)

    url = None
    if confession.status == "posted":
        url = facebook.postUrl(confession.fb_id)
    return render_template("confession.html", confession=confession, url=url)


@app.route('/', methods=['POST'])
@csrf.exempt
def webhook():
    """ endpoint for processing incoming messaging events. """
    try:
        if validateRequest(request):
            receivedRequest(request)
        else:
            error = "Invalid request received: " + str(request)
            log(error)
            adminBot.sendErrorMessage(error)
            abort(400)
    except Exception as e:
        adminBot.exceptionOccured(e)
        traceback.print_exc()

    return "ok", 200


def validateRequest(request):
    log(request.headers)
    advertised = request.headers.get("X-Hub-Signature")

    if advertised is None:
        return False

    log("Request data:")
    log(request.get_data())

    log("Signature:")
    log(advertised)

    received = "sha1={}".format(hmac.new(
        key=VERIFY_TOKEN.encode('utf-8'),
        msg=request.get_data(),
        digestmod=hashlib.sha1
    ).hexdigest())

    log("Outcome:")
    log(received)

    return hmac.compare_digest(
        advertised,
        received
    )


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
                    receivedMessage.delay(sender, recipient, message)

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    payload = messaging_event["postback"]["payload"]  # the message's text
                    receivedPostback.delay(sender, recipient, payload)


@job('low', connection=rqCon)
def receivedMessage(sender, recipient, message):
    if sender == recipient:  # filter messages to self
        return

    try:
        adminBot.receivedMessage(sender, recipient, message)
    except Exception as e:
        adminBot.exceptionOccured(e)
        traceback.print_exc()


@job('low', connection=rqCon)
def receivedPostback(sender, recipient, payload):
    try:
        with app.app_context():
            adminBot.receivedPostback(sender, recipient, payload)
    except Exception as e:
        adminBot.exceptionOccured(e)
        traceback.print_exc()


if __name__ == '__main__':
    app.run(debug=DEBUG)
