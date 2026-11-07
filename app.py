# MyQchat - Developed by QWNG - FINAL V3 - PART 1/6 - Backend Core
# Username + Password Only - Email Optional in Settings - Tick Request - Admin in Settings
import os, random, secrets, json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MyQchat-QWNG-V3-Secret-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///myqchat_final.db")
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
db = SQLAlchemy(app)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT = "https://myqchat-1.onrender.com/auth/google/callback"
OWNER_USERNAME = "LoyalWQ"

# ================= MODELS - PART 1 ONLY =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(20), unique=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(300))
    google_id = db.Column(db.String(100))
    # Email - OPTIONAL - Only for recovery - Added in Settings after login
    recovery_email = db.Column(db.String(120))
    email = db.Column(db.String(120))  # Kept for old users - New users will have empty
    is_admin = db.Column(db.Boolean, default=False)
    tick = db.Column(db.String(20), default="")
    bio = db.Column(db.String(200), default="Hey there! I am using MyQchat")
    avatar_color = db.Column(db.String(20), default="#075e54")
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    dark_mode = db.Column(db.Boolean, default=False)
    wallpaper = db.Column(db.String(20), default="default")
    notifications = db.Column(db.Boolean, default=True)
    read_receipts = db.Column(db.Boolean, default=True)
    privacy_last_seen = db.Column(db.String(20), default="everyone")  # everyone, contacts, nobody
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime)
    delete_requested_at = db.Column(db.DateTime)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    def to_dict(self):
        return {"id":self.id,"uid":self.uid,"username":self.username,"name":self.name or self.username,"tick":self.tick,"is_admin":self.is_admin,"online":self.online,"last_seen":self.last_seen.strftime("%I:%M %p") if self.last_seen else "","bio":self.bio,"avatar_color":self.avatar_color,"dark_mode":self.dark_mode,"wallpaper":self.wallpaper,"notifications":self.notifications,"read_receipts":self.read_receipts,"privacy_last_seen":self.privacy_last_seen,"has_recovery_email":bool(self.recovery_email or self.email),"recovery_email":self.recovery_email or self.email or ""}

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
    to_uid = db.Column(db.String(20))
    to_id = db.Column(db.Integer)
    text = db.Column(db.String(2000))
    msg_type = db.Column(db.String(20), default="text")
    image_data = db.Column(db.Text)
    reply_to_id = db.Column(db.Integer)
    reply_to_text = db.Column(db.String(200))
    reaction = db.Column(db.String(20), default="")
    is_starred = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_broadcast = db.Column(db.Boolean, default=False)
    broadcast_tag = db.Column(db.String(20), default="")
    is_forwarded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(20))
    username = db.Column(db.String(80))
    name = db.Column(db.String(100))
    caption = db.Column(db.String(500))
    image_data = db.Column(db.Text)
    song = db.Column(db.String(200), default="")  # Background song name / link - No MP3 upload
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer)
    uid = db.Column(db.String(20))

class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer)
    uid = db.Column(db.String(20))
    name = db.Column(db.String(100))
    text = db.Column(db.String(300))
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
    call_type = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Missed")
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

class TickRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(20))
    username = db.Column(db.String(80))
    name = db.Column(db.String(100))
    requested_tick = db.Column(db.String(20))  # Blue, Orange, Green
    reason = db.Column(db.String(300))
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    admin_note = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
                    for cname, ctype in [("google_id","VARCHAR(100)"),("recovery_email","VARCHAR(120)"),("avatar_color","VARCHAR(20)"),("dark_mode","BOOLEAN DEFAULT FALSE"),("wallpaper","VARCHAR(20)"),("notifications","BOOLEAN DEFAULT TRUE"),("read_receipts","BOOLEAN DEFAULT TRUE"),("privacy_last_seen","VARCHAR(20)"),("delete_requested_at","TIMESTAMP")]:
                        db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS {cname} {ctype}'))
                    db.session.commit()
                except Exception as e: print("PG migrate:", e); db.session.rollback()
            else:
                try:
                    cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
                    add_map = {"google_id":"VARCHAR(100)","recovery_email":"VARCHAR(120)","avatar_color":"VARCHAR(20) DEFAULT '#075e54'","dark_mode":"BOOLEAN DEFAULT 0","wallpaper":"VARCHAR(20) DEFAULT 'default'","notifications":"BOOLEAN DEFAULT 1","read_receipts":"BOOLEAN DEFAULT 1","privacy_last_seen":"VARCHAR(20) DEFAULT 'everyone'","delete_requested_at":"TIMESTAMP"}
                    for k,v in add_map.items():
                        if k not in cols: db.session.execute(text(f"ALTER TABLE user ADD COLUMN {k} {v}"))
                    db.session.commit()
                    mcols = [r[1] for r in db.session.execute(text("PRAGMA table_info(message)")).fetchall()]
                    if "reaction" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN reaction VARCHAR(20) DEFAULT ''"))
                    if "is_starred" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN is_starred BOOLEAN DEFAULT 0"))
                    if "reply_to_id" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN reply_to_id INTEGER"))
                    if "is_forwarded" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN is_forwarded BOOLEAN DEFAULT 0"))
                    if "image_data" not in mcols: db.session.execute(text("ALTER TABLE message ADD COLUMN image_data TEXT"))
                    db.session.commit()
                except Exception as e: print("SQLite migrate:", e); db.session.rollback()
            if not User.query.filter_by(username=OWNER_USERNAME).first():
                u = User(username=OWNER_USERNAME, name="LoyalWQ Owner", is_admin=True, tick="L", uid=gen_uid(), avatar_color="#7b1fa2")
                u.set_password("AlwaysBeLoyalQ"); db.session.add(u); db.session.commit()
                print("Owner created UID:", u.uid)
    except Exception as e: print("init_db error:", e)
init_db()

# ---------- AUTH - USERNAME + PASSWORD ONLY - NO EMAIL ----------
@app.route("/api/signup", methods=["POST"])
def signup():
    try:
        d = request.get_json(force=True)
        username=(d.get("username") or "").strip()
        password=d.get("password") or ""
        name=(d.get("name") or username).strip()
        # Email NOT required - Old code had email - Now removed
        if not username or not password: return jsonify({"success":False,"error":"Username and Password required"}),400
        if len(username)<3: return jsonify({"success":False,"error":"Username must be at least 3 letters"}),400
        if len(password)<4: return jsonify({"success":False,"error":"Password must be at least 4 letters"}),400
        if User.query.filter_by(username=username).first(): return jsonify({"success":False,"error":"Username already taken - Try another"}),400
        colors=["#075e54","#7b1fa2","#e91e63","#ff5722","#3f51b5","#009688"]
        u=User(username=username, name=name, uid=gen_uid(), avatar_color=random.choice(colors)); u.set_password(password)
        if username==OWNER_USERNAME: u.is_admin=True; u.tick="L"
        db.session.add(u); db.session.commit()
        return jsonify({"success":True,"user":u.to_dict()})
    except Exception as e: db.session.rollback(); return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/login", methods=["POST"])
def login():
    try:
        d=request.get_json(force=True); username=(d.get("username") or "").strip(); password=d.get("password") or ""
        u=User.query.filter_by(username=username).first()
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
        email=info.get("email"); name=info.get("name","User"); u=User.query.filter_by(recovery_email=email).first() or User.query.filter_by(email=email).first()
        if not u:
            base=email.split("@")[0].replace(".","")[:15]; uname=base; i=1
            while User.query.filter_by(username=uname).first(): i+=1; uname=f"{base}{i}"
            u=User(username=uname, name=name, uid=gen_uid(), google_id=info.get("sub"), recovery_email=email, email=email); u.set_password(secrets.token_hex(8))
            if uname==OWNER_USERNAME: u.is_admin=True; u.tick="L"
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
# ================= PART 2 - CHAT + POST + GROUP + STATUS + CALL APIs =================
# PART 1 me jo tha - Auth / Models - wo yahan nahi hai - Sirf naya hai

@app.route("/api/me")
def me_api():
    uid = request.args.get("uid")
    u = User.query.filter_by(uid=uid).first()
    if not u: return jsonify({"success":False}), 404
    d = u.to_dict(); d["online_count"] = User.query.filter_by(online=True).count()
    return jsonify({"success":True,"user":d})

@app.route("/api/users")
def users_api():
    uid = request.args.get("uid","")
    q = request.args.get("q","").strip().lower()
    all_users = User.query.filter(User.uid != uid).order_by(User.created_at.desc()).all()
    out=[]
    me_u = User.query.filter_by(uid=uid).first()
    for u in all_users:
        if q and q not in u.name.lower() and q not in u.username.lower() and q not in (u.uid or ""): continue
        last = Message.query.filter(((Message.sender_uid==uid)&(Message.to_uid==u.uid))|((Message.sender_uid==u.uid)&(Message.to_uid==uid))).order_by(Message.created_at.desc()).first()
        is_blocked = False
        if me_u: is_blocked = Block.query.filter_by(blocker_id=me_u.id, blocked_uid=u.uid).first() is not None
        d = u.to_dict()
        if last:
            if last.is_deleted: d["last_msg"] = "This message was deleted"
            elif last.msg_type=="image": d["last_msg"] = ("You: Photo" if last.sender_uid==uid else "Photo")
            elif last.msg_type=="voice": d["last_msg"] = ("You: Voice" if last.sender_uid==uid else "Voice")
            else: d["last_msg"] = ("You: " + last.text if last.sender_uid==uid else last.text)
            d["last_time"] = last.created_at.strftime("%I:%M %p")
        else:
            d["last_msg"] = u.bio; d["last_time"] = ""
        d["is_blocked"] = is_blocked
        out.append(d)
    groups = Group.query.all()
    for g in groups:
        members = [m.uid for m in GroupMember.query.filter_by(gid=g.gid).all()]
        if uid in members:
            last = Message.query.filter_by(to_uid=g.gid).order_by(Message.created_at.desc()).first()
            out.append({"id":g.id,"uid":g.gid,"username":g.gid,"name":"Group: "+g.name,"tick":"","is_admin":False,"online":False,"last_seen":"","bio":"Group","avatar_color":"#25d366","is_group":True,"last_msg":(last.text if last and not last.is_deleted else "No messages yet"),"last_time":last.created_at.strftime("%I:%M %p") if last else ""})
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
        txt = "This message was deleted" if m.is_deleted else m.text
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
        if not is_group and to_u:
            if Block.query.filter_by(blocker_id=to_u.id, blocked_uid=my_uid).first():
                return jsonify({"success":False,"error":"You are blocked by this user"}),403
            if Block.query.filter_by(blocker_id=me_u.id, blocked_uid=to_uid).first():
                return jsonify({"success":False,"error":"You blocked this user. Unblock first"}),403
        if not is_group and me_u.username!="LoyalWQ":
            is_contact = Contact.query.filter_by(owner_id=to_u.id, contact_uid=my_uid).first() or Contact.query.filter_by(owner_id=me_u.id, contact_uid=to_uid).first()
            if not is_contact:
                cnt=Message.query.filter_by(sender_uid=my_uid, to_uid=to_uid).count()
                if cnt>=2: return jsonify({"success":False,"error":"Save to contacts first - Unknown limit: 2 messages only"}),403
                if len(text)>30: return jsonify({"success":False,"error":"Unknown - Max 30 letters. Save contact to send longer"}),400
        last=Message.query.filter_by(sender_uid=my_uid).order_by(Message.created_at.desc()).first()
        if last and (datetime.utcnow()-last.created_at).total_seconds()<2:
            return jsonify({"success":False,"error":"Wait a second..."}),429
        one_hr_ago=datetime.utcnow()-timedelta(hours=1)
        cnt_hr=Message.query.filter(Message.sender_uid==my_uid, Message.created_at>=one_hr_ago).count()
        if cnt_hr>=300: return jsonify({"success":False,"error":"Hourly limit 300 reached"}),429
        if msg_type=="image":
            cnt_img=Message.query.filter(Message.sender_uid==my_uid, Message.msg_type=="image", Message.created_at>=one_hr_ago).count()
            if cnt_img>=2: return jsonify({"success":False,"error":"Image limit: 2 per hour"}),429
        m=Message(sender_id=me_u.id, sender_uid=my_uid, sender_name=me_u.name, to_uid=to_uid, to_id=to_u.id if to_u else 0, text=text or ("Photo" if msg_type=="image" else "Voice"), msg_type=msg_type, image_data=image_data, reply_to_id=reply_to_id, reply_to_text=reply_to_text)
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
    return jsonify({"success":True,"msg":"Report sent to Admin. Admin will check."})

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
    db.session.commit(); return jsonify({"success":True,"msg":"Calling..."})

@app.route("/api/calls")
def calls_api():
    uid=request.args.get("uid"); calls=CallLog.query.filter((CallLog.caller_uid==uid)|(CallLog.to_uid==uid)).order_by(CallLog.created_at.desc()).limit(20).all()
    return jsonify({"success":True,"calls":[{"id":c.id,"from":c.caller_name,"to":c.to_uid,"type":c.call_type,"status":c.status,"time":c.created_at.strftime("%d/%m %I:%M %p")} for c in calls]})

# ---------- POSTS - IMAGE + SONG - NO REEL ----------
@app.route("/api/posts", methods=["GET","POST"])
def posts_api():
    if request.method=="POST":
        d=request.get_json(force=True); me_u=User.query.filter_by(uid=d.get("my_uid")).first()
        if not me_u: return jsonify({"success":False}),404
        # 1 user - 1-3 photo per day check
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
        cnt_today = Post.query.filter(Post.uid==me_u.uid, Post.created_at>=today_start).count()
        if cnt_today>=3: return jsonify({"success":False,"error":"Daily limit: 3 posts per day"}),429
        p=Post(uid=me_u.uid, username=me_u.username, name=me_u.name, caption=(d.get("caption") or "")[:500], image_data=d.get("image_data",""), song=(d.get("song") or "")[:200])
        db.session.add(p); db.session.commit(); return jsonify({"success":True,"id":p.id})
    posts=Post.query.order_by(Post.created_at.desc()).limit(20).all()
    out=[]
    for p in posts:
        u=User.query.filter_by(uid=p.uid).first()
        liked = PostLike.query.filter_by(post_id=p.id, uid=request.args.get("my_uid","")).first() is not None
        comments=PostComment.query.filter_by(post_id=p.id).order_by(PostComment.created_at.asc()).all()
        out.append({"id":p.id,"uid":p.uid,"username":p.username,"name":p.name,"caption":p.caption,"image_data":p.image_data,"song":p.song,"likes":p.likes,"liked":liked,"avatar_color":u.avatar_color if u else "#075e54","tick":u.tick if u else "","time":p.created_at.strftime("%d/%m %I:%M %p"),"comments":[{"name":c.name,"text":c.text,"time":c.created_at.strftime("%I:%M %p")} for c in comments]})
    return jsonify({"success":True,"posts":out})

@app.route("/api/post-like", methods=["POST"])
def post_like_api():
    d=request.get_json(force=True); p=Post.query.get(d.get("post_id")); uid=d.get("my_uid")
    ex=PostLike.query.filter_by(post_id=p.id, uid=uid).first()
    if ex: db.session.delete(ex); p.likes=max(0,p.likes-1); db.session.commit(); return jsonify({"success":True,"liked":False,"likes":p.likes})
    db.session.add(PostLike(post_id=p.id, uid=uid)); p.likes+=1; db.session.commit(); return jsonify({"success":True,"liked":True,"likes":p.likes})

@app.route("/api/post-comment", methods=["POST"])
def post_comment_api():
    d=request.get_json(force=True); me_u=User.query.filter_by(uid=d.get("my_uid")).first()
    db.session.add(PostComment(post_id=d.get("post_id"), uid=me_u.uid, name=me_u.name, text=(d.get("text") or "")[:300])); db.session.commit(); return jsonify({"success":True})

@app.route("/api/post-delete", methods=["POST"])
def post_delete_api():
    d=request.get_json(force=True); p=Post.query.get(d.get("post_id"))
    if not p: return jsonify({"success":False}),404
    if p.uid!=d.get("my_uid"): return jsonify({"success":False,"error":"Only owner can delete"}),403
    PostLike.query.filter_by(post_id=p.id).delete(); PostComment.query.filter_by(post_id=p.id).delete(); db.session.delete(p); db.session.commit(); return jsonify({"success":True})
    # ================= PART 3 - ADMIN (SETTINGS ME CHHUPA) + TICK REQUEST + SETTINGS APIs =================
# Admin samne nahi hai - Sirf Settings me - Sirf LoyalWQ ko dikhega - Frontend me bhi wahi check hai

def is_owner(uid):
    u = User.query.filter_by(uid=uid).first()
    return u and u.username == "LoyalWQ" and u.is_admin

def is_admin_user(uid):
    u = User.query.filter_by(uid=uid).first()
    return u and u.is_admin

# ---------- TICK REQUEST - LOG BHI REQUEST KAR SAKTA HAI ----------
@app.route("/api/tick-request", methods=["POST"])
def tick_request_api():
    d = request.get_json(force=True)
    me_u = User.query.filter_by(uid=d.get("my_uid")).first()
    if not me_u: return jsonify({"success":False,"error":"Login first"}),401
    if me_u.username == "LoyalWQ":
        return jsonify({"success":False,"error":"Owner already has L Tick"}),400
    tick = d.get("tick","").strip()  # Blue, Orange, Green
    if tick not in ["Blue","Orange","Green"]:
        return jsonify({"success":False,"error":"Choose Blue / Orange / Green"}),400
    # L Tick request nahi ho sakta - Sirf Owner ka hai
    if tick == "L":
        return jsonify({"success":False,"error":"L Tick only for Owner"}),400
    # Scam Tick request nahi - Wo report se milega
    if tick == "Scam":
        return jsonify({"success":False,"error":"Scam Tick cannot be requested"}),400
    # Ek pending request pehle se hai to dobara nahi
    ex = TickRequest.query.filter_by(uid=me_u.uid, status="pending").first()
    if ex: return jsonify({"success":False,"error":"Your request is already pending. Wait for Admin."}),400
    reason = (d.get("reason") or "")[:300]
    if len(reason) < 5:
        return jsonify({"success":False,"error":"Reason likho - Kyu chahiye tick? Min 5 letters"}),400
    db.session.add(TickRequest(uid=me_u.uid, username=me_u.username, name=me_u.name, requested_tick=tick, reason=reason))
    db.session.commit()
    return jsonify({"success":True,"msg":"Tick Request sent to Admin. Admin approve / reject karega."})

@app.route("/api/my-tick-request")
def my_tick_req_api():
    uid = request.args.get("uid")
    reqs = TickRequest.query.filter_by(uid=uid).order_by(TickRequest.created_at.desc()).all()
    return jsonify({"success":True,"requests":[{"id":r.id,"tick":r.requested_tick,"reason":r.reason,"status":r.status,"admin_note":r.admin_note,"time":r.created_at.strftime("%d/%m %I:%M %p")} for r in reqs]})

# ---------- SETTINGS APIs - BADA SETTINGS ----------
@app.route("/api/update-profile", methods=["POST"])
def update_profile_api():
    d = request.get_json(force=True)
    u = User.query.filter_by(uid=d.get("my_uid")).first()
    if not u: return jsonify({"success":False}),404
    if d.get("name"): u.name = d.get("name")[:100]
    if d.get("bio") is not None: u.bio = d.get("bio")[:200]
    if d.get("avatar_color"): u.avatar_color = d.get("avatar_color")
    if d.get("dark_mode") is not None: u.dark_mode = bool(d.get("dark_mode"))
    if d.get("wallpaper"): u.wallpaper = d.get("wallpaper")
    if d.get("notifications") is not None: u.notifications = bool(d.get("notifications"))
    if d.get("read_receipts") is not None: u.read_receipts = bool(d.get("read_receipts"))
    if d.get("privacy_last_seen"): u.privacy_last_seen = d.get("privacy_last_seen")
    db.session.commit()
    return jsonify({"success":True,"user":u.to_dict(),"msg":"Profile saved"})

@app.route("/api/update-recovery-email", methods=["POST"])
def recovery_email_api():
    d = request.get_json(force=True)
    u = User.query.filter_by(uid=d.get("my_uid")).first()
    if not u: return jsonify({"success":False}),404
    email = (d.get("email") or "").strip().lower()
    if email == "":
        u.recovery_email = None; u.email = None; db.session.commit()
        return jsonify({"success":True,"msg":"Recovery Email removed"})
    if "@" not in email or "." not in email:
        return jsonify({"success":False,"error":"Valid Email likho"}),400
    # Same email kisi aur ka to nahi
    ex = User.query.filter(User.uid != u.uid, User.recovery_email == email).first()
    if ex: return jsonify({"success":False,"error":"This email is already used"}),400
    u.recovery_email = email; u.email = email; db.session.commit()
    return jsonify({"success":True,"msg":"Recovery Email saved - Password bhoolne par kaam aayegi"})

@app.route("/api/change-password", methods=["POST"])
def change_pass_api():
    d = request.get_json(force=True)
    u = User.query.filter_by(uid=d.get("my_uid")).first()
    if not u: return jsonify({"success":False}),404
    old = d.get("old_password") or ""
    new = d.get("new_password") or ""
    if not u.check_password(old): return jsonify({"success":False,"error":"Old password wrong"}),400
    if len(new) < 4: return jsonify({"success":False,"error":"New password min 4 letters"}),400
    u.set_password(new); db.session.commit()
    return jsonify({"success":True,"msg":"Password changed"})

@app.route("/api/delete-account", methods=["POST"])
def delete_account_api():
    d = request.get_json(force=True)
    u = User.query.filter_by(uid=d.get("my_uid")).first()
    if not u: return jsonify({"success":False}),404
    if u.username == "LoyalWQ": return jsonify({"success":False,"error":"Owner account cannot be deleted"}),403
    # Permanent Delete - 15 din appeal ke liye - Abhi mark karo
    u.delete_requested_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success":True,"msg":"Delete Request sent. Account 15 din me delete hoga. 15 din ke andar Settings > Cancel Delete se wapas le sakte ho."})

@app.route("/api/cancel-delete", methods=["POST"])
def cancel_delete_api():
    d = request.get_json(force=True)
    u = User.query.filter_by(uid=d.get("my_uid")).first()
    if not u: return jsonify({"success":False}),404
    u.delete_requested_at = None; db.session.commit()
    return jsonify({"success":True,"msg":"Delete cancelled. Account safe hai."})

@app.route("/api/blocked-list")
def blocked_list_api():
    uid = request.args.get("uid")
    u = User.query.filter_by(uid=uid).first()
    if not u: return jsonify({"success":True,"blocked":[]})
    blocks = Block.query.filter_by(blocker_id=u.id).all()
    out=[]
    for b in blocks:
        bu = User.query.filter_by(uid=b.blocked_uid).first()
        if bu: out.append(bu.to_dict())
    return jsonify({"success":True,"blocked":out})

@app.route("/api/starred")
def starred_api():
    my_uid = request.args.get("my_uid"); other = request.args.get("other_uid")
    msgs = Message.query.filter(((Message.sender_uid==my_uid)&(Message.to_uid==other))|((Message.sender_uid==other)&(Message.to_uid==my_uid)), Message.is_starred==True).order_by(Message.created_at.desc()).all()
    return jsonify({"success":True,"starred":[{"id":m.id,"from":m.sender_name,"text":"This message was deleted" if m.is_deleted else m.text,"time":m.created_at.strftime("%I:%M %p")} for m in msgs]})

# ---------- REPORT LIST - ADMIN ONLY ----------
@app.route("/api/reports")
def reports_api():
    uid = request.args.get("admin_uid")
    if not is_admin_user(uid): return jsonify({"success":False,"error":"Admin only"}),403
    reps = Report.query.order_by(Report.created_at.desc()).limit(50).all()
    out=[]
    for r in reps:
        rep_u = User.query.get(r.reporter_id)
        tgt = User.query.filter_by(uid=r.reported_uid).first()
        out.append({"id":r.id,"reporter":rep_u.username if rep_u else "Unknown","reported_uid":r.reported_uid,"reported_name":tgt.name if tgt else "Unknown","reported_tick":tgt.tick if tgt else "","reason":r.reason,"detail":r.detail,"time":r.created_at.strftime("%d/%m %I:%M %p")})
    return jsonify({"success":True,"reports":out})

# ---------- ADMIN PANEL APIS - SETTINGS KE ANDAR ----------
@app.route("/api/admin/stats")
def admin_stats_api():
    uid = request.args.get("admin_uid")
    if not is_admin_user(uid): return jsonify({"success":False,"error":"Admin only"}),403
    return jsonify({"success":True,"stats":{
        "total_users":User.query.count(),
        "online_users":User.query.filter_by(online=True).count(),
        "total_messages":Message.query.count(),
        "total_posts":Post.query.count(),
        "total_reports":Report.query.count(),
        "pending_ticks":TickRequest.query.filter_by(status="pending").count(),
        "total_groups":Group.query.count()
    }})

@app.route("/api/admin/tick-requests")
def admin_tick_list_api():
    uid = request.args.get("admin_uid")
    if not is_admin_user(uid): return jsonify({"success":False}),403
    reqs = TickRequest.query.order_by(TickRequest.created_at.desc()).all()
    return jsonify({"success":True,"requests":[{"id":r.id,"uid":r.uid,"username":r.username,"name":r.name,"tick":r.requested_tick,"reason":r.reason,"status":r.status,"time":r.created_at.strftime("%d/%m %I:%M %p")} for r in reqs]})

@app.route("/api/admin/tick-action", methods=["POST"])
def admin_tick_action_api():
    d = request.get_json(force=True)
    if not is_admin_user(d.get("admin_uid")): return jsonify({"success":False}),403
    r = TickRequest.query.get(d.get("request_id"))
    if not r: return jsonify({"success":False}),404
    action = d.get("action")  # approve / reject
    if action == "approve":
        r.status = "approved"; u = User.query.filter_by(uid=r.uid).first()
        if u: u.tick = r.requested_tick
        r.admin_note = d.get("note","Approved")
    else:
        r.status = "rejected"; r.admin_note = d.get("note","Rejected by Admin")
    db.session.commit()
    return jsonify({"success":True,"msg":"Tick "+r.status})

@app.route("/api/admin/users")
def admin_users_api():
    uid = request.args.get("admin_uid")
    if not is_admin_user(uid): return jsonify({"success":False}),403
    users = User.query.order_by(User.created_at.desc()).limit(100).all()
    return jsonify({"success":True,"users":[u.to_dict() for u in users]})

@app.route("/api/admin/user-action", methods=["POST"])
def admin_user_action_api():
    d = request.get_json(force=True)
    if not is_owner(d.get("admin_uid")): return jsonify({"success":False,"error":"Owner only"}),403
    target = User.query.filter_by(uid=d.get("target_uid")).first()
    if not target: return jsonify({"success":False}),404
    if target.username == "LoyalWQ": return jsonify({"success":False,"error":"Cannot action on Owner"}),403
    action = d.get("action")
    if action == "ban":
        target.is_banned = True; target.banned_until = datetime.utcnow() + timedelta(days=int(d.get("days",7)))
        msg = "User banned for "+str(d.get("days",7))+" days"
    elif action == "unban":
        target.is_banned = False; target.banned_until = None; msg = "User unbanned"
    elif action == "scam_tick":
        target.tick = "Scam"; msg = "Scam Tick lag gaya"
    elif action == "remove_tick":
        target.tick = ""; msg = "Tick removed"
    elif action == "give_tick":
        target.tick = d.get("tick","Blue"); msg = "Tick given: "+target.tick
    elif action == "delete":
        Message.query.filter((Message.sender_uid==target.uid)|(Message.to_uid==target.uid)).delete()
        Post.query.filter_by(uid=target.uid).delete()
        db.session.delete(target); db.session.commit()
        return jsonify({"success":True,"msg":"User deleted permanently"})
    else:
        return jsonify({"success":False,"error":"Unknown action"}),400
    db.session.commit()
    return jsonify({"success":True,"msg":msg})

@app.route("/api/admin/broadcast", methods=["POST"])
def admin_broadcast_api():
    d = request.get_json(force=True)
    if not is_admin_user(d.get("admin_uid")): return jsonify({"success":False}),403
    text = (d.get("text") or "")[:500]
    tag = d.get("tag","Announcement")  # Announcement / Warning / Ad
    if not text: return jsonify({"success":False,"error":"Message likho"}),400
    users = User.query.all()
    for u in users:
        if u.uid == d.get("admin_uid"): continue
        m = Message(sender_id=0, sender_uid="QWNG_BOT", sender_name="QWNG Bot", to_uid=u.uid, to_id=u.id, text=text, msg_type="text", is_broadcast=True, broadcast_tag=tag)
        db.session.add(m)
    db.session.commit()
    return jsonify({"success":True,"msg":"Broadcast sent to all users via QWNG Bot - Tag: "+tag})

@app.route("/api/admin/report-action", methods=["POST"])
def admin_report_action_api():
    d = request.get_json(force=True)
    if not is_admin_user(d.get("admin_uid")): return jsonify({"success":False}),403
    r = Report.query.get(d.get("report_id"))
    if not r: return jsonify({"success":False}),404
    action = d.get("action")  # warn / scam / delete / ignore
    tgt = User.query.filter_by(uid=r.reported_uid).first()
    if action == "scam" and tgt: tgt.tick = "Scam"
    if action == "delete" and tgt:
        Message.query.filter_by(sender_uid=tgt.uid).delete()
    db.session.delete(r); db.session.commit()
    return jsonify({"success":True,"msg":"Report handled: "+action})

@app.route("/api/admin/delete-report", methods=["POST"])
def admin_del_report_api():
    d = request.get_json(force=True)
    if not is_admin_user(d.get("admin_uid")): return jsonify({"success":False}),403
    r = Report.query.get(d.get("report_id"))
    if r: db.session.delete(r); db.session.commit()
    return jsonify({"success":True})

@app.route("/api/owner-backup")
def owner_backup_api():
    uid = request.args.get("admin_uid")
    if not is_owner(uid): return jsonify({"success":False,"error":"Owner only"}),403
    users = User.query.all()
    data = {"users":[{"uid":u.uid,"username":u.username,"name":u.name,"tick":u.tick,"online":u.online} for u in users],"messages":Message.query.count(),"posts":Post.query.count(),"reports":Report.query.count(),"exported_at":datetime.utcnow().strftime("%d/%m/%Y %I:%M %p")}
    return jsonify({"success":True,"backup":data})

# ---------- TERMS - POLICY ONLY - NO FEATURES ----------
@app.route("/api/terms")
def terms_api():
    return jsonify({"title":"Terms & Conditions - MyQchat","updated":"07 November 2026","sections":[
        {"h":"1. Welcome to MyQchat","t":"MyQchat is a social chat app by QWNG. By using MyQchat, you agree to these Terms. If you do not agree, please do not use the app."},
        {"h":"2. Eligibility","t":"You must be at least 13 years old to use MyQchat. If you are under 18, you must use MyQchat with your parent or guardian's permission. You are responsible for your account and activity."},
        {"h":"3. Your Account","t":"You must create your account with a unique Username and a strong Password. You are responsible for keeping your Password safe. Do not share your Password with anyone. You can add a Recovery Email in Settings to recover your account. If someone else uses your account, you will be responsible."},
        {"h":"4. Privacy Policy","t":"We collect only what is needed to run MyQchat: your Username, Name, UID, Bio, Profile colour, Messages you send, Posts you create, and your Recovery Email if you add it. Your Recovery Email is used only for account recovery and safety. We do not sell your data. We do not share your data with any third party for advertising. Messages are stored on our server to deliver them to the other person. If you delete a message, it will show as 'This message was deleted'. Your Last Seen and Online status is visible as per your Privacy Settings."},
        {"h":"5. Your Content","t":"You own the content you post - your messages, posts, and status. By posting, you give MyQchat permission to store and show it to the people you send it to. You must not post content that belongs to someone else without permission. You can delete your own posts and messages."},
        {"h":"6. Safety & Moderation","t":"To keep MyQchat safe, if a user reports a message, that reported message may be reviewed by Admin for safety check. We do not read your private chats for fun. Review happens only when a report is made, or when required by law. If you break the rules, Admin may warn you, remove your Tick, ban you for some days, or delete your account."},
        {"h":"7. Prohibited Behaviour","t":"You must NOT: 1) Harass, threaten, bully or abuse anyone. 2) Post hate speech, vulgar, obscene or adult content. 3) Pretend to be someone else or create fake account to scam. 4) Send spam, scam links, or fraud messages. 5) Share someone's private info like phone, address, password without permission. 6) Try to hack, break or misuse MyQchat. 7) Post illegal content."},
        {"h":"8. Tick & Verification","t":"Ticks show trust level. Blue, Orange, Green Ticks can be requested from Settings > Request Tick with a reason. Admin will approve or reject. L Tick is only for the Owner of MyQchat and cannot be requested. Scam Tick is given by Admin after reports and investigation, and cannot be requested. Admin can remove any Tick at any time."},
        {"h":"9. Account Deletion & Appeal","t":"You can request Permanent Delete from Settings > Delete Account. Your account will be deleted after 15 days. Within 15 days, you can cancel delete from Settings and appeal. If Admin deletes your account for rule break, you can appeal within 15 days by contacting Admin. After 15 days, deletion is final."},
        {"h":"10. Service & Availability","t":"MyQchat is provided as-is. Sometimes server may be slow, or down for maintenance. We try to keep it fast and safe, but we cannot promise 100% uptime. We may update features, fix bugs, or change these Terms. Big changes will be shown in the app."},
        {"h":"11. Liability","t":"MyQchat and QWNG are not responsible for any loss, damage, or dispute between users. You use MyQchat at your own risk. You are responsible for what you send and share. Be careful before sharing personal info with strangers."},
        {"h":"12. Changes to Terms","t":"We may update these Terms when needed. The updated date will be shown on top. By continuing to use MyQchat after changes, you agree to the new Terms."},
        {"h":"13. Contact","t":"For help, report, appeal, or any question, contact QWNG Team from Settings > Help & Support. Owner: LoyalWQ. App: MyQchat by QWNG."}
    ]})
    # ================= PART 4 - FRONTEND HTML + CSS - BADA SETTINGS =================
FRONTEND = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>MyQchat - by QWNG</title><style>
*{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#eef2f5;color:#111b21;overflow:hidden}
a{color:#00a884;text-decoration:none}
button{cursor:pointer;border:none}
input,textarea,select{outline:none}
.top{background:#075e54;color:#fff;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:20}
.top b{font-size:19px;letter-spacing:.3px}.top small{display:block;font-size:10px;opacity:.85;font-weight:400}
.top .icons{display:flex;gap:14px;font-size:20px}.top .icons span{cursor:pointer}
.tabs{display:flex;background:#075e54;color:#fff}
.tabs div{flex:1;text-align:center;padding:12px 0;font-size:14px;cursor:pointer;opacity:.75;border-bottom:3px solid transparent}
.tabs div.active{opacity:1;border-bottom:3px solid #fff;font-weight:700}
.page{display:none;height:calc(100vh - 106px);overflow-y:auto;padding-bottom:90px;background:#fff}
.page.active{display:block}
.searchBox{padding:10px;background:#fff;display:flex;gap:8px;position:sticky;top:0;z-index:5}
.searchBox input{flex:1;background:#f0f2f5;border:none;border-radius:22px;padding:11px 14px;font-size:14px}
.searchBox button{background:#00a884;color:#fff;border-radius:22px;padding:0 14px;font-weight:600}
.chipRow{display:flex;gap:8px;padding:0 12px 10px;overflow-x:auto;white-space:nowrap}
.chip{background:#f0f2f5;border-radius:20px;padding:7px 14px;font-size:13px;cursor:pointer}
.chip.on{background:#075e54;color:#fff}
.userRow{display:flex;align-items:center;gap:12px;padding:11px 14px;cursor:pointer;border-bottom:1px solid #f0f2f5}
.userRow:active{background:#f0f2f5}
.avatar{width:48px;height:48px;border-radius:50%;color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;flex-shrink:0;position:relative}
.avatar .dot{position:absolute;right:0;bottom:2px;width:13px;height:13px;border-radius:50%;border:2px solid #fff}
.userInfo{flex:1;min-width:0}.userInfo b{font-size:15px;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.userInfo span{font-size:12.5px;color:#667781;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.tick{font-size:11px;padding:1px 6px;border-radius:10px;color:#fff;margin-left:5px;vertical-align:middle}
.tick.Blue{background:#2196f3}.tick.Orange{background:#ff9800}.tick.Green{background:#4caf50}.tick.L{background:#7b1fa2}.tick.Scam{background:#f44336}
.time{font-size:11px;color:#667781;white-space:nowrap;text-align:right}
.card{margin:12px;background:#fff;border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,.08);overflow:hidden}
.cardHead{padding:14px;display:flex;gap:12px;align-items:center}
.postImg{width:100%;max-height:420px;object-fit:cover;background:#000;display:block}
.postActions{display:flex;gap:18px;padding:10px 14px;font-size:19px;border-top:1px solid #f0f2f5}
.postActions span{cursor:pointer}.postActions span.liked{color:#e91e63}
.songBox{margin:10px 14px;background:#e8f5e9;border-radius:10px;padding:10px;font-size:13px}
.commentBox{padding:0 14px 12px;font-size:13px;color:#333}.commentBox b{color:#111}
.commentInput{display:flex;gap:8px;padding:10px 14px;border-top:1px solid #f0f2f5}
.commentInput input{flex:1;background:#f0f2f5;border:none;border-radius:20px;padding:9px 12px}
.commentInput button{background:#00a884;color:#fff;border-radius:20px;padding:0 14px}
.empty{text-align:center;color:#8696a0;padding:50px 20px;font-size:14px;line-height:1.6}
.empty b{color:#111;font-size:17px}
.btn{width:100%;background:#00a884;color:#fff;padding:13px;border-radius:12px;font-size:15px;font-weight:700;margin-top:10px}
.btn2{background:#075e54}.btnRed{background:#e53935}.btnGrey{background:#e9edef;color:#111}
.inp{width:100%;padding:12px 14px;border:1px solid #d1d7db;border-radius:10px;margin-top:10px;font-size:14px;background:#fff}
label{font-size:12px;color:#667781;font-weight:600;display:block;margin-top:14px}
.authWrap{max-width:420px;margin:0 auto;padding:28px 20px}
.authLogo{width:72px;height:72px;border-radius:18px;background:linear-gradient(135deg,#7b1fa2,#e91e63,#ff9800);display:flex;align-items:center;justify-content:center;color:#fff;font-size:38px;font-weight:900;margin:10px auto;box-shadow:0 6px 20px rgba(123,31,162,.35)}
.authLogo i{width:12px;height:12px;background:#25d366;border-radius:50%;position:absolute;margin:22px 0 0 22px;border:2px solid #fff}
.linkRow{text-align:center;margin-top:14px;font-size:13px;color:#667781}
.linkRow a{font-weight:700;cursor:pointer}
.small{font-size:11px;color:#8696a0;text-align:center;margin-top:10px;line-height:1.5}
.small a{color:#00a884}
/* CHAT SCREEN */
.chatHead{background:#075e54;color:#fff;padding:10px 12px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:30}
.chatHead b{flex:1;font-size:16px}.chatHead small{display:block;font-size:11px;opacity:.85;font-weight:400}
.chatHead .act{font-size:20px;cursor:pointer;padding:4px}
.chatArea{background:#ece5dd;height:calc(100vh - 118px);overflow-y:auto;padding:12px 10px 10px}
body.dark .chatArea{background:#0b141a}
.msg{max-width:82%;padding:8px 10px 6px;border-radius:10px;margin-bottom:8px;font-size:14.5px;line-height:1.4;position:relative;box-shadow:0 1px 1px rgba(0,0,0,.12);word-wrap:break-word}
.msg.mine{background:#d9fdd3;margin-left:auto;border-top-right-radius:2px}
.msg.theirs{background:#fff;margin-right:auto;border-top-left-radius:2px}
body.dark .msg.theirs{background:#202c33;color:#e9edef}
body.dark .msg.mine{background:#005c4b;color:#e9edef}
.msg .mTime{font-size:10px;color:#667781;float:right;margin:8px 0 0 8px}
.msg .fwd{font-size:11px;color:#00a884;font-style:italic}
.msg .replyBox{background:rgba(0,0,0,.06);border-left:3px solid #00a884;padding:6px 8px;border-radius:6px;font-size:12px;margin-bottom:5px;color:#555}
.msg img{width:100%;border-radius:8px;max-height:320px;object-fit:cover}
.msg .react{position:absolute;bottom:-10px;right:8px;background:#fff;border-radius:12px;padding:1px 6px;font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.2)}
.msg .star{color:#ffb300;font-size:11px}
.broadcast{max-width:92%;margin:8px auto;background:#fff3cd;border:1px solid #ffe082;border-radius:10px;padding:10px;font-size:13px}
.broadcast b{color:#e65100}
.inputBar{display:flex;align-items:center;gap:6px;padding:8px;background:#f0f2f5;position:fixed;bottom:0;left:0;right:0;z-index:40}
.inputBar .pill{flex:1;background:#fff;border-radius:26px;display:flex;align-items:center;padding:0 6px}
.inputBar input{flex:1;border:none;padding:11px 8px;font-size:14px;background:transparent}
.inputBar .ic{font-size:21px;padding:6px;cursor:pointer}
.sendBtn{width:44px;height:44px;border-radius:50%;background:#00a884;color:#fff;font-size:20px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.emojiBar{display:none;gap:6px;padding:8px;background:#fff;overflow-x:auto;white-space:nowrap;border-top:1px solid #eee}
.emojiBar span{font-size:22px;cursor:pointer;padding:4px}
/* MODAL / SETTINGS */
.modal{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:flex-end;justify-content:center;z-index:100}
.modal.open{display:flex}
.sheet{background:#fff;width:100%;max-height:88vh;overflow-y:auto;border-radius:20px 20px 0 0;padding:18px;padding-bottom:30px}
.sheet h3{font-size:18px;margin-bottom:6px}.sheet p{font-size:13px;color:#667781;line-height:1.5}
.setItem{display:flex;align-items:center;gap:12px;padding:14px 4px;border-bottom:1px solid #f0f2f5;cursor:pointer}
.setItem:active{background:#f0f2f5}
.setItem .ic{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0}
.setItem b{font-size:14.5px;display:block}.setItem span{font-size:12px;color:#667781}
.setHead{padding:20px 16px;background:#075e54;color:#fff;display:flex;gap:14px;align-items:center}
.setHead b{font-size:17px}.setHead span{font-size:12px;opacity:.9}
.setSec{padding:14px 16px 4px;font-size:12px;color:#00a884;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.adminBox{background:#fff3e0;border:1px solid #ffcc80;border-radius:12px;padding:12px;margin:12px}
.adminBox b{color:#e65100}
.dangerBox{background:#ffebee;border:1px solid #ffcdd2;border-radius:12px;padding:12px;margin:12px}
.toggle{margin-left:auto;width:46px;height:26px;background:#ccc;border-radius:20px;position:relative;flex-shrink:0}
.toggle.on{background:#00a884}.toggle:after{content:'';position:absolute;width:22px;height:22px;background:#fff;border-radius:50%;top:2px;left:2px;transition:.2s}
.toggle.on:after{left:22px}
.wallRow{display:flex;gap:10px;margin-top:10px}.wallOpt{flex:1;height:46px;border-radius:10px;cursor:pointer;border:3px solid transparent;text-align:center;line-height:40px;font-size:12px;font-weight:700}
.wallOpt.on{border-color:#00a884}
.termsPage{padding:18px;line-height:1.7;font-size:14px}.termsPage h2{font-size:20px;margin-bottom:6px}.termsPage h3{font-size:15px;margin:16px 0 6px;color:#075e54}
.fab{position:fixed;right:16px;bottom:90px;width:56px;height:56px;border-radius:50%;background:#00a884;color:#fff;font-size:26px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:50}
.statusCard{display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid #f0f2f5;align-items:center}
.callRow{display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid #f0f2f5;align-items:center}
@media(min-width:700px){.page,.chatArea{max-width:520px;margin:0 auto}}
</style></head><body>
<!-- AUTH -->
<div id="authPage">
<div class="authWrap">
<div style="position:relative;width:72px;margin:0 auto"><div class="authLogo">Q<i></i></div></div>
<h2 style="text-align:center;margin-top:14px">MyQchat</h2>
<p style="text-align:center;color:#667781;font-size:13px;margin-top:4px">Chat, Friends, Groups, Status & More<br>By QWNG • Free • Fast • Secure</p>
<div id="loginBox">
<label>Username</label><input id="l_user" class="inp" placeholder="Username">
<label>Password</label><input id="l_pass" class="inp" type="password" placeholder="Password">
<div id="l_msg" style="color:#e53935;font-size:13px;margin-top:8px"></div>
<button class="btn" onclick="doLogin()">Login</button>
<button class="btn btn2" onclick="googleLogin()">G &nbsp; Continue with Google</button>
<div class="linkRow">New here? <a onclick="showSignup()">Create Account</a></div>
</div>
<div id="signupBox" style="display:none">
<label>Your Name</label><input id="s_name" class="inp" placeholder="Name">
<label>Username</label><input id="s_user" class="inp" placeholder="Choose Username - min 3 letters">
<label>Password</label><input id="s_pass" class="inp" type="password" placeholder="Password - min 4 letters">
<div id="s_msg" style="color:#e53935;font-size:13px;margin-top:8px"></div>
<button class="btn" onclick="doSignup()">Create Account</button>
<div class="linkRow">Already have account? <a onclick="showLogin()">Login</a></div>
</div>
<p class="small">By continuing, you agree to our<br><a onclick="openTerms()">Terms & Conditions</a> • <a onclick="openTerms()">Privacy Policy</a><br>Email is NOT needed for Signup. You can add Recovery Email later in Settings.</p>
</div></div>

<!-- MAIN APP -->
<div id="mainApp" style="display:none">
<div class="top"><div><b>MyQchat</b><small id="topStatus">Online</small></div><div class="icons"><span onclick="openSearch()">🔍</span><span onclick="openSettings()">⚙️</span></div></div>
<div class="tabs"><div id="tabChats" class="active" onclick="showTab('chats')">Chats</div><div id="tabPosts" onclick="showTab('posts')">Posts</div><div id="tabStatus" onclick="showTab('status')">Status</div><div id="tabCalls" onclick="showTab('calls')">Calls</div></div>

<!-- CHATS PAGE -->
<div id="page-chats" class="page active">
<div class="searchBox"><input id="chatSearch" placeholder="Search by Name / Username / UID" oninput="loadUsers()"><button onclick="openAddContact()">+ Add</button></div>
<div class="chipRow"><div class="chip on" onclick="filterChip(this,'all')">All</div><div class="chip" onclick="filterChip(this,'unread')">Unread</div><div class="chip" onclick="filterChip(this,'groups')">Groups</div><div class="chip" onclick="filterChip(this,'fav')">Favourites</div></div>
<div id="chatList"></div>
<div class="fab" onclick="openAddContact()">+</div>
</div>

<!-- POSTS PAGE -->
<div id="page-posts" class="page">
<div class="card" style="padding:14px"><b>📸 Create Post</b><p style="font-size:12px;color:#667781">Photo + Song Name — Max 3 posts / day</p>
<input id="postCaption" class="inp" placeholder="Caption likho... (max 500)">
<input id="postSong" class="inp" placeholder="Song name / link (optional) — No MP3 upload">
<label>Photo (optional)</label><input id="postImage" type="file" accept="image/*" class="inp">
<button class="btn" onclick="createPost()">Post</button></div>
<div id="postList"></div>
</div>

<!-- STATUS PAGE -->
<div id="page-status" class="page">
<div class="card" style="padding:14px"><b>✨ My Status</b><input id="statusText" class="inp" placeholder="Status likho... (max 300)"><button class="btn" onclick="postStatus()">Post Status</button><p class="small">Status 24 hours me auto delete hoga</p></div>
<div id="statusList"></div>
</div>

<!-- CALLS PAGE -->
<div id="page-calls" class="page"><div id="callList"></div></div>

<!-- SETTINGS PAGE - BADA WALA -->
<div id="page-settings" class="page">
<div class="setHead"><div class="avatar" id="setAvatar" style="width:60px;height:60px;font-size:24px">L</div><div><b id="setName">LoyalWQ</b><span id="setUid">UID: 00000000</span><br><span id="setTickLine"></span></div></div>
<div class="setSec">Profile</div>
<div class="setItem" onclick="openEditProfile()"><div class="ic" style="background:#e3f2fd">👤</div><div><b>Edit Profile</b><span>Name, Bio, Colour</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openRecoveryEmail()"><div class="ic" style="background:#fff3e0">📧</div><div><b>Recovery Email</b><span id="recoveryLine">Not added - Add for password recovery</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openTickRequest()"><div class="ic" style="background:#e8f5e9">✔️</div><div><b>Request Tick</b><span>Blue / Orange / Green — Admin approve karega</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openMyTickStatus()"><div class="ic" style="background:#f3e5f5">📋</div><div><b>My Tick Requests</b><span>Pending / Approved / Rejected</span></div><div style="margin-left:auto">›</div></div>

<div class="setSec">Chats & Looks</div>
<div class="setItem"><div class="ic" style="background:#e0f2f1">🌙</div><div><b>Dark Mode</b><span>Night me aankhon ke liye</span></div><div class="toggle" id="darkToggle" onclick="toggleDark(event)"></div></div>
<div class="setItem"><div class="ic" style="background:#fce4ec">🎨</div><div><b>Wallpaper</b><span>Chat background</span></div><div style="margin-left:auto">›</div></div>
<div style="padding:0 16px"><div class="wallRow"><div class="wallOpt on" data-wall="default" style="background:#ece5dd" onclick="setWallpaper('default',this)">Default</div><div class="wallOpt" data-wall="green" style="background:#d9fdd3" onclick="setWallpaper('green',this)">Green</div><div class="wallOpt" data-wall="blue" style="background:#dbeafe" onclick="setWallpaper('blue',this)">Blue</div><div class="wallOpt" data-wall="dark" style="background:#0b141a;color:#fff" onclick="setWallpaper('dark',this)">Dark</div></div></div>
<div class="setItem"><div class="ic" style="background:#e8eaf6">🔔</div><div><b>Notifications</b><span>New message alert</span></div><div class="toggle on" id="notifToggle" onclick="toggleNotif(event)"></div></div>

<div class="setSec">Privacy & Safety</div>
<div class="setItem" onclick="openPrivacy()"><div class="ic" style="background:#e3f2fd">🔒</div><div><b>Privacy</b><span>Last Seen, Read Receipts</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openBlocked()"><div class="ic" style="background:#ffebee">🚫</div><div><b>Blocked Users</b><span id="blockedCount">0 blocked</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openChangePass()"><div class="ic" style="background:#fff8e1">🔑</div><div><b>Change Password</b><span>Old + New Password</span></div><div style="margin-left:auto">›</div></div>

<div class="setSec">Help & Legal</div>
<div class="setItem" onclick="openTerms()"><div class="ic" style="background:#e0f2f1">📄</div><div><b>Terms & Conditions</b><span>Full policy — Click to open page</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openTerms()"><div class="ic" style="background:#e8f5e9">🛡️</div><div><b>Privacy Policy</b><span>How we use your data</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openHelp()"><div class="ic" style="background:#e3f2fd">❓</div><div><b>Help & Support</b><span>QWNG Team se contact</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="openAbout()"><div class="ic" style="background:#f3e5f5">ℹ️</div><div><b>About MyQchat</b><span>Version, Owner, QWNG</span></div><div style="margin-left:auto">›</div></div>

<div id="adminSection" style="display:none">
<div class="setSec" style="color:#e65100">Admin Panel — Only for LoyalWQ</div>
<div class="adminBox"><b>🛡️ ADMIN PANEL — Settings ke andar</b><p style="font-size:12px;color:#666;margin-top:4px">Ye sirf tumko dikhega. Kisi aur ko nahi.</p>
<div id="adminStats" style="font-size:13px;margin-top:8px">Loading stats...</div>
<button class="btn btn2" onclick="openAdminUsers()">👥 All Users</button>
<button class="btn" onclick="openAdminTicks()">✔️ Tick Requests</button>
<button class="btn btn2" onclick="openAdminReports()">🚩 Reports</button>
<button class="btn" onclick="openBroadcast()"> Broadcast via QWNG Bot</button>
<button class="btn btn2" onclick="ownerBackup()">💾 Owner Backup</button>
</div></div>

<div class="setSec">Account</div>
<div class="setItem" onclick="openDeleteAccount()"><div class="ic" style="background:#ffebee">🗑️</div><div><b style="color:#e53935">Delete Account</b><span>Permanent — 15 din me delete — Appeal possible</span></div><div style="margin-left:auto">›</div></div>
<div class="setItem" onclick="doLogout()"><div class="ic" style="background:#e9edef">🚪</div><div><b>Logout</b><span>Is device se logout</span></div><div style="margin-left:auto">›</div></div>
<p class="small">MyQchat — Developed by QWNG<br>Owner: LoyalWQ • Version V3 • Made with ❤️</p>
</div>
</div>

<!-- CHAT SCREEN -->
<div id="chatScreen" style="display:none">
<div class="chatHead"><span onclick="closeChat()" style="font-size:22px;cursor:pointer">←</span><div class="avatar" id="chatAvatar" style="width:40px;height:40px;font-size:17px">A</div><b id="chatName">Name<small id="chatStatus">Online</small></b><span class="act" onclick="callUser('voice')">📞</span><span class="act" onclick="callUser('video')">📹</span><span class="act" onclick="openChatInfo()">⋮</span></div>
<div style="padding:8px 12px;background:#fff;display:flex;gap:8px"><input id="chatSearchIn" placeholder="Search in chat..." style="flex:1;background:#f0f2f5;border:none;border-radius:18px;padding:8px 12px" oninput="loadMessages()"><button onclick="openStarred()" style="background:#fff3e0;border:none;border-radius:18px;padding:6px 12px">⭐ Starred</button></div>
<div class="chatArea" id="chatArea"></div>
<div class="emojiBar" id="emojiBar"><span onclick="addEmoji('😀')">😀</span><span onclick="addEmoji('😂')">😂</span><span onclick="addEmoji('❤️')">❤️</span><span onclick="addEmoji('🔥')">🔥</span><span onclick="addEmoji('👍')">👍</span><span onclick="
"""
# ================= PART 5 - FRONTEND JS - CHAT + POSTS + STATUS + CALLS - ENGLISH ONLY ================="""
FRONTEND_JS = r"""<script>
let ME=null, CUR=null, CUR_NAME="", REPLY_ID=null, REPLY_TEXT="", CUR_FILTER='all', CHAT_TIMER=null;
function val(id){return document.getElementById(id).value.trim()}
function show(id){return document.getElementById(id)}
function openModal(html){show('modalBody').innerHTML=html; show('modal').classList.add('open')}
function closeModal(){show('modal').classList.remove('open')}
function showLogin(){show('loginBox').style.display='block';show('signupBox').style.display='none'}
function showSignup(){show('loginBox').style.display='none';show('signupBox').style.display='block'}
function googleLogin(){window.location.href='/auth/google'}
function openTerms(){
  fetch('/api/terms').then(r=>r.json()).then(d=>{
    let h=`<h2>${d.title}</h2><p style="color:#667781">Last updated: ${d.updated}</p>`;
    d.sections.forEach(s=>{h+=`<h3>${s.h}</h3><p>${s.t}</p>`});
    show('termsContent').innerHTML=h;
    show('mainApp').style.display='none'; show('authPage').style.display='none'; show('termsPage').style.display='block';
  });
}
function closeTerms(){
  show('termsPage').style.display='none';
  if(ME) show('mainApp').style.display='block'; else show('authPage').style.display='block';
}
async function doSignup(){
  let name=val('s_name'), user=val('s_user'), passw=show('s_pass').value;
  if(!user||!passw){show('s_msg').innerText='Username and Password are required';return}
  show('s_msg').innerText='Creating account...';
  let r=await fetch('/api/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:passw,name:name||user})});
  let d=await r.json();
  if(!d.success){show('s_msg').innerText=d.error;return}
  ME=d.user; afterLogin();
}
async function doLogin(){
  let user=val('l_user'), passw=show('l_pass').value;
  if(!user||!passw){show('l_msg').innerText='Enter Username and Password';return}
  show('l_msg').innerText='Logging in...';
  let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:passw})});
  let d=await r.json();
  if(!d.success){show('l_msg').innerText=d.error;return}
  ME=d.user; afterLogin();
}
function afterLogin(){
  show('authPage').style.display='none'; show('mainApp').style.display='block';
  localStorage.setItem('myqchat_uid', ME.uid);
  show('topStatus').innerText = ME.username + ' - UID: ' + ME.uid;
  loadSettingsPage(); loadUsers(); loadPosts(); loadStatus(); loadCalls();
  setInterval(()=>{ if(CUR) loadMessages(); else loadUsers(); }, 3000);
}
async function doLogout(){
  await fetch('/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid:ME.uid})});
  localStorage.removeItem('myqchat_uid'); location.reload();
}
function showTab(t){
  ['chats','posts','status','calls','settings'].forEach(x=>{ let el=show('page-'+x); if(el) el.classList.remove('active'); });
  let p=show('page-'+t); if(p) p.classList.add('active');
  ['tabChats','tabPosts','tabStatus','tabCalls'].forEach(x=>show(x).classList.remove('active'));
  if(t==='chats') show('tabChats').classList.add('active');
  if(t==='posts') show('tabPosts').classList.add('active');
  if(t==='status') show('tabStatus').classList.add('active');
  if(t==='calls') show('tabCalls').classList.add('active');
}
function openSettings(){ showTab('settings'); loadSettingsPage(); }
function filterChip(el, f){ document.querySelectorAll('.chip').forEach(c=>c.classList.remove('on')); el.classList.add('on'); CUR_FILTER=f; loadUsers(); }
function tickHtml(t){ if(!t) return ''; return `<span class="tick ${t}">${t==='L'?'L ✓':t+' ✓'}</span>` }
async function loadUsers(){
  if(!ME) return;
  let q=val('chatSearch');
  let r=await fetch(`/api/users?uid=${ME.uid}&q=${encodeURIComponent(q)}`); let d=await r.json();
  let list=show('chatList'); if(!d.users || d.users.length===0){ list.innerHTML=`<div class="empty"><b>No chats yet</b><br>Tap + to add a contact by UID<br>Or search a user by UID</div>`; return; }
  let html='';
  d.users.forEach(u=>{
    if(CUR_FILTER==='groups' && !u.is_group) return;
    if(CUR_FILTER==='fav' && !u.is_fav) return;
    let last = u.last_msg||u.bio||'';
    let col = u.avatar_color||'#075e54';
    let onlineDot = u.online?'<span class="dot" style="background:#25d366"></span>':'<span class="dot" style="background:#a8a8a8"></span>';
    let name = u.is_group? u.name : (u.name||u.username);
    html+=`<div class="userRow" onclick="openChat('${u.uid}','${name.replace(/'/g,"")}','${col}')"><div class="avatar" style="background:${col}">${name.charAt(0).toUpperCase()}${onlineDot}</div><div class="userInfo"><b>${name} ${tickHtml(u.tick)}</b><span>${last.substring(0,45)}</span></div><div class="time">${u.last_time||''}<br><span style="font-size:10px;color:#00a884">${u.online?'Online':''}</span></div></div>`;
  });
  list.innerHTML=html||`<div class="empty">No results</div>`;
}
function openSearch(){ showTab('chats'); setTimeout(()=>show('chatSearch').focus(),100); }
function openAddContact(){
  openModal(`<h3>Add Contact by UID</h3><p>Ask your friend for their 8-digit UID. Search and add them.</p><label>Friend UID (8 digits)</label><input id="addUid" class="inp" placeholder="e.g. 12345678" maxlength="8"><div id="addMsg" style="color:#e53935;font-size:13px;margin-top:8px"></div><button class="btn" onclick="doSearchUid()">Search</button><div id="addResult"></div>`);
}
async function doSearchUid(){
  let q=val('addUid'); if(q.length!==8){show('addMsg').innerText='Enter 8-digit UID';return}
  let r=await fetch(`/api/search-uid?q=${q}`); let d=await r.json();
  if(!d.success){show('addMsg').innerText=d.error;return}
  show('addResult').innerHTML=`<div class="card" style="padding:12px;display:flex;gap:10px;align-items:center"><div class="avatar" style="background:${d.user.avatar_color}">${d.user.name.charAt(0)}</div><div style="flex:1"><b>${d.user.name} ${tickHtml(d.user.tick)}</b><br><span style="font-size:12px;color:#667781">@${d.user.username} - UID ${d.user.uid}</span></div><button class="btn" style="width:auto;margin:0;padding:8px 14px" onclick="doAddContact('${d.user.uid}')">Add</button></div>`;
}
async function doAddContact(uid){
  let r=await fetch('/api/add-contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,contact_uid:uid})});
  let d=await r.json(); alert(d.msg||d.error||'Added'); closeModal(); loadUsers();
}
function openChat(uid, name, col){
  CUR=uid; CUR_NAME=name;
  show('mainApp').style.display='none'; show('chatScreen').style.display='block';
  show('chatName').innerHTML=name; show('chatAvatar').innerText=name.charAt(0).toUpperCase(); show('chatAvatar').style.background=col||'#075e54';
  show('chatStatus').innerText='Tap for info';
  loadMessages();
}
function closeChat(){ CUR=null; show('chatScreen').style.display='none'; show('mainApp').style.display='block'; loadUsers(); }
async function loadMessages(){
  if(!ME||!CUR) return;
  let s=val('chatSearchIn');
  let r=await fetch(`/api/messages?my_uid=${ME.uid}&other_uid=${CUR}&search=${encodeURIComponent(s)}`); let d=await r.json();
  let area=show('chatArea');
  if(!d.messages||d.messages.length===0){ area.innerHTML=`<div class="empty"><b>No messages yet</b><br>Say Hi<br><span style="font-size:12px">Unknown users: Max 2 messages, 30 letters each.<br>Save to contacts for full chat.</span></div>`; return; }
  let html='';
  d.messages.forEach(m=>{
    let isMine = m.from===ME.uid;
    let cls = isMine?'mine':'theirs';
    let inner='';
    if(m.is_forwarded) inner+=`<div class="fwd">Forwarded</div>`;
    if(m.reply_to_text) inner+=`<div class="replyBox">${m.reply_to_text}</div>`;
    if(m.is_broadcast) inner+=`<div style="background:#fff3cd;border-radius:8px;padding:8px;margin-bottom:5px"><b style="color:#e65100">${m.tag||'Announcement'} - QWNG Bot</b><br>${m.text}</div>`;
    else if(m.type==='image' && m.image_data) inner+=`<img src="${m.image_data}"><br>${m.text!=='Photo'?m.text:''}`
    else if(m.type==='voice') inner+=`🎤 Voice Message (15 sec)`;
    else inner+=`${m.text}`;
    let react = m.reaction?`<span class="react">${m.reaction}</span>`:'';
    let star = m.is_starred?' <span class="star">★</span>':'';
    html+=`<div class="msg ${cls}" onclick="msgOptions(${m.id},'${m.text.replace(/'/g,"").substring(0,80)}',${isMine})">${inner}<span class="mTime">${m.time}${star}</span>${react}</div>`;
  });
  area.innerHTML=html; area.scrollTop=area.scrollHeight;
}
function msgOptions(id, txt, isMine){
  let delBtn = isMine?`<button class="btn btnRed" onclick="deleteMsg(${id})">Delete for Everyone</button>`:'';
  openModal(`<h3>Message Options</h3><p>${txt}</p><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px"><button class="btn" style="width:auto" onclick="reactMsg(${id},'❤️')">❤️</button><button class="btn" style="width:auto" onclick="reactMsg(${id},'😂')">😂</button><button class="btn" style="width:auto" onclick="reactMsg(${id},'🔥')">🔥</button><button class="btn" style="width:auto" onclick="reactMsg(${id},'👍')">👍</button><button class="btn" style="width:auto" onclick="reactMsg(${id},'😮')">😮</button></div><button class="btn btn2" onclick="starMsg(${id})">⭐ Star / Unstar</button><button class="btn btn2" onclick="replyMsg(${id},'${txt}')">↩️ Reply</button><button class="btn btn2" onclick="forwardMsg(${id})">➡️ Forward</button>${delBtn}<button class="btn btnGrey" onclick="closeModal()">Close</button>`);
}
async function reactMsg(id, em){ await fetch('/api/react',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id, reaction:em})}); closeModal(); loadMessages(); }
async function starMsg(id){ await fetch('/api/star',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})}); closeModal(); loadMessages(); }
function replyMsg(id, txt){ REPLY_ID=id; REPLY_TEXT=txt; closeModal(); show('msgInput').placeholder='Replying to: '+txt.substring(0,30)+'...'; show('msgInput').focus(); }
async function forwardMsg(id){
  let to = prompt('Enter UID to forward to:'); if(!to) return;
  await fetch('/api/forward',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id, my_uid:ME.uid, to_uid:to})}); closeModal(); alert('Forwarded'); loadMessages();
}
async function deleteMsg(id){ if(!confirm('Delete for everyone? It will show as "This message was deleted"')) return; await fetch('/api/delete-msg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id, my_uid:ME.uid})}); closeModal(); loadMessages(); }
async function sendMsg(){
  let t=show('msgInput').value.trim(); if(!t) return;
  if(t.length>500){alert('Max 500 characters');return}
  let r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid, to_uid:CUR, text:t, type:'text', reply_to_id:REPLY_ID, reply_to_text:REPLY_TEXT})});
  let d=await r.json(); if(!d.success){alert(d.error);return}
  show('msgInput').value=''; show('msgInput').placeholder='Message...'; REPLY_ID=null; REPLY_TEXT=''; loadMessages();
}
function toggleEmoji(){ let e=show('emojiBar'); e.style.display = e.style.display==='flex'?'none':'flex'; }
function addEmoji(em){ show('msgInput').value+=em; show('msgInput').focus(); }
async function sendImage(inp){
  let f=inp.files[0]; if(!f) return;
  let reader=new FileReader();
  reader.onload=async function(){
    let img=new Image(); img.onload=async function(){
      let c=document.createElement('canvas'); let w=360; let h=img.height*(360/img.width); c.width=w; c.height=h; c.getContext('2d').drawImage(img,0,0,w,h);
      let data=c.toDataURL('image/jpeg',0.7);
      let r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,to_uid:CUR,text:'Photo',type:'image',image_data:data})});
      let d=await r.json(); if(!d.success) alert(d.error); loadMessages();
    }; img.src=reader.result;
  }; reader.readAsDataURL(f);
}
function sendVoice(){ alert('Voice Message: Max 15 sec. This demo sends a voice placeholder. Voice auto-deletes in 20 minutes.'); fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,to_uid:CUR,text:'Voice Message',type:'voice'})}).then(()=>loadMessages()); }
function openChatInfo(){
  openModal(`<h3>Chat Info</h3><p>${CUR_NAME}</p><button class="btn btn2" onclick="openStarred()">⭐ Starred Messages</button><button class="btn btn2" onclick="reportUser()">🚩 Report User</button><button class="btn btn2" onclick="blockUser()">🚫 Block User</button><button class="btn btnGrey" onclick="clearChat()">🧹 Clear Chat</button><button class="btn btnRed" onclick="closeModal();closeChat()">Close</button>`);
}
async function openStarred(){
  let r=await fetch(`/api/starred?my_uid=${ME.uid}&other_uid=${CUR}`); let d=await r.json();
  let h=`<h3>⭐ Starred Messages</h3>`; if(!d.starred.length) h+=`<p>No starred messages</p>`;
  d.starred.forEach(m=>{h+=`<div class="card" style="padding:10px"><b>${m.from}</b> • ${m.time}<br>${m.text}</div>`});
  h+=`<button class="btn btnGrey" onclick="closeModal()">Close</button>`; openModal(h);
}
async function reportUser(){
  let reason=prompt('Report reason: Scam / Harassment / Fake / Spam / Other'); if(!reason) return;
  let detail=prompt('Details (max 400 letters):')||'';
  await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,reported_uid:CUR,reason,detail})});
  alert('Report sent to Admin'); closeModal();
}
async function blockUser(){
  if(!confirm('Block this user?')) return;
  await fetch('/api/block',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,target_uid:CUR,action:'block'})});
  alert('User blocked'); closeModal(); closeChat();
}
async function clearChat(){
  if(!confirm('Clear all messages in this chat?')) return;
  await fetch('/api/clear-chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,other_uid:CUR})});
  closeModal(); loadMessages();
}
async function callUser(type){
  await fetch('/api/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,to_uid:CUR,type})});
  alert('Calling '+CUR_NAME+' ('+type+')... This is a call log demo. Real calling comes in next update.');
}
// POSTS
async function createPost(){
  let cap=val('postCaption'), song=val('postSong');
  let file=show('postImage').files[0]; let imgData='';
  if(file){
    imgData=await new Promise(res=>{ let rd=new FileReader(); rd.onload=()=>{ let im=new Image(); im.onload=()=>{ let c=document.createElement('canvas'); let w=360; let h=im.height*(360/im.width); c.width=w; c.height=h; c.getContext('2d').drawImage(im,0,0,w,h); res(c.toDataURL('image/jpeg',0.7)); }; im.src=rd.result; }; rd.readAsDataURL(file); });
  }
  let r=await fetch('/api/posts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,caption:cap,song:song,image_data:imgData})});
  let d=await r.json(); if(!d.success){alert(d.error);return}
  show('postCaption').value=''; show('postSong').value=''; show('postImage').value=''; alert('Post created'); loadPosts();
}
async function loadPosts(){
  if(!ME) return;
  let r=await fetch(`/api/posts?my_uid=${ME.uid}`); let d=await r.json();
  let list=show('postList'); if(!d.posts||d.posts.length===0){ list.innerHTML=`<div class="empty"><b>No posts yet</b><br>Be the first to post a photo</div>`; return; }
  let html='';
  d.posts.forEach(p=>{
    let commentsHtml=''; p.comments.forEach(c=>{ commentsHtml+=`<div style="margin-top:6px"><b>${c.name}</b> ${c.text} <span style="color:#999;font-size:11px">${c.time}</span></div>` });
    let delBtn = p.uid===ME.uid?`<span onclick="deletePost(${p.id})" style="color:#e53935">🗑️ Delete</span>`:'';
    html+=`<div class="card"><div class="cardHead"><div class="avatar" style="background:${p.avatar_color}">${p.name.charAt(0)}</div><div style="flex:1"><b>${p.name} ${tickHtml(p.tick)}</b><br><span style="font-size:11px;color:#667781">@${p.username} • ${p.time}</span></div>${delBtn}</div>${p.caption?`<div style="padding:0 14px 10px">${p.caption}</div>`:''}${p.image_data?`<img class="postImg" src="${p.image_data}">`:''}${p.song?`<div class="songBox">🎵 Song: ${p.song}</div>`:''}<div class="postActions"><span class="${p.liked?'liked':''}" onclick="likePost(${p.id},this)">❤️ ${p.likes}</span><span onclick="document.getElementById('cmt-${p.id}').focus()">💬 ${p.comments.length}</span><span onclick="sharePost(${p.id})">↗️ Share</span></div><div class="commentBox">${commentsHtml}</div><div class="commentInput"><input id="cmt-${p.id}" placeholder="Add a comment..."><button onclick="commentPost(${p.id})">Send</button></div></div>`;
  });
  list.innerHTML=html;
}
async function likePost(id, el){ let r=await fetch('/api/post-like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,my_uid:ME.uid})}); let d=await r.json(); if(d.success) loadPosts(); }
async function commentPost(id){ let t=show('cmt-'+id).value.trim(); if(!t) return; await fetch('/api/post-comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,my_uid:ME.uid,text:t})}); loadPosts(); }
async function deletePost(id){ if(!confirm('Delete this post?')) return; await fetch('/api/post-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,my_uid:ME.uid})}); loadPosts(); }
function sharePost(id){ alert('Post link copied: MyQchat Post #'+id); }
// STATUS & CALLS
async function postStatus(){ let t=val('statusText'); if(!t) return; await fetch('/api/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,text:t})}); show('statusText').value=''; loadStatus(); }
async function loadStatus(){
  if(!ME) return; let r=await fetch('/api/status'); let d=await r.json();
  let list=show('statusList'); if(!d.status||d.status.length===0){ list.innerHTML=`<div class="empty"><b>No status updates</b><br>Post your first status</div>`; return; }
  list.innerHTML=d.status.map(s=>`<div class="statusCard"><div class="avatar" style="background:#075e54">${s.name.charAt(0)}</div><div><b>${s.name}</b><br><span>${s.text}</span><br><span style="font-size:11px;color:#999">${s.time} • Auto-deletes in 24h</span></div></div>`).join('');
}
async function loadCalls(){
  if(!ME) return; let r=await fetch(`/api/calls?uid=${ME.uid}`); let d=await r.json();
  let list=show('callList'); if(!d.calls||d.calls.length===0){ list.innerHTML=`<div class="empty"><b>No calls yet</b><br>Tap phone icon in chat to call</div>`; return; }
  list.innerHTML=d.calls.map(c=>`<div class="callRow"><div class="avatar" style="background:#009688">📞</div><div style="flex:1"><b>${c.from}</b><br><span style="font-size:12px;color:#667781">${c.type} • ${c.status}</span></div><span style="font-size:11px;color:#999">${c.time}</span></div>`).join('');
}
</script>"""
# ================= PART 6 - SETTINGS + ADMIN JS + FINAL RUN - ENGLISH ONLY =================
SETTINGS_JS = r"""<script>
async function loadSettingsPage(){
  if(!ME) return;
  // Fetch fresh ME
  let r=await fetch(`/api/me?uid=${ME.uid}`); let d=await r.json();
  if(d.success) ME=d.user;
  show('setName').innerText = ME.name + ' ' + (ME.tick ? '('+ME.tick+' ✓)' : '');
  show('setUid').innerText = 'UID: ' + ME.uid + ' • @' + ME.username;
  show('setAvatar').innerText = ME.name.charAt(0).toUpperCase();
  show('setAvatar').style.background = ME.avatar_color||'#075e54';
  show('setTickLine').innerText = ME.tick ? 'Tick: '+ME.tick+' ✓' : 'No Tick yet - Request from below';
  show('recoveryLine').innerText = ME.has_recovery_email ? 'Added: '+ME.recovery_email : 'Not added - Add for password recovery';
  // Dark mode toggle
  show('darkToggle').classList.toggle('on', !!ME.dark_mode);
  document.body.classList.toggle('dark', !!ME.dark_mode);
  show('notifToggle').classList.toggle('on', ME.notifications!==false);
  // Admin section - ONLY for LoyalWQ - Hidden for others
  if(ME.username==='LoyalWQ' && ME.is_admin){
    show('adminSection').style.display='block';
    loadAdminStats();
  } else {
    show('adminSection').style.display='none';
  }
  // Blocked count
  let rb=await fetch(`/api/blocked-list?uid=${ME.uid}`); let bd=await rb.json();
  show('blockedCount').innerText = (bd.blocked?bd.blocked.length:0) + ' blocked';
}
function toggleDark(e){
  e.stopPropagation();
  let on = !show('darkToggle').classList.contains('on');
  show('darkToggle').classList.toggle('on', on);
  document.body.classList.toggle('dark', on);
  fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,dark_mode:on})});
}
function toggleNotif(e){
  e.stopPropagation();
  let on = !show('notifToggle').classList.contains('on');
  show('notifToggle').classList.toggle('on', on);
  fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,notifications:on})});
}
function setWallpaper(w, el){
  document.querySelectorAll('.wallOpt').forEach(x=>x.classList.remove('on')); el.classList.add('on');
  let area = document.querySelector('.chatArea');
  if(w==='green') area.style.background='#d9fdd3';
  else if(w==='blue') area.style.background='#dbeafe';
  else if(w==='dark') area.style.background='#0b141a';
  else area.style.background='#ece5dd';
  fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,wallpaper:w})});
}
function openEditProfile(){
  openModal(`<h3>Edit Profile</h3><label>Your Name</label><input id="e_name" class="inp" value="${ME.name}"><label>Bio (max 200)</label><textarea id="e_bio" class="inp" rows="2">${ME.bio||''}</textarea><label>Profile Colour</label><div style="display:flex;gap:8px;margin-top:10px"><div onclick="document.getElementById('e_color').value='#075e54'" style="width:36px;height:36px;border-radius:50%;background:#075e54;cursor:pointer"></div><div onclick="document.getElementById('e_color').value='#7b1fa2'" style="width:36px;height:36px;border-radius:50%;background:#7b1fa2;cursor:pointer"></div><div onclick="document.getElementById('e_color').value='#e91e63'" style="width:36px;height:36px;border-radius:50%;background:#e91e63;cursor:pointer"></div><div onclick="document.getElementById('e_color').value='#ff5722'" style="width:36px;height:36px;border-radius:50%;background:#ff5722;cursor:pointer"></div><div onclick="document.getElementById('e_color').value='#3f51b5'" style="width:36px;height:36px;border-radius:50%;background:#3f51b5;cursor:pointer"></div></div><input id="e_color" class="inp" value="${ME.avatar_color}"><button class="btn" onclick="saveProfile()">Save Profile</button><button class="btn btnGrey" onclick="closeModal()">Cancel</button>`);
}
async function saveProfile(){
  let r=await fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,name:val('e_name'),bio:show('e_bio').value,avatar_color:val('e_color')})});
  let d=await r.json(); alert(d.msg||'Saved'); closeModal(); loadSettingsPage(); loadUsers();
}
function openRecoveryEmail(){
  openModal(`<h3>Recovery Email</h3><p>Optional. Only for password recovery. We do not share it.</p><label>Recovery Email</label><input id="rec_email" class="inp" placeholder="example@gmail.com" value="${ME.recovery_email||''}"><button class="btn" onclick="saveRecovery()">Save Email</button><button class="btn btnGrey" onclick="removeRecovery()">Remove Email</button><button class="btn btnGrey" onclick="closeModal()">Cancel</button>`);
}
async function saveRecovery(){
  let r=await fetch('/api/update-recovery-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,email:val('rec_email')})});
  let d=await r.json(); alert(d.msg||d.error); if(d.success){closeModal(); loadSettingsPage();}
}
async function removeRecovery(){
  await fetch('/api/update-recovery-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,email:''})});
  alert('Recovery Email removed'); closeModal(); loadSettingsPage();
}
function openTickRequest(){
  openModal(`<h3>Request Tick</h3><p>You can request Blue, Orange or Green Tick. Admin will approve or reject. L Tick is only for Owner. Scam Tick cannot be requested.</p><label>Choose Tick</label><select id="tick_choice" class="inp"><option value="Blue">Blue ✓ - Trusted User</option><option value="Orange">Orange ✓ - Active Creator</option><option value="Green">Green ✓ - Verified Member</option></select><label>Why do you need Tick? (Min 5 letters)</label><textarea id="tick_reason" class="inp" rows="3" placeholder="I am active, I help users..."></textarea><button class="btn" onclick="sendTickRequest()">Send Request</button><button class="btn btnGrey" onclick="closeModal()">Cancel</button>`);
}
async function sendTickRequest(){
  let r=await fetch('/api/tick-request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,tick:val('tick_choice'),reason:show('tick_reason').value})});
  let d=await r.json(); alert(d.msg||d.error); if(d.success) closeModal();
}
async function openMyTickStatus(){
  let r=await fetch(`/api/my-tick-request?uid=${ME.uid}`); let d=await r.json();
  let h=`<h3>My Tick Requests</h3>`; if(!d.requests.length) h+=`<p>No requests yet. Request from Settings > Request Tick.</p>`;
  d.requests.forEach(x=>{ h+=`<div class="card" style="padding:10px"><b>${x.tick} ✓</b> • ${x.status}<br><span style="font-size:12px;color:#666">${x.reason}</span><br><span style="font-size:11px;color:#999">${x.time} ${x.admin_note?'• '+x.admin_note:''}</span></div>` });
  h+=`<button class="btn btnGrey" onclick="closeModal()">Close</button>`; openModal(h);
}
function openPrivacy(){
  openModal(`<h3>Privacy</h3><label>Last Seen Privacy</label><select id="priv_seen" class="inp"><option value="everyone">Everyone</option><option value="contacts">Contacts Only</option><option value="nobody">Nobody</option></select><label style="margin-top:12px"><input type="checkbox" id="priv_read" ${ME.read_receipts?'checked':''}> Read Receipts (Blue ticks)</label><button class="btn" onclick="savePrivacy()">Save Privacy</button><button class="btn btnGrey" onclick="closeModal()">Cancel</button>`);
  show('priv_seen').value = ME.privacy_last_seen||'everyone';
}
async function savePrivacy(){
  await fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,privacy_last_seen:val('priv_seen'),read_receipts:show('priv_read').checked})});
  alert('Privacy saved'); closeModal(); loadSettingsPage();
}
async function openBlocked(){
  let r=await fetch(`/api/blocked-list?uid=${ME.uid}`); let d=await r.json();
  let h=`<h3>Blocked Users</h3>`; if(!d.blocked.length) h+=`<p>No blocked users.</p>`;
  d.blocked.forEach(u=>{ h+=`<div class="userRow"><div class="avatar" style="background:${u.avatar_color}">${u.name.charAt(0)}</div><div class="userInfo"><b>${u.name}</b><span>@${u.username}</span></div><button class="btn" style="width:auto;margin:0;padding:6px 12px" onclick="unblockUser('${u.uid}')">Unblock</button></div>` });
  h+=`<button class="btn btnGrey" onclick="closeModal()">Close</button>`; openModal(h);
}
async function unblockUser(uid){
  await fetch('/api/block',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,target_uid:uid,action:'unblock'})});
  alert('Unblocked'); closeModal(); openBlocked();
}
function openChangePass(){
  openModal(`<h3>Change Password</h3><label>Old Password</label><input id="old_pw" type="password" class="inp" placeholder="Old Password"><label>New Password</label><input id="new_pw" type="password" class="inp" placeholder="New Password - Min 4 letters"><button class="btn" onclick="saveNewPass()">Change Password</button><button class="btn btnGrey" onclick="closeModal()">Cancel</button>`);
}
async function saveNewPass(){
  let r=await fetch('/api/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid,old_password:show('old_pw').value,new_password:show('new_pw').value})});
  let d=await r.json(); alert(d.msg||d.error); if(d.success) closeModal();
}
function openDeleteAccount(){
  openModal(`<h3 style="color:#e53935">Delete Account</h3><p>Permanent Delete. Your account will be deleted after 15 days. Within 15 days you can cancel from Settings and appeal. After 15 days deletion is final.</p><button class="btn btnRed" onclick="confirmDelete()">Request Delete</button><button class="btn btnGrey" onclick="cancelDeleteReq()">Cancel Delete Request</button><button class="btn btnGrey" onclick="closeModal()">Close</button>`);
}
async function confirmDelete(){
  if(!confirm('Are you sure? Account will be deleted in 15 days.')) return;
  let r=await fetch('/api/delete-account',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid})});
  let d=await r.json(); alert(d.msg||d.error); closeModal();
}
async function cancelDeleteReq(){
  await fetch('/api/cancel-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid})});
  alert('Delete cancelled. Account is safe.'); closeModal();
}
function openHelp(){
  openModal(`<h3>Help & Support</h3><p>Need help? Contact QWNG Team.</p><div class="card" style="padding:12px"><b>Owner:</b> LoyalWQ<br><b>App:</b> MyQchat by QWNG<br><b>Version:</b> V3 - Final<br><b>Support:</b> Go to Settings > Help & Support<br><br>For Report: Open Chat > ⋮ > Report User<br>For Appeal: Contact Admin within 15 days</div><button class="btn btnGrey" onclick="closeModal()">Close</button>`);
}
function openAbout(){
  openModal(`<h3>About MyQchat</h3><div style="text-align:center"><div class="authLogo" style="margin:0 auto">Q</div><h3 style="margin-top:10px">MyQchat</h3><p>Developed by QWNG<br>Owner: LoyalWQ<br>Version V3 - Final<br><br>Chat, Friends, Groups, Status & More<br>Free, Fast & Secure</p></div><button class="btn btnGrey" onclick="closeModal()">Close</button>`);
}
// ---------- ADMIN JS - ONLY FOR LOYALWQ ----------
async function loadAdminStats(){
  let r=await fetch(`/api/admin/stats?admin_uid=${ME.uid}`); let d=await r.json();
  if(d.success){
    let s=d.stats;
    show('adminStats').innerHTML=`Users: <b>${s.total_users}</b> • Online: <b>${s.online_users}</b><br>Messages: <b>${s.total_messages}</b> • Posts: <b>${s.total_posts}</b><br>Reports: <b>${s.total_reports}</b> • Pending Ticks: <b>${s.pending_ticks}</b> • Groups: <b>${s.total_groups}</b>`;
  }
}
async function openAdminUsers(){
  let r=await fetch(`/api/admin/users?admin_uid=${ME.uid}`); let d=await r.json();
  let h=`<h3>All Users</h3>`; d.users.forEach(u=>{
    h+=`<div class="card" style="padding:10px"><b>${u.name} ${u.tick?'('+u.tick+' ✓)':''}</b> • @${u.username} • UID ${u.uid}<br><span style="font-size:12px;color:#666">${u.online?'Online':'Offline'} • ${u.bio}</span><br><div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap"><button class="btn" style="width:auto;margin:0;padding:6px 10px;font-size:12px" onclick="adminAction('${u.uid}','give_tick','Blue')">Give Blue</button><button class="btn" style="width:auto;margin:0;padding:6px 10px;font-size:12px" onclick="adminAction('${u.uid}','scam_tick')">Scam</button><button class="btn" style="width:auto;margin:0;padding:6px 10px;font-size:12px" onclick="adminAction('${u.uid}','remove_tick')">Remove Tick</button><button class="btn btnRed" style="width:auto;margin:0;padding:6px 10px;font-size:12px" onclick="adminAction('${u.uid}','ban')">Ban 7 Days</button></div></div>`;
  });
  h+=`<button class="btn btnGrey" onclick="closeModal()">Close</button>`; openModal(h);
}
async function adminAction(uid, action, tick){
  let days = action==='ban' ? prompt('Ban for how many days?','7') : 7;
  let r=await fetch('/api/admin/user-action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_uid:ME.uid,target_uid:uid,action:action,tick:tick||'Blue',days:days})});
  let d=await r.json(); alert(d.msg||d.error); closeModal(); loadAdminStats();
}
async function openAdminTicks(){
  let r=await fetch(`/api/admin/tick-requests?admin_uid=${ME.uid}`); let d=await r.json();
  let h=`<h3>Tick Requests</h3>`; if(!d.requests.length) h+=`<p>No requests.</p>`;
  d.requests.forEach(x=>{
    h+=`<div class="card" style="padding:10px"><b>${x.name} (@${x.username})</b> wants <b>${x.tick} ✓</b> • ${x.status}<br><span style="font-size:12px">${x.reason}</span><br><span style="font-size:11px;color:#999">${x.time}</span><br>${x.status==='pending'?`<div style="display:flex;gap:6px;margin-top:8px"><button class="btn" style="width:auto;margin:0" onclick="tickAction(${x.id},'approve')">Approve</button><button class="btn btnRed" style="width:auto;margin:0" onclick="tickAction(${x.id},'reject')">Reject</button></div>`:''}</div>`;
  });
  h+=`<button class="btn btnGrey" onclick="closeModal()">Close</button>`; openModal(h);
}
async function tickAction(id, action){
  let note = prompt('Admin note (optional):','')||'';
  await fetch('/api/admin/tick-action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_uid:ME.uid,request_id:id,action:action,note:note})});
  alert('Tick '+action); closeModal(); openAdminTicks(); loadAdminStats();
}
async function openAdminReports(){
  let r=await fetch(`/api/reports?admin_uid=${ME.uid}`); let d=await r.json();
  let h=`<h3>Reports</h3>`; if(!d.reports.length) h+=`<p>No reports.</p>`;
  d.reports.forEach(x=>{
    h+=`<div class="card" style="padding:10px"><b>Reporter:</b> ${x.reporter}<br><b>Reported:</b> ${x.reported_name} (${x.reported_uid}) ${x.reported_tick}<br><b>Reason:</b> ${x.reason}<br><span style="font-size:12px">${x.detail}</span><br><span style="font-size:11px;color:#999">${x.time}</span><br><div style="display:flex;gap:6px;margin-top:8px"><button class="btn" style="width:auto;margin:0" onclick="reportAction(${x.id},'scam')">Scam Tick</button><button class="btn btnRed" style="width:auto;margin:0" onclick="reportAction(${x.id},'delete')">Delete Msgs</button><button class="btn btnGrey" style="width:auto;margin:0" onclick="reportAction(${x.id},'ignore')">Ignore</button></div></div>`;
  });
  h+=`<button class="btn btnGrey" onclick="closeModal()">Close</button>`; openModal(h);
}
async function reportAction(id, action){
  await fetch('/api/admin/report-action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_uid:ME.uid,report_id:id,action:action})});
  alert('Report handled: '+action); closeModal(); openAdminReports(); loadAdminStats();
}
function openBroadcast(){
  openModal(`<h3>Broadcast via QWNG Bot</h3><p>Message will go to all users as QWNG Bot.</p><label>Tag</label><select id="bc_tag" class="inp"><option>Announcement</option><option>Warning</option><option>Ad</option></select><label>Message (Max 500)</label><textarea id="bc_text" class="inp" rows="3" placeholder="Hello everyone..."></textarea><button class="btn" onclick="sendBroadcast()">Send to All</button><button class="btn btnGrey" onclick="closeModal()">Cancel</button>`);
}
async function sendBroadcast(){
  let r=await fetch('/api/admin/broadcast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({admin_uid:ME.uid,text:show('bc_text').value,tag:val('bc_tag')})});
  let d=await r.json(); alert(d.msg||d.error); if(d.success) closeModal();
}
async function ownerBackup(){
  let r=await fetch(`/api/owner-backup?admin_uid=${ME.uid}`); let d=await r.json();
  if(!d.success){alert(d.error);return}
  openModal(`<h3>Owner Backup</h3><p>Exported: ${d.backup.exported_at}</p><div class="card" style="padding:12px">Users: ${d.backup.users.length}<br>Messages: ${d.backup.messages}<br>Posts: ${d.backup.posts}<br>Reports: ${d.backup.reports}</div><p style="font-size:12px;color:#666">Backup is message-only summary. Full DB backup is in Render / Supabase.</p><button class="btn btnGrey" onclick="closeModal()">Close</button>`);
}
// Auto-login if UID saved
window.onload = function(){
  let saved = localStorage.getItem('myqchat_uid');
  let g = new URLSearchParams(location.search).get('google_uid');
  let uid = g || saved;
  if(uid){
    fetch(`/api/me?uid=${uid}`).then(r=>r.json()).then(d=>{
      if(d.success){ ME=d.user; afterLogin(); }
    });
  }
};
</script></body></html>"""

# FINAL HOME - FRONTEND + JS COMBINED
@app.route("/app")
def app_page():
    return FRONTEND + FRONTEND_JS + SETTINGS_JS

# Override / to serve full app (FRONTEND already has </body> missing JS, so we serve combined)
@app.route("/")
def home():
    return FRONTEND + FRONTEND_JS + SETTINGS_JS
# ================= PART 7-A - QWNG BOT - DEFAULT CHAT - SCRIPTED FAKE AI - AUTOCORRECT =================
# Bot AI nahi hai - Scripted hai - Possible Questions -> Fixed Response
# Autocorrect: hilp -> help, helo -> hello, tik -> tick, pasword -> password

import re, difflib

BOT_UID = "QWNG_BOT"
BOT_NAME = "QWNG Bot"

# ---- AUTOCORRECT DICTIONARY ----
CORRECT_MAP = {
    "hilp":"help","hepl":"help","halp":"help","hep":"help","hlep":"help",
    "helo":"hello","hii":"hi","hiii":"hi","hey":"hi","hellow":"hello",
    "tik":"tick","tic":"tick","tikc":"tick","tickk":"tick",
    "pasword":"password","paswrod":"password","pass":"password","passward":"password",
    "seting":"settings","setings":"settings","settting":"settings","setting":"settings",
    "acount":"account","acconut":"account","accout":"account",
    "delet":"delete","delet":"delete","dlete":"delete","deletaccount":"delete account",
    "repot":"report","repoert":"report","raport":"report",
    "blok":"block","blcok":"block","bolck":"block",
    "chat":"chat","caht":"chat","chatt":"chat",
    "grup":"group","goup":"group","grop":"group",
    "post":"post","posst":"post","pots":"post",
    "statu":"status","staus":"status","stats":"status",
    "cal":"call","coll":"call",
    "emai":"email","emial":"email","mail":"email",
    "logn":"login","logni":"login","singup":"signup","sigup":"signup",
    "onlie":"online","ofline":"offline",
    "brodcast":"broadcast","bordcast":"broadcast",
    "admin":"admin","admn":"admin",
    "ownr":"owner","onwer":"owner",
    "privecy":"privacy","privcy":"privacy",
    "term":"terms","terms":"terms","condition":"terms",
    "wallpaper":"wallpaper","walpaper":"wallpaper",
    "dark":"dark mode","drak":"dark mode",
    "photo":"photo","phto":"photo","pic":"photo","image":"photo",
    "song":"song","sng":"song",
    "uid":"uid","id":"uid",
    "contact":"contact","contct":"contact",
    "frend":"friend","freind":"friend",
    "problm":"problem","problem":"problem","issue":"problem",
    "thanku":"thank you","thank":"thank you","tnx":"thank you",
    "bye":"bye","byee":"bye",
    "ok":"ok","okey":"ok","okk":"ok",
}

ALL_KEYWORDS = list(CORRECT_MAP.keys()) + ["help","hello","hi","tick","password","settings","account","delete","report","block","chat","group","post","status","call","email","login","signup","online","broadcast","admin","owner","privacy","terms","wallpaper","dark mode","photo","song","uid","contact","friend","problem","thank you","bye","ok","how are you","who are you","what can you do","features","price","free","safe","owner name","your name","backup","export","star","forward","reply","emoji","voice","video","search"]

def autocorrect_text(text):
    # Lower + clean
    raw = text.lower().strip()
    words = re.findall(r"[a-z]+", raw)
    fixed_words = []
    for w in words:
        if w in CORRECT_MAP:
            fixed_words.append(CORRECT_MAP[w])
        else:
            # Fuzzy match - 80% similar to known keyword
            close = difflib.get_close_matches(w, ALL_KEYWORDS, n=1, cutoff=0.78)
            if close:
                fixed_words.append(close[0])
            else:
                fixed_words.append(w)
    fixed = " ".join(fixed_words)
    # Multi-word fix: "delet account" -> "delete account"
    fixed = fixed.replace("delet account","delete account").replace("dlete account","delete account")
    fixed = fixed.replace("change pasword","change password").replace("change password","change password")
    return fixed

def get_bot_reply(user_text, me_uid, me_name):
    orig = user_text.strip()
    t = autocorrect_text(orig)
    tl = t.lower()
    # Save corrected flag
    was_corrected = (t.lower() != orig.lower())
    prefix = ""
    if was_corrected and len(orig) > 2:
        prefix = f"Did you mean: \"{t}\"? I understood it as that.\n\n"

    # ===== 1. GREETING =====
    if any(x in tl for x in ["hello","hi","hey","hii","good morning","good evening","namaste"]):
        return prefix + f"Hello {me_name}! 👋 Welcome to MyQchat.\nI am QWNG Bot. I can help you.\n\nType **help** to see all options.\n\nWhat do you want help with?\n1. Tick\n2. Password\n3. Account Delete\n4. Report / Block\n5. Chat / Group / Post\n6. Settings\n\nJust type the number or word. Example: Type **1** or **tick**"

    # ===== 2. HELP MENU - MAIN =====
    if tl in ["help","help me","i need help","need help","menu","options","what can you do","features"]:
        return prefix + "Sure! What do you need help with? Please choose one option:\n\n1️⃣ Tick - How to get Tick?\n2️⃣ Password - Forgot / Change Password?\n3️⃣ Account - Delete / Recovery Email?\n4️⃣ Chat - How to chat, Add Contact?\n5️⃣ Group - How to create Group?\n6️⃣ Post - How to post Photo + Song?\n7️⃣ Report / Block - How to Report someone?\n8️⃣ Settings - Dark Mode, Wallpaper, Privacy?\n9️⃣ Terms - Terms & Privacy Policy?\n🔟 Owner / Admin - Who is Owner?\n\nType the number. Example: Type **2** for Password help."

    # ===== 3. TICK =====
    if tl in ["1","tick","tick help","how to get tick","get tick","tick request"] or "tick" in tl:
        if "request" in tl or "get" in tl or "how" in tl or tl=="1" or tl=="tick":
            return prefix + "✔️ **Tick Help**\n\nYou can request Blue, Orange or Green Tick.\n\nSteps:\n1. Go to Settings\n2. Tap Request Tick\n3. Choose Blue / Orange / Green\n4. Write Reason\n5. Tap Send Request\n\nAdmin will Approve or Reject.\n\n⚠️ L Tick is only for Owner. It cannot be requested.\nScam Tick cannot be requested. It is given after Report.\n\nType **help** to go back to menu."

    # ===== 4. PASSWORD =====
    if tl in ["2","password","forgot password","change password","reset password"] or "password" in tl:
        if "forgot" in tl or "reset" in tl:
            return prefix + "🔑 **Forgot Password?**\n\nIf you added Recovery Email in Settings, use it to recover.\n\nSteps:\n1. Go to Settings > Recovery Email\n2. Check if Email is added\n3. If not added, you cannot recover. Create new account.\n\nTo avoid this, add Recovery Email NOW from Settings.\n\nType **help** for menu."
        if "change" in tl or tl=="2":
            return prefix + "🔑 **Change Password**\n\nSteps:\n1. Go to Settings\n2. Tap Change Password\n3. Enter Old Password\n4. Enter New Password (Min 4 letters)\n5. Tap Change\n\nDone! Your password is changed.\n\nType **help** for menu."
        return prefix + "🔑 **Password Help**\n\nType:\n- **forgot password** - If you forgot password\n- **change password** - If you want to change password\n\nType **help** for menu."

    # ===== 5. ACCOUNT / DELETE / EMAIL =====
    if tl in ["3","account","delete account","delete","recovery email","recovery"] or "delete" in tl or "recovery" in tl or "account" in tl:
        if "delete" in tl:
            return prefix + "🗑️ **Delete Account**\n\nSteps:\n1. Go to Settings\n2. Tap Delete Account\n3. Tap Request Delete\n\nYour account will be deleted after 15 days.\nWithin 15 days, you can Cancel Delete from Settings and Appeal.\nAfter 15 days, deletion is final.\n\nAre you sure? Type **yes delete** to continue, or **help** for menu."
        if "recovery" in tl or "email" in tl:
            return prefix + "📧 **Recovery Email**\n\nEmail is NOT needed for Signup.\nYou can add it later in Settings.\n\nSteps:\n1. Go to Settings\n2. Tap Recovery Email\n3. Enter Email\n4. Tap Save\n\nIt is used only for password recovery. We do not share it.\n\nType **help** for menu."
        return prefix + "👤 **Account Help**\n\nType:\n- **delete account** - To delete account\n- **recovery email** - To add Recovery Email\n- **change password** - To change password\n\nType **help** for menu."

    # ===== 6. CHAT / CONTACT / UID =====
    if tl in ["4","chat","how to chat","add contact","uid","contact","friend"] or "chat" in tl or "contact" in tl or "uid" in tl or "friend" in tl:
        return prefix + "💬 **Chat Help**\n\n**How to Chat?**\n1. Go to Chats tab\n2. Tap + button\n3. Enter Friend's 8-digit UID\n4. Tap Search > Add\n5. Now tap their name and chat\n\n**UID Kya Hai?**\nUID is your 8-digit Permanent ID. Example: 12345678\nYou can see your UID in Settings on top.\nShare your UID with friends to get added.\n\n**Unknown Limit:**\nIf you are not in contacts, you can send only 2 messages, Max 30 letters each.\nSave to contacts for full chat.\n\nType **help** for menu."

    # ===== 7. GROUP =====
    if tl in ["5","group","create group","how to group"] or "group" in tl:
        return prefix + "👥 **Group Help**\n\nTo create Group:\n1. Go to Chats\n2. Tap + > Create Group (In next update, Group button will be in Chats)\n3. Add members by UID\n4. Give Group Name\n5. Tap Create\n\nGroup chat works like normal chat.\n\nType **help** for menu."

    # ===== 8. POST =====
    if tl in ["6","post","how to post","photo","song","post photo"] or "post" in tl or "photo" in tl or "song" in tl:
        return prefix + "📸 **Post Help**\n\nTo create Post:\n1. Go to Posts tab\n2. Write Caption (Max 500 letters)\n3. Add Song Name / Link (Optional) - No MP3 upload\n4. Choose Photo (Optional)\n5. Tap Post\n\nRules:\n- Max 3 posts per day\n- Photo auto-compresses to 360p for speed\n- You can Like and Comment on posts\n- Only owner can delete post\n\nType **help** for menu."

    # ===== 9. REPORT / BLOCK =====
    if tl in ["7","report","block","how to report","how to block"] or "report" in tl or "block" in tl:
        return prefix + "🚩 **Report / Block Help**\n\n**To Report:**\n1. Open Chat of that user\n2. Tap ⋮ (3 dots)\n3. Tap Report User\n4. Choose Reason: Scam / Harassment / Fake / Spam / Other\n5. Write Details (Max 400 letters)\n\n**To Block:**\n1. Open Chat > ⋮ > Block User\n2. To Unblock: Settings > Blocked Users > Unblock\n\nAdmin will check reported message. If guilty, Scam Tick or Ban will be given.\n\nType **help** for menu."

    # ===== 10. SETTINGS =====
    if tl in ["8","settings","dark mode","wallpaper","privacy","notification"] or "settings" in tl or "dark" in tl or "wallpaper" in tl or "privacy" in tl:
        if "dark" in tl:
            return prefix + "🌙 **Dark Mode**\n\nSteps:\n1. Go to Settings\n2. Turn ON Dark Mode toggle\n\nIt is easy on eyes at night.\n\nType **help** for menu."
        if "wallpaper" in tl:
            return prefix + "🎨 **Wallpaper**\n\nSteps:\n1. Go to Settings > Wallpaper\n2. Choose Default / Green / Blue / Dark\n\nType **help** for menu."
        if "privacy" in tl:
            return prefix + "🔒 **Privacy**\n\nSteps:\n1. Go to Settings > Privacy\n2. Choose Last Seen: Everyone / Contacts Only / Nobody\n3. Turn ON/OFF Read Receipts\n\nType **help** for menu."
        return prefix + "⚙️ **Settings Help**\n\nSettings has:\n- Edit Profile\n- Recovery Email\n- Request Tick\n- Dark Mode\n- Wallpaper\n- Privacy\n- Blocked Users\n- Change Password\n- Terms & Conditions\n- Delete Account\n- Logout\n- Admin Panel (Only for Owner)\n\nType **dark mode** or **wallpaper** or **privacy** for detail.\nType **help** for menu."

    # ===== 11. TERMS =====
    if tl in ["9","terms","privacy policy","policy"] or "terms" in tl or "policy" in tl:
        return prefix + "📄 **Terms & Privacy Policy**\n\nTo read full Terms:\n1. Go to Settings\n2. Tap Terms & Conditions\n\nFull page will open. It is policy only, no features.\n\nShort summary:\n- You must be 13+ years old\n- Do not harass, scam, spam\n- Reported messages may be reviewed by Admin for safety\n- You can delete account, 15 days appeal time\n- We do not sell your data\n\nType **help** for menu."

    # ===== 12. OWNER / ADMIN =====
    if tl in ["10","owner","admin","who is owner","your name","who are you"] or "owner" in tl or "admin" in tl or "who are you" in tl:
        return prefix + "👑 **Owner / Admin**\n\nOwner of MyQchat is **LoyalWQ**.\nApp is Developed by **QWNG**.\n\nAdmin Panel is inside Settings. Only Owner can see it.\nAdmin can approve Tick, check Reports, Broadcast, Ban user.\n\nIf you need help from Admin, report from Chat or use Help.\n\nType **help** for menu."

    # ===== 13. HOW ARE YOU / BYE / THANKS =====
    if "how are you" in tl or "how r you" in tl or tl=="how are you":
        return prefix + "I am good! Thanks for asking 😊\nI am QWNG Bot, always online to help you.\n\nType **help** to see what I can do."
    if tl in ["bye","goodbye","see you"]:
        return prefix + "Bye! 👋 Take care.\nCome back anytime. Type **hi** to start again."
    if "thank" in tl or tl=="thanks" or tl=="thank you":
        return prefix + "You are welcome! 😊\nHappy to help.\n\nType **help** if you need anything else."
    if tl in ["ok","okay","okey","good","nice","great"]:
        return prefix + "Great! 👍\n\nType **help** to see all options."
    if tl in ["yes delete","yes","delete yes"]:
        return prefix + "To delete account, go to Settings > Delete Account > Request Delete.\nYour account will be deleted in 15 days. You can cancel within 15 days.\n\nType **help** for menu."
    if "free" in tl or "price" in tl or "cost" in tl:
        return prefix + "MyQchat is 100% FREE. No price. No premium.\nChat, Post, Group, Status - All Free.\n\nType **help** for menu."
    if "safe" in tl or "secure" in tl:
        return prefix + "Yes, MyQchat is Safe.\nWe do not sell your data.\nWe do not share your data for advertising.\nYour Recovery Email is used only for recovery.\n\nType **help** for menu."
    if "backup" in tl or "export" in tl:
        return prefix + "💾 **Backup / Export**\n\nOwner Backup is only for Owner.\nChat Export will come in next update.\n\nType **help** for menu."
    if "star" in tl or "forward" in tl or "reply" in tl or "emoji" in tl or "voice" in tl or "video" in tl or "search" in tl:
        return prefix + "✨ **Chat Features**\n\n- Tap a message to see options: React, Star, Reply, Forward, Delete\n- Emoji button for emojis\n- Attach button for Photo\n- Mic button for Voice\n- Search icon to search in chat\n\nType **help** for menu."

    # ===== 14. NUMBERS 1-10 already handled above, but if user types just number with extra text =====
    if tl in ["1","2","3","4","5","6","7","8","9","10"]:
        return get_bot_reply(tl, me_uid, me_name)  # recursion safe - will hit above

    # ===== 15. FALLBACK - DID NOT UNDERSTAND =====
    return prefix + "Sorry, I didn't understand that. 😅\n\nI am not real AI. I am a scripted Bot. I only understand these words.\n\nPlease choose one option:\n\nType **help** to see all options.\n\nOr try:\n- help\n- tick\n- password\n- chat\n- post\n- report\n- settings\n- terms\n\nWhat do you want help with?"

# ---------- BOT API - SEND TO BOT + GET REPLY ----------
@app.route("/api/bot-chat", methods=["POST"])
def bot_chat_api():
    try:
        d = request.get_json(force=True)
        my_uid = d.get("my_uid"); text = (d.get("text") or "").strip()
        if not text: return jsonify({"success":False,"error":"Empty"}),400
        me_u = User.query.filter_by(uid=my_uid).first()
        if not me_u: return jsonify({"success":False,"error":"User not found"}),404
        # 1. Save user message to Bot
        m1 = Message(sender_id=me_u.id, sender_uid=my_uid, sender_name=me_u.name, to_uid=BOT_UID, to_id=0, text=text, msg_type="text")
        db.session.add(m1); db.session.commit()
        # 2. Get Bot reply (with autocorrect)
        reply = get_bot_reply(text, my_uid, me_u.name)
        # 3. Save Bot reply
        m2 = Message(sender_id=0, sender_uid=BOT_UID, sender_name=BOT_NAME, to_uid=my_uid, to_id=me_u.id, text=reply, msg_type="text", is_broadcast=False)
        db.session.add(m2); db.session.commit()
        return jsonify({"success":True,"reply":reply})
    except Exception as e:
        db.session.rollback(); return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/bot-messages")
def bot_msgs_api():
    my_uid = request.args.get("my_uid")
    msgs = Message.query.filter(((Message.sender_uid==my_uid)&(Message.to_uid==BOT_UID))|((Message.sender_uid==BOT_UID)&(Message.to_uid==my_uid))).order_by(Message.created_at.asc()).all()
    out=[]
    for m in msgs:
        out.append({"id":m.id,"from":m.sender_uid,"from_name":m.sender_name,"text":m.text,"type":m.msg_type,"time":m.created_at.strftime("%I:%M %p")})
    return jsonify({"success":True,"messages":out})

# ---------- DEFAULT CHAT - BOT CHAT AUTO-CREATE ON SIGNUP / LOGIN ----------
@app.route("/api/ensure-bot-chat", methods=["POST"])
def ensure_bot_api():
    d = request.get_json(force=True); my_uid = d.get("my_uid")
    me_u = User.query.filter_by(uid=my_uid).first()
    if not me_u: return jsonify({"success":False}),404
    ex = Message.query.filter(((Message.sender_uid==my_uid)&(Message.to_uid==BOT_UID))|((Message.sender_uid==BOT_UID)&(Message.to_uid==my_uid))).first()
    if not ex:
        welcome = f"Hello {me_u.name}! 👋 Welcome to MyQchat.\n\nI am QWNG Bot - Your helper.\n\nI am not real AI, but I can help you with many things.\n\nType **help** to see all options.\n\nWhat do you want help with?\n1. Tick\n2. Password\n3. Account\n4. Chat\n5. Group\n6. Post\n\nJust type **help** or **1** or **tick**"
        m = Message(sender_id=0, sender_uid=BOT_UID, sender_name=BOT_NAME, to_uid=my_uid, to_id=me_u.id, text=welcome, msg_type="text")
        db.session.add(m); db.session.commit()
    return jsonify({"success":True})
    # ================= PART 7-B - BOT FRONTEND - BOT ON TOP + QUICK BUTTONS =================
BOT_FRONTEND_JS = r"""<script>
// ---------- BOT FRONTEND - PART 7-B ----------
async function ensureBotChat(){
  if(!ME) return;
  await fetch('/api/ensure-bot-chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid})});
}
function openBotChat(){
  CUR = "QWNG_BOT"; CUR_NAME = "QWNG Bot";
  show('mainApp').style.display='none'; show('chatScreen').style.display='block';
  show('chatName').innerHTML = 'QWNG Bot <span class="tick Green">Bot ✓</span>';
  show('chatAvatar').innerText = 'Q';
  show('chatAvatar').style.background = '#7b1fa2';
  show('chatStatus').innerText = 'Always Online • Scripted Helper';
  loadBotMessages();
}
async function loadBotMessages(){
  if(!ME) return;
  let r = await fetch(`/api/bot-messages?my_uid=${ME.uid}`);
  let d = await r.json();
  let area = show('chatArea');
  if(!d.messages || d.messages.length===0){
    area.innerHTML = `<div class="empty"><b>QWNG Bot</b><br>Your helper is here.<br>Type <b>help</b> to start.</div>`;
    return;
  }
  let html = '';
  d.messages.forEach(m=>{
    let isMine = m.from === ME.uid;
    let cls = isMine ? 'mine' : 'theirs';
    // Bot message me **bold** ko <b> me convert
    let txt = m.text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
    html += `<div class="msg ${cls}">${txt}<span class="mTime">${m.time}</span></div>`;
  });
  // Quick Buttons - Only after Bot message
  html += `<div style="display:flex;gap:6px;flex-wrap:wrap;padding:8px 2px">
    <button onclick="sendBotQuick('help')" style="background:#e3f2fd;border:none;border-radius:18px;padding:7px 12px;font-size:12px;cursor:pointer">❓ Help</button>
    <button onclick="sendBotQuick('tick')" style="background:#e8f5e9;border:none;border-radius:18px;padding:7px 12px;font-size:12px;cursor:pointer">✔️ Tick</button>
    <button onclick="sendBotQuick('password')" style="background:#fff3e0;border:none;border-radius:18px;padding:7px 12px;font-size:12px;cursor:pointer">🔑 Password</button>
    <button onclick="sendBotQuick('chat')" style="background:#f3e5f5;border:none;border-radius:18px;padding:7px 12px;font-size:12px;cursor:pointer">💬 Chat</button>
    <button onclick="sendBotQuick('post')" style="background:#e0f2f1;border:none;border-radius:18px;padding:7px 12px;font-size:12px;cursor:pointer">📸 Post</button>
    <button onclick="sendBotQuick('report')" style="background:#ffebee;border:none;border-radius:18px;padding:7px 12px;font-size:12px;cursor:pointer">🚩 Report</button>
  </div>`;
  area.innerHTML = html;
  area.scrollTop = area.scrollHeight;
}
async function sendBotQuick(txt){
  show('msgInput').value = txt;
  await sendBotMsg();
}
async function sendBotMsg(){
  let t = show('msgInput').value.trim();
  if(!t) return;
  show('msgInput').value = '';
  let r = await fetch('/api/bot-chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({my_uid:ME.uid, text:t})});
  let d = await r.json();
  if(!d.success){ alert(d.error); return; }
  loadBotMessages();
}
// Override sendMsg - If chatting with Bot, use Bot API
let _oldSendMsg = sendMsg;
sendMsg = async function(){
  if(CUR === "QWNG_BOT"){
    await sendBotMsg();
    return;
  }
  await _oldSendMsg();
};
// Override loadMessages - If Bot, load Bot messages
let _oldLoadMessages = loadMessages;
loadMessages = async function(){
  if(CUR === "QWNG_BOT"){
    await loadBotMessages();
    return;
  }
  await _oldLoadMessages();
};
// Override openChat - If Bot, open Bot Chat
let _oldOpenChat = openChat;
openChat = function(uid, name, col){
  if(uid === "QWNG_BOT"){
    openBotChat();
    return;
  }
  _oldOpenChat(uid, name, col);
};
// Bot on Top of Chat List - Inject Bot row before normal list
let _oldLoadUsers = loadUsers;
loadUsers = async function(){
  await ensureBotChat();
  if(!ME) return;
  let q = val('chatSearch');
  // If searching, let normal loadUsers handle it
  if(q){
    await _oldLoadUsers();
    return;
  }
  // First get Bot last message
  let br = await fetch(`/api/bot-messages?my_uid=${ME.uid}`);
  let bd = await br.json();
  let botLast = bd.messages && bd.messages.length ? bd.messages[bd.messages.length-1].text : 'Hello! Type help to see all options.';
  botLast = botLast.replace(/\n/g, ' ').substring(0,45);
  // Now load normal users
  let r = await fetch(`/api/users?uid=${ME.uid}&q=`);
  let d = await r.json();
  let list = show('chatList');
  let botRow = `<div class="userRow" onclick="openBotChat()" style="background:#f3e5f5;border-left:4px solid #7b1fa2"><div class="avatar" style="background:#7b1fa2">Q<span class="dot" style="background:#25d366"></span></div><div class="userInfo"><b>QWNG Bot <span class="tick Green">Bot ✓</span></b><span>${botLast}</span></div><div class="time">Now<br><span style="font-size:10px;color:#00a884">Online</span></div></div>`;
  // Build normal list manually (reuse old logic by calling API again is heavy, so we render here)
  let html = botRow;
  if(d.users){
    d.users.forEach(u=>{
      if(CUR_FILTER==='groups' && !u.is_group) return;
      let last = u.last_msg||u.bio||'';
      let col = u.avatar_color||'#075e54';
      let onlineDot = u.online?'<span class="dot" style="background:#25d366"></span>':'<span class="dot" style="background:#a8a8a8"></span>';
      let name = u.is_group? u.name : (u.name||u.username);
      let tick = u.tick ? `<span class="tick ${u.tick}">${u.tick==='L'?'L ✓':u.tick+' ✓'}</span>` : '';
      html+=`<div class="userRow" onclick="openChat('${u.uid}','${name.replace(/'/g,"")}','${col}')"><div class="avatar" style="background:${col}">${name.charAt(0).toUpperCase()}${onlineDot}</div><div class="userInfo"><b>${name} ${tick}</b><span>${last.substring(0,45)}</span></div><div class="time">${u.last_time||''}<br><span style="font-size:10px;color:#00a884">${u.online?'Online':''}</span></div></div>`;
    });
  }
  list.innerHTML = html;
};
// Make sure Bot is ensured after login
let _oldAfterLogin = afterLogin;
afterLogin = function(){
  _oldAfterLogin();
  ensureBotChat();
};
</script>"""

# FINAL HOME - UPDATE TO INCLUDE BOT JS TOO
def final_home():
    return FRONTEND + FRONTEND_JS + SETTINGS_JS + BOT_FRONTEND_JS
app.view_functions['home'] = final_home
app.view_functions['app_page'] = lambda: FRONTEND + FRONTEND_JS + SETTINGS_JS + BOT_FRONTEND_JS
# ================= PART 7-C - BOT EXTRA 20 QUESTIONS - ENGLISH ONLY =================
# No Hindi - All Bot replies in English like 【entity-WhatsApp¦canonical_name=WhatsApp】

def get_bot_reply_extra(user_text, me_uid, me_name):
    t = autocorrect_text(user_text)
    tl = t.lower().strip()

    # 1. APP DOWNLOAD / INSTALL
    if any(x in tl for x in ["download app","app download","how to download","install app","apk","apk download"]):
        return "📱 **How to Download / Install App?**\n\nYou do not need to download any APK for MyQchat.\n\nSteps:\n1. Open MyQchat link in Chrome\n2. Tap 3 dots in Chrome\n3. Tap Add to Home Screen / Install App\n4. App will appear on Home Screen\n\nNow it will work like a real app. 0 MB download, Auto Update.\n\nType **help** for menu."

    # 2. ONLINE / LAST SEEN
    if any(x in tl for x in ["online","last seen","online status"]):
        return "🟢 **Online / Last Seen**\n\nGreen dot = User is Online.\nGrey dot = User is Offline.\n\nYour Online status:\n1. When you open the app, you will show as Online\n2. When you close it, Last Seen time will show\n\nTo hide it:\nGo to Settings > Privacy > Last Seen > Nobody\n\nType **help** for menu."

    # 3. HOW TO SEND PHOTO
    if any(x in tl for x in ["send photo","send image","photo send","image send","how to send photo"]):
        return "📸 **How to Send Photo?**\n\nSteps:\n1. Open Chat\n2. Tap Attach 📎 or Camera 📷 button below\n3. Choose Photo\n4. Tap Send\n\nRules:\n- Max 2 photos per hour\n- Photo will auto-compress to 360p for speed\n- Photo will auto-delete in 1 hour\n\nType **help** for menu."

    # 4. VOICE MESSAGE
    if any(x in tl for x in ["voice","voice message","audio"]):
        return "🎤 **Voice Message**\n\nSteps:\n1. Open Chat\n2. Tap Mic 🎤 button\n3. Record Voice\n\nRules:\n- Max 15 seconds\n- Voice will auto-delete in 20 minutes\n\nType **help** for menu."

    # 5. DELETE MESSAGE
    if any(x in tl for x in ["delete message","message delete","delete msg"]):
        return "🗑️ **Delete Message**\n\nSteps:\n1. Tap on the message\n2. Tap Delete for Everyone\n3. Confirm\n\nAfter that everyone will see: \"This message was deleted\"\n\nNote: Only sender can delete.\n\nType **help** for menu."

    # 6. STAR / REPLY / FORWARD / REACT
    if any(x in tl for x in ["star message","reply","forward message","react","reaction"]):
        return "⭐ **Star / Reply / Forward / React**\n\nTap on any message to see options:\n- React - Send emoji reaction\n- Star - Save important message, it will show in Starred\n- Reply - Reply to a message\n- Forward - Send message to someone else\n- Delete - Delete for Everyone\n\nType **help** for menu."

    # 7. UNBLOCK
    if any(x in tl for x in ["unblock","blocked list"]):
        return "🚫 **How to Unblock?**\n\nSteps:\n1. Go to Settings\n2. Tap Blocked Users\n3. Tap Unblock on the user you want to unblock\n\nNow that user can send you messages.\n\nType **help** for menu."

    # 8. SEARCH
    if any(x in tl for x in ["search","find user"]):
        return "🔍 **How to Search?**\n\n1. In Chats, type Name / Username / UID in Search box on top\n2. Inside Chat, type in Search in chat box\n3. To search by UID - Tap + button > Enter UID > Search\n\nType **help** for menu."

    # 9. STATUS
    if any(x in tl for x in ["status","story"]):
        return "✨ **Status Help**\n\nSteps:\n1. Go to Status tab\n2. Write Status (Max 300 letters)\n3. Tap Post Status\n\nStatus will auto-delete in 24 hours.\nAll Status will show in Status tab.\n\nType **help** for menu."

    # 10. CALL
    if any(x in tl for x in ["call","phone","video call"]):
        return "📞 **Call Help**\n\nSteps:\n1. Open Chat\n2. Tap Phone 📞 for Voice or Video 📹 for Video on top\n3. Call will be saved in Calls tab\n\nNote: Right now Call is a Call Log demo. Real calling will come in next update.\n\nType **help** for menu."

    # 11. BIO / PROFILE
    if any(x in tl for x in ["bio","profile","name change","change name"]):
        return "👤 **Profile / Bio / Name**\n\nSteps:\n1. Go to Settings\n2. Tap Edit Profile\n3. Change Name, Bio, Colour\n4. Tap Save Profile\n\nBio Max 200 letters.\nExample Bio: Hey there! I am using MyQchat\n\nType **help** for menu."

    # 12. NOTIFICATION
    if any(x in tl for x in ["notification","notif","alert"]):
        return "🔔 **Notifications**\n\nSteps:\n1. Go to Settings\n2. Turn ON / OFF Notifications toggle\n\nIf ON, you will get alert for new message.\n\nType **help** for menu."

    # 13. LOGOUT
    if any(x in tl for x in ["logout","log out","sign out"]):
        return "🚪 **Logout**\n\nSteps:\n1. Go to Settings\n2. Scroll down\n3. Tap Logout\n\nAfter Logout you will show as Offline. Login again to show as Online.\n\nType **help** for menu."

    # 14. WHO MADE APP
    if any(x in tl for x in ["qwng","who made","developer","made by","who created"]):
        return "👑 **Who Made MyQchat?**\n\nMyQchat is Developed by **QWNG**.\nOwner is **LoyalWQ**.\n\nApp is Free, Fast & Secure.\n\nType **help** for menu."

    # 15. VERSION / UPDATE
    if any(x in tl for x in ["version","update","new version","latest"]):
        return "ℹ️ **Version Info**\n\nCurrent Version: **V3 - Final + Bot**\nApp: MyQchat by QWNG\nOwner: LoyalWQ\n\nThis is a browser app, so Update is automatic. No download needed.\n\nType **help** for menu."

    # 16. SCAM / FAKE
    if any(x in tl for x in ["scam","fraud","fake","hacker","hack"]):
        return "🛡️ **Stay Safe From Scam / Fake**\n\n- Never share your Password with anyone\n- Never click on unknown links\n- If someone asks for money, Report immediately\n- Scam Tick is given by Admin after Report\n\nTo Report: Chat > 3 dots > Report User > Scam\n\nType **help** for menu."

    # 17. SAVE CONTACT
    if any(x in tl for x in ["save contact","contact save","add friend"]):
        return "👥 **Save Contact**\n\nSteps:\n1. Go to Chats > + button\n2. Enter Friend UID\n3. Tap Search > Add\n\nNow you can chat fully - Up to 500 letters.\nWithout saving, only 2 messages, 30 letters.\n\nType **help** for menu."

    # 18. LANGUAGE
    if any(x in tl for x in ["hindi","language","english","urdu"]):
        return "🌐 **Language**\n\nMyQchat is in English right now, like 【entity-WhatsApp¦canonical_name=WhatsApp】.\nBot also replies in English.\n\nHindi option may come in future.\n\nType **help** for menu."

    # 19. TIME / DATE
    if any(x in tl for x in ["time","date","today","what is time"]):
        from datetime import datetime
        now = datetime.now()
        return f"🕐 **Time**\n\nCurrent time is: {now.strftime('%I:%M %p')}\nDate: {now.strftime('%d/%m/%Y')}\n\nType **help** for menu."

    # 20. JOKE / FUN
    if any(x in tl for x in ["joke","funny","bored","boring"]):
        return "😂 **Joke Time!**\n\nWhy did the phone go to school?\nTo improve its network! 😂\n\nWant another? Type **joke** again.\n\nType **help** for menu."

    return None

# ---- PATCH: Check C first, then A ----
_old_get_bot_reply = get_bot_reply
def get_bot_reply_new(user_text, me_uid, me_name):
    extra = get_bot_reply_extra(user_text, me_uid, me_name)
    if extra is not None:
        orig = user_text.strip()
        corrected = autocorrect_text(orig)
        if corrected.lower() != orig.lower() and len(orig) > 2:
            return f"Did you mean: \"{corrected}\"? I understood it as that.\n\n" + extra
        return extra
    return _old_get_bot_reply(user_text, me_uid, me_name)

get_bot_reply = get_bot_reply_new
# ================= PART 7-D - BOT EXTRA 30 QUESTIONS - ENGLISH ONLY =================
# No Hindi - All Bot replies in English like WhatsApp

def get_bot_reply_extra2(user_text, me_uid, me_name):
    t = autocorrect_text(user_text)
    tl = t.lower().strip()

    if any(x in tl for x in ["love","crush","girlfriend","boyfriend","i love you"]):
        return "❤️ **Love**\n\nLove is beautiful. Be honest, be kind, and respect each other.\n\nIf you like someone, talk to them directly in MyQchat.\nDo not share personal photos with strangers.\n\nType **help** for menu."

    if any(x in tl for x in ["shayari","poetry"]):
        return "✍️ **Shayari**\n\nDistance means so little, when someone means so much.\n\nWant more? Type **shayari** again.\n\nType **help** for menu."

    if any(x in tl for x in ["motivation","motivated","sad","depressed","lonely","tired"]):
        return "💪 **Motivation**\n\nYou are stronger than you think.\nOne small step today is better than no step.\nTake a break, drink water, and try again.\n\nYou can do it!\n\nType **help** for menu."

    if any(x in tl for x in ["study","exam","homework","school","college"]):
        return "📚 **Study Help**\n\nTips:\n1. Study 25 minutes, take 5 minutes break\n2. Write important points\n3. Revise before sleep\n4. Keep phone away while studying\n\nYou got this!\n\nType **help** for menu."

    if any(x in tl for x in ["game","play game","pubg","free fire","gaming"]):
        return "🎮 **Games**\n\nMyQchat is for chatting, not for gaming.\nBut you can chat with your game friends here.\nShare your UID with your squad and make a Group.\n\nType **help** for menu."

    if any(x in tl for x in ["quiz","ask me"]):
        return "🧠 **Quiz Time!**\n\nWhat is 2 + 2?\nA) 3  B) 4  C) 5\n\nType **answer 4** to check.\n\nType **help** for menu."

    if "answer 4" in tl or tl == "4":
        return "✅ Correct! 2 + 2 = 4. You are smart!\n\nType **quiz** for another question.\nType **help** for menu."

    if any(x in tl for x in ["weather","rain"]):
        return "🌤️ **Weather**\n\nI cannot check live weather. Please check your phone weather app.\n\nStay safe. If it rains, stay inside.\n\nType **help** for menu."

    if any(x in tl for x in ["song","music","suggest song"]):
        return "🎵 **Song**\n\nYou can add a Song Name in your Post.\nGo to Posts > Write Caption > Add Song Name > Post.\n\nNo MP3 upload. Only name or link.\n\nType **help** for menu."

    if any(x in tl for x in ["money","earn money","job","work"]):
        return "💰 **Money / Job**\n\nMyQchat does not give money.\nBeware of anyone who says Earn Money by clicking links. That is often a scam.\nNever pay money to strangers.\n\nType **help** for menu."

    if any(x in tl for x in ["creator","influencer","famous","viral"]):
        return "⭐ **Become Famous**\n\nTips:\n1. Post good photos daily (Max 3 per day)\n2. Write good captions\n3. Be active in chats and groups\n4. Request Tick from Settings\n\nConsistency is key.\n\nType **help** for menu."

    if any(x in tl for x in ["admin panel","become admin"]):
        return "🛡️ **Admin Panel**\n\nAdmin Panel is inside Settings.\nOnly Owner LoyalWQ can see it.\nYou cannot become Admin by requesting.\nAdmin can approve Tick, check Reports, Broadcast.\n\nType **help** for menu."

    if any(x in tl for x in ["group admin","group owner","remove member"]):
        return "👥 **Group Admin**\n\nGroup creator is Group Admin.\nTo remove a member, contact Group Admin.\nGroup management full controls will come in next update.\n\nType **help** for menu."

    if any(x in tl for x in ["emoji","sticker"]):
        return "😊 **Emoji / Sticker**\n\nIn Chat, tap 😊 button to open Emoji bar.\nTap any emoji to send.\nStickers will come in next update.\n\nType **help** for menu."

    if any(x in tl for x in ["wallpaper","theme","font","color","colour"]):
        return "🎨 **Wallpaper / Theme**\n\nSteps:\n1. Go to Settings\n2. Tap Wallpaper\n3. Choose Default / Green / Blue / Dark\n\nFont size option will come in next update.\n\nType **help** for menu."

    if any(x in tl for x in ["dark mode","night mode"]):
        return "🌙 **Dark Mode**\n\nSteps:\n1. Go to Settings\n2. Turn ON Dark Mode toggle\n\nIt is easy on eyes at night.\n\nType **help** for menu."

    if any(x in tl for x in ["hide online","hide last seen"]):
        return "👻 **Hide Online / Last Seen**\n\nSteps:\n1. Go to Settings > Privacy\n2. Last Seen > Choose Nobody\n\nNow no one can see your Last Seen.\n\nType **help** for menu."

    if any(x in tl for x in ["read receipt","blue tick","seen"]):
        return "✔️✔️ **Read Receipts**\n\nSteps:\n1. Go to Settings > Privacy\n2. Turn ON / OFF Read Receipts\n\nIf OFF, others will not know if you read their message.\n\nType **help** for menu."

    if any(x in tl for x in ["spam","spam message"]):
        return "🚫 **Spam**\n\nIf someone sends spam:\n1. Open Chat > 3 dots > Report User > Spam\n2. Block the user\n\nAdmin will check and take action.\n\nType **help** for menu."

    if any(x in tl for x in ["forgot","cannot login","login problem","login failed"]):
        return "🔑 **Login Problem**\n\nCheck:\n1. Username is correct?\n2. Password is correct?\n3. Caps Lock is OFF?\n\nIf you forgot password and added Recovery Email, use it.\nIf not, create a new account.\n\nType **help** for menu."

    if any(x in tl for x in ["username","change username"]):
        return "👤 **Username**\n\nUsername cannot be changed after Signup.\nUsername must be unique.\nIf you want a new username, create a new account.\n\nYour Name can be changed from Settings > Edit Profile.\n\nType **help** for menu."

    if any(x in tl for x in ["number","phone","mobile","whatsapp number"]):
        return "📞 **Phone Number**\n\nMyQchat does not ask for Phone Number.\nWe use UID, not phone number.\nNever share your phone number with strangers.\n\nType **help** for menu."

    if any(x in tl for x in ["location","address","where are you","where do you live"]):
        return "📍 **Location**\n\nI am QWNG Bot. I live in MyQchat server.\nDo not share your home address with strangers.\nStay safe.\n\nType **help** for menu."

    if any(x in tl for x in ["birthday","happy birthday"]):
        return "🎂 **Happy Birthday!**\n\nHappy Birthday! Wishing you happiness and success!\n\nCelebrate with your friends in MyQchat. Post a photo!\n\nType **help** for menu."

    if any(x in tl for x in ["good morning","good night","good evening","good afternoon"]):
        return "☀️ **Greetings!**\n\nGood Morning / Evening to you too!\nHope your day is great.\n\nType **help** to see what I can do."

    if any(x in tl for x in ["who is loyalwq","loyalwq","owner name"]):
        return "👑 **LoyalWQ**\n\nLoyalWQ is the Owner of MyQchat.\nApp is Developed by QWNG.\nL Tick is only for Owner.\n\nType **help** for menu."

    if any(x in tl for x in ["thank","thanks"]):
        return "You are welcome! Happy to help.\n\nType **help** if you need anything else."

    if any(x in tl for x in ["bot","are you bot","are you real","are you ai","are you human"]):
        return "🤖 **About Me**\n\nI am QWNG Bot. I am not real AI. I am a scripted Bot.\nI only understand fixed questions.\nI can help you with Tick, Password, Chat, Post, Report, Settings and more.\n\nType **help** to see all options."

    if any(x in tl for x in ["help me","i need help","please help"]):
        return "Sure! What do you need help with? Please choose one option:\n\n1. Tick\n2. Password\n3. Account\n4. Chat\n5. Group\n6. Post\n7. Report\n8. Settings\n9. Terms\n10. Owner\n\nType the number. Example: Type **2** for Password."

    if any(x in tl for x in ["rules","rule"]):
        return "📜 **Rules**\n\n1. Do not harass or bully anyone\n2. Do not send spam or scam links\n3. Do not share others private info\n4. Do not post hate or adult content\n5. Respect everyone\n\nIf you break rules, Admin can warn, ban, or delete your account.\n\nType **help** for menu."

    return None

# Patch - Check D first, then C, then A
_old2 = get_bot_reply
def get_bot_reply_final(user_text, me_uid, me_name):
    e2 = get_bot_reply_extra2(user_text, me_uid, me_name)
    if e2 is not None:
        orig = user_text.strip()
        corrected = autocorrect_text(orig)
        if corrected.lower() != orig.lower() and len(orig) > 2:
            return f"Did you mean: \"{corrected}\"? I understood it as that.\n\n" + e2
        return e2
    return _old2(user_text, me_uid, me_name)
get_bot_reply = get_bot_reply_final
