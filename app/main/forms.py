from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Optional


__author__ = 'Daniel'


# Form for adding a thumbtack
class AddThumbtack(Form):
    name = StringField('Name', validators=[DataRequired()])
    kind = RadioField('Type',
                      validators=[DataRequired()],
                      choices=[('category', 'category'),
                               ('idea', 'idea')])
    description = TextAreaField('Description', validators=[DataRequired()])
    asin = StringField('Amazon ASIN', validators=[Optional()])


class AddThumbtackType(Form):
    kind = RadioField('Type',
                      validators=[DataRequired()],
                      choices=[('category', 'category'),
                               ('item', 'item'),
                               ('idea', 'idea')])


# Form for doing an asin check for thumbtacks when the user is adding an item
class AsinCheck(Form):
    asin = StringField("Amazon's ASIN", validators=[DataRequired()])


# Confirmation that the item is what the user intended
class AsinCorrect(Form):
    correct_asin = RadioField('Is this correct?',
                              validators=[DataRequired()],
                              choices=[('choice1', 'Yes'), ('choice2', 'No')],)


# Confirmation that the user wants to delete.
class Delete(Form):
    confirmation = RadioField(
                    'Are you sure you want to delete this?',
                    validators=[DataRequired()],
                    choices=[('choice1', 'NO!!'), ('choice2', 'Yes')],
                    default='choice1')
    confirmation_phrase = StringField('Type "DeleteNow"', validators=[DataRequired()])


# Form for adding comments
class Comment(Form):
    title = StringField('Title: ', validators=[Optional()])
    comment = TextAreaField(label='Comment:', validators=[DataRequired()])
