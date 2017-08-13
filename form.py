from wtforms import Form, BooleanField, StringField, PasswordField, validators

class ConfessionForm(Form):
    confession = StringField('Confession', [validators.Length(min=10)])
    accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])
