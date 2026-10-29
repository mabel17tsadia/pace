import os
import pandas as pd

# Folder that holds the demo CSV files
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# Read one CSV file from the data folder (empty cells become "")
def read_csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, name)).fillna("")


# Turn "a|b|c" into ["a", "b", "c"] (an empty cell becomes [])
def split_list(value):
    return value.split("|") if value else []


# Get one person's rows from a CSV file as a list of dictionaries
def rows_for(name, person_id):
    df = read_csv(name)
    return df[df["person_id"] == person_id].to_dict("records")


# All demo people, with drains and calms as lists
def get_people():
    people = read_csv("people.csv").to_dict("records")
    for p in people:
        p["drains"] = split_list(p["drains"])
        p["calms"] = split_list(p["calms"])
    return people


# One person by id, or None if there is no such person
def get_person(person_id):
    for p in get_people():
        if p["id"] == person_id:
            return p
    return None


# A person's sleep and steps for the last 7 days
def get_daily(person_id):
    return rows_for("daily.csv", person_id)


# A person's heart rate readings for today (every 15 minutes)
def get_heart(person_id):
    return rows_for("heart.csv", person_id)


# A person's tasks for today, with steps as a list
def get_tasks(person_id):
    tasks = rows_for("tasks.csv", person_id)
    for t in tasks:
        t["steps"] = split_list(t["steps"])
    return tasks


# A person's inbox messages, each with a suggested task
def get_inbox(person_id):
    return rows_for("inbox.csv", person_id)
