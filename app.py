import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'myqchat-final-complete-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///myqchat_final.db').replace('postgres://','postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
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

# ---------- FRONTEND - Browser wala MyQchat ----------
@app.route('/')
def index():
    return '''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MyQchat - Developed by QWNG</title><style>body{font-family:Arial;background:#fafafa;margin:0}.top{background:#fff;padding:12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between}.card{background:#fff;margin:12px;padding:14px;border-radius:14px}input{width:100%;padding:10px;border:1px solid #ddd;border-radius:10px;margin:6px 0;box-sizing:border-box}button{background:#111;color:#fff;border:0;padding:10px 16px;border-radius:10px;margin-right:6px}.msg{padding:8px;border-radius:10px;margin:6px 0;background:#f1f1f1}</style></head><body><div class="top"><b>MyQchat</b><span>Developed by QWNG</span></div><div class="card"><h2>Login / Signup</h2><input id="u" placeholder="Username - LoyalWQ = Owner"><input id="e" placeholder="Email - loyalwq@gmail.com"><input id="p" type="password" placeholder="Password - Owner = AlwaysBeLoyalQ"><input id="n" placeholder="Name"><button onclick="signup()">Signup</button><button onclick="login()">Login</button><p id="me"></p></div><div class="card"><h3>Users</h3><div id="users"></div><h3>Chat</h3><div id="msgs"></div><input id="txt" placeholder="Message likho"><button onclick="send()">Send</button></div><script>let myId=localStorage.getItem("myqchat_id"), chatId=null;async function signup(){let r=await fetch("/api/signup",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u.value,email:e.value,password:p.value,name:n.value})});let d=await r.json();alert(JSON.stringify(d));}async function login(){let r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.success){myId=d.user_id;localStorage.setItem("myqchat_id",myId);document.getElementById("me").innerText="Login OK - "+d.username+" Admin:"+d.is_admin;loadUsers();}else alert(d.error);}async function loadUsers(){let r=await fetch("/api/users?user_id="+myId);let d=await r.json();document.getElementById("users").innerHTML=d.map(x=>"<div>"+x.name+" (@"+x.username+") <button onclick=startChat("+x.id+")>Chat</button></div>").join("");}async function startChat(other){let r=await fetch("/api/start_chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user1:myId,user2:other})});let d=await r.json();chatId=d.chat_id;loadMsgs();}async function loadMsgs(){if(!chatId)return;let r=await fetch("/api/messages?chat_id="+chatId+"&user_id="+myId);let d=await r.json();document.getElementById("msgs").innerHTML=d.map(m=>"<div class=msg>"+m.sender_name+": "+m.text+" <small>"+m.time+"</small></div>").join("");}async function send(){await fetch("/api/send",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chat_id:chatId,sender_id:myId,text:txt.value})});txt.value="";loadMsgs();}if(myId){loadUsers();}setInterval(loadMsgs,3000);</script><p style="text-align:center">Developed by QWNG - 2026 QWNG Company | Owner can view chats for moderation</p></body></html>'''

@app.route('/api/signup', methods=['POST'])
def api_signup():
    d=request.json or {}
    username=d.get('username','').strip(); email=d.get('email','').strip().lower(); password=d.get('password',''); name=d.get('name',username)
    if not username or not email or not password: return jsonify({"error":"All fields required"}),400
    if User.query.filter_by(username=username).first(): return jsonify({"error":"Username already taken. Same username cannot create another account."}),400
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Email already taken. Same Gmail cannot create another account."}),400
    u=User(username=username,email=email,name=name)
    if username=='LoyalWQ' and email=='loyalwq@gmail.com':
        if password!='AlwaysBeLoyalQ': return jsonify({"error":"Admin password must be AlwaysBeLoyalQ"}),400
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

if __name__=='__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='LoyalWQ').first():
            u=User(username='LoyalWQ', email='loyalwq@gmail.com', name='LoyalWQ Owner', is_admin=True)
            u.set_password('AlwaysBeLoyalQ'); db.session.add(u); db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
