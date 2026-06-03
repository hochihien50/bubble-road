from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "change-me"

DB = "bubble.db"


def get_db():
    return sqlite3.connect(DB)


def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        xp INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        author TEXT,
        votes INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        author TEXT,
        content TEXT
    )
    """)

    con.commit()
    con.close()


# Tạo database ngay khi app khởi động
init_db()


@app.route("/")
def home():
    con = get_db()
    posts = con.execute(
        "SELECT * FROM posts ORDER BY id DESC"
    ).fetchall()
    con.close()

    return render_template(
        "index.html",
        posts=posts,
        user=session.get("user")
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = get_db()

        try:
            con.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (u, p)
            )
            con.commit()
            con.close()

            return redirect("/login")

        except:
            con.close()
            return "Username already exists"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = get_db()

        user = con.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (u, p)
        ).fetchone()

        con.close()

        if user:
            session["user"] = u
            return redirect("/")

        return "Wrong username/password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/create", methods=["GET", "POST"])
def create():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        con = get_db()

        con.execute(
            "INSERT INTO posts(title,content,author) VALUES(?,?,?)",
            (title, content, session["user"])
        )

        con.execute(
            "UPDATE users SET xp=xp+10 WHERE username=?",
            (session["user"],)
        )

        con.commit()
        con.close()

        return redirect("/")

    return render_template("create.html")


@app.route("/post/<int:pid>", methods=["GET", "POST"])
def post(pid):
    con = get_db()

    if request.method == "POST" and "user" in session:
        con.execute(
            "INSERT INTO comments(post_id,author,content) VALUES(?,?,?)",
            (pid, session["user"], request.form["content"])
        )

        con.execute(
            "UPDATE users SET xp=xp+2 WHERE username=?",
            (session["user"],)
        )

        con.commit()

    p = con.execute(
        "SELECT * FROM posts WHERE id=?",
        (pid,)
    ).fetchone()

    comments = con.execute(
        "SELECT * FROM comments WHERE post_id=?",
        (pid,)
    ).fetchall()

    con.close()

    return render_template(
        "post.html",
        post=p,
        comments=comments,
        user=session.get("user")
    )


@app.route("/vote/<int:pid>")
def vote(pid):
    if "user" not in session:
        return redirect("/login")

    con = get_db()

    con.execute(
        "UPDATE posts SET votes=votes+1 WHERE id=?",
        (pid,)
    )

    con.commit()
    con.close()

    return redirect("/")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
