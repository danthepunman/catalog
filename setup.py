import os
import ast
from pip import main
from flask.ext.script import Manager, prompt_bool, prompt
import app.database
from migrate.exceptions import DatabaseAlreadyControlledError
from app.models import Categories, Items

manager = Manager(usage='Initial Setup')


@manager.command
def start_here():
    if prompt_bool('Is this the initial setup?'):
        requirements()
        print 'requirements done'
        database_setup()
        print 'database setup'
        edit_config()
        print 'config done'
        client_secrets()
        print 'client secrets done'
        items_restored()
        print 'items restored'
    else:
        print 'Please run the setup manager with the individual commands. '
        print 'For database commands enter "python manage.py database" instead.'
    return


@manager.command
def requirements():
    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir)
    source_file = 'requirements.txt'
    main(['install', '-r', source_file])
    return


@manager.command
def database_setup():
    try:
        app.database.init_db()
    except DatabaseAlreadyControlledError:
        app.database.migrate_db()
    else:
        app.database.create_categories()
        app.database.create_search_index()
        app.database.test()
    return


@manager.command
def items_restored():
    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/app/admin/Items_Backup")
    source_file = 'items_database_categories.py'
    categories_list = []
    # Open the original file default is read only
    with open(source_file) as f:
        # iterate over the lines of the original file
        for line in f:
            split_line = line.split(']')
            split2_line = split_line[0].split('[')
            categories_ids = split2_line[1].split(',')
            categories_list = categories_list + categories_ids
    f.close()
    for category in categories_list:
        # Get the category that the items are being recovered.
        category_obj = app.database.session.query(Categories).filter_by(id=category).first()
        # Establish the root path on the operating system
        basedir = os.path.abspath(os.path.dirname(__file__))
        # Change the working directory to the backup directory
        os.chdir(basedir + "/app/admin/Items_Backup")
        # Open the file that is being used in the recovery
        with open('items_database_export_%s.py' % category_obj.name) as f:
            # iterate ove the lines of the file
            for lines in f:
                if lines.startswith('{'):
                    # ast evaluates the string as an object.
                    item = ast.literal_eval(lines)
                    # create an Items object with the details from the line.
                    new_item = Items(asin=item['asin'], name=item['name'], category_id=item['category_id'],
                                     description=item['description'], created_by='Category')
                    # add the new item
                    app.database.session.add(new_item)
                    app.database.session.commit()
                    # add on the other elements of the item that is not passed in the initiation of the object
                    new_item.small_image = item['small_image']
                    new_item.medium_image = item['medium_image']
                    new_item.large_image = item['large_image']
                    new_item.brand = item['brand']
                    new_item.list_price = item['list_price']
                    new_item.offers = item['offers']
                    app.database.session.add(new_item)
                    app.database.session.commit()

    print 'Items have be recovered'
    return


@manager.command
def edit_config():
    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/app")
    source_file = 'default_config.py'
    edited_file = source_file + '.temp'
    try:
        with open(source_file) as f:
            e = open(edited_file, 'w', 1)
            for lines in f:
                if lines.startswith('CATALOG'):
                    admin = prompt('What is the admins email? (Must match google sign-in!!')
                    e.write("CATALOG_ADMIN = '%s' \n" % (admin, ))
                elif lines.startswith('AWSACCESSKEYID'):
                    aws_key = prompt('Please enter amazon access key: ')
                    e.write("AWSACCESSKEYID = '%s' \n" % (aws_key, ))
                elif lines.startswith('AWSSECRETKEY'):
                    aws_secret = prompt('Please enter amazon secret key: ')
                    e.write("AWSSECRETKEY = '%s' \n" % (aws_secret, ))
                    print 'Successfully added keys and secrets'
                else:
                    e.write(lines)
            # Close both files
            f.close()
            e.close()
            # Delete the original
            os.remove(source_file)
            # Rename the temp with the original file
            os.rename(edited_file, source_file)
    except IOError:
        print 'Sorry. Could not open the file. Please go to default_config and enter the data manually'


@manager.command
def client_secrets():

    # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir + "/app")
    source_file = 'client_secrets.json'
    edit_file = source_file + '.temp'
    with open(source_file) as f:
        e = open(edit_file, 'w', 1)
        for line in f:
            if line.startswith('{'):
                new_line = line.split('need_key')
                client_id = prompt("Enter the client id for Google oauth")
                # Request the key
                secret = prompt('What is the Google client secret?')
                e.write('%s%s%s%s%s' % (new_line[0], client_id, new_line[1], secret, new_line[2]))
        # Close both files
        f.close()
        e.close()
        # Delete the original
        os.remove(source_file)
        # Rename the temp file with the original name
        os.rename(edit_file, source_file)
    print 'Thank you'
    return
