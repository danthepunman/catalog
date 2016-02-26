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
    # Creates the foreign key for the parent of the category
    parent_id = Column(Integer, ForeignKey(id))
    name = Column(String, nullable=False)
    children = relationship('Categories',
                            cascade='all, delete-orphan',
                            backref=backref('parent', remote_side=id),
                            collection_class=attribute_mapped_collection('name')
                            )
    thumbtack = relationship('Thumbtacks', backref='categories')

    # Object initiation
    def __init__(self, name, parent_id=None):
        self.name = name
        self.parent_id = parent_id

    # Object representation
    def __repr__(self):
        return 'Categories(name=%r, id=%r, parent_id=%r)' % (
            self.name,
            self.id,
            self.parent_id
        )

    # A way to present the tree with indentation
    def dump(self, _indent=0):
        return "    " * _indent + repr(self) + "\n" + "".join([c.dump(_indent + 1)
                                                               for c in self.children.values()])

    # Gets the parents name
    @property
    def parents_name(self):
        parent = session.query(Categories).filter_by(id=self.parent_id).first()
        return parent.name


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

    # Object initiation
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
            "Name":     self.name,
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
    social = Column(String(64), nullable=False, unique=True)
    nickname = Column(String(64), nullable=False)
    email = Column(String(64), nullable=True)
    picture = Column(String)
    favorites_categories = relationship('FavoritesCategories', backref='users')
    favorites_item = relationship('FavoriteItems', backref='users')
    comments = relationship('Comments', backref='users')
    thumbtack = relationship('Thumbtacks', backref='users')

    # Object initiation
    def __init__(self, social, nickname, email, picture):
        self.social = social
        self.nickname = nickname
        self.email = email
        self.picture = picture

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

    # Object representation
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

    # Object initiation
    def __init__(self, user, category):
        self.user = user
        self.category = category

    # Object representation
    def __repr__(self):
        user_obj = session.query(Users).filter_by(id=self.user).first()
        category_obj = session.query(Categories).filter_by(id=self.category).first()
        return '<User %r likes %r>' % (user_obj.nickname, category_obj.name)


# Favorite Items
class FavoriteItems(Base):
    __tablename__ = 'favoriteitems'
    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey('users.id'))
    item = Column(Integer, ForeignKey('items.id'))

    # Object initiation
    def __init__(self, user, item):
        self.user = user
        self.item = item

    # Object representation
    def __repr__(self):
        user_obj = session.query(Users).filter_by(id=self.user).first()
        item_obj = session.query(Items).filter_by(id=self.item).first()
        return '<User %r likes %r>' % (user_obj.nickname, item_obj.name)


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

    # Object initiation
    def __init__(self, user, item, title, comment, time):
        self.user = user
        self.item = item
        self.title = title
        self.comment = comment
        self.time = time

    # Object representation
    def __repr__(self):
        return '<%r>' % self.title

    @property
    def user_name(self):
        user_name = session.query(Users).filter_by(id=self.user).first()
        return user_name.nickname


# Amazon API
# Nodes
class CategoriesNode(Base):
    __tablename__ = 'categoriesnode'
    id = Column(Integer, primary_key=True)
    category = Column(Integer, ForeignKey('categories.id'))
    category_relation = relationship('Categories',
                                     backref='categories_node')
    amazon_node = Column(String)
    search_index = Column(String)
    keywords = Column(String)

    @property
    def is_good_match(self):
        return True

    # Object initiation
    def __init__(self, category, amazon_node, search_index, keywords):
        self.category = category
        self.amazon_node = amazon_node
        self.search_index = search_index
        self.keywords = keywords

    # Object representation
    def __repr__(self):
        category_obj = session.query(Categories).filter_by(id=self.category).first()
        return '<Category: %r, Node: %r, Search Index: %r>' % (category_obj.name, self.amazon_node, self.search_index)


# Amazon Search
class AmazonSearch(Base):
    __tablename__ = 'amazonsearch'
    id = Column(Integer, primary_key=True)
    category = Column(Integer, ForeignKey('categories.id'))
    category_relation = relationship('Categories',
                                     backref='amazonsearch')
    keyword = Column(String(64), nullable=False)
    search_index = Column(String(64), nullable=False)
    sort = Column(String(64), nullable=False)
    amazon_node = Column(Integer, ForeignKey('categoriesnode.id'))
    node_relation = relationship('CategoriesNode',
                                 backref='amazonsearch')
    response_group = Column(String(64))
    max_pages = Column(Integer)

    # Object initiation
    def __init__(self, category, keyword, search_index, sort, amazon_node, response_group):
        self.category = category
        self.keyword = keyword
        self.search_index = search_index
        self.sort = sort
        self.amazon_node = amazon_node
        self.response_group = response_group

    # Object representation
    def __repr__(self):
        category_obj = session.query(Categories).filter_by(id=self.category).first()
        return '<Category: %r, Keywords: %r, Node: %r, Search Index: %r>' % (category_obj.name, self.keyword, self.amazon_node, self.search_index)


# Amazon Search Index List
class AmazonSearchIndex(Base):
    __tablename__ = 'amazonsearchindex'
    id = Column(Integer, primary_key=True)
    search_index = Column(String(64))

    # Object initiation
    def __init__(self, search_index):
        self.search_index = search_index

    def __repr__(self):
        return '<%r>' % self.search_index


# Amazon Returned Items from search
class AmazonReturnedItems(Base):
    __tablename__ = 'amazonreturneditems'
    id = Column(Integer, primary_key=True)
    amazonsearch_id = Column(Integer, ForeignKey('amazonsearch.id'))
    search_relation = relationship('AmazonSearch',
                                   backref='amazonreturneditems')
    asin = Column(String(32))
    page = Column(Integer)
    is_acceptable = Column(Boolean, default=True)

    # Object initiation
    def __init__(self, amazonsearch_id, asin, page):
        self.amazonsearch_id = amazonsearch_id
        self.asin = asin
        self.page = page

    # Object representation
    def __repr__(self):
        category_obj = session.query(Categories).filter_by(id=self.category).first()
        return '<Search id: %r, asin: %r, page: %r>' % (self.amazonsearch_id, self.asin, self.page)


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

    # Object initiation
    def __init__(self, name, kind, user, category, description):
        self.name = name
        self.kind = kind
        self.user = user
        self.category = category
        self.description = description

    def __repr__(self):
        return '<%r>' % self.name

    @property
    def user_name(self):
        user_name = session.query(Users).filter_by(id=self.user).first()
        return user_name.nickname
