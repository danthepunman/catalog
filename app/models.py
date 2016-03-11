from flask.ext.login import UserMixin, current_user
from sqlalchemy import Column, Integer, String,  DATETIME, ForeignKey, Boolean
from sqlalchemy import Enum, Text
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.collections import attribute_mapped_collection

from database import Base, session
from default_config import CATALOG_ADMIN

__author__ = 'Daniel'


# Categories
class Categories(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey(id))
    name = Column(String, nullable=False)
    children = relationship('Categories',
                            cascade='all, delete-orphan',
                            backref=backref('parent', remote_side=id),
                            collection_class=attribute_mapped_collection('name')
                            )
    thumbtack = relationship('Thumbtacks', backref='categories')

    def __init__(self, name, parent_id=None):
        self.name = name
        self.parent_id = parent_id

    def __repr__(self):
        return 'Categories(name=%r, id=%r, parent_id=%r)' % (
            self.name,
            self.id,
            self.parent_id
        )

    def dump(self, _indent=0):
        return "    " * _indent + repr(self) + "\n" + "".join([c.dump(_indent + 1)
                                                               for c in self.children.values()])

    @property
    def parents_name(self):
        parent = session.query(Categories).filter_by(id=self.parent_id).first()
        return parent.name

    @property
    def serialize(self):
        parent = session.query(Categories).filter_by(id=self.parent_id).first()
        if parent:
            parent_name = parent.name
        else:
            parent_name = None
        children = {}
        i = 1
        category_children = session.query(Categories).filter_by(parent_id=self.id).all()
        if category_children:
            for child in category_children:
                children['Child%i' % i] = {}
                children['Child%i' % i]['Name'] = child.name
                children['Child%i' % i]['ID'] = child.id
                i += 1
        return {
            "Name":         self.name,
            "ID":           self.id,
            "Parent's Name":  parent_name,
            "Parent's ID":  self.parent_id,
            "Sub-Categories":     children
        }


# Items
class Items(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    asin = Column(String)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship('Categories', backref='items')
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    small_image = Column(String)
    medium_image = Column(String)
    large_image = Column(String)
    brand = Column(String)
    list_price = Column(String)
    offers = Column(String)
    favorite_item = relationship('FavoriteItems', backref='items')
    comments = relationship('Comments', backref='items')
    created_by = Column(Enum('Category', 'Thumbtack'))

    def __init__(self, asin, name, category_id, description, created_by):
        self.asin = asin
        self.name = name
        self.category_id = category_id
        self.description = description
        self.created_by = created_by

    # Normal representation of Items
    # def __repr__(self):
    #     return 'Items(asin=%r, name=%r, category_id=%r, description=%r, created_by=%r)' % (
    #         self.asin,
    #         self.name,
    #         self.category_id,
    #         self.description,
    #         self.created_by
    #     )

    # For extracting Items to recreate data rows
    def __repr__(self):
        return "{'asin': %r, 'name': %r, 'category_id': %r, 'description': %r, 'created_by': %r, 'small_image': %r, " \
               "'medium_image': %r, 'large_image': %r, 'brand': %r, 'list_price': %r, 'offers': %r}" % (
                   self.asin,
                   self.name,
                   self.category_id,
                   self.description,
                   self.created_by,
                   self.small_image,
                   self.medium_image,
                   self.large_image,
                   self.brand,
                   self.list_price,
                   self.offers
               )

    @property
    def serialize(self):
        return {
            "ID": self.id,
            "Name":     self.name,
            "ASIN": self.asin,
            "Description":  self.description,
            "Small Image":  self.small_image,
            "Medium Image":     self.medium_image,
            "Large Image":  self.large_image,
            "Brand":    self.brand,
            "List Price":   self.list_price,
            "Offers":   self.offers
        }

    @property
    def is_liked(self):
        if session.query(FavoriteItems).filter_by(user=current_user.id, item=self.id).first():
            return True
        else:
            return False

    @property
    def like_count(self):
        count = session.query(FavoriteItems).filter_by(item=self.id).count()
        return count

    @property
    def comments_count(self):
        count = session.query(Comments).filter_by(item=self.id).count()
        return count


# Users
class Users(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    social = Column(String, nullable=False, unique=True)
    nickname = Column(String, nullable=False)
    email = Column(String, nullable=True)
    picture = Column(String)
    favorites_categories = relationship('FavoritesCategories', backref='users')
    favorites_item = relationship('FavoriteItems', backref='users')
    comments = relationship('Comments', backref='users')
    thumbtack = relationship('Thumbtacks', backref='users')

    def __init__(self, social, nickname, email, picture):
        self.social = social
        self.nickname = nickname
        self.email = email
        self.picture = picture

    @property
    def admin_serialize(self):
        fav_categories = []
        for favorite in session.query(FavoritesCategories).filter_by(user=self.id).all():
            category = session.query(Categories).filter_by(id=favorite.category).first()
            fav_categories.append(category)
        favorite_categories = {}
        cat = 1
        if fav_categories:
            for favorite in fav_categories:
                favorite_categories['Category%i' % cat] = favorite.name
                cat += 1
        fav_items = []
        for favorite in session.query(FavoriteItems).filter_by(user=self.id).all():
            item = session.query(Items).filter_by(id=favorite.item).first()
            fav_items.append(item)
        favorite_items = {}
        it = 1
        if fav_items:
            for favorite in fav_items:
                favorite_items["Item%i" % it] = {}
                favorite_items["Item%i" % it]["Name"] = favorite.name
                favorite_items["Item%i" % it]["Category"] = favorite.category.name
                favorite_items["Item%i" % it]["Brand"] = favorite.brand
                it += 1
        comments = session.query(Comments).filter_by(user=self.id).all()
        user_comments = {}
        com = 1
        if comments:
            for comment in comments:
                user_comments["Comment%i" % com] = {}
                user_comments["Comment%i" % com]["Title"] = comment.title
                user_comments["Comment%i" % com]["Comment"] = comment.comment
                user_comments["Comment%i" % com]["Item"] = comment.item.name
                com += 1
        thumbtacks = session.query(Thumbtacks).filter_by(user=self.id).all()
        user_thumbtacks = {}
        thum = 1
        if thumbtacks:
            for thumb in thumbtacks:
                user_thumbtacks['Thumbtack%i' % thum] = {}
                user_thumbtacks['Thumbtack%i' % thum]['Kind'] = thumb.kind
                user_thumbtacks['Thumbtack%i' % thum]['Name'] = thumb.name
                user_thumbtacks['Thumbtack%i' % thum]['Category'] = thumb.category.name
                user_thumbtacks['Thumbtack%i' % thum]['Description'] = thumb.description
                thum += 1
        return {
            'ID': self.id,
            'Name': self.nickname,
            'Email': self.email,
            'Picture': self.picture,
            'Favorite Categories': favorite_categories,
            'Favorite Items': favorite_items,
            'Comments': user_comments,
            'Thumbtacks': user_thumbtacks
        }

    @property
    def public_serialize(self):
        fav_categories = []
        for favorite in session.query(FavoritesCategories).filter_by(user=self.id).all():
            category = session.query(Categories).filter_by(id=favorite.category).first()
            fav_categories.append(category)
        favorite_categories = {}
        cat = 1
        if fav_categories:
            for favorite in fav_categories:
                favorite_categories['Category%i' % cat] = favorite.name
                cat += 1
        fav_items = []
        for favorite in session.query(FavoriteItems).filter_by(user=self.id).all():
            item = session.query(Items).filter_by(id=favorite.item).first()
            fav_items.append(item)
        favorite_items = {}
        it = 1
        if fav_items:
            for favorite in fav_items:
                favorite_items["Item%i" % it] = {}
                favorite_items["Item%i" % it]["Name"] = favorite.name
                favorite_items["Item%i" % it]["Category"] = favorite.category.name
                favorite_items["Item%i" % it]["Brand"] = favorite.brand
                it += 1
        comments = session.query(Comments).filter_by(user=self.id).all()
        user_comments = {}
        com = 1
        if comments:
            for comment in comments:
                user_comments["Comment%i" % com] = {}
                user_comments["Comment%i" % com]["Title"] = comment.title
                user_comments["Comment%i" % com]["Comment"] = comment.comment
                user_comments["Comment%i" % com]["Item"] = comment.item.name
                com += 1
        thumbtacks = session.query(Thumbtacks).filter_by(user=self.id).all()
        user_thumbtacks = {}
        thum = 1
        if thumbtacks:
            for thumb in thumbtacks:
                user_thumbtacks['Thumbtack%i' % thum] = {}
                user_thumbtacks['Thumbtack%i' % thum]['Kind'] = thumb.kind
                user_thumbtacks['Thumbtack%i' % thum]['Name'] = thumb.name
                user_thumbtacks['Thumbtack%i' % thum]['Category'] = thumb.category.name
                user_thumbtacks['Thumbtack%i' % thum]['Description'] = thumb.description
                thum += 1
        return {
            'ID': self.id,
            'Name': self.nickname,
            'Picture': self.picture,
            'Favorite Categories': favorite_categories,
            'Favorite Items': favorite_items,
            'Comments': user_comments,
            'Thumbtacks': user_thumbtacks
        }

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)
        except NameError:
            return str(self.id)

    def __repr__(self):
        return '<User %r>' % self.nickname

    @property
    def is_admin(self):
        if self.email == CATALOG_ADMIN:
            return True
        else:
            return False


# Favorite Categories
class FavoritesCategories(Base):
    __tablename__ = "favoritescategories"
    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey('users.id'))
    category = Column(Integer, ForeignKey('categories.id'))
    category_relation = relationship('Categories',
                                     backref='favoritescategories')

    def __init__(self, user, category):
        self.user = user
        self.category = category

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'User': self.user.nickname,
            'Category': self.category.name
        }


# Favorite Items
class FavoriteItems(Base):
    __tablename__ = 'favoriteitems'
    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey('users.id'))
    item = Column(Integer, ForeignKey('items.id'))

    def __init__(self, user, item):
        self.user = user
        self.item = item

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'User': self.user.nickname,
            'Item': self.item.name
        }


# Comments on Items
class Comments(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey('users.id'))
    item = Column(Integer, ForeignKey('items.id'))
    title = Column(String)
    comment = Column(Text)
    time = Column(DATETIME)
    admin_screened = Column(Boolean, default=False)

    def __init__(self, user, item, title, comment, time):
        self.user = user
        self.item = item
        self.title = title
        self.comment = comment
        self.time = time

    @property
    def user_name(self):
        user_name = session.query(Users).filter_by(id=self.user).first()
        return user_name.nickname

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'User': self.user.nickname,
            'Item': self.item.name,
            'Title': self.title,
            'Comment': self.comment,
            'Time': self.time
        }


# Amazon API
# Nodes
class CategoryNodes(Base):
    __tablename__ = 'categorynodes'
    id = Column(Integer, primary_key=True)
    category = Column(Integer, ForeignKey('categories.id'))
    category_relation = relationship('Categories',
                                     backref='category_nodes')
    amazon_node = Column(String)
    search_index = Column(String)
    keywords = Column(String)

    @property
    def is_good_match(self):
        return True

    def __init__(self, category, amazon_node, search_index, keywords):
        self.category = category
        self.amazon_node = amazon_node
        self.search_index = search_index
        self.keywords = keywords

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'Category': self.category.name,
            'Amazon Node': self.amazon_node,
            'Search Index': self.search_index.search_index,
            'Keywords': self.keywords,
        }


# Amazon Search
class AmazonSearches(Base):
    __tablename__ = 'amazonsearches'
    id = Column(Integer, primary_key=True)
    category = Column(Integer, ForeignKey('categories.id'))
    category_relation = relationship('Categories',
                                     backref='amazonsearches')
    keyword = Column(String, nullable=False)
    search_index = Column(String, nullable=False)
    sort = Column(String, nullable=False)
    amazon_node = Column(Integer, ForeignKey('categorynodes.id'))
    node_relation = relationship('CategoryNodes',
                                 backref='amazonsearches')
    response_group = Column(String)
    max_pages = Column(Integer)

    def __init__(self, category, keyword, search_index, sort, amazon_node, response_group):
        self.category = category
        self.keyword = keyword
        self.search_index = search_index
        self.sort = sort
        self.amazon_node = amazon_node
        self.response_group = response_group

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'Category': self.category.name,
            'Amazon Node': self.amazon_node.amazon_node,
            'Search Index': self.search_index.search_index,
            'Keywords': self.keyword,
            'Sort': self.sort,
            'Response_group': self.response_group,
            'Maximum Page Results': self.max_pages
        }


# Amazon Search Index List
class AmazonSearchIndex(Base):
    __tablename__ = 'amazonsearchindex'
    id = Column(Integer, primary_key=True)
    search_index = Column(String)

    def __init__(self, search_index):
        self.search_index = search_index

    @property
    def serialize(self):
        return {
            "Search Index Id": self.id,
            "Search Index": self.search_index
        }


# Amazon Returned Items from search
class AmazonReturnedItems(Base):
    __tablename__ = 'amazonreturneditems'
    id = Column(Integer, primary_key=True)
    amazon_search = Column(Integer, ForeignKey('amazonsearches.id'))
    search_relation = relationship('AmazonSearches',
                                   backref='amazonreturneditems')
    asin = Column(String)
    page = Column(Integer)
    is_acceptable = Column(Boolean, default=True)

    def __init__(self, amazonsearch_id, asin, page):
        self.amazonsearch_id = amazonsearch_id
        self.asin = asin
        self.page = page

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'Amazon Search Id': self.amazonsearch_id,
            'ASIN': self.asin,
            'Page': self.page,
            'Acceptable': self.is_acceptable
        }


class Thumbtacks(Base):
    __tablename__ = 'thumbtacks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(Enum('category', 'item', 'idea'))
    user = Column(Integer, ForeignKey('users.id'))
    category = Column(Integer, ForeignKey('categories.id'))
    description = Column(Text)
    asin = Column(String)
    image = Column(String)
    admin_screened = Column(Boolean, default=False)

    def __init__(self, name, kind, user, category, description):
        self.name = name
        self.kind = kind
        self.user = user
        self.category = category
        self.description = description

    @property
    def user_name(self):
        user_name = session.query(Users).filter_by(id=self.user).first()
        return user_name.nickname

    @property
    def serialize(self):
        return {
            'ID': self.id,
            'Name': self.name,
            'Kind': self.kind,
            'Creator': self.user.nickname,
            'Category': self.category.name,
            'Category ID': self.category,
            'Description': self.description
        }