from flask import Flask, render_template, request, redirect, session
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "change-me"

# 🔥 SUPABASE POSTGRES
DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# CONNECT DATABASE
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL)


# =========================
# INIT TABLES
# =========================
def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        xp INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts(
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT,
        votes INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments(
        id SERIAL PRIMARY KEY,
        post_id INTEGER,
        author TEXT,
        content TEXT
    )
    """)

    con.commit()
    con.close()


init_db()


# =========================
# HOME
# =========================
@app.route("/")
def home():
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = cur.fetchall()

    con.close()

    return render_template("index.html", posts=posts, user=session.get("user"))


# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = get_db()
        cur = con.cursor()

        try:
            cur.execute(
                "INSERT INTO users(username,password) VALUES(%s,%s)",
                (u, p)
            )
            con.commit()
            con.close()
            return redirect("/login")

        except:
            con.close()
            return "Username already exists"

    return render_template("register.html")


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = get_db()
        cur = con.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (u, p)
        )

        user = cur.fetchone()
        con.close()

        if user:
            session["user"] = u
            return redirect("/")

        return "Wrong username/password"

    return render_template("login.html")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# CREATE POST
# =========================
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


# =========================
# POST DETAIL + COMMENT
# =========================
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


# =========================
# VOTE (v1 - chưa chống spam)
# =========================
@app.route("/vote/<int:pid>")
def vote(pid):
    if "user" not in session:
        return redirect("/login")

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "UPDATE posts SET votes = votes + 1 WHERE id=%s",
        (pid,)
    )

    con.commit()
    con.close()

    return redirect("/")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
