from flask_wtf import FlaskForm
from wtforms import StringField, validators, TextAreaField


class ConfessionForm(FlaskForm):
    confession = TextAreaField('Confession', [validators.Length(min=10)], description="Confession...", render_kw={"style": "resize: vertical;", "rows": 10, "placeholder": "Confession..."})