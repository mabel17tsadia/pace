import os
from datetime import date, datetime
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, request, url_for, abort, flash
import data
from pace import get_pace
from ai import suggest_task, write_alert

# Load settings like SECRET_KEY from the .env file
load_dotenv()

# Create the Flask app; the secret key lets it remember each user's theme
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# The themes a user can pick from
THEMES = ["calm", "colorful", "bright", "dark"]

# The five feelings on the Check in page
FEELINGS = ["Calm", "Okay", "Tired", "Worried", "Overwhelmed"]

# The three load levels a task can have
LOADS = ["Light", "Medium", "Heavy"]

# Gentle alert messages already written, so Today doesn't call Claude on every visit
ALERT_CACHE = {}


# Give every template the user's current theme (calm if none picked yet)
@app.context_processor
def add_theme():
    return {"theme": session.get("theme", "calm")}


# The person picked on the home page, or None if nobody is picked yet
def current_person():
    return data.get_person(session.get("person_id"))


# Today's tasks for a person: the demo tasks plus any they added, minus any moved
# to tomorrow, in time order
def tasks_for(person):
    added = [t for t in session.get("added_tasks", []) if t["person_id"] == person["id"]]
    moved = session.get("moved", [])
    tasks = [t for t in data.get_tasks(person["id"]) + added if [person["id"], t["title"]] not in moved]
    return sorted(tasks, key=lambda t: t["time"] or "99:99")


# Home page: choose which demo person to use
@app.route("/")
def choose():
    return render_template("choose.html", title="Choose a demo person", people=data.get_people())


# Save the chosen person in the session, then open Today
@app.route("/choose/<person_id>")
def choose_person(person_id):
    if data.get_person(person_id):
        session["person_id"] = person_id
        return redirect(url_for("today"))
    return redirect(url_for("choose"))


# Today screen: pace, inbox suggestions and the day's plan
@app.route("/today")
def today():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    pid = person["id"]
    daily = data.get_daily(pid)
    # The demo "today" is the newest date in the data, shown like "Wednesday 28 October"
    d = date.fromisoformat(daily[-1]["date"])
    pace = get_pace(person, daily, data.get_heart(pid))
    tasks = tasks_for(person)

    # Gentle alert: on a Gentle day, warn about the first Heavy task (unless "Keep my plan" was picked)
    alert = None
    heavy = next((t for t in tasks if t["load"] == "Heavy"), None)
    if pace["level"] == "Gentle" and heavy and pid not in session.get("alert_kept", []):
        key = (pid, heavy["title"])
        if key not in ALERT_CACHE:
            ALERT_CACHE[key] = write_alert(person, heavy)
        alert = {"task": heavy, "message": ALERT_CACHE[key]}

    return render_template("today.html", title="Today",
                           day=f"{d:%A} {d.day} {d:%B}",
                           pace=pace, alert=alert,
                           inbox=data.get_inbox(pid),
                           tasks=tasks)


# Gentle alert choices: lighter task first, move to tomorrow, keep my plan, message someone
@app.route("/alert", methods=["POST"])
def alert_choice():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    choice = request.form.get("choice")
    title = request.form.get("title", "")
    tasks = tasks_for(person)

    # Lighter task first: open the steps of the first Light task
    if choice == "lighter":
        light = next((i for i, t in enumerate(tasks) if t["load"] == "Light"), None)
        if light is not None:
            flash(f"Starting with a lighter task: {tasks[light]['title']}.")
            return redirect(url_for("task_steps", index=light))
        flash("There is no lighter task today.")
    # Move to tomorrow: hide the task from today's plan (demo only, saved in the session)
    elif choice == "move":
        session["moved"] = session.get("moved", []) + [[person["id"], title]]
        flash(f"{title} moved to tomorrow.")
    # Keep my plan: hide the alert for this person
    elif choice == "keep":
        session["alert_kept"] = session.get("alert_kept", []) + [person["id"]]
        flash("Okay, keeping your plan. Go gently.")
    # Message someone I trust: open the Circle page
    elif choice == "message":
        flash("Choose someone in your Circle to message.")
        return redirect(url_for("circle"))
    return redirect(url_for("today"))


# Task steps screen: one task's steps, shown one at a time by static/js/steps.js
@app.route("/task/<int:index>")
def task_steps(index):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    tasks = tasks_for(person)
    if index >= len(tasks):
        abort(404)
    return render_template("task.html", title=tasks[index]["title"],
                           task=tasks[index], person=person)


# Add a task: type a task, get a suggested load and steps, change them, then save
@app.route("/add", methods=["GET", "POST"])
def add_task():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    task_title = request.form.get("title", "").strip()[:80]
    action = request.form.get("action")

    # Save: keep the edited task in the session (demo only, keeps the last 10) and go to Today
    if action == "save" and task_title and request.form.get("load") in LOADS:
        steps = [s.strip()[:80] for s in request.form.getlist("steps") if s.strip()]
        added = session.get("added_tasks", [])
        added.append({"person_id": person["id"], "title": task_title,
                      "time": request.form.get("time", ""), "part_of_day": "",
                      "load": request.form["load"], "source": "manual",
                      "steps": steps or [task_title]})
        session["added_tasks"] = added[-10:]
        flash("Task added to your plan.")
        return redirect(url_for("today"))

    # Suggest: ask the AI (or the keyword backup) for a load level and steps
    suggestion = suggest_task(task_title) if action == "suggest" and task_title else None
    return render_template("add.html", title="Add a task", task_title=task_title,
                           suggestion=suggestion, loads=LOADS)


# Check in screen: pick a feeling, add an optional note, then Save (or Skip)
@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    checkins = session.get("checkins", [])

    # Save: add the check in to the session (demo only, keeps the last 20) and go to Today
    if request.method == "POST" and request.form.get("feeling") in FEELINGS:
        checkins.append({"person_id": person["id"],
                         "time": datetime.now().strftime("%H:%M"),
                         "feeling": request.form["feeling"],
                         "note": request.form.get("note", "").strip()[:200]})
        session["checkins"] = checkins[-20:]
        flash("Check in saved. Thank you.")
        return redirect(url_for("today"))

    # Show the form, plus this person's earlier check ins
    mine = [c for c in checkins if c["person_id"] == person["id"]]
    return render_template("checkin.html", title="Check in", feelings=FEELINGS, checkins=mine)


# Circle screen - placeholder for now
@app.route("/circle")
def circle():
    return render_template("placeholder.html", title="Circle")


# Me screen - placeholder for now
@app.route("/me")
def me():
    return render_template("me.html", title="Me")


# Save the chosen theme, then go back to the page the user was on
@app.route("/theme/<name>")
def set_theme(name):
    if name in THEMES:
        session["theme"] = name
    return redirect(request.referrer or url_for("today"))


# Start the app in debug mode when this file is run directly
if __name__ == "__main__":
    app.run(debug=True)
