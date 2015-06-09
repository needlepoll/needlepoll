#! /usr/bin/python3

from flask import Flask, render_template, request, redirect
import psycopg2
import random
import base64
import config

def interp_form_boolean(string):
	if string == "on":
		return True
	elif string == "None":
		return False
	else:
		pass

connection = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (config.database_name, config.database_user, config.database_host, config.database_password))

app = Flask(__name__)

@app.route("/")
def render_root():
	return render_template("create.html")

@app.route("/poll/<pollid>/")
def render_poll(pollid):
	cursor = connection.cursor()
	cursor.execute("SELECT * FROM polls WHERE id = %s", (pollid,))
	results = cursor.fetchone()
	if results == None:
		return render_template("error.html", err="Poll does not exist"), 404
	if results[3] == True:
		inputtype = "checkbox"
	else:
		inputtype = "radio"
	question = results[1]
	options = results[2]
	return render_template("poll.html", inputtype=inputtype, question=question, options=options)

@app.route("/poll/<pollid>/vote/", methods=["POST"])
def vote(pollid):
	ipad = request.headers.get("X-Forwarded-For")
	cursor = connection.cursor()
	cursor.execute("SELECT * FROM votes WHERE id = %s AND ip = %s", (pollid, ipad))
	previous_vote = cursor.fetchone()
	cursor.execute("SELECT options FROM polls WHERE id = %s", (pollid,))
	results = cursor.fetchone()
	cursor.execute("SELECT ip FROM polls WHERE id = %s", (pollid,))
	multiple_per_ip = cursor.fetchone()[0]
	options = results[0]
	option_responses = []
	selection = request.form.get("options")
	if selection != None:
		print(selection)
		for i in range(len(options)):
			option_responses.append(False)
		try:
			option_responses[int(selection)] = True
		except:
			return render_template("error.html", err="Vote contained invalid choice(s)")
	else:
		for i in range(len(options)):
			option_responses.append(interp_form_boolean(str(request.form.get(str(i)))))
	if previous_votes == None and (not multiple_per_ip):
		cursor.execute("INSERT INTO votes VALUES (%s, %s, %s);", (pollid, option_responses, ipad))
		connection.commit()
		return redirect("/poll/%s/results/" % pollid, code=302)
	else:
		return render_template("error.html", err="Someone using your IP has already voted in this poll")

@app.route("/poll/<pollid>/results/")
def render_poll_results(pollid):
	cursor = connection.cursor()
	cursor.execute("SELECT * FROM polls WHERE id = %s", (pollid,))
	results = cursor.fetchone()
	if results == None:
		return render_template("error.html", err="Poll does not exist"), 404
	_, question, options, _, _, _ = results
	options = tuple(options)
	cursor.execute("SELECT selections FROM votes WHERE id = %s", (pollid,))
	votes = [tuple(x[0]) for x in cursor.fetchall()]
	num_votes = len(votes)
	times_voted = []
	for item in list(zip(*votes)):
		t = 0
		for vot in item:
			if vot: t += 1
		times_voted.append(t)
	times_voted = tuple(times_voted)
	percent_voted = []
	for j in times_voted:
		percent_voted.append(round((j/num_votes)*100))
	percent_voted = tuple(percent_voted)
	zipped = list(zip(options, times_voted, percent_voted))
	zipped = tuple(reversed(sorted(zipped, key=lambda x: x[1])))
	return render_template("results.html", zipped=zipped, question=question, votes=num_votes)

@app.route("/create/", methods=["POST"])
def create():
	question = request.form["question"]
	options = [x for x in request.form["options"].split("\r\n") if x != ""]
	multiple_selections = interp_form_boolean(str(request.form.get("multiple")))
	multiple_votes = interp_form_boolean(str(request.form.get("iplimit")))
	pollid = base64.b64encode(open("/dev/urandom", "rb").read(9)).decode("ascii").replace("/", "x").lower()
	ipad = request.headers.get("X-Forwarded-For")
	cursor = connection.cursor()
	cursor.execute("INSERT INTO polls VALUES (%s, %s, %s, %s, %s, %s);", (pollid, question, options, multiple_selections, multiple_votes, ipad))
	connection.commit()
	return redirect("/poll/%s/" % pollid, code=302)

if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5001)
