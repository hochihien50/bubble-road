from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import bcrypt

app = Flask(__name__)
app.secret_key = "change-me"

DATABASE_URL = os.getenv("DATABASE_URL")


# ======================
# DB CONNECT (SAFE)
# ======================
def get_db():
    return psycopg2.connect(DATABASE_URL)


# ======================
# INIT DB SAFE (NO CRASH)
# ======================
def init_db():
    con = get_db()
    cur = con.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        role TEXT DEFAULT 'user'
    )
    """)

    # POSTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT,
        votes INTEGER DEFAULT 0
    )
    """)

    # COMMENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id SERIAL PRIMARY KEY,
        post_id INTEGER,
        author TEXT,
        content TEXT
    )
    """)

    # VOTES (ANTI SPAM)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id SERIAL PRIMARY KEY,
        username TEXT,
        post_id INTEGER,
        UNIQUE(username, post_id)
    )
    """)

    con.commit()
    con.close()


init_db()


# ======================
# HOME
# ======================
@app.route("/")
def home():
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = cur.fetchall()

    con.close()
    return render_template("index.html", posts=posts, user=session.get("user"))


# ======================
# REGISTER
# ======================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt())

        con = get_db()
        cur = con.cursor()

        try:
            cur.execute(
                "INSERT INTO users(username,password) VALUES(%s,%s)",
                (u, hashed.decode())
            )
            con.commit()
        except:
            con.close()
            return "User exists"

        con.close()
        return redirect("/login")

    return render_template("register.html")


# ======================
# LOGIN
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT password FROM users WHERE username=%s", (u,))
        data = cur.fetchone()
        con.close()

        if data and bcrypt.checkpw(p.encode(), data[0].encode()):
            session["user"] = u
            return redirect("/")

        return "Wrong login"

    return render_template("login.html")


# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ======================
# CREATE POST
# ======================
@app.route("/create", methods=["GET", "POST"])
def create():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        con = get_db()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO posts(title,content,author) VALUES(%s,%s,%s)",
            (title, content, session["user"])
        )

        cur.execute(
            "UPDATE users SET xp = xp + 10 WHERE username=%s",
            (session["user"],)
        )

        con.commit()
        con.close()

        return redirect("/")

    return render_template("create.html")


# ======================
# POST + COMMENT
# ======================
@app.route("/post/<int:pid>", methods=["GET", "POST"])
def post(pid):
    con = get_db()
    cur = con.cursor()

    if request.method == "POST" and "user" in session:
        cur.execute(
            "INSERT INTO comments(post_id,author,content) VALUES(%s,%s,%s)",
            (pid, session["user"], request.form["content"])
        )

        cur.execute(
            "UPDATE users SET xp = xp + 2 WHERE username=%s",
            (session["user"],)
        )

        con.commit()
        return redirect(f"/post/{pid}")

    cur.execute("SELECT * FROM posts WHERE id=%s", (pid,))
    post_data = cur.fetchone()

    cur.execute("SELECT * FROM comments WHERE post_id=%s", (pid,))
    comments = cur.fetchall()

    con.close()

    return render_template(
        "post.html",
        post=post_data,
        comments=comments,
        user=session.get("user")
    )


# ======================
# VOTE (ANTI SPAM FIX)
# ======================
@app.route("/vote/<int:pid>", methods=["POST"])
def vote(pid):
    if "user" not in session:
        return redirect("/login")

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT 1 FROM votes WHERE username=%s AND post_id=%s",
        (session["user"], pid)
    )

    if cur.fetchone():
        con.close()
        return redirect("/")

    cur.execute(
        "INSERT INTO votes(username,post_id) VALUES(%s,%s)",
        (session["user"], pid)
    )

    cur.execute(
        "UPDATE posts SET votes = votes + 1 WHERE id=%s",
        (pid,)
    )

    cur.execute(
        "UPDATE users SET xp = xp + 1 WHERE username=%s",
        (session["user"],)
    )

    con.commit()
    con.close()

    return redirect("/")


# ======================
# PROFILE (FIX NO LEVEL ERROR)
# ======================
@app.route("/profile/<user>")
def profile(user):
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT xp, level FROM users WHERE username=%s", (user,))
    data = cur.fetchone()

    con.close()

    # FIX CRASH
    if not data:
        return "User not found"

    return render_template(
        "profile.html",
        user=user,
        data=data
    )


# ======================
# LEADERBOARD (SAFE)
# ======================
@app.route("/leaderboard")
def leaderboard():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT username, xp
        FROM users
        ORDER BY xp DESC
        LIMIT 10
    """)
    users = cur.fetchall()

    con.close()

    return render_template("leaderboard.html", users=users)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
