import json
import random
import string
from datetime import datetime
from xml.dom import minidom
import httplib2
import requests
from flask import render_template, redirect, request, url_for, flash, \
    current_app, make_response, jsonify, session as login_session, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets

from sqlalchemy import desc, exists

from forms import AddThumbtack, AsinCheck, AsinCorrect, Delete, Comment, AddThumbtackType
from . import main
from .. import csrf, lm
from ..amazon_api import AmazonASINCheck
from ..database import session
from ..models import Categories, Items, Users, FavoritesCategories, FavoriteItems, Comments, Thumbtacks

__author__ = 'Daniel'

# Retrieves the client id from Google's client secrets
CLIENT_ID = json.loads(
    open('app/client_secrets.json', 'r').read())['web']['client_id']
# Variable used in Google sign-in
APPLICATION_NAME = "Catalog App"
# variable used in parsing Amazon API response with minidom
xmlns = "http://webservices.amazon.com/AWSECommerceService/2011-08-01"

# Part of the login manager
lm.login_view = 'login'


# Connects the current user with data table User
@lm.user_loader
def load_user(id):
    current_user = Users.query.get(int(id))
    return current_user


# Before each request to the main blueprint the current user is connected to the 'g' context
@main.before_request
def before_request():
    g.user = current_user


# Gets the category tree for the left side
def sidebar(category_id):
    # Main Categories
    child_of_root = session.query(Categories).filter_by(parent_id=1).all()
    parent_list = []
    category = session.query(Categories).filter_by(id=category_id).one()
    parents_id = category.parent_id
    parent = category
    # Loops through getting each layer of parents up to the Main Category
    while parents_id != 1:
        parent = session.query(Categories).filter_by(id=parents_id).one()
        parent_list.append(parent)
        parents_id = parent.parent_id
    # Determine the main category called 'father'
    if parent_list != []:
        father = parent_list.pop()
    else:
        father = parent
    # Gets the children categories
    children = session.query(Categories).filter_by(parent_id=category_id).all()
    return child_of_root, father, parent_list, parent, children, category


# Gets the data for the right sidebar
def right_sidebar():
    # Users favorite categories
    category_favorites_list = []
    favorite_categories = session.query(FavoritesCategories.category).filter_by(user=current_user.id).all()
    # Iterate through getting each category
    for fav in favorite_categories:
        favorite = session.query(Categories).filter_by(id=fav.category).first()
        category_favorites_list.append(favorite)

    # Users favorite items
    item_favorites_list = []
    favorite_items = session.query(FavoriteItems.item).filter_by(user=current_user.id).all()
    for fav in favorite_items:
        favorite = session.query(Items).filter_by(id=fav.item).first()
        item_favorites_list.append(favorite)

    return category_favorites_list, item_favorites_list


# Adds context to redirect back to the page that sent the request
def redirect_url(default='index'):
    return request.args.get('next') or request.referrer or url_for(default)


# Helper function with xml parsing
def get_list(parent, tag):
    data = parent.getElementsByTagNameNS(xmlns, tag)
    parent.childNodes
    return data


# Helper function with xml parsing
def get_data(parent, tag):
    data = parent.getElementsByTagNameNS(xmlns, tag)[0].firstChild.data
    data = data.encode('utf-8').strip()
    return data


# Used as a sandbox to test and debug
@main.route('/')
def index():
    # if session.query(FavoriteItems.id).filter(FavoriteItems.user == user, FavoriteItems.item == item_id).count() == 0:
    return render_template('layout.html')


# Landing page for logging in
@main.route('/login/', methods=['GET', 'POST'])
def login():
    # Left sidebar
    child_of_root = session.query(Categories).filter_by(parent_id=1).all()
    # Creates a id for the client in order to verify the response
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    # Passes the state to the login_session
    login_session['state'] = state
    # Checks to see if the user is already logged in
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('catalog'))
    return render_template('login.html', child_of_root=child_of_root,
                           CLIENT_ID=CLIENT_ID, STATE=state)


# Login using google
@csrf.exempt
@main.route('/gconnect', methods=['POST'])
def gconnect():
    # verify that the response is from the same client from the original request
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Gets the data from the response
    code = request.data

    try:
        # Uses flow from secret module to change the data response to a token
        oauth_flow = flow_from_clientsecrets('app/client_secrets.json',
                                             scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)

    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # if successful then the access token is obtained
    access_token = credentials.access_token
    # Generate a url to use the access token to get the users info
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    # Send the request
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # check the result for errors
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-type'] = 'application/json'
    gplus_id = credentials.id_token['sub']
    # Check that the result from Google is the same as from the client
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401
        )
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the response from Google is for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401
        )
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check the credentials to see if they are already store, if so they are already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
    # Store the access token in login session under credentials
    login_session['credentials'] = credentials.access_token
    # Save the gplus_id
    login_session['gplus_id'] = gplus_id
    # Retrieve the users info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    # Make the request
    answer = requests.get(userinfo_url, params=params)
    # Store the response in the variable data
    data = answer.json()
    # Add the details to login_session
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    me = data
    # Setup for entry into the database table for Users
    social = 'google$' + me['id']
    username = me['given_name']
    email = me['email']
    picture = me['picture']
    if email is None:
        flash('Authentication failed.')
        return redirect(url_for('.catalog'))
    # Check to see if the user is already in the database
    user = session.query(Users).filter(exists().where(Users.email == email)).first()
    if not user:
        # If not add to the database
        user = Users(social=social, nickname=username, email=email, picture=picture)
        session.add(user)
        session.commit()
    # Gives the user the status logged_in
    login_user(user, True, True, False)
    # Give the user feedback that they are successfully logged in before returning them to the catalog
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px; border-radius: 150px: ' \
              '-webkit-border-radius: 150px; -moz-border-radius: 150px;"> '
    flash('you are now logged in as %s' % login_session['username'])

    return output


# Logging out of google
@login_required
@main.route('/gdisconnect')
def gdisconnect():
    # Get access token from login_session
    access_token = login_session['credentials']
    # If none user is not logged in
    if access_token is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'applications/json'
        return response
    # Setup url for revoking the token with Google
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['credentials']
    # Send request
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    # Process the result from Google
    if result['status'] == '200':
        # If successful then delete info from login_session
        logout_user()
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        flash('Successfully disconnected.')
        return redirect(url_for('.catalog'))
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response

# # Logout the user
# @main.route('/logout')
# def logout():
#     logout_user()
#     print current_user.is_anonymous
#     return redirect(url_for('.catalog'))


# Landing page for the application
@main.route('/catalog/')
def catalog():
    # Gets the main categories
    child_of_root = session.query(Categories).filter_by(parent_id=1).all()
    return render_template('./catalog.html', child_of_root=child_of_root)


# Page for a category selected
@main.route('/catalog/category/<int:category_id>/')
def catalog_category(category_id):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # thumbtacks
    thumbtacks = session.query(Thumbtacks).filter_by(category=category_id).all()
    # Right sidebar
    category_favorite_list = []
    item_favorite_list = []
    # Check that the current user is authenticated before request right_sidebar info
    if current_user.is_authenticated:
        category_favorite_list, item_favorite_list = right_sidebar()
    # If category has no children categories then it redirects to the page displaying items
    if not children:
        return redirect(url_for('.catalog_items', category_id=category.id, page=1))
    return render_template('catalog_category.html', category=category,
                           parent=parent,
                           children=children, parent_list=parent_list,
                           child_of_root=child_of_root,
                           father=father,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list,
                           thumbtacks=thumbtacks)


# Page for category that has items
@main.route('/catalog/category/<int:category_id>/catalog_items/page/<int:page>')
def catalog_items(category_id, page):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    category_favorite_list = []
    item_favorite_list = []
    # Right sidebar
    # Check that the current user is authenticated before request right_sidebar info
    if current_user.is_authenticated:
        category_favorite_list, item_favorite_list = right_sidebar()
    # Determine how many items are in the category
    item_count = session.query(Items).filter_by(category_id=category_id, created_by='Category').count()
    # Determine how many pages for the category
    pages = item_count/10
    if item_count > 10:
        start = (page-1) * 10
        end = start + 10
        # If there are more than 10 then it will be split into multiple pages and only get the first 10 items
        items = session.query(Items).filter_by(category_id=category_id, created_by='Category').order_by(desc(Items.asin))[start:end]
    else:
        # if less than 10 get all the items
        items = session.query(Items).filter_by(category_id=category_id, created_by='Category').all()

    # Get the thumbtacks for this category
    thumbtacks = session.query(Thumbtacks).filter_by(category=category_id).all()
    return render_template('catalog_items.html', items=items, child_of_root=child_of_root,
                           category=category, parent_list=parent_list,
                           parent=parent, father=father,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list,
                           thumbtacks=thumbtacks, category_id=category_id,
                           page=page, pages=pages)


# Allows for a json response of all items in a category
@main.route('/catalog/category/<int:category_id>/catalog_items/JSON')
def catalog_items_json(category_id):
    items = session.query(Items).filter_by(category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])



@main.route('/catalog/category/<int:category_id>/item/<int:item_id>')
def item_details(category_id, item_id):
    # Get the details of the item
    item = session.query(Items).filter_by(id=item_id).one()
    # Get the comments for this item
    comments = session.query(Comments).filter_by(item=item_id).all()
    # Get the category this item is in
    category = session.query(Categories).filter_by(id=category_id).one()
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category.id)
    category_favorite_list = []
    item_favorite_list = []
    if current_user.is_authenticated:
        # Check to see if the user has liked any of the items
        category_favorite_list, item_favorite_list = right_sidebar()
    return render_template('item_details.html', item=item, child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           category=category, category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list, comments=comments)


# This inverses the state of whether the user likes an item or not
@login_required
@main.route('/catalog/item/<int:item_id>/item_favorite')
def item_favorite(item_id):
    # Get the user's id
    user = current_user.id
    # Get the item
    item = session.query(Items).filter_by(id=item_id).first()
    favorited = session.query(FavoriteItems).filter_by(user=user, item=item.id).first()
    # Check to see if the user already favorites this item
    if favorited:
        # Remove object from table if the user wants to not favorite the item anymore
        unlike = session.query(FavoriteItems).filter_by(user=user, item=item_id).first()
        session.delete(unlike)
        session.commit()
    else:
        like = FavoriteItems(user, item_id)
        session.add(like)
        session.commit()
    return redirect(redirect_url())


# Users can add a comment on an item
@login_required
@main.route('/catalog/item/<int:item_id>/add_comment', methods=['GET', 'POST'])
def add_comment(item_id):
    # Get the item
    item = session.query(Items).filter_by(id=item_id).one()
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(item.category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    form = Comment()
    if form.validate_on_submit():
        # Create the new object, Comment
        new_comment = Comments(current_user.id, item.id, form.title.data, form.comment.data, datetime.now())
        session.add(new_comment)
        session.commit()
        return redirect(url_for('.item_details', category_id=item.category_id, item_id=item_id))
    return render_template('comment_add.html', child_of_root=child_of_root, father=father,
                           parent_list=parent_list, parent=parent, children=children,
                           category=category, category_favorite_list=category_favorite_list, item=item, form=form,
                           item_favorite_list=item_favorite_list)


# User can edit their own comments
@login_required
@main.route('/catalog/item/<int:item_id>/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
def edit_comment(item_id, comment_id):
    # Get item
    item = session.query(Items).filter_by(id=item_id).first()
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(item.category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    # Get comment
    comment = session.query(Comments).filter_by(id=comment_id).first()
    # Check that the user is the one that made the comment
    if comment.user == current_user.id:
        # Fill the form with the details of the comment
        comment_edit = Comment(obj=comment)
        if comment_edit.validate_on_submit():
            # Upon valid submission populate the comment object with the new data
            comment_edit.populate_obj(comment)
            session.commit()
            flash('Comment has been updated')
            return redirect(url_for('.item_details', category_id=item.category_id, item_id=item_id))
    else:
        # If not the author of the comment, redirect back to the previous page
        flash('Only the user that created this comment can edit it.')
        return redirect(url_for('.item_details', category_id=item.category_id, item_id=item_id))
    return render_template('edit_comment.html', category_id=item.category_id, comment_edit=comment_edit,
                           child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list, comment=comment, item=item)


# The user can delete their own comment
@login_required
@main.route('/catalog/item/<int:item_id>/delete_comment/<int:comment_id>', methods=['GET', 'POST'])
def delete_comment(item_id, comment_id):
    # Get item
    item = session.query(Items).filter_by(id=item_id).first()
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(item.category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    # Get the comment
    comment = session.query(Comments).filter_by(id=comment_id).one()
    # Check that the user is the one that made the comment
    if comment.user == current_user.id:
        confirmation_form = Delete()
        if confirmation_form.validate_on_submit():
            # Deletion requires double verification.
            if confirmation_form.confirmation.data == 'choice2' and \
                            confirmation_form.confirmation_phrase.data == 'DeleteNow':
                session.delete(comment)
                session.commit()
                flash('Comment has been deleted')
                return redirect(url_for('.item_details', category_id=item.category_id, item_id=item_id))
    else:
        # If not the author of the comment, redirect back to the previous page
        flash('Only the user that created this comment can edit it.')
        return redirect(redirect_url())
    return render_template('delete_comment.html', category_id=item.category_id,
                           confirmation_form=confirmation_form,
                           child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list, comment=comment,
                           item=item)


# File uploads not implemented.
# In the future it could be incorporated into the comments or the thumbtacks
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1] in current_app.ALLOWED_EXTENSIONS

# User section


# This is the page for the user own profile
@login_required
@main.route('/user/')
def get_user():
    user = session.query(Users).filter_by(id=current_user.id).first()
    return render_template('user_profile.html', user=user, login_session=login_session)


# This is for other to look at a user's profile
@main.route('/profile/user/<int:user_id>')
def profile(user_id):
    user = session.query(Users).filter_by(id=user_id).first()
    return render_template('profile.html', user=user)


# Allows user to favorite or unfavored a category
@login_required
@main.route('/catalog/category/<int:category_id>/favorite/add')
def favorite_category(category_id):
    # Try to find where user favored the category before
    favorite = session.query(FavoritesCategories).filter_by(user=current_user.id, category=category_id).first()
    # if it exists then delete it
    if favorite:
        session.delete(favorite)
        session.commit()
        flash('Category deleted from your favorites')
    else:
        # if it doesn't exist then add it
        favorite = FavoritesCategories(user=current_user.id, category=category_id)
        session.add(favorite)
        session.commit()
        flash('Category added to your favorites')
    return redirect(url_for('.catalog_category', category_id=category_id))


# Thumbtack section
@login_required
@main.route('/catalog/category/<int:category_id>/add_thumbtack_type', methods=['GET', 'POST'])
def add_thumbtack_type(category_id):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    # Thumbtacks can be an category, item, or idea
    thumbtack_type = AddThumbtackType()
    if thumbtack_type.validate_on_submit():
        if thumbtack_type.kind.data == 'item':
            # If user wants to add an item they need to provide the asin
            return redirect(url_for('.add_thumbtack_asin', category_id=category_id))
        else:
            # Using different form if its not an item. The kind is passed through the url
            return redirect(url_for('.add_thumbtack', category_id=category_id, kind=thumbtack_type.kind.data))
    return render_template('add_thumbtack.html', category_id=category_id, child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list,
                           thumbtack_type=thumbtack_type)


# If category or idea was selected for thumbtack type then this function is used
@main.route('/catalog/category/<int:category_id>/kind/<kind>/add/', methods=['GET', 'POST'])
def add_thumbtack(category_id, kind):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    form = AddThumbtack()
    # Apply the kind to the form
    form.kind.data = kind
    if form.validate_on_submit():
        # Create a thumbtack object
        new_thumbtack = Thumbtacks(name=form.name.data,
                                   kind=form.kind.data,
                                   user=current_user.id,
                                   category=category_id,
                                   description=form.description.data)
        # Add and commit it
        session.add(new_thumbtack)
        session.commit()

        flash('New thumbtack added')
        return redirect(url_for('.catalog_category', category_id=category_id))
    return render_template('add_thumbtack.html', category_id=category_id, child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list,
                           form=form, kind=kind)


# If item was selected then this one will be used
@login_required
@main.route('/catalog/category/<int:category_id>/add_thumbtack_asin', methods=['GET', 'POST'])
def add_thumbtack_asin(category_id):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()

    form_asin = AsinCheck()

    # If asin is submitted then we will call it from the Amazon API
    if form_asin.validate_on_submit():
        # Get the asin from the form
        asin = form_asin.asin.data
        # Check to see if it is in the database already
        item_check = session.query(Items).filter_by(asin=asin).first()
        if item_check:
            # If it is the user is informed that it is and they can add a comment to it
            flash('Item is already in our catalog. If you would like to leave a comment that would be great')
            # Redirect them to the item
            return redirect(url_for('.item_details', category_id=item_check.category_id, item_id=item_check.id))
        else:
            # Create a request from the amazon api
            asin_check = AmazonASINCheck(asin)
            # Convert it to an url
            url = asin_check.url_creation()
            # Send an request
            h = httplib2.Http()
            results = h.request(url, 'GET')
            heading = results[0]
            # Response is in xml format
            xml = results[1]
            # Check that the response was good
            if heading['status'] == '200':
                # Parse the xml
                dom = minidom.parseString(xml)
                # Check that the request was valid
                isvalid = get_data(dom, 'IsValid')
                test = isvalid
                if test == 'True':
                    # Start gathering the info about the item
                    description = 'Description:  '
                    # Gets a list of the attributes
                    item_attributes = get_list(dom, 'ItemAttributes')
                    for it_at in item_attributes:
                        children = get_list(it_at, '*')
                        for child in children:
                            child_name = child.tagName
                            # Get the elements name 'Feature' which is our description
                            if child_name == 'Feature':
                                child_data = child.firstChild.nodeValue
                                child_string = child_data.encode('utf-8').strip()
                                description += child_string + ', '
                        # The title is the name of the item
                        title = get_data(it_at, 'Title')
                    # Create a data object of the item, add and commit it.
                    # The last element distinguishes it from items in the categories
                    asin_check = Items(asin, title, category_id, description, 'Thumbtack')
                    session.add(asin_check)
                    session.commit()
                    # Get the additional info we need of the object
                    item_links = get_list(dom, 'ItemLinks')
                    item_link = get_list(item_links[0], 'ItemLink')
                    for it_li in item_link:
                        descrip = get_data(it_li, 'Description')
                        if descrip == 'All Offers':
                            all_offers = get_data(it_li, 'URL')
                    asin_check.offers = all_offers
                    small_image = get_list(dom, 'SmallImage')
                    for image in small_image:
                        small_image_url = get_data(image, 'URL')
                        asin_check.small_image = small_image_url
                    medium_image = get_list(dom, 'MediumImage')
                    for image in medium_image:
                        medium_image_url = get_data(image, 'URL')
                        asin_check.medium_image = medium_image_url
                    large_image = get_list(dom, 'LargeImage')
                    for image in large_image:
                        large_image_url = get_data(image, 'URL')
                        asin_check.large_image = large_image_url
                    for it_at in item_attributes:
                        brand = get_data(it_at, 'Brand')
                        asin_check.brand = brand
                        list_price = get_list(it_at, 'ListPrice')
                        for price in list_price:
                            formatted_price = get_data(price, 'FormattedPrice')
                            asin_check.list_price = formatted_price
                    # Commit the changes to the database
                    session.add(asin_check)
                    session.commit()

        return redirect(url_for('.add_thumbtack_asin_correct', category_id=category_id, asin=asin))

    return render_template('add_thumbtack.html', category_id=category_id, child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list,
                           form_asin=form_asin)


# The user gets the item to see if it is the one he was wanting
@main.route('/catalog/category/<int:category_id>/add_thumbtack/asin_correct/<asin>', methods=['GET', 'POST'])
def add_thumbtack_asin_correct(category_id, asin):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    # Get the item using the asin
    item = session.query(Items).filter_by(asin=asin).first()
    form_correct = AsinCorrect()
    if form_correct.validate_on_submit():
        if form_correct.correct_asin.data == 'choice1':
            # If the user confirms it is correct, the thumbtack is created
            new_thumbtack = Thumbtacks(name=item.name,
                                       kind='item',
                                       user=current_user.id,
                                       category=category_id,
                                       description=item.description)
            # We add the asin and image to this thumbtack
            new_thumbtack.asin = asin
            new_thumbtack.image = item.small_image
            session.add(new_thumbtack)
            session.commit()
            flash('New thumbtack added')
            return redirect(url_for('.catalog_category', category_id=category_id))
        else:
            return redirect(url_for('.add_thumbtack_asin', category_id=category_id))
    return render_template('add_thumbtack.html', category_id=category_id, child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list,
                           form_correct=form_correct, item=item)


# The user can edit their own thumbtacks (except items)
@login_required
@main.route('/catalog/category/<int:category_id>/edit_thumbtack/<int:thumbtack_id>', methods=['GET', 'POST'])
def edit_thumbtack(category_id, thumbtack_id):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    # Get the thumbtack
    thumbtack = session.query(Thumbtacks).filter_by(id=thumbtack_id).first()
    # Check if the thumbtack is an item
    if thumbtack.kind == 'item':
        # Inform the user that they can't edit the item
        flash('Sorry, items cannot be edited. You can only delete them')
        return redirect(redirect_url())
    else:
        # Check that the user is the creator
        if thumbtack.user == current_user.id:
            # Populate the form with the thumbtack
            edit_thumb = AddThumbtack(obj=thumbtack)
            if edit_thumb.validate_on_submit():
                # Populate the data obj and commit it
                edit_thumb.populate_obj(thumbtack)
                session.commit()
                flash('Thumbtack has been updated')
                return redirect(redirect_url())
        else:
            flash('Only the user that created this thumbtack can edit it.')
            return redirect(url_for('.catalog_category', category_id=category_id))
    return render_template('edit_thumbtack.html', category_id=category_id, edit_thumb=edit_thumb,
                           child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list)


@login_required
@main.route('/catalog/category/<int:category_id>/delete_thumbtack/<int:thumbtack_id>', methods=['GET', 'POST'])
def delete_thumbtack(category_id, thumbtack_id):
    # Left sidebar
    child_of_root, father, parent_list, parent, children, category = sidebar(category_id)
    # Right sidebar
    category_favorite_list, item_favorite_list = right_sidebar()
    # Get the thumbtack
    thumbtack = session.query(Thumbtacks).filter_by(id=thumbtack_id).one()
    # Check that the user is the creator
    if thumbtack.user == current_user.id:
        confirmation_form = Delete()
        if confirmation_form.validate_on_submit():
            if confirmation_form.confirmation.data == 'choice2' and \
                            confirmation_form.confirmation_phrase.data == 'DeleteNow':
                # If confirmed delete object
                session.delete(thumbtack)
                session.commit()
                flash('Thumbtack has been deleted')
                return redirect(url_for(redirect_url()))

    return render_template('delete_thumbtack.html', category_id=category_id,
                           confirmation_form=confirmation_form,
                           child_of_root=child_of_root,
                           father=father, parent_list=parent_list, parent=parent,
                           children=children, category=category,
                           category_favorite_list=category_favorite_list,
                           item_favorite_list=item_favorite_list, thumbtack=thumbtack)


# Privacy statement was generated when I was trying to implement the amazon oauth.
# Amazon would not work with implementing 'https' for the site
# Kept the privacy statement
@main.route('/privacy_statement')
def privacy_statement():
    return render_template('privacy_policy.html')
