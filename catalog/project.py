from flask import Flask, render_template, request, redirect, jsonify, url_for, flash

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc

from database_setup import Base, Category, Item, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
						open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"


engine = create_engine('sqlite:///catalogitems.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#Login Page
@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits)
					for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

# oauth connection for fb
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	access_token = request.data

	app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
		'web']['app_id']
	app_secret = json.loads(
		open('fb_client_secrets.json', 'r').read())['web']['app_secret']
	url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
		app_id, app_secret, access_token)
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]

	# Use token to get user info from API
	userinfo_url = "https://graph.facebook.com/v2.4/me"
	# strip expire tag from access token
	token = result.split("&")[0]


	url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]
	# print "url sent for API access:%s"% url
	# print "API JSON result: %s" % result
	data = json.loads(result)
	login_session['provider'] = 'facebook'
	login_session['username'] = data["name"]
	login_session['email'] = data["email"]
	login_session['facebook_id'] = data["id"]

	# The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
	stored_token = token.split("=")[1]
	login_session['access_token'] = stored_token

	# Get user picture
	url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]
	data = json.loads(result)

	login_session['picture'] = data["data"]["url"]

	# see if user exists
	user_id = getUserID(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']

	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

	flash("Now logged in as %s" % login_session['username'])
	return output

# Logout from fb
@app.route('/fbdisconnect')
def fbdisconnect():
	facebook_id = login_session['facebook_id']
	# The access token must me included to successfully logout
	access_token = login_session['access_token']
	url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
	h = httplib2.Http()
	result = h.request(url, 'DELETE')[1]
	return "you have been logged out"


# oauth connection for gmail
@app.route('/gconnect', methods=['POST'])
def gconnect():
	# Validate state token
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	# Obtain authorization code
	code = request.data

	try:
		# Upgrade the authorization code into a credentials object
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(
			json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check that the access token is valid.
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
		   % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])
	# If there was an error in the access token info, abort.
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is used for the intended user.
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
		response = make_response(
			json.dumps("Token's client ID does not match app's."), 401)
		print "Token's client ID does not match app's."
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'),
								 200)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Store the access token in the session for later use.
	login_session['credentials'] = credentials.access_token
	login_session['gplus_id'] = gplus_id


	# Get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']
	login_session['provider'] = 'google'

	# See if a user exists, if it doesn't make a new one
	user_id = getUserID(data["email"])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("you are now logged in as %s" % login_session['username'])
	print "done!"
	return output


# User Helper Functions
def createUser(login_session):
	newUser = User(name=login_session['username'], email=login_session[
				   'email'], picture=login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email=login_session['email']).one()
	return user.id

def getUserInfo(user_id):
	user = session.query(User).filter_by(id=user_id).one()
	return user

def getUserID(email):
	try:
		user = session.query(User).filter_by(email=email).one()
		return user.id
	except:
		return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
	# Only disconnect a connected user.
	credentials = login_session.get('credentials')
	if credentials is None:
		response = make_response(
			json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		print('credentials is None')
		return response
	access_token = login_session.get('credentials')
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]

	if result['status'] == '200':
		# Reset the user's sesson.
		del login_session['credentials']
		del login_session['gplus_id']
		#del login_session['username']
		#del login_session['email']
		#del login_session['picture']

		print('Successfully deleted')
		response = make_response(json.dumps('Successfully disconnected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		# For whatever reason, the given token was invalid.
		print('Looks like token is invalid')
		print('access token is ' + str(access_token))
		response = make_response(
			json.dumps('Failed to revoke token for given user.', 400))
		response.headers['Content-Type'] = 'application/json'
		return response

# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
	if 'provider' in login_session:
		if login_session['provider'] == 'google':
			gdisconnect()
		if login_session['provider'] == 'facebook':
			fbdisconnect()
			del login_session['facebook_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']
		del login_session['user_id']
		del login_session['provider']
		flash("You have successfully been logged out.")
		print('You have successfully been logged out.')
		#return '<script>alert("ok")</script>'
		return redirect(url_for('showCategoriesandItems'))
	else:
		print('Not Logged in')
		#return '<script>alert("Not ok")</script>'
		flash("You were not logged in")
		return redirect(url_for('showCategoriesandItems'))

# Show Categories and latest Items
@app.route('/')
@app.route('/catalog')
def showCategoriesandItems():
	categories = session.query(Category).all()
	items = session.query(Item).order_by(desc(Item.id)).limit(10)
	# return "This page will show all my restaurants"
	if 'username' not in login_session:
		return render_template('publichome.html', categories=categories, items = items, session = login_session)
	else:
		return render_template('home.html', categories=categories, items = items, session = login_session)

# Show Items by category
@app.route('/catalog/<string:category_name>/items', methods=['GET'])
def showItemsByCategory(category_name):
	categories = session.query(Category)
	selected_category = categories.filter_by(name = category_name).one()
	#print(selected_category.name)
	items = session.query(Item).filter_by(category_id = selected_category.id)
	return render_template('catalogitems.html', categories = categories, items = items)
	# return "This page will be for making a new restaurant"

# Add New Item to Catalog
@app.route('/catalog/additem', methods=['GET', 'POST'])
def addItemToCatalog():
	if 'username' not in login_session:
		return redirect('/login')
	categories = session.query(Category).all()
	if request.method == 'POST':
		user_id = login_session['user_id']
		name = request.form.get('name')
		description = request.form.get('description')
		selected_category = request.form.get('categories')
		if name and description and selected_category:
			category = session.query(Category).filter_by(name = str(selected_category)).one()
		
			item = Item(user_id = user_id, name = name, description = description, category = category)
			session.add(item)
			session.commit()
			print('Item Successfully Added')
			flash('Item Successfully Added')
			return redirect(url_for('showCategoriesandItems'))
		else:
			flash('All Fields are mandatory, Item not added')
			return redirect(url_for('addItemToCatalog'))
	else:
		return render_template('additem.html', categories = categories)

# Show Item with Description
@app.route('/catalog/<string:category_name>/item/<string:item_name>')
def showItem(category_name, item_name):
	category = session.query(Category).filter_by(name = category_name).one()
	item = session.query(Item).filter_by(name = item_name, category = category).one()
	print(item.name)
	return render_template('item.html', category = category, item = item, session = login_session)

# Edit Item
@app.route('/catalog/<int:item_id>/edit', methods = ['GET', 'POST'])
def editItem(item_id):
	item = session.query(Item).filter_by(id = item_id).first()
	if item is None:
		flash('Requested Item Not Found')
		return redirect(url_for('showCategoriesandItems'))

	if 'username' not in login_session:
		return redirect('/login')
	if item.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to edit this Item.');}</script><body onload='myFunction()''>"
	categories = session.query(Category).all()
	if request.method == 'POST':
		user_id = login_session['user_id']
		name = request.form.get('name')
		description = request.form.get('description')
		selected_category = request.form.get('categories')
		category = session.query(Category).filter_by(name = str(selected_category)).one()

		if name and description and selected_category:
			item.name = name
			item.description = description
			item.category_id = selected_category
			item.category = category
		else:
			flash('All fields are mandatory')
			return redirect((url_for('editItem', item_id = item.id)))
		print('Item Successfully Edited')
		flash('Item Successfully Edited')
		return redirect(url_for('showCategoriesandItems'))
	else:
		return render_template('edititem.html', item = item, categories = categories, session = login_session)


# Delete Item
@app.route('/catalog/<int:item_id>/delete', methods = ['GET', 'POST'])
def deleteItem(item_id):
	item = session.query(Item).filter_by(id = item_id).first()
	#category = item.category

	if item is None:
		flash('Requested Item not found for delete')
		return redirect(url_for('showCategoriesandItems'))

	if 'username' not in login_session:
		return redirect('/login')
	if item.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to delete this Item.');}</script><body onload='myFunction()''>"

	if request.method == 'POST':
		session.delete(item)
		print('Item Successfully Deleted')
		flash('Item Successfully Deleted')
		session.commit()
		return redirect(url_for('showCategoriesandItems'))
	else:
		return render_template('deleteitem.html', item = item, session = login_session)

# JSON API for all catalog items
@app.route('/catalog/JSON')
def catalogJSON():
	categories = session.query(Category).all()
	items = session.query(Item).all()
	return jsonify(Categories = [i.serialize for i in categories], Items = [i.serialize for i in items])

#JSON API for specific category itesm
@app.route('/catalog/<string:category_name>/JSON')
def catalogCategoryJSON(category_name):
	category = session.query(Category).filter_by(name = category_name).one()
	items = session.query(Item).filter_by(category_id = category.id).all()
	return jsonify(Items = [i.serialize for i in items])


#JSON API for specific item of a specific category
@app.route('/catalog/<string:category_name>/<string:item_name>/JSON/')
def itemJSON(category_name, item_name):
	category = session.query(Category).filter_by(name = category_name).one()
	item = session.query(Item).filter_by(name = item_name).one()
	return jsonify(category = category.serialize, item = item.serialize)

if __name__ == '__main__':
	app.debug = True
	app.secret_key = 'super_secret_key'  # secret key should not be here
	app.run(host='0.0.0.0', port=8080)
