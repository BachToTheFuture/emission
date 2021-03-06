from flask import Flask, render_template, url_for, request, redirect, flash, Response, make_response, jsonify
import db
import json

app = Flask('app')
app.secret_key = 'super secret string'  # Change this!

uiPathAnswers = {}
doUI = True
uiAsk = "hamburger"
uiAsks = []

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


import flask_login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class User(flask_login.UserMixin):
  pass

################### LOGIN STUFF

@login_manager.user_loader
def user_loader(username):
    if not db.checkUser("username", username):
        return
    user = User()
    user.id = username
    return user

@login_manager.request_loader
def request_loader(request):
	if request.form:
		print("Authentication")
		username = request.form["username"]
		if not db.checkPassword(username, request.form["password"]):
			print("User not authenticated!")
			return
		user = User()
		user.id = username
		return user

############################ NO CACHE

@app.after_request
def add_header(r):
		"""
		Add headers to both force latest IE rendering engine or Chrome Frame,
		and also to cache the rendered page for 10 minutes.
		"""
		r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
		r.headers["Pragma"] = "no-cache"
		r.headers["Expires"] = "0"
		r.headers['Cache-Control'] = 'public, max-age=0'
		return r

############################ ROUTES

@app.route('/')
def index():
	return render_template('landing.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
	# If there is a form submitted
	if request.form:
		# If inputPassword2 field is not empty, this is a registration.
		name = request.form["username"]
		pwrd = request.form["password"]
		# Registration
		if request.form["password2"]:
			# Check if the user already exists
			if (pwrd != request.form["password2"]):
				flash("Passwords do not match!")
				return render_template('login.html')
			if (len(pwrd) < 6):
				flash("Password must be at least 6 characters.")
				return render_template('login.html')
		
			if db.checkUser("username", name):
				flash("User '{}' already exists!".format(name))
				return render_template('login.html')
			else:
				print("New user {} registered!".format(name))
				db.addUser(name, pwrd)
				flash("User created!")
				return render_template('login.html', newuser=True)
			
		# Validated user
		elif db.checkUser("username", name) and db.checkPassword(name, pwrd):
			print(name, "has been verified!")
			user = User()
			user.id = request.form["username"]
			userid = str(db.getPartWith('username', user.id, '_id'))
			resp = make_response(redirect(url_for('dashboard')))
			resp.set_cookie('userID', userid)
			flask_login.login_user(user)
			return resp

		else:
			print("Unauthorized")
			flash("Incorrect credentials!")
			return render_template('login.html')

	else:
		return render_template('login.html')

# Unauthorized access redirects to login page
@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))


"""
The following pages require authentication
Current user's username is stored in this variable: flask_login.current_user.id
"""

@app.route('/dashboard', methods=['GET', 'POST'])
@flask_login.login_required
def dashboard():
	username = flask_login.current_user.id
	print('Logged in as: ' + username)
	userid = request.cookies.get('userID')
	#print(db.get_data(userid, []))
	scores = db.get_data(userid, ['score'])["score"]

	activities = db.get_data(userid, ['activities'])
	if request.method == 'POST' and request.form:
		activities = {}
		date = "d" + request.form["date"].replace("/", '_')
		for i, val in request.form.items():
			if i == 'date': continue
			if val.lstrip('-+').isdigit(): val = int(val)
			activities['activities.' + i.replace('-', '.') + '.' + date] = val
		db.updateActivities(userid, activities)
		flash("Your responses have been saved!")
	return render_template('index.html', username=username)

@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect('/')


@app.route('/leaderboard')
@flask_login.login_required
def leaderboard():
	username = flask_login.current_user.id
	return render_template('leaderboard.html', username=username)

@app.route('/settings')
@flask_login.login_required
def settings():
	username = flask_login.current_user.id
	return render_template('settings.html', username=username)

@app.route('/chatbot')
@flask_login.login_required
def chatbot():
	username = flask_login.current_user.id
	return render_template('chatbot.html', username=username)

@app.route('/map')
@flask_login.login_required
def mapPage():
	username = flask_login.current_user.id
	return render_template('map.html', username=username)

@app.route('/profile')
@flask_login.login_required
def profile():
	username = flask_login.current_user.id

	userid = request.cookies.get('userID')
	scores = db.get_data(userid, ['scores'])['scores']

	score = db.get_data(userid, ['score'])['score']
	friends = db.get_data(userid, ['friends'])
	friends = [] if 'friends' not in friends else friends["friends"]

	return render_template('profile.html', username=username,
		friends=friends, score=score)

@app.route('/information')
@flask_login.login_required
def info():
	username = flask_login.current_user.id
	return render_template('information.html', username=username)

@app.route('/get-info', methods=['POST'])
@flask_login.login_required
def getInfo():
	data = request.get_json()['parts']
	userid = request.cookies.get('userID')
	re = db.get_data(userid, data)
	return jsonify(re)

@app.route('/save-scores', methods=['POST'])
@flask_login.login_required
def saveScore():
	data = request.get_json()
	userid = request.cookies.get('userID')
	db.updateActivities(userid, data)
	return jsonify({})

@app.route('/get-leader', methods=['POST'])
@flask_login.login_required
def getLeader():
	userid = request.cookies.get('userID')
	re = db.get_leaderboard(userid)
	return jsonify(re)

@app.route('/foodCalorie', methods=['POST'])
@flask_login.login_required
def foodCalorie():
	global uiPathAnswers, uiAsks
	data = request.get_json()['food']
	if data in uiPathAnswers.keys():
		return jsonify({'answer': uiPathAnswers[data]})
	if data not in uiAsks:
		uiAsks.append(data)
	while data not in uiPathAnswers.keys():
		pass
	return jsonify({'answer': uiPathAnswers[data]})

@app.route('/ui-data', methods=['POST'])
def uiData():
	global uiPathAnswers, uiAsks
	data = request.get_json()
	print("DATA", data)
	food = data['food']
	calories = data['calories']
	if food in uiAsks:
		del uiAsks[uiAsks.index(food)]
	uiPathAnswers[food] = calories
	return jsonify({})

@app.route('/ui-go', methods=['POST'])
def goUI():
	global doUI, uiAsks
	if len(uiAsks) > 0:
		ask = uiAsks[0]
		del uiAsks[0]
		return jsonify({"go": True, "food": ask})
	return jsonify({"go": False})

@app.route('/befriend', methods=['POST'])
@flask_login.login_required
def befriend():
	userid = request.cookies.get('userID')
	othername = request.get_json()['name']
	db.befriend(userid, othername)
	return jsonify({'success': True})

@app.route('/search', methods=['POST'])
def searchNames():
	name = request.get_json()['name']
	return jsonify({'names': db.search_names(name)})

@app.route('/google-cloud', methods=['POST'])
def cloud():
	j = request.get_json()
	print(j)
	return jsonify({})



app.run(host='0.0.0.0', port=8080, debug=True)