from flask import Flask, render_template, session, request, redirect, url_for
from utils import auth, add, get, parse
import json, urllib2

app = Flask(__name__)

# ===========================================
# ROUTES
# ===========================================
@app.route('/')
@app.route('/home/')
def home():
    if 'user' in session:
        u = session['user']
    else:
        u = ""
    return render_template('home.html', username = u)

@app.route("/authenticate/", methods = ["GET", "POST"])
def authenticate():
    alert = ""
    if 'user' in session:
        u = session['user']
        return render_template('home.html', username = u)

    if 'register' in request.form.keys():
        if (int(request.form['age']) not in range(1, 101)) or (int(request.form['height']) not in range(1, 101)) or (int(request.form['weight']) not in range(1, 1001)):
            msg = "Please put an age and height from 1 to 100. The weight should be from 1 to 1000."
        elif auth.register(request.form['username'], request.form['password']):
            u = request.form['username']
            gender = request.form['gender']
            age = request.form['age']
            height = request.form['height']
            weight = request.form['weight']
            add.add_profile(u, gender, age, height, weight)
            msg = "Successfully registered!"
            alert = "alert alert-danger"
        else:
            msg = "Failed to register! Username is taken."
        return render_template("authenticate.html", register_message = msg, alarm = alert)

    elif 'login' in request.form.keys():
        if not request.form['username'] or not request.form['password']:
            msg = "Please enter a username and password."
        elif auth.login(request.form['username'], request.form['password']):
            session["user"] = request.form['username']
            return redirect(url_for("profile"))
        else:
            msg = "Failed to login. Username and/or password incorrect."
        return render_template("authenticate.html", login_message = msg, alerm = alert)

    else:
        return render_template("authenticate.html")


@app.route('/profile/')
def profile():
    if 'user' in session:
        u = session['user']
        info = get.get_user_data(u)
        bmi = parse.show_bmi(get.get_bmi(u))
        if info[0] == 'm':
            info[0] = 'Male'
        else:
            info[0] = 'Female'
        return render_template('profile.html', username = u, gender = info[0], age = info[1], height = info[2], weight = info[3], value = bmi['value'], status = bmi['status'], risks = bmi['risk'])
    else:
        return redirect(url_for("home"))

@app.route('/display/', methods = ["GET", "POST"])
def display():
    if 'user' in session:
        u = session['user']
    else:
        u = ""

    d = {}
    ar = []
    if 'search' in request.form.keys():
        if not request.form['lookup']:
            return redirect(url_for("home"))
        else:
            # Get food api key
            api_key_food = get.getAPIKeys(0)

            # First API
            num_results = 10
            url = "http://api.nal.usda.gov/ndb/search/?format=json&q=%s&sort=n&max=%d&offset=0&api_key=%s" % (request.form["lookup"].replace(" ", "_"), num_results, api_key_food)

            # try to connect to API
            try:
                connection = urllib2.urlopen(url)
                jsonf = connection.read()
                connection.close()
                jsonf = json.loads(jsonf)
            except urllib2.URLError, err:
                # print err
                if err.code == 403:
                    print "403 Error. Access denied!"
                else:
                    print "Unknown error code: " + str(err.code)

                jsonf = {"errors": err.code}

            # return error
            if "errors" in jsonf.keys():
                return render_template("display.html", error="Search not found", query=request.form['lookup'])
            jsonf = jsonf["list"]["item"]

            # Second API
            for index in jsonf:
                #print index
                nutri = "http://api.nal.usda.gov/ndb/nutrients/?format=json&api_key=%s&nutrients=205&nutrients=204&nutrients=208&nutrients=269&nutrients=291&nutrients=301&nutrients=303&nutrients=431&nutrients=304&nutrients=305&nutrients=306&nutrients=307&nutrients=401&nutrients=415&nutrients=418&nutrients=320&ndbno=%s"%(api_key_food,index["ndbno"])
                nutrif = json.loads(urllib2.urlopen(nutri).read())

                z = index["name"]
                holder = z.find("UPC")
                if holder != -1:
                    holder -= 2
                z = z[0:holder]
                if nutrif["report"]["foods"]:
                    d[z] = nutrif["report"]["foods"][0]["nutrients"]


            # parse.get_list_of_food_nutrients(d.items())
            d = parse.show_nutrients(d.items())

            #getting rid of -- and changing them to zeroes
            for name in d:
                x = d[name]
                for nutrient in x:
                    y = x[nutrient]
                    if y.find("--") != -1:
                        dash = y.find("--")
                        dash += 2
                        x[nutrient] = "0" + x[nutrient][2:]

            return render_template('display.html', fooddata = d, foodname=request.form['lookup'], username=u)
    else:
        return redirect(url_for("home"))

@app.route('/calorie/', methods = ["GET", "POST"])
def calorie():
    if 'user' in session:
        if 'food_item' in request.form:
            add.add_meal(session['user'], request.form["food_item"], parse.remove_units(request.form["calories"]))
        calorie_tracker = get.get_calories(session['user'])
        return render_template('calorie.html', calorie_display = calorie_tracker)
    else:
        return redirect(url_for('home'))

@app.route('/update/', methods = ["GET", "POST"])
def update():
    red = True
    if 'user' in session:
        msg = ""
        if 'update' in request.form.keys():
            u = session['user']
            age = request.form['age']
            height = request.form['height']
            weight = request.form['weight']
            if not height and not age and not weight:
                msg = "You didn't enter anything. Try again."
                return render_template('update.html', update = msg, color = red)
            info = get.get_user_data(u)
            if age == '':
                age = info[1]
            if height == '':
                height = info[2]
            if weight == '':
                weight = info[3]
            if (int(age) not in range(1, 101)) or (int(height) not in range(1, 101)) or (int(weight) not in range(1, 1001)):
                msg = "Age and height can only have values from 1 to 100. Weight can only have a value from 1 to 1000."
            else:
                add.update_profile(u, age, height, weight)
                msg = "Information updated!"
                red = False
        return render_template('update.html', update = msg, color = red)
    else:
        return redirect(url_for('home'))

@app.route('/logout/')
def logout():
    if 'user' in session:
        session.pop('user')
    return redirect(url_for('home'))

# ===========================================
# RUN
# ===========================================

if __name__ == '__main__':
    app.debug = True
    app.config.from_object('config')
    app.secret_key = app.config['SECRET_KEY']
    app.run()
