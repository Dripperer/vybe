from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # in produzione va cambiata

DB_FILE = "database.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if os.path.exists(DB_FILE):
        return
    conn = get_db()
    c = conn.cursor()

    # Utenti
    c.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        bio TEXT,
        avatar TEXT
    )
    """)

    # Post
    c.execute("""
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        song TEXT,
        artist TEXT,
        clip TEXT,
        clip_type TEXT,
        mood TEXT,
        cover TEXT,
        likes INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Commenti
    c.execute("""
    CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        text TEXT,
        FOREIGN KEY(post_id) REFERENCES posts(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Gruppi
    c.execute("""
    CREATE TABLE groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT
    )
    """)

    # Messaggi nei gruppi (chat semplice)
    c.execute("""
    CREATE TABLE group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        user_id INTEGER,
        text TEXT,
        FOREIGN KEY(group_id) REFERENCES groups(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Notifiche (es: commenti ai tuoi post)
    c.execute("""
    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Utente di esempio
    c.execute("""
    INSERT INTO users (username, password_hash, bio, avatar)
    VALUES (?, ?, ?, ?)
    """, (
        "demo",
        generate_password_hash("demo"),
        "Amo il grunge e il rock anni 90.",
        "https://i.pravatar.cc/150?img=3"
    ))

    # Gruppo di esempio
    c.execute("""
    INSERT INTO groups (name, description)
    VALUES (?, ?)
    """, ("Grunge Lovers", "Per chi vive di chitarre distorte e urla catartiche."))

    # Post di esempio
    c.execute("""
    INSERT INTO posts (user_id, song, artist, clip, clip_type, mood, cover, likes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,
        "Smells Like Teen Spirit",
        "Nirvana",
        "https://open.spotify.com/track/5ghIJDpPoe3CfHMGu71E6T",
        "spotify",
        "Rock",
        "https://i.scdn.co/image/ab67616d0000b273b3e3e0e0e0e0e0e0e0e0e0e0",
        5
    ))

    conn.commit()
    conn.close()


init_db()


def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_user():
    user = current_user()
    notif_count = 0
    if user:
        conn = get_db()
        notif_count = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user["id"],)
        ).fetchone()["c"]
        conn.close()
    return dict(current_user=user, notif_count=notif_count)


# HOME / FEED
@app.route("/")
def index():
    conn = get_db()
    posts = conn.execute("""
        SELECT posts.*, users.username, users.avatar
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", posts=posts)


# REGISTRAZIONE
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        bio = request.form["bio"]
        avatar = request.form["avatar"] or "https://i.pravatar.cc/150"

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO users (username, password_hash, bio, avatar)
                VALUES (?, ?, ?, ?)
            """, (username, generate_password_hash(password), bio, avatar))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username già esistente.")
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        session["user_id"] = user["id"]
        return redirect("/")
    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return render_template("login.html", error="Credenziali non valide.")
    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# AGGIUNGI POST
@app.route("/add", methods=["POST"])
def add():
    user = current_user()
    if not user:
        return redirect("/login")

    song = request.form["song"]
    artist = request.form["artist"]
    clip = request.form["clip"]
    clip_type = request.form["clip_type"]
    mood = request.form["mood"]
    cover = request.form["cover"]

    conn = get_db()
    conn.execute("""
        INSERT INTO posts (user_id, song, artist, clip, clip_type, mood, cover)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user["id"], song, artist, clip, clip_type, mood, cover))
    conn.commit()
    conn.close()
    return redirect("/")


# LIKE
@app.route("/like/<int:post_id>")
def like(post_id):
    user = current_user()
    if not user:
        return redirect("/login")
    conn = get_db()
    conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect("/")


# COMMENTI
@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    user = current_user()
    if not user:
        return redirect("/login")
    text = request.form["text"]

    conn = get_db()
    conn.execute("""
        INSERT INTO comments (post_id, user_id, text)
        VALUES (?, ?, ?)
    """, (post_id, user["id"], text))

    # notifica all'autore del post
    post = conn.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post and post["user_id"] != user["id"]:
        conn.execute("""
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        """, (post["user_id"], f"{user['username']} ha commentato il tuo post."))
    conn.commit()
    conn.close()
    return redirect("/")


# PROFILO
@app.route("/profile/<username>")
def profile(username):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        conn.close()
        return "Utente non trovato", 404
    posts = conn.execute("""
        SELECT * FROM posts WHERE user_id = ? ORDER BY id DESC
    """, (user["id"],)).fetchall()
    conn.close()
    return render_template("profile.html", profile_user=user, posts=posts)


# NOTIFICHE
@app.route("/notifications")
def notifications():
    user = current_user()
    if not user:
        return redirect("/login")
    conn = get_db()
    notifs = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return render_template("notifications.html", notifications=notifs)


# GRUPPI
@app.route("/groups")
def groups():
    conn = get_db()
    groups = conn.execute("SELECT * FROM groups").fetchall()
    conn.close()
    return render_template("groups.html", groups=groups)


@app.route("/add_group", methods=["POST"])
def add_group():
    user = current_user()
    if not user:
        return redirect("/login")
    name = request.form["name"]
    description = request.form["description"]
    conn = get_db()
    conn.execute("INSERT INTO groups (name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    conn.close()
    return redirect("/groups")


# CHAT SEMPLICE NEI GRUPPI
@app.route("/groups/<int:group_id>", methods=["GET", "POST"])
def group_detail(group_id):
    user = current_user()
    conn = get_db()
    group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
    if not group:
        conn.close()
        return "Gruppo non trovato", 404

    if request.method == "POST":
        if not user:
            conn.close()
            return redirect("/login")
        text = request.form["text"]
        conn.execute("""
            INSERT INTO group_messages (group_id, user_id, text)
            VALUES (?, ?, ?)
        """, (group_id, user["id"], text))
        conn.commit()

    messages = conn.execute("""
        SELECT group_messages.*, users.username, users.avatar
        FROM group_messages
        JOIN users ON group_messages.user_id = users.id
        WHERE group_id = ?
        ORDER BY group_messages.id DESC
    """, (group_id,)).fetchall()
    conn.close()
    return render_template("group_detail.html", group=group, messages=messages)


if __name__ == "__main__":
    app.run(debug=True)
