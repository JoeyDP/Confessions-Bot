from flask_wtf import FlaskForm
from wtforms import StringField, validators, TextAreaField

class ConfessionForm(FlaskForm):
    confession = TextAreaField('Confession', [validators.Length(min=10)], render_kw={})
    # accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])
