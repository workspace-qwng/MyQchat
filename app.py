# MyQchat - Developed by QWNG - FINAL 【entity-WhatsApp¦canonical_name=WhatsApp】 Like - PART 1/3
import os, random, time, secrets, json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MyQchat-QWNG-Secret-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///myqchat_final.db")
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT = "https://myqchat-1.onrender.com/auth/google/callback"
OWNER_EMAIL = "loyalwq@gmail.com"
OWNER_USERNAME = "LoyalWQ"

# ---------- MODELS ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(20), unique=True)  # 8-digit Permanent UID
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(300))
    google_id = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    tick = db.Column(db.String(20), default="")  # Blue, Orange, Green, L, Scam
    bio = db.Column(db.String(200), default="Hey there! I am using MyQchat")
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    def to_dict(self):
        return {"id":self.id,"uid":self.uid,"username":self.username,"email":self.email,"name":self.name or self.username,"tick":self.tick,"is_admin":self.is_admin,"online":self.online,"last_seen":self.last_seen.strftime("%H:%M") if self.last_seen else "","bio":self.bio}

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer)
    contact_uid = db.Column(db.String(20))
    contact_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer)
    sender_uid = db.Column(db.String(20))
    sender_name = db.Column(db.String(100))
    to_uid = db.Column(db.String(20))
    to_id = db.Column(db.Integer)
    text = db.Column(db.String(500))
    msg_type = db.Column(db.String(20), default="text")  # text, image, voice, broadcast
    is_deleted = db.Column(db.Boolean, default=False)
    is_broadcast = db.Column(db.Boolean, default=False)
    broadcast_tag = db.Column(db.String(20), default="")  # Announcement, Warning, Ad
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer)
    reported_uid = db.Column(db.String(20))
    reason = db.Column(db.String(20))  # Scam, Harassment, Fake, Spam, Other
    detail = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer)
    blocked_uid = db.Column(db.String(20))

def gen_uid():
    while True:
        u = str(random.randint(10000000, 99999999))
        if not User.query.filter_by(uid=u).first():
            return u

def get_user_by_uid(uid):
    return User.query.filter_by(uid=uid).first()

def init_db():
    try:
        with app.app_context():
            db.create_all()
            db_url = os.environ.get("DATABASE_URL","")
            if "postgres" in db_url:
                try:
                    db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_id VARCHAR(100)'))
                    db.session.commit()
                except Exception as e:
                    print("PG migrate:", e); db.session.rollback()
            else:
                try:
                    cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
                    if "google_id" not in cols:
                        db.session.execute(text("ALTER TABLE user ADD COLUMN google_id VARCHAR(100)"))
                        db.session.commit()
                except Exception as e:
                    print("SQLite migrate:", e); db.session.rollback()
            if not User.query.filter_by(username=OWNER_USERNAME).first():
                u = User(username=OWNER_USERNAME, email=OWNER_EMAIL, name="LoyalWQ Owner", is_admin=True, tick="L", uid=gen_uid())
                u.set_password("AlwaysBeLoyalQ"); db.session.add(u); db.session.commit()
                print("Owner created UID:", u.uid)
    except Exception as e:
        print("init_db error:", e)
init_db()

# ---------- AUTH APIs ----------
@app.route("/api/signup", methods=["POST"])
def signup():
    try:
        d = request.get_json(force=True)
        username = (d.get("username") or "").strip()
        email = (d.get("email") or "").strip().lower()
        password = d.get("password") or ""
        name = (d.get("name") or username).strip()
        if not username or not email or not password:
            return jsonify({"success":False,"error":"All fields required"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"success":False,"error":"Username already taken"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"success":False,"error":"Email already used"}), 400
        u = User(username=username, email=email, name=name, uid=gen_uid())
        u.set_password(password)
        if email == OWNER_EMAIL: u.is_admin=True; u.tick="L"
        db.session.add(u); db.session.commit()
        return jsonify({"success":True,"user":u.to_dict()})
    except Exception as e:
        db.session.rollback(); return jsonify({"success":False,"error":str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login():
    try:
        d = request.get_json(force=True)
        username = (d.get("username") or "").strip()
        password = d.get("password") or ""
        u = User.query.filter_by(username=username).first() or User.query.filter_by(email=username.lower()).first()
        if not u or not u.check_password(password):
            return jsonify({"success":False,"error":"Wrong username or password"}), 401
        if u.is_banned:
            if u.banned_until and u.banned_until > datetime.utcnow():
                return jsonify({"success":False,"error":"Banned till "+str(u.banned_until)}), 403
        u.online=True; u.last_seen=datetime.utcnow(); db.session.commit()
        session["uid"]=u.uid
        return jsonify({"success":True,"user":u.to_dict()})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    uid = request.get_json(force=True, silent=True) or {}
    u = User.query.filter_by(uid=uid.get("uid")).first()
    if u: u.online=False; u.last_seen=datetime.utcnow(); db.session.commit()
    session.clear(); return jsonify({"success":True})

@app.route("/auth/google")
def google_auth():
    from urllib.parse import urlencode
    params = {"client_id":GOOGLE_CLIENT_ID,"redirect_uri":GOOGLE_REDIRECT,"response_type":"code","scope":"openid email profile","access_type":"offline","prompt":"consent"}
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(params))

@app.route("/auth/google/callback")
def google_cb():
    code = request.args.get("code")
    if not code: return "Google login failed - No code"
    try:
        import requests
        r = requests.post("https://oauth2.googleapis.com/token", data={"code":code,"client_id":GOOGLE_CLIENT_ID,"client_secret":GOOGLE_CLIENT_SECRET,"redirect_uri":GOOGLE_REDIRECT,"grant_type":"authorization_code"}, timeout=15).json()
        id_token = r.get("id_token")
        if not id_token: return "Google token failed: "+str(r)
        from google.oauth2 import id_token as gid
        from google.auth.transport import requests as greq
        info = gid.verify_oauth2_token(id_token, greq.Request(), GOOGLE_CLIENT_ID)
        email = info.get("email"); name = info.get("name","User")
        u = User.query.filter_by(email=email).first()
        if not u:
            base = email.split("@")[0].replace(".","")[:15]
            uname = base
            i=1
            while User.query.filter_by(username=uname).first():
                i+=1; uname=f"{base}{i}"
            u = User(username=uname, email=email, name=name, uid=gen_uid(), google_id=info.get("sub"))
            u.set_password(secrets.token_hex(8))
            if email==OWNER_EMAIL: u.is_admin=True; u.tick="L"
            db.session.add(u); db.session.commit()
        u.online=True; db.session.commit()
        session["uid"]=u.uid
        return redirect(f"/?google_uid={u.uid}")
    except Exception as e:
        return f"Google login error: {e}"

@app.route("/fix-db")
def fix_db():
    try: init_db(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@app.route("/cron/cleanup")
def cleanup():
    try:
        now = datetime.utcnow()
        # Message 2 din, Image 1 hr, Voice 20 min
        Message.query.filter(Message.created_at < now - timedelta(days=2), Message.msg_type=="text").delete()
        Message.query.filter(Message.created_at < now - timedelta(hours=1), Message.msg_type=="image").delete()
        Message.query.filter(Message.created_at < now - timedelta(minutes=20), Message.msg_type=="voice").delete()
        db.session.commit(); return jsonify({"ok":True,"cleaned":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@app.errorhandler(404)
def e404(e): return jsonify({"success":False,"error":"Not found"}), 404
@app.errorhandler(500)
def e500(e): return jsonify({"success":False,"error":"Server error"}), 500
# ---------- CHAT APIs - PART 2 ----------
@app.route("/api/me")
def me():
    uid = request.args.get("uid")
    u = User.query.filter_by(uid=uid).first()
    if not u: return jsonify({"success":False}), 404
    return jsonify({"success":True,"user":u.to_dict()})

@app.route("/api/users")
def users():
    uid = request.args.get("uid","")
    all_users = User.query.filter(User.uid != uid).order_by(User.created_at.desc()).all()
    # Chats List ke liye - last message bhi bhejo
    out=[]
    for u in all_users:
        last = Message.query.filter(((Message.sender_uid==uid)&(Message.to_uid==u.uid))|((Message.sender_uid==u.uid)&(Message.to_uid==uid))).order_by(Message.created_at.desc()).first()
        unread = Message.query.filter_by(sender_uid=u.uid, to_uid=uid).count()
        d=u.to_dict()
        d["last_msg"] = ("You: " + last.text if last and last.sender_uid==uid else last.text) if last and not last.is_deleted else ("Deleted message" if last else "")
        d["last_time"] = last.created_at.strftime("%I:%M %p") if last else ""
        d["unread"] = unread
        out.append(d)
    return jsonify({"success":True,"users":out})

@app.route("/api/search-uid")
def search_uid():
    q = request.args.get("q","").strip()
    u = User.query.filter_by(uid=q).first()
    if not u: return jsonify({"success":False,"error":"No user found with this UID"})
    return jsonify({"success":True,"user":u.to_dict()})

@app.route("/api/add-contact", methods=["POST"])
def add_contact():
    d=request.get_json(force=True); owner=d.get("my_uid"); c_uid=d.get("contact_uid")
    u=User.query.filter_by(uid=c_uid).first()
    if not u: return jsonify({"success":False,"error":"UID not found"}),404
    if Contact.query.filter_by(owner_id=User.query.filter_by(uid=owner).first().id, contact_uid=c_uid).first():
        return jsonify({"success":True,"msg":"Already in contacts"})
    ow=User.query.filter_by(uid=owner).first()
    db.session.add(Contact(owner_id=ow.id, contact_uid=c_uid, contact_name=u.name)); db.session.commit()
    return jsonify({"success":True,"msg":"Contact saved"})

@app.route("/api/messages")
def get_msgs():
    my_uid=request.args.get("my_uid"); other_uid=request.args.get("other_uid")
    msgs=Message.query.filter(((Message.sender_uid==my_uid)&(Message.to_uid==other_uid))|((Message.sender_uid==other_uid)&(Message.to_uid==my_uid))).order_by(Message.created_at.asc()).all()
    out=[]
    for m in msgs:
        out.append({"id":m.id,"from":m.sender_uid,"from_name":m.sender_name,"text":"This message was deleted" if m.is_deleted else m.text,"type":m.msg_type,"is_deleted":m.is_deleted,"is_broadcast":m.is_broadcast,"tag":m.broadcast_tag,"time":m.created_at.strftime("%I:%M %p")})
    return jsonify({"success":True,"messages":out})

@app.route("/api/send", methods=["POST"])
def send_msg():
    try:
        d=request.get_json(force=True)
        my_uid=d.get("my_uid"); to_uid=d.get("to_uid"); text=(d.get("text") or "").strip()
        msg_type=d.get("type","text")
        if not text: return jsonify({"success":False,"error":"Empty message"}),400
        if len(text)>100 and msg_type=="text": return jsonify({"success":False,"error":"Max 100 characters"}),400
        me_u=User.query.filter_by(uid=my_uid).first(); to_u=User.query.filter_by(uid=to_uid).first()
        if not me_u or not to_u: return jsonify({"success":False,"error":"User not found"}),404
        # Unknown = 2 msg x 30 letters - check contact
        is_contact = Contact.query.filter_by(owner_id=to_u.id, contact_uid=my_uid).first() or Contact.query.filter_by(owner_id=me_u.id, contact_uid=to_uid).first()
        if not is_contact and me_u.username!="LoyalWQ":
            cnt=Message.query.filter_by(sender_uid=my_uid, to_uid=to_uid).count()
            if cnt>=2: return jsonify({"success":False,"error":"Save to contacts first - Unknown limit 2 messages"}),403
            if len(text)>30: return jsonify({"success":False,"error":"Unknown - Max 30 letters. Save contact to send longer"}),400
        # Cooldown - 10 sec check
        last=Message.query.filter_by(sender_uid=my_uid).order_by(Message.created_at.desc()).first()
        if last and (datetime.utcnow()-last.created_at).total_seconds()<3:
            return jsonify({"success":False,"error":"Wait 3 seconds"}),429
        # 300 msg/hour
        one_hr_ago=datetime.utcnow()-timedelta(hours=1)
        cnt_hr=Message.query.filter(Message.sender_uid==my_uid, Message.created_at>=one_hr_ago).count()
        if cnt_hr>=300: return jsonify({"success":False,"error":"Hourly limit 300 reached"}),429
        m=Message(sender_id=me_u.id, sender_uid=my_uid, sender_name=me_u.name, to_uid=to_uid, to_id=to_u.id, text=text, msg_type=msg_type)
        db.session.add(m); db.session.commit()
        return jsonify({"success":True,"id":m.id})
    except Exception as e:
        db.session.rollback(); return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/delete-msg", methods=["POST"])
def del_msg():
    d=request.get_json(force=True); mid=d.get("id"); my_uid=d.get("my_uid")
    m=Message.query.get(mid)
    if not m: return jsonify({"success":False}),404
    if m.sender_uid!=my_uid: return jsonify({"success":False,"error":"Only sender can delete"}),403
    m.is_deleted=True; db.session.commit()
    return jsonify({"success":True})

@app.route("/api/report", methods=["POST"])
def report():
    d=request.get_json(force=True)
    detail=(d.get("detail") or "")[:400]
    db.session.add(Report(reporter_id=User.query.filter_by(uid=d.get("my_uid")).first().id if User.query.filter_by(uid=d.get("my_uid")).first() else 0, reported_uid=d.get("reported_uid"), reason=d.get("reason"), detail=detail)); db.session.commit()
    return jsonify({"success":True,"msg":"Report sent to Admin"})

@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    d=request.get_json(force=True)
    me_u=User.query.filter_by(uid=d.get("my_uid")).first()
    if not me_u or not me_u.is_admin: return jsonify({"success":False,"error":"Admin only"}),403
    users=User.query.all()
    for u in users:
        if u.uid==me_u.uid: continue
        db.session.add(Message(sender_id=me_u.id, sender_uid=me_u.uid, sender_name="QWNG Bot", to_uid=u.uid, to_id=u.id, text=d.get("text",""), msg_type="text", is_broadcast=True, broadcast_tag=d.get("tag","Announcement")))
    db.session.commit(); return jsonify({"success":True,"msg":"Broadcast sent"})

@app.route("/api/terms")
def terms():
    return jsonify({"title":"Terms","text":"13+ only. Owner can view chats for moderation. Be respectful."})

@app.route("/")
def home():
    return FRONTEND
# ---------- FRONTEND - PART 3 - WhatsApp Like - 3 Pages ----------
FRONTEND = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyQchat - Developed by QWNG</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:Arial,sans-serif}
body{background:#efeae2}
.top{background:#075e54;color:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
.top h1{font-size:22px} .top span{font-size:12px;opacity:.9}
.page{display:none;padding:0}.page.active{display:block}
.card{background:#fff;margin:16px;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
input{width:100%;padding:13px;margin:8px 0;border:1px solid #ddd;border-radius:8px;font-size:15px}
button{padding:11px 18px;border:none;border-radius:22px;font-size:15px;cursor:pointer}
.btn-green{background:#00a884;color:#fff;width:100%;margin-top:8px}.btn-black{background:#111;color:#fff}
.btn-outline{background:#fff;border:1px solid #ccc}
.search{margin:12px;background:#fff;border-radius:22px;padding:10px 14px;display:flex;gap:8px}
.search input{border:none;padding:0;margin:0;outline:none}
.tabs{display:flex;gap:8px;padding:0 12px}.tabs button{background:#fff;border:1px solid #ddd;padding:7px 14px;border-radius:20px}
.tabs button.on{background:#d9fdd3}
.chat-item{background:#fff;display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid #f0f0f0;cursor:pointer;align-items:center}
.avatar{width:48px;height:48px;border-radius:50%;background:#075e54;color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:bold;flex-shrink:0}
.chat-item b{font-size:16px}.chat-item p{font-size:13px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px}
.time{font-size:12px;color:#666;margin-left:auto}
.badge{background:#25d366;color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:12px}
.chat-head{background:#075e54;color:#fff;padding:10px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10}
.chat-head .back{font-size:24px;cursor:pointer}
.msgs{padding:12px;padding-bottom:90px;min-height:70vh}
.bubble{max-width:80%;padding:8px 10px;border-radius:10px;margin:6px 0;font-size:15px;position:relative;word-wrap:break-word}
.mine{background:#d9fdd3;margin-left:auto}.theirs{background:#fff}
.bubble small{font-size:11px;color:#555;float:right;margin:6px 0 0 8px}
.deleted{font-style:italic;color:#777}
.inputbar{position:fixed;bottom:0;left:0;right:0;background:#efeae2;padding:8px;display:flex;gap:8px}
.inputbar input{border-radius:22px;background:#fff}
.sendbtn{background:#00a884;color:#fff;border-radius:50%;width:48px;height:48px;font-size:20px}
.footer{text-align:center;font-size:12px;color:#888;padding:12px}
.tick{color:#53bdeb;font-weight:bold}.tick-L{color:#ff9800;font-weight:bold}
</style></head><body>

<!-- PAGE 1 - LOGIN -->
<div id="page-login" class="page active">
<div class="top"><div><h1>MyQchat</h1><span>Developed by QWNG</span></div><span id="login-status"></span></div>
<div class="card"><h2>Welcome to MyQchat</h2><p style="color:#666;margin:8px 0">Chat with anyone using 8-digit UID. No phone number needed.</p>
<input id="su_name" placeholder="Your Name - e.g. Rahul"><input id="su_username" placeholder="Username"><input id="su_email" placeholder="Email"><input id="su_pass" type="password" placeholder="Password">
<button class="btn-green" onclick="doSignup()">Create Account</button>
<hr style="margin:14px 0"><input id="li_user" placeholder="Username or Email"><input id="li_pass" type="password" placeholder="Password">
<button class="btn-green" onclick="doLogin()">Login</button>
<button class="btn-outline" style="width:100%;margin-top:8px" onclick="location.href='/auth/google'">Sign in with Google</button>
<p id="auth-msg" style="color:#075e54;margin-top:10px"></p></div>
<div class="card"><b>Your UID - After Login</b><p style="color:#666">You will get a permanent 8-digit UID. Share it with friends to chat.</p></div>
<div class="footer">Developed by QWNG - 2026 QWNG Company | Owner - LoyalWQ</div></div>

<!-- PAGE 2 - CHATS LIST -->
<div id="page-chats" class="page">
<div class="top"><div><h1>MyQchat</h1><span id="my-info"></span></div><span onclick="doLogout()" style="cursor:pointer">Logout</span></div>
<div class="search"><span>🔍</span><input id="search-uid" placeholder="Search by 8-digit UID..."><button class="btn-black" onclick="searchUID()">Search</button></div>
<div id="search-result"></div>
<div class="tabs"><button class="on">All</button><button>Unread</button><button>Favourites</button><button>Groups</button></div>
<div id="chat-list" style="margin-top:10px"></div>
<div class="card" id="admin-box" style="display:none"><b>Admin Broadcast - QWNG Bot</b><input id="bc-text" placeholder="Announcement message"><input id="bc-tag" placeholder="Tag - Announcement / Warning / Ad"><button class="btn-green" onclick="doBroadcast()">Send to All</button></div>
<div class="card"><b>Shop</b><p>Shop inside app - Mail: qwngofficial@gmail.com</p><b>Ad</b><p>Single Local Ad - EarnKaro Link Ad - Backed by Ratan Tata</p></div>
<div class="footer">Developed by QWNG</div></div>

<!-- PAGE 3 - CHAT SCREEN -->
<div id="page-chat" class="page">
<div class="chat-head"><span class="back" onclick="showPage('page-chats')">←</span><div class="avatar" id="chat-avatar">?</div><div><b id="chat-name">Name</b><br><span id="chat-uid" style="font-size:12px"></span> <span id="chat-online" style="font-size:12px"></span></div><span style="margin-left:auto">📹 📞 ⋮</span></div>
<div class="msgs" id="msgs"></div>
<div class="inputbar"><input id="msg-input" placeholder="Message" maxlength="100"><button class="sendbtn" onclick="sendMsg()">➤</button></div></div>

<script>
let me=null, currentChat=null, currentChatUser=null;
function showPage(id){document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.getElementById(id).classList.add('active');window.scrollTo(0,0)}
function getQ(n){return new URLSearchParams(location.search).get(n)}
async function api(url,body){let r=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json()}
async function doSignup(){let b={name:document.getElementById('su_name').value,username:document.getElementById('su_username').value,email:document.getElementById('su_email').value,password:document.getElementById('su_pass').value};let j=await api('/api/signup',b);document.getElementById('auth-msg').innerText=j.success?'Account created! Now Login - Your UID: '+j.user.uid:j.error;if(j.success){document.getElementById('li_user').value=b.username}}
async function doLogin(){let b={username:document.getElementById('li_user').value,password:document.getElementById('li_pass').value};let j=await api('/api/login',b);if(!j.success){document.getElementById('auth-msg').innerText=j.error;return}me=j.user;localStorage.setItem('myqchat_uid',me.uid);localStorage.setItem('myqchat_user',JSON.stringify(me));afterLogin()}
function afterLogin(){document.getElementById('my-info').innerText='Hi, '+me.name+' | UID: '+me.uid+(me.tick?' | Tick: '+me.tick:'');if(me.is_admin)document.getElementById('admin-box').style.display='block';showPage('page-chats');loadChats()}
async function loadChats(){let j=await api('/api/users?uid='+me.uid);let h='';j.users.forEach(u=>{let letter=(u.name||'?')[0].toUpperCase();let tick=u.tick?` <span class="tick">${u.tick==='L'?'L ✓':u.tick+' ✓'}</span>`:'';h+=`<div class="chat-item" onclick="openChat('${u.uid}','${u.name.replace(/'/g,'')}')"><div class="avatar">${letter}</div><div><b>${u.name}${tick}</b><p>${u.last_msg||u.bio||''}</p></div><span class="time">${u.last_time||''}</span>${u.unread?`<span class="badge">${u.unread}</span>`:''}</div>`});document.getElementById('chat-list').innerHTML=h||'<div class="card">No users yet. Share your UID with friends.</div>'}
async function searchUID(){let q=document.getElementById('search-uid').value;let j=await api('/api/search-uid?q='+q);document.getElementById('search-result').innerHTML=j.success?`<div class="card"><b>${j.user.name} (@${j.user.username}) - UID: ${j.user.uid}</b><br><button class="btn-green" onclick="saveContact('${j.user.uid}')">Save to Contacts</button> <button class="btn-black" onclick="openChat('${j.user.uid}','${j.user.name}')">Chat</button></div>`:`<div class="card">${j.error}</div>`}
async function saveContact(uid){let j=await api('/api/add-contact',{my_uid:me.uid,contact_uid:uid});alert(j.msg||j.error);loadChats()}
async function openChat(uid,name){currentChat=uid;currentChatUser=name;document.getElementById('chat-name').innerText=name;document.getElementById('chat-uid').innerText='UID: '+uid;document.getElementById('chat-avatar').innerText=name[0].toUpperCase();showPage('page-chat');loadMsgs();let t=setInterval(()=>{if(document.getElementById('page-chat').classList.contains('active'))loadMsgs();else clearInterval(t)},3000)}
async function loadMsgs(){if(!currentChat)return;let j=await api(`/api/messages?my_uid=${me.uid}&other_uid=${currentChat}`);let h='';j.messages.forEach(m=>{let mine=m.from===me.uid;let cls=mine?'mine':'theirs';let txt=m.is_deleted?'<span class="deleted">🚫 This message was deleted</span>':m.text;let del=mine&&!m.is_deleted?` <span style="cursor:pointer" onclick="delMsg(${m.id})">🗑️</span>`:'';let bc=m.is_broadcast?`[${m.tag}] `:'';h+=`<div class="bubble ${cls}">${bc}${txt}<small>${m.time} ${mine?'✓✓':''}</small>${del}</div>`});document.getElementById('msgs').innerHTML=h;window.scrollTo(0,document.body.scrollHeight)}
async function sendMsg(){let inp=document.getElementById('msg-input');let txt=inp.value.trim();if(!txt)return;let j=await api('/api/send',{my_uid:me.uid,to_uid:currentChat,text:txt});if(!j.success){alert(j.error);return}inp.value='';loadMsgs()}
async function delMsg(id){if(!confirm('Delete for everyone?'))return;await api('/api/delete-msg',{id:id,my_uid:me.uid});loadMsgs()}
async function doBroadcast(){let j=await api('/api/broadcast',{my_uid:me.uid,text:document.getElementById('bc-text').value,tag:document.getElementById('bc-tag').value||'Announcement'});alert(j.msg||j.error)}
function doLogout(){localStorage.clear();location.href='/'}
document.getElementById('msg-input')?.addEventListener('keypress',e=>{if(e.key==='Enter')sendMsg()});
window.onload=async()=>{let g=getQ('google_uid');let saved=localStorage.getItem('myqchat_uid');if(g){let j=await api('/api/me?uid='+g);if(j.success){me=j.user;localStorage.setItem('myqchat_uid',me.uid);afterLogin();return}}if(saved){let j=await api('/api/me?uid='+saved);if(j.success){me=j.user;afterLogin()}}};
</script></body></html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
