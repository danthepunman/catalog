from flask.ext.wtf import Form
from wtforms import StringField, SelectField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Optional


__author__ = 'Daniel'
# These are the forms used in the admin blueprint


# Used in route for adding a category
class Category(Form):
    name = StringField('Category Name', validators=[DataRequired()])
    category = SelectField('Select Parent Category', validators=[DataRequired()], coerce=int)


# Used with selecting a category
class SelectCategory(Form):
    category_id = SelectField('Category', validators=[DataRequired()], coerce=int)


class MultipleAddition(Form):
    name1 = StringField('Name', validators=[DataRequired()])
    name2 = StringField('Name', validators=[DataRequired()])
    name3 = StringField('Name', validators=[DataRequired()])
    name4 = StringField('Name', validators=[DataRequired()])
    name5 = StringField('Name', validators=[DataRequired()])
    description1 = TextAreaField('Description', validators=[Optional()])
    description2 = TextAreaField('Description', validators=[Optional()])
    description3 = TextAreaField('Description', validators=[Optional()])
    description4 = TextAreaField('Description', validators=[Optional()])
    description5 = TextAreaField('Description', validators=[Optional()])
    items_move = SelectField('Category', validators=[DataRequired()], coerce=int)

# Used if Amazon API is not used
# class Item(Form):
#     category_id = SelectField('Category', validators=[DataRequired()], coerce=int)


# Delete form has a double confirmation
class Delete(Form):
    confirmation = RadioField(
                    'Are you sure you want to delete this?',
                    validators=[DataRequired()],
                    choices=[('choice1', 'NO!!'), ('choice2', 'Yes')],
                    default='choice1')
    confirmation_phrase = StringField('Type "DeleteNow"', validators=[DataRequired()])


# Gives the admin option to move or delete the children of category being deleted
class MoveChildrenCategory(Form):
    children = RadioField(
        'What would you like to do with the children categories?',
        choices=[('choice1', 'Move'), ('choice2', 'Delete')],
        default='choice1')
    category_id = SelectField('Select a New Parent Category', coerce=int)


# Gives the admin option to move or delete the items of the category being deleted
class MoveItems(Form):
    items = RadioField(
        'What would you like to do with the items in this categories?',
        choices=[('choice1', 'Move'), ('choice2', 'Delete')],
        default='choice1')
    item_category = SelectField('Select a Category for the Items', coerce=int)


# Confirms the creation of all the categories.
class ConfirmCreation(Form):
    confirmation = RadioField(
                    'Are you sure you want to create categories?',
                    validators=[DataRequired()],
                    choices=[('choice1', 'Yes'), ('choice2', 'NO')],
                    default='choice1')


# Gets an item number, so we can retrieve the Amazon Node
class GetAmazonNode(Form):
    asin = StringField('ASIN of item in the category you are looking for:', validators=[DataRequired()])
    search_index = SelectField('Choose the searchIndex for this category:', coerce=int)
    keywords = StringField('Choose the keywords for this category:', validators=[DataRequired()])


# Checks that the node returns the correct items for the category.
class CheckAmazonNode(Form):
    confirmation = RadioField(
                    'Is this the right category?',
                    validators=[DataRequired()],
                    choices=[('choice1', 'Yes'), ('choice2', 'NO')],
                    default='choice1')

