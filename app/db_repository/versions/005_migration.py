from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
sessions = Table('sessions', pre_meta,
    Column('id', INTEGER, primary_key=True, nullable=False),
    Column('session_id', VARCHAR(length=256)),
    Column('data', TEXT),
    Column('expiry', DATETIME),
)

amazonreturneditems = Table('amazonreturneditems', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('amazonsearch_id', Integer),
    Column('asin', String(length=32)),
    Column('page', Integer),
    Column('is_acceptable', Boolean, default=ColumnDefault(True)),
)

amazonsearch = Table('amazonsearch', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('category', Integer),
    Column('keyword', String(length=64), nullable=False),
    Column('search_index', String(length=64), nullable=False),
    Column('sort', String(length=64), nullable=False),
    Column('amazon_node', Integer),
    Column('response_group', String(length=64)),
    Column('max_pages', Integer),
)

amazonsearchindex = Table('amazonsearchindex', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('search_index', String(length=64)),
)

categories = Table('categories', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('parent_id', Integer),
    Column('name', String, nullable=False),
)

categoriesnode = Table('categoriesnode', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('category', Integer),
    Column('amazon_node', String),
    Column('search_index', String),
    Column('keywords', String),
)

comments = Table('comments', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('user', Integer),
    Column('item', Integer),
    Column('title', String),
    Column('comment', Text),
    Column('time', DATETIME),
    Column('admin_screened', Boolean, default=ColumnDefault(False)),
)

favoriteitems = Table('favoriteitems', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('user', Integer),
    Column('item', Integer),
)

favoritescategories = Table('favoritescategories', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('user', Integer),
    Column('category', Integer),
)

items = Table('items', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('asin', String),
    Column('category_id', Integer),
    Column('name', String, nullable=False),
    Column('description', Text, nullable=False),
    Column('small_image', String),
    Column('medium_image', String),
    Column('large_image', String),
    Column('brand', String),
    Column('list_price', String),
    Column('offers', String),
    Column('created_by', Enum('Category', 'Thumbtack')),
)

thumbtacks = Table('thumbtacks', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String, nullable=False),
    Column('kind', Enum('category', 'item', 'idea')),
    Column('user', Integer),
    Column('category', Integer),
    Column('description', Text),
    Column('asin', String),
    Column('image', String),
    Column('admin_screened', Boolean, default=ColumnDefault(False)),
)

users = Table('users', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('social', String(length=64), nullable=False),
    Column('nickname', String(length=64), nullable=False),
    Column('email', String(length=64)),
    Column('picture', String),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['sessions'].drop()
    post_meta.tables['amazonreturneditems'].create()
    post_meta.tables['amazonsearch'].create()
    post_meta.tables['amazonsearchindex'].create()
    post_meta.tables['categories'].create()
    post_meta.tables['categoriesnode'].create()
    post_meta.tables['comments'].create()
    post_meta.tables['favoriteitems'].create()
    post_meta.tables['favoritescategories'].create()
    post_meta.tables['items'].create()
    post_meta.tables['thumbtacks'].create()
    post_meta.tables['users'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['sessions'].create()
    post_meta.tables['amazonreturneditems'].drop()
    post_meta.tables['amazonsearch'].drop()
    post_meta.tables['amazonsearchindex'].drop()
    post_meta.tables['categories'].drop()
    post_meta.tables['categoriesnode'].drop()
    post_meta.tables['comments'].drop()
    post_meta.tables['favoriteitems'].drop()
    post_meta.tables['favoritescategories'].drop()
    post_meta.tables['items'].drop()
    post_meta.tables['thumbtacks'].drop()
    post_meta.tables['users'].drop()
