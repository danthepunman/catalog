# Hobby Catalog Website - pages full of fun

## Class Project:
This is a project for Udacity.com Full Stack Nanodegree.
Using the Flask framework this app creates a website of categories, items, comments, and thumbtacks. It provides tools for the admin to create and change the categories, populate the categories with items using Amazon's api, review user's comments and thumbtacks.  Users, logging in with Google's oauth, can add comments on items, add thumbtacks to categories, even suggest items from Amazon for the category.  Since the info for the items is from Amazon, it cannot be altered.

## Prerequisites:

- Python 2.7
- An account with [Amazon's Associates](http://docs.aws.amazon.com/AWSECommerceService/latest/DG/becomingAssociate.html)
- An account with Google and have an API key for Oauth2

## Installation:

- Clone the app from Github
- 
- From the commandline while in the apps root directory (contains setup.py and manage.py) run the setup.py file:
    - ~$ python manage.py setup start_here
- At the prompts:
    - Affirm if it is the first time running
    - Enter the admin's email (must match the Admin's Google sign in)
    - Enter your credentials for Amazon Associates
    - Enter the client id and secret key for Google
- Start the server from the commandline (same directory)
    - ~$ python manage.py runserver
- Note if using vagrant you have to add host
    - ~$ python manage.py runserver -h 0.0.0.0 -p 5000

## Operations:

### Commandline

Many operations can be done from the commandline.

- ~$ python manage.py shell
    - Gives a python commandline
    - With session.query you can perform searches on the database
- ~$ python manage.py setup \<command\>
    - This first group of commands are done at the installation phase with the 'start_here' command
    - Requirements = Runs the requirements file through pip install to verify that all packages are installed.
    - items_restored = Restores the items. After initial run, this feature should be done inside the web browser. There, it checks if items already exists inside the category.
    - edit_config = Will ask for the admin email and amazon id and key. 
    - client_secrets = Will ask for the Google id and secret key but will only work if the phrase 'need_key' is in those spots in client_secrets.json
    - database_setup = Don't use. Refer to next group of commands
- ~$ python manage.py database \<command\>
    - init_db = Initiates the database. Run only if 'catalog.db' does not exists.
    - migrate_db = If 'catalog.db' exists this will update the database of any changes made to the schema in 'models.py'
    - check_db = Checks for categories. If none exists, it will ask if you would like to create them.
    - test = Same as check_db but without the dialog
    - empty_db = Opposite of init_db. Drops all tables in the database.
    - create_categories = Adds all the categories to the database.  If you want to change the name of the categories in the mass create_categories, look at database.py.  If you change the name of a category that is a parent to other categories, then you need to change the name in the function call that inputs its children into the database.
    - create_search_index = Populates the table for Amazon indices. Used to narrow the search for items from Amazon API
    - reset_db = Resets the database by calling 'empty_db', 'migrate_db', 'create_search_index', and 'create_categories'

### Homepage

- On the web browser go to 127.0.0.1:5000/catalog
- By clicking on Login, you can sign in using Google

### Admin

The admin has a lot options and can get a pulse of the site from the admin's home page.  The admin's navigation bar has links to categories and items. These pages includes all of them in the database. The first section includes quick links to many operations. The next section gives an overview of site by numbers.  It's broken down to categories, items, users, comments and thumbtacks.

### Categories

Categories are first add at the time of setup. This mass adding of categories can be done at any time. Make sure to empty the database before calling the create_categories function. Otherwise you will have duplicates.  You can also add single or groups of five categories. Either from the admin's homepage, all categories page or within the catalog itself (the user side of the website).  You can edit and delete categories as you see fit.

### Items

Now for some fun!!! I chose to integrate the site with items from Amazon.
To add items:

- First retrieve an item number (ASIN) from the Amazon Website that matches the categories topic.
- When the admin selects the link to add items, the form will ask for the ASIN, Search Index that the item falls under, and the name of the category is inserted as the keywords.  The admin can adjust the keywords if needed.  I have found that adding the parent category helps narrow down the search.
- The next page will give ten items. If they match the category, accept the node. If the admin declines it will refresh the first form and ask that the admin enter a different ASIN or change the keywords.
- This will bring up the items again with a picture. If an item does not belong, the admin can select 'Remove Item' and it will be removed.
- If there are more items available for the current search, the admin can select the page number at the bottom of the page.
- Once the admin is done retrieving items, select the category name at the top.  It will take the admin to the catalog where the items can be viewed in the in the catalog.
- If the admin selects to add items in a category that has already has items, it will give the admin the option to reuse the node and search that is saved in the database.
- One of the quick links at the top of the admin page is 'Amazon Searches'. It will give the admin a page of all the Amazon nodes and searches in the database. You can reuse them or delete them.
- Since the info is from Amazon and part of the API agreement, it cannot be altered.

### Users

- Users are logged in using Google.
- Each user has their own profile page. 
- The public profile page for the user does not show their email.
- They can favorite categories and items. Both show up on the right side of the page when they are logged in.

### Comments

- Users can comment on items.
- They can edit and delete their own comments.
- The admin has a link that shows all the comments that need to be reviewed.  If they are found inappropriate, they can be deleted. If the admin selects approve, it flags it in the database and removes it from the list.
- The admin also has a dashboard that shows the category name next to the comment to get a snapshot that comments are staying on topic.

### Thumbtacks

- Users can give suggestions for categories.
- There are three types
    - Categories: If they want to suggest a sub category for the given category.
    - Idea: Just like a comment but for the category
    - Item: If there is an Amazon item that they would like to suggest. They enter the ASIN number. Verify that it is correct and the item is presented as a thumbtack.
- Categories and Ideas can be edited and deleted by the User. Items can only be deleted.
- Like Comments, the admin can review thumbtacks, approving and deleting as they see fit.

### Item Backup and recovery

- Under normal operations this would not be necessary.  But since there is a cap on the API calls, I wanted to provide a quick way to populate the categories with items for the reviewer of this project. 