import os, json
from flask import Flask, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'myqchat-final-complete-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///myqchat_final.db').replace('postgres://','postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT = os.environ.get('GOOGLE_REDIRECT', 'https://myqchat-1.onrender.com/auth/google/callback')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    ban_until = db.Column(db.DateTime, nullable=True)
    ban_reason = db.Column(db.String(500), default='')
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)
    def is_ban_active(self):
        if not self.is_banned: return False
        if self.ban_until and self.ban_until < datetime.utcnow():
            self.is_banned=False; self.ban_until=None; db.session.commit(); return False
        return True

class Block(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    blocker_id=db.Column(db.Integer, db.ForeignKey('user.id'))
    blocked_id=db.Column(db.Integer, db.ForeignKey('user.id'))

class Chat(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    is_group=db.Column(db.Boolean, default=False)
    group_name=db.Column(db.String(100))
    user1=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user2=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    members_json=db.Column(db.Text, default='[]')

class Message(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    chat_id=db.Column(db.Integer, db.ForeignKey('chat.id'))
    sender_id=db.Column(db.Integer, db.ForeignKey('user.id'))
    text=db.Column(db.Text)
    is_deleted_for_all=db.Column(db.Boolean, default=False)
    deleted_for_json=db.Column(db.Text, default='[]')
    created_at=db.Column(db.DateTime, default=datetime.utcnow)

def is_admin(u): return u and u.is_admin and u.username=='LoyalWQ' and u.email=='loyalwq@gmail.com'

@app.route('/')
def index():
    return '''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MyQchat - Developed by QWNG</title><script src="https://accounts.google.com/gsi/client" async></script><style>body{font-family:Arial;background:#fafafa;margin:0}.top{background:#fff;padding:12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between}.card{background:#fff;margin:12px;padding:14px;border-radius:14px}input{width:100%;padding:10px;border:1px solid #ddd;border-radius:10px;margin:6px 0;box-sizing:border-box}button{background:#111;color:#fff;border:0;padding:10px 16px;border-radius:10px;margin-right:6px}.msg{padding:8px;border-radius:10px;margin:6px 0;background:#f1f1f1}.gbtn{background:#fff;color:#111;border:1px solid #ddd}</style></head><body><div class="top"><b>MyQchat</b><span>Developed by QWNG</span></div><div class="card"><h2>Login / Signup</h2><input id="u" placeholder="Username"><input id="e" placeholder="Email"><input id="p" type="password" placeholder="Password"><input id="n" placeholder="Name"><button onclick="signup()">Signup</button><button onclick="login()">Login</button><p id="me"></p><hr><p>Ya Google se login karo:</p><div id="g_id_onload" data-client_id="YOUR_GOOGLE_CLIENT_ID" data-callback="onGoogle"></div><div class="g_id_signin" data-type="standard" data-size="large" data-theme="outline" data-text="sign_in_with" data-shape="rectangular" data-logo_alignment="left"></div><br><button class="gbtn" onclick="window.location='/login/google'">Google Login - Redirect wala</button></div><div class="card"><h3>Users</h3><div id="users"></div><h3>Chat - Real Chatting</h3><div id="msgs"></div><input id="txt" placeholder="Message likho"><button onclick="send()">Send</button></div><script>let myId=localStorage.getItem("myqchat_id"), chatId=null;function val(id){return document.getElementById(id).value;}async function signup(){let btn=document.getElementById("me");btn.innerText="Signup ho raha hai...";try{let r=await fetch("/api/signup",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:val("u"),email:val("e"),password:val("p"),name:val("n")||val("u")})});let d=await r.json();btn.innerText=JSON.stringify(d);alert(JSON.stringify(d));}catch(e){btn.innerText="Error: "+e;}}async function login(){let btn=document.getElementById("me");btn.innerText="Login ho raha hai...";try{let r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:val("u"),password:val("p")})});let d=await r.json();if(d.success){myId=d.user_id;localStorage.setItem("myqchat_id",myId);btn.innerText="Login OK - "+d.username+" Admin:"+d.is_admin;loadUsers();}else{btn.innerText=d.error;alert(d.error);}}catch(e){btn.innerText="Error: "+e;}}async function onGoogle(resp){let r=await fetch("/api/google_login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credential:resp.credential})});let d=await r.json();if(d.success){myId=d.user_id;localStorage.setItem("myqchat_id",myId);document.getElementById("me").innerText="Google Login OK - "+d.username;loadUsers();}else alert(d.error);}async function loadUsers(){let r=await fetch("/api/users?user_id="+myId);let d=await r.json();document.getElementById("users").innerHTML=d.map(x=>"<div>"+x.name+" (@"+x.username+") <button onclick=startChat("+x.id+")>Chat</button></div>").join("");}async function startChat(other){let r=await fetch("/api/start_chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user1:myId,user2:other})});let d=await r.json();chatId=d.chat_id;loadMsgs();}async function loadMsgs(){if(!chatId)return;let r=await fetch("/api/messages?chat_id="+chatId+"&user_id="+myId);let d=await r.json();document.getElementById("msgs").innerHTML=d.map(m=>"<div class=msg>"+m.sender_name+": "+m.text+" <small>"+m.time+"</small></div>").join("");}async function send(){await fetch("/api/send",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chat_id:chatId,sender_id:myId,text:document.getElementById("txt").value})});document.getElementById("txt").value="";loadMsgs();}if(myId){loadUsers();}setInterval(loadMsgs,3000);</script><p style="text-align:center">Developed by QWNG - 2026 QWNG Company | Owner can view chats for moderation</p></body></html>'''.replace('YOUR_GOOGLE_CLIENT_ID', GOOGLE_CLIENT_ID)

@app.route('/api/google_login', methods=['POST'])
def api_google_login():
    d = request.json or {}
    cred = d.get('credential','')
    if not cred: return jsonify({"error":"No Google credential"}),400
    try:
        info = id_token.verify_oauth2_token(cred, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = info.get('email','').lower()
        name = info.get('name','')
        gid = info.get('sub','')
    except Exception as e:
        return jsonify({"error":f"Google verify failed: {e}"}),400
    u = User.query.filter_by(email=email).first()
    if not u:
        base = email.split('@')[0]
        username = base
        i=1
        while User.query.filter_by(username=username).first():
            username = f"{base}{i}"; i+=1
        u = User(username=username, email=email, name=name, google_id=gid)
        if username=='LoyalWQ' and email=='loyalwq@gmail.com': u.is_admin=True
        u.set_password(os.urandom(16).hex())
        db.session.add(u); db.session.commit()
    else:
        if not u.google_id: u.google_id=gid; db.session.commit()
    if u.is_ban_active(): return jsonify({"error":"Banned"}),403
    return jsonify({"success":True,"user_id":u.id,"username":u.username,"email":u.email,"is_admin":u.is_admin,"name":u.name})

@app.route('/login/google')
def login_google():
    import urllib.parse
    params = {"client_id":GOOGLE_CLIENT_ID,"redirect_uri":GOOGLE_REDIRECT,"response_type":"code","scope":"openid email profile","access_type":"offline","prompt":"consent"}
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?"+urllib.parse.urlencode(params))

@app.route('/auth/google/callback')
def google_callback():
    import requests as rq
    code = request.args.get('code')
    if not code: return "Google login failed - no code",400
    data = {"code":code,"client_id":GOOGLE_CLIENT_ID,"client_secret":GOOGLE_CLIENT_SECRET,"redirect_uri":GOOGLE_REDIRECT,"grant_type":"authorization_code"}
    tok = rq.post("https://oauth2.googleapis.com/token", data=data).json()
    idtok = tok.get('id_token')
    if not idtok: return f"Token failed: {tok}",400
    try:
        info = id_token.verify_oauth2_token(idtok, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception as e: return f"Verify failed: {e}",400
    email = info.get('email','').lower(); name = info.get('name',''); gid = info.get('sub','')
    u = User.query.filter_by(email=email).first()
    if not u:
        base=email.split('@')[0]; username=base; i=1
        while User.query.filter_by(username=username).first():
            username=f"{base}{i}"; i+=1
        u=User(username=username,email=email,name=name,google_id=gid)
        if username=='LoyalWQ' and email=='loyalwq@gmail.com': u.is_admin=True
        u.set_password(os.urandom(16).hex()); db.session.add(u); db.session.commit()
    return f"<h2>Google Login OK - {u.username}</h2><p>Ab wapas MyQchat kholo - Tum login ho gaye ho - User ID: {u.id}</p><a href='/'>Back to MyQchat</a>"

@app.route('/api/signup', methods=['POST'])
def api_signup():
    d=request.json or {}
    username=d.get('username','').strip(); email=d.get('email','').strip().lower(); password=d.get('password',''); name=d.get('name',username)
    if not username or not email or not password: return jsonify({"error":"All fields required - Username, Email, Password bharo"}),400
    if User.query.filter_by(username=username).first(): return jsonify({"error":"Username already taken. Same username cannot create another account."}),400
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Email already taken. Same Gmail cannot create another account."}),400
    u=User(username=username,email=email,name=name)
    if username=='LoyalWQ' and email=='loyalwq@gmail.com':
        u.is_admin=True
    u.set_password(password); db.session.add(u); db.session.commit()
    return jsonify({"success":True,"user_id":u.id,"is_admin":u.is_admin})

@app.route('/api/login', methods=['POST'])
def api_login():
    d=request.json or {}; username=d.get('username','').strip(); password=d.get('password','')
    u=User.query.filter((User.username==username)|(User.email==username)).first()
    if not u or not u.check_password(password): return jsonify({"error":"Invalid credentials"}),401
    if u.is_ban_active(): return jsonify({"error":f"Banned. Reason: {u.ban_reason}. Until: {u.ban_until or 'Permanent'}"}),403
    return jsonify({"success":True,"user_id":u.id,"username":u.username,"email":u.email,"is_admin":u.is_admin,"name":u.name})

@app.route('/api/users', methods=['GET'])
def api_users():
    user_id=request.args.get('user_id', type=int)
    users=User.query.filter(User.id!=user_id, User.is_banned==False).all()
    blocked=[b.blocked_id for b in Block.query.filter_by(blocker_id=user_id).all()]
    return jsonify([{"id":u.id,"username":u.username,"name":u.name,"email":u.email} for u in users if u.id not in blocked])

@app.route('/api/chats', methods=['GET'])
def api_chats():
    user_id=request.args.get('user_id', type=int); result=[]
    for ch in Chat.query.all():
        if ch.is_group:
            members=json.loads(ch.members_json or '[]')
            if user_id in members: result.append({"id":ch.id,"is_group":True,"name":ch.group_name,"members":members})
        else:
            if user_id in [ch.user1, ch.user2]:
                other_id=ch.user2 if ch.user1==user_id else ch.user1
                other=User.query.get(other_id)
                if not other: continue
                if Block.query.filter_by(blocker_id=user_id, blocked_id=other.id).first(): continue
                result.append({"id":ch.id,"is_group":False,"name":other.name,"username":other.username,"other_id":other.id})
    return jsonify(result)

@app.route('/api/start_chat', methods=['POST'])
def api_start_chat():
    d=request.json or {}; u1=d.get('user1'); u2=d.get('user2')
    if Block.query.filter_by(blocker_id=u2, blocked_id=u1).first(): return jsonify({"error":"You are blocked"}),403
    ch=Chat.query.filter(((Chat.user1==u1)&(Chat.user2==u2))|((Chat.user1==u2)&(Chat.user2==u1)), Chat.is_group==False).first()
    if not ch: ch=Chat(user1=u1,user2=u2); db.session.add(ch); db.session.commit()
    return jsonify({"chat_id":ch.id})

@app.route('/api/messages', methods=['GET'])
def api_messages():
    chat_id=request.args.get('chat_id', type=int); user_id=request.args.get('user_id', type=int)
    msgs=Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all(); res=[]
    for m in msgs:
        if m.is_deleted_for_all:
            res.append({"id":m.id,"text":"This message was deleted","is_deleted":True,"sender_id":m.sender_id,"time":m.created_at.strftime('%H:%M')}); continue
        if user_id in json.loads(m.deleted_for_json or '[]'): continue
        sender=User.query.get(m.sender_id)
        res.append({"id":m.id,"text":m.text,"sender_id":m.sender_id,"sender_name":sender.name if sender else "?","is_me":m.sender_id==user_id,"time":m.created_at.strftime('%H:%M')})
    return jsonify(res)

@app.route('/api/send', methods=['POST'])
def api_send():
    d=request.json or {}; m=Message(chat_id=d.get('chat_id'), sender_id=d.get('sender_id'), text=d.get('text','').strip()); db.session.add(m); db.session.commit(); return jsonify({"success":True})

@app.route('/api/block', methods=['POST'])
def api_block():
    d=request.json or {}
    if not Block.query.filter_by(blocker_id=d.get('blocker_id'), blocked_id=d.get('blocked_id')).first():
        db.session.add(Block(blocker_id=d.get('blocker_id'), blocked_id=d.get('blocked_id'))); db.session.commit()
    return jsonify({"success":True})

@app.route('/api/delete_for_me', methods=['POST'])
def api_delete_for_me():
    d=request.json or {}; m=Message.query.get(d.get('message_id')); lst=json.loads(m.deleted_for_json or '[]')
    if d.get('user_id') not in lst: lst.append(d.get('user_id')); m.deleted_for_json=json.dumps(lst); db.session.commit()
    return jsonify({"success":True})

@app.route('/api/delete_for_all', methods=['POST'])
def api_delete_for_all():
    d=request.json or {}; m=Message.query.get(d.get('message_id')); sender=User.query.get(d.get('user_id'))
    if m.sender_id!=d.get('user_id') and not (sender and is_admin(sender)): return jsonify({"error":"Only sender or owner can delete for everyone"}),403
    m.is_deleted_for_all=True; db.session.commit(); return jsonify({"success":True})

@app.route('/api/groups/create', methods=['POST'])
def api_group_create():
    d=request.json or {}; g=Chat(is_group=True, group_name=d.get('name'), members_json=json.dumps([d.get('creator_id')])); db.session.add(g); db.session.commit(); return jsonify({"group_id":g.id})

@app.route('/api/groups/add', methods=['POST'])
def api_group_add():
    d=request.json or {}; g=Chat.query.get(d.get('group_id')); members=json.loads(g.members_json or '[]')
    if d.get('user_id') not in members: members.append(d.get('user_id')); g.members_json=json.dumps(members); db.session.commit()
    return jsonify({"success":True})

@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    admin=User.query.get(request.args.get('admin_id', type=int))
    if not is_admin(admin): return jsonify({"error":"Owner only"}),403
    return jsonify([{"id":u.id,"username":u.username,"email":u.email,"name":u.name,"is_banned":u.is_banned,"ban_until":str(u.ban_until) if u.ban_until else None,"ban_reason":u.ban_reason} for u in User.query.all()])

@app.route('/api/admin/messages', methods=['GET'])
def api_admin_messages():
    admin=User.query.get(request.args.get('admin_id', type=int))
    if not is_admin(admin): return jsonify({"error":"Owner only"}),403
    msgs=Message.query.order_by(Message.created_at.desc()).limit(100).all()
    return jsonify([{"id":m.id,"text":m.text,"sender":User.query.get(m.sender_id).username if User.query.get(m.sender_id) else "?","chat_id":m.chat_id,"time":str(m.created_at),"is_deleted":m.is_deleted_for_all} for m in msgs])

@app.route('/api/admin/ban', methods=['POST'])
def api_admin_ban():
    d=request.json or {}; admin=User.query.get(d.get('admin_id'))
    if not is_admin(admin): return jsonify({"error":"Owner only"}),403
    target=User.query.get(d.get('target_id'))
    if target.is_admin: return jsonify({"error":"Cannot ban owner"}),400
    target.is_banned=True; target.ban_reason=d.get('reason','Violation')
    if d.get('days',0)>0: target.ban_until=datetime.utcnow()+timedelta(days=d.get('days'))
    else: target.ban_until=None
    db.session.commit(); return jsonify({"success":True})

@app.route('/api/admin/unban', methods=['POST'])
def api_admin_unban():
    d=request.json or {}; admin=User.query.get(d.get('admin_id'))
    if not is_admin(admin): return jsonify({"error":"Owner only"}),403
    target=User.query.get(d.get('target_id')); target.is_banned=False; target.ban_until=None; target.ban_reason=''; db.session.commit(); return jsonify({"success":True})

@app.route('/api/terms')
def api_terms():
    return jsonify({"title":"Terms","content":"Owner (LoyalWQ - loyalwq@gmail.com) can view chats for moderation, safety, ban. Do not share private data. Owner can temp/perm ban. Same username/email cannot create another account."})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error":"API not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error":"Server error"}), 500

if __name__=='__main__':
    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import text
            cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
            if 'google_id' not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN google_id VARCHAR(100)"))
                db.session.commit()
        except Exception as e:
            print("SQLite migrate:", e)
            db.session.rollback()
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_id VARCHAR(100)'))
            db.session.commit()
        except Exception as e:
            print("Postgres migrate:", e)
            db.session.rollback()
        if not User.query.filter_by(username='LoyalWQ').first():
            u=User(username='LoyalWQ', email='loyalwq@gmail.com', name='LoyalWQ Owner', is_admin=True)
            u.set_password('AlwaysBeLoyalQ'); db.session.add(u); db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
