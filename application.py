
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_jsglue import JSGlue
from tempfile import gettempdir
import string
from yelp.client import Client
from yelp.oauth1_authenticator import Oauth1Authenticator

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

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    results = client.search("Harvard Square", {"term": "food"})
    results_list = []
    for i in range(12):
        results_list.append(results.businesses[i].name)
    return jsonify(results_list)

    
