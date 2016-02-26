import os.path
from migrate.versioning import api
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from default_config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO
from flask.ext.script import Manager, prompt_bool
import models

__author__ = 'Daniel'

manager = Manager(usage='Perform database operations')

engine = create_engine(SQLALCHEMY_DATABASE_URI, convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()
session = Session(engine)


# Initiates the database. catalog.db cannot exists.
@manager.command
def init_db():
    import models
    Base.metadata.create_all(bind=engine)
    if not os.path.exists(SQLALCHEMY_MIGRATE_REPO):
        api.create(SQLALCHEMY_MIGRATE_REPO, 'database repository')
        api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    else:
        api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, api.version(SQLALCHEMY_MIGRATE_REPO))


# Migrates the database if any changes have been made to the models.py schema
@manager.command
def migrate_db():
    import imp
    v = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    migration = SQLALCHEMY_MIGRATE_REPO + ('/versions/%03d_migration.py' % (v+1))
    tmp_module = imp.new_module('old_model')
    old_model = api.create_model(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    exec(old_model, tmp_module.__dict__)
    script = api.make_update_script_for_model(SQLALCHEMY_DATABASE_URI,
                                              SQLALCHEMY_MIGRATE_REPO,
                                              tmp_module.meta,
                                              Base.metadata)
    open(migration, "wt").write(script)
    api.upgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    v = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    print('New migration saved as' + migration)
    print('Current database version' + str(v))


# Checks if categories exists in the database.
@manager.command
def check_db():
    test_categories = session.query(models.Categories).all()
    if not test_categories:
        if prompt_bool('There are no categories. Would you like to create categories?'):
            create_categories()

    else:
        print "Categories are present"
    return


# Same as check_db but without the dialog
@manager.command
def test():
    test_categories = session.query(models.Categories).all()
    if test_categories:
        print "Datebase is ready"
    return


# Performs the drop_all() on the database
@manager.command
def empty_db():
    import models
    Base.metadata.drop_all(bind=engine)
    return


# Sets up all the categories in a tree
@manager.command
def create_categories():
    # root created first since the others are children to Root
    root = models.Categories(name='Root')
    session.add(root)
    session.commit()
    # child of root: these are the main categories under root
    children_of_root = ['Sports', 'Music', 'Electronics', 'Vehicles', 'Cooking']
    for child in children_of_root:
        c = models.Categories(name=child, parent_id=root.id)
        session.add(c)
    session.commit()

    # internal function to add all the other categories
    def children_of_category(children_list, category):
        parent = session.query(models.Categories).filter_by(name=category).first()
        for children in children_list:
            new_category = models.Categories(name=children, parent_id=parent.id)
            session.add(new_category)
        session.commit()
        return

    # List of sub-categories for each category
    children_of_sports = ['Baseball', 'Basketball', 'Football', 'Hockey']
    children_of_baseball = ['Baseball Equipment', 'Baseball Clothing']
    children_of_baseballequipment = ['Baseball Bats', 'Baseball Balls', 'Baseball Gloves', "Catcher's Gear",
                                     "Umpire's Gear"]
    children_of_gloves = ['Batting Gloves', "Fielder's Glove", "Catcher's Mit"]
    children_of_catchersgear = ['Shin Guards', "Catcher's Chest Protector", "Catcher's Face Mask"]
    children_of_umpiresgear = ['Umpire Face Mask', 'Umpire Chest Protector', 'Brush', 'Ball Bag']
    children_of_basketball = ['Basketball Equipment', 'Basketball Clothing']
    children_of_basketballequipment = ['Basketball Hoops', 'Basketball Nets', 'Basketball Backboards',
                                       'Basketball Stands', 'Basketballs']
    children_of_football = ['Football Equipment', 'Football clothing']
    children_of_footballequipment = ['Footballs', 'Kicking Tees', 'Football Pads', 'Football Helmets']
    children_of_hockey = ['Hockey Equipment', 'Hockey Clothing']
    children_of_hockeyequipment = ['Hockey Pads', 'Hockey Helmets', 'Sticks', 'Pucks']
    children_of_music = ['Recorded Music', 'Musical Instruments', 'Recording']
    children_of_recorded = ['Albums', 'Songs', 'Concerts']
    children_of_albums = ['Rock Albums', 'HipHop Albums', 'Adult Albums', 'Children Albums', 'Country Albums',
                          'Inspirational Albums', 'Latin Albums']
    children_of_songs = ['Rock Songs', 'HipHop Songs', 'Adult Songs', 'Children Songs', 'Country Songs',
                         'Inspirational Songs', 'Latin Songs']
    children_of_instruments = ['Electric Instruments', 'String Instruments', 'Percussion', 'Brass Instruments']
    children_of_electricinstruments = ['Electric Guitars', 'Electric Bass', 'Piano Keyboards']
    children_of_recording = ['Microphones', 'Pickups', 'Software', 'Mixing Boards']
    children_of_electronics = ['Computers', 'Audio/Video', 'Lighting', 'Remote Control']
    children_of_computers = ['Monitors', 'Computer Systems', 'Computer Keyboards', 'Mouse', 'Hard Drives',
                             'Card Readers', 'Computer Software', 'Experimental Boards']
    children_of_monitors = ['LED Monitors', 'LCD Monitors']
    children_of_computersystems = ['All-in-One Systems', 'Bare Bones Systems', 'Gaming Systems']
    children_of_computerkeyboards = ['Wired Keyboards', 'Wireless Keyboard']
    children_of_mouse = ['Wired Mouse', 'Wireless Mouse']
    children_of_harddrives = ['SSD', 'Flash']
    children_of_audiovideo = ["TV's", "Sound Systems", 'DVD/BlueRay Players', 'Mobile Speakers']
    children_of_tvs = ['LED TV', 'LCD TV', 'Plasma TV']
    children_of_lighting = ['Black Lights', 'Disco Balls', 'Lava Lamps', 'LED Lights', 'Solar Lights',
                            'Christmas Lights']
    children_of_remotecontrol = ["Complete Units", "Shells", 'Motors', 'Controllers', 'Radio Receivers']
    children_of_vehicles = ['Cars', "ATV's", 'Boats', 'Motorcycles']
    children_of_cars = ['Model Cars', 'Posters', 'Accessories']
    children_of_atvs = ['Four Wheelers', 'Dune Buggies', 'Go Carts']
    children_of_boats = ['Fishing Boats', 'Canoes', 'Sailboats', 'Pontoons']
    children_of_motorcycles = ['Dirt Bikes', 'Mini Bikes', 'Tires']
    children_of_cooking = ['Baking', 'Grilling', 'Ethnic Flavors', 'Diets']
    children_of_baking = ['Oven Dishes', 'Thermometers', 'Foil and Paper']
    children_of_grilling = ['Grilling Utensils', 'Seasons', 'Lighters', 'Lights']
    children_of_ethnicflavors = ['Latin', 'Asian', 'Mediterranean', 'Soul', 'European']
    children_of_diets = ['Weight Watchers', 'Atkins', 'Paleo']
    # Calling the internal function for each of the lists
    children_of_category(children_of_sports, 'Sports')
    children_of_category(children_of_baseball, 'Baseball')
    children_of_category(children_of_basketball, 'Basketball')
    children_of_category(children_of_football, 'Football')
    children_of_category(children_of_hockey, 'Hockey')
    children_of_category(children_of_music, 'Music')
    children_of_category(children_of_recorded, 'Recorded Music')
    children_of_category(children_of_instruments, 'Musical Instruments')
    children_of_category(children_of_recording, 'Recording')
    children_of_category(children_of_electronics, 'Electronics')
    children_of_category(children_of_computers, 'Computers')
    children_of_category(children_of_audiovideo, 'Audio/Video')
    children_of_category(children_of_lighting, 'Lighting')
    children_of_category(children_of_remotecontrol, 'Remote Control')
    children_of_category(children_of_vehicles, 'Vehicles')
    children_of_category(children_of_cars, 'Cars')
    children_of_category(children_of_atvs, "ATV's")
    children_of_category(children_of_boats, 'Boats')
    children_of_category(children_of_motorcycles, 'Motorcycles')
    children_of_category(children_of_cooking, 'Cooking')
    children_of_category(children_of_baking, 'Baking')
    children_of_category(children_of_grilling, 'Grilling')
    children_of_category(children_of_ethnicflavors, 'Ethnic Flavors')
    children_of_category(children_of_diets, 'Diets')
    children_of_category(children_of_baseballequipment, 'Baseball Equipment')
    children_of_category(children_of_gloves, 'Baseball Gloves')
    children_of_category(children_of_catchersgear, "Catcher's Gear")
    children_of_category(children_of_umpiresgear, "Umpire's Gear")
    children_of_category(children_of_basketballequipment, 'Basketball Equipment')
    children_of_category(children_of_footballequipment, 'Football Equipment')
    children_of_category(children_of_hockeyequipment, 'Hockey Equipment')
    children_of_category(children_of_albums, 'Albums')
    children_of_category(children_of_songs, 'Songs')
    children_of_category(children_of_electricinstruments, 'Electric Instruments')
    children_of_category(children_of_monitors, 'Monitors')
    children_of_category(children_of_computersystems, 'Computer Systems')
    children_of_category(children_of_computerkeyboards, 'Computer Keyboards')
    children_of_category(children_of_mouse, 'Mouse')
    children_of_category(children_of_harddrives, 'Hard Drives')
    children_of_category(children_of_tvs, "TV's")
    return


# Creates the list of search_indices used by Amazon in their api search
@manager.command
def create_search_index():
    search_index = ['All', 'Wine', 'Wireless', 'ArtsAndCrafts', 'Miscellaneous', 'Electronics', 'Jewelry', 'MobileApps',
                    'Photo', 'Shoes', 'KindleStore', 'Automotive', 'Pantry', 'MusicalInstruments', 'DigitalMusic',
                    'GiftCards', 'FashionBaby', 'FashionGirls', 'GourmetFood', 'HomeGarden', 'MusicTracks',
                    'UnboxVideo', 'FashionWomen', 'VideoGames', 'FashionMen', 'Kitchen', 'Video', 'Software', 'Beauty',
                    'Grocery', 'FashionBoys', 'Industrial', 'PetSupplies', 'OfficeProducts', 'Magazines', 'Watches',
                    'Luggage', 'OutdoorLiving', 'Toys', 'SportingGoods', 'PCHardware', 'Movies', 'Books',
                    'Collectibles', 'VHS', 'MP3Downloads', 'Fashion', 'Tools', 'Baby', 'Apparel', 'Marketplace', 'DVD',
                    'Appliances', 'Music', 'LawnAndGarden', 'WirelessAccessories', 'Blended', 'HealthPersonalCare',
                    'Classical']
    for i in search_index:
        index = models.AmazonSearchIndex(i)
        session.add(index)
    session.commit()


# A quick way to drop_all, migrate, add categories and amazon search indices
@manager.command
def reset_db():
    empty_db()
    print 'Empty db'
    migrate_db()
    print 'init_db'
    create_search_index()
    print 'search_index created'
    create_categories()
    print 'categories created'
    return

