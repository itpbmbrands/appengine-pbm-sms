# Import Pyton libraries
import csv
import logging
import json

# import users from appengine api
from google.appengine.api import users

# Import the Flask Framework
from flask import Flask
from flask import render_template, redirect, url_for
from flask import request
from flask import flash

# import from twilio
from twilio import TwilioRestException
from twilio.rest import TwilioRestClient


secrets = json.loads(open('secrets.json').read())

# app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets["flask"]

# list of users able to access app
ALLOWED_EMAIL = secrets["allowed_email"]

#  configure twilio client
TWILIO_SID = secrets["twilio_sid"]
TWILIO_TOKEN  = secrets["twilio_token"]
TWILIO_NUMBER = secrets["twilio_number"]
twilio_client = TwilioRestClient(TWILIO_SID, TWILIO_TOKEN)

# set global variable FAILED - will contain failures
FAILED = []


def send_sms(info, text_message):

    success = True

    try:
        message = twilio_client.messages.create(
            body=text_message,
            to=info["number"],
            from_=TWILIO_NUMBER
            )
    except TwilioRestException as e:
        logging.error(e)
        success = False

    return success


@app.route('/', methods=['POST', 'GET'])
def home():

    authorized = False

    user = users.get_current_user()
    logout_url = users.create_logout_url('/')
    login_url = users.create_login_url('/')
    logged_in = False

    context = {"logout_url": logout_url, "login_url": login_url}

    if user:
        if user.email() in ALLOWED_EMAIL or users.is_current_user_admin():
            authorized = True
            greeting = ('Welcome, %s!' % user.email())
            logged_in = True
        else:
            greeting = "You are not authorized to be here!"
    else:
        greeting = "Please login!"

    context.update(
        {
            "greeting": greeting,
            "authorized": authorized,
            "logged_in": logged_in
        })

    if request.method == 'GET':

        FAILED[:] = []

        return render_template('base.html', **context)

    if request.method == 'POST':

        contact_list = request.files['contact_list']

        if ".csv" not in contact_list.filename:
            flash("The file <strong>%s</strong> is not a csv" % contact_list.filename)
            return render_template('base.html', **context)

        csv_reader = csv.reader(contact_list, delimiter=',')
        text_message = request.form["message"]

        info_list = []

        try:
            for row in csv_reader:
                info = {
                    "first_name": row[0],
                    "last_name": row[1],
                    "number": row[2]
                    }
                info_list.append(info)
        except Exception as error:

            logging.error(error)

            flash("There was a problem with the submitted file. "
                 "Ensure that it's a properly formatted csv.")
            return render_template('base.html', **context)

        for info in info_list:

            success = send_sms(info, text_message)
            if not success:
                full_name = info["first_name"] + " " + info["last_name"]
                logging.error("Failed to send to: %s" % full_name)
                FAILED.append(full_name)

        return redirect(url_for('complete'))





@app.route('/complete', methods=['GET'])
def complete(context=None):
    return render_template('complete.html', failed=FAILED)




@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
