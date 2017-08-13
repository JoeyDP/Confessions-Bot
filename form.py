from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, validators

class ConfessionForm(FlaskForm):
    confession = StringField('Confession', [validators.Length(min=10)])
    # accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])
