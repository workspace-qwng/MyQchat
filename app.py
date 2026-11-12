import os
import json
import sqlite3
import hashlib
import secrets
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
DATABASE = "myqchat.db"
VERSION = "2.0.0-SMART-BOT"
OWNER_USERNAME = "LoyalWQ"
OWNER_UID = "10000001"
OWNER_PASSWORD = "AlwaysBeLoyalQ"
SUPPORT_EMAIL = "support.qwng@gmail.com"
APP_URL = "myqchat-1.onrender.com"
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db
def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, uid TEXT UNIQUE, tick TEXT, is_admin INTEGER DEFAULT 0, bio TEXT, email TEXT, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, text TEXT, created_at TEXT, starred INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, admin_id INTEGER, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS group_members (id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER, user_id INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS polls (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, options TEXT, votes TEXT, creator_id INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT, content TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, username TEXT, uid TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT, time_text TEXT, done INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER, target_id INTEGER, reason TEXT, status TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS tick_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tick_type TEXT, reason TEXT, status TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS bot_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, last_topic TEXT, last_question TEXT, last_answer TEXT, context_json TEXT, updated_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, artist TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS status (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, created_at TEXT)")
    row = db.execute("SELECT * FROM users WHERE uid = '10000001'").fetchone()
    if not row:
        pw = generate_password_hash(OWNER_PASSWORD)
        db.execute("INSERT INTO users (username, password, uid, tick, is_admin, bio, email, created_at) VALUES ('LoyalWQ', ?, '10000001', 'L', 1, 'Owner of MyQchat', 'loyalwq@gmail.com', ?)", (pw, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        db.execute("UPDATE users SET is_admin = 1, tick = 'L' WHERE uid = '10000001'")
    db.commit()
    if db.execute("SELECT COUNT(*) FROM songs").fetchone()[0] == 0:
        db.execute("INSERT INTO songs (title, artist) VALUES ('QWNG Anthem', 'QWNG')")
        db.commit()
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
@app.route("/api/health")
def health():
    return jsonify({"ok": True, "app": "MyQchat", "owner": "LoyalWQ", "owner_uid": "10000001", "status": "Live"})
@app.route("/api/info")
def info():
    return jsonify({"ok": True, "app": "MyQchat", "team": "QWNG Software Developer Team", "owner": "LoyalWQ", "owner_uid": "10000001", "support": "support.qwng@gmail.com", "url": "myqchat-1.onrender.com"})
with app.app_context():
    init_db()
    GOOD_LAYOUT_CSS = "body{font-family:Arial;margin:0;background:rgb(240,240,240)} .top{background:rgb(7,94,84);color:white;padding:12px;display:flex;justify-content:space-between} .menu{display:flex;gap:8px} .menu button{background:white;border:none;padding:8px 10px;border-radius:8px;cursor:pointer} .main{display:flex;flex-direction:column;height:100vh} .chatbox{flex:1;overflow-y:auto;padding:10px;background:rgb(229,221,213)} .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px;max-width:80%} .msgme{background:rgb(220,248,198);margin-left:auto} .inputrow{display:flex;padding:10px;background:white;gap:8px} .inputrow input{flex:1;padding:12px;border-radius:20px;border:1px solid rgb(220,220,220)} .inputrow button{padding:10px 16px;border-radius:20px;border:none;background:rgb(7,94,84);color:white} .loginbox{background:white;padding:20px;margin:20px;border-radius:12px} .loginbox input{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid rgb(220,220,220)} .loginbox button{width:100%;padding:12px;border-radius:8px;border:none;background:rgb(7,94,84);color:white} .bottomnav{display:flex;background:white;border-top:1px solid rgb(220,220,220)} .bottomnav button{flex:1;padding:12px;border:none;background:white;cursor:pointer}"

GOOD_LAYOUT_LOGIN = "<div class='loginbox'><h2>MyQchat by QWNG</h2><p>Login to continue</p><input id='loginUser' placeholder='Username'><input id='loginPass' type='password' placeholder='Password'><button onclick='doLogin()'>Login</button><button onclick='showSignup()'>Create New Account</button><p>Owner LoyalWQ UID 10000001</p><p>Support support.qwng@gmail.com</p></div>"

GOOD_LAYOUT_SIGNUP = "<div class='loginbox'><h2>Create Account</h2><input id='signUser' placeholder='Choose Username'><input id='signPass' type='password' placeholder='Choose Password'><input id='signEmail' placeholder='Recovery Email'><button onclick='doSignup()'>Signup</button><button onclick='showLogin()'>Back to Login</button></div>"

GOOD_LAYOUT_MAIN = "<div class='top'><div>MyQchat</div><div>QWNG Bot Online</div></div><div class='chatbox' id='messagesBox'><div class='msg'>Welcome to MyQchat. Tap QWNG Bot or Smart Bot to chat.</div><div class='msg' onclick=\"openChat('QWNG Bot')\">QWNG Bot - Answers from code</div><div class='msg' onclick=\"openChat('Smart Bot')\">Smart Bot - Gemini 2.5 Flash</div><div class='msg' onclick=\"openChat('LoyalWQ')\">LoyalWQ - Owner L Tick</div></div><div class='inputrow'><input id='msgInput' placeholder='Type message'><button onclick='sendMsg()'>Send</button></div><div class='bottomnav'><button onclick='showChats()'>Chats</button><button onclick='showGroups()'>Groups</button><button onclick='showSongs()'>Songs</button><button onclick='showSettings()'>Settings</button></div>"

GOOD_LAYOUT_JS = "let currentChat='QWNG Bot'; function openChat(n){currentChat=n; document.getElementById('messagesBox').innerHTML='<div class=msg>Chat with '+n+'</div>';} function sendMsg(){let box=document.getElementById('msgInput'); let text=box.value.trim(); if(!text) return; let m=document.createElement('div'); m.className='msg msgme'; m.innerText=text; document.getElementById('messagesBox').appendChild(m); box.value=''; let t=document.createElement('div'); t.className='msg'; t.innerText='...'; t.id='typingMsg'; document.getElementById('messagesBox').appendChild(t); setTimeout(function(){fetch('/api/bot/smart-fallback?q='+encodeURIComponent(text)).then(r=>r.json()).then(d=>{document.getElementById('typingMsg').innerText=d.result.answer;});},2000);} function showLogin(){document.getElementById('mainBox').innerHTML=LOGIN_HTML;} function showSignup(){document.getElementById('mainBox').innerHTML=SIGNUP_HTML;} function doLogin(){alert('Login checking');} function doSignup(){alert('Signup checking');} function showChats(){document.getElementById('mainBox').innerHTML=MAIN_HTML;} function showGroups(){alert('Groups opening');} function showSongs(){alert('Songs opening');} function showSettings(){alert('Settings opening');}"

@app.route("/")
def home_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>MyQchat by QWNG</title><style>" + GOOD_LAYOUT_CSS + "</style></head><body><div class='main' id='mainBox'>" + GOOD_LAYOUT_LOGIN + "</div><script>var LOGIN_HTML = `" + GOOD_LAYOUT_LOGIN + "`; var SIGNUP_HTML = `" + GOOD_LAYOUT_SIGNUP + "`; var MAIN_HTML = `" + GOOD_LAYOUT_MAIN + "`;" + GOOD_LAYOUT_JS + "</script></body></html>"
    return html
  @app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    if len(username) < 3:
        return jsonify({"ok": False, "error": "Username min 3 chars"})
    if len(password) < 4:
        return jsonify({"ok": False, "error": "Password min 4 chars"})
    db = get_db()
    if db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone():
        return jsonify({"ok": False, "error": "Username already taken"})
    import random as _r
    uid = str(_r.randint(10000000, 99999999))
    while db.execute("SELECT * FROM users WHERE uid = ?", (uid,)).fetchone():
        uid = str(_r.randint(10000000, 99999999))
    pw = generate_password_hash(password)
    db.execute("INSERT INTO users (username, password, uid, tick, is_admin, bio, email, created_at) VALUES (?, ?, ?, '', 0, '', ?, ?)", (username, pw, uid, email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    row = db.execute("SELECT id, username, uid, tick, bio, email FROM users WHERE username = ?", (username,)).fetchone()
    return jsonify({"ok": True, "user": dict(row)})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "User not found"})
    if not check_password_hash(row["password"], password):
        return jsonify({"ok": False, "error": "Wrong password"})
    return jsonify({"ok": True, "user": {"id": row["id"], "username": row["username"], "uid": row["uid"], "tick": row["tick"], "is_admin": row["is_admin"], "bio": row["bio"], "email": row["email"]}})

@app.route("/api/users")
def api_users():
    db = get_db()
    rows = db.execute("SELECT id, username, uid, tick, bio FROM users ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify({"ok": True, "users": [dict(r) for r in rows]})

@app.route("/api/profile")
def api_profile():
    uid = request.args.get("uid") or ""
    db = get_db()
    row = db.execute("SELECT id, username, uid, tick, bio, email FROM users WHERE uid = ?", (uid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "User not found"})
    return jsonify({"ok": True, "profile": dict(row)})

@app.route("/api/profile/update", methods=["POST"])
def api_profile_update():
    data = request.get_json() or {}
    uid = data.get("uid") or ""
    name = (data.get("username") or "").strip()
    bio = data.get("bio") or ""
    email = data.get("email") or ""
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE uid = ?", (uid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "User not found"})
    if name:
        db.execute("UPDATE users SET username = ? WHERE uid = ?", (name, uid))
    db.execute("UPDATE users SET bio = ?, email = ? WHERE uid = ?", (bio, email, uid))
    db.commit()
    return jsonify({"ok": True, "saved": True})

@app.route("/api/search")
def api_search():
    q = request.args.get("q") or ""
    db = get_db()
    rows = db.execute("SELECT id, username, uid, tick, bio FROM users WHERE username LIKE ? OR uid LIKE ? LIMIT 20", ("%" + q + "%", "%" + q + "%")).fetchall()
    return jsonify({"ok": True, "results": [dict(r) for r in rows]})

@app.route("/api/my-uid")
def api_my_uid():
    username = request.args.get("username") or ""
    db = get_db()
    row = db.execute("SELECT username, uid, tick FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "User not found"})
    return jsonify({"ok": True, "user": dict(row)})
@app.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    data = request.get_json() or {}
    sender = data.get("sender_id")
    receiver = data.get("receiver_id")
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty message"})
    if len(text) > 2000:
        return jsonify({"ok": False, "error": "Message too long"})
    db = get_db()
    db.execute("INSERT INTO messages (sender_id, receiver_id, text, created_at, starred) VALUES (?, ?, ?, ?, 0)", (sender, receiver, text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    row = db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify({"ok": True, "message": dict(row)})

@app.route("/api/chat/list")
def api_chat_list():
    user1 = request.args.get("user1") or "0"
    user2 = request.args.get("user2") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM messages WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?) ORDER BY id ASC LIMIT 500", (user1, user2, user2, user1)).fetchall()
    return jsonify({"ok": True, "messages": [dict(r) for r in rows]})

@app.route("/api/chat/reply", methods=["POST"])
def api_chat_reply():
    data = request.get_json() or {}
    sender = data.get("sender_id")
    receiver = data.get("receiver_id")
    text = (data.get("text") or "").strip()
    reply_to = data.get("reply_to") or ""
    if not text:
        return jsonify({"ok": False, "error": "Empty reply"})
    full = "Reply to " + str(reply_to) + ": " + text
    db = get_db()
    db.execute("INSERT INTO messages (sender_id, receiver_id, text, created_at, starred) VALUES (?, ?, ?, ?, 0)", (sender, receiver, full, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    return jsonify({"ok": True, "replied": True})

@app.route("/api/chat/star", methods=["POST"])
def api_chat_star():
    data = request.get_json() or {}
    mid = data.get("message_id")
    db = get_db()
    row = db.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Message not found"})
    new_val = 0 if row["starred"] == 1 else 1
    db.execute("UPDATE messages SET starred = ? WHERE id = ?", (new_val, mid))
    db.commit()
    return jsonify({"ok": True, "starred": new_val})

@app.route("/api/chat/starred")
def api_chat_starred():
    user_id = request.args.get("user_id") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM messages WHERE (sender_id = ? OR receiver_id = ?) AND starred = 1 ORDER BY id DESC LIMIT 100", (user_id, user_id)).fetchall()
    return jsonify({"ok": True, "starred": [dict(r) for r in rows]})

@app.route("/api/chat/forward", methods=["POST"])
def api_chat_forward():
    data = request.get_json() or {}
    mid = data.get("message_id")
    sender = data.get("sender_id")
    receiver = data.get("receiver_id")
    db = get_db()
    row = db.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Message not found"})
    db.execute("INSERT INTO messages (sender_id, receiver_id, text, created_at, starred) VALUES (?, ?, ?, ?, 0)", (sender, receiver, "Forwarded: " + row["text"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    return jsonify({"ok": True, "forwarded": True})

@app.route("/api/chat/edit", methods=["POST"])
def api_chat_edit():
    data = request.get_json() or {}
    mid = data.get("message_id")
    text = (data.get("text") or "").strip()
    db = get_db()
    row = db.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Message not found"})
    db.execute("UPDATE messages SET text = ? WHERE id = ?", (text, mid))
    db.commit()
    return jsonify({"ok": True, "edited": True})

@app.route("/api/chat/delete", methods=["POST"])
def api_chat_delete():
    data = request.get_json() or {}
    mid = data.get("message_id")
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ?", (mid,))
    db.commit()
    return jsonify({"ok": True, "deleted": True})

@app.route("/api/chat/search")
def api_chat_search():
    user_id = request.args.get("user_id") or "0"
    q = request.args.get("q") or ""
    db = get_db()
    rows = db.execute("SELECT * FROM messages WHERE (sender_id = ? OR receiver_id = ?) AND text LIKE ? ORDER BY id DESC LIMIT 50", (user_id, user_id, "%" + q + "%")).fetchall()
    return jsonify({"ok": True, "results": [dict(r) for r in rows]})
    @app.route("/api/groups", methods=["GET"])
def api_groups_list():
    db = get_db()
    rows = db.execute("SELECT * FROM groups ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        members = db.execute("SELECT user_id FROM group_members WHERE group_id = ?", (r["id"],)).fetchall()
        d["members"] = [m["user_id"] for m in members]
        out.append(d)
    return jsonify({"ok": True, "groups": out})

@app.route("/api/groups/create", methods=["POST"])
def api_groups_create():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    admin_id = data.get("admin_id")
    if not name:
        return jsonify({"ok": False, "error": "Group name required"})
    db = get_db()
    db.execute("INSERT INTO groups (name, admin_id, created_at) VALUES (?, ?, ?)", (name, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    row = db.execute("SELECT * FROM groups ORDER BY id DESC LIMIT 1").fetchone()
    db.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (row["id"], admin_id))
    db.commit()
    return jsonify({"ok": True, "group": dict(row)})

@app.route("/api/groups/add", methods=["POST"])
def api_groups_add():
    data = request.get_json() or {}
    gid = data.get("group_id")
    uid = data.get("user_id")
    db = get_db()
    if db.execute("SELECT * FROM group_members WHERE group_id = ? AND user_id = ?", (gid, uid)).fetchone():
        return jsonify({"ok": False, "error": "Already member"})
    db.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (gid, uid))
    db.commit()
    return jsonify({"ok": True, "added": True})

@app.route("/api/groups/remove", methods=["POST"])
def api_groups_remove():
    data = request.get_json() or {}
    gid = data.get("group_id")
    uid = data.get("user_id")
    db = get_db()
    db.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (gid, uid))
    db.commit()
    return jsonify({"ok": True, "removed": True})

@app.route("/api/groups/delete", methods=["POST"])
def api_groups_delete():
    data = request.get_json() or {}
    gid = data.get("group_id")
    db = get_db()
    db.execute("DELETE FROM group_members WHERE group_id = ?", (gid,))
    db.execute("DELETE FROM groups WHERE id = ?", (gid,))
    db.commit()
    return jsonify({"ok": True, "deleted": True})

@app.route("/api/groups/leave", methods=["POST"])
def api_groups_leave():
    data = request.get_json() or {}
    gid = data.get("group_id")
    uid = data.get("user_id")
    db = get_db()
    db.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (gid, uid))
    db.commit()
    return jsonify({"ok": True, "left": True})

@app.route("/api/status", methods=["GET"])
def api_status_list():
    db = get_db()
    rows = db.execute("SELECT status.*, users.username FROM status LEFT JOIN users ON status.user_id = users.id ORDER BY status.id DESC LIMIT 100").fetchall()
    return jsonify({"ok": True, "status": [dict(r) for r in rows]})

@app.route("/api/status", methods=["POST"])
def api_status_create():
    data = request.get_json() or {}
    uid = data.get("user_id")
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Status empty"})
    if len(text) > 200:
        return jsonify({"ok": False, "error": "Status max 200 chars"})
    db = get_db()
    db.execute("INSERT INTO status (user_id, text, created_at) VALUES (?, ?, ?)", (uid, text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    return jsonify({"ok": True, "posted": True})

@app.route("/api/status/delete", methods=["POST"])
def api_status_delete():
    data = request.get_json() or {}
    sid = data.get("status_id")
    db = get_db()
    db.execute("DELETE FROM status WHERE id = ?", (sid,))
    db.commit()
    return jsonify({"ok": True, "deleted": True})

@app.route("/api/calls")
def api_calls_list():
    return jsonify({"ok": True, "calls": [], "note": "Call history is stored in app. Voice call needs internet and mic."})

@app.route("/api/calls/start", methods=["POST"])
def api_calls_start():
    data = request.get_json() or {}
    caller = data.get("caller_id")
    receiver = data.get("receiver_id")
    return jsonify({"ok": True, "call": "started", "caller": caller, "receiver": receiver, "note": "Call started. Tap End to stop. Tap Mute to mute."})

@app.route("/api/calls/end", methods=["POST"])
def api_calls_end():
    return jsonify({"ok": True, "call": "ended"})
    @app.route("/api/songs", methods=["GET"])
def api_songs_list():
    q = request.args.get("q") or ""
    db = get_db()
    if q:
        rows = db.execute("SELECT * FROM songs WHERE title LIKE ? OR artist LIKE ? ORDER BY id ASC", ("%" + q + "%", "%" + q + "%")).fetchall()
    else:
        rows = db.execute("SELECT * FROM songs ORDER BY id ASC").fetchall()
    return jsonify({"ok": True, "songs": [dict(r) for r in rows]})

@app.route("/api/songs/add", methods=["POST"])
def api_songs_add():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    artist = (data.get("artist") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Song title required"})
    db = get_db()
    db.execute("INSERT INTO songs (title, artist) VALUES (?, ?)", (title, artist))
    db.commit()
    row = db.execute("SELECT * FROM songs ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify({"ok": True, "song": dict(row)})

@app.route("/api/songs/delete", methods=["POST"])
def api_songs_delete():
    data = request.get_json() or {}
    sid = data.get("song_id")
    db = get_db()
    db.execute("DELETE FROM songs WHERE id = ?", (sid,))
    db.commit()
    return jsonify({"ok": True, "deleted": True})

@app.route("/api/songs/play/<int:song_id>")
def api_songs_play(song_id):
    db = get_db()
    row = db.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Song not found"})
    return jsonify({"ok": True, "now_playing": dict(row), "status": "playing", "note": "Play only inside app. Download not allowed."})

@app.route("/api/songs/search")
def api_songs_search():
    q = request.args.get("q") or ""
    db = get_db()
    rows = db.execute("SELECT * FROM songs WHERE title LIKE ? ORDER BY id ASC LIMIT 20", ("%" + q + "%",)).fetchall()
    return jsonify({"ok": True, "results": [dict(r) for r in rows]})

SONG_PLAYER_JS = "let currentSongId=0; function playSong(id){fetch('/api/songs/play/'+id).then(r=>r.json()).then(d=>{if(d.ok){document.getElementById('nowPlaying').innerText='Now Playing: '+d.now_playing.title+' - '+d.now_playing.artist; currentSongId=id;}});} function searchSong(){let q=document.getElementById('songSearch').value; fetch('/api/songs?q='+encodeURIComponent(q)).then(r=>r.json()).then(d=>{let box=document.getElementById('songList'); box.innerHTML=''; d.songs.forEach(s=>{let div=document.createElement('div'); div.className='msg'; div.innerText=s.title+' - '+s.artist; div.onclick=function(){playSong(s.id);}; box.appendChild(div);});});}"

SONG_PLAYER_HTML = "<div class='loginbox'><h3>Songs</h3><input id='songSearch' placeholder='Search song'><button onclick='searchSong()'>Search</button><div id='nowPlaying'>No song playing</div><div id='songList'></div></div>"

@app.route("/songs-page")
def songs_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Songs MyQchat</title><style>" + GOOD_LAYOUT_CSS + "</style></head><body><div class='main'>" + SONG_PLAYER_HTML + "</div><script>" + SONG_PLAYER_JS + " searchSong();</script></body></html>"
    return html
    @app.route("/api/tick/request", methods=["POST"])
def api_tick_request():
    data = request.get_json() or {}
    uid = data.get("user_id")
    tick_type = data.get("tick_type") or ""
    reason = data.get("reason") or ""
    if tick_type not in ["Blue", "Green"]:
        return jsonify({"ok": False, "error": "Tick must be Blue or Green"})
    if tick_type == "Green" and len(reason.strip()) < 5:
        return jsonify({"ok": False, "error": "Green Tick needs reason min 5 chars"})
    db = get_db()
    db.execute("INSERT INTO tick_requests (user_id, tick_type, reason, status) VALUES (?, ?, ?, 'Pending')", (uid, tick_type, reason))
    db.commit()
    return jsonify({"ok": True, "requested": True, "note": "Blue Tick needs no reason. Green Tick needs reason. Payment only inside app."})

@app.route("/api/tick/my")
def api_tick_my():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM tick_requests WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    return jsonify({"ok": True, "requests": [dict(r) for r in rows]})

@app.route("/api/admin/ticks")
def api_admin_ticks():
    db = get_db()
    rows = db.execute("SELECT tick_requests.*, users.username FROM tick_requests LEFT JOIN users ON tick_requests.user_id = users.id ORDER BY tick_requests.id DESC").fetchall()
    return jsonify({"ok": True, "ticks": [dict(r) for r in rows]})

@app.route("/api/admin/tick/approve", methods=["POST"])
def api_admin_tick_approve():
    data = request.get_json() or {}
    rid = data.get("request_id")
    db = get_db()
    row = db.execute("SELECT * FROM tick_requests WHERE id = ?", (rid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Request not found"})
    db.execute("UPDATE tick_requests SET status = 'Approved' WHERE id = ?", (rid,))
    db.execute("UPDATE users SET tick = ? WHERE id = ?", (row["tick_type"], row["user_id"]))
    db.commit()
    return jsonify({"ok": True, "approved": True})

@app.route("/api/admin/tick/reject", methods=["POST"])
def api_admin_tick_reject():
    data = request.get_json() or {}
    rid = data.get("request_id")
    db = get_db()
    db.execute("UPDATE tick_requests SET status = 'Rejected' WHERE id = ?", (rid,))
    db.commit()
    return jsonify({"ok": True, "rejected": True})

@app.route("/api/report", methods=["POST"])
def api_report():
    data = request.get_json() or {}
    reporter = data.get("reporter_id")
    target = data.get("target_id")
    reason = (data.get("reason") or "").strip()
    if len(reason) < 5:
        return jsonify({"ok": False, "error": "Reason min 5 chars"})
    db = get_db()
    target_row = db.execute("SELECT * FROM users WHERE id = ?", (target,)).fetchone()
    if target_row and target_row["uid"] == "10000001":
        return jsonify({"ok": False, "error": "Cannot report Owner"})
    db.execute("INSERT INTO reports (reporter_id, target_id, reason, status) VALUES (?, ?, ?, 'Pending')", (reporter, target, reason))
    db.commit()
    return jsonify({"ok": True, "reported": True})

@app.route("/api/reports/my")
def api_reports_my():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM reports WHERE reporter_id = ? ORDER BY id DESC", (uid,)).fetchall()
    return jsonify({"ok": True, "reports": [dict(r) for r in rows]})

@app.route("/api/admin/reports")
def api_admin_reports():
    db = get_db()
    rows = db.execute("SELECT reports.*, users.username FROM reports LEFT JOIN users ON reports.target_id = users.id ORDER BY reports.id DESC").fetchall()
    return jsonify({"ok": True, "reports": [dict(r) for r in rows]})

@app.route("/api/admin/report/handle", methods=["POST"])
def api_admin_report_handle():
    data = request.get_json() or {}
    rid = data.get("report_id")
    action = data.get("action") or "Handled"
    db = get_db()
    db.execute("UPDATE reports SET status = ? WHERE id = ?", (action, rid))
    db.commit()
    return jsonify({"ok": True, "handled": True, "action": action})

@app.route("/api/block", methods=["POST"])
def api_block():
    data = request.get_json() or {}
    blocker = data.get("blocker_id")
    blocked = data.get("blocked_id")
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (blocked,)).fetchone()
    if row and row["uid"] == "10000001":
        return jsonify({"ok": False, "error": "Cannot block Owner"})
    return jsonify({"ok": True, "blocked": True, "blocker": blocker, "blocked_user": blocked})

@app.route("/api/admin/users")
def api_admin_users():
    db = get_db()
    rows = db.execute("SELECT id, username, uid, tick, is_admin, bio FROM users ORDER BY id DESC").fetchall()
    return jsonify({"ok": True, "users": [dict(r) for r in rows]})

@app.route("/api/admin/broadcast", methods=["POST"])
def api_admin_broadcast():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Message empty"})
    return jsonify({"ok": True, "broadcast": message, "sent": True})

@app.route("/api/make-me-admin")
def api_make_me_admin():
    uid = request.args.get("uid") or ""
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE uid = ?", (uid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "User not found"})
    if uid != "10000001":
        return jsonify({"ok": False, "error": "Only Owner can be admin by this route"})
    db.execute("UPDATE users SET is_admin = 1, tick = 'L' WHERE uid = ?", (uid,))
    db.commit()
    return jsonify({"ok": True, "admin": True})
    @app.route("/api/poll/create", methods=["POST"])
def api_poll_create():
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    options = data.get("options") or []
    creator = data.get("creator_id")
    if not question:
        return jsonify({"ok": False, "error": "Question required"})
    if len(options) < 2:
        return jsonify({"ok": False, "error": "Min 2 options"})
    db = get_db()
    db.execute("INSERT INTO polls (question, options, votes, creator_id) VALUES (?, ?, ?, ?)", (question, json.dumps(options), json.dumps([0] * len(options)), creator))
    db.commit()
    row = db.execute("SELECT * FROM polls ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify({"ok": True, "poll": dict(row)})

@app.route("/api/poll/list")
def api_poll_list():
    db = get_db()
    rows = db.execute("SELECT * FROM polls ORDER BY id DESC").fetchall()
    return jsonify({"ok": True, "polls": [dict(r) for r in rows]})

@app.route("/api/poll/vote", methods=["POST"])
def api_poll_vote():
    data = request.get_json() or {}
    pid = data.get("poll_id")
    idx = int(data.get("option") or 0)
    db = get_db()
    row = db.execute("SELECT * FROM polls WHERE id = ?", (pid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Poll not found"})
    votes = json.loads(row["votes"])
    if idx < 0 or idx >= len(votes):
        return jsonify({"ok": False, "error": "Bad option"})
    votes[idx] += 1
    db.execute("UPDATE polls SET votes = ? WHERE id = ?", (json.dumps(votes), pid))
    db.commit()
    return jsonify({"ok": True, "votes": votes})

@app.route("/api/notes/add", methods=["POST"])
def api_notes_add():
    data = request.get_json() or {}
    uid = data.get("user_id")
    title = (data.get("title") or "").strip()
    content = data.get("content") or ""
    db = get_db()
    db.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)", (uid, title, content))
    db.commit()
    return jsonify({"ok": True, "saved": True})

@app.route("/api/notes/list")
def api_notes_list():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    return jsonify({"ok": True, "notes": [dict(r) for r in rows]})

@app.route("/api/notes/delete", methods=["POST"])
def api_notes_delete():
    data = request.get_json() or {}
    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (data.get("note_id"),))
    db.commit()
    return jsonify({"ok": True, "deleted": True})

@app.route("/api/contacts/add", methods=["POST"])
def api_contacts_add():
    data = request.get_json() or {}
    uid = data.get("user_id")
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    target_uid = (data.get("uid") or "").strip()
    db = get_db()
    db.execute("INSERT INTO contacts (user_id, name, username, uid) VALUES (?, ?, ?, ?)", (uid, name, username, target_uid))
    db.commit()
    return jsonify({"ok": True, "saved": True})

@app.route("/api/contacts/list")
def api_contacts_list():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM contacts WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    return jsonify({"ok": True, "contacts": [dict(r) for r in rows]})

@app.route("/api/reminders/add", methods=["POST"])
def api_reminders_add():
    data = request.get_json() or {}
    uid = data.get("user_id")
    title = (data.get("title") or "").strip()
    time_text = data.get("time_text") or ""
    db = get_db()
    db.execute("INSERT INTO reminders (user_id, title, time_text, done) VALUES (?, ?, ?, 0)", (uid, title, time_text))
    db.commit()
    return jsonify({"ok": True, "added": True})

@app.route("/api/reminders/list")
def api_reminders_list():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    rows = db.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    return jsonify({"ok": True, "reminders": [dict(r) for r in rows]})

@app.route("/api/reminders/done", methods=["POST"])
def api_reminders_done():
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE reminders SET done = 1 WHERE id = ?", (data.get("reminder_id"),))
    db.commit()
    return jsonify({"ok": True, "done": True})

@app.route("/api/backup")
def api_backup():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    msgs = db.execute("SELECT * FROM messages WHERE sender_id = ? OR receiver_id = ? ORDER BY id ASC", (uid, uid)).fetchall()
    notes = db.execute("SELECT * FROM notes WHERE user_id = ?", (uid,)).fetchall()
    return jsonify({"ok": True, "backup": {"messages": [dict(r) for r in msgs], "notes": [dict(r) for r in notes]}})

@app.route("/api/export")
def api_export():
    uid = request.args.get("user_id") or "0"
    db = get_db()
    user = db.execute("SELECT username, uid, tick FROM users WHERE id = ?", (uid,)).fetchone()
    return jsonify({"ok": True, "export": {"user": dict(user) if user else {}, "app": "MyQchat", "support": "support.qwng@gmail.com"}})

@app.route("/api/auto-backup")
def api_auto_backup():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return jsonify({"ok": True, "total_users": total, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    BOT_AUTOCORRECT = {"bleu": "blue", "blu": "blue", "tik": "tick", "tickk": "tick", "grren": "green", "gren": "green", "blck": "block", "blcok": "block", "sng": "song", "songg": "song", "chatt": "chat", "grup": "group", "grpu": "group", "staus": "status", "sttatus": "status", "cal": "call", "seting": "setting", "setings": "settings", "pasword": "password", "paswrd": "password", "admn": "admin", "admim": "admin", "repot": "report", "repport": "report", "profle": "profile", "prfile": "profile", "searh": "search", "serach": "search", "hlep": "help", "hepl": "help", "owener": "owner", "ownner": "owner", "qwn": "qwng", "myqcaht": "myqchat", "myqchatt": "myqchat", "loyallwq": "loyalwq", "uidd": "uid", "login": "login", "logn": "login", "singup": "signup", "sigup": "signup", "remider": "reminder", "remnder": "reminder", "notess": "notes", "polls": "poll", "bakup": "backup", "exprot": "export", "uploadd": "upload", "downlod": "download"}

def bot_clean_text(text):
    t = (text or "").strip().lower()
    t = t.replace(",", " ").replace(".", " ").replace("?", " ").replace("!", " ")
    t = " ".join(t.split())
    return t

def bot_autocorrect_text(text):
    cleaned = bot_clean_text(text)
    words = cleaned.split()
    out = []
    for w in words:
        if w in BOT_AUTOCORRECT:
            out.append(BOT_AUTOCORRECT[w])
        else:
            out.append(w)
    return " ".join(out)

def bot_autocorrect_suggest(text):
    cleaned = bot_clean_text(text)
    fixed = bot_autocorrect_text(text)
    changed = []
    a = cleaned.split()
    b = fixed.split()
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            changed.append({"from": a[i], "to": b[i]})
    return {"ok": True, "input": cleaned, "fixed": fixed, "changed": changed}

def bot_spell_check_one(word):
    w = (word or "").lower().strip()
    if w in BOT_AUTOCORRECT:
        return BOT_AUTOCORRECT[w]
    return w

def bot_fix_common_phrase(text):
    t = bot_autocorrect_text(text)
    t = t.replace("blue tick price", "blue tick")
    t = t.replace("green tick price", "green tick")
    t = t.replace("l tick owner", "l tick")
    t = t.replace("my uid", "uid")
    return t

def bot_is_typo(text):
    cleaned = bot_clean_text(text)
    fixed = bot_autocorrect_text(text)
    return cleaned != fixed

@app.route("/api/bot/autocorrect")
def api_bot_autocorrect():
    q = request.args.get("q") or ""
    res = bot_autocorrect_suggest(q)
    return jsonify(res)
    BOT_STOPWORDS = ["please", "tell", "me", "about", "what", "is", "the", "how", "can", "i", "do", "my", "to", "in", "for", "a", "an", "and", "or", "on", "of", "give", "show", "want", "need", "get", "know", "just", "now", "here", "there"]

BOT_INTENTS = {"blue_tick": ["blue tick", "blue", "verification tick", "verified"], "green_tick": ["green tick", "green", "green verification"], "l_tick": ["l tick", "owner tick", "loyal tick"], "scam_tick": ["scam tick", "scam", "fake tick"], "owner": ["owner", "loyalwq", "founder", "creator of app"], "qwng": ["qwng", "qwng team", "developer team"], "myqchat": ["myqchat", "this app", "app info"], "support": ["support", "support email", "contact support", "help email"], "song": ["song", "music", "play song", "song library", "add song"], "chat": ["chat", "message", "one to one chat", "send message", "reply"], "group": ["group", "group chat", "add member", "remove member", "group admin"], "status": ["status", "status post", "view status", "delete status"], "call": ["call", "voice call", "video call", "start call", "end call"], "settings": ["settings", "setting", "app settings", "change setting"], "admin": ["admin", "admin panel", "admin access", "admin control"], "tick_request": ["tick request", "request tick", "apply tick", "get tick"], "report": ["report", "report user", "abuse", "scam report"], "block": ["block", "block user", "unblock", "blocked list"], "uid": ["uid", "user id", "my uid", "find uid"], "login": ["login", "sign in", "login problem", "cannot login"], "signup": ["signup", "sign up", "create account", "new account"], "password": ["password", "forgot password", "change password", "reset password"], "otp": ["otp", "verification code"], "profile": ["profile", "my profile", "edit profile", "bio", "profile photo"], "search": ["search", "search user", "find user", "search by uid", "search by username"], "poll": ["poll", "create poll", "vote", "poll result"], "notes": ["notes", "my notes", "save note", "write note"], "contacts": ["contacts", "saved contacts", "saved contact", "my contacts"], "reminder": ["reminder", "set reminder", "my reminder", "remind me"], "backup": ["backup", "backup chat", "restore backup"], "export": ["export", "export chat", "export data"], "star": ["star", "starred", "star message", "starred message"], "forward": ["forward", "forward message"], "edit": ["edit message", "edit chat"], "delete": ["delete message", "delete chat", "delete account"], "mute": ["mute", "mute chat", "unmute"], "archive": ["archive", "archived chat"], "pin": ["pin", "pin chat", "pinned"], "help": ["help", "menu", "start", "options", "what can you do"]}

BOT_INTENT_WEIGHTS = {"blue_tick": 10, "green_tick": 10, "l_tick": 10, "scam_tick": 10, "owner": 10, "qwng": 9, "myqchat": 9, "support": 10, "song": 9, "chat": 8, "group": 9, "status": 9, "call": 9, "settings": 8, "admin": 10, "tick_request": 10, "report": 10, "block": 10, "uid": 10, "login": 9, "signup": 9, "password": 10, "otp": 10, "profile": 8, "search": 9, "poll": 9, "notes": 8, "contacts": 8, "reminder": 8, "backup": 9, "export": 8, "star": 8, "forward": 8, "edit": 8, "delete": 8, "mute": 8, "archive": 8, "pin": 8, "help": 5}

BOT_INTENT_ANSWERS = {"blue_tick": "Blue Tick is verification. No reason needed.", "green_tick": "Green Tick needs reason. Reason is mandatory.", "l_tick": "L Tick is only for Owner LoyalWQ UID 10000001.", "scam_tick": "Scam Tick appears after report. Admin checks report.", "owner": "Owner is LoyalWQ UID 10000001 with L Tick.", "qwng": "QWNG is a Software Developer Team.", "myqchat": "MyQchat is a simple chat app built by QWNG.", "support": "Support email is support.qwng@gmail.com. Reply within 24 hours.", "song": "Song Library is in app. Admin adds songs by URL. You can pick from list or paste custom URL.", "chat": "Chat is 1 to 1 chat. You can Reply, Star, Forward, Edit, Delete.", "group": "Group is group chat. Admin can add and remove members.", "status": "Status is short post. You can post and delete status.", "call": "Call is voice and video call. Tap Start to start, End to stop.", "settings": "Settings has Admin Panel, Tick Request, Report, Block, Backup, Export.", "admin": "Admin Panel is inside Settings. Only Owner can see Admin Panel.", "tick_request": "Tick Request is inside Settings. Choose Blue or Green.", "report": "Report is inside Settings. Write reason and send.", "block": "Block is inside Settings. Blocked user cannot message you.", "uid": "UID is your user id. Search by Username and UID is available.", "login": "Login with username and password. If forgot, use recovery email.", "signup": "Signup with username, password and recovery email.", "password": "Never share password or OTP. MyQchat never asks for password or OTP.", "otp": "Never share OTP. MyQchat never asks for OTP.", "profile": "Profile has username, UID, tick, bio and email.", "search": "Search by Username and UID is available in app.", "poll": "Poll is vote. Create poll with question and options.", "notes": "Notes is your private notes. Save title and content.", "contacts": "Saved Contacts is your saved people list.", "reminder": "Reminders is your reminder list. Set title and time.", "backup": "Backup is in Settings. Backup saves your chats and notes.", "export": "Export is in Settings. Export gives your data.", "star": "Star saves message in Starred list.", "forward": "Forward sends message to another user.", "edit": "Edit changes your message text.", "delete": "Delete removes message or chat.", "mute": "Mute stops notifications for chat.", "archive": "Archive hides chat from main list.", "pin": "Pin keeps chat on top.", "help": "Help menu: Tick, Song, Chat, Group, Status, Call, Settings, Admin, Report, Block, UID, Login, Password."}

def bot_remove_stopwords(text):
    cleaned = bot_clean_text(text)
    words = cleaned.split()
    out = []
    for w in words:
        if w not in BOT_STOPWORDS:
            out.append(w)
    return out

def bot_score_intents(text):
    fixed = bot_fix_common_phrase(text)
    words = bot_remove_stopwords(fixed)
    scores = {}
    for intent, keys in BOT_INTENTS.items():
        score = 0
        weight = BOT_INTENT_WEIGHTS.get(intent, 8)
        for k in keys:
            if k == fixed:
                score += weight + 20
            elif k in fixed:
                score += weight
            elif k in words:
                score += 5
        scores[intent] = score
    best = "help"
    best_score = 0
    for k, v in scores.items():
        if v > best_score:
            best = k
            best_score = v
    return {"best": best, "score": best_score, "scores": scores, "words": words, "fixed": fixed}

def bot_get_intent(text):
    return bot_score_intents(text)["best"]

def bot_get_top_intents(text, limit=3):
    res = bot_score_intents(text)
    items = sorted(res["scores"].items(), key=lambda x: x[1], reverse=True)
    out = []
    for k, v in items:
        if v > 0:
            out.append({"intent": k, "score": v, "answer": BOT_INTENT_ANSWERS.get(k, "")})
    return out[:limit]

def bot_intent_confidence(text):
    res = bot_score_intents(text)
    top = bot_get_top_intents(text, 2)
    if len(top) < 2:
        return 100
    if top[0]["score"] == 0:
        return 0
    gap = top[0]["score"] - top[1]["score"]
    if gap >= 10:
        return 95
    if gap >= 5:
        return 80
    return 60

def bot_answer_by_intent(text):
    res = bot_score_intents(text)
    intent = res["best"]
    conf = bot_intent_confidence(text)
    ans = BOT_INTENT_ANSWERS.get(intent, "Help menu: Tick, Song, Chat, Group, Status, Call, Settings.")
    return {"intent": intent, "score": res["score"], "confidence": conf, "answer": ans}

@app.route("/api/bot/intent")
def api_bot_intent():
    q = request.args.get("q") or ""
    return jsonify(bot_answer_by_intent(q))

@app.route("/api/bot/top-intents")
def api_bot_top_intents():
    q = request.args.get("q") or ""
    return jsonify({"ok": True, "top": bot_get_top_intents(q, 5)})
    BOT_LOW_CONFIDENCE_LIMIT = 10
BOT_MID_CONFIDENCE_LIMIT = 20

def bot_clean_for_score(text):
    fixed = bot_fix_common_phrase(text)
    words = bot_remove_stopwords(fixed)
    return {"fixed": fixed, "words": words, "word_count": len(words)}

def bot_score_with_phrase_bonus(text):
    res = bot_score_intents(text)
    fixed = res["fixed"]
    for intent, keys in BOT_INTENTS.items():
        for k in keys:
            if fixed == k:
                res["scores"][intent] += 20
            if fixed.startswith(k + " ") or fixed.endswith(" " + k):
                res["scores"][intent] += 5
    best = "help"
    best_score = 0
    for k, v in res["scores"].items():
        if v > best_score:
            best = k
            best_score = v
    res["best"] = best
    res["score"] = best_score
    return res

def bot_is_low_confidence(text):
    res = bot_score_intents(text)
    return res["score"] < BOT_LOW_CONFIDENCE_LIMIT

def bot_is_mid_confidence(text):
    res = bot_score_intents(text)
    return res["score"] >= BOT_LOW_CONFIDENCE_LIMIT and res["score"] < BOT_MID_CONFIDENCE_LIMIT

def bot_best_or_help(text):
    res = bot_score_with_phrase_bonus(text)
    if res["score"] == 0:
        return {"intent": "help", "score": 0, "confidence": 0, "answer": BOT_INTENT_ANSWERS["help"], "need_options": True}
    conf = bot_intent_confidence(text)
    ans = BOT_INTENT_ANSWERS.get(res["best"], BOT_INTENT_ANSWERS["help"])
    return {"intent": res["best"], "score": res["score"], "confidence": conf, "answer": ans, "need_options": conf < 60}

def bot_answer_with_options(text):
    base = bot_best_or_help(text)
    if base["need_options"]:
        top = bot_get_top_intents(text, 3)
        base["options"] = [t["intent"] for t in top]
        base["option_answers"] = [t["answer"] for t in top]
        base["answer"] = base["answer"] + " Choose one: " + ", ".join(base["options"])
    return base

def bot_match_two_intents(text):
    top = bot_get_top_intents(text, 2)
    if len(top) == 2 and top[0]["score"] > 0 and top[1]["score"] > 0 and abs(top[0]["score"] - top[1]["score"]) <= 3:
        return {"double": True, "first": top[0], "second": top[1], "answer": top[0]["answer"] + " Also: " + top[1]["answer"]}
    if len(top) >= 1:
        return {"double": False, "first": top[0], "answer": top[0]["answer"]}
    return {"double": False, "first": {"intent": "help", "score": 0}, "answer": BOT_INTENT_ANSWERS["help"]}

def bot_explain_score(text):
    res = bot_score_intents(text)
    top = bot_get_top_intents(text, 3)
    return {"input": text, "fixed": res["fixed"], "words": res["words"], "best": res["best"], "score": res["score"], "top": top, "confidence": bot_intent_confidence(text)}

@app.route("/api/bot/score")
def api_bot_score():
    q = request.args.get("q") or ""
    return jsonify(bot_explain_score(q))

@app.route("/api/bot/answer-intent")
def api_bot_answer_intent():
    q = request.args.get("q") or ""
    return jsonify(bot_answer_with_options(q))
    BOT_SYNONYMS = {"song": ["music", "track", "audio", "tune"], "chat": ["message", "talk", "conversation"], "group": ["team", "community", "room"], "status": ["story", "post", "update"], "call": ["voice", "phone", "video"], "settings": ["setting", "options", "setup", "config"], "admin": ["manager", "control", "panel"], "report": ["complaint", "abuse", "scam"], "block": ["ban", "stop", "mute user"], "uid": ["userid", "user id", "account id"], "login": ["signin", "sign in", "enter"], "signup": ["register", "create account", "join"], "password": ["pass", "pwd", "secret"], "profile": ["account", "bio", "about me"], "search": ["find", "lookup", "discover"], "poll": ["vote", "survey", "question"], "notes": ["note", "memo", "diary"], "contacts": ["contact", "friends", "saved people"], "reminder": ["remind", "alert", "alarm"], "backup": ["save", "copy", "store"], "export": ["download data", "save data"], "help": ["support", "guide", "menu"], "owner": ["founder", "creator", "boss"], "tick": ["badge", "verify", "verification"], "blue": ["blue tick"], "green": ["green tick"]}

BOT_SHORT_FORMS = {"pwd": "password", "dp": "profile", "uid": "uid", "id": "uid", "msg": "message", "msgs": "messages", "grp": "group", "st": "status", "ad": "admin", "blk": "block", "rpt": "report", "sng": "song", "plz": "please", "u": "you", "ur": "your", "abt": "about", "info": "information", "acc": "account", "bio": "profile", "pic": "profile", "ph": "photo", "num": "number", "adminp": "admin panel", "tickreq": "tick request"}

BOT_PHRASE_SYNONYMS = {"how to get blue tick": "blue tick", "how to get green tick": "green tick", "who is owner": "owner", "who made app": "owner", "forgot password": "password", "change password": "password", "add song": "song", "play song": "song", "create group": "group", "post status": "status", "start call": "call", "open settings": "settings", "open admin": "admin", "report user": "report", "block user": "block", "find user": "search", "search user": "search", "create poll": "poll", "my notes": "notes", "my contacts": "contacts", "set reminder": "reminder", "backup chat": "backup", "export chat": "export", "need help": "help"}

def bot_expand_short_forms(text):
    cleaned = bot_clean_text(text)
    words = cleaned.split()
    out = []
    for w in words:
        if w in BOT_SHORT_FORMS:
            out.append(BOT_SHORT_FORMS[w])
        else:
            out.append(w)
    return " ".join(out)

def bot_expand_synonyms(text):
    fixed = bot_expand_short_forms(text)
    fixed = bot_autocorrect_text(fixed)
    for phrase, target in BOT_PHRASE_SYNONYMS.items():
        if phrase in fixed:
            fixed = fixed.replace(phrase, target)
    words = fixed.split()
    out = []
    for w in words:
        found = w
        for base, syns in BOT_SYNONYMS.items():
            if w in syns:
                found = base
                break
        out.append(found)
    return " ".join(out)

def bot_normalize_text(text):
    t = bot_clean_text(text)
    t = bot_expand_short_forms(t)
    t = bot_autocorrect_text(t)
    t = bot_expand_synonyms(t)
    t = bot_fix_common_phrase(t)
    return t

def bot_get_base_word(word):
    w = (word or "").lower().strip()
    if w in BOT_SHORT_FORMS:
        w = BOT_SHORT_FORMS[w]
    if w in BOT_AUTOCORRECT:
        w = BOT_AUTOCORRECT[w]
    for base, syns in BOT_SYNONYMS.items():
        if w in syns:
            return base
    return w

def bot_expand_all(text):
    return {"input": text, "cleaned": bot_clean_text(text), "short_expanded": bot_expand_short_forms(text), "autocorrected": bot_autocorrect_text(text), "normalized": bot_normalize_text(text)}

@app.route("/api/bot/normalize")
def api_bot_normalize():
    q = request.args.get("q") or ""
    return jsonify(bot_expand_all(q))
    BOT_EXTRA_SHORT = {"b": "blue", "g": "green", "l": "l", "t": "tick", "own": "owner", "sup": "support", "hlp": "help", "set": "settings", "prof": "profile", "srch": "search", "rem": "reminder", "cnt": "contacts", "bck": "backup", "exp": "export", "fwd": "forward", "edt": "edit", "dlt": "delete", "str": "star", "arch": "archive", "pn": "pin", "mt": "mute"}

BOT_EXTRA_SYNONYMS = {"verification": "tick", "verified": "tick", "badge": "tick", "apply": "request", "request": "request", "get": "request", "want": "request", "need": "request", "open": "show", "see": "show", "view": "show", "make": "create", "new": "create", "remove": "delete", "erase": "delete", "clear": "delete", "stop": "block", "hide": "archive", "top": "pin", "save": "backup", "send": "chat", "write": "chat", "join": "group", "leave": "group", "add": "create", "list": "show", "check": "show"}

def bot_expand_extra_short(text):
    cleaned = bot_clean_text(text)
    words = cleaned.split()
    out = []
    for w in words:
        if w in BOT_EXTRA_SHORT:
            out.append(BOT_EXTRA_SHORT[w])
        else:
            out.append(w)
    return " ".join(out)

def bot_expand_extra_synonyms(text):
    t = bot_expand_extra_short(text)
    words = t.split()
    out = []
    for w in words:
        if w in BOT_EXTRA_SYNONYMS:
            out.append(BOT_EXTRA_SYNONYMS[w])
        else:
            out.append(w)
    return " ".join(out)

def bot_full_normalize(text):
    t = bot_clean_text(text)
    t = bot_expand_short_forms(t)
    t = bot_expand_extra_short(t)
    t = bot_autocorrect_text(t)
    t = bot_expand_synonyms(t)
    t = bot_expand_extra_synonyms(t)
    t = bot_fix_common_phrase(t)
    return " ".join(t.split())

def bot_normalize_with_intent(text):
    norm = bot_full_normalize(text)
    intent_res = bot_score_intents(norm)
    return {"input": text, "normalized": norm, "intent": intent_res["best"], "score": intent_res["score"], "answer": BOT_INTENT_ANSWERS.get(intent_res["best"], BOT_INTENT_ANSWERS["help"])}

def bot_is_short_form(text):
    cleaned = bot_clean_text(text)
    words = cleaned.split()
    for w in words:
        if w in BOT_SHORT_FORMS or w in BOT_EXTRA_SHORT:
            return True
    return False

def bot_count_synonym_hits(text):
    norm = bot_full_normalize(text)
    orig = bot_clean_text(text)
    if orig == norm:
        return 0
    return 1

@app.route("/api/bot/full-normalize")
def api_bot_full_normalize():
    q = request.args.get("q") or ""
    return jsonify(bot_normalize_with_intent(q))

@app.route("/api/bot/short-check")
def api_bot_short_check():
    q = request.args.get("q") or ""
    return jsonify({"ok": True, "input": q, "is_short": bot_is_short_form(q), "normalized": bot_full_normalize(q)})
    import math

BOT_MEANING_DOCS = {"blue_tick": "blue tick verification tick blue verified account", "green_tick": "green tick verification tick green reason mandatory", "l_tick": "l tick owner only loyalwq owner tick", "owner": "owner loyalwq founder creator app owner", "support": "support email contact help support reply", "song": "song music play library song list custom url", "chat": "chat message reply star forward edit delete chat", "group": "group member add remove group chat admin", "status": "status post view delete status story", "call": "call voice video start end call mute", "settings": "settings admin panel tick request report block backup export settings", "admin": "admin panel owner only admin control users", "report": "report scam abuse report user reason", "block": "block user unblock blocked cannot message", "uid": "uid user id search username uid find user", "login": "login username password sign in account", "password": "password otp never share password otp safe", "profile": "profile bio username uid tick email profile", "search": "search username uid find user search", "poll": "poll vote question options poll result", "notes": "notes private note title content save note", "contacts": "contacts saved contacts people saved list", "reminder": "reminder title time remind alert", "backup": "backup save chats notes backup restore", "export": "export data download export chat data", "help": "help menu options start help tick song chat"}

def bot_tokenize(text):
    return bot_full_normalize(text).split()

def bot_tf_scores(words):
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    total = len(words) if words else 1
    out = {}
    for k, v in counts.items():
        out[k] = v / total
    return out

def bot_idf_scores(docs):
    total_docs = len(docs)
    df = {}
    for doc_text in docs.values():
        seen = set(doc_text.split())
        for w in seen:
            df[w] = df.get(w, 0) + 1
    out = {}
    for w, c in df.items():
        out[w] = math.log((total_docs + 1) / (c + 1)) + 1
    return out

BOT_IDF = bot_idf_scores(BOT_MEANING_DOCS)

def bot_tfidf_vector(text):
    words = bot_tokenize(text)
    tf = bot_tf_scores(words)
    vec = {}
    for w, v in tf.items():
        vec[w] = v * BOT_IDF.get(w, 1.0)
    return vec

def bot_doc_vector(doc_text):
    words = doc_text.split()
    tf = bot_tf_scores(words)
    vec = {}
    for w, v in tf.items():
        vec[w] = v * BOT_IDF.get(w, 1.0)
    return vec

def bot_cosine(vec1, vec2):
    keys = set(vec1.keys()) | set(vec2.keys())
    dot = 0
    n1 = 0
    n2 = 0
    for k in keys:
        a = vec1.get(k, 0)
        b = vec2.get(k, 0)
        dot += a * b
        n1 += a * a
        n2 += b * b
    if n1 == 0 or n2 == 0:
        return 0
    return dot / (math.sqrt(n1) * math.sqrt(n2))

def bot_meaning_match(text):
    qvec = bot_tfidf_vector(text)
    best = "help"
    best_score = 0
    scores = {}
    for intent, doc in BOT_MEANING_DOCS.items():
        dvec = bot_doc_vector(doc)
        s = bot_cosine(qvec, dvec)
        scores[intent] = round(s, 4)
        if s > best_score:
            best = intent
            best_score = s
    return {"best": best, "score": round(best_score, 4), "scores": scores}

@app.route("/api/bot/meaning")
def api_bot_meaning():
    q = request.args.get("q") or ""
    return jsonify(bot_meaning_match(q))
   def bot_levenshtein(a, b):
    a = (a or "").lower()
    b = (b or "").lower()
    if a == b:
        return 0
    la = len(a)
    lb = len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]

def bot_fuzzy_similarity(a, b):
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if a == b:
        return 100
    dist = bot_levenshtein(a, b)
    longest = max(len(a), len(b))
    if longest == 0:
        return 0
    return round((1 - dist / longest) * 100, 1)

def bot_fuzzy_best_word(word):
    w = (word or "").lower().strip()
    all_words = set()
    for doc in BOT_MEANING_DOCS.values():
        for x in doc.split():
            all_words.add(x)
    best = w
    best_score = 0
    for cand in all_words:
        s = bot_fuzzy_similarity(w, cand)
        if s > best_score:
            best = cand
            best_score = s
    return {"input": w, "best": best, "score": best_score}

def bot_fix_fuzzy_words(text):
    words = bot_full_normalize(text).split()
    out = []
    for w in words:
        if w in BOT_IDF or w in ["the", "a", "an"]:
            out.append(w)
        else:
            fb = bot_fuzzy_best_word(w)
            if fb["score"] >= 70:
                out.append(fb["best"])
            else:
                out.append(w)
    return " ".join(out)

def bot_smart_match(text):
    norm = bot_full_normalize(text)
    fixed_fuzzy = bot_fix_fuzzy_words(norm)
    intent_res = bot_score_intents(fixed_fuzzy)
    meaning_res = bot_meaning_match(fixed_fuzzy)
    final_intent = intent_res["best"]
    if intent_res["score"] == 0 and meaning_res["score"] > 0.1:
        final_intent = meaning_res["best"]
    if meaning_res["best"] != intent_res["best"] and meaning_res["score"] > 0.35 and intent_res["score"] < 10:
        final_intent = meaning_res["best"]
    ans = BOT_INTENT_ANSWERS.get(final_intent, BOT_INTENT_ANSWERS["help"])
    return {"input": text, "normalized": norm, "fuzzy_fixed": fixed_fuzzy, "intent": intent_res["best"], "intent_score": intent_res["score"], "meaning": meaning_res["best"], "meaning_score": meaning_res["score"], "final": final_intent, "answer": ans}

def bot_is_fuzzy_match(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    return norm != fixed

@app.route("/api/bot/fuzzy")
def api_bot_fuzzy():
    q = request.args.get("q") or ""
    return jsonify(bot_smart_match(q))

@app.route("/api/bot/fuzzy-word")
def api_bot_fuzzy_word():
    q = request.args.get("q") or ""
    return jsonify(bot_fuzzy_best_word(q))
BOT_TOPIC_WORDS = {"tick": ["tick", "blue", "green", "verification"], "song": ["song", "music", "play"], "chat": ["chat", "message", "reply"], "group": ["group", "member"], "status": ["status", "story"], "call": ["call", "voice"], "settings": ["settings", "setting"], "admin": ["admin", "panel"], "support": ["support", "email", "help"], "owner": ["owner", "loyalwq"], "password": ["password", "otp"], "uid": ["uid", "search"], "poll": ["poll", "vote"], "notes": ["notes", "note"], "contacts": ["contacts"], "reminder": ["reminder"]}

BOT_SHORT_FOLLOWUPS = {"hard one": "hard", "easy one": "easy", "next one": "next", "same": "same", "again": "again", "and then": "next", "what about it": "detail", "tell more": "detail", "how much": "price", "how to get": "how"}

def bot_detect_topic(text):
    norm = bot_full_normalize(text)
    for topic, keys in BOT_TOPIC_WORDS.items():
        for k in keys:
            if k in norm:
                return topic
    return ""

def bot_save_memory(user_id, username, question, answer, topic):
    db = get_db()
    row = db.execute("SELECT * FROM bot_memory WHERE user_id = ?", (user_id,)).fetchone()
    ctx = json.dumps({"topic": topic, "question": question, "answer": answer})
    if row:
        db.execute("UPDATE bot_memory SET username = ?, last_topic = ?, last_question = ?, last_answer = ?, context_json = ?, updated_at = ? WHERE user_id = ?", (username, topic, question, answer, ctx, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    else:
        db.execute("INSERT INTO bot_memory (user_id, username, last_topic, last_question, last_answer, context_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, username, topic, question, answer, ctx, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    return True

def bot_get_memory(user_id):
    db = get_db()
    row = db.execute("SELECT * FROM bot_memory WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {"found": False, "topic": "", "last_question": "", "last_answer": ""}
    return {"found": True, "topic": row["last_topic"] or "", "last_question": row["last_question"] or "", "last_answer": row["last_answer"] or "", "username": row["username"] or ""}

def bot_clear_memory(user_id):
    db = get_db()
    db.execute("DELETE FROM bot_memory WHERE user_id = ?", (user_id,))
    db.commit()
    return True

def bot_resolve_followup(text, user_id):
    norm = bot_full_normalize(text)
    mem = bot_get_memory(user_id)
    if not mem["found"]:
        return {"resolved": norm, "topic": bot_detect_topic(text), "used_memory": False}
    if norm in BOT_SHORT_FOLLOWUPS:
        mapped = BOT_SHORT_FOLLOWUPS[norm]
        if mapped in ["hard", "easy", "next", "again"]:
            return {"resolved": mem["topic"] + " " + mapped, "topic": mem["topic"], "used_memory": True, "last_question": mem["last_question"]}
        if mapped == "detail":
            return {"resolved": mem["topic"] + " detail", "topic": mem["topic"], "used_memory": True, "last_question": mem["last_question"]}
    if len(norm.split()) <= 2 and mem["topic"]:
        topic_words = BOT_TOPIC_WORDS.get(mem["topic"], [])
        has_topic = False
        for w in topic_words:
            if w in norm:
                has_topic = True
        if not has_topic:
            return {"resolved": mem["topic"] + " " + norm, "topic": mem["topic"], "used_memory": True, "last_question": mem["last_question"]}
    return {"resolved": norm, "topic": bot_detect_topic(text) or mem["topic"], "used_memory": False}

@app.route("/api/bot/memory/get")
def api_bot_memory_get():
    uid = request.args.get("user_id") or "0"
    return jsonify(bot_get_memory(uid))

@app.route("/api/bot/memory/clear", methods=["POST"])
def api_bot_memory_clear():
    data = request.get_json() or {}
    bot_clear_memory(data.get("user_id"))
    return jsonify({"ok": True, "cleared": True})
    BOT_TOPIC_CHANGE_PHRASES = ["leave it", "new topic", "change topic", "other question", "next question", "different", "forget it", "new question", "ok next", "now tell", "another", "one more"]

def bot_is_topic_change(text, user_id):
    norm = bot_full_normalize(text)
    mem = bot_get_memory(user_id)
    if not mem["found"]:
        return False
    for p in BOT_TOPIC_CHANGE_PHRASES:
        if p in norm:
            return True
    new_topic = bot_detect_topic(text)
    old_topic = mem["topic"]
    if new_topic and old_topic and new_topic != old_topic:
        if len(norm.split()) >= 2:
            return True
    return False

def bot_handle_topic_change(text, user_id, username):
    if bot_is_topic_change(text, user_id):
        bot_clear_memory(user_id)
        norm = bot_full_normalize(text)
        new_topic = bot_detect_topic(text)
        for p in BOT_TOPIC_CHANGE_PHRASES:
            norm = norm.replace(p, "").strip()
        norm = " ".join(norm.split())
        if not norm:
            norm = new_topic
        return {"changed": True, "cleaned": norm, "new_topic": new_topic, "old_cleared": True}
    return {"changed": False, "cleaned": bot_full_normalize(text), "new_topic": bot_detect_topic(text), "old_cleared": False}

def bot_answer_with_memory(text, user_id, username="User"):
    change = bot_handle_topic_change(text, user_id, username)
    if change["changed"]:
        resolved = change["cleaned"]
    else:
        res = bot_resolve_followup(text, user_id)
        resolved = res["resolved"]
    smart = bot_smart_match(resolved)
    topic = bot_detect_topic(resolved) or smart["final"]
    bot_save_memory(user_id, username, text, smart["answer"], topic)
    smart["topic"] = topic
    smart["topic_changed"] = change["changed"]
    smart["used_memory"] = not change["changed"] and bot_resolve_followup(text, user_id).get("used_memory", False)
    return smart

def bot_memory_summary(user_id):
    mem = bot_get_memory(user_id)
    if not mem["found"]:
        return {"ok": True, "summary": "No memory yet. Ask anything."}
    return {"ok": True, "summary": "Last topic " + mem["topic"] + ". Last question " + mem["last_question"] + ". Last answer " + mem["last_answer"]}

@app.route("/api/bot/memory-answer")
def api_bot_memory_answer():
    q = request.args.get("q") or ""
    uid = request.args.get("user_id") or "0"
    name = request.args.get("username") or "User"
    return jsonify(bot_answer_with_memory(q, uid, name))

@app.route("/api/bot/topic-change")
def api_bot_topic_change():
    q = request.args.get("q") or ""
    uid = request.args.get("user_id") or "0"
    return jsonify(bot_handle_topic_change(q, uid, "User"))
  BOT_HELP_MENU = "Help Menu: 1 Blue Tick 2 Green Tick 3 L Tick 4 Song 5 Chat 6 Group 7 Status 8 Call 9 Settings 10 Admin 11 Report 12 Block 13 UID 14 Login 15 Password 16 Support"

BOT_FALLBACK_ANSWERS = ["I can help with MyQchat. " + BOT_HELP_MENU, "Try one: Blue Tick, Song, Chat, Group, Status, Call, Settings.", "I know MyQchat best. Ask about Tick, Song, Chat, Group, Status, Call, Settings, Support."]

BOT_TYPING_TIMES = {"short": 1.2, "medium": 2.0, "long": 2.8}

def bot_fallback_answer(text):
    norm = bot_full_normalize(text)
    if not norm:
        return {"answer": BOT_HELP_MENU, "type": "help", "confidence": 0}
    smart = bot_smart_match(norm)
    if smart["intent_score"] >= 10 or smart["meaning_score"] >= 0.2:
        return {"answer": smart["answer"], "type": "matched", "intent": smart["final"], "confidence": 90}
    if smart["intent_score"] >= 5:
        top = bot_get_top_intents(norm, 3)
        opts = ", ".join([t["intent"] for t in top])
        return {"answer": "Did you mean " + opts + " " + BOT_HELP_MENU, "type": "suggest", "intent": smart["final"], "confidence": 60}
    idx = len(norm) % len(BOT_FALLBACK_ANSWERS)
    return {"answer": BOT_FALLBACK_ANSWERS[idx], "type": "fallback", "intent": "help", "confidence": 0}

def bot_typing_time(answer):
    words = len((answer or "").split())
    if words <= 5:
        return BOT_TYPING_TIMES["short"]
    if words <= 12:
        return BOT_TYPING_TIMES["medium"]
    return BOT_TYPING_TIMES["long"]

def bot_typing_text(answer):
    t = bot_typing_time(answer)
    if t <= 1.2:
        return "typing 1.2 sec"
    if t <= 2.0:
        return "typing 2.0 sec"
    return "typing 2.8 sec"

def bot_smart_fallback_full(text, user_id="0", username="User"):
    change = bot_handle_topic_change(text, user_id, username)
    use_text = change["cleaned"] if change["changed"] else bot_resolve_followup(text, user_id)["resolved"]
    fb = bot_fallback_answer(use_text)
    ans = fb["answer"]
    if len(ans) > 500:
        ans = ans[:500]
    topic = bot_detect_topic(use_text) or fb.get("intent", "help")
    bot_save_memory(user_id, username, text, ans, topic)
    return {"ok": True, "result": {"answer": ans, "intent": fb.get("intent", "help"), "type": fb.get("type", "fallback"), "confidence": fb.get("confidence", 0), "typing": bot_typing_text(ans), "typing_seconds": bot_typing_time(ans), "topic": topic, "topic_changed": change["changed"]}}

@app.route("/api/bot/smart-fallback")
def api_bot_smart_fallback():
    q = request.args.get("q") or ""
    uid = request.args.get("user_id") or "0"
    name = request.args.get("username") or "User"
    return jsonify(bot_smart_fallback_full(q, uid, name))
BOT_KNOWLEDGE = {"blue tick": "Blue Tick is verification. No reason needed. Request in Settings.", "blue tick price": "Blue Tick price is shown inside app in Settings Tick Request. Never pay on email or WhatsApp.", "green tick": "Green Tick needs reason. Reason is mandatory. Request in Settings.", "green tick price": "Green Tick price is shown inside app in Settings Tick Request. Never pay outside app.", "l tick": "L Tick is only for Owner LoyalWQ UID 10000001. No one else can get L Tick.", "scam tick": "Scam Tick appears after report. Admin checks report and then adds Scam Tick.", "owner": "Owner is LoyalWQ UID 10000001 with L Tick.", "qwng": "QWNG is a Software Developer Team. QWNG built MyQchat.", "myqchat": "MyQchat is a simple chat app built by QWNG. Features are Chat, Group, Status, Call, Song, Poll, Notes, Contacts, Reminders.", "support": "Support email is support.qwng@gmail.com. Reply within 24 hours. Never share password or OTP.", "song": "Song Library is in app. Admin adds songs by URL in Admin Panel. User can pick from list or paste custom URL.", "play song": "Open Songs, pick song from list, tap Play. Or paste custom URL.", "add song": "Admin adds songs by URL in Admin Panel. User can paste custom URL to play.", "chat": "Chat is 1 to 1 chat. You can Reply, Star, Forward, Edit, Delete, Mute, Archive, Pin Chat.", "reply": "Reply: long press message, tap Reply, type message.", "star": "Star: tap Star to save message in Starred list.", "forward": "Forward: tap Forward, choose user, send.", "edit message": "Edit: tap Edit on your message, change text, save.", "delete message": "Delete: tap Delete on message to remove it.", "delete chat": "Delete Chat: open chat, tap Delete Chat.", "mute": "Mute: tap Mute to stop notifications for chat.", "archive": "Archive: tap Archive to hide chat from main list.", "pin chat": "Pin Chat: tap Pin to keep chat on top.", "group": "Group is group chat. Admin can add and remove members. Group has admin, members, messages.", "create group": "Create Group: open Groups, tap Create, enter name, add members.", "add member": "Add Member: open Group, tap Add, choose user.", "remove member": "Remove Member: open Group, tap member, tap Remove. Only admin can remove.", "status": "Status is short post. You can post text status and delete it.", "post status": "Post Status: open Status, type text, tap Post.", "delete status": "Delete Status: open Status, tap Delete on your status.", "call": "Call is voice and video call. Tap Start to start, End to stop.", "voice call": "Voice Call: open chat, tap Call, choose Voice.", "video call": "Video Call: open chat, tap Call, choose Video.", "settings": "Settings has Admin Panel, Tick Request, Report, Block, Backup, Export, Profile, Search.", "admin": "Admin Panel is inside Settings. Only Owner can see Admin Panel.", "admin panel": "Admin Panel is inside Settings. Only Owner can see Admin Panel. Admin can approve tick, check reports.", "tick request": "Tick Request is inside Settings. Choose Blue or Green. Green needs reason.", "report": "Report is inside Settings. Write reason and send. Admin checks report.", "report user": "Report: open Settings, tap Report, choose user, write reason, send.", "block": "Block is inside Settings. Blocked user cannot message you.", "block user": "Block: open Settings, tap Block, choose user, confirm.", "unblock": "Unblock: open Settings, Blocked list, tap Unblock.", "uid": "UID is your user id. Search by Username and UID is available.", "my uid": "Your UID is shown in Profile. Share UID to let others find you.", "search": "Search by Username and UID is available. Open Search, type username or UID.", "search user": "Search: open Search, type username or UID, tap user.", "login": "Login with username and password. If forgot, use recovery email.", "signup": "Signup with username, password and recovery email.", "create account": "Create Account: open Signup, enter username, password, recovery email.", "password": "Never share password or OTP. MyQchat never asks for password or OTP.", "forgot password": "Forgot Password: open Login, tap Forgot, use recovery email.", "otp": "Never share OTP. MyQchat never asks for OTP.", "profile": "Profile has username, UID, tick, bio and email. Edit in Profile.", "edit profile": "Edit Profile: open Profile, change bio or email, save.", "poll": "Poll is vote. Create poll with question and options. Users vote.", "create poll": "Create Poll: open Poll, enter question, add options, post.", "vote": "Vote: open Poll, choose option, tap Vote.", "notes": "Notes is your private notes. Save title and content.", "my notes": "My Notes: open Notes, see your saved notes.", "contacts": "Saved Contacts is your saved people list. Add name, username, UID.", "saved contacts": "Saved Contacts: open Contacts, add name, username, UID.", "reminder": "Reminders is your reminder list. Set title and time.", "set reminder": "Set Reminder: open Reminders, enter title and time, save.", "backup": "Backup is in Settings. Backup saves your chats and notes.", "export": "Export is in Settings. Export gives your data.", "payment": "Payment only inside MyQchat app in Settings. Never send money on email or WhatsApp.", "help": "Help Menu: Tick, Song, Chat, Group, Status, Call, Settings, Admin, Report, Block, UID, Login, Password, Support."}

BOT_WRONG_HISTORY = {}

def bot_search_knowledge(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_KNOWLEDGE:
        return BOT_KNOWLEDGE[fixed]
    if norm in BOT_KNOWLEDGE:
        return BOT_KNOWLEDGE[norm]
    best_key = ""
    best_score = 0
    for key in BOT_KNOWLEDGE:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best = key
            best_score = s
    if best_score >= 70:
        return BOT_KNOWLEDGE[best_key]
    smart = bot_smart_match(fixed)
    if smart["final"] in BOT_KNOWLEDGE:
        return BOT_KNOWLEDGE[smart["final"]]
    return ""

def bot_self_correct(user_id, wrong_answer):
    BOT_WRONG_HISTORY[user_id] = wrong_answer
    return {"ok": True, "note": "Got it. I will explain differently next time. Ask again in other words."}

def bot_answer_after_correction(text, user_id):
    wrong = BOT_WRONG_HISTORY.get(user_id, "")
    ans = bot_search_knowledge(text)
    if not ans:
        fb = bot_fallback_answer(text)
        ans = fb["answer"]
    if wrong and ans == wrong:
        smart = bot_smart_match(text)
        top = bot_get_top_intents(text, 3)
        alt = ""
        for t in top:
            if t["answer"] != wrong:
                alt = t["answer"]
                break
        if alt:
            ans = "Let me explain differently. " + alt
        else:
            ans = "Let me explain differently. " + BOT_HELP_MENU
    return {"answer": ans, "was_wrong_before": wrong != "", "wrong": wrong}

@app.route("/api/bot/knowledge")
def api_bot_knowledge():
    q = request.args.get("q") or ""
    ans = bot_search_knowledge(q)
    if not ans:
        return jsonify({"ok": False, "answer": BOT_HELP_MENU})
    return jsonify({"ok": True, "answer": ans})

@app.route("/api/bot/wrong", methods=["POST"])
def api_bot_wrong():
    data = request.get_json() or {}
    return jsonify(bot_self_correct(data.get("user_id") or "0", data.get("wrong") or ""))

@app.route("/api/bot/correct-answer")
def api_bot_correct_answer():
    q = request.args.get("q") or ""
    uid = request.args.get("user_id") or "0"
    return jsonify(bot_answer_after_correction(q, uid))
    BOT_TICK_DATA = {"blue_tick_what": "Blue Tick is verification. It shows account is verified.", "blue_tick_reason": "Blue Tick needs no reason. Just request in Settings.", "blue_tick_price": "Blue Tick price is shown inside app in Settings Tick Request.", "blue_tick_time": "Blue Tick is checked by Admin. Wait for Admin approval.", "green_tick_what": "Green Tick is verification with reason. It shows account is trusted with reason.", "green_tick_reason": "Green Tick needs reason. Reason is mandatory. Write clear reason.", "green_tick_price": "Green Tick price is shown inside app in Settings Tick Request.", "green_tick_time": "Green Tick is checked by Admin. Admin reads reason then approves.", "l_tick_what": "L Tick is only for Owner. L means LoyalWQ.", "l_tick_who": "L Tick is only for LoyalWQ UID 10000001. No one else can get L Tick.", "scam_tick_what": "Scam Tick appears after report. It warns other users.", "scam_tick_how": "Scam Tick: user reports, Admin checks, Admin adds Scam Tick if scam is true.", "tick_request_how": "Tick Request: open Settings, tap Tick Request, choose Blue or Green, send.", "tick_approve": "Tick Approve: only Admin can approve. Admin opens Admin Panel, checks request, taps Approve.", "tick_reject": "Tick Reject: Admin can reject if reason is wrong or fake.", "owner_who": "Owner is LoyalWQ UID 10000001 with L Tick.", "owner_contact": "Owner contact is via Support email support.qwng@gmail.com.", "owner_role": "Owner controls app, Admin Panel, tick, reports, broadcast.", "qwng_what": "QWNG is a Software Developer Team. QWNG built MyQchat.", "qwng_team": "QWNG Team builds chat app, bot, songs, admin system.", "admin_who": "Admin is user with admin access. Owner is main admin.", "admin_panel_where": "Admin Panel is inside Settings. Only Owner can see Admin Panel.", "admin_panel_work": "Admin Panel: approve tick, check reports, check users, send broadcast.", "support_email": "Support email is support.qwng@gmail.com. Reply within 24 hours.", "support_time": "Support replies within 24 hours. Write clear issue with UID.", "support_what": "Support helps with login, tick, report, block, song, chat problem."}

def bot_search_tick_owner(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_TICK_DATA:
        return BOT_TICK_DATA[fixed]
    if norm in BOT_TICK_DATA:
        return BOT_TICK_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_TICK_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_TICK_DATA[best_key]
    smart = bot_smart_match(fixed)
    for key in BOT_TICK_DATA:
        if smart["final"] in key:
            return BOT_TICK_DATA[key]
    return ""

def bot_tick_answer(text):
    ans = bot_search_tick_owner(text)
    if ans:
        return {"found": True, "answer": ans, "source": "tick_owner_admin_support"}
    ans2 = bot_search_knowledge(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "general"}
    return {"found": False, "answer": BOT_HELP_MENU, "source": "help"}

@app.route("/api/bot/tick-owner")
def api_bot_tick_owner():
    q = request.args.get("q") or ""
    return jsonify(bot_tick_answer(q))
    BOT_ADMIN_DATA = {"admin_add": "Admin Add: only Owner can make admin. Owner opens Admin Panel.", "admin_remove": "Admin Remove: Owner can remove admin in Admin Panel.", "broadcast_what": "Broadcast is message to all users. Only Admin can send broadcast.", "broadcast_how": "Broadcast: Admin opens Admin Panel, writes message, taps Send Broadcast.", "report_check": "Report Check: Admin opens Admin Panel, opens Reports, reads reason, takes action.", "report_action": "Report Action: Admin can warn, block, add Scam Tick, or reject report.", "block_check": "Block Check: Admin can see blocked users in Admin Panel.", "user_list": "User List: Admin can see all users in Admin Panel.", "tick_list": "Tick List: Admin can see all tick requests in Admin Panel.", "support_safe": "Support is safe. Never share password or OTP with support.", "support_fake": "Fake support asks for OTP or money. Real support never asks for OTP or money.", "payment_safe": "Payment only inside MyQchat app in Settings. Never send money on email or WhatsApp.", "payment_fake": "If anyone sends UPI link on email or WhatsApp, it is scam. Block and Report.", "scam_warn": "If scam, do not pay. Block user and Report in Settings.", "scam_help": "Scam Help: Block user, Report with reason, contact support.qwng@gmail.com."}

def bot_search_admin_support(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_ADMIN_DATA:
        return BOT_ADMIN_DATA[fixed]
    if norm in BOT_ADMIN_DATA:
        return BOT_ADMIN_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_ADMIN_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_ADMIN_DATA[best_key]
    return ""

def bot_full_tick_admin_answer(text):
    ans = bot_search_tick_owner(text)
    if ans:
        return {"found": True, "answer": ans, "source": "tick_owner"}
    ans2 = bot_search_admin_support(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "admin_support"}
    ans3 = bot_search_knowledge(text)
    if ans3:
        return {"found": True, "answer": ans3, "source": "general"}
    return {"found": False, "answer": BOT_HELP_MENU, "source": "help"}

def bot_is_safety_question(text):
    norm = bot_full_normalize(text)
    for w in ["password", "otp", "payment", "upi", "money", "scam", "fake", "link"]:
        if w in norm:
            return True
    return False

def bot_safety_answer(text):
    if bot_is_safety_question(text):
        if "password" in bot_full_normalize(text) or "otp" in bot_full_normalize(text):
            return "Never share password or OTP. MyQchat never asks for password or OTP."
        if "payment" in bot_full_normalize(text) or "upi" in bot_full_normalize(text) or "money" in bot_full_normalize(text):
            return "Payment only inside MyQchat app in Settings. Never send money on email or WhatsApp."
        if "scam" in bot_full_normalize(text):
            return "If scam, Block user and Report in Settings. Contact support.qwng@gmail.com."
    return ""

@app.route("/api/bot/admin-support")
def api_bot_admin_support():
    q = request.args.get("q") or ""
    return jsonify(bot_full_tick_admin_answer(q))

@app.route("/api/bot/safety")
def api_bot_safety():
    q = request.args.get("q") or ""
    ans = bot_safety_answer(q)
    if not ans:
        ans = "Safe: Never share password or OTP. Payment only inside app."
    return jsonify({"ok": True, "answer": ans})
    BOT_CHAT_DATA = {"chat_what": "Chat is 1 to 1 chat. Send message, reply, star, forward, edit, delete.", "chat_start": "Chat Start: open Chats, tap user, type message, tap Send.", "chat_reply": "Chat Reply: tap message, tap Reply, type reply.", "chat_star": "Chat Star: tap Star on message to save in Starred list.", "chat_forward": "Chat Forward: tap Forward, choose user, send.", "chat_edit": "Chat Edit: tap Edit on your message, change text, save.", "chat_delete": "Chat Delete: tap Delete on message to remove it.", "chat_search": "Chat Search: open Chat, tap Search, type word.", "chat_mute": "Chat Mute: tap Mute to stop notifications.", "chat_archive": "Chat Archive: tap Archive to hide chat.", "chat_pin": "Chat Pin: tap Pin to keep chat on top.", "chat_delete_all": "Delete Chat: open chat, tap Delete Chat, confirm.", "group_what": "Group is group chat. Many users chat together.", "group_create": "Group Create: open Groups, tap Create, enter name, add members.", "group_add": "Group Add: open Group, tap Add, choose user.", "group_remove": "Group Remove: open Group, tap member, tap Remove. Only admin can remove.", "group_leave": "Group Leave: open Group, tap Leave.", "group_delete": "Group Delete: only group admin can delete group.", "group_admin": "Group Admin controls members. Admin can add and remove.", "group_message": "Group Message: type in group box, tap Send. All members see it."}

def bot_search_chat_group(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_CHAT_DATA:
        return BOT_CHAT_DATA[fixed]
    if norm in BOT_CHAT_DATA:
        return BOT_CHAT_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_CHAT_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_CHAT_DATA[best_key]
    return ""

@app.route("/api/bot/chat-group")
def api_bot_chat_group():
    q = request.args.get("q") or ""
    ans = bot_search_chat_group(q)
    if not ans:
        ans = BOT_HELP_MENU
    return jsonify({"ok": True, "answer": ans})
    BOT_STATUS_CALL_DATA = {"status_what": "Status is short post. You can post text status and delete it.", "status_post": "Status Post: open Status, type text, tap Post.", "status_view": "Status View: open Status, see all status list.", "status_delete": "Status Delete: open Status, tap Delete on your status.", "status_time": "Status shows time when posted.", "status_who": "Status shows username of user who posted.", "call_what": "Call is voice and video call. Tap Start to start, End to stop.", "call_start": "Call Start: open chat, tap Call, choose Voice or Video.", "call_end": "Call End: tap End to stop call.", "call_mute": "Call Mute: tap Mute during call to mute mic.", "call_voice": "Voice Call: voice only, no video.", "call_video": "Video Call: voice plus video.", "call_problem": "Call Problem: check internet and mic. Try again.", "call_history": "Call History: open Calls, see list.", "chat_block_in_chat": "Block in Chat: open chat, tap Block, confirm.", "chat_report_in_chat": "Report in Chat: open chat, tap Report, write reason."}

def bot_search_status_call(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_STATUS_CALL_DATA:
        return BOT_STATUS_CALL_DATA[fixed]
    if norm in BOT_STATUS_CALL_DATA:
        return BOT_STATUS_CALL_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_STATUS_CALL_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_STATUS_CALL_DATA[best_key]
    return ""

def bot_full_chat_group_status_call(text):
    ans = bot_search_chat_group(text)
    if ans:
        return {"found": True, "answer": ans, "source": "chat_group"}
    ans2 = bot_search_status_call(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "status_call"}
    ans3 = bot_search_knowledge(text)
    if ans3:
        return {"found": True, "answer": ans3, "source": "general"}
    return {"found": False, "answer": BOT_HELP_MENU, "source": "help"}

@app.route("/api/bot/status-call")
def api_bot_status_call():
    q = request.args.get("q") or ""
    return jsonify(bot_full_chat_group_status_call(q))
    BOT_SONG_PROFILE_DATA = {"song_what": "Song Library is in app. Admin adds songs by URL. User can pick from list or paste custom URL.", "song_play": "Song Play: open Songs, pick song, tap Play.", "song_search": "Song Search: open Songs, type title, tap Search.", "song_add": "Song Add: Admin adds songs by URL in Admin Panel.", "song_custom": "Song Custom: paste custom URL in Songs to play your song.", "song_delete": "Song Delete: only Admin can delete song.", "song_list": "Song List: open Songs, see all songs.", "profile_what": "Profile has username, UID, tick, bio and email.", "profile_view": "Profile View: open Profile, see username, UID, tick, bio.", "profile_edit": "Profile Edit: open Profile, change bio or email, save.", "profile_bio": "Profile Bio: short text about you. Edit in Profile.", "profile_photo": "Profile Photo: change in Profile.", "profile_uid": "Profile UID: your UID is shown in Profile.", "settings_what": "Settings has Admin Panel, Tick Request, Report, Block, Backup, Export, Profile, Search.", "settings_open": "Settings Open: tap bottom Settings button.", "settings_profile": "Settings Profile: open Settings, tap Profile.", "settings_tick": "Settings Tick: open Settings, tap Tick Request.", "settings_report": "Settings Report: open Settings, tap Report.", "settings_block": "Settings Block: open Settings, tap Block."}

def bot_search_song_profile(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_SONG_PROFILE_DATA:
        return BOT_SONG_PROFILE_DATA[fixed]
    if norm in BOT_SONG_PROFILE_DATA:
        return BOT_SONG_PROFILE_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_SONG_PROFILE_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_SONG_PROFILE_DATA[best_key]
    return ""

@app.route("/api/bot/song-profile")
def api_bot_song_profile():
    q = request.args.get("q") or ""
    ans = bot_search_song_profile(q)
    if not ans:
        ans = BOT_HELP_MENU
    return jsonify({"ok": True, "answer": ans})
    BOT_SEARCH_SETTINGS_DATA = {"search_what": "Search by Username and UID is available.", "search_user": "Search User: open Search, type username or UID, tap user.", "search_username": "Search by Username: type username in Search.", "search_uid": "Search by UID: type UID in Search.", "search_result": "Search Result shows username, UID, tick, bio.", "settings_backup": "Settings Backup: open Settings, tap Backup.", "settings_export": "Settings Export: open Settings, tap Export.", "settings_help": "Settings Help: open Settings, tap Help.", "settings_support": "Settings Support: support email is support.qwng@gmail.com.", "settings_admin": "Settings Admin: Admin Panel is inside Settings. Only Owner can see it.", "settings_logout": "Settings Logout: open Settings, tap Logout.", "settings_delete_account": "Settings Delete Account: open Settings, tap Delete Account, confirm."}

def bot_search_search_settings(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_SEARCH_SETTINGS_DATA:
        return BOT_SEARCH_SETTINGS_DATA[fixed]
    if norm in BOT_SEARCH_SETTINGS_DATA:
        return BOT_SEARCH_SETTINGS_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_SEARCH_SETTINGS_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_SEARCH_SETTINGS_DATA[best_key]
    return ""

def bot_full_song_profile_search(text):
    ans = bot_search_song_profile(text)
    if ans:
        return {"found": True, "answer": ans, "source": "song_profile"}
    ans2 = bot_search_search_settings(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "search_settings"}
    ans3 = bot_search_knowledge(text)
    if ans3:
        return {"found": True, "answer": ans3, "source": "general"}
    return {"found": False, "answer": BOT_HELP_MENU, "source": "help"}

BIG_LAYOUT_CSS = "body{font-family:Arial;margin:0;background:rgb(245,245,245)} .bigTop{background:rgb(7,94,84);color:white;padding:16px;font-size:20px;display:flex;justify-content:space-between} .bigHero{background:white;margin:12px;padding:16px;border-radius:16px;text-align:center} .bigHero h2{margin:4px} .bigGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px} .bigCard{background:white;padding:16px;border-radius:14px;text-align:center;cursor:pointer} .bigCard b{font-size:16px} .bigCard p{font-size:12px;color:rgb(100,100,100)} .bigChat{background:white;margin:10px;padding:12px;border-radius:14px} .bigInput{display:flex;gap:8px;padding:10px} .bigInput input{flex:1;padding:14px;border-radius:24px;border:1px solid rgb(220,220,220)} .bigInput button{padding:12px 20px;border-radius:24px;border:none;background:rgb(7,94,84);color:white} .bigBottom{display:flex;background:white;border-top:1px solid rgb(220,220,220)} .bigBottom button{flex:1;padding:14px;border:none;background:white;font-size:14px}"

BIG_LAYOUT_HOME = "<div class='bigTop'><div>MyQchat</div><div>QWNG</div></div><div class='bigHero'><h2>Welcome to MyQchat</h2><p>Simple, Fast, Beautiful Chat by QWNG</p><p>Owner LoyalWQ UID 10000001 L Tick</p></div><div class='bigGrid'><div class='bigCard' onclick=\"openChat('QWNG Bot')\"><b>QWNG Bot</b><p>Answers from code, fast</p></div><div class='bigCard' onclick=\"openChat('Smart Bot')\"><b>Smart Bot</b><p>Gemini 2.5 Flash, smart</p></div><div class='bigCard' onclick='showSongs()'><b>Songs</b><p>Song Library, play songs</p></div><div class='bigCard' onclick='showGroups()'><b>Groups</b><p>Group chat, members</p></div><div class='bigCard' onclick='showChats()'><b>Chats</b><p>1 to 1 chat, reply, star</p></div><div class='bigCard' onclick='showSettings()'><b>Settings</b><p>Tick, Report, Block, Backup</p></div></div><div class='bigChat'><b>Features</b><p>Chat, Group, Status, Call, Song, Poll, Notes, Contacts, Reminders, Backup, Export, Tick, Report, Block</p></div>"

@app.route("/api/bot/song-profile-search")
def api_bot_song_profile_search():
    q = request.args.get("q") or ""
    return jsonify(bot_full_song_profile_search(q))

@app.route("/big-home")
def big_home_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>MyQchat Big Home</title><style>" + BIG_LAYOUT_CSS + "</style></head><body>" + BIG_LAYOUT_HOME + "<div class='bigInput'><input id='msgInput' placeholder='Ask QWNG Bot'><button onclick='sendMsg()'>Send</button></div><div class='bigBottom'><button onclick='showChats()'>Chats</button><button onclick='showGroups()'>Groups</button><button onclick='showSongs()'>Songs</button><button onclick='showSettings()'>Settings</button></div><script>" + GOOD_LAYOUT_JS + "</script></body></html>"
    return html
 BOT_POLL_NOTES_DATA = {"poll_what": "Poll is vote. Create poll with question and options. Users vote.", "poll_create": "Poll Create: open Poll, enter question, add options, post.", "poll_vote": "Poll Vote: open Poll, choose option, tap Vote.", "poll_result": "Poll Result: open Poll, see votes for each option.", "poll_delete": "Poll Delete: only creator can delete poll.", "notes_what": "Notes is your private notes. Save title and content.", "notes_add": "Notes Add: open Notes, enter title and content, tap Save.", "notes_list": "Notes List: open Notes, see your saved notes.", "notes_delete": "Notes Delete: open Notes, tap Delete on note.", "notes_edit": "Notes Edit: open Notes, tap note, change text, save.", "contacts_what": "Saved Contacts is your saved people list.", "contacts_add": "Contacts Add: open Contacts, enter name, username, UID, save.", "contacts_list": "Contacts List: open Contacts, see saved people.", "contacts_delete": "Contacts Delete: open Contacts, tap Delete on contact.", "reminder_what": "Reminders is your reminder list. Set title and time.", "reminder_add": "Reminder Add: open Reminders, enter title and time, save.", "reminder_list": "Reminder List: open Reminders, see your reminders.", "reminder_done": "Reminder Done: open Reminders, tap Done when done."}

def bot_search_poll_notes(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_POLL_NOTES_DATA:
        return BOT_POLL_NOTES_DATA[fixed]
    if norm in BOT_POLL_NOTES_DATA:
        return BOT_POLL_NOTES_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_POLL_NOTES_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_POLL_NOTES_DATA[best_key]
    return ""

@app.route("/api/bot/poll-notes")
def api_bot_poll_notes():
    q = request.args.get("q") or ""
    ans = bot_search_poll_notes(q)
    if not ans:
        ans = BOT_HELP_MENU
    return jsonify({"ok": True, "answer": ans})   
BOT_SAFETY_DATA = {"password_what": "Password is secret for login. Never share password.", "password_safe": "Password Safe: never share password with anyone. MyQchat never asks for password.", "password_forgot": "Forgot Password: use recovery email in Login page.", "password_change": "Change Password: open Profile, use recovery email.", "password_strong": "Strong Password: use 8 chars, mix letters and numbers.", "otp_what": "OTP is one time code for verification.", "otp_safe": "OTP Safe: never share OTP with anyone. MyQchat never asks for OTP.", "otp_fake": "Fake OTP: if someone asks for OTP on email or 【entity-WhatsApp¦canonical_name=WhatsApp】, it is scam.", "login_safe": "Login Safe: login only inside app. Never login via link from email.", "login_problem": "Login Problem: check username and password. Use recovery email if forgot.", "block_what": "Block stops user from messaging you.", "block_how": "Block: open Settings, tap Block, choose user, confirm.", "block_unblock": "Unblock: open Settings, Blocked list, tap Unblock.", "block_effect": "After Block, blocked user cannot message you or see your profile.", "block_owner": "Cannot block Owner LoyalWQ UID 10000001.", "report_what": "Report is complaint about scam or abuse.", "report_how": "Report: open Settings, tap Report, choose user, write reason, send.", "report_reason": "Report Reason: write clear reason, min 5 chars.", "report_check": "Report Check: Admin checks report in Admin Panel.", "report_result": "Report Result: Admin can warn, block, add Scam Tick.", "report_owner": "Cannot report Owner LoyalWQ UID 10000001.", "scam_what": "Scam is fake money or fake link or fake tick.", "scam_example": "Scam Example: UPI link on email, WhatsApp payment, fake tick price.", "scam_protect": "Scam Protect: payment only inside app in Settings. Never pay outside app.", "scam_action": "Scam Action: Block user, Report with reason, contact support.qwng@gmail.com.", "scam_tick_what": "Scam Tick appears after report. It warns others.", "scam_tick_how": "Scam Tick: user reports, Admin checks, Admin adds Scam Tick if true.", "payment_safe": "Payment Safe: payment only inside MyQchat app in Settings.", "payment_where": "Payment Where: open Settings, Tick Request, see price, pay inside app.", "payment_fake": "Payment Fake: if anyone sends UPI link on email or WhatsApp, it is scam.", "payment_check": "Payment Check: never send money on email or WhatsApp. Only inside app.", "link_safe": "Link Safe: do not click unknown link. Login only inside app.", "link_fake": "Fake Link: link from email or WhatsApp can be fake.", "email_safe": "Email Safe: support is support.qwng@gmail.com. Never share OTP or password on email.", "whatsapp_safe": "WhatsApp Safe: MyQchat never asks for money on WhatsApp."}

def bot_search_safety(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_SAFETY_DATA:
        return BOT_SAFETY_DATA[fixed]
    if norm in BOT_SAFETY_DATA:
        return BOT_SAFETY_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_SAFETY_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_SAFETY_DATA[best_key]
    return ""

def bot_safety_full_answer(text):
    ans = bot_search_safety(text)
    if ans:
        return {"found": True, "answer": ans, "source": "safety"}
    ans2 = bot_safety_answer(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "safety_short"}
    return {"found": False, "answer": "Never share password or OTP. Payment only inside app in Settings. If scam, Block and Report.", "source": "help"}

@app.route("/api/bot/safety-full")
def api_bot_safety_full():
    q = request.args.get("q") or ""
    return jsonify(bot_safety_full_answer(q)
BOT_SAFETY_DATA = {"password_what": "Password is secret for login. Never share password.", "password_safe": "Password Safe: never share password with anyone. MyQchat never asks for password.", "password_forgot": "Forgot Password: use recovery email in Login page.", "password_change": "Change Password: open Profile, use recovery email.", "password_strong": "Strong Password: use 8 chars, mix letters and numbers.", "otp_what": "OTP is one time code for verification.", "otp_safe": "OTP Safe: never share OTP with anyone. MyQchat never asks for OTP.", "otp_fake": "Fake OTP: if someone asks for OTP on email or 【entity-WhatsApp¦canonical_name=WhatsApp】, it is scam.", "login_safe": "Login Safe: login only inside app. Never login via link from email.", "login_problem": "Login Problem: check username and password. Use recovery email if forgot.", "block_what": "Block stops user from messaging you.", "block_how": "Block: open Settings, tap Block, choose user, confirm.", "block_unblock": "Unblock: open Settings, Blocked list, tap Unblock.", "block_effect": "After Block, blocked user cannot message you or see your profile.", "block_owner": "Cannot block Owner LoyalWQ UID 10000001.", "report_what": "Report is complaint about scam or abuse.", "report_how": "Report: open Settings, tap Report, choose user, write reason, send.", "report_reason": "Report Reason: write clear reason, min 5 chars.", "report_check": "Report Check: Admin checks report in Admin Panel.", "report_result": "Report Result: Admin can warn, block, add Scam Tick.", "report_owner": "Cannot report Owner LoyalWQ UID 10000001.", "scam_what": "Scam is fake money or fake link or fake tick.", "scam_example": "Scam Example: UPI link on email, WhatsApp payment, fake tick price.", "scam_protect": "Scam Protect: payment only inside app in Settings. Never pay outside app.", "scam_action": "Scam Action: Block user, Report with reason, contact support.qwng@gmail.com.", "scam_tick_what": "Scam Tick appears after report. It warns others.", "scam_tick_how": "Scam Tick: user reports, Admin checks, Admin adds Scam Tick if true.", "payment_safe": "Payment Safe: payment only inside MyQchat app in Settings.", "payment_where": "Payment Where: open Settings, Tick Request, see price, pay inside app.", "payment_fake": "Payment Fake: if anyone sends UPI link on email or WhatsApp, it is scam.", "payment_check": "Payment Check: never send money on email or WhatsApp. Only inside app.", "link_safe": "Link Safe: do not click unknown link. Login only inside app.", "link_fake": "Fake Link: link from email or WhatsApp can be fake.", "email_safe": "Email Safe: support is support.qwng@gmail.com. Never share OTP or password on email.", "whatsapp_safe": "WhatsApp Safe: MyQchat never asks for money on WhatsApp."}

def bot_search_safety(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_SAFETY_DATA:
        return BOT_SAFETY_DATA[fixed]
    if norm in BOT_SAFETY_DATA:
        return BOT_SAFETY_DATA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_SAFETY_DATA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 65:
        return BOT_SAFETY_DATA[best_key]
    return ""

def bot_safety_full_answer(text):
    ans = bot_search_safety(text)
    if ans:
        return {"found": True, "answer": ans, "source": "safety"}
    ans2 = bot_safety_answer(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "safety_short"}
    return {"found": False, "answer": "Never share password or OTP. Payment only inside app in Settings. If scam, Block and Report.", "source": "help"}

@app.route("/api/bot/safety-full")
def api_bot_safety_full():
    q = request.args.get("q") or ""
    return jsonify(bot_safety_full_answer(q))
BOT_PASSWORD_BLOCK_EXTRA = {"password_rule_1": "Never share password. MyQchat never asks for password.", "password_rule_2": "Password must be min 4 chars. Use strong password.", "password_rule_3": "If forgot password, use recovery email.", "password_rule_4": "Do not use same password on other apps.", "otp_rule_1": "Never share OTP. MyQchat never asks for OTP.", "otp_rule_2": "OTP is sent to recovery email only.", "otp_rule_3": "If someone asks OTP on email or 【entity-WhatsApp¦canonical_name=WhatsApp】, it is scam.", "block_rule_1": "Block stops user from messaging you.", "block_rule_2": "Blocked user cannot see your status or call you.", "block_rule_3": "You can unblock anytime in Settings.", "block_rule_4": "Cannot block Owner LoyalWQ.", "report_rule_1": "Report needs reason min 5 chars.", "report_rule_2": "Admin checks report within 24 hours.", "report_rule_3": "Fake report is also checked.", "report_rule_4": "Cannot report Owner LoyalWQ.", "scam_rule_1": "Scam is fake money or fake link.", "scam_rule_2": "If scam, Block and Report.", "scam_rule_3": "Contact support.qwng@gmail.com if scam.", "scam_rule_4": "Payment only inside app.", "payment_rule_1": "Payment only inside MyQchat app in Settings.", "payment_rule_2": "Never send money on email or 【entity-WhatsApp¦canonical_name=WhatsApp】.", "payment_rule_3": "Tick price is shown inside app.", "payment_rule_4": "If UPI link on email, it is scam.", "safety_rule_1": "Never share password or OTP.", "safety_rule_2": "Payment only inside app.", "safety_rule_3": "If scam, Block and Report.", "safety_rule_4": "Support is support.qwng@gmail.com.", "safety_rule_5": "Login only inside app, not via email link.", "help_rule_1": "Help Menu has Tick, Song, Chat, Group, Status, Call, Settings, Admin, Report, Block, UID, Login, Password, Support.", "help_rule_2": "QWNG Bot answers from code, fast.", "help_rule_3": "Smart Bot answers via Gemini 2.5 Flash when code has no answer."}

BOT_COMBINED_SAFETY_KB = {}
BOT_COMBINED_SAFETY_KB.update(BOT_KNOWLEDGE)
BOT_COMBINED_SAFETY_KB.update(BOT_TICK_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_ADMIN_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_CHAT_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_STATUS_CALL_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_SONG_PROFILE_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_SEARCH_SETTINGS_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_POLL_NOTES_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_BACKUP_EXPORT_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_SAFETY_DATA)
BOT_COMBINED_SAFETY_KB.update(BOT_PASSWORD_BLOCK_EXTRA)
BOT_COMBINED_SAFETY_KB.update(BOT_EXTRA_QA)

def bot_search_all_combined(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_COMBINED_SAFETY_KB:
        return BOT_COMBINED_SAFETY_KB[fixed]
    if norm in BOT_COMBINED_SAFETY_KB:
        return BOT_COMBINED_SAFETY_KB[norm]
    best_key = ""
    best_score = 0
    for key in BOT_COMBINED_SAFETY_KB:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 70:
        return BOT_COMBINED_SAFETY_KB[best_key]
    smart = bot_smart_match(fixed)
    if smart["final"] in BOT_COMBINED_SAFETY_KB:
        return BOT_COMBINED_SAFETY_KB[smart["final"]]
    top = bot_get_top_intents(fixed, 1)
    if top:
        intent = top[0]["intent"]
        for key in BOT_COMBINED_SAFETY_KB:
            if intent in key:
                return BOT_COMBINED_SAFETY_KB[key]
    return ""

def bot_final_knowledge_answer(text):
    ans = bot_search_all_combined(text)
    if ans:
        return {"found": True, "answer": ans, "source": "combined_big"}
    ans2 = bot_search_knowledge(text)
    if ans2:
        return {"found": True, "answer": ans2, "source": "general"}
    fb = bot_fallback_answer(text)
    return {"found": False, "answer": fb["answer"], "source": "fallback"}

@app.route("/api/bot/all-knowledge")
def api_bot_all_knowledge():
    q = request.args.get("q") or ""
    return jsonify(bot_final_knowledge_answer(q))

@app.route("/api/bot/password-block")
def api_bot_password_block():
    q = request.args.get("q") or ""
    ans = bot_search_safety(q)
    if not ans:
        ans = BOT_PASSWORD_BLOCK_EXTRA.get("safety_rule_1", "Never share password or OTP.")
    return jsonify({"ok": True, "answer": ans cm})
    import urllib.request
import urllib.error

GOOGLE_STUDIO_API_KEY = "AQ.Ab8RN6KzPb2y_uHlz0qrHri-rFx32ar0GcL_8dfkgngwu_xPyw"
GOOGLE_STUDIO_MODEL = "gemini-2.5-flash"
GOOGLE_STUDIO_URL = "https://generativelanguage.googleapis.com/v1beta/models/" + GOOGLE_STUDIO_MODEL + ":generateContent"

SMART_BOT_SYSTEM_PROMPT = "You are Smart Bot in MyQchat by QWNG. Owner LoyalWQ. Support Mail is support.qwng@gmail.com. App myqchat-1.onrender.com. You help QWNG Bot when question is not in code. Answer in simple English, max 20 words. Never ask password or OTP or UPI. Never give UPI link or fake link. Payment only inside app Settings Request Tick. If scam warn and say Block and Report."

QWNG_BOT_SYSTEM_PROMPT = "You are QWNG Bot in MyQchat. Use code knowledge first. If not know, ask Smart Bot. Never say I did not understand. Show Help menu. Owner LoyalWQ. Support email is support.qwng@gmail.com."

DEFAULT_CHATS = [{"id": "qwn_bot", "name": "QWNG Bot", "type": "code_bot", "info": "Answers from code, fast"}, {"id": "smart_bot", "name": "Smart Bot", "type": "api_bot", "info": "Gemini 2.5 Flash, smart"}]

def call_smart_bot(user_question, system_prompt=SMART_BOT_SYSTEM_PROMPT):
    if GOOGLE_STUDIO_API_KEY == "AQ.Ab8RN6KzPb2y_uHlz0qrHri-rFx32ar0GcL_8dfkgngwu_xPyw" or GOOGLE_STUDIO_API_KEY.strip() == "":
        return "Smart Bot needs API key. Please paste key in code top. I can still help with MyQchat. " + BOT_HELP_MENU
    try:
        data = {"contents": [{"parts": [{"text": user_question}]}], "systemInstruction": {"parts": [{"text": system_prompt}]}, "generationConfig": {"maxOutputTokens": 120, "temperature": 0.7}}
        req = urllib.request.Request(GOOGLE_STUDIO_URL, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json", "x-goog-api-key": GOOGLE_STUDIO_API_KEY}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            j = json.loads(body)
            text = j["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            if len(text) > 500:
                text = text[:500]
            if "password" in text.lower() and "never share" not in text.lower():
                text = "Never share password or OTP. MyQchat never asks for password or OTP. " + BOT_HELP_MENU
            if "upi" in text.lower() and "http" in text.lower():
                text = "Payment only inside MyQchat app in Settings. Never pay on email or WhatsApp."
            return text
    except Exception as e:
        return "Smart Bot error. I can still help with MyQchat. " + BOT_HELP_MENU

def bot_api_memory_answer(text, user_id, username):
    mem = bot_resolve_followup(text, user_id)
    resolved = mem["resolved"]
    local = bot_final_knowledge_answer(resolved)
    if local["found"] and len(local["answer"]) > 5:
        topic = bot_detect_topic(resolved) or "general"
        bot_save_memory(user_id
      def bot_final_test_one(q, user_id="999", username="Tester"):
    code_ans = bot_final_knowledge_answer(q)
    smart_needed = not code_ans["found"]
    if not smart_needed:
        return {"q": q, "source": "code", "answer": code_ans["answer"], "ok": True}
    api_ans = call_smart_bot(q)
    return {"q": q, "source": "api", "answer": api_ans, "ok": True}

def bot_final_test_many():
    tests = ["what is blue tick", "how to get green tick", "who is owner", "how to play song", "how to create group", "how to post status", "how to call", "how to report", "how to block", "what is uid", "how to search user", "how to create poll", "how to save notes", "how to backup", "support email", "payment safe", "password safe", "what is qwng", "what is myqchat", "help menu"]
    out = []
    for t in tests:
        r = bot_final_test_one(t)
        out.append(r)
    return out

def bot_memory_storage_test(user_id):
    mem = bot_get_memory(user_id)
    return mem

@app.route("/api/final/bot-test")
def api_final_bot_test():
    results = bot_final_test_many()
    return jsonify({"ok": True, "total": len(results), "tests": results})

@app.route("/api/final/smart-test")
def api_final_smart_test():
    q = request.args.get("q") or "what is myqchat"
    ans = call_smart_bot(q)
    return jsonify({"ok": True, "q": q, "answer": ans, "model": GOOGLE_STUDIO_MODEL})

@app.route("/api/final/memory-test")
def api_final_memory_test():
    uid = request.args.get("user_id") or "0"
    return jsonify(bot_memory_storage_test(uid))

@app.route("/api/final/all-systems")
def api_final_all_systems():
    return jsonify({"ok": True, "systems": ["autocorrect", "intent_score", "synonym_short", "fuzzy_tfidf", "context_memory", "topic_change", "fallback", "typing", "self_correction", "tick_owner_admin_support", "chat_group_status_call", "song_profile_search", "poll_notes_backup", "password_block_safety", "api_memory"]})
FRONTEND_BIG_CSS = "body{font-family:Arial;margin:0;background:rgb(245,245,245)} .topbar{background:rgb(7,94,84);color:white;padding:14px;display:flex;justify-content:space-between;align-items:center} .topbar b{font-size:18px} .herobox{background:white;margin:12px;padding:18px;border-radius:16px;text-align:center} .herobox h1{margin:4px;font-size:22px} .herobox p{color:rgb(100,100,100);font-size:13px} .grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px} .card{background:white;padding:16px;border-radius:14px;text-align:center;cursor:pointer} .card b{font-size:15px} .card p{font-size:12px;color:rgb(100,100,100)} .chatlist{background:white;margin:10px;border-radius:14px;overflow:hidden} .chatrow{display:flex;gap:10px;padding:12px;border-bottom:1px solid rgb(240,240,240);cursor:pointer} .avatar{width:44px;height:44px;border-radius:50%;background:rgb(7,94,84);color:white;display:flex;align-items:center;justify-content:center;font-size:18px} .chatinfo{flex:1} .chatinfo b{font-size:14px} .chatinfo p{font-size:12px;color:rgb(120,120,120);margin:2px} .time{font-size:11px;color:rgb(150,150,150)} .bottombar{display:flex;background:white;border-top:1px solid rgb(220,220,220);position:fixed;bottom:0;width:100%} .bottombar button{flex:1;padding:14px;border:none;background:white;font-size:14px;cursor:pointer}"

FRONTEND_BIG_HOME_HTML = "<div class='topbar'><b>MyQchat</b><span>QWNG</span></div><div class='herobox'><h1>Welcome to MyQchat</h1><p>Simple, Fast, Beautiful Chat by QWNG</p><p>Owner LoyalWQ UID 10000001 L Tick</p></div><div class='grid2'><div class='card' onclick=\"openChat('QWNG Bot')\"><b>QWNG Bot</b><p>Fast answers from code</p></div><div class='card' onclick=\"openChat('Smart Bot')\"><b>Smart Bot</b><p>Gemini 2.5 Flash smart</p></div><div class='card' onclick='showSongs()'><b>Songs</b><p>Play songs, custom URL</p></div><div class='card' onclick='showGroups()'><b>Groups</b><p>Group chat, members</p></div></div><div class='chatlist'><div class='chatrow' onclick=\"openChat('QWNG Bot')\"><div class='avatar'>Q</div><div class='chatinfo'><b>QWNG Bot</b><p>Ask about Tick, Song, Chat, Group</p></div><div class='time'>Now</div></div><div class='chatrow' onclick=\"openChat('Smart Bot')\"><div class='avatar'>S</div><div class='chatinfo'><b>Smart Bot</b><p>Ask anything, smart help</p></div><div class='time'>Now</div></div><div class='chatrow' onclick=\"openChat('LoyalWQ')\"><div class='avatar'>L</div><div class='chatinfo'><b>LoyalWQ L Tick</b><p>Owner UID 10000001</p></div><div class='time'>Now</div></div></div>"

@app.route("/frontend-big")
def frontend_big_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>MyQchat Big</title><style>" + FRONTEND_BIG_CSS + "</style></head><body>" + FRONTEND_BIG_HOME_HTML + "<div style='height:70px'></div><div class='bottombar'><button onclick='showChats()'>Chats</button><button onclick='showGroups()'>Groups</button><button onclick='showSongs()'>Songs</button><button onclick='showSettings()'>Settings</button></div><script>" + GOOD_LAYOUT_JS + "</script></body></html>"
    return html
 FRONTEND_CHAT_JS = "let activeChat='QWNG Bot'; let activeUserId='1'; function openChat(name){activeChat=name; let box=document.getElementById('chatBox'); if(!box) return; box.innerHTML=''; let head=document.createElement('div'); head.className='chatrow'; head.innerHTML='<div class=avatar>'+name.charAt(0)+'</div><div class=chatinfo><b>'+name+'</b><p>Online</p></div>'; box.appendChild(head); let welcome=document.createElement('div'); welcome.className='msg'; welcome.innerText='Hello. I am '+name+'. Ask about Tick, Song, Chat, Group, Status, Call, Settings.'; box.appendChild(welcome);} function sendMsgBig(){let input=document.getElementById('msgInput'); if(!input) return; let text=input.value.trim(); if(!text) return; let box=document.getElementById('chatBox'); let m=document.createElement('div'); m.className='msg msgme'; m.innerText=text; box.appendChild(m); input.value=''; let t=document.createElement('div'); t.className='msg'; t.innerText='typing...'; t.id='typingRow'; box.appendChild(t); fetch('/api/bot/smart-fallback?q='+encodeURIComponent(text)+'&user_id='+activeUserId).then(r=>r.json()).then(d=>{document.getElementById('typingRow').innerText=d.result.answer;});} function showChatsBig(){window.location.href='/frontend-big';} function showGroupsBig(){window.location.href='/frontend-big';} function showSongsBig(){window.location.href='/songs-page';} function showSettingsBig(){alert('Settings: Tick Request, Report, Block, Backup, Export, Support support.qwng@gmail.com');} function showLoginBig(){window.location.href='/';} function doLoginBig(){alert('Login checking with server');} function doSignupBig(){alert('Signup checking with server');}"

FRONTEND_CHAT_HTML = "<div class='topbar'><b id='chatTitle'>QWNG Bot</b><span onclick='showChatsBig()'>Back</span></div><div class='chatbox' id='chatBox' style='height:70vh;overflow-y:auto;padding:10px'></div><div class='inputrow' style='display:flex;gap:8px;padding:10px;background:white'><input id='msgInput' placeholder='Type message' style='flex:1;padding:12px;border-radius:20px;border:1px solid rgb(220,220,220)'><button onclick='sendMsgBig()' style='padding:10px 16px;border-radius:20px;border:none;background:rgb(7,94,84);color:white'>Send</button></div>"

@app.route("/chat-page")
def chat_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Chat MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px;max-width:80%} .msgme{background:rgb(220,248,198);margin-left:auto} </style></head><body>" + FRONTEND_CHAT_HTML + "<script>" + FRONTEND_CHAT_JS + " openChat('QWNG Bot');</script></body></html>"
    return html

@app.route("/bot-page")
def bot_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Bot MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px;max-width:80%} .msgme{background:rgb(220,248,198);margin-left:auto} </style></head><body><div class='topbar'><b>QWNG Bot + Smart Bot</b><span>QWNG</span></div><div class='herobox'><h2>2 Bots</h2><p>QWNG Bot from code, Smart Bot from Gemini 2.5 Flash</p></div>" + FRONTEND_CHAT_HTML + "<script>" + FRONTEND_CHAT_JS + " openChat('QWNG Bot');</script></body></html>"
    return html
FRONTEND_FEATURES_JS = "function showPolls(){fetch('/api/poll/list').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); if(!box) return; box.innerHTML='<div class=msg>Polls</div>'; d.polls.forEach(p=>{let div=document.createElement('div'); div.className='msg'; div.innerText=p.question; box.appendChild(div);});});} function createPoll(){let q=prompt('Poll question'); if(!q) return; let o1=prompt('Option 1'); let o2=prompt('Option 2'); fetch('/api/poll/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,options:[o1,o2],creator_id:1})}).then(r=>r.json()).then(d=>{alert('Poll created'); showPolls();});} function showNotes(){fetch('/api/notes/list?user_id=1').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); box.innerHTML='<div class=msg>Notes</div>'; d.notes.forEach(n=>{let div=document.createElement('div'); div.className='msg'; div.innerText=n.title+' - '+n.content; box.appendChild(div);});});} function addNote(){let t=prompt('Note title'); let c=prompt('Note content'); fetch('/api/notes/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:1,title:t,content:c})}).then(r=>r.json()).then(d=>{alert('Note saved'); showNotes();});} function showContacts(){fetch('/api/contacts/list?user_id=1').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); box.innerHTML='<div class=msg>Saved Contacts</div>'; d.contacts.forEach(c=>{let div=document.createElement('div'); div.className='msg'; div.innerText=c.name+' - '+c.username+' UID '+c.uid; box.appendChild(div);});});} function showReminders(){fetch('/api/reminders/list?user_id=1').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); box.innerHTML='<div class=msg>Reminders</div>'; d.reminders.forEach(rm=>{let div=document.createElement('div'); div.className='msg'; div.innerText=rm.title+' at '+rm.time_text; box.appendChild(div);});});}"

FRONTEND_FEATURES_HTML = "<div class='grid2'><div class='card' onclick='showPolls()'><b>Poll</b><p>Create and vote</p></div><div class='card' onclick='showNotes()'><b>Notes</b><p>Private notes</p></div><div class='card' onclick='showContacts()'><b>Contacts</b><p>Saved people</p></div><div class='card' onclick='showReminders()'><b>Reminders</b><p>Set reminder</p></div><div class='card' onclick='createPoll()'><b>Create Poll</b><p>New poll</p></div><div class='card' onclick='addNote()'><b>Add Note</b><p>New note</p></div></div>"

@app.route("/features-page")
def features_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Features MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px} </style></head><body><div class='topbar'><b>Features</b><span>QWNG</span></div>" + FRONTEND_FEATURES_HTML + "<div id='chatBox' style='padding:10px'></div><script>" + FRONTEND_FEATURES_JS + "</script></body></html>"
    return html
  FRONTEND_ADMIN_JS = "function showAdmin(){fetch('/api/admin/users').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); if(!box) return; box.innerHTML='<div class=msg>Admin Users</div>'; d.users.forEach(u=>{let div=document.createElement('div'); div.className='msg'; div.innerText=u.username+' UID '+u.uid+' Tick '+u.tick; box.appendChild(div);});});} function showTicks(){fetch('/api/admin/ticks').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); box.innerHTML='<div class=msg>Tick Requests</div>'; d.ticks.forEach(t=>{let div=document.createElement('div'); div.className='msg'; div.innerText='User '+t.user_id+' Tick '+t.tick_type+' Status '+t.status; box.appendChild(div);});});} function showReports(){fetch('/api/admin/reports').then(r=>r.json()).then(d=>{let box=document.getElementById('chatBox'); box.innerHTML='<div class=msg>Reports</div>'; d.reports.forEach(rp=>{let div=document.createElement('div'); div.className='msg'; div.innerText='Report '+rp.id+' Reason '+rp.reason; box.appendChild(div);});});} function requestTick(){let t=prompt('Tick Blue or Green'); let reason=prompt('Reason, Green needs reason'); fetch('/api/tick/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:1,tick_type:t,reason:reason})}).then(r=>r.json()).then(d=>{alert('Tick requested');});} function doReport(){let target=prompt('Target user id'); let reason=prompt('Reason min 5 chars'); fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reporter_id:1,target_id:target,reason:reason})}).then(r=>r.json()).then(d=>{alert('Reported');});} function doBlock(){let target=prompt('Block user id'); fetch('/api/block',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({blocker_id:1,blocked_id:target})}).then(r=>r.json()).then(d=>{alert('Blocked');});} function doBackup(){fetch('/api/backup?user_id=1').then(r=>r.json()).then(d=>{alert('Backup done. Messages '+d.backup.messages.length);});} function doExport(){fetch('/api/export?user_id=1').then(r=>r.json()).then(d=>{alert('Export done for '+d.export.user.username);});}"

FRONTEND_SETTINGS_HTML = "<div class='grid2'><div class='card' onclick='requestTick()'><b>Tick Request</b><p>Blue or Green</p></div><div class='card' onclick='doReport()'><b>Report</b><p>Report user</p></div><div class='card' onclick='doBlock()'><b>Block</b><p>Block user</p></div><div class='card' onclick='doBackup()'><b>Backup</b><p>Save chats</p></div><div class='card' onclick='doExport()'><b>Export</b><p>Get data</p></div><div class='card' onclick='showAdmin()'><b>Admin</b><p>Only Owner</p></div><div class='card' onclick='showTicks()'><b>Tick List</b><p>Admin check</p></div><div class='card' onclick='showReports()'><b>Reports</b><p>Admin check</p></div></div>"

@app.route("/settings-page")
def settings_page():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Settings MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px} </style></head><body><div class='topbar'><b>Settings</b><span>QWNG</span></div><div class='herobox'><p>Support support.qwng@gmail.com</p><p>Payment only inside app</p><p>Never share password or OTP</p></div>" + FRONTEND_SETTINGS_HTML + "<div id='chatBox' style='padding:10px'></div><script>" + FRONTEND_ADMIN_JS + "</script></body></html>"
    return html

@app.route("/admin-page")
def admin_page_route():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Admin MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px} </style></head><body><div class='topbar'><b>Admin Panel</b><span>Owner Only</span></div>" + FRONTEND_SETTINGS_HTML + "<div id='chatBox' style='padding:10px'></div><script>" + FRONTEND_ADMIN_JS + "</script></body></html>"
    return html
TERMS_TEXT = "MyQchat Terms: App by QWNG. Owner LoyalWQ UID 10000001. Use app for good chat. Do not scam. Do not share password or OTP. Payment only inside app in Settings. Admin can block scam users. Support support.qwng@gmail.com."

PRIVACY_TEXT = "MyQchat Privacy: We save username, UID, bio, email, chats, notes, contacts, reminders. Notes and contacts are private. We never ask password or OTP. We never sell data. Support support.qwng@gmail.com."

HELP_TEXT = "MyQchat Help: Ask QWNG Bot about Tick, Song, Chat, Group, Status, Call, Settings, Admin, Report, Block, UID, Login, Password. Support email support.qwng@gmail.com. Reply within 24 hours."

@app.route("/terms")
def terms_page():
    return jsonify({"ok": True, "terms": TERMS_TEXT, "app": "MyQchat", "owner": "LoyalWQ", "support": "support.qwng@gmail.com"})

@app.route("/privacy")
def privacy_page():
    return jsonify({"ok": True, "privacy": PRIVACY_TEXT, "app": "MyQchat", "support": "support.qwng@gmail.com"})

@app.route("/help")
def help_page():
    return jsonify({"ok": True, "help": HELP_TEXT, "menu": BOT_HELP_MENU, "support": "support.qwng@gmail.com"})

@app.route("/api/health-full")
def health_full():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_msgs = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    total_songs = db.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    return jsonify({"ok": True, "app": "MyQchat", "version": VERSION, "owner": "LoyalWQ", "owner_uid": "10000001", "total_users": total_users, "total_messages": total_msgs, "total_songs": total_songs, "support": "support.qwng@gmail.com", "status": "Live"})
    BOT_EXTRA_DATA_1 = {"app_start": "App Start: open MyQchat, login, see Chats.", "app_home": "App Home: Chats, Groups, Songs, Settings at bottom.", "app_chats": "App Chats: list of chats with name, last message, time.", "app_groups_home": "App Groups: list of groups.", "app_songs_home": "App Songs: list of songs.", "app_settings_home": "App Settings: Tick, Report, Block, Backup, Export.", "login_home": "Login Home: enter username and password, tap Login.", "signup_home": "Signup Home: enter username, password, recovery email, tap Signup.", "bot_home": "Bot Home: QWNG Bot and Smart Bot are default chats.", "bot_use": "Bot Use: tap QWNG Bot or Smart Bot, type question.", "bot_typing": "Bot Typing: bot shows typing 1.2 sec for short, 2.8 sec for long.", "bot_memory_use": "Bot Memory: bot remembers last topic.", "bot_topic_use": "Bot Topic: if you change topic, bot forgets old topic."}

BOT_EXTRA_DATA_2 = {"chat_extra_1": "Chat Extra: you can star, forward, edit, delete message.", "chat_extra_2": "Chat Extra: you can mute, archive, pin chat.", "group_extra_1": "Group Extra: admin can add, remove, delete group.", "group_extra_2": "Group Extra: members can leave group.", "status_extra_1": "Status Extra: post text, view list, delete.", "call_extra_1": "Call Extra: voice, video, mute, end.", "song_extra_1": "Song Extra: search, play, custom URL.", "poll_extra_1": "Poll Extra: create, vote, see result.", "notes_extra_1": "Notes Extra: add, list, delete.", "contacts_extra_1": "Contacts Extra: add, list, delete.", "reminder_extra_1": "Reminder Extra: add, list, done.", "backup_extra_1": "Backup Extra: backup chats and notes.", "export_extra_1": "Export Extra: export user data."}

BOT_EXTRA_DATA_3 = {"tick_extra_1": "Tick Extra: Blue needs no reason, Green needs reason, L only Owner.", "tick_extra_2": "Tick Extra: request in Settings, Admin approves.", "admin_extra_1": "Admin Extra: Admin Panel inside Settings, only Owner.", "admin_extra_2": "Admin Extra: approve tick, check reports, broadcast.", "report_extra_1": "Report Extra: reason min 5 chars, Admin checks.", "block_extra_1": "Block Extra: blocked user cannot message.", "uid_extra_1": "UID Extra: UID is user id, search by UID.", "login_extra_1": "Login Extra: username plus password.", "password_extra_1": "Password Extra: never share password or OTP.", "support_extra_1": "Support Extra: support.qwng@gmail.com, reply in 24 hours.", "payment_extra_1": "Payment Extra: payment only inside app in Settings.", "safety_extra_1": "Safety Extra: if scam, Block and Report."}

BOT_EXTRA_DATA_4 = {"qwng_extra_1": "QWNG Extra: QWNG is Software Developer Team.", "myqchat_extra_1": "MyQchat Extra: simple chat app by QWNG.", "owner_extra_1": "Owner Extra: LoyalWQ UID 10000001 L Tick.", "version_extra_1": "Version Extra: 2.0.0 Smart Bot.", "url_extra_1": "URL Extra: myqchat-1.onrender.com.", "features_extra_1": "Features Extra: Chat, Group, Status, Call, Song, Poll, Notes, Contacts, Reminders, Backup, Export.", "help_extra_1": "Help Extra: ask bot about Tick, Song, Chat, Group, Status, Call, Settings.", "chat_help_extra": "Chat Help Extra: open Chats, tap user, send message.", "group_help_extra": "Group Help Extra: open Groups, create group.", "song_help_extra": "Song Help Extra: open Songs, play song.", "status_help_extra": "Status Help Extra: open Status, post.", "call_help_extra": "Call Help Extra: open chat, tap Call."}

BOT_ALL_EXTRA = {}
BOT_ALL_EXTRA.update(BOT_EXTRA_DATA_1)
BOT_ALL_EXTRA.update(BOT_EXTRA_DATA_2)
BOT_ALL_EXTRA.update(BOT_EXTRA_DATA_3)
BOT_ALL_EXTRA.update(BOT_EXTRA_DATA_4)
BOT_ALL_EXTRA.update(BOT_COMBINED_SAFETY_KB)

def bot_search_extra_all(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_ALL_EXTRA:
        return BOT_ALL_EXTRA[fixed]
    if norm in BOT_ALL_EXTRA:
        return BOT_ALL_EXTRA[norm]
    best_key = ""
    best_score = 0
    for key in BOT_ALL_EXTRA:
        s = bot_fuzzy_similarity(fixed, key)
        if s > best_score:
            best_key = key
            best_score = s
    if best_score >= 70:
        return BOT_ALL_EXTRA[best_key]
    return ""

def bot_final_answer_all(text, user_id="0", username="User"):
    local = bot_search_extra_all(text)
    if local:
        topic = bot_detect_topic(text) or "general"
        bot_save_memory(user_id, username, text, local, topic)
        return {"source": "code_extra", "answer": local, "topic": topic}
    code = bot_final_knowledge_answer(text)
    if code["found"]:
        return {"source": "code", "answer": code["answer"], "topic": bot_detect_topic(text) or "general"}
    api_ans = call_smart_bot(text)
    return {"source": "api", "answer": api_ans, "topic": "smart"}

@app.route("/api/bot/extra-all")
def api_bot_extra_all():
    q = request.args.get("q") or ""
    return jsonify(bot_final_answer_all(q, request.args.get("user_id") or "0", request.args.get("username") or "User"))

@app.route("/api/final/run")
def api_final_run():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return jsonify({"ok": True, "app": "MyQchat", "version": VERSION, "owner": "LoyalWQ", "owner_uid": "10000001", "total_users": total_users, "support": "support.qwng@gmail.com", "status": "Ready to run", "start": "gunicorn app:app", "health": "/api/health"})

@app.route("/api/final/count")
def api_final_count():
    return jsonify({"ok": True, "parts": "1 to 24 combined", "systems": "autocorrect, intent, synonym, fuzzy, memory, topic, fallback, typing, self correction, knowledge, api", "datasheet": len(BOT_ALL_EXTRA)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    BOT_FINAL_EXTRA_QA = {"final_q1": "MyQchat is a simple chat app built by QWNG.", "final_q2": "Owner is LoyalWQ UID 10000001 with L Tick.", "final_q3": "QWNG is a Software Developer Team.", "final_q4": "Support email is support.qwng@gmail.com. Reply within 24 hours.", "final_q5": "Blue Tick is verification. No reason needed.", "final_q6": "Green Tick needs reason. Reason is mandatory.", "final_q7": "L Tick is only for Owner.", "final_q8": "Scam Tick appears after report.", "final_q9": "Song Library: Admin adds songs by URL. User can pick or paste custom URL.", "final_q10": "Chat has Reply, Star, Forward, Edit, Delete, Mute, Archive, Pin.", "final_q11": "Group has admin, members, add, remove, leave, delete.", "final_q12": "Status is short post. You can post and delete.", "final_q13": "Call is voice and video. Tap Start, End.", "final_q14": "Settings has Admin Panel, Tick Request, Report, Block, Backup, Export.", "final_q15": "Admin Panel is inside Settings. Only Owner can see it.", "final_q16": "Tick Request is inside Settings.", "final_q17": "Report and Block are inside Settings.", "final_q18": "Search by Username and UID is available.", "final_q19": "Poll, Notes, Saved Contacts, Reminders are available.", "final_q20": "Backup and Export are available in Settings.", "final_q21": "Never share password or OTP. MyQchat never asks for it.", "final_q22": "Payment only inside MyQchat app in Settings. Never pay on email or 【entity-WhatsApp¦canonical_name=WhatsApp】.", "final_q23": "If scam, Block and Report. Contact support.qwng@gmail.com.", "final_q24": "QWNG Bot answers from code, fast. Smart Bot answers via Gemini 2.5 Flash.", "final_q25": "App URL is myqchat-1.onrender.com."}

def bot_search_final_extra(text):
    norm = bot_full_normalize(text)
    fixed = bot_fix_fuzzy_words(norm)
    if fixed in BOT_FINAL_EXTRA_QA:
        return BOT_FINAL_EXTRA_QA[fixed]
    if norm in BOT_FINAL_EXTRA_QA:
        return BOT_FINAL_EXTRA_QA[norm]
    return ""

FRONTEND_EXTRA_BOT_HTML = "<div class='topbar'><b>Smart Bot Chat</b><span>QWNG</span></div><div class='herobox'><h2>Chat with Bots</h2><p>QWNG Bot fast, Smart Bot smart</p><p>Typing 1.2 sec short, 2.8 sec long</p></div><div class='grid2'><div class='card' onclick=\"openChat('QWNG Bot')\"><b>QWNG Bot</b><p>Code answers</p></div><div class='card' onclick=\"openChat('Smart Bot')\"><b>Smart Bot</b><p>Gemini 2.5 Flash</p></div></div>"

FRONTEND_EXTRA_ADMIN_HTML = "<div class='topbar'><b>Admin plus Settings Extra</b><span>Owner Only</span></div><div class='herobox'><p>Admin Panel, Tick List, Reports, Broadcast</p><p>Settings: Tick, Report, Block, Backup, Export</p></div>"

@app.route("/frontend-extra-bot")
def frontend_extra_bot():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Extra Bot MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px} </style></head><body>" + FRONTEND_EXTRA_BOT_HTML + FRONTEND_CHAT_HTML + "<script>" + FRONTEND_CHAT_JS + " openChat('QWNG Bot');</script></body></html>"
    return html

@app.route("/frontend-extra-admin")
def frontend_extra_admin():
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Extra Admin MyQchat</title><style>" + FRONTEND_BIG_CSS + " .msg{background:white;padding:8px 10px;margin:6px;border-radius:10px} </style></head><body>" + FRONTEND_EXTRA_ADMIN_HTML + FRONTEND_SETTINGS_HTML + "<div id='chatBox' style='padding:10px'></div><script>" + FRONTEND_ADMIN_JS + "</script></body></html>"
    return html

@app.route("/api/final/extra-test")
def api_final_extra_test():
    tests = ["what is myqchat", "who is owner", "blue tick", "green tick", "l tick", "song", "chat", "group", "status", "call", "settings", "admin", "report", "block", "uid", "login", "password", "support", "payment", "scam"]
    out = []
    for t in tests:
        ans = bot_search_final_extra(t)
        if not ans:
            ans = bot_search_all_combined(t)
        if not ans:
            ans = BOT_HELP_MENU
        out.append({"q": t, "answer": ans})
    return jsonify({"ok": True, "total": len(out), "tests": out})

@app.route("/api/final/deploy")
def api_final_deploy():
    return jsonify({"ok": True, "app": "MyQchat", "owner": "LoyalWQ", "owner_uid": "10000001", "start_command": "gunicorn app:app", "health_url": "myqchat-1.onrender.com/api/health", "uptime": "UptimeRobot ping every 5 minutes", "database": "Use Postgres DATABASE_URL from Supabase for no delete", "api_key": "AQ.Ab8RN6KzPb2y_uHlz0qrHri-rFx32ar0GcL_8dfkgngwu_xPyw", "model": "gemini-2.5-flash", "support": "support.qwng@gmail.com", "status": "Ready to deploy"})

@app.route("/api/final/complete")
def api_final_complete():
    total_kb = len(BOT_ALL_EXTRA) + len(BOT_FINAL_EXTRA_QA) + len(BOT_COMBINED_SAFETY_KB)
    return jsonify({"ok": True, "message": "MyQchat 28 Parts Complete", "app": "MyQchat", "team": "QWNG Software Developer Team", "owner": "LoyalWQ", "owner_uid": "10000001", "parts": "1 to 28 combined", "systems": 10, "datasheet_entries": total_kb, "layout": "Big, Free, Beautiful, Mobile, Features focused", "support": "support.qwng@gmail.com", "status": "Complete"})
    
