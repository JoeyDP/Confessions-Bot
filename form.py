from flask_wtf import FlaskForm
from wtforms import StringField, validators, TextAreaField

class ConfessionForm(FlaskForm):
    confession = TextAreaField('Confession', [validators.Length(min=10)], type="", render_kw={"style": "resize: vertical;", "rows": 10})
    # accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])
