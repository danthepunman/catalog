import ast
import os
import re
from xml.dom import minidom
import httplib2

from flask import render_template, redirect, jsonify, request, url_for, flash, g
from flask.ext.login import current_user
from sqlalchemy import desc
from sqlalchemy.sql import func

from forms import Category, Delete, SelectCategory, ConfirmCreation
from forms import GetAmazonNode, CheckAmazonNode
from forms import MoveChildrenCategory, MoveItems, MultipleAddition
from . import admin
from .. import lm
from ..amazon_api import AmazonASINCheck, AmazonNodeSearch, AmazonItemsSearch
from ..database import session, create_categories, empty_db

from ..models import Categories, Items, Users, AmazonSearches, FavoritesCategories
from ..models import CategoryNodes, AmazonSearchIndex, AmazonReturnedItems
from ..models import FavoriteItems, Comments, Thumbtacks

# variable used in parsing Amazon API response with minidom
xmlns = "http://webservices.amazon.com/AWSECommerceService/2011-08-01"


# Helper function that is used frequently in parsing xml response from Amazon
def get_list(parent, tag):
    data = parent.getElementsByTagNameNS(xmlns, tag)
    parent.childNodes
    return data


# Helper function that is used frequently in parsing xml response from Amazon
def get_data(parent, tag):
    data = parent.getElementsByTagNameNS(xmlns, tag)[0].firstChild.data
    data = data.encode('utf-8').strip()
    return data


# Adds context to redirect back to the page that sent the request
def redirect_url(default='.admin_index'):
    return request.args.get('next') or request.referrer or url_for(default)


# Gets the current users id from the database
@lm.user_loader
def load_user(id):
    current_user = Users.query.get(int(id))
    return current_user


# Before each request that is in the Admin Blueprint,
# the user is checked to make sure that they are the admin
@admin.before_request
def before_request():
    g.user = current_user
    if not current_user.is_admin:
        flash('Not authorize to view requested page', category='message')
        return redirect(url_for('main.catalog'))
    else:
        return


# The dashboard for the admin to get an overview of the website and database.
@admin.route('/index/')
def admin_index():
    # Categories
    # Total Number of Categories
    categories = session.query(Categories).count()
    # Categories that need items
    categories_need_items = session.query(Categories).filter_by(children=None).count()
    # First Category that needs items
    first_category_need_items = session.query(Categories).filter_by(children=None).first()
    # Category with most favorites
    top_favorites = session.query(FavoritesCategories.category, func.count(
        FavoritesCategories.category).label('total')).group_by(
        FavoritesCategories.category).order_by(desc('total')).all()[:5]
    # Makes a list of the database objects in order to get the details on the webpage
    top_five_categories_favorite = []
    # From the prior query, j stands for the category id and k stands for the count
    for j, k in top_favorites:
        category = session.query(Categories).filter_by(id=j).first()
        is_favorite = ' is liked ' + str(k) + ' times'
        top_five_categories_favorite.append(category.name + is_favorite)

    # Users
    # Total number of users
    users = session.query(Users).count()
    # User with the most favorite categories
    u_with_most_fav_categories = session.query(
        FavoritesCategories.user, func.count(FavoritesCategories.user).label('total')).group_by(
        FavoritesCategories.user).order_by(desc('total')).all()[:5]
    # Transforms the list returned from the query into a workable list
    user_with_most_fav_categories = []
    for j, k in u_with_most_fav_categories:
        user = session.query(Users).filter_by(id=j).first()
        has_most = ' at ' + str(k)
        user_with_most_fav_categories.append(user.nickname + has_most)
    # User with the most items
    u_with_most_fav_items = session.query(FavoriteItems.user, func.count(FavoriteItems.user).label('total')) \
        .group_by(FavoriteItems.user).order_by(desc('total')).all()[:5]
    user_with_most_fav_items = []
    for j, k in u_with_most_fav_items:
        user = session.query(Users).filter_by(id=j).first()
        has_most = ' at ' + str(k)
        user_with_most_fav_items.append(user.nickname + has_most)
    # User with the most comments
    u_with_most_comments = session.query(Comments.user, func.count(Comments.user).label('total')) \
        .group_by(Comments.user).order_by(desc('total')).all()[:5]
    user_with_most_comments = []
    for j, k in u_with_most_comments:
        user = session.query(Users).filter_by(id=j).first()
        has_most = ' at ' + str(k)
        user_with_most_comments.append(user.nickname + has_most)
    # User with the most thumbtacks
    u_with_most_thumbtacks = session.query(Thumbtacks.user, func.count(Thumbtacks.user).label('total')) \
        .group_by(Thumbtacks.user).order_by(desc('total')).all()[:5]
    user_with_most_thumbtacks = []
    for j, k in u_with_most_thumbtacks:
        user = session.query(Users).filter_by(id=j).first()
        has_most = ' at ' + str(k)
        user_with_most_thumbtacks.append(user.nickname + has_most)

    # Items
    # Total number of items
    items = session.query(Items).count()
    # Items most liked
    i_with_most_likes = session.query(FavoriteItems.item, func.count(FavoriteItems.item).label('total')) \
        .group_by(FavoriteItems.item).order_by(desc('total')).all()[:5]
    item_with_most_likes = []
    for j, k in i_with_most_likes:
        item = session.query(Items).filter_by(id=j).first()
        has_most = ' at ' + str(k)
        item_with_most_likes.append(item.name + has_most)
    # Item with most comments
    i_with_most_comments = session.query(Comments.item, func.count(Comments.item).label('total')) \
        .group_by(Comments.item).order_by(desc('total')).all()[:5]
    item_with_most_comments = []
    for j, k in i_with_most_comments:
        item = session.query(Items).filter_by(id=j).first()
        has_most = ' at ' + str(k)
        item_with_most_comments.append(item.name + has_most)

    # Thumbtacks
    thumbtacks = session.query(Thumbtacks).count()
    # Gets a list of thumbtacks that need to be reviewed by the admin
    thumbtacks_need_review = session.query(Thumbtacks).filter_by(admin_screened=False).count()
    # Gets a list of category names and thumbtack names.  Allows to see if thumbtacks are relevant to category topics.
    category_with_thumbtacks = session.query(Categories.name, Thumbtacks.name)\
        .join('thumbtack').group_by(Categories.name).order_by(Categories.name).all()[:5]

    # Comments
    # Number of comments
    comments = session.query(Comments).count()
    # Number of comments that need to be reviewed
    comments_need_review = session.query(Comments).filter_by(admin_screened=False).count()

    return render_template('admin/admin_index.html', categories=categories,
                           categories_need_items=categories_need_items,
                           first_category_need_items=first_category_need_items,
                           top_five_categories_favorite=top_five_categories_favorite,
                           users=users, user_with_most_fav_categories=user_with_most_fav_categories,
                           user_with_most_fav_items=user_with_most_fav_items,
                           user_with_most_comments=user_with_most_comments,
                           user_with_most_thumbtacks=user_with_most_thumbtacks,
                           items=items, item_with_most_likes=item_with_most_likes,
                           item_with_most_comments=item_with_most_comments,
                           thumbtacks=thumbtacks, thumbtacks_need_review=thumbtacks_need_review,
                           category_with_thumbtacks=category_with_thumbtacks,
                           comments=comments, comments_need_review=comments_need_review)


# Provides an easy way for the admin to empty the database of all categories and items
@admin.route('/database/delete_categories', methods=['GET', 'POST'])
def database_empty_categories():
    form = Delete()
    if form.validate_on_submit():
        if form.confirmation.data == 'choice2' and \
                        form.confirmation_phrase.data == 'DeleteNow':
            empty_db()
            flash('Categories have been deleted', category='message')
        return redirect(url_for(redirect_url()))
    return render_template('admin/delete_categories.html', form=form)


# Provides a way for the admin to install the generic categories provided by the app
@admin.route('/database/create_categories', methods=['GET', 'POST'])
def database_create_categories():
    categories = session.query(Categories).all()
    # Checks the database to see if the categories already exists.
    # If they do warn the admin that the categories are still in the database
    if categories:
        warning = '*** Categories already exist. Please empty database so there is no ' \
                  'duplication of categories. ***'
    form = ConfirmCreation()
    if form.validate_on_submit():
        if form.confirmation.data == 'choice1':
            create_categories()
            flash('Categories have been added', category='message')
        return redirect(url_for(redirect_url()))
    return render_template('admin/create_categories.html', form=form, warning=warning)


# Provides the admin a dashboard of all the categories in the database
@admin.route('/category/categories')
def categories_all():
    categories = session.query(Categories).all()
    return render_template('admin/categories.html', categories=categories)


# Narrows down the list of categories to ones with items
@admin.route('/category/categories_with_items')
def categories_with_items():
    category_list = []
    categories = session.query(Items.category_id).group_by(Items.category_id).order_by(Items.category_id).all()
    for category in categories:
        cat = session.query(Categories).filter_by(id=category.category_id).first()
        item_count = session.query(Items).filter_by(category_id=category.category_id).count()
        category_list.append((cat, item_count))
    return render_template('admin/categories_with_items.html', categories=category_list)


# Admin can add a category
@admin.route('/category/categories/add', methods=['GET', 'POST'])
def category_add():
    form = Category()
    # Gets the drop down choices for the form
    form.category.choices = [(g.id, g.name) for g in session.query(Categories).all()]
    if form.validate_on_submit():
        # Creates a new category from the post response
        new_category = Categories(name=form.name.data, parent_id=form.category.data)
        session.add(new_category)
        session.commit()
        flash('New Category added', category='message')
        # checks if the parent category had any items
        if session.query(Items).filter_by(category_id=form.category.data).all():
            for item in session.query(Items).filter_by(category_id=form.category.data).all():
                # Move the items to the new category.
                # A category should only have children categories  or items
                item.category_id = new_category.id
                session.add(item)
            session.commit()
            flash('Items for the parent category has been moved', category='message')
        return redirect(url_for('main.catalog_category', category_id=form.category.id))
    return render_template('admin/add_category.html', form=form)


# Admin can add five categories, first a category must be selected
@admin.route('/category/categories/add_5', methods=['GET', 'POST'])
def categories_add_5():
    form = SelectCategory()
    form.category_id.choices = [(g.id, g.name)
                                for g
                                in session.query(Categories).all()]
    if form.validate_on_submit():
        # Continues with the add_five_categories function
        return redirect(url_for('.add_five_categories', category_id=form.category_id.data))
    return render_template('admin/categories_add_5.html', form=form)


# If the admin, chooses to add a category while on a category page,
# then the parent category is already known.
@admin.route('/category/categories/<int:category_id>/add_one', methods=['GET', 'POST'])
def category_add_one(category_id):
    category = session.query(Categories).filter_by(id=category_id).first()
    form = Category()
    form.category.choices = [(g.id, g.name) for g in session.query(Categories).all()]
    # The same template is used, the parent category is already selected for the admin
    if request.method == 'GET':
        form.category.data = category.id
    if form.validate_on_submit():
        # new category
        new_category = Categories(name=form.name.data, parent_id=form.category.data)
        session.add(new_category)
        session.commit()
        flash('New Category added', category='message')
        # checking for items
        if session.query(Items).filter_by(category_id=form.category.data).all():
            for item in session.query(Items).filter_by(category_id=form.category.data).all():
                item.category_id = new_category.id
                session.add(item)
            session.commit()
            flash('Items for the parent category has been moved', category='message')
        return redirect(url_for('main.catalog_category', category_id=category_id))
    return render_template('admin/add_category.html', form=form)


# Continuing the creation of five categories
@admin.route('/category/categories/<int:category_id>/add_five', methods=['GET', 'POST'])
def add_five_categories(category_id):
    category = session.query(Categories).filter_by(id=category_id).one()
    form = MultipleAddition()
    items = session.query(Items).filter_by(category_id=category.id).all()
    if items:
        # Provide a choice on where to move the items.
        form.items_move.choices = [(1, 'First New Category'),
                                   (2, 'Second New Category'),
                                   (3, 'Third New Category'),
                                   (4, 'Fourth New Category'),
                                   (5, 'Fifth New Category')]
    if form.validate_on_submit():
        # Add all the categories at once
        session.add_all([
            Categories(name=form.name1.data, parent_id=category.id),
            Categories(name=form.name2.data, parent_id=category.id),
            Categories(name=form.name3.data, parent_id=category.id),
            Categories(name=form.name4.data, parent_id=category.id),
            Categories(name=form.name5.data, parent_id=category.id)
        ])
        session.commit()
        # Now move the items to the selected new category
        if items:
            if form.items_move.data == 1:
                new_category = session.query(Categories).filter_by(name=form.name1.data).one()
            elif form.items_move.data == 2:
                new_category = session.query(Categories).filter_by(name=form.name2.data).one()
            elif form.items_move.data == 3:
                new_category = session.query(Categories).filter_by(name=form.name3.data).one()
            elif form.items_move.data == 4:
                new_category = session.query(Categories).filter_by(name=form.name4.data).one()
            else:
                new_category = session.query(Categories).filter_by(name=form.name5.data).one()
            for item in items:
                item.category_id = new_category.id
                session.add(item)
            session.commit()
        flash('Five categories were added', category='message')
        return redirect(url_for('main.catalog_category', category_id=category_id))
    return render_template('admin/multiple_categories.html', form=form, category=category,
                           items=items)


# Admin can edit a category
@admin.route('/category/categories/<int:category_id>/edit', methods=['GET', 'POST'])
def category_edit(category_id):
    category = session.query(Categories).filter_by(id=category_id).one()
    # Puts in the category details into the form
    form = Category(obj=category)
    form.category.choices = [(g.id, g.name)
                             for g in session.query(Categories).all()]
    form.category.data = category.parent_id
    if form.validate_on_submit():
        # Takes the updated data and updates the database
        form.populate_obj(category)
        session.commit()
        flash('Category has been updated', category='message')
        return redirect(url_for('main.catalog_category',
                                category_id=category.id))
    return render_template('admin/edit_category.html', form=form,
                           category=category, )


# Admin can delete a category
@admin.route('/category/categories/<int:category_id>/delete', methods=['GET', 'POST'])
def category_delete(category_id):
    # Gets the category to be deleted
    category = session.query(Categories).filter_by(id=category_id).one()
    # Get the parent id
    parent = category.parent_id
    # Uses three forms
    # Confirmation is the double verification that this category will be deleted
    confirmation_form = Delete()
    # Form to find out what should happen to the children
    children_form = MoveChildrenCategory()
    # Form to find out what should happen to the items
    items_form = MoveItems()
    children_form.category_id.choices = [(g.id, g.name)
                                         for g in session.query(Categories).all()]
    children_form.category_id.default = parent
    items_form.item_category.choices = [(g.id, g.name)
                                        for g
                                        in session.query(Categories).filter_by
                                        (children=None).all()]
    items_form.item_category.default = parent
    items = session.query(Items).filter_by(category_id=category.id).all()
    children = session.query(Categories).filter_by(parent_id=category.id).all()
    if confirmation_form.validate_on_submit():
        # Confirm that the admin wants to delete this category
        if confirmation_form.confirmation.data == 'choice2' and \
                        confirmation_form.confirmation_phrase.data == 'DeleteNow':
            if children:
                # If admin selects choice1, the children are moved to the selected category
                if children_form.children.data == 'choice1':
                    new_parent = children_form.category_id.data
                    for child in children:
                        # Assign the new parents id to each of the categories
                        child.parent_id = new_parent
                        session.add(child)
                    session.delete(category)
                    session.commit()
                    parent_new = session.query(Categories).filter_by(id=new_parent).one()
                    flash('The children categories have moved to %s' %
                          parent_new.name, category='message')
                    return redirect(url_for('main.catalog_category', category_id=parent))
                else:
                    # Choice2 is to delete all the childre
                    # Get a list of all the children under the category
                    categories_delete = []
                    # First layer of children
                    children = session.query(Categories).filter_by(parent_id=category_id).all()
                    # A replication of children is created because if you remove items from a list that is being
                    # iterated then items of that list will be skipped
                    echo_children = []
                    echo_children = echo_children + children
                    # Using a while loop keeps the search for children of children of children ... as long as there
                    # are children to check for more children
                    while echo_children != []:
                        for child in children:
                            # Add the child to the delete list
                            categories_delete.append(child)
                            # Get all the children of that child
                            kids = session.query(Categories).filter_by(parent_id=child.id).all()
                            for kid in kids:
                                # For each of the new children found we add them to the list we are iterating over
                                # plus the list that the while loop is checking
                                children.append(kid)
                                echo_children.append(kid)
                            # We remove the current child from the list the while loop is checking
                            echo_children.remove(child)
                    # We iterate through the delete list to delete each of them.
                    for cat in categories_delete:
                        session.delete(cat)
                    session.commit()
                    flash("The category and it's children categories have been deleted",
                          category='message')
                    return redirect(url_for('main.catalog_category', category_id=parent))
            elif items:
                # If admin selects choice1, the items are moved to the selected category
                if items_form.items.data == 'choice1':
                    new_category = items_form.item_category.data
                    for item in items:
                        # Assign the new parents id to each of the items
                        item.category_id = new_category
                        session.add(item)
                    # Delete the category
                    session.delete(category)
                    session.commit()
                    item_category = session.query(Categories).filter_by(id=new_category).one()
                    flash('The items in this category have moved to %s' %
                          item_category.name, category='message')
                    return redirect(url_for('main.catalog_category', category_id=parent))
                else:
                    # Choice2 is to delete the items
                    for item in items:
                        session.delete(item)
                    session.commit()
                    # Delete the category
                    session.delete(category)
                    session.commit()
                    flash('The items in this category have been deleted', category='message')
                    return redirect(url_for('main.catalog_category', category_id=parent))
            else:
                # If there are no children or items then just delete the category
                session.delete(category)
                session.commit()
                flash('Category has been deleted', category='message')
                return redirect(url_for('main.catalog_category', category_id=parent))
        return redirect(url_for('main.catalog_category', category_id=category.id))
    return render_template('admin/delete_category.html', category_id=category_id, category=category,
                           confirmation_form=confirmation_form, children_form=children_form,
                           items_form=items_form, items=items, children=children, parent=parent)


@admin.route('/items')
def items_all():
    # Retrieves all the items to display on a dashboard
    items = session.query(Items).all()
    return render_template('admin/items.html', items=items)


@admin.route('/amazon/searches')
def amazon_searches():
    # A dashboard of all the previous searches so the Admin can reuse them
    node_list = []
    # Get all the node searches in the database
    node_searches = session.query(CategoryNodes).all()
    for node in node_searches:
        # Get the category that node search is for
        category = session.query(Categories).filter_by(id=node.category).first()
        node_list.append((node, category))
    search_list = []
    # Get the amazon searches
    amazon_search = session.query(AmazonSearches).all()
    for search in amazon_search:
        category = session.query(Categories).filter_by(id=search.category).first()
        search_list.append((search, category))
    return render_template('admin/amazon_searches.html',
                           node_list=node_list, search_list=search_list)


# Admin can delete a node if it is irrelevant to the category
@admin.route('/amazon/node/<int:amazon_node_id>/delete')
def amazon_node_delete(amazon_node_id):
    node = session.query(CategoryNodes).filter_by(id=amazon_node_id).first()
    session.delete(node)
    session.commit()
    return redirect(redirect_url())


# Admin can delete the search if it is getting the wrong items
@admin.route('/amazon/search/<int:amazon_search_id>/delete')
def amazon_search_delete(amazon_search_id):
    search = session.query(AmazonSearches).filter_by(id=amazon_search_id).first()
    session.delete(search)
    session.commit()
    return redirect(redirect_url())


# Retrieving items from Amazon starts with getting the node that matches the category
@admin.route('/amazon/node/category_id/<int:category_id>/search', methods=['GET', 'POST'])
def amazon_node_search(category_id):
    # Get the category object that getting the new items
    category = session.query(Categories).filter_by(id=category_id).one()
    previous_searches = []
    # Check for previous nodes and searches for this category
    # If so give the admin the option to reuse the search
    previous_nodes = session.query(CategoryNodes).filter_by(category=category_id).all()
    if previous_nodes:
        for node in previous_nodes:
            searches = session.query(AmazonSearches).filter_by(amazon_node=node.id).all()
            for search in searches:
                previous_searches.append((node, search))

    form = GetAmazonNode()
    # Amazon search index is overarching concept categories
    form.search_index.choices = [(g.id, g.search_index) for g in session.query(AmazonSearchIndex).all()]
    if request.method == 'GET':
        # The form is populated with the category name as the keyword.
        # But the Admin can change it to get different results
        form.keywords.data = category.name
    if form.validate_on_submit():
        # To get the node, the Admin must provide one item number from Amazon known as the ASIN
        # that is relevant to the category.
        asin = form.asin.data
        search_index = session.query(AmazonSearchIndex).filter_by(id=form.search_index.data).one()
        keywords = form.keywords.data
        # Check if parameters have been used before
        test_amazon_node_search = session.query(CategoryNodes.id).\
            filter(CategoryNodes.category == category_id,
                   CategoryNodes.keywords == keywords,
                   CategoryNodes.search_index == search_index.search_index).first()
        if test_amazon_node_search:
            return redirect(url_for('.amazon_node_check', category_id=category_id,
                                    browse_node=test_amazon_node_search[0]))
        else:
            # The Amazon Api requests are setup as classes in a separate module (amazon_api.py)
            node_lookup = AmazonNodeSearch(asin)
            # Convert the request to an url
            url = node_lookup.url_creation()
            # Sends the request
            h = httplib2.Http()
            # The results return from a GET request
            results = h.request(url, 'GET')
            heading = results[0]
            # The body of the response is in xml format
            xml = results[1]
            # Check that the response is good
            if heading['status'] == '200':
                # The xml is parsed with minidom
                dom = minidom.parseString(xml)
                print dom.toprettyxml()
                # Using the helper function we can retrieve the node
                browse_node = get_data(dom, 'BrowseNodeId')
                print browse_node
                # The node is stored in the database for further use.
                c_node = CategoryNodes(category_id, browse_node, search_index.search_index, keywords)
                session.add(c_node)
                session.commit()

                return redirect(url_for('.amazon_node_check', category_id=category_id, browse_node=c_node.id))
            else:
                print heading['status']
                dom = minidom.parseString(xml)
                print dom.toprettyxml()
                flash('There was a problem with the request', category='message')
                return redirect(redirect_url())
    return render_template('admin/amazon_node_get.html', form=form,
                           category_id=category_id,
                           category=category, previous_searches=previous_searches)


# Once a node is retrieved, it is used to get a sampling of items. This allows the Admin to verify
# that it is a good node.
@admin.route('/amazon/node/category/<int:category_id>/browse_node/<int:browse_node>/check', methods=['GET', 'POST'])
def amazon_node_check(category_id, browse_node):
    # Set the page to none so we get the first page
    page = None
    # Establish the variable outside of the if statement
    amazon_search_id = None
    # Get the node that was stored in the database on previous request
    node = session.query(CategoryNodes).filter_by(id=browse_node).first()
    # Check the database to see if this search has been done before
    test_amazon_search = session.query(AmazonSearches.id).filter(AmazonSearches.keyword == node.keywords,
                                                                 AmazonSearches.category == category_id,
                                                                 AmazonSearches.search_index == node.search_index,
                                                                 AmazonSearches.amazon_node == node.id).first()
    print test_amazon_search, node.keywords, node.keywords, category_id, node.search_index, browse_node
    if test_amazon_search:
        items_list = []
        old_search = session.query(AmazonSearches).filter_by(id=test_amazon_search[0]).first()
        items = old_search.amazonreturneditems[:10]
        for item in items:
            old_item = session.query(Items).filter_by(asin=item.asin).first()
            items_list.append(old_item)
        form = CheckAmazonNode()
        if form.validate_on_submit():
            if form.confirmation.data == 'choice1':
                # If Admin confirms that these are good items, then we continue to add them
                return redirect(url_for('.amazon_add_items', category_id=category_id,
                                        amazon_search_id=old_search.id))
            else:
                # In the database mark the node as being a bad match
                bad_node = session.query(CategoryNodes) \
                    .filter_by(id=browse_node).first()
                bad_node.good_match = False
                session.add(bad_node)
                session.commit()
                flash('Please try a different item number or change the keywords')

                return redirect(url_for('.amazon_node_search', category_id=category_id))
        return render_template('admin/amazon_node_check.html', form=form, items_list=items_list)

    else:
        # If it hasn't then store it in the database
        new_search = AmazonSearches(category=category_id, keyword=node.keywords, search_index=node.search_index,
                                    sort='salesrank', amazon_node=node.id, response_group='Images,ItemAttributes')
        session.add(new_search)
        session.commit()
        print new_search.id
        amazon_fresh_search = session.query(AmazonSearches).filter_by(id=new_search.id).first()
        print amazon_fresh_search
        # Set up the Amazon request using the amazon_api module
        node_test = AmazonItemsSearch(node.amazon_node, node.search_index, node.keywords, page)
        # Convert the request to an url
        url = node_test.url_creation()
        # Sends the request
        h = httplib2.Http()
        # The results return from a GET request
        results = h.request(url, 'GET')
        heading = results[0]
        # The body of the response is in xml format
        xml = results[1]
        # Establish the list for items
        items_list = []
        # Check that the response is good
        if heading['status'] == '200':
            # The xml is parsed with minidom
            dom = minidom.parseString(xml)
            print dom.toprettyxml()
            # Using the helper function we get the response for isValid
            isvalid = get_data(dom, 'IsValid')
            test = isvalid
            # If it is a good response from Amazon we can continue to parse the document
            if test == 'True':
                # The helper function returns a list of items
                items = get_list(dom, 'Item')
                # The helper function finds the number of pages available for this search
                pages = get_data(dom, 'TotalPages')
                print pages
                if int(pages) >= 10:
                    # Amazon's api will only return the first 10 pages even if the 'TotalPages' is higher
                    amazon_fresh_search.max_pages = 10
                else:
                    # xml data is always a string must convert to integer
                    amazon_fresh_search.max_pages = int(pages)

                # Iterate through the items
                for item in items:
                    # asin is amazon's item number
                    asin = get_data(item, 'ASIN')
                    # Initiate the description string before the loop
                    description = 'Description:  '
                    # The details of the item are under 'ItemAttributes
                    item_attributes = get_list(item, 'ItemAttributes')
                    for it_at in item_attributes:
                        # Get a list of all the tags under item_attributes
                        children = get_list(it_at, '*')
                        for child in children:
                            child_name = child.tagName
                            # There multiples of the tag, 'Feature' which is what we use for description
                            if child_name == 'Feature':
                                # Get the xml value for 'Feature
                                child_data = child.firstChild.nodeValue
                                # Encode it into utf-8 and stripping rare unicode for database storage
                                child_string = child_data.encode('utf-8').strip()
                                # Add it to the string 'description'
                                description += child_string + ', '
                        # With the helper function we get the title which is used as the name of the item
                        title = get_data(it_at, 'Title')
                    # Check to see if the asin has been stored in the database
                    asin_check = session.query(Items).filter_by(asin=asin).first()
                    # If it is not found in the database we add it
                    if not asin_check:
                        # Prepare the variables for entry into the database
                        uasin = unicode(asin, errors='ignore')
                        utitle = unicode(title, errors='ignore')
                        udescription = unicode(description, errors='ignore')
                        # Add the item to the database
                        asin_check = Items(uasin, utitle, category_id, udescription, 'Category')
                        session.add(asin_check)
                        session.commit()
                        flash(title + 'has been added to database', category='message')
                    else:
                        # If the item is in the database we check for any name changes
                        if asin_check.name != unicode(title, errors='ignore'):
                            asin_check.name = unicode(title, errors='ignore')
                            session.add(asin_check)
                            session.commit()
                        # We see if it was stored under a different category.
                        elif asin_check.category_id != category_id:
                            uasin = unicode(asin, errors='ignore')
                            utitle = unicode(title, errors='ignore')
                            udescription = unicode(description, errors='ignore')
                            # If so we add it as a new item so it will be under both categories
                            asin_check = Items(uasin, utitle, category_id, udescription, 'Category')
                            session.add(asin_check)
                            session.commit()
                    # Now that the item is in the database, more info is gathered about it.
                    item_links = get_list(item, 'ItemLinks')
                    item_link = get_list(item_links[0], 'ItemLink')
                    for it_li in item_link:
                        # Amazon provide url links for each item under 'Description'
                        descrip = get_data(it_li, 'Description')

                        # 'All Offers' is where the user can purchase the item
                        if descrip == 'All Offers':
                            all_offers = get_data(it_li, 'URL')
                            # Store the url under offers
                            asin_check.offers = all_offers
                        # Store the url for the small image
                        small_image = get_list(item, 'SmallImage')
                        for image in small_image:
                            small_image_url = get_data(image, 'URL')
                            asin_check.small_image = small_image_url
                        # Store the url for the medium image
                        medium_image = get_list(item, 'MediumImage')
                        for image in medium_image:
                            medium_image_url = get_data(image, 'URL')
                            asin_check.medium_image = medium_image_url
                        # Store the url for the large image
                        large_image = get_list(item, 'LargeImage')
                        for image in large_image:
                            large_image_url = get_data(image, 'URL')
                            asin_check.large_image = large_image_url

                    for it_at in item_attributes:
                        # Store the brand
                        children = get_list(it_at, '*')
                        for child in children:
                            child_name = child.tagName
                        # There multiples of the tag, 'Feature' which is what we use for description
                            if child_name == 'Brand':
                                brand = get_data(it_at, 'Brand')
                                print brand
                                asin_check.brand = brand
                            # Store the list price
                            list_price = get_list(it_at, 'ListPrice')
                            for price in list_price:
                                formatted_price = get_data(price, 'FormattedPrice')
                                asin_check.list_price = formatted_price
                    # Update the item with the new details
                    session.add(asin_check)
                    session.commit()
                    # Add it to the items_list to display it on the webpage
                    items_list.append(asin_check)
                    # Check to see if the item as been added to the AmazonReturnedItems
                    if session.query(AmazonReturnedItems.id) \
                            .filter(AmazonReturnedItems.amazonsearch_id == amazon_fresh_search.id,
                                    AmazonReturnedItems.asin == asin_check.asin).count() == 0:
                        # If not add it so we can work with it in the future
                        new_item = AmazonReturnedItems(amazonsearch_id=amazon_fresh_search.id,
                                                       asin=asin_check.asin,
                                                       page=None)
                        session.add(new_item)
                        session.commit()

        else:
            dom = minidom.parseString(xml)
            print dom.toprettyxml()

    form = CheckAmazonNode()
    if form.validate_on_submit():
        if form.confirmation.data == 'choice1':
            # If Admin confirms that these are good items, then we continue to add them
            return redirect(url_for('.amazon_add_items', category_id=category_id,
                                    amazon_search_id=amazon_fresh_search.id))
        else:
            # In the database mark the node as being a bad match
            bad_node = session.query(CategoryNodes) \
                .filter_by(id=browse_node).first()
            bad_node.good_match = False
            session.add(bad_node)
            session.commit()
            flash('Please try a different item number or change the keywords', category='message')

            return redirect(url_for('.amazon_node_search', category_id=category_id))
    return render_template('admin/amazon_node_check.html', form=form, items_list=items_list)


# Now that the node is confirmed as good, the Admin gets the list of items.
# If the admin wants to remove the item a link is provided to do so.
# Only items with a flag 'is_acceptable' shows on page.
@admin.route('/amazon/items/category_id/<int:category_id>/search_id/<int:amazon_search_id>/add')
def amazon_add_items(category_id, amazon_search_id):
    # Retrieves the search
    search = session.query(AmazonSearches).filter_by(id=amazon_search_id).first()
    # Gets the current category
    category = session.query(Categories).filter_by(id=category_id).one()
    # Gets all the items under that search. 'page=None' gets the ones returned on the node check
    items = session.query(AmazonReturnedItems).filter_by(amazonsearch_id=amazon_search_id, page=None).all()
    new_items = []
    for item in items:
        # Checks the flag 'is_acceptable'
        if item.is_acceptable:
            # If it is then gets the details of that item
            new_item = session.query(Items).filter_by(asin=item.asin, category_id=category_id).first()
            # Adds it to the list to show on the webpage
            new_items.append(new_item)
    return render_template('admin/amazon_add_items.html', category_id=category_id, new_items=new_items,
                           amazon_search_id=amazon_search_id, search=search, category=category)


# If there are more than one page available for the specific search then this request is used
@admin.route('/amazon/items/category_id/<int:category_id>/search_id/<int:amazon_search_id>/add/page/<int:page>')
def amazon_extra_items(category_id, amazon_search_id, page):
    # Gets the details of the search
    search = session.query(AmazonSearches).filter_by(id=amazon_search_id).first()

    # Gets the current category
    category = session.query(Categories).filter_by(id=category_id).one()
    # Check to see if the search for this page has been completed
    if session.query(AmazonReturnedItems).filter_by(amazonsearch_id=amazon_search_id, page=page).count() == 0:
        # If no items are found then proceed with making call to Amazon Api
        # Sets up the api request with the addition of page parameter specified
        page_search = AmazonItemsSearch(browse_node=search.node_relation.amazon_node,
                                        search_index=search.search_index,
                                        keywords=search.keyword,
                                        page=str(page))
        # Convert the request to an url
        url = page_search.url_creation()
        # Sends the request
        h = httplib2.Http()
        # The results return from a GET request
        results = h.request(url, 'GET')
        heading = results[0]
        # The body of the response is in xml format
        xml = results[1]
        # Establish the list for items
        items_list = []
        # Check that the response is good
        if heading['status'] == '200':
            # The xml is parsed with minidom
            dom = minidom.parseString(xml)
            print dom.toprettyxml()
            # Using the helper function we get the response for isValid
            isvalid = get_data(dom, 'IsValid')
            test = isvalid
            if test == 'True':
                # Repeats the iteration just like in the node_check
                items = get_list(dom, 'Item')
                for item in items:
                    asin = get_data(item, 'ASIN')
                    description = 'Description:  '
                    item_attributes = get_list(item, 'ItemAttributes')
                    for it_at in item_attributes:
                        children = get_list(it_at, '*')
                        for child in children:
                            child_name = child.tagName
                            if child_name == 'Feature':
                                child_data = child.firstChild.nodeValue
                                child_string = child_data.encode('utf-8').strip()
                                description += child_string + ', '
                        title = get_data(it_at, 'Title')
                    asin_check = session.query(Items).filter_by(asin=asin).first()
                    if not asin_check:
                        uasin = unicode(asin, errors='ignore')
                        utitle = unicode(title, errors='ignore')
                        udescription = unicode(description, errors='ignore')
                        asin_check = Items(uasin,
                                           utitle,
                                           category_id,
                                           udescription,
                                           'Category')
                        session.add(asin_check)
                        session.commit()
                        flash(title.encode('ascii', errors='ignore') + 'has been added to database', category='message')
                    else:
                        if asin_check.name != title:
                            asin_check.name = title
                            session.add(asin_check)
                            session.commit()
                        elif asin_check.category_id != category_id:
                            asin_check = Items(asin, title, category_id, description, 'Category')
                            session.add(asin_check)
                            session.commit()
                    # Now that the item is in the database, more info is gathered about it.
                    item_links = get_list(item, 'ItemLinks')
                    item_link = get_list(item_links[0], 'ItemLink')
                    for it_li in item_link:
                        # Amazon provide url links for each item under 'Description'
                        descrip = get_list(it_li, 'Description')
                        # 'All Offers' is where the user can purchase the item
                        if descrip == 'All Offers':
                            all_offers = get_data(it_li, 'URL')
                            # Store the url under offers
                            asin_check.offers = all_offers
                    small_image = get_list(item, 'SmallImage')
                    for image in small_image:
                        small_image_url = get_data(image, 'URL')
                        asin_check.small_image = small_image_url
                    medium_image = get_list(item, 'MediumImage')
                    for image in medium_image:
                        medium_image_url = get_data(image, 'URL')
                        asin_check.medium_image = medium_image_url
                    large_image = get_list(item, 'LargeImage')
                    for image in large_image:
                        large_image_url = get_data(image, 'URL')
                        asin_check.large_image = large_image_url
                    for it_at in item_attributes:
                        # Store the brand
                        children = get_list(it_at, '*')
                        for child in children:
                            child_name = child.tagName
                        # There multiples of the tag, 'Feature' which is what we use for description
                            if child_name == 'Brand':
                                brand = get_data(it_at, 'Brand')
                                print brand
                                asin_check.brand = brand
                            # Store the list price
                            list_price = get_list(it_at, 'ListPrice')
                            for price in list_price:
                                formatted_price = get_data(price, 'FormattedPrice')
                                asin_check.list_price = formatted_price
                    # Update the item with the new details
                    session.add(asin_check)
                    session.commit()
                    # Add it to the items_list to display it on the webpage
                    items_list.append(asin_check)
                    # Check to see if the item has been added to the AmazonReturnedItems
                    if session.query(AmazonReturnedItems.id) \
                            .filter(AmazonReturnedItems.amazonsearch_id == amazon_search_id,
                                    AmazonReturnedItems.asin == asin_check.asin).count() == 0:
                        # This time the page number is added
                        new_item = AmazonReturnedItems(amazonsearch_id=amazon_search_id,
                                                       asin=asin_check.asin,
                                                       page=str(page))
                        session.add(new_item)
                        session.commit()
    # Retrieve items under this search and page
    # This is the same as amazon_add_items but for the specific page
    items = session.query(AmazonReturnedItems).filter_by(amazonsearch_id=amazon_search_id, page=page).all()
    new_items = []
    for item in items:
        if item.is_acceptable:
            new_item = session.query(Items).filter_by(asin=item.asin).first()
            new_items.append(new_item)
    return render_template('admin/amazon_extra_items.html',
                           category_id=category_id,
                           category=category,
                           new_items=new_items,
                           amazon_search_id=amazon_search_id,
                           page=page,
                           search=search)


# When admin wants to remove an item during the search
@admin.route('/amazon/item/category_id/<int:category_id>/search_id/<int:amazon_search_id>/asin/<string:asin>/remove')
def amazon_remove_item(category_id, amazon_search_id, asin):
    # Gets the item from Amazon returned items
    item = session.query(AmazonReturnedItems).filter_by(asin=asin, amazonsearch_id=amazon_search_id).first()
    page = item.page
    # Changes the flag is_acceptable so that it is not shown on the webpage
    item.is_acceptable = False
    # Deletes it from the items table
    remove_item = session.query(Items).filter_by(asin=asin).first()
    session.delete(remove_item)
    session.commit()
    if page is None:
        return redirect(url_for('.amazon_add_items', category_id=category_id, amazon_search_id=amazon_search_id))
    else:
        return redirect(url_for('.amazon_extra_items', category_id=category_id, amazon_search_id=amazon_search_id,
                                page=page))


# If the admin wants to get back an item that was removed
@admin.route('/amazon/items/items_removed')
def amazon_removed_items():
    items_list = []
    # Gets all the items flagged not acceptable
    items = session.query(AmazonReturnedItems).filter(is_acceptable=False).all()
    for item in items:
        # Gets the amazon search for that item
        amazon_search = session.query(AmazonSearches).filter_by(id=item.amazonsearch_id).first()
        # Gets the category that it was in.
        # The name is no longer in the system so the admin will have to do figure out which item
        # needs to be recovered using the asin
        category = session.query(Categories).filter_by(id=amazon_search.category).first()
        # append the item and category to the list
        items_list.append((item, category))
    return render_template('admin/amazon_removed_items', items_list=items_list)


@admin.route('/amazon/items/item_recover/asin/<int:asin>/amazon_search/<int:amazon_search>', )
def amazon_recover_item(amazon_search, asin):
    # We get the search to have category id
    search = session.query(AmazonSearches).filter_by(id=amazon_search).first()
    # using the amazon api we setup a request for the single item
    recovered_item = AmazonASINCheck(asin=asin)
    # Convert the request to an url
    url = recovered_item.url_creation()
    # Sends the request
    h = httplib2.Http()
    # The results return from a GET request
    results = h.request(url, 'GET')
    heading = results[0]
    # The body of the response is in xml format
    xml = results[1]
    if heading['status'] == '200':
        # The xml is parsed with minidom
        dom = minidom.parseString(xml)
        print dom.toprettyxml()
        # Using the helper function we get the response for isValid
        isvalid = get_data(dom, 'IsValid')
        test = isvalid
        if test == 'True':
            # Repeats the iteration just like in the node_check
            items = get_list(dom, 'Item')
            for item in items:
                asin = get_data(item, 'ASIN')
                description = 'Description:  '
                item_attributes = get_list(item, 'ItemAttributes')
                for it_at in item_attributes:
                    children = get_list(it_at, '*')
                    for child in children:
                        child_name = child.tagName
                        if child_name == 'Feature':
                            child_data = child.firstChild.nodeValue
                            child_string = child_data.encode('utf-8').strip()
                            description += child_string + ', '
                    title = get_data(it_at, 'Title')
                asin_check = session.query(Items).filter_by(asin=asin).first()
                if not asin_check:
                    uasin = unicode(asin, errors='ignore')
                    utitle = unicode(title, errors='ignore')
                    udescription = unicode(description, errors='ignore')
                    # add the item back into the items table
                    asin_check = Items(uasin,
                                       utitle,
                                       search.category,
                                       udescription,
                                       'Category')
                    session.add(asin_check)
                    session.commit()
                    flash(title.encode('utf-8') + 'has been added to database', category='message')
                else:
                    if asin_check.name != title:
                        asin_check.name = title
                        session.add(asin_check)
                        session.commit()
                    elif asin_check.category_id != search.category:
                        asin_check = Items(asin, title, search.category, description, 'Category')
                        session.add(asin_check)
                        session.commit()
                small_image = get_list(item, 'SmallImage')
                for image in small_image:
                    small_image_url = get_data(image, 'URL')
                    asin_check.small_image = small_image_url
                medium_image = get_list(item, 'MediumImage')
                for image in medium_image:
                    medium_image_url = get_data(image, 'URL')
                    asin_check.medium_image = medium_image_url
                large_image = get_list(item, 'LargeImage')
                for image in large_image:
                    large_image_url = get_data(image, 'URL')
                    asin_check.large_image = large_image_url
                for it_at in item_attributes:
                    # Store the brand
                    children = get_list(it_at, '*')
                    for child in children:
                        child_name = child.tagName
                    # There multiples of the tag, 'Feature' which is what we use for description
                        if child_name == 'Brand':
                            brand = get_data(it_at, 'Brand')
                            print brand
                            asin_check.brand = brand
                        # Store the list price
                        list_price = get_list(it_at, 'ListPrice')
                        for price in list_price:
                            formatted_price = get_data(price, 'FormattedPrice')
                            asin_check.list_price = formatted_price
                session.add(asin_check)
                session.commit()
                # the item in the returned items table is queried
                item_recovered = session.query(AmazonReturnedItems).filter_by(asin=asin).first()
                # The flag is changed back to acceptable
                item_recovered.is_acceptable = True
                session.add(recovered_item)
                session.commit()
                flash('Item has be restored', category='message')
                return redirect(redirect_url())

# The following functions would be used if not using the Amazon API.
# The models class would have to be altered to match
# @admin.route('/item_add', methods=['GET', 'POST'])
# def item_add():
#     form = Item()
#     form.category_id.choices = [(g.id, g.name)
#                                 for g
#                                 in session.query(Categories).filter_by(children=None).all()]
#     if form.validate_on_submit():
#         category = form.category_id.data
#         new_item = Items(name=form.item.data,
#                          category_id=form.category_id.data,
#                          description=form.description.data)
#         session.add(new_item)
#         session.commit()
#         flash('New Item added', category='message')
#         return redirect(url_for('main.catalog_category', category_id=category))
#     return render_template('admin/add_item.html', form=form)
#
#
# @admin.route('/item_add_5', methods=['GET', 'POST'])
# def item_add_5():
#     form = SelectCategory()
#     form.category_id.choices = [(g.id, g.name)
#                                 for g
#                                 in session.query(Categories).filter_by(children=None).all()]
#     if form.validate_on_submit():
#         return redirect(url_for('.add_five_items', category_id=form.category_id.data))
#     return render_template('admin/item_add_5.html', form=form)
#
#
# @admin.route('/add_five_items/category/<int:category_id>', methods=['GET', 'POST'])
# def add_five_items(category_id):
#     category = session.query(Categories).filter_by(id=category_id).one()
#     form = MultipleAddition()
#     if form.validate_on_submit():
#         session.add_all([
#             Items(name=form.name1.data, category_id=category_id, description=form.description1.data),
#             Items(name=form.name2.data, category_id=category_id, description=form.description2.data),
#             Items(name=form.name3.data, category_id=category_id, description=form.description3.data),
#             Items(name=form.name4.data, category_id=category_id, description=form.description4.data),
#             Items(name=form.name5.data, category_id=category_id, description=form.description5.data)
#         ])
#         session.commit()
#         flash('Five items were added', category='message')
#         return redirect(url_for('main.catalog_category', category_id=category_id))
#     return render_template('admin/multiple_items.html', form=form, category=category)
#
#
# @admin.route('/item_edit/<int:item_id>', methods=['GET', 'POST'])
# def item_edit(item_id):
#     item = session.query(Items).filter_by(id=item_id).one()
#     form = Item(obj=item)
#     form.category_id.choices = [(g.id, g.name)
#                                 for g
#                                 in session.query(Categories).filter_by(children=None).all()]
#     form.item.data = item.name
#     form.category_id.data = item.category_id
#     if form.validate_on_submit():
#         form.populate_obj(item)
#         session.commit()
#         flash('Item has been updated', category='message')
#         return redirect(url_for('main.catalog_items', category_id=item.category_id))
#     return render_template('admin/edit_item.html', form=form, item_id=item_id)
#
#


@admin.route('/item_delete/<int:item_id>', methods=['GET', 'POST'])
def item_delete(item_id):
    item = session.query(Items).filter_by(id=item_id).first()
    form = Delete()
    if form.validate_on_submit():
        if form.confirmation.data == 'choice2' and \
                        form.confirmation_phrase.data == 'DeleteNow':
            session.delete(item)
            session.commit()
        return redirect(url_for('.items_all'))
    return render_template('admin/delete_item.html', item=item, form=form)


# A dashboard for all the users
@admin.route('/users')
def users_all():
    users = session.query(Users).all()
    return render_template('admin/users.html', users=users)


# Admin can delete a user
@admin.route('/user/user/<int:user_id>/delete')
def user_delete(user_id):
    user = session.query(Users).filter_by(id=user_id).one()
    session.delete(user)
    session.commit()
    return redirect(redirect_url())


# A dashboard for all the thumbtacks
@admin.route('/thumbtacks')
def thumbtacks_all():
    list_thumbtacks = []
    all_thumbtacks = session.query(Thumbtacks).all()
    for thumbtack in all_thumbtacks:
        # Retrieves the category
        category = session.query(Categories).filter_by(id=thumbtack.category).one()
        # the list is passed both the thumbtack and category to the webpage
        list_thumbtacks.append((thumbtack, category))
    return render_template('admin/thumbtacks.html', list_thumbtacks=list_thumbtacks)


# This dashboard is so the admin can approve the thumbtack
@admin.route('/thumbtacks/admin_screen')
def thumbtacks_admin_screen():
    list_of_thumbtacks = []
    # Gets the thumbtacks that need to be reviewed by the admin
    thumbtacks_need_review = session.query(Thumbtacks).filter_by(admin_screened=False).all()
    for thumb in thumbtacks_need_review:
        # Retrieves the category
        category = session.query(Categories).filter_by(id=thumb.category).one()
        # The thumbtack and category are placed in the list for the webpage
        list_of_thumbtacks.append((thumb, category))
    return render_template('admin/thumbtacks_admin_screen.html', list_of_thumbtacks=list_of_thumbtacks)


# Delete Thumbtack
@admin.route('/thumbtack/<int:thumbtack_id>/delete')
def thumbtack_delete(thumbtack_id):
    thumbtack = session.query(Thumbtacks).filter_by(id=thumbtack_id).one()
    session.delete(thumbtack)
    session.commit()
    return redirect(redirect_url())


# The admin can approve the thumbtack
@admin.route('/thumbtack/<int:thumbtack_id>/approve')
def thumbtack_approve(thumbtack_id):
    thumbtack = session.query(Thumbtacks).filter_by(id=thumbtack_id).one()
    thumbtack.admin_screened = True
    session.add(thumbtack)
    session.commit()
    return redirect(redirect_url())


# A dashboard for all the comments
@admin.route('/comments')
def comments_all():
    list_comments = []
    all_comments = session.query(Comments).all()
    for comment in all_comments:
        item = session.query(Items).filter_by(id=comment.item).first()
        list_comments.append((comment, item))
    return render_template('admin/comments.html', list_comments=list_comments)


# This dashboard is so the admin can approve the comment
@admin.route('/comments/admin_screen')
def comments_admin_screen():
    list_of_comments = []
    comments_need_review = session.query(Comments).filter_by(admin_screened=False).all()
    for comment in comments_need_review:
        item = session.query(Items).filter_by(id=comment.item).first()
        list_of_comments.append((comment, item))
    return render_template('admin/comments_admin_screen.html', list_of_comments=list_of_comments)


# Admin can delete a comment
@admin.route('/comments/comment/<int:comment_id>/delete')
def comment_delete(comment_id):
    comment = session.query(Comments).filter_by(id=comment_id).first()
    session.delete(comment)
    session.commit()
    return redirect(redirect_url())


# Admin can approve comments
@admin.route('/comments/comment/<int:comment_id>/approve')
def comment_approve(comment_id):
    comment = session.query(Comments).filter_by(id=comment_id).first()
    comment.admin_screened = True
    session.add(comment)
    session.commit()
    return redirect(redirect_url())

# The following two features were added to be able to populate the items table without having to do the Amazon Api.
# This is for development purposes and not production


# First to backup the items in a category, this page provides the categories that still need to be backed up.
@admin.route('/database/items/backup')
def items_backup():
    # Initiate a list of categories with ten items
    categories_ten_items = []
    # Query the items table grouped and counted by category id.
    items = session.query(Items, func.count(Items.category_id).label('total'))\
        .filter_by(created_by='Category').group_by(Items.category_id).order_by(desc('total'))
    for j,k in items:
        if k > 9:
            categories_ten_items.append(j.category_id)
    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/Items_Backup")
    # Initiate a list of categories that is already backed up
    categories_list = []
    # Open the file that contains the list of categories already backed up
    with open('items_database_categories.py', 'r') as fo:
        # Read each line
        for lines in fo:
            # Split the string at the beginning of the list
            line = lines.split('[')
            # if the line ends with a continuation break split there
            if line[1].endswith('\ \n'):
                string = line[1].split('\ \n')
                # Split at the commas to get the list of category ids
                categories = string[0].split(',')
                for category in categories:
                    # Append them to the list
                    categories_list.append(int(category))
            # if the line ends at the end of the list, split there
            elif line[1].endswith(']'):
                string = line[1].split(']')
                # Split at the commas to get the list of category ids
                categories = string[0].split(',')
                for category in categories:
                    # Append them to the list
                    categories_list.append(int(category))
    # Close the file
    fo.close()
    categories_not_done = []
    # Create a list of categories that still need to be backed up
    categories_id_not_done = list(set(categories_ten_items) - set(categories_list))
    # Query for each of the ids and place the data object in a list that will be passed to the webpage
    for category in categories_id_not_done:
        cat = session.query(Categories).filter_by(id=category).first()
        categories_not_done.append(cat)
    return render_template('admin/items_backup.html', categories_not_done=categories_not_done)


# Admin selects a category to back up
@admin.route('/database/items/category/<int:category_id>/backup')
def items_backup_category(category_id):
    # Query for the category
    category = session.query(Categories).filter_by(id=category_id).first()
    # Take out all spaces and other characters that are not alpha_numeric
    category_name = re.sub(r'[^\w]', '_', category.name)
    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/Items_Backup")
    # Create a file with the name of the category
    fo = open('items_database_export_%s.py' % category_name, 'w')
    # The string that the file starts with
    opening_string = '\nItems = [\n'
    # Write it to the file
    fo.write(opening_string)
    # Query for all items in that category
    items = session.query(Items).filter_by(category_id=category.id).all()
    # Iterate through the list
    for item in items:
        # Create a string with items data. Each item gets its own line.
        item_string = str(item) + '\n'
        fo.write(item_string)
    # Create the closing string and write it to file
    closing_string = ']\n'
    fo.write(closing_string)
    # Close the file
    fo.close()
    # Establish the path again. Without it the working directory is reverted back with the close of previous file.
    basedir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(basedir + "/Items_Backup")
    # Updating the list of categories that are backup
    source_file = 'items_database_categories.py'
    # Create a temp file
    edited_file = source_file + '.temp'
    # The string that we want to add
    string = str(category.id) + ']'
    # Open the original file default is read only
    with open(source_file) as f:
        # open the temp file in write mode
        e = open(edited_file, 'w', 1)
        # iterate over the lines of the original file
        for lines in f:
            # if line ends with a continuation break then we know the line if full, we just copy it to the temp file.
            if lines.endswith('\ \n'):
                e.write(lines)
            elif lines.endswith(']'):
                # if line ends with the end of the list then we need to determine if there is room for our addition
                if len(lines) + len(string) + 3 < 80:
                    # if so we split at the end of the list and add the string
                    line = lines.split(']')
                    e.write(line[0] + ', ' + string)
                else:
                    lines.split(']')
                    # if the line is too long then we will create a new line
                    e.write(line[0] + '] \ \n categories = [' + string)
    # Close both files
    f.close()
    e.close()
    # Delete the original
    os.remove(source_file)
    # Rename the temp with the original file
    os.rename(edited_file, source_file)
    flash('Items in ' + category.name + ' have been backed up.')
    return redirect(redirect_url())


# Recover the items backed up
@admin.route('/database/items/recover')
def items_recover():
    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/Items_Backup")
    categories_id_list = []
    # Open the file that contains the list of categories already backed up
    with open('items_database_categories.py', 'r') as fo:
        # Read each line
        for lines in fo:
            # Split the string at the beginning of the list
            line = lines.split('[')
            # if the line ends with a continuation break split there
            if line[1].endswith('\ \n'):
                string = line[1].split('\ \n')
                # Split at the commas to get the list of category ids
                categories = string[0].split(',')
                for category in categories:
                    # Append them to the list
                    categories_id_list.append(int(category))
            # if the line ends at the end of the list, split there
            elif line[1].endswith(']'):
                string = line[1].split(']')
                # Split at the commas to get the list of category ids
                categories = string[0].split(',')
                for category in categories:
                    # Add the ids to the list
                    categories_id_list.append(int(category))
    categories_list = []
    categories_already_recovered = []
    for category in categories_id_list:
        # Get the categories and add to the list for the webpage
        cat = session.query(Categories).filter_by(id=category).first()
        items = session.query(Items).filter_by(category_id=category).first()
        if items:
            categories_already_recovered.append(cat)
        else:
            categories_list.append(cat)
    return render_template('admin/items_recover.html', categories_list=categories_list,
                           categories_already_recovered=categories_already_recovered)


# When the admin selects a category to recover its items
@admin.route('database/items/category/<int:category_id>/recover')
def items_recover_category(category_id):
    # Check for items in the category
    test_items = session.query(Items).filter_by(category_id=category_id).all()
    # If items exists then return to previous page with warning that items already exists
    if test_items:
        flash('Items already exist for this category. Please remove them or pick a different category')
        return redirect(redirect_url())
    # Get the category that the items are being recovered.
    category = session.query(Categories).filter_by(id=category_id).first()
    # Establish the root path on the operating system
    # Take out all spaces and other characters that are not alpha_numeric
    category_name = re.sub(r'[^\w]', '_', category.name)
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/Items_Backup")
    # Open the file that is being used in the recovery
    with open('items_database_export_%s.py' % category_name) as f:
        # iterate ove the lines of the file
        for lines in f:
            if lines.startswith('{'):
                # ast evaluates the string as an object.
                item = ast.literal_eval(lines)
                # create an Items object with the details from the line.
                new_item = Items(asin=item['asin'], name=item['name'], category_id=item['category_id'],
                                 description=item['description'], created_by='Category')
                # add the new item
                session.add(new_item)
                session.commit()
                # add on the other elements of the item that is not passed in the initiation of the object
                new_item.small_image = item['small_image']
                new_item.medium_image = item['medium_image']
                new_item.large_image = item['large_image']
                new_item.brand = item['brand']
                new_item.list_price = item['list_price']
                new_item.offers = item['offers']
                session.add(new_item)
                session.commit()

    return redirect(redirect_url())


# JSON for admin
# All Users return in JSON format
@admin.route('/users/JSON')
def users_all_json():
    users = session.query(Users).all()
    return jsonify(Items=[i.admin_serialize for i in users])


# JSON for favorite Categories
@admin.route('/favorite_categories/JSON')
def favorite_categories_json():
    favorite_categories = session.query(FavoritesCategories).all()
    return jsonify(Items=[i.serialize for i in favorite_categories])


# JSON for favorite Categories by Category
@admin.route('/favorite_categories/category/<int:category_id>/JSON')
def favorite_categories_category_json(category_id):
    favorite_categories = session.query(FavoritesCategories).filter_by(category=category_id).all()
    return jsonify(Items=[i.serialize for i in favorite_categories])


# JSON for favorite Categories by User
@admin.route('/favorite_categories/user/<int:user_id>/JSON')
def favorite_categories_user_json(user_id):
    favorite_categories = session.query(FavoritesCategories).filter_by(user=user_id).all()
    return jsonify(Items=[i.serialize for i in favorite_categories])


# JSON for favorite Items
@admin.route('/favorite_items/JSON')
def favorite_items_json():
    favorite_items = session.query(FavoriteItems).all()
    return jsonify(Items=[i.serialize for i in favorite_items])


# JSON for favorite Items by Item
@admin.route('/favorite_items/items/<int:item_id>/JSON')
def favorite_items_item_json(item_id):
    favorite_items = session.query(FavoriteItems).filter_by(item=item_id).all()
    return jsonify(Items=[i.serialize for i in favorite_items])


# JSON for favorite Items by User
@admin.route('/favorite_items/user/<int:user_id>/JSON')
def favorite_items_user_json(user_id):
    favorite_items = session.query(FavoriteItems).filter_by(user=user_id).all()
    return jsonify(Items=[i.serialize for i in favorite_items])


# JSON for Category Nodes
@admin.route('/category_nodes/JSON')
def category_node_json():
    nodes = session.query(CategoryNodes).all()
    return jsonify(Items=[i.serialize for i in nodes])


# JSON for Amazon Searches
@admin.route('/amazon_searches/JSON')
def amazon_searches_json():
    searches = session.query(AmazonSearches).all()
    return jsonify(Items=[i.serialize for i in searches])


# JSON for Amazon Search Indices
@admin.route('/amazon_search_indices/JSON')
def amazon_search_indices_json():
    indices = session.query(AmazonSearchIndex).all()
    return jsonify(Items=[i.serialize for i in indices])


# JSON for Amazon Returned Items
@admin.route('/amazon_returned_items/JSON')
def amazon_returned_items_json():
    items = session.query(AmazonReturnedItems).all()
    return jsonify(Items=[i.serialize for i in items])


# JSON for Amazon Returned Items by amazon_search
@admin.route('/amazon_returned_items/amazon_search/<int:amazon_search_id>/JSON')
def amazon_returned_items_search_json(amazon_search_id):
    items = session.query(AmazonReturnedItems).filter_by(amazon_search=amazon_search_id).all()
    return jsonify(Items=[i.serialize for i in items])



