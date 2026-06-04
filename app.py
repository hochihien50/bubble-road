from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import bcrypt

app = Flask(__name__)
app.secret_key = "change-me"

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL)


# ======================
# INIT DB (optional)
# ======================
def init_db():
    con = get_db()
    cur = con.cursor()
    con.commit()
    con.close()


init_db()

# ======================
# REGISTER (bcrypt)
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
# PROFILE
# ======================
@app.route("/profile/<user>")
def profile(user):
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT xp, role FROM users WHERE username=%s", (user,))
    u = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM posts WHERE author=%s", (user,))
    posts = cur.fetchone()

    con.close()

    return render_template("profile.html", user=user, data=u, posts=posts)


# ======================
# LEADERBOARD
# ======================
@app.route("/leaderboard")
def leaderboard():
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT username, xp FROM users ORDER BY xp DESC LIMIT 10")
    users = cur.fetchall()

    con.close()

    return render_template("leaderboard.html", users=users)


# ======================
# CREATE POST
# ======================
@app.route("/create", methods=["POST"])
def create():
    if "user" not in session:
        return redirect("/login")

    title = request.form["title"]
    content = request.form["content"]

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "INSERT INTO posts(title,content,author) VALUES(%s,%s,%s)",
        (title, content, session["user"])
    )

    cur.execute(
        "UPDATE users SET xp=xp+10 WHERE username=%s",
        (session["user"],)
    )

    con.commit()
    con.close()

    return redirect("/")


# ======================
# VOTE (ANTI SPAM)
# ======================
@app.route("/vote/<int:pid>")
def vote(pid):
    if "user" not in session:
        return redirect("/login")

    u = session["user"]

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT 1 FROM votes WHERE username=%s AND post_id=%s",
        (u, pid)
    )

    if cur.fetchone():
        return "Already voted"

    cur.execute(
        "INSERT INTO votes(username,post_id) VALUES(%s,%s)",
        (u, pid)
    )

    cur.execute(
        "UPDATE posts SET votes=votes+1 WHERE id=%s",
        (pid,)
    )

    con.commit()
    con.close()

    return redirect("/")


# ======================
# REPORT SYSTEM
# ======================
@app.route("/report", methods=["POST"])
def report():
    if "user" not in session:
        return redirect("/login")

    target_type = request.form["type"]
    target_id = request.form["id"]
    reason = request.form["reason"]

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO reports(reporter,target_type,target_id,reason)
        VALUES(%s,%s,%s,%s)
    """, (session["user"], target_type, target_id, reason))

    con.commit()
    con.close()

    return "Reported"


# ======================
# ADMIN PANEL
# ======================
@app.route("/admin")
def admin():
    if session.get("user") != "admin":
        return "No access"

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM reports ORDER BY id DESC")
    reports = cur.fetchall()

    con.close()

    return render_template("admin.html", reports=reports)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
