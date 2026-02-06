from flask import Flask, render_template, request, redirect, jsonify
import sqlite3

app = Flask(__name__)

def db():
    return sqlite3.connect("database.db")

# HOME / FEED
@app.route("/")
def index():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    posts = c.fetchall()
    return render_template("index.html", posts=posts)

# ADD POST
@app.route("/add", methods=["POST"])
def add():
    song = request.form["song"]
    artist = request.form["artist"]
    clip = request.form["clip"]
    mood = request.form["mood"]

    conn = db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO posts (song, artist, clip, mood) VALUES (?, ?, ?, ?)",
        (song, artist, clip, mood)
    )
    conn.commit()
    return redirect("/")

# GROUPS
@app.route("/groups")
def groups():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM groups")
    groups = c.fetchall()
    return render_template("groups.html", groups=groups)

app.run(debug=True)
