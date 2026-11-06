# MyQchat - Developed by QWNG - FINAL V2 - PART 1/4 - Backend Core
# Features: UID, Auth, Google, Groups, Status, Calls, Reactions, Star, Reply
import os, random, secrets, json, base64, time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MyQchat-QWNG-2026-V2-Secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///myqchat_final.db")
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Image max 2MB
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
db = SQLAlchemy(app)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT = "https://myqchat-1.onrender.com/auth/google/callback"
OWNER_EMAIL = "loyalwq@gmail.com"
OWNER_USERNAME = "LoyalWQ"

# ================= MODELS - PART 1 ONLY =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(20), unique=True)  # 8-digit Permanent UID - 9 crore combos
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(300))
    google_id = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    tick = db.Column(db.String(20), default="")  # L, Blue, Orange, Green, Scam
    bio = db.Column(db.String(200), default="Hey there! I am using MyQchat")
    avatar_color = db.Column(db.String(20), default="#075e54")
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    dark_mode = db.Column(db.Boolean, default=False)
    wallpaper = db.Column(db.String(20), default="default")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime)
    delete_requested_at = db.Column(db.DateTime)  # Permanent Delete ID + 15 days appeal
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    def to_dict(self):
        return {"id":self.id,"uid":self.uid,"username":self.username,"email":self.email,"name":self.name or self.username,"tick":self.tick,"is_admin":self.is_admin,"online":self.online,"last_seen":self.last_seen.strftime("%I:%M %p") if self.last_seen else "","bio":self.bio,"avatar_color":self.avatar_color,"dark_mode":self.dark_mode,"wallpaper":self.wallpaper}

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer)
    contact_uid = db.Column(db.String(20))
    contact_name = db.Column(db.String(100))
    is_fav = db.Column(db.Boolean, default=False)
    is_muted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer)
    sender_uid = db.Column(db.String(20))
    sender_name = db.Column(db.String(100))
    to_uid = db.Column(db.String(20))  # user UID or GROUP_123
    to_id = db.Column(db.Integer)
    text = db.Column(db.String(2000))
    msg_type = db.Column(db.String(20), default="text")  # text, image, voice, broadcast, system
    image_data = db.Column(db.Text)  # base64 360p image
    reply_to_id = db.Column(db.Integer)
    reply_to_text = db.Column(db.String(200))
    reaction = db.Column(db.String(20), default="")  # ❤️ 😂 👍 🔥 😮
    is_starred = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_broadcast = db.Column(db.Boolean, default=False)
    broadcast_tag = db.Column(db.String(20), default="")
    is_forwarded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gid = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100))
    created_by = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gid = db.Column(db.String(20))
    uid = db.Column(db.String(20))

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(20))
    name = db.Column(db.String(100))
    text = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caller_uid = db.Column(db.String(20))
    caller_name = db.Column(db.String(100))
    to_uid = db.Column(db.String(20))
    call_type = db.Column(db.String(20))  # voice, video
    status = db.Column(db.String(20), default="Missed")  # Missed, Answered, Outgoing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer)
    reported_uid = db.Column(db.String(20))
    reason = db.Column(db.String(20))
    detail = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer)
    blocked_uid = db.Column(db.String(20))

def gen_uid():
    while True:
        u = str(random.randint(10000000, 99999999))
        if not User.query.filter_by(uid=u).first(): return u

def gen_gid():
    return "GROUP_" + str(random.randint(1000, 9999))

def init_db():
    try:
        with app.app_context():
            db.create_all()
            db_url = os.environ.get("DATABASE_URL","")
            if "postgres" in db_url:
                try:
                    for col in ["google_id VARCHAR(100)","avatar_color VARCHAR(20)","dark_mode BOOLEAN DEFAULT FALSE","wallpaper VARCHAR(20)","delete_requested_at TIMESTAMP"]:
                        cname = col.split()[0]
                        db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS {cname} {col.split(" ",1)[1]}'))
                    db.session.commit()
                except Exception as e: print("PG migrate:", e); db.session.rollback()
            else:
                try:
                    cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
                    if "google_id" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN google_id VARCHAR(100)"))
                    if "avatar_color" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN avatar_color VARCHAR(20) DEFAULT '#075e54'"))
                    if "dark_mode" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN dark_mode BOOLEAN DEFAULT 0"))
                    if "wallpaper" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN wallpaper VARCHAR(20) DEFAULT 'default'"))
                    db.session.commit()
                    # Message new cols
                    mcols = [r[1] for r in db.session.execute(text("PRAGMA table_info(message)")).fetchall()]
                    if "reaction" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN reaction VARCHAR(20) DEFAULT ''"))
                    if "is_starred" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN is_starred BOOLEAN DEFAULT 0"))
                    if "reply_to_id" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN reply_to_id INTEGER"))
                    if "is_forwarded" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN is_forwarded BOOLEAN DEFAULT 0"))
                    if "image_data" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN image_data TEXT"))
                    db.session.commit()
                except Exception as e: print("SQLite migrate:", e); db.session.rollback()
            if not User.query.filter_by(username=OWNER_USERNAME).first():
                u = User(username=OWNER_USERNAME, email=OWNER_EMAIL, name="LoyalWQ Owner", is_admin=True, tick="L", uid=gen_uid(), avatar_color="#7b1fa2")
                u.set_password("AlwaysBeLoyalQ"); db.session.add(u); db.session.commit()
                print("Owner created UID:", u.uid)
    except Exception as e: print("init_db error:", e)
init_db()

# ---------- AUTH - PART 1 ----------
@app.route("/api/signup", methods=["POST"])
def signup():
    try:
        d = request.get_json(force=True)
        username=(d.get("username") or "").strip(); email=(d.get("email") or "").strip().lower(); password=d.get("password") or ""; name=(d.get("name") or username).strip()
        if not username or not email or not password: return jsonify({"success":False,"error":"All fields required"}),400
        if User.query.filter_by(username=username).first(): return jsonify({"success":False,"error":"Username already taken"}),400
        if User.query.filter_by(email=email).first(): return jsonify({"success":False,"error":"Email already used"}),400
        colors=["#075e54","#7b1fa2","#e91e63","#ff5722","#3f51b5","#009688"]
        u=User(username=username,email=email,name=name,uid=gen_uid(),avatar_color=random.choice(colors)); u.set_password(password)
        if email==OWNER_EMAIL: u.is_admin=True; u.tick="L"
        db.session.add(u); db.session.commit()
        return jsonify({"success":True,"user":u.to_dict()})
    except Exception as e: db.session.rollback(); return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/login", methods=["POST"])
def login():
    try:
        d=request.get_json(force=True); username=(d.get("username") or "").strip(); password=d.get("password") or ""
        u=User.query.filter_by(username=username).first() or User.query.filter_by(email=username.lower()).first()
        if not u or not u.check_password(password): return jsonify({"success":False,"error":"Wrong username or password"}),401
        if u.is_banned and u.banned_until and u.banned_until>datetime.utcnow(): return jsonify({"success":False,"error":"Banned till "+str(u.banned_until)}),403
        u.online=True; u.last_seen=datetime.utcnow(); db.session.commit(); session["uid"]=u.uid
        return jsonify({"success":True,"user":u.to_dict()})
    except Exception as e: return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/logout", methods=["POST"])
def logout():
    d=request.get_json(force=True,silent=True) or {}; u=User.query.filter_by(uid=d.get("uid")).first()
    if u: u.online=False; u.last_seen=datetime.utcnow(); db.session.commit()
    session.clear(); return jsonify({"success":True})

@app.route("/auth/google")
def google_auth():
    from urllib.parse import urlencode
    p={"client_id":GOOGLE_CLIENT_ID,"redirect_uri":GOOGLE_REDIRECT,"response_type":"code","scope":"openid email profile","access_type":"offline","prompt":"consent"}
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(p))

@app.route("/auth/google/callback")
def google_cb():
    code=request.args.get("code")
    if not code: return "Google login failed"
    try:
        import requests
        r=requests.post("https://oauth2.googleapis.com/token",data={"code":code,"client_id":GOOGLE_CLIENT_ID,"client_secret":GOOGLE_CLIENT_SECRET,"redirect_uri":GOOGLE_REDIRECT,"grant_type":"authorization_code"},timeout=15).json()
        id_token=r.get("id_token")
        if not id_token: return "Google token failed: "+str(r)
        from google.oauth2 import id_token as gid
        from google.auth.transport import requests as greq
        info=gid.verify_oauth2_token(id_token,greq.Request(),GOOGLE_CLIENT_ID)
        email=info.get("email"); name=info.get("name","User"); u=User.query.filter_by(email=email).first()
        if not u:
            base=email.split("@")[0].replace(".","")[:15]; uname=base; i=1
            while User.query.filter_by(username=uname).first(): i+=1; uname=f"{base}{i}"
            u=User(username=uname,email=email,name=name,uid=gen_uid(),google_id=info.get("sub")); u.set_password(secrets.token_hex(8))
            if email==OWNER_EMAIL: u.is_admin=True; u.tick="L"
            db.session.add(u); db.session.commit()
        u.online=True; db.session.commit(); session["uid"]=u.uid
        return redirect(f"/?google_uid={u.uid}")
    except Exception as e: return f"Google login error: {e}"

@app.route("/fix-db")
def fix_db():
    try: init_db(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@app.route("/cron/cleanup")
def cleanup():
    try:
        now=datetime.utcnow()
        Message.query.filter(Message.created_at < now - timedelta(days=2), Message.msg_type=="text").delete()
        Message.query.filter(Message.created_at < now - timedelta(hours=1), Message.msg_type=="image").delete()
        Message.query.filter(Message.created_at < now - timedelta(minutes=20), Message.msg_type=="voice").delete()
        db.session.commit(); return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})
@app.errorhandler(404)
def e404(e): return jsonify({"success":False,"error":"Not found"}),404
@app.errorhandler(500)
def e500(e): return jsonify({"success":False,"error":"Server error"}),500
# ================= PART 2 - CHAT + GROUP + STATUS + CALL + PROFILE APIs =================
# PART 1 me jo tha - Auth / Models - wo yahan nahi hai - Sirf naya hai

@app.route("/api/me")
def me_api():
    uid = request.args.get("uid")
    u = User.query.filter_by(uid=uid).first()
    if not u: return jsonify({"success":False}), 404
    # Online count
    online_count = User.query.filter_by(online=True).count()
    d = u.to_dict(); d["online_count"] = online_count
    return jsonify({"success":True,"user":d})

@app.route("/api/users")
def users_api():
    uid = request.args.get("uid","")
    q = request.args.get("q","").strip().lower()
    all_users = User.query.filter(User.uid != uid).order_by(User.created_at.desc()).all()
    out=[]
    for u in all_users:
        if q and q not in u.name.lower() and q not in u.username.lower(): continue
        last = Message.query.filter(((Message.sender_uid==uid)&(Message.to_uid==u.uid))|((Message.sender_uid==u.uid)&(Message.to_uid==uid))).order_by(Message.created_at.desc()).first()
        # Blocked check
        me_u = User.query.filter_by(uid=uid).first()
        is_blocked = False
        if me_u: is_blocked = Block.query.filter_by(blocker_id=me_u.id, blocked_uid=u.uid).first() is not None
        d = u.to_dict()
        if last:
            if last.is_deleted: d["last_msg"] = "🚫 This message was deleted"
            elif last.msg_type=="image": d["last_msg"] = ("You: 📷 Photo" if last.sender_uid==uid else "📷 Photo")
            elif last.msg_type=="voice": d["last_msg"] = ("You: 🎤 Voice" if last.sender_uid==uid else "🎤 Voice")
            else: d["last_msg"] = ("You: " + last.text if last.sender_uid==uid else last.text)
            d["last_time"] = last.created_at.strftime("%I:%M %p")
        else:
            d["last_msg"] = u.bio; d["last_time"] = ""
        d["is_blocked"] = is_blocked
        out.append(d)
    # Groups bhi list me dikhao
    groups = Group.query.all()
    for g in groups:
        members = [m.uid for m in GroupMember.query.filter_by(gid=g.gid).all()]
        if uid in members:
            last = Message.query.filter_by(to_uid=g.gid).order_by(Message.created_at.desc()).first()
            out.append({"id":g.id,"uid":g.gid,"username":g.gid,"name":"👥 "+g.name,"tick":"","is_admin":False,"online":False,"last_seen":"","bio":"Group","avatar_color":"#25d366","is_group":True,"last_msg":(last.text if last and not last.is_deleted else "No messages yet"),"last_time":last.created_at.strftime("%I:%M %p") if last else ""})
    return jsonify({"success":True,"users":out,"online_count":User.query.filter_by(online=True).count()})

@app.route("/api/search-uid")
def search_uid_api():
    q = request.args.get("q","").strip()
    u = User.query.filter_by(uid=q).first()
    if not u: return jsonify({"success":False,"error":"No user found with UID "+q})
    return jsonify({"success":True,"user":u.to_dict()})

@app.route("/api/add-contact", methods=["POST"])
def add_contact_api():
    d=request.get_json(force=True); owner=d.get("my_uid"); c_uid=d.get("contact_uid")
    ow=User.query.filter_by(uid=owner).first(); u=User.query.filter_by(uid=c_uid).first()
    if not u: return jsonify({"success":False,"error":"UID not found"}),404
    if Contact.query.filter_by(owner_id=ow.id, contact_uid=c_uid).first():
        return jsonify({"success":True,"msg":"Already in contacts"})
    db.session.add(Contact(owner_id=ow.id, contact_uid=c_uid, contact_name=u.name)); db.session.commit()
    return jsonify({"success":True,"msg":"Contact saved - Now you can send long messages"})

@app.route("/api/messages")
def get_msgs_api():
    my_uid=request.args.get("my_uid"); other_uid=request.args.get("other_uid"); search=request.args.get("search","").lower()
    if other_uid and other_uid.startswith("GROUP_"):
        msgs=Message.query.filter_by(to_uid=other_uid).order_by(Message.created_at.asc()).all()
    else:
        msgs=Message.query.filter(((Message.sender_uid==my_uid)&(Message.to_uid==other_uid))|((Message.sender_uid==other_uid)&(Message.to_uid==my_uid))).order_by(Message.created_at.asc()).all()
    out=[]
    for m in msgs:
        txt = "🚫 This message was deleted" if m.is_deleted else m.text
        if search and search not in txt.lower(): continue
        out.append({"id":m.id,"from":m.sender_uid,"from_name":m.sender_name,"text":txt,"type":m.msg_type,"image_data":m.image_data if m.msg_type=="image" and not m.is_deleted else "","is_deleted":m.is_deleted,"is_broadcast":m.is_broadcast,"tag":m.broadcast_tag,"reaction":m.reaction,"is_starred":m.is_starred,"is_forwarded":m.is_forwarded,"reply_to_text":m.reply_to_text or "","time":m.created_at.strftime("%I:%M %p"),"date":m.created_at.strftime("%d/%m/%Y")})
    return jsonify({"success":True,"messages":out})

@app.route("/api/send", methods=["POST"])
def send_api():
    try:
        d=request.get_json(force=True)
        my_uid=d.get("my_uid"); to_uid=d.get("to_uid"); text=(d.get("text") or "").strip()
        msg_type=d.get("type","text"); image_data=d.get("image_data","")
        reply_to_id=d.get("reply_to_id"); reply_to_text=d.get("reply_to_text","")
        if not text and not image_data: return jsonify({"success":False,"error":"Empty message"}),400
        if msg_type=="text" and len(text)>500: return jsonify({"success":False,"error":"Max 500 characters"}),400
        me_u=User.query.filter_by(uid=my_uid).first()
        is_group = to_uid.startswith("GROUP_") if to_uid else False
        to_u = None if is_group else User.query.filter_by(uid=to_uid).first()
        if not me_u: return jsonify({"success":False,"error":"You not found"}),404
        if not is_group and not to_u: return jsonify({"success":False,"error":"User not found"}),404
        # Block check
        if not is_group and to_u:
            if Block.query.filter_by(blocker_id=to_u.id, blocked_uid=my_uid).first():
                return jsonify({"success":False,"error":"You are blocked by this user"}),403
            if Block.query.filter_by(blocker_id=me_u.id, blocked_uid=to_uid).first():
                return jsonify({"success":False,"error":"You blocked this user. Unblock first"}),403
        # Unknown limit - only for 1-1, not group, not owner
        if not is_group and me_u.username!="LoyalWQ":
            is_contact = Contact.query.filter_by(owner_id=to_u.id, contact_uid=my_uid).first() or Contact.query.filter_by(owner_id=me_u.id, contact_uid=to_uid).first()
            if not is_contact:
                cnt=Message.query.filter_by(sender_uid=my_uid, to_uid=to_uid).count()
                if cnt>=2: return jsonify({"success":False,"error":"Save to contacts first - Unknown limit: 2 messages only"}),403
                if len(text)>30: return jsonify({"success":False,"error":"Unknown - Max 30 letters. Save contact to send longer"}),400
        # Cooldown 3 sec
        last=Message.query.filter_by(sender_uid=my_uid).order_by(Message.created_at.desc()).first()
        if last and (datetime.utcnow()-last.created_at).total_seconds()<2:
            return jsonify({"success":False,"error":"Wait a second..."}),429
        # 300 / hour
        one_hr_ago=datetime.utcnow()-timedelta(hours=1)
        cnt_hr=Message.query.filter(Message.sender_uid==my_uid, Message.created_at>=one_hr_ago).count()
        if cnt_hr>=300: return jsonify({"success":False,"error":"Hourly limit 300 reached"}),429
        # Image limit 2/hour
        if msg_type=="image":
            cnt_img=Message.query.filter(Message.sender_uid==my_uid, Message.msg_type=="image", Message.created_at>=one_hr_ago).count()
            if cnt_img>=2: return jsonify({"success":False,"error":"Image limit: 2 per hour"}),429
        m=Message(sender_id=me_u.id, sender_uid=my_uid, sender_name=me_u.name, to_uid=to_uid, to_id=to_u.id if to_u else 0, text=text or ("📷 Photo" if msg_type=="image" else "🎤 Voice"), msg_type=msg_type, image_data=image_data, reply_to_id=reply_to_id, reply_to_text=reply_to_text)
        db.session.add(m); db.session.commit()
        return jsonify({"success":True,"id":m.id})
    except Exception as e:
        db.session.rollback(); return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/delete-msg", methods=["POST"])
def del_msg_api():
    d=request.get_json(force=True); mid=d.get("id"); my_uid=d.get("my_uid")
    m=Message.query.get(mid)
    if not m: return jsonify({"success":False}),404
    if m.sender_uid!=my_uid: return jsonify({"success":False,"error":"Only sender can delete"}),403
    m.is_deleted=True; db.session.commit()
    return jsonify({"success":True,"msg":"Deleted for everyone"})

@app.route("/api/react", methods=["POST"])
def react_api():
    d=request.get_json(force=True); m=Message.query.get(d.get("id"))
    if not m: return jsonify({"success":False}),404
    m.reaction=d.get("reaction",""); db.session.commit()
    return jsonify({"success":True})

@app.route("/api/star", methods=["POST"])
def star_api():
    d=request.get_json(force=True); m=Message.query.get(d.get("id"))
    if not m: return jsonify({"success":False}),404
    m.is_starred=not m.is_starred; db.session.commit()
    return jsonify({"success":True,"starred":m.is_starred})

@app.route("/api/forward", methods=["POST"])
def forward_api():
    d=request.get_json(force=True); orig=Message.query.get(d.get("id")); me_u=User.query.filter_by(uid=d.get("my_uid")).first(); to_uid=d.get("to_uid")
    if not orig or not me_u: return jsonify({"success":False}),404
    to_u=User.query.filter_by(uid=to_uid).first()
    m=Message(sender_id=me_u.id, sender_uid=me_u.uid, sender_name=me_u.name, to_uid=to_uid, to_id=to_u.id if to_u else 0, text=orig.text, msg_type=orig.msg_type, image_data=orig.image_data, is_forwarded=True)
    db.session.add(m); db.session.commit(); return jsonify({"success":True})

@app.route("/api/report", methods=["POST"])
def report_api():
    d=request.get_json(force=True); detail=(d.get("detail") or "")[:400]
    reporter=User.query.filter_by(uid=d.get("my_uid")).first()
    db.session.add(Report(reporter_id=reporter.id if reporter else 0, reported_uid=d.get("reported_uid"), reason=d.get("reason"), detail=detail)); db.session.commit()
    return jsonify({"success":True,"msg":"Report sent to Admin. Admin will check in 24 hrs."})

@app.route("/api/block", methods=["POST"])
def block_api():
    d=request.get_json(force=True); me_u=User.query.filter_by(uid=d.get("my_uid")).first(); target=d.get("target_uid"); action=d.get("action","block")
    if action=="unblock":
        Block.query.filter_by(blocker_id=me_u.id, blocked_uid=target).delete(); db.session.commit(); return jsonify({"success":True,"msg":"Unblocked"})
    if not Block.query.filter_by(blocker_id=me_u.id, blocked_uid=target).first():
        db.session.add(Block(blocker_id=me_u.id, blocked_uid=target)); db.session.commit()
    return jsonify({"success":True,"msg":"User blocked"})

@app.route("/api/clear-chat", methods=["POST"])
def clear_chat_api():
    d=request.get_json(force=True); my_uid=d.get("my_uid"); other=d.get("other_uid")
    if other.startswith("GROUP_"):
        Message.query.filter_by(to_uid=other).delete()
    else:
        Message.query.filter(((Message.sender_uid==my_uid)&(Message.to_uid==other))|((Message.sender_uid==other)&(Message.to_uid==my_uid))).delete()
    db.session.commit(); return jsonify({"success":True,"msg":"Chat cleared"})

@app.route("/api/broadcast", methods=["POST"])
def broadcast_api():
    d=request.get_json(force=True); me_u=User.query.filter_by(uid=d.get("my_uid")).first()
    if not me_u or not me_u.is_admin: return jsonify({"success":False,"error":"Admin only"}),403
    users=User.query.all()
    for u in users:
        if u.uid==me_u.uid: continue
        db.session.add(Message(sender_id=me_u.id, sender_uid=me_u.uid, sender_name="QWNG Bot", to_uid=u.uid, to_id=u.id, text=d.get("text",""), msg_type="text", is_broadcast=True, broadcast_tag=d.get("tag","Announcement")))
    db.session.commit(); return jsonify({"success":True,"msg":"Broadcast sent to all users"})

@app.route("/api/groups", methods=["POST"])
def create_group_api():
    d=request.get_json(force=True); me_u=User.query.filter_by(uid=d.get("my_uid")).first()
    gid=gen_gid(); g=Group(gid=gid, name=d.get("name","My Group"), created_by=me_u.uid if me_u else ""); db.session.add(g)
    db.session.add(GroupMember(gid=gid, uid=me_u.uid))
    for uid in d.get("members",[]):
        if not GroupMember.query.filter_by(gid=gid, uid=uid).first():
            db.session.add(GroupMember(gid=gid, uid=uid))
    db.session.commit(); return jsonify({"success":True,"gid":gid,"msg":"Group created"})

@app.route("/api/status", methods=["GET","POST"])
def status_api():
    if request.method=="POST":
        d=request.get_json(force=True); u=User.query.filter_by(uid=d.get("my_uid")).first()
        db.session.add(Status(uid=d.get("my_uid"), name=u.name if u else "", text=d.get("text","")[:300])); db.session.commit()
        return jsonify({"success":True,"msg":"Status posted"})
    sts=Status.query.filter(Status.created_at >= datetime.utcnow()-timedelta(hours=24)).order_by(Status.created_at.desc()).all()
    return jsonify({"success":True,"status":[{"id":s.id,"uid":s.uid,"name":s.name,"text":s.text,"time":s.created_at.strftime("%I:%M %p")} for s in sts]})

@app.route("/api/call", methods=["POST"])
def call_api():
    d=request.get_json(force=True); me_u=User.query.filter_by(uid=d.get("my_uid")).first()
    db.session.add(CallLog(caller_uid=d.get("my_uid"), caller_name=me_u.name if me_u else "", to_uid=d.get("to_uid"), call_type=d.get("type","voice"), status="Outgoing"))
    db.session.commit(); return jsonify({"success":True,"msg":"Calling... - Voice/Video call UI will open"})

@app.route("/api/calls")
def calls_api():
    uid=request.args.get("uid"); calls=CallLog.query.filter((CallLog.caller_uid==uid)|(CallLog.to_uid==uid)).order_by(CallLog.created_at.desc()).limit(20).all()
    return jsonify({"success":True,"calls":[{"id":c.id,"from":c.caller_name,"to":c.to_uid,"type":c.call_type,"status":c.status,"time":c.created_at.strftime("%d/%m %I:%M %p")} for c in calls]})

@app.route("/api/profile-update", methods=["POST"])
def profile_api():
    d=request.get_json(force=True); u=User.query.filter_by(uid=d.get("uid")).first()
    if not u: return jsonify({"success":False}),404
    if d.get("name"): u.name=d.get("name")[:50]
    if d.get("bio") is not None: u.bio=d.get("bio")[:200]
    if d.get("avatar_color"): u.avatar_color=d.get("avatar_color")
    if d.get("dark_mode") is not None: u.dark_mode=bool(d.get("dark_mode"))
    if d.get("wallpaper"): u.wallpaper=d.get("wallpaper")
    db.session.commit(); return jsonify({"success":True,"user":u.to_dict()})

@app.route("/api/delete-account", methods=["POST"])
def delete_acc_api():
    d=request.get_json(force=True); u=User.query.filter_by(uid=d.get("uid")).first()
    if not u: return jsonify({"success":False}),404
    u.delete_requested_at=datetime.utcnow(); db.session.commit()
    return jsonify({"success":True,"msg":"Delete request received. Your ID will be deleted in 15 days. Contact Admin to appeal within 15 days."})

@app.route("/api/terms")
def terms_api():
    return jsonify({"title":"Terms","text":"13+ only. Owner can view chats for moderation. Be respectful. No spam, no scam, no harassment."})

@app.route("/")
def home_api():
    return FRONTEND
# ================= PART 3 - FRONTEND HTML + CSS - 【entity-WhatsApp¦canonical_name=WhatsApp】 Like =================
# PART 4 me JS aayega - Isliye yahan FRONTEND_HEAD hai - FRONTEND Part 4 me banega
FRONTEND_HEAD = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyQchat - Developed by QWNG</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:Arial,sans-serif}
body{background:#efeae2;color:#111}
body.dark{background:#0b141a;color:#e9edef}
body.dark .card,body.dark .chat-item,body.dark .bubble.theirs{background:#202c33;color:#e9edef}
body.dark .search,body.dark .inputbar input{background:#2a3942;color:#fff}
.top{background:#075e54;color:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:20}
.top h1{font-size:23px}.top small{font-size:11px;opacity:.9}
.page{display:none}.page.active{display:block}
.card{background:#fff;margin:12px;padding:16px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.12)}
input,textarea,select{width:100%;padding:13px;margin:7px 0;border:1px solid #ddd;border-radius:10px;font-size:15px;outline:none}
button{padding:11px 16px;border:none;border-radius:22px;font-size:15px;cursor:pointer}
.btn-green{background:#00a884;color:#fff;width:100%;margin-top:8px;font-weight:bold}
.btn-black{background:#111;color:#fff}.btn-grey{background:#eee;color:#111}
.btn-small{padding:7px 12px;font-size:13px}
.search{margin:12px;background:#fff;border-radius:24px;padding:8px 12px;display:flex;gap:8px;align-items:center}
.search input{border:none;padding:8px;margin:0}
.tabs{display:flex;gap:8px;padding:0 12px;overflow-x:auto}.tabs button{background:#fff;border:1px solid #ddd;padding:7px 14px;border-radius:20px;white-space:nowrap}
.tabs button.on{background:#d9fdd3;border-color:#00a884}
.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:#fff;display:flex;justify-content:space-around;padding:10px 0;border-top:1px solid #eee;z-index:20}
.bottom-nav div{text-align:center;font-size:12px;cursor:pointer;color:#666}.bottom-nav div.on{color:#00a884;font-weight:bold}
.chat-item{background:#fff;display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid #f0f0f0;cursor:pointer;align-items:center}
.avatar{width:50px;height:50px;border-radius:50%;color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:bold;flex-shrink:0}
.chat-item b{font-size:16px}.chat-item p{font-size:13px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:210px}
.time{font-size:11px;color:#666;margin-left:auto;white-space:nowrap}.badge{background:#25d366;color:#fff;border-radius:50%;min-width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:12px;padding:0 5px}
.tick{color:#53bdeb;font-weight:bold}.tick-L{color:#ff9800;font-weight:bold}.tick-scam{color:#ff0000;font-weight:bold}
.chat-head{background:#075e54;color:#fff;padding:10px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:20}
.chat-head .back{font-size:26px;cursor:pointer}
.msgs{padding:12px;padding-bottom:140px;min-height:72vh;background-image:url('');}
.bubble{max-width:82%;padding:8px 10px;border-radius:12px;margin:6px 0;font-size:15px;position:relative;word-wrap:break-word;box-shadow:0 1px 2px rgba(0,0,0,.1);clear:both}
.bubble.mine{background:#d9fdd3;float:right;border-top-right-radius:2px}
.bubble.theirs{background:#fff;float:left;border-top-left-radius:2px}
.bubble small{font-size:11px;color:#555;float:right;margin:8px 0 0 8px}
.bubble .reply-box{background:rgba(0,0,0,.06);border-left:3px solid #00a884;padding:6px 8px;border-radius:6px;font-size:13px;margin-bottom:6px}
.bubble .fwd{font-size:11px;color:#888;font-style:italic}
.bubble img{max-width:100%;border-radius:8px;margin-top:4px}
.deleted{font-style:italic;color:#777}
.msg-actions{display:flex;gap:8px;margin-top:4px;font-size:12px}.msg-actions span{cursor:pointer;background:rgba(0,0,0,.05);padding:3px 7px;border-radius:12px}
.inputbar{position:fixed;bottom:52px;left:0;right:0;background:#efeae2;padding:8px;display:flex;gap:6px;align-items:center;z-index:20}
.inputbar .box{flex:1;background:#fff;border-radius:24px;display:flex;align-items:center;padding:4px 10px}
.inputbar .box input{border:none;padding:10px;margin:0}
.icon-btn{background:#fff;border:1px solid #eee;border-radius:50%;width:42px;height:42px;font-size:19px;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0}
.sendbtn{background:#00a884;color:#fff;border-radius:50%;width:48px;height:48px;font-size:22px;border:none;cursor:pointer;flex-shrink:0}
.emoji-bar{display:none;background:#fff;padding:8px;border-radius:12px;margin:8px;flex-wrap:wrap;gap:6px}.emoji-bar span{font-size:22px;cursor:pointer}
.reply-preview{display:none;background:#fff;margin:8px;padding:8px 10px;border-left:4px solid #00a884;border-radius:8px;font-size:13px}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;align-items:center;justify-content:center}
.modal .box{background:#fff;padding:18px;border-radius:14px;width:92%;max-width:420px;max-height:85vh;overflow:auto}
.footer{text-align:center;font-size:12px;color:#888;padding:14px;padding-bottom:70px}
.call-banner{display:none;background:#25d366;color:#fff;padding:12px;text-align:center;position:sticky;top:0;z-index:30}
</style></head><body>
<div class="call-banner" id="call-banner">📞 Calling... <button class="btn-small" onclick="endCall()">End Call</button></div>

<!-- PAGE 1 - LOGIN -->
<div id="page-login" class="page active">
<div class="top"><div><h1>MyQchat</h1><small>Developed by QWNG</small></div><span>🌙</span></div>
<div class="card"><h2>Welcome to MyQchat</h2><p style="color:#666;margin:8px 0;font-size:14px">Chat with anyone using 8-digit UID. No phone number needed. Global chat app.</p>
<input id="su_name" placeholder="Your Name"><input id="su_username" placeholder="Username"><input id="su_email" placeholder="Email"><input id="su_pass" type="password" placeholder="Password">
<button class="btn-green" onclick="doSignup()">Create Account</button>
<hr style="margin:14px 0"><input id="li_user" placeholder="Username or Email"><input id="li_pass" type="password" placeholder="Password">
<button class="btn-green" onclick="doLogin()">Login</button>
<button class="btn-grey" style="width:100%;margin-top:8px" onclick="location.href='/auth/google'">G - Sign in with Google</button>
<p id="auth-msg" style="color:#075e54;margin-top:10px"></p>
<p style="font-size:12px;color:#888;margin-top:8px">By continuing you agree to Terms - 13+ only. Owner can view chats for moderation.</p></div>
<div class="footer">Developed by QWNG - 2026</div></div>

<!-- PAGE 2 - CHATS LIST -->
<div id="page-chats" class="page">
<div class="top"><div><h1>MyQchat</h1><small id="my-info">Loading...</small></div><div style="display:flex;gap:14px;font-size:20px"><span onclick="showPage('page-status')">🟢</span><span onclick="showPage('page-profile')">👤</span><span onclick="showPage('page-settings')">⚙️</span></div></div>
<div class="search"><span>🔍</span><input id="search-uid" placeholder="Search by 8-digit UID or Name..."><button class="btn-black btn-small" onclick="searchUID()">Search</button></div>
<div id="search-result"></div>
<div class="tabs"><button class="on" onclick="filterTab(this,'all')">All</button><button onclick="filterTab(this,'unread')">Unread</button><button onclick="filterTab(this,'fav')">Favourites</button><button onclick="showPage('page-groups')">Groups</button><button onclick="showPage('page-calls')">Calls</button></div>
<div id="chat-list" style="margin-top:10px"></div>
<div class="card" id="admin-box" style="display:none"><b>🔊 Admin Broadcast - QWNG Bot</b><input id="bc-text" placeholder="Announcement message"><input id="bc-tag" placeholder="Tag - Announcement / Warning / Ad"><button class="btn-green" onclick="doBroadcast()">Send to All Users</button></div>
<div class="card"><b>🛍️ Shop</b><p style="font-size:13px;color:#555">Shop inside app - Mail: qwngofficial@gmail.com</p><b>📢 Ad</b><p style="font-size:13px;color:#555">Single Local Ad - One ad at a time</p></div>
<div style="height:60px"></div></div>

<!-- PAGE 3 - CHAT SCREEN - FIXED BUBBLES -->
<div id="page-chat" class="page">
<div class="chat-head"><span class="back" onclick="backToChats()">←</span><div class="avatar" id="chat-avatar">?</div><div style="flex:1"><b id="chat-name">Name</b><br><span id="chat-uid" style="font-size:12px"></span> <span id="chat-online" style="font-size:12px"></span></div><span style="font-size:22px;cursor:pointer" onclick="startCall('video')">📹</span><span style="font-size:22px;cursor:pointer" onclick="startCall('voice')">📞</span><span style="font-size:22px;cursor:pointer" onclick="openChatMenu()">⋮</span></div>
<div style="background:#fff;padding:6px 12px;display:flex;gap:8px"><input id="chat-search" placeholder="Search in this chat..." style="margin:0;padding:8px"><button class="btn-black btn-small" onclick="loadMsgs()">Search</button></div>
<div class="msgs" id="msgs"></div>
<div class="reply-preview" id="reply-preview"></div>
<div class="emoji-bar" id="emoji-bar"></div>
<div class="inputbar"><div class="box"><span style="font-size:22px;cursor:pointer" onclick="toggleEmoji()">😀</span><input id="msg-input" placeholder="Message" maxlength="500"><span style="font-size:20px;cursor:pointer" onclick="document.getElementById('img-input').click()">📎</span><span style="font-size:20px;cursor:pointer" onclick="document.getElementById('img-input').click()">📷</span></div><button class="icon-btn" onclick="sendVoice()">🎤</button><button class="sendbtn" onclick="sendMsg()">➤</button></div>
<input type="file" id="img-input" accept="image/*" style="display:none" onchange="sendImage(this)"></div>

<!-- PAGE 4 - PROFILE -->
<div id="page-profile" class="page"><div class="top"><span style="font-size:24px;cursor:pointer" onclick="showPage('page-chats')">←</span><h1>Profile</h1><span></span></div>
<div class="card" style="text-align:center"><div class="avatar" id="prof-avatar" style="width:80px;height:80px;font-size:36px;margin:0 auto">?</div><h2 id="prof-name" style="margin-top:10px"></h2><p id="prof-uid" style="color:#666"></p><p id="prof-bio"></p></div>
<div class="card"><b>Edit Profile</b><input id="edit-name" placeholder="Name"><input id="edit-bio" placeholder="Bio - Hey there! I am using MyQchat"><select id="edit-color"><option value="#075e54">Green</option><option value="#7b1fa2">Purple</option><option value="#e91e63">Pink</option><option value="#ff5722">Orange</option><option value="#3f51b5">Blue</option></select><button class="btn-green" onclick="saveProfile()">Save Profile</button></div>
<div class="card"><b>Starred Messages</b><div id="starred-list">No starred yet</div></div></div>

<!-- PAGE 5 - SETTINGS -->
<div id="page-settings" class="page"><div class="top"><span style="font-size:24px;cursor:pointer" onclick="showPage('page-chats')">←</span><h1>Settings</h1><span></span></div>
<div class="card"><b>Appearance</b><p><label><input type="checkbox" id="dark-toggle" onchange="toggleDark()"> Dark Mode</label></p><p>Wallpaper: <select id="wall-select" onchange="changeWall()"><option value="default">Default</option><option value="green">Green</option><option value="purple">Purple</option></select></p></div>
<div class="card"><b>Account</b><p id="settings-uid"></p><button class="btn-grey" style="width:100%" onclick="doLogout()">Logout</button><button class="btn-grey" style="width:100%;margin-top:8px;color:red" onclick="requestDelete()">Delete My ID - 15 days appeal</button></div>
<div class="card"><b>Help</b><p>Terms - 13+ only. Owner can view chats for moderation.</p><p>Contact Admin: loyalwq@gmail.com</p></div></div>

<!-- PAGE 6 - STATUS -->
<div id="page-status" class="page"><div class="top"><span style="font-size:24px;cursor:pointer" onclick="showPage('page-chats')">←</span><h1>Status</h1><span></span></div>
<div class="card"><input id="status-text" placeholder="Write status - e.g. Busy, At work..."><button class="btn-green" onclick="postStatus()">Post Status</button></div><div id="status-list"></div></div>

<!-- PAGE 7 - GROUPS -->
<div id="page-groups" class="page"><div class="top"><span style="font-size:24px;cursor:pointer" onclick="showPage('page-chats')">←</span><h1>Groups</h1><span></span></div>
<div class="card"><b>Create Group</b><input id="group-name" placeholder="Group Name"><input id="group-members" placeholder="Members UID - comma se - e.g. 12345678,87654321"><button class="btn-green" onclick="createGroup()">Create Group</button></div><div id="group-list"></div></div>

<!-- PAGE 8 - CALLS -->
<div id="page-calls" class="page"><div class="top"><span style="font-size:24px;cursor:pointer" onclick="showPage('page-chats')">←</span><h1>Calls</h1><span></span></div><div id="calls-list"></div></div>

<!-- MODAL - CHAT MENU -->
<div class="modal" id="chat-modal"><div class="box"><h3 id="modal-title">Chat Options</h3><button class="btn-grey" style="width:100%;margin-top:8px" onclick="clearChat()">Clear Chat</button><button class="btn-grey" style="width:100%;margin-top:8px" onclick="blockUser()">Block User</button><button class="btn-grey" style="width:100%;margin-top:8px" onclick="openReport()">Report User</button><button class="btn-black" style="width:100%;margin-top:8px" onclick="closeModal()">Close
# ================= PART 4 - JS + FINAL ASSEMBLY - Sab Buttons Kaam Karenge =================
JS_PART = r"""
<script>
let me=null, currentChat=null, currentChatUser=null, replyToId=null, replyToText="", forwardId=null, filter="all";
function showPage(id){document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.getElementById(id).classList.add('active');if(id==='page-chats')loadChats();if(id==='page-status')loadStatus();if(id==='page-calls')loadCalls();if(id==='page-profile')loadProfile();window.scrollTo(0,0)}
function getQ(n){return new URLSearchParams(location.search).get(n)}
async function api(url,body){let r=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});try{return await r.json()}catch(e){return {success:false,error:'Server busy - wait 30 sec'}}}
function tickHtml(t){if(!t)return '';if(t==='L')return ' <span class="tick-L">L ✓</span>';if(t==='Scam')return ' <span class="tick-scam">Scam ⚠️</span>';return ` <span class="tick">${t} ✓</span>`}
async function doSignup(){let b={name:document.getElementById('su_name').value,username:document.getElementById('su_username').value,email:document.getElementById('su_email').value,password:document.getElementById('su_pass').value};let j=await api('/api/signup',b);document.getElementById('auth-msg').innerText=j.success?'Account created! Now Login - Your UID: '+j.user.uid:j.error;if(j.success)document.getElementById('li_user').value=b.username}
async function doLogin(){let b={username:document.getElementById('li_user').value,password:document.getElementById('li_pass').value};let j=await api('/api/login',b);if(!j.success){document.getElementById('auth-msg').innerText=j.error;return}me=j.user;localStorage.setItem('myqchat_uid',me.uid);afterLogin()}
function afterLogin(){document.getElementById('my-info').innerText='Hi, '+me.name+' | UID: '+me.uid+tickHtml(me.tick);if(me.is_admin)document.getElementById('admin-box').style.display='block';if(me.dark_mode)document.body.classList.add('dark');showPage('page-chats')}
async function loadChats(){if(!me)return;let q=document.getElementById('search-uid')?document.getElementById('search-uid').value:'';let j=await api('/api/users?uid='+me.uid+'&q='+encodeURIComponent(q));if(!j.success)return;let h='';j.users.forEach(u=>{if(filter==='unread'&&!u.unread)return;let letter=(u.name||'?')[0].toUpperCase();let bg=u.avatar_color||'#075e54';h+=`<div class="chat-item" onclick="openChat('${u.uid}','${u.name.replace(/'/g,'')}')"><div class="avatar" style="background:${bg}">${letter}</div><div style="flex:1"><b>${u.name}${tickHtml(u.tick)}</b><p>${u.last_msg||''}</p></div><span class="time">${u.last_time||''}</span></div>`});document.getElementById('chat-list').innerHTML=h||'<div class="card">No users yet. Share your UID with friends. Search UID above.</div>'}
function filterTab(el,f){document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('on'));el.classList.add('on');filter=f;loadChats()}
async function searchUID(){let q=document.getElementById('search-uid').value.trim();if(!q){loadChats();return}if(q.length===8&&!isNaN(q)){let j=await api('/api/search-uid?q='+q);document.getElementById('search-result').innerHTML=j.success?`<div class="card"><b>${j.user.name} (@${j.user.username}) - UID: ${j.user.uid} ${tickHtml(j.user.tick)}</b><br><span style="font-size:13px">${j.user.bio}</span><br><button class="btn-green" onclick="saveContact('${j.user.uid}')">Save to Contacts</button> <button class="btn-black" onclick="openChat('${j.user.uid}','${j.user.name}')">Chat</button></div>`:`<div class="card">${j.error}</div>`}else{loadChats()}}
async function saveContact(uid){let j=await api('/api/add-contact',{my_uid:me.uid,contact_uid:uid});alert(j.msg||j.error);loadChats()}
async function openChat(uid,name){currentChat=uid;currentChatUser=name;document.getElementById('chat-name').innerText=name;document.getElementById('chat-uid').innerText='UID: '+uid;document.getElementById('chat-avatar').innerText=name[0].toUpperCase();showPage('page-chat');loadMsgs()}
function backToChats(){currentChat=null;showPage('page-chats')}
async function loadMsgs(){if(!currentChat)return;let s=document.getElementById('chat-search').value||'';let j=await api(`/api/messages?my_uid=${me.uid}&other_uid=${currentChat}&search=${encodeURIComponent(s)}`);let h='';let lastDate='';j.messages.forEach(m=>{if(m.date!==lastDate){h+=`<div style="text-align:center;clear:both;padding:8px"><span style="background:#fff;padding:5px 12px;border-radius:10px;font-size:12px">${m.date}</span></div>`;lastDate=m.date}let mine=m.from===me.uid;let cls=mine?'mine':'theirs';let txt=m.is_deleted?'🚫 This message was deleted':m.text;let reply=m.reply_to_text?`<div class="reply-box">↩️ ${m.reply_to_text}</div>`:'';let fwd=m.is_forwarded?'<div class="fwd">Forwarded</div>':'';let bc=m.is_broadcast?`[${m.tag}] `:'';let img=m.image_data?`<br><img src="${m.image_data}">`:'';let react=m.reaction?`<div>${m.reaction}</div>`:'';let star=m.is_starred?'⭐ ':'';let del=mine&&!m.is_deleted?`<span onclick="delMsg(${m.id})">🗑️ Delete</span>`:'';h+=`<div class="bubble ${cls}">${fwd}${reply}${bc}${star}${txt}${img}${react}<small>${m.time} ${mine?'✓✓':''}</small><div class="msg-actions"><span onclick="setReply(${m.id},'${txt.replace(/'/g,'')}')">↩️ Reply</span><span onclick="openForward(${m.id})">➡️ Forward</span><span onclick="reactMsg(${m.id},'❤️')">❤️</span><span onclick="reactMsg(${m.id},'😂')">😂</span><span onclick="starMsg(${m.id})">⭐ Star</span>${del}</div></div><div style="clear:both"></div>`});document.getElementById('msgs').innerHTML=h||'<div class="card">No messages yet. Say Hi!</div>';window.scrollTo(0,document.body.scrollHeight)}
async function sendMsg(){let inp=document.getElementById('msg-input');let txt=inp.value.trim();if(!txt)return;let j=await api('/api/send',{my_uid:me.uid,to_uid:currentChat,text:txt,reply_to_id:replyToId,reply_to_text:replyToText});if(!j.success){alert(j.error);return}inp.value='';replyToId=null;replyToText='';document.getElementById('reply-preview').style.display='none';loadMsgs()}
function setReply(id,txt){replyToId=id;replyToText=txt.substring(0,60);let p=document.getElementById('reply-preview');p.style.display='block';p.innerHTML='Replying to: '+replyToText+' <span onclick="cancelReply()" style="float:right;cursor:pointer">✖</span>';document.getElementById('msg-input').focus()}
function cancelReply(){replyToId=null;replyToText='';document.getElementById('reply-preview').style.display='none'}
async function delMsg(id){if(!confirm('Delete for everyone?'))return;await api('/api/delete-msg',{id:id,my_uid:me.uid});loadMsgs()}
async function reactMsg(id,em){await api('/api/react',{id:id,reaction:em});loadMsgs()}
async function starMsg(id){let j=await api('/api/star',{id:id});alert(j.starred?'Starred ⭐':'Unstarred');loadMsgs()}
function openForward(id){forwardId=id;document.getElementById('forward-modal').style.display='flex'}
function closeForward(){document.getElementById('forward-modal').style.display='none'}
async function doForward(){let to=document.getElementById('forward-uid').value;let j=await api('/api/forward',{id:forwardId,my_uid:me.uid,to_uid:to});alert(j.success?'Forwarded':'Failed');closeForward()}
function toggleEmoji(){let e=document.getElementById('emoji-bar');if(e.style.display==='flex'){e.style.display='none';return}e.style.display='flex';e.innerHTML='';['😀','😂','❤️','👍','🔥','😮','😢','🙏','🎉','😡','👋','🥳','😍','🤔','💯','✨'].forEach(em=>{let s=document.createElement('span');s.innerText=em;s.onclick=()=>{document.getElementById('msg-input').value+=em};e.appendChild(s)})}
async function sendImage(input){let f=input.files[0];if(!f)return;if(f.size>500000){alert('Image too big - Use small image');return}let r=new FileReader();r.onload=async()=>{let j=await api('/api/send',{my_uid:me.uid,to_uid:currentChat,text:'📷 Photo',type:'image',image_data:r.result});if(!j.success)alert(j.error);else loadMsgs()};r.readAsDataURL(f)}
async function sendVoice(){if(!confirm('Send 15 sec Voice Note? (Demo - Voice will show as 🎤 Voice message)'))return;let j=await api('/api/send',{my_uid:me.uid,to_uid:currentChat,text:'🎤 Voice Note - 15 sec',type:'voice'});if(!j.success)alert(j.error);else loadMsgs()}
async function doBroadcast(){let j=await api('/api/broadcast',{my_uid:me.uid,text:document.getElementById('bc-text').value,tag:document.getElementById('bc-tag').value||'Announcement'});alert(j.msg||j.error)}
function doLogout(){api('/api/logout',{uid:me?me.uid:''});localStorage.clear();location.href='/'}
function startCall(type){document.getElementById('call-banner').style.display='block';api('/api/call',{my_uid:me.uid,to_uid:currentChat,type:type});setTimeout(()=>{alert(type==='video'?'Video Call UI - Video call will connect soon':'Voice Call UI - Voice call will connect soon')},500)}
function endCall(){document.getElementById('call-banner').style.display='none'}
function openChatMenu(){document.getElementById('modal-title').innerText=currentChatUser+' - Options';document.getElementById('chat-modal').style.display='flex'}
function closeModal(){document.getElementById('chat-modal').style.display='none';document.getElementById('report-box').style.display='none'}
async function clearChat(){if(!confirm('Clear all messages?'))return;await api('/api/clear-chat',{my_uid:me.uid,other_uid:currentChat});closeModal();loadMsgs()}
async function blockUser(){await api('/api/block',{my_uid:me.uid,target_uid:currentChat,action:'block'});alert('User blocked');closeModal();backToChats()}
function openReport(){document.getElementById('report-box').style.display='block'}
async function sendReport(){let j=await api('/api/report',{my_uid:me.uid,reported_uid:currentChat,reason:document.getElementById('report-reason').value,detail:document.getElementById('report-detail').value});alert(j.msg);closeModal()}
async function loadProfile(){if(!me)return;document.getElementById('prof-avatar').innerText=me.name[0].toUpperCase();document.getElementById('prof-avatar').style.background=me.avatar_color;document.getElementById('prof-name').innerText=me.name+tickHtml(me.tick);document.getElementById('prof-uid').innerText='UID: '+me.uid+' | @'+me.username;document.getElementById('prof-bio').innerText=me.bio;document.getElementById('edit-name').value=me.name;document.getElementById('edit-bio').value=me.bio;document.getElementById('settings-uid').innerText='UID: '+me.uid+' | Email: '+me.email}
async function saveProfile(){let j=await api('/api/profile-update',{uid:me.uid,name:document.getElementById('edit-name').value,bio:document.getElementById('edit-bio').value,avatar_color:document.getElementById('edit-color').value});if(j.success){me=j.user;localStorage.setItem('myqchat_uid',me.uid);alert('Profile saved');afterLogin()}else alert('Failed')}
async function toggleDark(){let on=document.getElementById('dark-toggle').checked;document.body.classList.toggle('dark',on);await api('/api/profile-update',{uid:me.uid,dark_mode:on})}
async function changeWall(){let w=document.getElementById('wall-select').value;await api('/api/profile-update',{uid:me.uid,wallpaper:w});alert('Wallpaper: '+w)}
async function requestDelete(){if(!confirm('Delete ID in 15 days? You can appeal in 15 days.'))return;let j=await api('/api/delete-account',{uid:me.uid});alert(j.msg)}
async function postStatus(){let j=await api('/api/status',{my_uid:me.uid,text:document.getElementById('status-text').value});alert(j.msg||'Posted');loadStatus()}
async function loadStatus
