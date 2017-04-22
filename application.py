'''
FoodGroups
Creators: Sam Lurye and Elizabeth Yeoh-Wang
Date: 12/16

application.py implements the backend for FoodGroups
'''

from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_jsglue import JSGlue
from tempfile import gettempdir
import string
from yelp.client import Client
from yelp.oauth1_authenticator import Oauth1Authenticator
import pyrebase
import re
from helpers import *

# global variables for storing email and password of current user
email = ""
password = ""

# list of preferences, for access later
cuisines = [
    "American",
    "Asian",
    "Caribbean",
    "Chinese",
    "French",
    "Greek",
    "Indian",
    "Italian",
    "Japanese",
    "Korean",
    "Latin",
    "Mediterranean",
    "Mexican",
    "Seafood",
    "Spanish",
    "Thai",
    "Vietnamese"
]

diet_rest = [
    "Gluten-free",
    "Halal",
    "Kosher",
    "Vegan",
    "Vegetarian"
]

preferences = cuisines + diet_rest

# API information for Firebase through Pyrebase
config = {
  "apiKey": "AIzaSyAYWfiPHs-y3ChdBVwssQjGbdq-CUbie68",
  "authDomain": "foodgroups-d123f.firebaseapp.com",
  "databaseURL": "https://foodgroups-d123f.firebaseio.com",
  "storageBucket": "foodgroups-d123f.appspot.com"
}

firebase = pyrebase.initialize_app(config)

fire_auth = firebase.auth()

db = firebase.database()

# API information for Yelp
auth = Oauth1Authenticator(
    consumer_key = "2XVtPIbmjsdUNWohPrjPNw",
    consumer_secret = "coHn82hLt5_p9Y97JhsBClknaG4",
    token = "WH2HhV5L96bTtIY87fPGomyCWqNKwElZ",
    token_secret = "KO-_ZmFEdWt7SQUWVXS3AFeTPMM"
)

client = Client(auth)

# configure application
app = Flask(__name__)
jsglue = JSGlue(app)

# the following lines (until @app.route) are taken directly from CS50 distribution code

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

@app.route("/", methods=["GET", "POST"])
def home():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    # check if user is getting recommendations for a group
    if request.args.get("groupname") != None and request.args.get("outing") != None:
        return render_template("home.html", groupname=request.args.get("groupname"), outing=request.args.get("outing"))
    else:
        return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        # try to sign user in, else return error message
        try:
            fire_auth.sign_in_with_email_and_password(request.form.get("email"), request.form.get("password"))
            return redirect(url_for("home"))
        except:
            return render_template("errorlogin.html", message = "Invalid email or password!")

@app.route("/logout")
def logout():
    # log out user
    fire_auth.current_user = None
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        # make sure user entered valid email and password for registration
        if not request.form.get("email"):
            return render_template("errorlogin.html", message = "Please provide an email!")
        elif not request.form.get("password"):
            return render_template("errorlogin.html", message = "Please provide a password!")
        elif request.form.get("password") != request.form.get("confirm"):
            return render_template("errorlogin.html", message = "Passwords must match!")
        else:
            # try to create account with Firebase, else return error message
            try:
                fire_auth.create_user_with_email_and_password(request.form.get("email"), request.form.get("password"))
                fire_auth.sign_in_with_email_and_password(request.form.get("email"), request.form.get("password"))
                # send user to set preferences
                return redirect(url_for("survey", scope="global"))
            except:
                return render_template("errorlogin.html", message = "Invalid email or password!")

@app.route("/search", methods=["GET", "POST"])
def search():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    # check if user is getting recommendation for self or for group, get results from Yelp API
    if request.args.get("outing") != None:
        params = {
            "term": "food " + request.args.get("outing")
        }
        # search for places that fit type outing at location set for group
        results = client.search(db.child("groups").child(request.args.get("groupname")).child("location").get().val(), **params)
    else:
        params = {
            "term": "food"
        }
        # search for places (general) at location set in user preferences
        results = client.search(db.child("users").child(get_email_branch(fire_auth)).child("preferences").child("location").get().val(), **params)

    # list for restaurant results
    rankings = []

    # put names of restaurants in a list, with no score yet 
    for i in range(len(results.businesses)):
        rankings.append([results.businesses[i].name, "N/A"])

    # assign score to restaurants in list if getting recommendations for a group, else display with no score
    if request.args.get("groupname") != None and request.args.get("outing") != None:
        # get members of the relevant group from Firebase
        members = db.child("groups").child(request.args.get("groupname")).child("members").get().each()
        # add up all members' cuisine preferences and set overall preferences for group in Firebase in groupprefs branch
        for cuisine in cuisines:
            pref_score = 0
            for member in members:
                try:
                    x = db.child("groups").child(request.args.get("groupname")).child("members").child(member.key()).child(cuisine).get().val()
                    pref_score += int(x)
                except:
                    print("for "+request.args.get("groupname")+", "+member.key()+" doesn't contain "+cuisine)
            db.child("groups").child(request.args.get("groupname")).child("groupprefs").update({cuisine: pref_score})
        # if a member of the group has dietary restrictions, then set those dietary restrictions to "on" in groupprefs branch
        for rest in diet_rest:
            for member in members:
                if db.child("groups").child(request.args.get("groupname")).child("members").child(member.key()).child(rest).get().val() != None:
                    db.child("groups").child(request.args.get("groupname")).child("groupprefs").update({rest: "on"})
                    break

        # contains group preference information
        group_info = db.child("groups").child(request.args.get("groupname")).child("groupprefs").get().each()

        i = 0
        # go through restaurants returned by API, assign each one a score
        for restaurant in results.businesses:
            restaurant_score = 1
            # adjust restaurant score based on rating and number of reviews
            restaurant_score *= ((restaurant.rating * restaurant.review_count) / 1000)
            # for each preference in groupprefs, check each restaurant to see if it fits the preference, adjust score accordingly
            for pref in group_info:
                for category in restaurant.categories:
                    if pref.key().lower() in category[0].lower() or pref.key().lower() in category[1]:
                        # cuisine
                        if pref.val() != "on":
                            restaurant_score += int(pref.val())
                        # dietary restrictions
                        else:
                            restaurant_score *= 10
            # fill a list with restaurant names and corresponding scores
            rankings[i] = [restaurant.name, restaurant_score]
            i += 1
        # sorts the list by score: (source) http://pythoncentral.io/how-to-sort-a-list-tuple-or-object-with-sorted-in-python/
        def getKey(item):
            return item[1]
        rankings = sorted(rankings, key=getKey, reverse=True)
    # return JSON for html file
    return jsonify(rankings)

@app.route("/survey", methods=["GET", "POST"]) 
def survey():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    """Brings user to survey page. Attempts to get user preferences from Firebase. If preferences exist,
    then they'll be filled in automatically. If the preferences don't exist, then Jinja in HTML handles setting
    everything to 0."""
    if request.method=="GET":
        # put user preferences in easily accessible forms (dictionary and set)
        pref_dict, prefs_set = get_user_prefs_set_and_dict(fire_auth, db, request.args.get("scope"))

        return render_template("survey.html", cuisines = cuisines, diet_rest = diet_rest, pref_dict = pref_dict, prefs_set = prefs_set, scope=request.args.get("scope"))
    else:
        # enter user preferences into user profile in Firebase
        if request.args.get("scope") == "global":
            db.child("users").child(get_email_branch(fire_auth)).child("preferences").set(request.form)
        # enter user preferences into proper branch in specific group in firebase
        else:
            db.child("groups").child(request.args.get("scope")).child("members").child(get_email_branch(fire_auth)).set(request.form)
        return redirect(url_for("home"))

@app.route("/createGroup", methods=["GET", "POST"])
def createGroup():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    # make sure the user has filled out the survey
    if db.child("users").child(get_email_branch(fire_auth)).child("preferences").get().val() == None:
        return redirect(url_for('survey', scope='global'))

    if request.method == "GET":
        return render_template("group.html")
    else:
        # make sure that the user has entered a valid group ID and password and that the group doesn't already exist
        if not request.form.get("groupid") or not request.form.get("password"):
            return render_template("error.html", message = "Please provide a group name and password!")
        if not request.form.get("groupid").isalnum():
            return render_template("error.html", message = "Please provide a valid group name!")
        if db.child("groups").child(request.form.get("groupid")).get().val() != None:
            return render_template("error.html", message = "Group already exists!")
        # create group in Firebase and set password
        db.child("groups").child(request.form.get("groupid")).child("password").set(request.form.get("password"))
        # add user to group in Firebase, add group to user's "mygroups" branch in Firebase
        user_dict, users_set = get_user_prefs_set_and_dict(fire_auth, db, "global")
        db.child("groups").child(request.form.get("groupid")).child("members").child(get_email_branch(fire_auth)).set(user_dict)
        db.child("users").child(get_email_branch(fire_auth)).child("mygroups").child(request.form.get("groupid")).set("True")
    return redirect(url_for("myGroups"))

@app.route("/joinGroup", methods=["GET", "POST"])
def joinGroup():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    # make sure the user has filled out the survey
    if db.child("users").child(get_email_branch(fire_auth)).child("preferences").get().val() == None:
        return redirect(url_for('survey', scope='global'))

    if request.method == "GET":
        return render_template("joingroup.html")
    else:
        # make sure the user enters valid group information
        if not request.form.get("groupid") or not request.form.get("password"):
            return render_template("error.html", message = "Please provide a group name and password!")
        if db.child("groups").child(request.form.get("groupid")).get().val() == None:
            return render_template("error.html", message = "Group does not exist!")
        if db.child("groups").child(request.form.get("groupid")).child("password").get().val() != request.form.get("password"):
            return render_template("error.html", message = "Invalid password!")

        # add user to given group and add group to user's "mygroups" branch in Firebase
        pref_dict, prefs_set = get_user_prefs_set_and_dict(fire_auth, db, "global")
        db.child("groups").child(request.form.get("groupid")).child("members").child(get_email_branch(fire_auth)).set(pref_dict)
        db.child("users").child(get_email_branch(fire_auth)).child("mygroups").child(request.form.get("groupid")).set("True")
    return redirect(url_for("myGroups"))

@app.route("/myGroups", methods=["GET", "POST"])
def myGroups():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    # make sure the user has filled out the survey
    if db.child("users").child(get_email_branch(fire_auth)).child("preferences").get().val() == None:
        return redirect(url_for('survey', scope='global'))

    if request.method == "GET":
        # get all groups the user is a part of, put them in list to pass to html template
        user_groups_data = db.child("users").child(get_email_branch(fire_auth)).child("mygroups").get().each()
        user_groups = []
        
        if not user_groups_data == None:
            for group in range(len(user_groups_data)):
                user_groups.append(user_groups_data[group].key())
        return render_template("mygroups.html", user_groups = user_groups)
    else:
        # creates an outing in Firebase
        db.child("groups").child(request.args.get("groupname")).update({ "current_outing" : request.form.get("outing-type-"+request.args.get("groupname")), "location" : request.form.get("location")})
        return redirect(url_for("pendingOutings"))

@app.route("/pendingOutings", methods=["GET", "POST"])
def pendingOutings():
    # check if user is logged in
    if fire_auth.current_user == None:
        return redirect(url_for("login"))

    # make sure the user has filled out the survey
    if db.child("users").child(get_email_branch(fire_auth)).child("preferences").get().val() == None:
        return redirect(url_for('survey', scope='global'))

    if request.method == "GET":
        # get all groups for user
        user_groups_data = db.child("users").child(get_email_branch(fire_auth)).child("mygroups").get().each()
        user_groups = []
        if not user_groups_data == None:
            for group in range(len(user_groups_data)):
                user_groups.append(user_groups_data[group].key())
        # if there are current outings in Firebase, then add them to list of outings to be sent to pending outings html template
        outings = []
        for group in user_groups:
            current_outing = db.child("groups").child(group).child("current_outing").get().val()
            if current_outing != None:
                outings.append((group, current_outing))
        return render_template("pendingoutings.html", outings = outings)
    else:
        # allow a user to update preferences for a given group
        return redirect(url_for("survey", scope=request.args.get("groupname")))
