#!/usr/bin/env python
import os
from app import create_app, db
from app.models import Categories, Users, Items, FavoritesCategories, CategoriesNode, AmazonSearch, Comments
from app.models import Thumbtacks, FavoriteItems, AmazonReturnedItems, AmazonSearchIndex
from app.database import session

from flask.ext.script import Manager, Shell

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)


from app.database import manager as database_manager
from setup import manager as setup_manager


# With manager, we can work with the app at the command line.
def make_shell_context():
    return dict(app=app, db=db,  Categories=Categories, Users=Users, Items=Items, Comments=Comments,
                FavoritesCategories=FavoritesCategories, CategoriesNode=CategoriesNode, AmazonSearch=AmazonSearch,
                Thumbtacks=Thumbtacks, FavoriteItems=FavoriteItems, AmazonReturnedItems=AmazonReturnedItems,
                AmazonSearchIndex=AmazonSearchIndex, session=session)
# Calling python manage.py shell will give you python command line and you can use session to
# test queries
manager.add_command("shell", Shell(make_context=make_shell_context))
# Calling python manage.py database will give you a list of commands to manage the database
manager.add_command('database', database_manager)
manager.add_command('setup', setup_manager)

# if this file is called by its self the manager will activate the server and launch the app.
# debug is default
if __name__ == '__main__':
    manager.run()
