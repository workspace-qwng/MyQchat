
import os, random
from flask import Flask, render_template_string, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'myqchat-clean-real-no-fake-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myqchat_real.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True, nullable=False)
    email=db.Column(db.String(120), unique=True, nullable=False)
    password_hash=db.Column(db.String(256), nullable=False)
    name=db.Column(db.String(100), default='MyQchat User')
    about=db.Column(db.String(500), default='Real MyQchat User')
    avatar=db.Column(db.String(800), default='https://picsum.photos/200/200?random=1')
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)

class Chat(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user1=db.Column(db.Integer, db.ForeignKey('user.id'))
    user2=db.Column(db.Integer, db.ForeignKey('user.id'))
    last_msg_time=db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    chat_id=db.Column(db.Integer, db.ForeignKey('chat.id'))
    sender_id=db.Column(db.Integer, db.ForeignKey('user.id'))
    text=db.Column(db.Text)
    created_at=db.Column(db.DateTime, default=datetime.utcnow)
    sender=db.relationship('User', foreign_keys=[sender_id])

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

BASE = '''<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>MyQchat REAL</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#111b21;color:#e9edef}
.header{background:#202c33;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0}
.logo{font-size:22px;font-weight:700}.logo span{color:#00a884}
.chat-row{display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid #1f2c34;align-items:center}
.chat-row img{width:50px;height:50px;border-radius:50%}
.chat-info{flex:1}.chat-top{display:flex;justify-content:space-between}.chat-name{font-size:17px}
.wallpaper{background:#0b141a;min-height:85vh;display:flex;flex-direction:column;padding:10px 0}
.bubble{max-width:75%;padding:8px 10px;border-radius:8px;margin:4px 10px;font-size:14px}
.bubble.sent{background:#005c4b;align-self:flex-end;margin-left:auto}
.bubble.recv{background:#202c33;align-self:flex-start;margin-right:auto}
.composer{background:#202c33;padding:8px 10px;display:flex;gap:8px;position:sticky;bottom:0}
.composer input{flex:1;background:#2a3942;border:none;border-radius:20px;padding:12px 16px;color:#fff;outline:none}
.fab{position:fixed;bottom:20px;right:16px;width:56px;height:56px;background:#00a884;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;color:#fff}
</style></head><body>CONTENT</body></html>'''
def render_page(inner): return render_template_string(BASE.replace('CONTENT', inner))

@app.route('/')
@login_required
def home(): return redirect('/chats')

@app.route('/chats')
@login_required
def chats_list():
    chats=Chat.query.filter((Chat.user1==current_user.id)|(Chat.user2==current_user.id)).order_by(Chat.last_msg_time.desc()).all()
    rows=''
    for ch in chats:
        other_id=ch.user2 if ch.user1==current_user.id else ch.user1
        other=User.query.get(other_id)
        if not other: continue
        last=Message.query.filter_by(chat_id=ch.id).order_by(Message.created_at.desc()).first()
        last_text=last.text[:35] if last else 'Start real chat!'
        rows+=f"<a href='/chat/{ch.id}'><div class='chat-row'><img src='{other.avatar}'><div class='chat-info'><div class='chat-top'><div class='chat-name'>{other.name}</div><div class='chat-time'>{last.created_at.strftime('%H:%M') if last else ''}</div></div><div style='color:#8696a0;font-size:14px'>{last_text}</div></div></div></a>"
    if not rows: rows='<div style="padding:60px;text-align:center;color:#8696a0">No real chats yet<br><a href="/contacts" style="color:#00a884">Add Friend →</a><br><br>Real users only!</div>'
    return render_page(f"<div class='header'><div class='logo'>MyQchat <span>REAL</span></div></div><div>{rows}</div><a href='/contacts'><div class='fab'>+</div></a>")

@app.route('/chat/<int:cid>', methods=['GET','POST'])
@login_required
def chat_view(cid):
    ch=Chat.query.get_or_404(cid)
    other_id=ch.user2 if ch.user1==current_user.id else ch.user1
    other=User.query.get_or_404(other_id)
    if request.method=='POST':
        txt=request.form.get('text','').strip()
        if txt:
            db.session.add(Message(chat_id=cid, sender_id=current_user.id, text=txt))
            ch.last_msg_time=datetime.utcnow(); db.session.commit()
        return redirect(f'/chat/{cid}')
    msgs=Message.query.filter_by(chat_id=cid).order_by(Message.created_at.asc()).all()
    bubbles=''.join([f"<div class='bubble {'sent' if m.sender_id==current_user.id else 'recv'}'>{m.text}<br><span style='font-size:11px;color:#8696a0'>{m.created_at.strftime('%H:%M')}</span></div>" for m in msgs])
    return render_page(f"<div class='header'><a href='/chats'>← {other.name}</a></div><div class='wallpaper'>{bubbles or '<div style=text-align:center;color:#8696a0;margin-top:40px>Start real conversation!</div>'}</div><form method='POST' class='composer'><input name='text' placeholder='Real message...' autofocus><button style='background:#00a884;color:#fff;border:none;width:42px;height:42px;border-radius:50%'>➤</button></form>")

@app.route('/contacts')
@login_required
def contacts_list():
    users=User.query.filter(User.id!=current_user.id).all()
    rows=''.join([f"<a href='/start_chat/{u.id}'><div class='chat-row'><img src='{u.avatar}'><div class='chat-info'><div class='chat-name'>{u.name}</div><div style='color:#8696a0'>{u.about[:40]}</div></div></div></a>" for u in users])
    return render_page(f"<div class='header'><a href='/chats'>←</a> Real Contacts</div><div>{rows or 'No users yet - friend must signup first!'}</div>")

@app.route('/start_chat/<int:uid>')
@login_required
def start_chat(uid):
    ex=Chat.query.filter(((Chat.user1==current_user.id)&(Chat.user2==uid))|((Chat.user1==uid)&(Chat.user2==current_user.id))).first()
    if ex: return redirect(f'/chat/{ex.id}')
    ch=Chat(user1=current_user.id, user2=uid); db.session.add(ch); db.session.commit()
    return redirect(f'/chat/{ch.id}')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form.get('username')).first()
        if u and u.check_password(request.form.get('password')):
            login_user(u); return redirect('/chats')
        return render_page("<div style='padding:40px;text-align:center'>Invalid <a href='/login'>Retry</a></div>")
    return render_page("<div style='max-width:380px;margin:40px auto;padding:24px;text-align:center'><div style='font-size:48px'>💬</div><div style='font-size:24px;font-weight:700'>MyQchat <span style='color:#00a884'>REAL</span></div><div style='color:#8696a0;font-size:12px'>No Fake • Phone Server</div><form method='POST' style='display:flex;flex-direction:column;gap:12px;margin-top:20px'><input name='username' placeholder='Username' required style='padding:14px;border-radius:12px;background:#202c33;color:#fff;border:1px solid #2a3942'><input name='password' type='password' placeholder='Password' required style='padding:14px;border-radius:12px;background:#202c33;color:#fff;border:1px solid #2a3942'><button style='background:#00a884;color:#fff;padding:14px;border:none;border-radius:12px'>Login</button></form><div style='margin-top:12px'><a href='/signup' style='color:#00a884'>Create Real Account</a></div></div>")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        if User.query.filter_by(username=request.form.get('username')).first(): return render_page("Exists <a href='/signup'>Retry</a>")
        u=User(username=request.form.get('username'), email=request.form.get('email') or f"{request.form.get('username')}@myqchat.com", name=request.form.get('name') or request.form.get('username'), avatar=f"https://picsum.photos/200/200?random={random.randint(1,1000)}")
        u.set_password(request.form.get('password')); db.session.add(u); db.session.commit(); login_user(u); return redirect('/chats')
    return render_page("<div style='max-width:380px;margin:40px auto;padding:24px'><form method='POST' style='display:flex;flex-direction:column;gap:12px'><input name='name' placeholder='Your Real Name' required style='padding:14px;border-radius:12px;background:#202c33;color:#fff;border:1px solid #2a3942'><input name='username' placeholder='Username' required style='padding:14px;border-radius:12px;background:#202c33;color:#fff;border:1px solid #2a3942'><input name='password' type='password' placeholder='Password' required style='padding:14px;border-radius:12px;background:#202c33;color:#fff;border:1px solid #2a3942'><button style='background:#00a884;color:#fff;padding:14px;border:none;border-radius:12px'>Create Real Account</button></form></div>")

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect('/login')

if __name__=='__main__':
    with app.app_context(): db.create_all()
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close()
    except: ip='127.0.0.1'
    print(f"MyQchat REAL - No Fake! http://127.0.0.1:5000 http://{ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
