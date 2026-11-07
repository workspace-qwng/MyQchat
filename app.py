import os
import re
import random
import string
import json
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///myqchat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db = SQLAlchemy(app)

OWNER_USERNAME = 'LoyalWQ'
OWNER_UID = '10000001'
APP_NAME = 'MyQchat'
APP_COMPANY = 'QWNG'
SUPPORT_EMAIL = 'qwngofficial@gmail.com'
MAX_BIO_LEN = 300
MAX_MSG_LEN = 1000
MAX_GROUP_NAME = 100
MAX_STATUS_LEN = 500
STATUS_EXPIRE_HOURS = 24
TEXT_DELETE_DAYS = 2
IMAGE_DELETE_MIN = 60
VOICE_DELETE_MIN = 20

def clean(s, n=500):
    if s is None:
        return ''
    return str(s).strip()[:n]

def clean_username(s):
    s = clean(s, 50).lower().replace(' ', '_')
    s = re.sub(r'[^a-z0-9_.]', '', s)
    return s

def is_valid_username(s):
    if not s or len(s) < 3 or len(s) > 30:
        return False
    if not re.match(r'^[a-z0-9_.]+$', s):
        return False
    return True

def is_valid_password(s):
    if not s or len(s) < 4 or len(s) > 100:
        return False
    return True

def is_valid_email(s):
    if not s:
        return False
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', s) is not None

def make_uid():
    while True:
        u = ''.join(random.choice(string.digits) for _ in range(8))
        if not User.query.filter_by(uid=u).first():
            return u

def make_gid():
    while True:
        g = ''.join(random.choice(string.digits) for _ in range(8))
        if not Group.query.filter_by(gid=g).first():
            return g

def make_call_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

def time_now():
    return datetime.utcnow()

def time_ago(dt):
    if not dt:
        return 'Now'
    diff = datetime.utcnow() - dt
    if diff.days > 0:
        return str(diff.days) + 'd ago'
    if diff.seconds > 3600:
        return str(diff.seconds // 3600) + 'h ago'
    if diff.seconds > 60:
        return str(diff.seconds // 60) + 'm ago'
    return 'Now'

def pub_user(u):
    if not u:
        return None
    return {'uid': u.uid, 'username': u.username, 'name': u.name, 'bio': u.bio, 'avatar_color': u.avatar_color, 'tick': u.tick, 'is_admin': u.is_admin, 'online': u.online, 'last_seen': time_ago(u.last_seen), 'dark_mode': u.dark_mode, 'wallpaper': u.wallpaper, 'recovery_email': u.recovery_email, 'privacy_last_seen': u.privacy_last_seen, 'privacy_photo': u.privacy_photo, 'privacy_about': u.privacy_about, 'read_receipts': u.read_receipts, 'notifications': u.notifications, 'font_size': u.font_size, 'chat_color': u.chat_color, 'auto_delete': u.auto_delete, 'created_at': str(u.created_at)}

def pub_message(m):
    return {'id': m.id, 'sender_uid': m.sender_uid, 'sender_name': m.sender_name, 'to_uid': m.to_uid, 'text': m.text, 'msg_type': m.msg_type, 'reply_to': m.reply_to, 'reply_text': m.reply_text, 'starred': m.starred, 'forwarded': m.forwarded, 'is_deleted': m.is_deleted, 'created_at': str(m.created_at), 'time': time_ago(m.created_at)}

def pub_group(g):
    return {'gid': g.gid, 'name': g.name, 'desc': g.desc, 'creator_uid': g.creator_uid, 'members': g.members, 'member_count': len(g.members.split(',') if g.members else []), 'created_at': str(g.created_at)}

def pub_song(s):
    return {'id': s.id, 'title': s.title, 'artist': s.artist, 'url': s.url, 'added_by': s.added_by, 'is_active': s.is_active}

def pub_status(s):
    return {'id': s.id, 'uid': s.uid, 'name': s.name, 'text': s.text, 'song_title': s.song_title, 'song_url': s.song_url, 'song_id': s.song_id, 'views': s.views, 'created_at': str(s.created_at), 'time': time_ago(s.created_at)}

def pub_tick(t):
    return {'id': t.id, 'uid': t.uid, 'username': t.username, 'name': t.name, 'tick': t.tick, 'reason': t.reason, 'status': t.status, 'admin_note': t.admin_note}

def pub_report(r):
    return {'id': r.id, 'reporter_uid': r.reporter_uid, 'reporter_name': r.reporter_name, 'reported_uid': r.reported_uid, 'reported_name': r.reported_name, 'reason': r.reason, 'detail': r.detail, 'status': r.status}

def pub_call(c):
    return {'id': c.id, 'from_uid': c.from_uid, 'from_name': c.from_name, 'to_uid': c.to_uid, 'to_name': c.to_name, 'call_type': c.call_type, 'duration': c.duration, 'status': c.status}

def get_me():
    d = request.get_json(silent=True) or {}
    uid = d.get('my_uid') or d.get('uid') or request.args.get('uid')
    if not uid:
        return None
    return User.query.filter_by(uid=uid).first()

def is_blocked(a, b):
    if not a or not b:
        return False
    return Block.query.filter_by(owner_uid=a, blocked_uid=b).first() is not None

def is_contact(a, b):
    return Contact.query.filter_by(owner_uid=a, contact_uid=b).first() is not None

def is_group_member(gid, uid):
    g = Group.query.filter_by(gid=gid).first()
    if not g:
        return False
    members = g.members.split(',') if g.members else []
    return uid in members

def add_group_member(gid, uid):
    g = Group.query.filter_by(gid=gid).first()
    if not g:
        return False
    members = g.members.split(',') if g.members else []
    if uid not in members:
        members.append(uid)
        g.members = ','.join(members)
        db.session.commit()
    return True

def remove_group_member(gid, uid):
    g = Group.query.filter_by(gid=gid).first()
    if not g:
        return False
    members = g.members.split(',') if g.members else []
    if uid in members:
        members.remove(uid)
        g.members = ','.join(members)
        db.session.commit()
    return True

def can_send_to(sender_uid, to_uid):
    if is_blocked(to_uid, sender_uid):
        return False
    if is_blocked(sender_uid, to_uid):
        return False
    return True

def check_rate_limit(uid, minutes=60, limit=100):
    since = datetime.utcnow() - timedelta(minutes=minutes)
    count = Message.query.filter_by(sender_uid=uid).filter(Message.created_at >= since).count()
    return count < limit

def get_unread_count(my_uid, with_uid):
    return Message.query.filter_by(to_uid=my_uid, sender_uid=with_uid, is_read=False).count()

def mark_read(my_uid, with_uid):
    rows = Message.query.filter_by(to_uid=my_uid, sender_uid=with_uid, is_read=False).all()
    for r in rows:
        r.is_read = True
    db.session.commit()

def delete_expired_status():
    cutoff = datetime.utcnow() - timedelta(hours=STATUS_EXPIRE_HOURS)
    rows = StatusItem.query.filter(StatusItem.created_at < cutoff).all()
    for r in rows:
        db.session.delete(r)
    db.session.commit()
    return len(rows)

def delete_expired_messages():
    text_cutoff = datetime.utcnow() - timedelta(days=TEXT_DELETE_DAYS)
    img_cutoff = datetime.utcnow() - timedelta(minutes=IMAGE_DELETE_MIN)
    voice_cutoff = datetime.utcnow() - timedelta(minutes=VOICE_DELETE_MIN)
    c1 = Message.query.filter(Message.msg_type=='text', Message.created_at < text_cutoff).delete()
    c2 = Message.query.filter(Message.msg_type=='image', Message.created_at < img_cutoff).delete()
    c3 = Message.query.filter(Message.msg_type=='voice', Message.created_at < voice_cutoff).delete()
    db.session.commit()
    return c1 + c2 + c3

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(200), default='')
    username = db.Column(db.String(200), default='')
    name = db.Column(db.String(200), default='')
    password = db.Column(db.String(200), default='')
    bio = db.Column(db.Text, default='')
    avatar_color = db.Column(db.String(200), default='')
    tick = db.Column(db.String(200), default='')
    is_admin = db.Column(db.Boolean, default=False)
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    dark_mode = db.Column(db.Boolean, default=False)
    wallpaper = db.Column(db.String(200), default='default')
    recovery_email = db.Column(db.String(200), default='')
    privacy_last_seen = db.Column(db.String(200), default='Everyone')
    privacy_photo = db.Column(db.String(200), default='Everyone')
    privacy_about = db.Column(db.String(200), default='Everyone')
    read_receipts = db.Column(db.Boolean, default=True)
    notifications = db.Column(db.Boolean, default=True)
    font_size = db.Column(db.String(200), default='Medium')
    chat_color = db.Column(db.String(200), default='Green')
    auto_delete = db.Column(db.Boolean, default=True)
    banned_until = db.Column(db.DateTime, default=datetime.utcnow)
    delete_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return pub_user(self)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_uid = db.Column(db.String(200), default='')
    sender_name = db.Column(db.String(200), default='')
    to_uid = db.Column(db.String(200), default='')
    text = db.Column(db.Text, default='')
    msg_type = db.Column(db.String(200), default='text')
    reply_to = db.Column(db.String(200), default='')
    reply_text = db.Column(db.Text, default='')
    starred = db.Column(db.Boolean, default=False)
    forwarded = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return pub_message(self)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(200), default='')
    contact_uid = db.Column(db.String(200), default='')
    contact_name = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(200), default='')
    blocked_uid = db.Column(db.String(200), default='')
    reason = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gid = db.Column(db.String(200), default='')
    name = db.Column(db.String(200), default='')
    desc = db.Column(db.String(200), default='')
    creator_uid = db.Column(db.String(200), default='')
    members = db.Column(db.Text, default='')
    admins = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return pub_group(self)

class GroupMsg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gid = db.Column(db.String(200), default='')
    sender_uid = db.Column(db.String(200), default='')
    sender_name = db.Column(db.String(200), default='')
    text = db.Column(db.Text, default='')
    msg_type = db.Column(db.String(200), default='text')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default='')
    artist = db.Column(db.String(200), default='')
    url = db.Column(db.String(200), default='')
    added_by = db.Column(db.String(200), default='')
    is_active = db.Column(db.Boolean, default=True)
    play_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return pub_song(self)

class StatusItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(200), default='')
    name = db.Column(db.String(200), default='')
    text = db.Column(db.Text, default='')
    song_title = db.Column(db.String(200), default='')
    song_url = db.Column(db.String(200), default='')
    song_id = db.Column(db.String(200), default='')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return pub_status(self)

class TickReq(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(200), default='')
    username = db.Column(db.String(200), default='')
    name = db.Column(db.String(200), default='')
    tick = db.Column(db.String(200), default='')
    reason = db.Column(db.Text, default='')
    status = db.Column(db.String(200), default='pending')
    admin_note = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_uid = db.Column(db.String(200), default='')
    reporter_name = db.Column(db.String(200), default='')
    reported_uid = db.Column(db.String(200), default='')
    reported_name = db.Column(db.String(200), default='')
    reason = db.Column(db.Text, default='')
    detail = db.Column(db.Text, default='')
    status = db.Column(db.String(200), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_uid = db.Column(db.String(200), default='')
    from_name = db.Column(db.String(200), default='')
    to_uid = db.Column(db.String(200), default='')
    to_name = db.Column(db.String(200), default='')
    call_type = db.Column(db.String(200), default='voice')
    duration = db.Column(db.String(200), default='0')
    status = db.Column(db.String(200), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StarMsg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(200), default='')
    msg_id = db.Column(db.String(200), default='')
    text = db.Column(db.Text, default='')
    from_name = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BroadcastMsg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_uid = db.Column(db.String(200), default='')
    from_name = db.Column(db.String(200), default='')
    text = db.Column(db.Text, default='')
    btype = db.Column(db.String(200), default='Announcement')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='LoyalWQ').first():
        u = User(uid='10000001', username='LoyalWQ', name='LoyalWQ', password=generate_password_hash('AlwaysBeLoyalQ'), tick='L', is_admin=True, avatar_color='#075e54')
        db.session.add(u)
        db.session.commit()
    if Song.query.count() == 0:
        for t, art, url in [('Calm Morning','QWNG Music','https://example.com/s1.mp3'),('Happy Vibes','QWNG Music','https://example.com/s2.mp3'),('Chill Evening','QWNG Music','https://example.com/s3.mp3'),('Morning Energy','QWNG Music','https://example.com/s4.mp3'),('Night Peace','QWNG Music','https://example.com/s5.mp3')]:
            db.session.add(Song(title=t, artist=art, url=url, added_by='System', is_active=True))
        db.session.commit()
      @app.route('/api/signup', methods=['POST'])
def signup():
    d = request.get_json(silent=True) or {}
    username = clean_username(d.get('username'))
    password = clean(d.get('password'), 100)
    name = clean(d.get('name'), 100) or username
    if not is_valid_username(username):
        return jsonify({'ok': False, 'error': 'Username must be 3-30 letters, numbers, dot, underscore'})
    if not is_valid_password(password):
        return jsonify({'ok': False, 'error': 'Password must be 4-100 letters'})
    if User.query.filter_by(username=username).first():
        return jsonify({'ok': False, 'error': 'Username already taken'})
    colors = ['#075e54','#128c7e','#25d366','#34b7f1','#075e54','#128c7e']
    u = User(uid=make_uid(), username=username, name=name, password=generate_password_hash(password), avatar_color=random.choice(colors), bio='Hey there! I am using MyQchat')
    db.session.add(u)
    db.session.commit()
    return jsonify({'ok': True, 'user': pub_user(u)})

@app.route('/api/login', methods=['POST'])
def login():
    d = request.get_json(silent=True) or {}
    username = clean_username(d.get('username'))
    password = clean(d.get('password'), 100)
    u = User.query.filter_by(username=username).first()
    if not u:
        return jsonify({'ok': False, 'error': 'User not found'})
    if not check_password_hash(u.password, password):
        return jsonify({'ok': False, 'error': 'Wrong password'})
    u.online = True
    u.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'user': pub_user(u)})

@app.route('/api/logout', methods=['POST'])
def logout():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if me:
        me.online = False
        me.last_seen = datetime.utcnow()
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/me', methods=['GET'])
def me():
    me = get_me()
    if me:
        return jsonify({'ok': True, 'user': pub_user(me)})
    return jsonify({'ok': False, 'error': 'Login first'})

@app.route('/api/users', methods=['GET'])
def users():
    me = get_me()
    q = clean(request.args.get('q'), 50)
    rows = User.query.all()
    out = []
    for u in rows:
        if me and u.uid == me.uid:
            continue
        if q and q.lower() not in u.username.lower() and q.lower() not in u.name.lower() and q != u.uid:
            continue
        out.append(pub_user(u))
    return jsonify({'users': out, 'count': len(out)})

@app.route('/api/search_uid', methods=['GET','POST'])
def search_uid():
    d = request.get_json(silent=True) or {}
    q = clean(d.get('q') or request.args.get('q'), 50)
    if not q:
        return jsonify({'ok': False, 'error': 'Enter UID or Username'})
    u = User.query.filter_by(uid=q).first() or User.query.filter_by(username=clean_username(q)).first()
    if u:
        return jsonify({'ok': True, 'user': pub_user(u)})
    return jsonify({'ok': False, 'error': 'User not found'})

@app.route('/api/add_contact', methods=['POST'])
def add_contact():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    contact_uid = clean(d.get('contact_uid'), 20)
    target = User.query.filter_by(uid=contact_uid).first()
    if not target:
        return jsonify({'ok': False, 'error': 'User not found'})
    if target.uid == me.uid:
        return jsonify({'ok': False, 'error': 'Cannot add yourself'})
    if Contact.query.filter_by(owner_uid=me.uid, contact_uid=contact_uid).first():
        return jsonify({'ok': False, 'error': 'Already in contacts'})
    db.session.add(Contact(owner_uid=me.uid, contact_uid=contact_uid, contact_name=target.name))
    db.session.commit()
    return jsonify({'ok': True, 'user': pub_user(target)})

@app.route('/api/contacts', methods=['GET'])
def contacts():
    me = get_me()
    if not me:
        return jsonify({'contacts': []})
    rows = Contact.query.filter_by(owner_uid=me.uid).all()
    out = []
    for c in rows:
        u = User.query.filter_by(uid=c.contact_uid).first()
        if u:
            d = pub_user(u)
            d['unread'] = get_unread_count(me.uid, u.uid)
            out.append(d)
    return jsonify({'contacts': out})

@app.route('/api/block', methods=['POST'])
def block():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    blocked_uid = clean(d.get('blocked_uid'), 20)
    if blocked_uid == me.uid:
        return jsonify({'ok': False, 'error': 'Cannot block yourself'})
    if not Block.query.filter_by(owner_uid=me.uid, blocked_uid=blocked_uid).first():
        db.session.add(Block(owner_uid=me.uid, blocked_uid=blocked_uid, reason=clean(d.get('reason'), 100)))
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/unblock', methods=['POST'])
def unblock():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    b = Block.query.filter_by(owner_uid=me.uid, blocked_uid=clean(d.get('blocked_uid'), 20)).first()
    if b:
        db.session.delete(b)
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/blocked', methods=['GET'])
def blocked():
    me = get_me()
    if not me:
        return jsonify({'blocked': []})
    rows = Block.query.filter_by(owner_uid=me.uid).all()
    out = []
    for b in rows:
        u = User.query.filter_by(uid=b.blocked_uid).first()
        if u:
            out.append(pub_user(u))
    return jsonify({'blocked': out})

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    if d.get('name'):
        me.name = clean(d.get('name'), 100)
    if d.get('bio') is not None:
        me.bio = clean(d.get('bio'), MAX_BIO_LEN)
    if d.get('recovery_email') is not None:
        em = clean(d.get('recovery_email'), 100)
        if em and not is_valid_email(em):
            return jsonify({'ok': False, 'error': 'Invalid email'})
        me.recovery_email = em
    if d.get('dark_mode') is not None:
        me.dark_mode = bool(d.get('dark_mode'))
    if d.get('wallpaper'):
        me.wallpaper = clean(d.get('wallpaper'), 50)
    if d.get('privacy_last_seen'):
        me.privacy_last_seen = clean(d.get('privacy_last_seen'), 20)
    if d.get('privacy_photo'):
        me.privacy_photo = clean(d.get('privacy_photo'), 20)
    if d.get('privacy_about'):
        me.privacy_about = clean(d.get('privacy_about'), 20)
    if d.get('read_receipts') is not None:
        me.read_receipts = bool(d.get('read_receipts'))
    if d.get('notifications') is not None:
        me.notifications = bool(d.get('notifications'))
    if d.get('font_size'):
        me.font_size = clean(d.get('font_size'), 20)
    if d.get('chat_color'):
        me.chat_color = clean(d.get('chat_color'), 20)
    db.session.commit()
    return jsonify({'ok': True, 'user': pub_user(me)})

@app.route('/api/change_password', methods=['POST'])
def change_password():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    if not d.get('old_password') or not d.get('new_password'):
        return jsonify({'ok': False, 'error': 'Enter old and new password'})
    if not check_password_hash(me.password, d.get('old_password')):
        return jsonify({'ok': False, 'error': 'Wrong old password'})
    if not is_valid_password(d.get('new_password')):
        return jsonify({'ok': False, 'error': 'New password too short'})
    me.password = generate_password_hash(d.get('new_password'))
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    d = request.get_json(silent=True) or {}
    username = clean_username(d.get('username'))
    u = User.query.filter_by(username=username).first()
    if not u:
        return jsonify({'ok': False, 'error': 'User not found'})
    if not u.recovery_email or u.recovery_email != clean(d.get('recovery_email'), 100):
        return jsonify({'ok': False, 'error': 'Recovery email not match. Set it in Settings first'})
    if not is_valid_password(d.get('new_password')):
        return jsonify({'ok': False, 'error': 'New password too short'})
    u.password = generate_password_hash(d.get('new_password'))
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/delete_account', methods=['POST'])
def delete_account():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    if not check_password_hash(me.password, d.get('password') or ''):
        return jsonify({'ok': False, 'error': 'Wrong password'})
    me.delete_at = datetime.utcnow() + timedelta(days=15)
    me.bio = 'Account scheduled for deletion. Appeal in 15 days.'
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Delete scheduled. Appeal in 15 days via Support'})

@app.route('/api/cancel_delete', methods=['POST'])
def cancel_delete():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if me:
        me.delete_at = datetime.utcnow()
        me.bio = 'Hey there! I am using MyQchat'
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/api/send', methods=['POST'])
def send():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    text = clean(d.get('text'), MAX_MSG_LEN)
    to_uid = clean(d.get('to_uid'), 20)
    if not text or not to_uid:
        return jsonify({'ok': False, 'error': 'Empty message'})
    if not can_send_to(me.uid, to_uid):
        return jsonify({'ok': False, 'error': 'User blocked you or you blocked user'})
    if not check_rate_limit(me.uid, 60, 200):
        return jsonify({'ok': False, 'error': 'Too many messages. Wait a minute'})
    m = Message(sender_uid=me.uid, sender_name=me.name, to_uid=to_uid, text=text, msg_type=clean(d.get('msg_type'), 20) or 'text', reply_to=clean(d.get('reply_to'), 20), reply_text=clean(d.get('reply_text'), 500))
    db.session.add(m)
    db.session.commit()
    return jsonify({'ok': True, 'id': m.id, 'message': pub_message(m)})

@app.route('/api/messages', methods=['GET'])
def messages():
    me = get_me()
    with_uid = clean(request.args.get('with'), 20)
    if not me or not with_uid:
        return jsonify({'messages': []})
    mark_read(me.uid, with_uid)
    rows = Message.query.filter(((Message.sender_uid==me.uid) & (Message.to_uid==with_uid)) | ((Message.sender_uid==with_uid) & (Message.to_uid==me.uid))).order_by(Message.id.asc()).limit(1000).all()
    return jsonify({'messages': [pub_message(m) for m in rows]})

@app.route('/api/chats', methods=['GET'])
def chats():
    me = get_me()
    bot = {'uid': 'BOT', 'username': 'QWNG Bot', 'name': 'QWNG Bot', 'bio': 'Always online. Type help', 'avatar_color': '#075e54', 'tick': 'L', 'online': True, 'last_seen': 'Now'}
    arr = [{'user': bot, 'last': 'Type help to see all options', 'time': 'Now', 'unread': 0}]
    if me:
        contact_uids = set()
        rows = Message.query.filter((Message.sender_uid==me.uid) | (Message.to_uid==me.uid)).order_by(Message.id.desc()).limit(200).all()
        for m in rows:
            other = m.to_uid if m.sender_uid == me.uid else m.sender_uid
            if other and other != 'BOT' and other not in contact_uids:
                contact_uids.add(other)
                u = User.query.filter_by(uid=other).first()
                if u:
                    arr.append({'user': pub_user(u), 'last': m.text[:60], 'time': time_ago(m.created_at), 'unread': get_unread_count(me.uid, other)})
        crows = Contact.query.filter_by(owner_uid=me.uid).all()
        for c in crows:
            if c.contact_uid not in contact_uids:
                u = User.query.filter_by(uid=c.contact_uid).first()
                if u:
                    arr.append({'user': pub_user(u), 'last': 'Tap to chat', 'time': 'Now', 'unread': 0})
    return jsonify({'chats': arr})

@app.route('/api/delete_msg', methods=['POST'])
def delete_msg():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    m = Message.query.filter_by(id=d.get('msg_id')).first()
    if not m:
        return jsonify({'ok': False, 'error': 'Message not found'})
    if m.sender_uid != me.uid:
        db.session.delete(m)
        db.session.commit()
        return jsonify({'ok': True, 'mode': 'for_me'})
    if d.get('for_everyone'):
        m.text = 'This message was deleted'
        m.is_deleted = True
        db.session.commit()
        return jsonify({'ok': True, 'mode': 'for_everyone'})
    db.session.delete(m)
    db.session.commit()
    return jsonify({'ok': True, 'mode': 'for_me'})

@app.route('/api/star_msg', methods=['POST'])
def star_msg():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    m = Message.query.filter_by(id=d.get('msg_id')).first()
    if not m:
        return jsonify({'ok': False})
    m.starred = not m.starred
    if m.starred:
        if not StarMsg.query.filter_by(owner_uid=me.uid, msg_id=str(m.id)).first():
            db.session.add(StarMsg(owner_uid=me.uid, msg_id=str(m.id), text=m.text, from_name=m.sender_name))
    else:
        s = StarMsg.query.filter_by(owner_uid=me.uid, msg_id=str(m.id)).first()
        if s:
            db.session.delete(s)
    db.session.commit()
    return jsonify({'ok': True, 'starred': m.starred})

@app.route('/api/starred', methods=['GET'])
def starred():
    me = get_me()
    if not me:
        return jsonify({'starred': []})
    rows = StarMsg.query.filter_by(owner_uid=me.uid).order_by(StarMsg.id.desc()).all()
    return jsonify({'starred': [{'id': s.id, 'msg_id': s.msg_id, 'text': s.text, 'from_name': s.from_name} for s in rows]})

@app.route('/api/forward', methods=['POST'])
def forward():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    text = clean(d.get('text'), MAX_MSG_LEN)
    to_uid = clean(d.get('to_uid'), 20)
    if not text or not to_uid:
        return jsonify({'ok': False})
    if not can_send_to(me.uid, to_uid):
        return jsonify({'ok': False, 'error': 'Blocked'})
    m = Message(sender_uid=me.uid, sender_name=me.name, to_uid=to_uid, text=text, forwarded=True)
    db.session.add(m)
    db.session.commit()
    return jsonify({'ok': True, 'id': m.id})
@app.route('/api/create_group', methods=['POST'])
def create_group():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    name = clean(d.get('name'), MAX_GROUP_NAME)
    if not name:
        return jsonify({'ok': False, 'error': 'Enter group name'})
    gid = make_gid()
    g = Group(gid=gid, name=name, desc=clean(d.get('desc'), 200), creator_uid=me.uid, members=me.uid, admins=me.uid)
    db.session.add(g)
    db.session.commit()
    return jsonify({'ok': True, 'gid': gid, 'group': pub_group(g)})

@app.route('/api/groups', methods=['GET'])
def groups():
    me = get_me()
    if not me:
        return jsonify({'groups': []})
    rows = Group.query.all()
    out = []
    for g in rows:
        members = g.members.split(',') if g.members else []
        if me.uid in members or g.creator_uid == me.uid:
            out.append(pub_group(g))
    return jsonify({'groups': out})

@app.route('/api/group_add_member', methods=['POST'])
def group_add_member():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    gid = clean(d.get('gid'), 20)
    uid = clean(d.get('uid'), 20)
    g = Group.query.filter_by(gid=gid).first()
    if not g:
        return jsonify({'ok': False, 'error': 'Group not found'})
    if g.creator_uid != me.uid and me.uid not in (g.admins.split(',') if g.admins else []):
        return jsonify({'ok': False, 'error': 'Only admin can add'})
    if add_group_member(gid, uid):
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/api/group_remove_member', methods=['POST'])
def group_remove_member():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    gid = clean(d.get('gid'), 20)
    uid = clean(d.get('uid'), 20)
    g = Group.query.filter_by(gid=gid).first()
    if not g or g.creator_uid != me.uid:
        return jsonify({'ok': False, 'error': 'Only creator can remove'})
    if remove_group_member(gid, uid):
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/api/group_leave', methods=['POST'])
def group_leave():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    gid = clean(d.get('gid'), 20)
    if remove_group_member(gid, me.uid):
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/api/group_send', methods=['POST'])
def group_send():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    gid = clean(d.get('gid'), 20)
    text = clean(d.get('text'), MAX_MSG_LEN)
    if not gid or not text:
        return jsonify({'ok': False})
    if not is_group_member(gid, me.uid):
        return jsonify({'ok': False, 'error': 'Not a member'})
    m = GroupMsg(gid=gid, sender_uid=me.uid, sender_name=me.name, text=text, msg_type='text')
    db.session.add(m)
    db.session.commit()
    return jsonify({'ok': True, 'id': m.id})

@app.route('/api/group_messages', methods=['GET'])
def group_messages():
    me = get_me()
    gid = clean(request.args.get('gid'), 20)
    if not me or not gid:
        return jsonify({'messages': []})
    if not is_group_member(gid, me.uid):
        return jsonify({'messages': [], 'error': 'Not a member'})
    rows = GroupMsg.query.filter_by(gid=gid).order_by(GroupMsg.id.asc()).limit(1000).all()
    return jsonify({'messages': [{'id': m.id, 'sender_uid': m.sender_uid, 'sender_name': m.sender_name, 'text': m.text, 'msg_type': m.msg_type, 'time': time_ago(m.created_at)} for m in rows]})

@app.route('/api/songs', methods=['GET'])
def songs():
    q = clean(request.args.get('q'), 100)
    rows = Song.query.filter_by(is_active=True).order_by(Song.play_count.desc()).all()
    out = []
    for s in rows:
        if q and q.lower() not in s.title.lower() and q.lower() not in s.artist.lower():
            continue
        out.append(pub_song(s))
    return jsonify({'songs': out, 'count': len(out)})

@app.route('/api/admin_add_song', methods=['POST'])
def admin_add_song():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only admin'})
    title = clean(d.get('title'), 100)
    url = clean(d.get('url'), 500)
    if not title or not url:
        return jsonify({'ok': False, 'error': 'Title and URL required'})
    if not url.startswith('http'):
        return jsonify({'ok': False, 'error': 'URL must start with http'})
    s = Song(title=title, artist=clean(d.get('artist'), 100) or 'QWNG Music', url=url, added_by=me.username, is_active=True)
    db.session.add(s)
    db.session.commit()
    return jsonify({'ok': True, 'id': s.id, 'song': pub_song(s)})

@app.route('/api/admin_delete_song', methods=['POST'])
def admin_delete_song():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False})
    s = Song.query.filter_by(id=d.get('song_id')).first()
    if s:
        s.is_active = False
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Song not found'})

@app.route('/api/song_play', methods=['POST'])
def song_play():
    d = request.get_json(silent=True) or {}
    s = Song.query.filter_by(id=d.get('song_id')).first()
    if s:
        s.play_count = (s.play_count or 0) + 1
        db.session.commit()
        return jsonify({'ok': True, 'play_count': s.play_count})
    return jsonify({'ok': False})

@app.route('/api/create_status', methods=['POST'])
def create_status():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    text = clean(d.get('text'), MAX_STATUS_LEN)
    if not text and not d.get('song_id') and not d.get('song_url'):
        return jsonify({'ok': False, 'error': 'Write something or choose song'})
    song_title = clean(d.get('song_title'), 100)
    song_url = clean(d.get('song_url'), 500)
    song_id = str(d.get('song_id') or '')
    if d.get('song_id'):
        s = Song.query.filter_by(id=d.get('song_id')).first()
        if s:
            song_title = s.title
            song_url = s.url
            s.play_count = (s.play_count or 0) + 1
    if song_url and not song_url.startswith('http'):
        return jsonify({'ok': False, 'error': 'Song URL must start with http'})
    old = StatusItem.query.filter_by(uid=me.uid).all()
    for o in old:
        db.session.delete(o)
    st = StatusItem(uid=me.uid, name=me.name, text=text, song_title=song_title, song_url=song_url, song_id=song_id, views=0)
    db.session.add(st)
    db.session.commit()
    return jsonify({'ok': True, 'status': pub_status(st)})

@app.route('/api/status', methods=['GET'])
def status():
    delete_expired_status()
    me = get_me()
    rows = StatusItem.query.order_by(StatusItem.created_at.desc()).limit(200).all()
    out = []
    for s in rows:
        out.append(pub_status(s))
    return jsonify({'status': out})

@app.route('/api/my_status', methods=['GET'])
def my_status():
    me = get_me()
    if not me:
        return jsonify({'status': []})
    rows = StatusItem.query.filter_by(uid=me.uid).order_by(StatusItem.created_at.desc()).all()
    return jsonify({'status': [pub_status(s) for s in rows]})

@app.route('/api/delete_status', methods=['POST'])
def delete_status():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    s = StatusItem.query.filter_by(id=d.get('status_id'), uid=me.uid).first()
    if s:
        db.session.delete(s)
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Status not found'})

@app.route('/api/view_status', methods=['POST'])
def view_status():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    s = StatusItem.query.filter_by(id=d.get('status_id')).first()
    if s and s.uid != me.uid:
        s.views = (s.views or 0) + 1
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/log_call', methods=['POST'])
def log_call():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    to_uid = clean(d.get('to_uid'), 20)
    to = User.query.filter_by(uid=to_uid).first()
    if not to:
        return jsonify({'ok': False, 'error': 'User not found'})
    if not can_send_to(me.uid, to_uid):
        return jsonify({'ok': False, 'error': 'Blocked'})
    c = CallLog(from_uid=me.uid, from_name=me.name, to_uid=to_uid, to_name=to.name, call_type=clean(d.get('call_type'), 20) or 'voice', duration=clean(d.get('duration'), 20) or '0', status=clean(d.get('status'), 20) or 'completed')
    db.session.add(c)
    db.session.commit()
    return jsonify({'ok': True, 'call': pub_call(c)})

@app.route('/api/calls', methods=['GET'])
def calls():
    me = get_me()
    if not me:
        return jsonify({'calls': []})
    rows = CallLog.query.filter((CallLog.from_uid==me.uid) | (CallLog.to_uid==me.uid)).order_by(CallLog.id.desc()).limit(200).all()
    return jsonify({'calls': [pub_call(c) for c in rows]})@app.route('/api/request_tick', methods=['POST'])
def request_tick():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    tick = clean(d.get('tick'), 20)
    if tick not in ['Blue','Orange','Green']:
        return jsonify({'ok': False, 'error': 'Only Blue, Orange, Green can be requested. L is only Owner, Scam is after report'})
    if tick == me.tick:
        return jsonify({'ok': False, 'error': 'You already have this tick'})
    old = TickReq.query.filter_by(uid=me.uid, status='pending').first()
    if old:
        return jsonify({'ok': False, 'error': 'One request already pending. Wait for admin'})
    tr = TickReq(uid=me.uid, username=me.username, name=me.name, tick=tick, reason=clean(d.get('reason'), 500), status='pending')
    db.session.add(tr)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Tick request sent to admin'})

@app.route('/api/my_tick_requests', methods=['GET'])
def my_tick_requests():
    me = get_me()
    if not me:
        return jsonify({'ticks': []})
    rows = TickReq.query.filter_by(uid=me.uid).order_by(TickReq.id.desc()).all()
    return jsonify({'ticks': [pub_tick(t) for t in rows]})

@app.route('/api/tick_requests', methods=['GET'])
def tick_requests():
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ticks': [], 'error': 'Only admin'})
    rows = TickReq.query.filter_by(status='pending').order_by(TickReq.id.asc()).all()
    return jsonify({'ticks': [pub_tick(t) for t in rows]})

@app.route('/api/admin_tick_decide', methods=['POST'])
def admin_tick_decide():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only admin'})
    tr = TickReq.query.filter_by(id=d.get('tick_id')).first()
    if not tr:
        return jsonify({'ok': False, 'error': 'Request not found'})
    action = clean(d.get('action'), 20)
    if action == 'approve':
        tr.status = 'approved'
        tr.admin_note = clean(d.get('admin_note'), 200)
        u = User.query.filter_by(uid=tr.uid).first()
        if u:
            u.tick = tr.tick
    elif action == 'reject':
        tr.status = 'rejected'
        tr.admin_note = clean(d.get('admin_note'), 200) or 'Not approved'
    else:
        return jsonify({'ok': False, 'error': 'Action must be approve or reject'})
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/report', methods=['POST'])
def report():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    reported_uid = clean(d.get('reported_uid'), 20)
    if not reported_uid or reported_uid == me.uid:
        return jsonify({'ok': False, 'error': 'Invalid user'})
    target = User.query.filter_by(uid=reported_uid).first()
    if not target:
        return jsonify({'ok': False, 'error': 'User not found'})
    reason = clean(d.get('reason'), 50)
    if reason not in ['Scam','Harassment','Fake','Spam','Abuse','Other']:
        reason = 'Other'
    detail = clean(d.get('detail'), 400)
    if not detail:
        return jsonify({'ok': False, 'error': 'Write detail in 400 letters'})
    old = Report.query.filter_by(reporter_uid=me.uid, reported_uid=reported_uid, status='pending').first()
    if old:
        return jsonify({'ok': False, 'error': 'Report already pending'})
    rep = Report(reporter_uid=me.uid, reporter_name=me.name, reported_uid=reported_uid, reported_name=target.name, reason=reason, detail=detail, status='pending')
    db.session.add(rep)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Report sent to admin'})

@app.route('/api/my_reports', methods=['GET'])
def my_reports():
    me = get_me()
    if not me:
        return jsonify({'reports': []})
    rows = Report.query.filter_by(reporter_uid=me.uid).order_by(Report.id.desc()).all()
    return jsonify({'reports': [pub_report(r) for r in rows]})

@app.route('/api/reports', methods=['GET'])
def reports():
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'reports': [], 'error': 'Only admin'})
    rows = Report.query.filter_by(status='pending').order_by(Report.id.asc()).all()
    return jsonify({'reports': [pub_report(r) for r in rows]})

@app.route('/api/admin_report_decide', methods=['POST'])
def admin_report_decide():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only admin'})
    rep = Report.query.filter_by(id=d.get('report_id')).first()
    if not rep:
        return jsonify({'ok': False, 'error': 'Report not found'})
    action = clean(d.get('action'), 20)
    target = User.query.filter_by(uid=rep.reported_uid).first()
    if action == 'scam':
        rep.status = 'scam'
        if target:
            target.tick = 'Scam'
    elif action == 'ban':
        rep.status = 'banned'
        if target:
            target.tick = 'Scam'
            target.banned_until = datetime.utcnow() + timedelta(days=30)
    elif action == 'warn':
        rep.status = 'warned'
    elif action == 'reject':
        rep.status = 'rejected'
    else:
        return jsonify({'ok': False, 'error': 'Action must be scam, ban, warn, reject'})
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/admin_broadcast', methods=['POST'])
def admin_broadcast():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only admin'})
    text = clean(d.get('text'), 500)
    if not text:
        return jsonify({'ok': False, 'error': 'Write message'})
    btype = clean(d.get('btype'), 20) or 'Announcement'
    if btype not in ['Announcement','Warning','Ad']:
        btype = 'Announcement'
    db.session.add(BroadcastMsg(from_uid=me.uid, from_name=me.name, text=text, btype=btype))
    users = User.query.all()
    sent = 0
    for u in users:
        if u.uid != me.uid:
            m = Message(sender_uid=me.uid, sender_name='MyQchat', to_uid=u.uid, text='[' + btype + '] ' + text, msg_type='broadcast')
            db.session.add(m)
            sent += 1
    db.session.commit()
    return jsonify({'ok': True, 'sent_to': sent})

@app.route('/api/broadcasts', methods=['GET'])
def broadcasts():
    me = get_me()
    if not me:
        return jsonify({'broadcasts': []})
    rows = BroadcastMsg.query.order_by(BroadcastMsg.id.desc()).limit(50).all()
    return jsonify({'broadcasts': [{'id': b.id, 'from_name': b.from_name, 'text': b.text, 'btype': b.btype, 'time': time_ago(b.created_at)} for b in rows]})

@app.route('/api/admin_users', methods=['GET'])
def admin_users():
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'users': [], 'error': 'Only admin'})
    q = clean(request.args.get('q'), 50)
    rows = User.query.all()
    out = []
    for u in rows:
        if q and q.lower() not in u.username.lower() and q.lower() not in u.name.lower():
            continue
        out.append(pub_user(u))
    return jsonify({'users': out})

@app.route('/api/admin_remove_tick', methods=['POST'])
def admin_remove_tick():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False})
    u = User.query.filter_by(uid=clean(d.get('uid'), 20)).first()
    if u and u.username != 'LoyalWQ':
        u.tick = ''
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Cannot remove Owner tick'})

@app.route('/api/admin_stats', methods=['GET'])
def admin_stats():
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only admin'})
    return jsonify({'ok': True, 'total_users': User.query.count(), 'total_messages': Message.query.count(), 'total_groups': Group.query.count(), 'total_songs': Song.query.count(), 'total_status': StatusItem.query.count(), 'pending_ticks': TickReq.query.filter_by(status='pending').count(), 'pending_reports': Report.query.filter_by(status='pending').count(), 'total_calls': CallLog.query.count()})

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False})
    c1 = delete_expired_status()
    c2 = delete_expired_messages()
    return jsonify({'ok': True, 'deleted_status': c1, 'deleted_messages': c2})
  FRONTEND_HEAD = '''
<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>MyQchat</title><style>
*{box-sizing:border-box}
body{font-family:Arial,sans-serif;margin:0;background:#ece5dd;color:#111}
.top{background:#075e54;color:#fff;padding:12px 14px;font-size:20px;font-weight:bold;display:flex;justify-content:space-between;align-items:center}
.top small{font-size:12px;font-weight:normal;opacity:0.9}
.card{background:#fff;margin:10px;padding:12px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
input,select,textarea{width:100%;padding:11px;margin:6px 0;border:1px solid #ccc;border-radius:8px;font-size:15px}
textarea{min-height:70px;resize:vertical}
button{background:#075e54;color:#fff;border:none;padding:12px;border-radius:8px;width:100%;font-size:16px;cursor:pointer}
button:active{opacity:0.9}
button.danger{background:#d32f2f}
button.secondary{background:#fff;color:#075e54;border:1px solid #075e54}
.msg{padding:8px 11px;border-radius:12px;margin:6px;max-width:78%;font-size:15px;line-height:1.4;word-break:break-word}
.mine{background:#dcf8c6;margin-left:auto;text-align:right;border-bottom-right-radius:4px}
.other{background:#fff;border-bottom-left-radius:4px}
.tabs{display:flex;background:#075e54;color:#fff;position:sticky;top:0;z-index:10}
.tabs div{flex:1;text-align:center;padding:12px 4px;cursor:pointer;font-size:14px}
.tabs div.active{background:#054d43;font-weight:bold}
.hidden{display:none}
.small{font-size:12px;color:#666;line-height:1.4}
.link{color:#34b7f1;cursor:pointer;text-decoration:underline}
.flex{display:flex;gap:8px;align-items:center}
.flex button{width:auto;flex:1}
.avatar{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:18px;flex-shrink:0}
.row{display:flex;gap:10px;align-items:center;padding:9px;border-bottom:1px solid #f0f0f0;cursor:pointer}
.row:last-child{border-bottom:none}
.row b{font-size:15px}
.row .sub{font-size:13px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
.badge{background:#25d366;color:#fff;font-size:11px;padding:2px 7px;border-radius:10px}
.tick{color:#34b7f1;font-weight:bold}
.tick-orange{color:#ff8c00;font-weight:bold}
.tick-green{color:#25d366;font-weight:bold}
.tick-scam{color:#d32f2f;font-weight:bold}
.chip{display:inline-block;background:#e8f5e9;color:#075e54;padding:4px 10px;border-radius:12px;font-size:12px;margin:2px}
.songrow{display:flex;gap:8px;align-items:center;padding:9px;border:1px solid #eee;border-radius:10px;margin:5px 0}
.songrow button{width:70px;padding:8px}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:flex-end;justify-content:center;z-index:50}
.modal-box{background:#fff;width:100%;max-width:520px;max-height:85vh;overflow:auto;padding:16px;border-radius:16px 16px 0 0}
.searchbox{position:sticky;top:0;background:#fff;padding-bottom:6px;z-index:5}
</style></head><body>
<div class='top'><span>MyQchat</span><small>by QWNG</small></div>
<div id='authPage' class='card'><h2 style='margin:4px 0'>Welcome to MyQchat</h2><p class='small'>Simple, fast and safe chatting. Login with Username and Password.</p><label>Username</label><input id='loginUser' placeholder='Username' autocomplete='username'><label>Password</label><input id='loginPass' type='password' placeholder='Password' autocomplete='current-password'><button onclick='doLogin()'>Login</button><p style='text-align:center;margin:14px 0 6px'>OR</p><label>New Username</label><input id='suUser' placeholder='New Username - e.g. rahul123'><label>Your Name</label><input id='suName' placeholder='Your Name'><label>New Password</label><input id='suPass' type='password' placeholder='New Password'><button onclick='doSignup()'>Create Account</button><p class='small' style='text-align:center;margin-top:12px'>By continuing, you agree to our <span class='link' onclick='showTerms()'>Terms</span> and <span class='link' onclick='showPrivacy()'>Privacy</span> • <span class='link' onclick='showHelp()'>Help</span></p><p class='small' style='text-align:center'><span class='link' onclick='showForgot()'>Forgot Password?</span></p><p class='small' style='text-align:center'>Support: qwngofficial@gmail.com</p></div>
<div id='mainPage' class='hidden'>
<div class='tabs'><div id='tabChats' class='active' onclick='showTab("Chats")'>Chats</div><div id='tabGroups' onclick='showTab("Groups")'>Groups</div><div id='tabStatus' onclick='showTab("Status")'>Status</div><div id='tabCalls' onclick='showTab("Calls")'>Calls</div><div id='tabSettings' onclick='showTab("Settings")'>Settings</div></div>
<div id='pageChats' class='card'><div class='searchbox'><input id='searchBox' placeholder='Search by Username or 8-digit UID' oninput='searchUsers()'><div id='searchRes'></div></div><div style='display:flex;justify-content:space-between;align-items:center'><h3 style='margin:6px 0'>Chats</h3><span class='small'>Online: <span id='onlineCount'>0</span></span></div><div id='chatList'></div><div id='broadcastBox'></div></div>
<div id='pageGroups' class='card hidden'><h3>Groups</h3><input id='grpName' placeholder='Group Name'><input id='grpDesc' placeholder='Group Description'><button onclick='createGroup()'>Create Group</button><div id='groupList' style='margin-top:10px'></div></div>
<div id='pageStatus' class='card hidden'><h3>Status — 24 hours</h3><textarea id='statusText' placeholder='Write status...'></textarea><label>Choose Song from Library</label><select id='statusSong'><option value=''>No Song</option></select><label>Or Custom Song URL</label><input id='statusCustomUrl' placeholder='Paste your song URL here'><input id='statusCustomTitle' placeholder='Custom Song Title'><button onclick='postStatus()'>Post Status</button><div id='statusList' style='margin-top:10px'></div><h4>Music Library</h4><input id='songSearch' placeholder='Search song...' oninput='loadSongs()'><div id='songList'></div></div>
<div id='pageCalls' class='card hidden'><h3>Calls</h3><p class='small'>Voice and Video call history. Tap a user in Chats to call.</p><div id='callList'></div></div>
<div id='pageSettings' class='card hidden'><h3>Settings</h3><label>Name</label><input id='setName' placeholder='Name'><label>Bio</label><textarea id='setBio' placeholder='Bio - About you'></textarea><label>Recovery Email (for Forgot Password)</label><input id='setRecovery' placeholder='Recovery Email'><label>Wallpaper</label><select id='setWallpaper'><option value='default'>Wallpaper Default</option><option value='green'>Wallpaper Green</option><option value='dark'>Wallpaper Dark</option><option value='blue'>Wallpaper Blue</option></select><label>Font Size</label><select id='setFont'><option value='Small'>Font Small</option><option value='Medium'>Font Medium</option><option value='Large'>Font Large</option></select><label>Chat Color</label><select id='setChatColor'><option value='Green'>Chat Green</option><option value='Blue'>Chat Blue</option><option value='Orange'>Chat Orange</option></select><label><input type='checkbox' id='setDark' style='width:auto'> Dark Mode</label><label><input type='checkbox' id='setRead' style='width:auto' checked> Read Receipts (Blue Tick)</label><label><input type='checkbox' id='setNotif' style='width:auto' checked> Notifications</label><label>Last Seen Privacy</label><select id='setLastSeen'><option value='Everyone'>Everyone</option><option value='Contacts'>My Contacts</option><option value='Nobody'>Nobody</option></select><button onclick='saveSettings()'>Save Settings</button><hr><h4>Request Tick</h4><label>Tick Type</label><select id='tickType'><option value='Blue'>Blue Tick</option><option value='Orange'>Orange Tick</option><option value='Green'>Green Tick</option></select><input id='tickReason' placeholder='Reason for Tick - Why you need it?'><button onclick='requestTick()'>Request Tick</button><div id='myTickBox'></div><hr><h4>Report User</h4><input id='reportUser' placeholder='Reported UID - 8 digit'><select id='reportReason'><option value='Scam'>Scam</option><option value='Harassment'>Harassment</option><option value='Fake'>Fake</option><option value='Spam'>Spam</option><option value='Abuse'>Abuse</option><option value='Other'>Other</option></select><textarea id='reportDetail' placeholder='Detail - 400 letters'></textarea><button onclick='sendReport()'>Report User</button><hr><div id='adminBox' class='hidden'><h3>Admin Panel</h3><p class='small'>Only Owner can see this.</p><label>Song Title</label><input id='songTitle' placeholder='Song Title'><label>Song Artist</label><input id='songArtist' placeholder='Song Artist'><label>Song URL</label><input id='songUrl' placeholder='Song URL - https://...'><button onclick='addSong()'>Add Song</button><hr><label>Broadcast Message</label><textarea id='broadcastText' placeholder='Broadcast Message to all users'></textarea><select id='broadcastType'><option value='Announcement'>Announcement</option><option value='Warning'>Warning</option><option value='Ad'>Ad</option></select><button onclick='sendBroadcast()'>Send Broadcast to All</button><div id='adminStats' style='margin-top:10px'></div><div id='tickList'></div><div id='reportList'></div><button onclick='loadAdminLists()'>Refresh Admin Lists</button></div><hr><button onclick='showTerms()' class='secondary'>Terms</button><br><br><button onclick='showPrivacy()' class='secondary'>Privacy</button><br><br><button onclick='showHelp()' class='secondary'>Help</button><br><br><button onclick='showStarred()' class='secondary'>Starred Messages</button><br><br><button onclick='showBlocked()' class='secondary'>Blocked Users</button><br><br><button onclick='doLogout()' class='secondary'>Logout</button><br><br><button onclick='deleteAccount()' class='danger'>Delete Account</button></div>
</div>
<div id='chatPage' class='card hidden'><button onclick='backToChats()' class='secondary' style='width:80px'>Back</button><h3 id='chatTitle'>Chat</h3><p class='small' id='chatSub'></p><div id='chatMsgs' style='max-height:420px;overflow:auto;background:#ece5dd;padding:8px;border-radius:10px;min-height:200px'></div><div class='flex' style='margin-top:8px'><input id='chatInput' placeholder='Message' onkeydown='if(event.key==="Enter")sendChat()'><button onclick='sendChat()' style='width:80px'>Send</button></div><div class='flex' style='margin-top:6px'><button onclick='attachFile()' class='secondary'>Attach</button><button onclick='openEmoji()' class='secondary'>Emoji</button><button onclick='recordVoice()' class='secondary'>Voice</button><button onclick='startCall("voice")' class='secondary'>Call</button><button onclick='startCall("video")' class='secondary'>Video</button></div><div id='emojiBox' class='hidden' style='font-size:26px;padding:10px;cursor:pointer'><span onclick='pickEmoji("😊")'>😊</span> <span onclick='pickEmoji("😂")'>😂</span> <span onclick='pickEmoji("❤️")'>❤️</span> <span onclick='pickEmoji("👍")'>👍</span> <span onclick='pickEmoji("🙏")'>🙏</span> <span onclick='pickEmoji("🎉")'>🎉</span> <span onclick='pickEmoji("🔥")'>🔥</span> <span onclick='pickEmoji("🌸")'>🌸</span></div><div id='replyBox' class='hidden small' style='background:#fff;padding:6px;border-radius:8px;margin-top:6px'>Replying to: <span id='replyText'></span> <span class='link' onclick='cancelReply()'>Cancel</span></div></div>
<div id='modal' class='hidden'><div class='modal-bg' onclick='if(event.target===this)closeModal()'><div class='modal-box'><button onclick='closeModal()' class='secondary' style='width:80px'>Close</button><div id='modalBody'></div></div></div></div>
'''
FRONTEND_JS = '''
<script>let ME=null; let CUR=null; let CURNAME=''; let REPLY_TO=''; let REPLY_TEXT='';
async function api(p,o){let r=await fetch(p,{method:o&&o.method||'GET',headers:{'Content-Type':'application/json'},body:o&&o.body?JSON.stringify(o.body):undefined}); return r.json();}
function tickHtml(t){if(t==='L')return ' <span class="tick">L ✓</span>'; if(t==='Blue')return ' <span class="tick">✓</span>'; if(t==='Orange')return ' <span class="tick-orange">✓</span>'; if(t==='Green')return ' <span class="tick-green">✓</span>'; if(t==='Scam')return ' <span class="tick-scam">SCAM</span>'; return '';}
async function doLogin(){let u=document.getElementById('loginUser').value.trim(); let p=document.getElementById('loginPass').value; if(!u||!p){alert('Enter Username and Password');return;} let d=await api('/api/login',{method:'POST',body:{username:u,password:p}}); if(!d.ok){alert(d.error);return;} ME=d.user; localStorage.setItem('myq_uid',ME.uid); showMain();}
async function doSignup(){let u=document.getElementById('suUser').value.trim(); let n=document.getElementById('suName').value.trim(); let p=document.getElementById('suPass').value; if(!u||!p){alert('Enter Username and Password');return;} let d=await api('/api/signup',{method:'POST',body:{username:u,name:n,password:p}}); if(!d.ok){alert(d.error);return;} ME=d.user; localStorage.setItem('myq_uid',ME.uid); showMain();}
function showTab(name){['Chats','Groups','Status','Calls','Settings'].forEach(t=>{document.getElementById('page'+t).classList.add('hidden'); document.getElementById('tab'+t).classList.remove('active');}); document.getElementById('page'+name).classList.remove('hidden'); document.getElementById('tab'+name).classList.add('active'); if(name==='Chats')loadChats(); if(name==='Groups')loadGroups(); if(name==='Status')loadStatus(); if(name==='Calls')loadCalls(); if(name==='Settings')loadSettings();}
async function showMain(){document.getElementById('authPage').classList.add('hidden'); document.getElementById('mainPage').classList.remove('hidden'); document.getElementById('chatPage').classList.add('hidden'); showTab('Chats'); loadBroadcasts();}
async function searchUsers(){let q=document.getElementById('searchBox').value.trim(); if(q.length<2){document.getElementById('searchRes').innerHTML='';return;} let d=await api('/api/search_uid?q='+encodeURIComponent(q)); if(d.ok){document.getElementById('searchRes').innerHTML='<div class="row" onclick="openChat(\\''+d.user.uid+'\\',\\''+d.user.name+'\\')"><div class="avatar" style="background:'+d.user.avatar_color+'">'+d.user.name.charAt(0)+'</div><div><b>'+d.user.name+tickHtml(d.user.tick)+'</b><div class="sub">@'+d.user.username+' • UID '+d.user.uid+'</div></div></div>';} else {document.getElementById('searchRes').innerHTML='<p class="small">Not found</p>';}}
async function loadChats(){if(!ME) return; let d=await api('/api/chats?uid='+ME.uid); let h=''; let online=0; d.chats.forEach(c=>{if(c.user.online)online++; let un=c.unread?'<span class="badge">'+c.unread+'</span>':''; h+='<div class="row" onclick="openChat(\\''+c.user.uid+'\\',\\''+c.user.name+'\\')"><div class="avatar" style="background:'+(c.user.avatar_color||'#075e54')+'">'+c.user.name.charAt(0)+'</div><div style="flex:1"><b>'+c.user.name+tickHtml(c.user.tick)+'</b><div class="sub">'+c.last+'</div></div>'+un+'</div>';}); document.getElementById('chatList').innerHTML=h||'<p class="small">No chats yet. Search user and start chat.</p>'; document.getElementById('onlineCount').innerText=online;}
async function loadBroadcasts(){let d=await api('/api/broadcasts'); if(d.broadcasts&&d.broadcasts.length){let h='<h4>Announcements</h4>'; d.broadcasts.slice(0,3).forEach(b=>{h+='<div class="card" style="margin:6px 0;background:#fff8e1"><b>['+b.btype+']</b> '+b.text+'</div>';}); document.getElementById('broadcastBox').innerHTML=h;}}
async function loadGroups(){if(!ME) return; let d=await api('/api/groups?uid='+ME.uid); let h=''; d.groups.forEach(g=>{h+='<div class="row" onclick="openGroup(\\''+g.gid+'\\',\\''+g.name+'\\')"><div class="avatar" style="background:#128c7e">G</div><div><b>'+g.name+'</b><div class="sub">'+g.member_count+' members • '+g.desc+'</div></div></div>';}); document.getElementById('groupList').innerHTML=h||'<p class="small">No groups yet.</p>';}
async function loadStatus(){let d=await api('/api/status'); let h=''; d.status.forEach(s=>{h+='<div class="row" onclick="viewStatus('+s.id+')"><div class="avatar" style="background:#34b7f1">'+s.name.charAt(0)+'</div><div><b>'+s.name+'</b><div class="sub">'+s.text+'</div><div class="sub">Song: '+(s.song_title||'No Song')+' • '+s.time+'</div></div></div>';}); document.getElementById('statusList').innerHTML=h||'<p class="small">No status yet.</p>'; loadSongs();}
async function loadSongs(){let q=document.getElementById('songSearch')?document.getElementById('songSearch').value:''; let d=await api('/api/songs?q='+encodeURIComponent(q||'')); let sel=document.getElementById('statusSong'); if(sel){sel.innerHTML='<option value="">No Song</option>'; d.songs.forEach(s=>{sel.innerHTML+='<option value="'+s.id+'">'+s.title+' - '+s.artist+'</option>';});} let h=''; d.songs.forEach(s=>{h+='<div class="songrow"><div style="flex:1"><b>'+s.title+'</b><div class="small">'+s.artist+' • Played '+ (s.play_count||0) +'</div></div><button onclick="playSong(\\''+s.url+'\\')">Play</button></div>';}); document.getElementById('songList').innerHTML=h;}
function playSong(url){window.open(url,'_blank');}
async function viewStatus(id){await api('/api/view_status',{method:'POST',body:{my_uid:ME.uid,status_id:id}}); loadStatus();}
async function loadCalls(){if(!ME) return; let d=await api('/api/calls?uid='+ME.uid); let h=''; d.calls.forEach(c=>{h+='<div class="row"><div class="avatar" style="background:#25d366">C</div><div><b>'+c.from_name+' → '+c.to_name+'</b><div class="sub">'+c.call_type+' • '+c.duration+' sec • '+c.status+'</div></div></div>';}); document.getElementById('callList').innerHTML=h||'<p class="small">No calls yet.</p>';}
function loadSettings(){if(!ME) return; document.getElementById('setName').value=ME.name||''; document.getElementById('setBio').value=ME.bio||''; document.getElementById('setRecovery').value=ME.recovery_email||''; document.getElementById('setWallpaper').value=ME.wallpaper||'default'; document.getElementById('setFont').value=ME.font_size||'Medium'; document.getElementById('setChatColor').value=ME.chat_color||'Green'; document.getElementById('setDark').checked=!!ME.dark_mode; document.getElementById('setRead').checked=ME.read_receipts!==false; document.getElementById('setNotif').checked=ME.notifications!==false; document.getElementById('setLastSeen').value=ME.privacy_last_seen||'Everyone'; if(ME.is_admin){document.getElementById('adminBox').classList.remove('hidden'); loadAdmin();} loadMyTicks();}
async function loadMyTicks(){let d=await api('/api/my_tick_requests?uid='+ME.uid); if(d.ticks&&d.ticks.length){let h='<p class="small">Your Tick Requests:</p>'; d.ticks.forEach(t=>{h+='<div>'+t.tick+' - '+t.status+'</div>';}); document.getElementById('myTickBox').innerHTML=h;}}
async function loadAdmin(){if(!ME) return; let d=await api('/api/admin_stats?uid='+ME.uid); if(d.ok){document.getElementById('adminStats').innerHTML='<b>Stats:</b> Users '+d.total_users+' • Messages '+d.total_messages+' • Songs '+d.total_songs+' • Pending Ticks '+d.pending_ticks+' • Pending Reports '+d.pending_reports;}}
async function loadAdminLists(){let t=await api('/api/tick_requests?uid='+ME.uid); let h='<h4>Pending Ticks</h4>'; t.ticks.forEach(x=>{h+='<div>'+x.username+' wants '+x.tick+' - '+x.reason+' <button onclick="decideTick('+x.id+',\\'approve\\')">Approve</button> <button onclick="decideTick('+x.id+',\\'reject\\')" class="danger">Reject</button></div>';}); document.getElementById('tickList').innerHTML=h; let r=await api('/api/reports?uid='+ME.uid); let h2='<h4>Pending Reports</h4>'; r.reports.forEach(x=>{h2+='<div>'+x.reporter_name+' reported '+x.reported_uid+' - '+x.reason+' - '+x.detail+' <button onclick="decideReport('+x.id+',\\'scam\\')">Scam</button> <button onclick="decideReport('+x.id+',\\'reject\\')" class="danger">Reject</button></div>';}); document.getElementById('reportList').innerHTML=h2;}
async function decideTick(id,action){await api('/api/admin_tick_decide',{method:'POST',body:{my_uid:ME.uid,tick_id:id,action:action}}); loadAdminLists();}
async function decideReport(id,action){await api('/api/admin_report_decide',{method:'POST',body:{my_uid:ME.uid,report_id:id,action:action}}); loadAdminLists();}
async function addSong(){let t=document.getElementById('songTitle').value; let a=document.getElementById('songArtist').value; let u=document.getElementById('songUrl').value; if(!t||!u){alert('Enter Title and URL');return;} let d=await api('/api/admin_add_song',{method:'POST',body:{my_uid:ME.uid,title:t,artist:a,url:u}}); if(!d.ok){alert(d.error);return;} alert('Song Added'); loadSongs();}
async function sendBroadcast(){let t=document.getElementById('broadcastText').value; if(!t){alert('Write message');return;} await api('/api/admin_broadcast',{method:'POST',body:{my_uid:ME.uid,text:t,btype:document.getElementById('broadcastType').value}}); alert('Broadcast Sent');}
async function requestTick(){let t=document.getElementById('tickType').value; let r=document.getElementById('tickReason').value; if(!r){alert('Enter reason');return;} let d=await api('/api/request_tick',{method:'POST',body:{my_uid:ME.uid,tick:t,reason:r}}); alert(d.ok?'Tick Request Sent':d.error);}
async function sendReport(){let u=document.getElementById('reportUser').value; let r=document.getElementById('reportReason').value; let de=document.getElementById('reportDetail').value; if(!u||!de){alert('Enter UID and Detail');return;} let d=await api('/api/report',{method:'POST',body:{my_uid:ME.uid,reported_uid:u,reason:r,detail:de}}); alert(d.ok?'Report Sent':d.error);}
async function saveSettings(){let d=await api('/api/update_profile',{method:'POST',body:{uid:ME.uid,name:document.getElementById('setName').value,bio:document.getElementById('setBio').value,recovery_email:document.getElementById('setRecovery').value,wallpaper:document.getElementById('setWallpaper').value,font_size:document.getElementById('setFont').value,chat_color:document.getElementById('setChatColor').value,dark_mode:document.getElementById('setDark').checked,read_receipts:document.getElementById('setRead').checked,notifications:document.getElementById('setNotif').checked,privacy_last_seen:document.getElementById('setLastSeen').value}}); if(d.ok){ME=d.user; alert('Settings Saved');} else alert('Failed');}
async function postStatus(){let t=document.getElementById('statusText').value; let sid=document.getElementById('statusSong').value; let curl=document.getElementById('statusCustomUrl').value; let ctitle=document.getElementById('statusCustomTitle').value; let d=await api('/api/create_status',{method:'POST',body:{my_uid:ME.uid,text:t,song_id:sid,song_url:curl,song_title:ctitle}}); if(!d.ok){alert(d.error);return;} alert('Status Posted'); loadStatus();}
async function createGroup(){let n=document.getElementById('grpName').value; if(!n){alert('Enter group name');return;} let d=await api('/api/create_group',{method:'POST',body:{my_uid:ME.uid,name:n,desc:document.getElementById('grpDesc').value}}); if(d.ok){alert('Group Created'); loadGroups();} else alert(d.error);}
async function openChat(uid,name){CUR=uid; CURNAME=name; document.getElementById('mainPage').classList.add('hidden'); document.getElementById('chatPage').classList.remove('hidden'); document.getElementById('chatTitle').innerText=name; document.getElementById('chatSub').innerText='UID: '+uid; loadChatMsgs();}
async function openGroup(gid,name){CUR='GROUP:'+gid; CURNAME=name; document.getElementById('mainPage').classList.add('hidden'); document.getElementById('chatPage').classList.remove('hidden'); document.getElementById('chatTitle').innerText=name+' (Group)'; loadChatMsgs();}
async function loadChatMsgs(){if(!CUR) return; if(CUR==='BOT'){document.getElementById('chatMsgs').innerHTML='<div class="msg other">Hello! I am QWNG Bot. Type <b>help</b> to see all options.</div>'; return;} if(CUR.startsWith('GROUP:')){let gid=CUR.replace('GROUP:',''); let d=await api('/api/group_messages?uid='+ME.uid+'&gid='+gid); let h=''; d.messages.forEach(m=>{let cls=m.sender_uid===ME.uid?'mine':'other'; h+='<div class="msg '+cls+'"><b>'+m.sender_name+'</b><br>'+m.text+'</div>';}); document.getElementById('chatMsgs').innerHTML=h||'<p class="small">No messages yet.</p>'; return;} let d=await api('/api/messages?uid='+ME.uid+'&with='+CUR); let h=''; d.messages.forEach(m=>{let cls=m.sender_uid===ME.uid?'mine':'other'; let rep=m.reply_text?'<div class="small">Reply: '+m.reply_text+'</div>':''; h+='<div class="msg '+cls+'" onclick="setReply('+m.id+',\\''+m.text.replace(/'/g,'')+'\\')">'+rep+m.text+(m.forwarded?' <span class="small">(Forwarded)</span>':'')+'</div>';}); document.getElementById('chatMsgs').innerHTML=h||'<p class="small">No messages yet. Say Hi!</p>';}
function setReply(id,text){REPLY_TO=id; REPLY_TEXT=text; document.getElementById('replyBox').classList.remove('hidden'); document.getElementById('replyText').innerText=text.slice(0,60);}
function cancelReply(){REPLY_TO=''; REPLY_TEXT=''; document.getElementById('replyBox').classList.add('hidden');}
function pickEmoji(e){document.getElementById('chatInput').value+=e; document.getElementById('emojiBox').classList.add('hidden');}
async function sendChat(){let t=document.getElementById('chatInput').value.trim(); if(!t){return;} if(CUR==='BOT'){let d=await api('/api/bot',{method:'POST',body:{text:t,my_uid:ME.uid}}); document.getElementById('chatMsgs').innerHTML+='<div class="msg mine">'+t+'</div><div class="msg other">'+d.reply+'</div>'; document.getElementById('chatInput').value=''; return;} if(CUR.startsWith('GROUP:')){let gid=CUR.replace('GROUP:',''); await api('/api/group_send',{method:'POST',body:{my_uid:ME.uid,gid:gid,text:t}}); document.getElementById('chatInput').value=''; loadChatMsgs(); return;} let body={my_uid:ME.uid,to_uid:CUR,text:t}; if(REPLY_TO){body.reply_to=REPLY_TO; body.reply_text=REPLY_TEXT;} let d=await api('/api/send',{method:'POST',body:body}); if(!d.ok){alert(d.error);return;} document.getElementById('chatInput').value=''; cancelReply(); loadChatMsgs();}
function backToChats(){document.getElementById('chatPage').classList.add('hidden'); document.getElementById('mainPage').classList.remove('hidden'); CUR=null; loadChats();}
function showTerms(){document.getElementById('modal').classList.remove('hidden'); document.getElementById('modalBody').innerHTML='<h2>Terms & Conditions</h2><p>Welcome to MyQchat by QWNG.</p><h4>1. Eligibility</h4><p>You must be 13+ or use with guardian permission.</p><h4>2. Account</h4><p>You are responsible for your Username and Password. Keep it safe.</p><h4>3. Privacy</h4><p>We collect username, bio, messages, status, songs. We do not sell your data.</p><h4>4. Content</h4><p>You own your content. Do not post illegal or harmful content.</p><h4>5. Safety</h4><p>Block and Report bad users. Admin can give Scam tick or ban.</p><h4>6. Prohibited</h4><p>No scam, harassment, fake, spam, illegal activity.</p><h4>7. Deletion & Appeal</h4><p>You can delete account. Appeal in 15 days via Support.</p><h4>8. Service</h4><p>Service may change or stop. We try to keep it running.</p><h4>9. Liability</h4><p>Use at your own risk. QWNG is not liable for user content.</p><h4>10. Changes</h4><p>Terms may change. Continued use means you accept new Terms.</p><h4>11. Contact</h4><p>qwngofficial@gmail.com</p>';}
function showPrivacy(){document.getElementById('modal').classList.remove('hidden'); document.getElementById('modalBody').innerHTML='<h2>Privacy Policy</h2><p>We collect: Username, Name, Bio, Messages, Status, Songs, Calls, Reports.</p><p>We use it to run MyQchat, show chats, status, songs, admin moderation.</p><p>We do NOT sell your data. We do NOT share password.</p><p>You can delete account in Settings. Contact qwngofficial@gmail.com</p>';}
function showHelp(){document.getElementById('modal').classList.remove('hidden'); document.getElementById('modalBody').innerHTML='<h2>Help</h2><p><b>Chat:</b> Search user by UID, tap, type, Send.</p><p><b>Group:</b> Groups > Create Group.</p><p><b>Status:</b> Status > Write > Choose Song > Post. 24 hours auto delete.</p><p><b>Song:</b> Admin adds song, user chooses from list or custom URL.</p><p><b>Bot:</b> Open QWNG Bot, type help.</p><p><b>Tick:</b> Settings > Request Tick.</p><p><b>Report:</b> Settings > Report User.</p><p><b>Support:</b> qwngofficial@gmail.com</p>';}
async function showStarred(){let d=await api('/api/starred?uid='+ME.uid); let h='<h2>Starred Messages</h2>'; d.starred.forEach(s=>{h+='<div class="card">'+s.text+' - '+s.from_name+'</div>';}); document.getElementById('modal').classList.remove('hidden'); document.getElementById('modalBody').innerHTML=h||'<p>No starred yet.</p>';}
async function showBlocked(){let d=await api('/api/blocked?uid='+ME.uid); let h='<h2>Blocked Users</h2>'; d.blocked.forEach(u=>{h+='<div>'+u.name+' <button onclick="unblockUser(\\''+u.uid+'\\')">Unblock</button></div>';}); document.getElementById('modal').classList.remove('hidden'); document.getElementById('modalBody').innerHTML=h||'<p>No blocked users.</p>';}
async function unblockUser(uid){await api('/api/unblock',{method:'POST',body:{my_uid:ME.uid,blocked_uid:uid}}); showBlocked();}
function showForgot(){let u=prompt('Enter Username'); if(!u) return; let e=prompt('Enter Recovery Email'); let n=prompt('Enter New Password'); api('/api/forgot_password',{method:'POST',body:{username:u,recovery_email:e,new_password:n}}).then(d=>alert(d.ok?'Password Reset Done':d.error));}
function closeModal(){document.getElementById('modal').classList.add('hidden');}
function attachFile(){let t=prompt('Enter image URL or text to send as file'); if(t){document.getElementById('chatInput').value=t; sendChat();}}
function openEmoji(){document.getElementById('emojiBox').classList.toggle('hidden');}
function recordVoice(){alert('Voice: Hold to record - 15 seconds. Auto delete 20 min.');}
async function startCall(type){if(!CUR||CUR==='BOT'){alert('Select a user to call');return;} let d=await api('/api/log_call',{method:'POST',body:{my_uid:ME.uid,to_uid:CUR,call_type:type,duration:'0'}}); alert(type+' call started with '+CURNAME);}
async function doLogout(){if(ME) await api('/api/logout',{method:'POST',body:{uid:ME.uid}}); localStorage.removeItem('myq_uid'); location.reload();}
async function deleteAccount(){if(!confirm('Delete account? You can appeal in 15 days.')) return; let p=prompt('Enter password to confirm'); if(!p) return; let d=await api('/api/delete_account',{method:'POST',body:{my_uid:ME.uid,password:p}}); alert(d.ok?d.msg:d.error);}
window.onload=async ()=>{let uid=localStorage.getItem('myq_uid'); if(uid){let d=await api('/api/me?uid='+uid); if(d.ok){ME=d.user; showMain();}}}
</script></body></html>'''
BOT_AUTOCORRECT = {'hilp':'help','hlp':'help','helo':'hello','hellow':'hello','hii':'hi','hiii':'hi','tik':'tick','tikk':'tick','pasword':'password','passwrod':'password','paswrod':'password','logn':'login','logni':'login','singup':'signup','singnup':'signup','staus':'status','statas':'status','satus':'status','gruop':'group','gorup':'group','grup':'group','mesage':'message','msg':'message','mesg':'message','freind':'friend','frnd':'friend','frind':'friend','onlin':'online','ofline':'offline','ofline':'offline','lastseen':'last seen','lstseen':'last seen','profle':'profile','profil':'profile','seting':'setting','setings':'settings','settting':'setting','notif':'notification','notificaton':'notification','dowload':'download','downlod':'download','instal':'install','instll':'install','uplod':'upload','uplode':'upload','delte':'delete','delet':'delete','forwad':'forward','forwrd':'forward','starred':'star','starr':'star','blck':'block','blok':'block','unblok':'unblock','serch':'search','sarch':'search','repport':'report','repot':'report','scm':'scam','scamm':'scam','admim':'admin','admn':'admin','owener':'owner','onwer':'owner','acount':'account','accout':'account','acounts':'account','chng':'change','chnage':'change','chnge':'change','emial':'email','emal':'email','recovry':'recovery','recovary':'recovery','forgt':'forgot','forgoten':'forgot','verison':'version','verson':'version','langage':'language','langauge':'language','lnguage':'language','jock':'joke','jok':'joke','shayri':'shayari','shayari':'shayari','motivaton':'motivation','motivatn':'motivation','stdy':'study','study':'study','gmae':'game','gme':'game','quizz':'quiz','quz':'quiz','weahter':'weather','wether':'weather','sonng':'song','sng':'song','musik':'music','music':'music','brthday':'birthday','bday':'birthday','lov':'love','lv':'love','pyar':'love','pyr':'love','dosti':'friend','yari':'friend','khel':'game','padhai':'study','mausam':'weather','gaana':'song','gana':'song','kahaani':'story','kahani':'story','photo':'photo','photu':'photo','voice':'voice','voise':'voice','call':'call','cal':'call','video':'video','vidio':'video','time':'time','tm':'time','date':'date','dt':'date','save':'save','sav':'save','contact':'contact','contect':'contact','brodcast':'broadcast','brodcast':'broadcast','anounce':'announcement','warn':'warning','help':'help','suport':'support','support':'support','qwng':'qwng','myqchat':'myqchat','myqcht':'myqchat'}

BOT_ANSWERS = {}
BOT_ANSWERS['help'] = 'Hello! I am QWNG Bot. I help you use MyQchat.\n\nType a number or word:\n1. Tick\n2. Password\n3. Chat\n4. Group\n5. Status\n6. Song\n7. Report\n8. Block\n9. Search\n10. Call\n\nOr type: love, shayari, motivation, study, game, quiz, joke, birthday, weather, download, install, online, last seen, photo, voice, delete, star, reply, forward, unblock, bio, profile, notification, logout, qwng, version, scam, save contact, language, time, date.\n\nType help anytime.'
BOT_ANSWERS['hi'] = 'Hi! How are you? Type help to see what I can do. I can help with Tick, Password, Chat, Group, Status, Song and more.'
BOT_ANSWERS['hello'] = 'Hello! Welcome to MyQchat. Type help to see menu. What do you want to do today?'
BOT_ANSWERS['hey'] = 'Hey! Good to see you. Type help for menu.'
BOT_ANSWERS['how are you'] = 'I am good, always online for you. How are you? Type help to see what I can do.'
BOT_ANSWERS['kaise ho'] = 'I am good! Type help to see menu in English.'
BOT_ANSWERS['who are you'] = 'I am QWNG Bot. I am the official helper bot of MyQchat. I am always online. I help with Tick, Password, Chat, Group, Status, Song, Report and more. Type help.'
BOT_ANSWERS['what is your name'] = 'My name is QWNG Bot. I work for MyQchat by QWNG.'
BOT_ANSWERS['what can you do'] = 'I can help with: Tick, Password, Chat, Group, Status, Song, Report, Block, Search, Call, Photo, Voice, Delete, Star, Reply, Forward, Unblock, Bio, Profile, Notification, Logout, Version, Scam, Save Contact, Language, Time, Date, Love, Shayari, Motivation, Study, Game, Quiz, Joke, Birthday, Weather. Type help.'
BOT_ANSWERS['1'] = 'Tick Help:\nGo to Settings > Request Tick.\nYou can request Blue, Orange, Green Tick.\nL Tick is only for Owner. It cannot be requested.\nScam Tick is only after report. It cannot be requested.\nWrite a good reason. Admin will approve or reject.'
BOT_ANSWERS['tick'] = 'Tick Help:\nGo to Settings > Request Tick.\nYou can request Blue, Orange, Green Tick.\nL Tick is only for Owner. It cannot be requested.\nScam Tick is only after report. It cannot be requested.\nWrite a good reason. Admin will approve or reject.'
BOT_ANSWERS['blue tick'] = 'Blue Tick is for trusted users. Go to Settings > Request Tick > Select Blue > Write reason > Send. Admin will check and approve.'
BOT_ANSWERS['orange tick'] = 'Orange Tick is for active users. Go to Settings > Request Tick > Select Orange > Write reason > Send.'
BOT_ANSWERS['green tick'] = 'Green Tick is for good users. Go to Settings > Request Tick > Select Green > Write reason > Send.'
BOT_ANSWERS['l tick'] = 'L Tick is only for Owner LoyalWQ. No one can request L Tick. It is special for Owner only.'
BOT_ANSWERS['scam tick'] = 'Scam Tick is given by Admin after a report is proved. You cannot request Scam Tick. If someone scams you, go to Settings > Report User. Write full detail.'
BOT_ANSWERS['2'] = 'Password Help:\nTo change password: Go to Settings > Change Password.\nTo reset if you forgot: On login page tap Forgot Password. Enter Username + Recovery Email + New Password.\nSet Recovery Email first in Settings, otherwise forgot password will not work.\nKeep password safe. Do not share with anyone.'
BOT_ANSWERS['password'] = 'Password Help:\nTo change password: Go to Settings > Change Password.\nTo reset if you forgot: On login page tap Forgot Password. Enter Username + Recovery Email + New Password.\nSet Recovery Email first in Settings, otherwise forgot password will not work.\nKeep password safe. Do not share with anyone.'
BOT_ANSWERS['forgot password'] = 'Forgot Password:\nOn login page tap Forgot Password.\nEnter Username, Recovery Email, New Password.\nRecovery Email must be same as saved in Settings.\nIf you did not save Recovery Email, contact Admin at qwngofficial@gmail.com'
BOT_ANSWERS['change password'] = 'Change Password:\nGo to Settings > Change Password.\nEnter old password, then new password, then save.\nUse strong password with letters and numbers.'
BOT_ANSWERS['3'] = 'Chat Help:\nTo chat: Search user by Username or 8-digit UID in Chats search box.\nTap user name to open chat.\nType message and tap Send.\nYou can Reply, Star, Forward, Delete message.\nLong press or tap message to see options.'
BOT_ANSWERS['chat'] = 'Chat Help:\nTo chat: Search user by Username or 8-digit UID in Chats search box.\nTap user name to open chat.\nType message and tap Send.\nYou can Reply, Star, Forward, Delete message.'
BOT_ANSWERS['new chat'] = 'New Chat:\nGo to Chats tab.\nSearch by Username or UID.\nTap user.\nStart chatting.'
BOT_ANSWERS['delete chat'] = 'Delete Chat:\nOpen chat.\nTap menu > Delete Chat.\nOr delete single message: tap message > Delete.\nDeleted message shows: This message was deleted.'
BOT_ANSWERS['4'] = 'Group Help:\nGo to Groups tab.\nEnter Group Name and Description.\nTap Create Group.\nTo add member: Open group > Add Member > Enter UID.\nAdmin can remove member. Member can leave group.'
BOT_ANSWERS['group'] = 'Group Help:\nGo to Groups tab.\nEnter Group Name and Description.\nTap Create Group.\nTo add member: Open group > Add Member > Enter UID.\nAdmin can remove member. Member can leave group.'
BOT_ANSWERS['create group'] = 'Create Group:\nGroups tab > Group Name > Description > Create Group.\nThen add members by UID.'
BOT_ANSWERS['add member'] = 'Add Member:\nOpen Group > Add Member > Enter UID of user > Add.\nOnly group admin can add.'
BOT_ANSWERS['leave group'] = 'Leave Group:\nOpen Group > Leave Group.\nYou will not get new group messages after leaving.'
BOT_ANSWERS['5'] = 'Status Help:\nGo to Status tab.\nWrite status text.\nChoose Song from Library or paste Custom Song URL.\nTap Post Status.\nStatus auto deletes in 24 hours.\nYou can see who viewed your status.'
BOT_ANSWERS['status'] = 'Status Help:\nGo to Status tab.\nWrite status text.\nChoose Song from Library or paste Custom Song URL.\nTap Post Status.\nStatus auto deletes in 24 hours.'
BOT_ANSWERS['6'] = 'Song Help:\nGo to Status tab > Music Library.\nAdmin adds permanent songs.\nYou can choose any song from list when posting Status.\nOr paste your own Custom Song URL + Title.\nSong plays when someone opens your status.'
BOT_ANSWERS['song'] = 'Song Help:\nGo to Status tab > Music Library.\nAdmin adds permanent songs.\nYou can choose any song from list when posting Status.\nOr paste your own Custom Song URL + Title.'
BOT_ANSWERS['7'] = 'Report Help:\nGo to Settings > Report User.\nEnter Reported UID (8-digit).\nSelect Reason: Scam, Harassment, Fake, Spam, Abuse, Other.\nWrite Detail in 400 letters.\nTap Report.\nAdmin will check. If proved, user gets Scam Tick or Ban.'
BOT_ANSWERS['report'] = 'Report Help:\nGo to Settings > Report User.\nEnter Reported UID (8-digit).\nSelect Reason: Scam, Harassment, Fake, Spam, Abuse, Other.\nWrite Detail in 400 letters.\nTap Report.\nAdmin will check.'
BOT_ANSWERS['8'] = 'Block Help:\nOpen chat of user > Block.\nBlocked user cannot message you.\nTo unblock: Settings > Blocked Users > Unblock.\nYou can also Report after Block.'
BOT_ANSWERS['block'] = 'Block Help:\nOpen chat of user > Block.\nBlocked user cannot message you.\nTo unblock: Settings > Blocked Users > Unblock.'
BOT_ANSWERS['9'] = 'Search Help:\nGo to Chats tab > Search box.\nSearch by Username or 8-digit UID.\nExample: Search LoyalWQ or UID.\nTap user to open chat.'
BOT_ANSWERS['search'] = 'Search Help:\nGo to Chats tab > Search box.\nSearch by Username or 8-digit UID.\nTap user to open chat.'
BOT_ANSWERS['10'] = 'Call Help:\nOpen chat > Tap Call for Voice Call.\nTap Video for Video Call.\nCall history is in Calls tab.\nIf call not connecting, check internet and try again.'
BOT_ANSWERS['call'] = 'Call Help:\nOpen chat > Tap Call for Voice Call.\nTap Video for Video Call.\nCall history is in Calls tab.'

def clean_bot_text(t):
    if not t:
        return ''
    t = str(t).lower().strip()
    t = t.replace('?','').replace('!','').replace('.','').replace(',','')
    while '  ' in t:
        t = t.replace('  ',' ')
    return t.strip()

def fix_bot_words(t):
    words = t.split(' ')
    out = []
    for w in words:
        if w in BOT_AUTOCORRECT:
            out.append(BOT_AUTOCORRECT[w])
        else:
            out.append(w)
    return ' '.join(out)

def get_bot_reply(raw_text, user_name='Friend'):
    t = clean_bot_text(raw_text)
    if not t:
        return 'Type help to see menu.'
    t = fix_bot_words(t)
    if t in BOT_ANSWERS:
        return BOT_ANSWERS[t]
    if t.startswith('hi') or t.startswith('hello') or t.startswith('hey'):
        return BOT_ANSWERS['hi']
    if 'help' in t:
        return BOT_ANSWERS['help']
    if 'tick' in t:
        if 'blue' in t:
            return BOT_ANSWERS['blue tick']
        if 'orange' in t:
            return BOT_ANSWERS['orange tick']
        if 'green' in t:
            return BOT_ANSWERS['green tick']
        if 'scam' in t:
            return BOT_ANSWERS['scam tick']
        if t.strip() == 'l' or ' l ' in ' '+t+' ':
            return BOT_ANSWERS['l tick']
        return BOT_ANSWERS['tick']
    if 'password' in t or 'forgot' in t:
        if 'forgot' in t:
            return BOT_ANSWERS['forgot password']
        if 'change' in t:
            return BOT_ANSWERS['change password']
        return BOT_ANSWERS['password']
    if 'chat' in t or 'message' in t:
        if 'delete' in t:
            return BOT_ANSWERS['delete chat']
        if 'new' in t:
            return BOT_ANSWERS['new chat']
        return BOT_ANSWERS['chat']
    if 'group' in t:
        if 'create' in t:
            return BOT_ANSWERS['create group']
        if 'add' in t:
            return BOT_ANSWERS['add member']
        if 'leave' in t:
            return BOT_ANSWERS['leave group']
        return BOT_ANSWERS['group']
    if 'status' in t:
        return BOT_ANSWERS['status']
    if 'song' in t or 'music' in t:
        return BOT_ANSWERS['song']
    if 'report' in t:
        return BOT_ANSWERS['report']
    if 'block' in t:
        return BOT_ANSWERS['block']
    if 'search' in t:
        return BOT_ANSWERS['search']
    if 'call' in t:
        return BOT_ANSWERS['call']
    if 'who are you' in t or 'your name' in t:
        return BOT_ANSWERS['who are you']
    if 'how are you' in t or 'kaise' in t:
        return BOT_ANSWERS['how are you']
    if 'what can you do' in t or 'what do you do' in t:
        return BOT_ANSWERS['what can you do']
    return "I didn't understand, Type help to see menu. Try: tick, password, chat, group, status, song, report, block, search, call, love, shayari, motivation, study, game, quiz, joke, birthday, weather."
  BOT_ANSWERS['love'] = 'Love Tip:\nTrue love is respect + care + trust.\nTalk honestly. Listen patiently. Never force.\nIf someone truly loves you, they will respect your time and your family.\nStay loyal. Stay kind. Type help for menu.'
BOT_ANSWERS['i love you'] = 'That is sweet! Love is beautiful when it is honest and respectful.\nTake care of the person you love. Talk, listen, and grow together.\nType love for love tip, or shayari for a line.'
BOT_ANSWERS['breakup'] = 'Breakup is painful, but it is not the end.\nTake time. Talk to a friend. Focus on study, health, and goals.\nDo not chase someone who does not respect you.\nBetter days will come. You are strong. Type motivation for strength.'
BOT_ANSWERS['crush'] = 'Crush Tip:\nIt is normal to like someone.\nBe confident, be kind, be respectful.\nTalk normally. Do not stalk or force.\nIf they say no, respect it and move forward with dignity.'
BOT_ANSWERS['shayari'] = 'Shayari for you:\nYour smile is my morning light,\nYour care makes my day bright.\nIn this busy world of noise,\nYour friendship is my sweetest choice.\n\nType shayari 2 for one more.'
BOT_ANSWERS['shayari 2'] = 'Shayari 2:\nDo not fear the dark night,\nStars still shine so bright.\nKeep walking with hope in heart,\nA new morning is about to start.\n\nType motivation for more strength.'
BOT_ANSWERS['shayari 3'] = 'Shayari 3:\nTrue friends are rare and true,\nThey stand beside me and you.\nIn joy and in pain,\nTheir love will always remain.'
BOT_ANSWERS['motivation'] = 'Motivation:\nYou are stronger than you think.\nOne small step today is better than zero steps.\nDo not compare your Day 1 with someone Day 100.\nStart now. Stay consistent. Your future you will thank you.'
BOT_ANSWERS['motivational'] = 'Motivation:\nDiscipline beats motivation.\nWake up. Drink water. Plan 3 tasks. Finish them.\nSmall wins daily = big change in 90 days.\nYou can do it.'
BOT_ANSWERS['sad'] = 'I understand. Feeling sad is okay.\nTake a deep breath. Drink water. Talk to someone you trust.\nGo for a walk. Listen to a good song.\nIf sadness stays long, talk to family or a trusted elder.\nYou are not alone. Type motivation.'
BOT_ANSWERS['depressed'] = 'Please take care of yourself.\nTalk to a trusted friend, family member, or elder today.\nRest, eat well, go outside for sunlight.\nIf you feel very low, please reach out to someone near you right now.\nYou matter. Type motivation for strength.'
BOT_ANSWERS['study'] = 'Study Tip:\n1. Make a simple timetable.\n2. Study 25 min, break 5 min.\n3. Write notes by hand.\n4. Revise same day.\n5. No phone during study.\n6. Sleep 7-8 hours.\nConsistency wins. Type study 2 for exam tip.'
BOT_ANSWERS['study 2'] = 'Exam Tip:\nStart with easy chapters to build confidence.\nSolve previous year papers.\nRevise mistakes, not only new topics.\nSleep well before exam.\nReach early. Read paper fully first.'
BOT_ANSWERS['exam'] = 'Exam Tip:\nMake a 7-day plan.\nDay 1-4: Learn. Day 5-6: Revise. Day 7: Mock test + rest.\nWrite answers in points. Keep handwriting neat.\nBelieve in your preparation.'
BOT_ANSWERS['game'] = 'Game Tip:\nPlay for fun, not for anger.\nTake break every 45 min.\nDrink water. Rest eyes.\nNever share password or OTP in game.\nNever buy from strangers. Use official store only.'
BOT_ANSWERS['【entity-free fire¦canonical_name=Free Fire】'] = '【entity-Free Fire¦canonical_name=Free Fire】 Tip:\nLand safe, loot fast, stay in zone.\nUse cover, do not rush alone.\nPlay with team, use voice chat wisely.\nTake breaks. Study first, game second.'
BOT_ANSWERS['【entity-pubg¦canonical_name=PUBG】'] = '【entity-PUBG¦canonical_name=PUBG】 / 【entity-BGMI¦canonical_name=BGMI】 Tip:\nLand safe, loot fast, stay in zone.\nUse cover. Do not rush alone.\nPlay with squad. Communicate.\nTake breaks. Study first, game second.'
BOT_ANSWERS['quiz'] = 'Quiz Time:\nQ: What is the capital of India?\nA) Mumbai  B) New Delhi  C) Kolkata  D) Chennai\n\nType quiz answer to see answer.\nType quiz 2 for next quiz.'
BOT_ANSWERS['quiz 2'] = 'Quiz 2:\nQ: Which planet is called Red Planet?\nA) Venus  B) Mars  C) Jupiter  D) Saturn\n\nType quiz 2 answer to see answer.'
BOT_ANSWERS['quiz answer'] = 'Quiz Answer: B) New Delhi is the capital of India.\nWell done! Type quiz 2 for next quiz.'
BOT_ANSWERS['quiz 2 answer'] = 'Quiz 2 Answer: B) Mars is called Red Planet.\nGreat! Type joke for fun.'
BOT_ANSWERS['joke'] = 'Joke:\nWhy did the phone go to school?\nBecause it wanted to be smarter!\n\nType joke 2 for one more.'
BOT_ANSWERS['joke 2'] = 'Joke 2:\nWhy did the computer go to the doctor?\nBecause it had a virus!\n\nType joke 3 for one more.'
BOT_ANSWERS['joke 3'] = 'Joke 3:\nWhat do you call a fish without eyes?\nA fsh!\n\nSmile and share happiness. Type help for menu.'
BOT_ANSWERS['birthday'] = 'Happy Birthday!\nMay your year be full of health, happiness, and success.\nStay kind, stay strong, keep smiling.\nCelebrate with love and good food!\nType birthday song for a birthday line.'
BOT_ANSWERS['birthday song'] = 'Birthday Line:\nHappy Birthday to you,\nMay all your dreams come true.\nWith love, joy, and light,\nYour future is shining bright!'
BOT_ANSWERS['happy birthday'] = 'Happy Birthday!\nMay your year be full of health, happiness, and success.\nStay kind, stay strong, keep smiling.\nType birthday song for a birthday line.'
BOT_ANSWERS['good morning'] = 'Good Morning! Have a beautiful day.\nDrink water. Plan 3 tasks. Smile and start.\nType motivation for energy.'
BOT_ANSWERS['good night'] = 'Good Night! Sleep well.\nKeep phone away. Think of 3 good things today.\nTomorrow is a new chance. Sweet dreams.'
BOT_ANSWERS['thank you'] = 'You are most welcome! Happy to help.\nType help anytime you need me.'
BOT_ANSWERS['thanks'] = 'You are most welcome! Happy to help.\nType help anytime you need me.'
BOT_ANSWERS['bye'] = 'Bye! Take care. Come back anytime.\nType help when you return.'
BOT_ANSWERS['ok'] = 'Great! Type help to see what else I can do.'
BOT_ANSWERS['nice'] = 'Thank you! You are nice too.\nType help for more.'
BOT_ANSWERS['download'] = 'Download Help:\nMyQchat is a web app. No need to download from store.\nOpen myqchat-1.onrender.com in Chrome.\nTap Menu > Add to Home Screen to install as app.\nIt will work like an app on your phone.'
BOT_ANSWERS['install'] = 'Install Help:\nOpen MyQchat link in Chrome.\nTap 3 dots Menu > Add to Home Screen > Add.\nNow MyQchat icon will show on home screen.\nTap it to open fast anytime.'
BOT_ANSWERS['app'] = 'App Help:\nMyQchat works in browser.\nYou can Add to Home Screen for app-like feel.\nNo Play Store download needed.\nLink: myqchat-1.onrender.com'
BOT_ANSWERS['online'] = 'Online Help:\nGreen dot means user is online now.\nIf no dot, user is offline.\nYour online status updates when you open app.\nTo hide Last Seen, go to Settings > Last Seen Privacy.'
BOT_ANSWERS['last seen'] = 'Last Seen Help:\nLast Seen shows when user was last active.\nGo to Settings > Last Seen Privacy.\nChoose Everyone, My Contacts, or Nobody.\nIf you choose Nobody, you also cannot see others Last Seen.'
BOT_ANSWERS['lastseen'] = 'Last Seen Help:\nLast Seen shows when user was last active.\nGo to Settings > Last Seen Privacy.\nChoose Everyone, My Contacts, or Nobody.'
BOT_ANSWERS['send photo'] = 'Send Photo Help:\nOpen chat > Tap Attach > Paste image URL or choose photo.\nTap Send.\nPhoto will show in chat.\nKeep photo size small for fast sending.'
BOT_ANSWERS['photo'] = 'Photo Help:\nOpen chat > Tap Attach > Paste image URL or choose photo.\nTap Send.\nPhoto will show in chat.'
BOT_ANSWERS['send video'] = 'Send Video Help:\nOpen chat > Tap Attach > Paste video URL.\nTap Send.\nKeep video short for fast sending.'
BOT_ANSWERS['voice'] = 'Voice Help:\nOpen chat > Tap Voice > Hold to record.\nVoice message is 15 seconds max.\nTap Send to send.\nVoice auto deletes in 20 minutes for privacy.'
BOT_ANSWERS['voice message'] = 'Voice Message Help:\nOpen chat > Tap Voice > Hold to record.\nVoice is 15 seconds max.\nTap Send.\nVoice auto deletes in 20 minutes.'
BOT_ANSWERS['voice call'] = 'Voice Call Help:\nOpen chat > Tap Call.\nWait for other user to accept.\nCall history shows in Calls tab.'
BOT_ANSWERS['video call'] = 'Video Call Help:\nOpen chat > Tap Video.\nAllow camera and mic permission.\nCall history shows in Calls tab.'
BOT_ANSWERS['delete message'] = 'Delete Message Help:\nTap message > Delete.\nIt will show: This message was deleted.\nYou can delete only your own message.\nFor full chat: Open chat > Delete Chat.'
BOT_ANSWERS['delete'] = 'Delete Help:\nTo delete message: Tap message > Delete.\nTo delete chat: Open chat > Delete Chat.\nTo delete account: Settings > Delete Account. You can appeal in 15 days.'
BOT_ANSWERS['star'] = 'Star Help:\nTap message > Star.\nStarred message saves in Starred Messages.\nGo to Settings > Starred Messages to see all starred.\nTap again to unstar.'
BOT_ANSWERS['starred'] = 'Starred Help:\nGo to Settings > Starred Messages.\nYou will see all messages you starred.\nTap message to open chat.'
BOT_ANSWERS['reply'] = 'Reply Help:\nTap message > Reply.\nType your reply and tap Send.\nYour reply will show above your message with original text.'
BOT_ANSWERS['forward'] = 'Forward Help:\nTap message > Forward.\nChoose user or group.\nTap Send.\nForwarded message shows (Forwarded) tag.'
BOT_ANSWERS['unblock'] = 'Unblock Help:\nGo to Settings > Blocked Users.\nTap Unblock next to user name.\nNow that user can message you again.'
BOT_ANSWERS['blocked'] = 'Blocked Help:\nGo to Settings > Blocked Users to see blocked list.\nTap Unblock to unblock.\nBlocked user cannot see your status or message you.'
BOT_ANSWERS['bio'] = 'Bio Help:\nGo to Settings > Bio.\nWrite about you in short line.\nExample: Simple boy. Love music. Study first.\nTap Save Settings.'
BOT_ANSWERS['profile'] = 'Profile Help:\nGo to Settings.\nYou can change Name, Bio, Recovery Email, Wallpaper, Font Size, Chat Color, Dark Mode.\nTap Save Settings after change.\nYour UID is fixed. It cannot change.'
BOT_ANSWERS['change name'] = 'Change Name:\nGo to Settings > Name.\nEnter new name > Save Settings.\nYour username stays same. Only display name changes.'
BOT_ANSWERS['notification'] = 'Notification Help:\nGo to Settings > Notifications.\nTurn ON to get new message alerts.\nTurn OFF if you want quiet.\nAlso check phone Settings > MyQchat > Allow Notifications.'
BOT_ANSWERS['logout'] = 'Logout Help:\nGo to Settings > Logout.\nYou will go to login page.\nYour chats and data stay safe.\nLogin again with Username and Password.'
BOT_ANSWERS['qwng'] = 'QWNG:\nQWNG is the team behind MyQchat.\nWe make simple, fast and safe apps.\nSupport: qwngofficial@gmail.com\nThank you for using MyQchat.'
BOT_ANSWERS['myqchat'] = 'MyQchat:\nMyQchat is a simple chat app by QWNG.\nChat 1-to-1, Group, Status, Song, Calls.\nNo Post, No Like, No Comment. Only Chat.\nType help for menu.'
BOT_ANSWERS['version'] = 'Version Help:\nYou are using latest MyQchat web version.\nIf something looks old, refresh page or clear cache.\nNew features come with updates from Admin.'
BOT_ANSWERS['scam'] = 'Scam Safety:\nNever share OTP, Password, or Bank details.\nAdmin will never ask for password.\nIf someone asks money, Block + Report.\nGo to Settings > Report User > Scam.\nStay safe.'
BOT_ANSWERS['fraud'] = 'Fraud Safety:\nNever share OTP, Password, or Bank details.\nAdmin will never ask for password.\nIf someone asks money, Block + Report.\nGo to Settings > Report User.'
BOT_ANSWERS['save contact'] = 'Save Contact Help:\nCopy UID of user from chat.\nSave in your phone contacts as Name + UID.\nNext time search by UID to chat fast.\nMyQchat also saves chat in Chat List.'
BOT_ANSWERS['save'] = 'Save Help:\nTo save chat: Star message.\nTo save contact: Copy UID and save in phone.\nTo save settings: Settings > Save Settings.'
BOT_ANSWERS['language'] = 'Language Help:\nMyQchat screen is in English only, like 【entity-WhatsApp¦canonical_name=WhatsApp】.\nBot replies in English only.\nThis keeps app clean and simple for everyone.'
BOT_ANSWERS['hindi'] = 'Language Help:\nMyQchat screen is in English only.\nBot replies in English only.\nType help for English menu.'
BOT_ANSWERS['time'] = 'Time Help:\nMyQchat shows message time in chat.\nStatus shows time left.\nCall shows duration in Calls tab.\nCheck phone time for current time.'
BOT_ANSWERS['date'] = 'Date Help:\nMessages show date and time.\nStatus auto deletes after 24 hours from posting date.\nAccount delete appeal is 15 days from delete date.'
BOT_ANSWERS['weather'] = 'Weather Help:\nI cannot see live weather.\nCheck your phone weather app for today.\nIf raining, stay safe. If hot, drink water.\nType motivation for a fresh day.'
BOT_ANSWERS['owner'] = 'Owner:\nOwner of MyQchat is LoyalWQ.\nOwner has special L Tick.\nOwner manages Admin Panel, Songs, Broadcasts, Ticks, Reports.\nContact via Support: qwngofficial@gmail.com'
BOT_ANSWERS['admin'] = 'Admin Help:\nAdmin Panel is only for Owner.\nAdmin manages Songs, Broadcasts, Ticks, Reports, Users.\nNormal users cannot see Admin Panel.\nIf you need help, contact qwngofficial@gmail.com'
BOT_ANSWERS['support'] = 'Support:\nEmail: qwngofficial@gmail.com\nWrite your Username + UID + Problem in detail.\nAdmin will reply soon.\nType help for menu.'
BOT_ANSWERS['help number'] = 'Help Menu Numbers:\n1 Tick  2 Password  3 Chat  4 Group  5 Status\n6 Song  7 Report  8 Block  9 Search  10 Call\nType number or word. Example: Type 1 or tick.'
BOT_ANSWERS['help me'] = 'I am here to help.\nType help to see full menu.\nOr type your problem word: tick, password, chat, group, status, song, report, block, search, call.'
BOT_ANSWERS['i need help'] = 'I am here to help.\nType help to see full menu.\nOr type: tick, password, chat, group, status, song, report, block, search, call.'
BOT_ANSWERS['what is myqchat'] = 'MyQchat is a simple chat app by QWNG.\nChat 1-to-1, Group, Status, Song, Calls.\nNo Post, No Like, No Comment. Only Chat.\nType help for menu.'
BOT_ANSWERS['contact admin'] = 'Contact Admin:\nEmail: qwngofficial@gmail.com\nWrite Username + UID + Problem in detail.\nAdmin will reply soon.'
BOT_ANSWERS['contact'] = 'Contact:\nSupport Email: qwngofficial@gmail.com\nWrite Username + UID + Problem.\nAdmin will reply soon.'
BOT_ANSWERS['email'] = 'Email Help:\nSupport Email: qwngofficial@gmail.com\nRecovery Email is in Settings.\nSet Recovery Email for Forgot Password.\nDo not share password by email.'
BOT_ANSWERS['safe'] = 'Safety:\nNever share OTP, Password, Bank details.\nAdmin never asks password.\nIf someone asks money, Block + Report.\nStay safe. Type scam for more.'
BOT_ANSWERS['internet'] = 'Internet Safety:\nDo not share password or OTP.\nDo not click unknown links.\nDo not talk to strangers about money.\nIf someone troubles you, Block + Report.'
BOT_ANSWERS['i am bored'] = 'Try this in MyQchat:\n1. Check Status of friends.\n2. Listen to a Song from Library.\n3. Start a new Chat.\n4. Type help to learn a new feature.'
BOT_ANSWERS['qwng'] = 'QWNG is a Software Developer Team.\nQWNG builds MyQchat and other software.\nSupport: qwngofficial@gmail.com'
BOT_ANSWERS['what is qwng'] = 'QWNG is a Software Developer Team.\nQWNG builds MyQchat and other software.\nSupport: qwngofficial@gmail.com'
BOT_ANSWERS['myqchat'] = 'MyQchat is a simple chat app built by QWNG - Software Developer Team.\nChat 1-to-1, Group, Status, Song, Calls.\nNo Post, No Like, No Comment. Only Chat.\nType help for menu.'
BOT_ANSWERS['what is myqchat'] = 'MyQchat is a simple chat app built by QWNG - Software Developer Team.\nChat 1-to-1, Group, Status, Song, Calls.\nNo Post, No Like, No Comment. Only Chat.\nType help for menu.'
BOT_ANSWERS['owner'] = 'Owner of MyQchat is LoyalWQ.\nOwner  has spe cial L Tick.\nMyQchat  is built by QWNG - Software Developer Team.\nContact via Support: qwngofficial@gmail.com'
@app.route('/api/bot', methods=['POST'])
def bot_api():
    d = request.get_json(silent=True) or {}
    me = get_me()
    name = me.name if me else 'Friend'
    text = clean(d.get('text'), 500)
    if not text:
        return jsonify({'ok': True, 'reply': 'Type help to see menu.'})
    reply = get_bot_reply(text, name)
    return jsonify({'ok': True, 'reply': reply})

@app.route('/api/bot_help', methods=['GET'])
def bot_help():
    return jsonify({'ok': True, 'help': BOT_ANSWERS['help'], 'quick': ['Help','Tick','Password','Chat','Group','Status','Song','Report','Block','Search','Call','Love','Shayari','Motivation','Study','Game','Quiz','Joke','Birthday','Weather','Download','Install','Online','Photo','Voice','Delete','Star','Reply','Forward','Unblock','Bio','Profile','Notification','Logout','QWNG','Version','Scam','Save Contact','Language','Time','Date','Advice','Safety','Contact']})

@app.route('/api/bot_quick', methods=['GET'])
def bot_quick():
    q = clean(request.args.get('q'), 50).lower()
    if not q:
        return jsonify({'ok': True, 'reply': BOT_ANSWERS['help']})
    reply = get_bot_reply(q, 'Friend')
    return jsonify({'ok': True, 'reply': reply})

@app.route('/api/help_topics', methods=['GET'])
def help_topics():
    topics = [
        {'title': 'Tick', 'text': 'Settings > Request Tick. Blue, Orange, Green only. L only Owner. Scam only after report.'},
        {'title': 'Password', 'text': 'Settings > Change Password. Forgot? Login > Forgot Password with Recovery Email.'},
        {'title': 'Chat', 'text': 'Search by Username or 8-digit UID. Tap user. Type and Send. Reply, Star, Forward, Delete available.'},
        {'title': 'Group', 'text': 'Groups > Create Group. Add member by UID. Admin can remove. Member can leave.'},
        {'title': 'Status', 'text': 'Status > Write + Choose Song > Post. Auto deletes in 24 hours.'},
        {'title': 'Song', 'text': 'Status > Music Library. Admin adds songs. You can choose or paste custom URL.'},
        {'title': 'Report', 'text': 'Settings > Report User. Enter UID + Reason + Detail. Admin checks.'},
        {'title': 'Block', 'text': 'Open chat > Block. Settings > Blocked Users > Unblock to unblock.'},
        {'title': 'Search', 'text': 'Chats > Search box. Search by Username or UID.'},
        {'title': 'Call', 'text': 'Open chat > Call for Voice, Video for Video. History in Calls tab.'},
        {'title': 'Photo', 'text': 'Open chat > Attach > Paste image URL > Send.'},
        {'title': 'Voice', 'text': 'Open chat > Voice > Hold to record. 15 sec max. Auto deletes in 20 min.'},
        {'title': 'Delete', 'text': 'Tap message > Delete. Shows This message was deleted.'},
        {'title': 'Star', 'text': 'Tap message > Star. See in Settings > Starred Messages.'},
        {'title': 'Reply', 'text': 'Tap message > Reply. Type reply and Send.'},
        {'title': 'Forward', 'text': 'Tap message > Forward. Choose user or group.'},
        {'title': 'Unblock', 'text': 'Settings > Blocked Users > Unblock.'},
        {'title': 'Bio', 'text': 'Settings > Bio. Write short line. Save Settings.'},
        {'title': 'Profile', 'text': 'Settings > Name, Bio, Recovery Email, Wallpaper, Font, Chat Color, Dark Mode.'},
        {'title': 'Notification', 'text': 'Settings > Notifications ON/OFF. Also allow in phone settings.'},
        {'title': 'Logout', 'text': 'Settings > Logout. Chats stay safe. Login again.'},
        {'title': 'QWNG', 'text': 'QWNG is a Software Developer Team. QWNG builds MyQchat and other software.'},
        {'title': 'Version', 'text': 'You are on latest web version. Refresh if old looks.'},
        {'title': 'Scam', 'text': 'Never share OTP, Password, Bank details. Admin never asks password. Block + Report.'},
        {'title': 'Save Contact', 'text': 'Copy UID and save in phone contacts as Name + UID.'},
        {'title': 'Language', 'text': 'MyQchat screen is English only, like WhatsApp. Bot replies in English only.'},
        {'title': 'Safety', 'text': 'Never share OTP or Password. Block + Report bad users.'},
        {'title': 'Contact', 'text': 'Support: qwngofficial@gmail.com. Write Username + UID + Problem.'},
    ]
    return jsonify({'ok': True, 'topics': topics})

@app.route('/api/backup', methods=['GET'])
def backup():
    me = get_me()
    if not me or not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only admin'})
    data = {'users': User.query.count(), 'messages': Message.query.count(), 'groups': Group.query.count(), 'songs': Song.query.count(), 'status': StatusItem.query.count(), 'reports': Report.query.count(), 'ticks': TickReq.query.count(), 'calls': CallLog.query.count(), 'backup_time': datetime.utcnow().strftime('%d-%m-%Y %H:%M')}
    return jsonify({'ok': True, 'backup': data})

@app.route('/api/export_my_data', methods=['GET'])
def export_my_data():
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    msgs = Message.query.filter((Message.sender_uid == me.uid) | (Message.to_uid == me.uid)).order_by(Message.id.desc()).limit(500).all()
    return jsonify({'ok': True, 'user': pub_user(me), 'messages': [pub_message(m) for m in msgs], 'export_time': datetime.utcnow().strftime('%d-%m-%Y %H:%M')})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'app': 'MyQchat', 'team': 'QWNG - Software Developer Team', 'status': 'running', 'time': datetime.utcnow().strftime('%d-%m-%Y %H:%M')})

@app.route('/api/app_info', methods=['GET'])
def app_info():
    return jsonify({'ok': True, 'app': 'MyQchat', 'team': 'QWNG - Software Developer Team', 'owner': 'LoyalWQ', 'version': '1.0', 'features': ['Chat', 'Group', 'Status', 'Song', 'Calls', 'Tick', 'Report', 'Broadcast', 'Bot Help'], 'support': 'qwngofficial@gmail.com'})

@app.route('/')
def home():
    return FRONTEND_HEAD + FRONTEND_JS

@app.route('/terms')
def terms_page():
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Terms - MyQchat</title></head><body style="font-family:Arial;padding:20px;max-width:700px;margin:auto"><h2>Terms & Conditions - MyQchat</h2><p>By QWNG - Software Developer Team</p><h4>1. Eligibility</h4><p>You must be 13+ or use with guardian permission.</p><h4>2. Account</h4><p>You are responsible for your Username and Password. Keep it safe. Do not share.</p><h4>3. Privacy</h4><p>We collect username, name, bio, messages, status, songs, calls, reports. We do not sell your data.</p><h4>4. Content</h4><p>You own your content. Do not post illegal, harmful, scam, or abusive content.</p><h4>5. Safety</h4><p>Block and Report bad users. Admin can give Scam Tick or Ban. Admin never asks password.</p><h4>6. Prohibited</h4><p>No scam, harassment, fake, spam, illegal activity, or sharing OTP / Bank details.</p><h4>7. Status & Song</h4><p>Status auto deletes in 24 hours. Songs are for personal use in Status.</p><h4>8. Deletion & Appeal</h4><p>You can delete account in Settings. Appeal in 15 days via Support: qwngofficial@gmail.com</p><h4>9. Service</h4><p>Service may change or stop. We try to keep it running.</p><h4>10. Liability</h4><p>Use at your own risk. QWNG - Software Developer Team is not liable for user content.</p><h4>11. Changes</h4><p>Terms may change. Continued use means you accept new Terms.</p><h4>12. Contact</h4><p>qwngofficial@gmail.com</p><p><a href="/">Back to MyQchat</a></p></body></html>'

@app.route('/privacy')
def privacy_page():
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Privacy - MyQchat</title></head><body style="font-family:Arial;padding:20px;max-width:700px;margin:auto"><h2>Privacy Policy - MyQchat</h2><p>By QWNG - Software Developer Team</p><p><b>We collect:</b> Username, Name, Bio, Messages, Status, Songs, Calls, Reports, Recovery Email.</p><p><b>We use it to:</b> Run MyQchat, show chats, status, songs, admin moderation, safety.</p><p><b>We do NOT:</b> Sell your data. Share your password. Share OTP or Bank details.</p><p><b>Your control:</b> You can change Bio, Settings, Delete Account in Settings.</p><p><b>Delete:</b> Status auto deletes in 24 hours. Voice auto deletes in 20 minutes.</p><p><b>Contact:</b> qwngofficial@gmail.com</p><p><a href="/">Back to MyQchat</a></p></body></html>'

@app.route('/help')
def help_page():
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Help - MyQchat</title></head><body style="font-family:Arial;padding:20px;max-width:700px;margin:auto"><h2>Help - MyQchat</h2><p>By QWNG - Software Developer Team</p><p><b>Chat:</b> Search user by Username or UID. Tap user. Type and Send.</p><p><b>Group:</b> Groups > Create Group > Add Member by UID.</p><p><b>Status:</b> Status > Write > Choose Song > Post. 24 hours auto delete.</p><p><b>Song:</b> Admin adds song. User chooses from list or custom URL.</p><p><b>Bot:</b> Open QWNG Bot. Type help. Bot is only for Help.</p><p><b>Tick:</b> Settings > Request Tick. Blue, Orange, Green only.</p><p><b>Report:</b> Settings > Report User. Write full detail.</p><p><b>Block:</b> Open chat > Block. Settings > Blocked Users > Unblock.</p><p><b>Call:</b> Open chat > Call / Video. History in Calls.</p><p><b>Forgot Password:</b> Login > Forgot Password. Need Recovery Email saved in Settings.</p><p><b>Support:</b> qwngofficial@gmail.com</p><p><a href="/">Back to MyQchat</a></p></body></html>'

@app.route('/about')
def about_page():
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>About - MyQchat</title></head><body style="font-family:Arial;padding:20px;max-width:700px;margin:auto"><h2>About MyQchat</h2><p>MyQchat is a simple chat app built by QWNG - Software Developer Team.</p><p>Chat 1-to-1, Group, Status, Song, Calls.</p><p>No Post, No Like, No Comment. Only Chat.</p><p>Owner: LoyalWQ</p><p>Support: qwngofficial@gmail.com</p><p><a href="/">Back to MyQchat</a></p></body></html>'

@app.errorhandler(404)
def not_found(e):
    return jsonify({'ok': False, 'error': 'Page not found. Go to MyQchat home.'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'ok': False, 'error': 'Server error. Try again.'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_owner()
        seed_songs()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
class MutedUser(db.Model):
    __tablename__ = 'muted_users'
    id = db.Column(db.Integer, primary_key=True)
    muter_uid = db.Column(db.String(20), nullable=False)
    muted_uid = db.Column(db.String(20), nullable=False)
    muted_name = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ArchivedChat(db.Model):
    __tablename__ = 'archived_chats'
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(20), nullable=False)
    chat_uid = db.Column(db.String(20), nullable=False)
    chat_name = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PinnedChat(db.Model):
    __tablename__ = 'pinned_chats'
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(20), nullable=False)
    chat_uid = db.Column(db.String(20), nullable=False)
    chat_name = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EditedMessage(db.Model):
    __tablename__ = 'edited_messages'
    id = db.Column(db.Integer, primary_key=True)
    msg_id = db.Column(db.Integer, nullable=False)
    old_text = db.Column(db.String(2000), default='')
    new_text = db.Column(db.String(2000), default='')
    editor_uid = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/api/edit_message', methods=['POST'])
def edit_message():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    m = Message.query.filter_by(id=d.get('msg_id')).first()
    if not m:
        return jsonify({'ok': False, 'error': 'Message not found'})
    if m.sender_uid != me.uid:
        return jsonify({'ok': False, 'error': 'Only sender can edit'})
    new_text = clean(d.get('new_text'), 2000)
    if not new_text:
        return jsonify({'ok': False, 'error': 'Enter new message'})
    if m.msg_type == 'deleted':
        return jsonify({'ok': False, 'error': 'Deleted message cannot be edited'})
    old = m.text
    m.text = new_text
    db.session.add(EditedMessage(msg_id=m.id, old_text=old, new_text=new_text, editor_uid=me.uid))
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Message edited'})

@app.route('/api/delete_chat', methods=['POST'])
def delete_chat():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    other = clean_uid(d.get('with_uid'))
    if not other:
        return jsonify({'ok': False, 'error': 'Select chat'})
    rows = Message.query.filter(((Message.sender_uid == me.uid) & (Message.to_uid == other)) | ((Message.sender_uid == other) & (Message.to_uid == me.uid))).all()
    for r in rows:
        if r.sender_uid == me.uid:
            r.text = 'This message was deleted'
            r.msg_type = 'deleted'
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Chat deleted for you', 'deleted_count': len(rows)})

@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    other = clean_uid(d.get('with_uid'))
    rows = Message.query.filter(((Message.sender_uid == me.uid) & (Message.to_uid == other)) | ((Message.sender_uid == other) & (Message.to_uid == me.uid))).all()
    for r in rows:
        if r.sender_uid == me.uid:
            r.text = 'This message was deleted'
            r.msg_type = 'deleted'
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Chat cleared'})

@app.route('/api/mute_user', methods=['POST'])
def mute_user():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    uid = clean_uid(d.get('muted_uid'))
    if not uid or uid == me.uid:
        return jsonify({'ok': False, 'error': 'Invalid user'})
    target = User.query.filter_by(uid=uid).first()
    if not target:
        return jsonify({'ok': False, 'error': 'User not found'})
    if MutedUser.query.filter_by(muter_uid=me.uid, muted_uid=uid).first():
        return jsonify({'ok': False, 'error': 'Already muted'})
    db.session.add(MutedUser(muter_uid=me.uid, muted_uid=uid, muted_name=target.name))
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'User muted. No notification from this user.'})

@app.route('/api/unmute_user', methods=['POST'])
def unmute_user():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    uid = clean_uid(d.get('muted_uid'))
    row = MutedUser.query.filter_by(muter_uid=me.uid, muted_uid=uid).first()
    if not row:
        return jsonify({'ok': False, 'error': 'Not muted'})
    db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'User unmuted'})

@app.route('/api/muted_list', methods=['GET'])
def muted_list():
    me = get_me()
    if not me:
        return jsonify({'muted': []})
    rows = MutedUser.query.filter_by(muter_uid=me.uid).all()
    out = []
    for r in rows:
        u = User.query.filter_by(uid=r.muted_uid).first()
        if u:
            out.append(pub_user(u))
    return jsonify({'muted': out})

@app.route('/api/archive_chat', methods=['POST'])
def archive_chat():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    uid = clean_uid(d.get('chat_uid'))
    if not uid:
        return jsonify({'ok': False, 'error': 'Select chat'})
    if ArchivedChat.query.filter_by(owner_uid=me.uid, chat_uid=uid).first():
        return jsonify({'ok': False, 'error': 'Already archived'})
    target = User.query.filter_by(uid=uid).first()
    name = target.name if target else uid
    db.session.add(ArchivedChat(owner_uid=me.uid, chat_uid=uid, chat_name=name))
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Chat archived'})

@app.route('/api/unarchive_chat', methods=['POST'])
def unarchive_chat():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    uid = clean_uid(d.get('chat_uid'))
    row = ArchivedChat.query.filter_by(owner_uid=me.uid, chat_uid=uid).first()
    if not row:
        return jsonify({'ok': False, 'error': 'Not archived'})
    db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Chat unarchived'})

@app.route('/api/archived_list', methods=['GET'])
def archived_list():
    me = get_me()
    if not me:
        return jsonify({'archived': []})
    rows = ArchivedChat.query.filter_by(owner_uid=me.uid).all()
    out = []
    for r in rows:
        u = User.query.filter_by(uid=r.chat_uid).first()
        if u:
            out.append(pub_user(u))
    return jsonify({'archived': out})

@app.route('/api/pin_chat', methods=['POST'])
def pin_chat():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    uid = clean_uid(d.get('chat_uid'))
    if not uid:
        return jsonify({'ok': False, 'error': 'Select chat'})
    if PinnedChat.query.filter_by(owner_uid=me.uid, chat_uid=uid).first():
        return jsonify({'ok': False, 'error': 'Already pinned'})
    if PinnedChat.query.filter_by(owner_uid=me.uid).count() >= 5:
        return jsonify({'ok': False, 'error': 'Max 5 pinned chats'})
    target = User.query.filter_by(uid=uid).first()
    name = target.name if target else uid
    db.session.add(PinnedChat(owner_uid=me.uid, chat_uid=uid, chat_name=name))
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Chat pinned on top'})

@app.route('/api/unpin_chat', methods=['POST'])
def unpin_chat():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    uid = clean_uid(d.get('chat_uid'))
    row = PinnedChat.query.filter_by(owner_uid=me.uid, chat_uid=uid).first()
    if not row:
        return jsonify({'ok': False, 'error': 'Not pinned'})
    db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Chat unpinned'})

@app.route('/api/pinned_list', methods=['GET'])
def pinned_list():
    me = get_me()
    if not me:
        return jsonify({'pinned': []})
    rows = PinnedChat.query.filter_by(owner_uid=me.uid).all()
    out = []
    for r in rows:
        u = User.query.filter_by(uid=r.chat_uid).first()
        if u:
            out.append(pub_user(u))
    return jsonify({'pinned': out})

@app.route('/api/search_messages', methods=['GET'])
def search_messages():
    me = get_me()
    if not me:
        return jsonify({'messages': []})
    q = clean(request.args.get('q'), 100).lower()
    if len(q) < 2:
        return jsonify({'messages': [], 'error': 'Type 2+ letters'})
    rows = Message.query.filter((Message.sender_uid == me.uid) | (Message.to_uid == me.uid)).order_by(Message.id.desc()).limit(200).all()
    out = []
    for m in rows:
        if q in m.text.lower():
            out.append(pub_message(m))
    return jsonify({'messages': out[:50]})

@app.route('/api/message_info', methods=['GET'])
def message_info():
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    m = Message.query.filter_by(id=request.args.get('msg_id')).first()
    if not m:
        return jsonify({'ok': False, 'error': 'Message not found'})
    edits = EditedMessage.query.filter_by(msg_id=m.id).all()
    return jsonify({'ok': True, 'message': pub_message(m), 'edited_count': len(edits), 'edited': [{'old': e.old_text, 'new': e.new_text, 'time': time_ago(e.created_at)} for e in edits]})
  class Poll(db.Model):
    __tablename__ = 'polls'
    id = db.Column(db.Integer, primary_key=True)
    creator_uid = db.Column(db.String(20), nullable=False)
    creator_name = db.Column(db.String(50), default='')
    question = db.Column(db.String(500), nullable=False)
    option1 = db.Column(db.String(200), default='')
    option2 = db.Column(db.String(200), default='')
    option3 = db.Column(db.String(200), default='')
    option4 = db.Column(db.String(200), default='')
    to_uid = db.Column(db.String(20), default='')
    group_id = db.Column(db.String(20), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PollVote(db.Model):
    __tablename__ = 'poll_votes'
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, nullable=False)
    voter_uid = db.Column(db.String(20), nullable=False)
    voter_name = db.Column(db.String(50), default='')
    option_no = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MyNote(db.Model):
    __tablename__ = 'my_notes'
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(100), default='')
    text = db.Column(db.String(2000), default='')
    color = db.Column(db.String(20), default='white')
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedContact(db.Model):
    __tablename__ = 'saved_contacts'
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(20), nullable=False)
    contact_uid = db.Column(db.String(20), nullable=False)
    contact_name = db.Column(db.String(50), default='')
    nickname = db.Column(db.String(50), default='')
    note = db.Column(db.String(300), default='')
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    owner_uid = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    detail = db.Column(db.String(500), default='')
    remind_date = db.Column(db.String(20), default='')
    remind_time = db.Column(db.String(20), default='')
    is_done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def pub_poll(p):
    v1 = PollVote.query.filter_by(poll_id=p.id, option_no=1).count()
    v2 = PollVote.query.filter_by(poll_id=p.id, option_no=2).count()
    v3 = PollVote.query.filter_by(poll_id=p.id, option_no=3).count()
    v4 = PollVote.query.filter_by(poll_id=p.id, option_no=4).count()
    total = v1 + v2 + v3 + v4
    return {'id': p.id, 'creator_uid': p.creator_uid, 'creator_name': p.creator_name, 'question': p.question, 'option1': p.option1, 'option2': p.option2, 'option3': p.option3, 'option4': p.option4, 'to_uid': p.to_uid, 'group_id': p.group_id, 'is_active': bool(p.is_active), 'votes1': v1, 'votes2': v2, 'votes3': v3, 'votes4': v4, 'total_votes': total, 'time': time_ago(p.created_at)}

def pub_note(n):
    return {'id': n.id, 'title': n.title, 'text': n.text, 'color': n.color, 'is_pinned': bool(n.is_pinned), 'time': time_ago(n.created_at), 'updated': time_ago(n.updated_at)}

def pub_saved_contact(c):
    return {'id': c.id, 'contact_uid': c.contact_uid, 'contact_name': c.contact_name, 'nickname': c.nickname, 'note': c.note, 'is_favorite': bool(c.is_favorite), 'time': time_ago(c.created_at)}

def pub_reminder(r):
    return {'id': r.id, 'title': r.title, 'detail': r.detail, 'remind_date': r.remind_date, 'remind_time': r.remind_time, 'is_done': bool(r.is_done), 'time': time_ago(r.created_at)}

@app.route('/api/create_poll', methods=['POST'])
def create_poll():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    q = clean(d.get('question'), 500)
    o1 = clean(d.get('option1'), 200)
    o2 = clean(d.get('option2'), 200)
    o3 = clean(d.get('option3'), 200)
    o4 = clean(d.get('option4'), 200)
    if not q or not o1 or not o2:
        return jsonify({'ok': False, 'error': 'Question + Option 1 + Option 2 required'})
    to_uid = clean_uid(d.get('to_uid'))
    gid = clean(d.get('group_id'), 20)
    if not to_uid and not gid:
        return jsonify({'ok': False, 'error': 'Select user or group for poll'})
    p = Poll(creator_uid=me.uid, creator_name=me.name, question=q, option1=o1, option2=o2, option3=o3, option4=o4, to_uid=to_uid, group_id=gid)
    db.session.add(p)
    db.session.commit()
    if to_uid:
        db.session.add(Message(sender_uid=me.uid, sender_name=me.name, to_uid=to_uid, text='Poll: ' + q + ' | 1. ' + o1 + ' | 2. ' + o2, msg_type='poll'))
        db.session.commit()
    return jsonify({'ok': True, 'poll': pub_poll(p)})

@app.route('/api/polls', methods=['GET'])
def polls_api():
    me = get_me()
    if not me:
        return jsonify({'polls': []})
    rows = Poll.query.filter((Poll.creator_uid == me.uid) | (Poll.to_uid == me.uid)).order_by(Poll.id.desc()).limit(50).all()
    return jsonify({'polls': [pub_poll(p) for p in rows]})

@app.route('/api/vote_poll', methods=['POST'])
def vote_poll():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    p = Poll.query.filter_by(id=d.get('poll_id')).first()
    if not p:
        return jsonify({'ok': False, 'error': 'Poll not found'})
    if not p.is_active:
        return jsonify({'ok': False, 'error': 'Poll closed'})
    opt = int(d.get('option_no') or 0)
    if opt < 1 or opt > 4:
        return jsonify({'ok': False, 'error': 'Select option 1 to 4'})
    if opt == 3 and not p.option3:
        return jsonify({'ok': False, 'error': 'Option 3 empty'})
    if opt == 4 and not p.option4:
        return jsonify({'ok': False, 'error': 'Option 4 empty'})
    old = PollVote.query.filter_by(poll_id=p.id, voter_uid=me.uid).first()
    if old:
        old.option_no = opt
        db.session.commit()
        return jsonify({'ok': True, 'msg': 'Vote updated', 'poll': pub_poll(p)})
    db.session.add(PollVote(poll_id=p.id, voter_uid=me.uid, voter_name=me.name, option_no=opt))
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Vote counted', 'poll': pub_poll(p)})

@app.route('/api/close_poll', methods=['POST'])
def close_poll():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    p = Poll.query.filter_by(id=d.get('poll_id')).first()
    if not p:
        return jsonify({'ok': False, 'error': 'Poll not found'})
    if p.creator_uid != me.uid and not me.is_admin:
        return jsonify({'ok': False, 'error': 'Only creator can close'})
    p.is_active = False
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Poll closed', 'poll': pub_poll(p)})

@app.route('/api/poll_result', methods=['GET'])
def poll_result():
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    p = Poll.query.filter_by(id=request.args.get('poll_id')).first()
    if not p:
        return jsonify({'ok': False, 'error': 'Poll not found'})
    votes = PollVote.query.filter_by(poll_id=p.id).all()
    return jsonify({'ok': True, 'poll': pub_poll(p), 'votes': [{'voter_name': v.voter_name, 'option_no': v.option_no, 'time': time_ago(v.created_at)} for v in votes]})

@app.route('/api/create_note', methods=['POST'])
def create_note():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    title = clean(d.get('title'), 100)
    text = clean(d.get('text'), 2000)
    if not title and not text:
        return jsonify({'ok': False, 'error': 'Write title or text'})
    color = clean(d.get('color'), 20) or 'white'
    if color not in ['white', 'yellow', 'green', 'pink', 'blue']:
        color = 'white'
    n = MyNote(owner_uid=me.uid, title=title, text=text, color=color)
    db.session.add(n)
    db.session.commit()
    return jsonify({'ok': True, 'note': pub_note(n)})

@app.route('/api/notes', methods=['GET'])
def notes_api():
    me = get_me()
    if not me:
        return jsonify({'notes': []})
    q = clean(request.args.get('q'), 100).lower()
    rows = MyNote.query.filter_by(owner_uid=me.uid).order_by(MyNote.is_pinned.desc(), MyNote.id.desc()).all()
    out = []
    for n in rows:
        if q and q not in n.title.lower() and q not in n.text.lower():
            continue
        out.append(pub_note(n))
    return jsonify({'notes': out})

@app.route('/api/update_note', methods=['POST'])
def update_note():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    n = MyNote.query.filter_by(id=d.get('note_id'), owner_uid=me.uid).first()
    if not n:
        return jsonify({'ok': False, 'error': 'Note not found'})
    if 'title' in d:
        n.title = clean(d.get('title'), 100)
    if 'text' in d:
        n.text = clean(d.get('text'), 2000)
    if 'color' in d:
        c = clean(d.get('color'), 20)
        if c in ['white', 'yellow', 'green', 'pink', 'blue']:
            n.color = c
    n.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'note': pub_note(n)})

@app.route('/api/delete_note', methods=['POST'])
def delete_note():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    n = MyNote.query.filter_by(id=d.get('note_id'), owner_uid=me.uid).first()
    if not n:
        return jsonify({'ok': False, 'error': 'Note not found'})
    db.session.delete(n)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Note deleted'})

@app.route('/api/pin_note', methods=['POST'])
def pin_note():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    n = MyNote.query.filter_by(id=d.get('note_id'), owner_uid=me.uid).first()
    if not n:
        return jsonify({'ok': False, 'error': 'Note not found'})
    n.is_pinned = not n.is_pinned
    n.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'pinned': n.is_pinned})

@app.route('/api/save_contact', methods=['POST'])
def save_contact():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    uid = clean_uid(d.get('contact_uid'))
    if not uid or uid == me.uid:
        return jsonify({'ok': False, 'error': 'Invalid user'})
    target = User.query.filter_by(uid=uid).first()
    if not target:
        return jsonify({'ok': False, 'error': 'User not found'})
    old = SavedContact.query.filter_by(owner_uid=me.uid, contact_uid=uid).first()
    if old:
        old.nickname = clean(d.get('nickname'), 50) or old.nickname
        old.note = clean(d.get('note'), 300) or old.note
        if 'is_favorite' in d:
            old.is_favorite = bool(d.get('is_favorite'))
        db.session.commit()
        return jsonify({'ok': True, 'msg': 'Contact updated', 'contact': pub_saved_contact(old)})
    c = SavedContact(owner_uid=me.uid, contact_uid=uid, contact_name=target.name, nickname=clean(d.get('nickname'), 50) or target.name, note=clean(d.get('note'), 300), is_favorite=bool(d.get('is_favorite')))
    db.session.add(c)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Contact saved', 'contact': pub_saved_contact(c)})

@app.route('/api/saved_contacts', methods=['GET'])
def saved_contacts():
    me = get_me()
    if not me:
        return jsonify({'contacts': []})
    q = clean(request.args.get('q'), 50).lower()
    rows = SavedContact.query.filter_by(owner_uid=me.uid).order_by(SavedContact.is_favorite.desc(), SavedContact.id.desc()).all()
    out = []
    for c in rows:
        if q and q not in c.contact_name.lower() and q not in c.nickname.lower() and q not in c.contact_uid:
            continue
        out.append(pub_saved_contact(c))
    return jsonify({'contacts': out})

@app.route('/api/delete_saved_contact', methods=['POST'])
def delete_saved_contact():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    c = SavedContact.query.filter_by(id=d.get('contact_id'), owner_uid=me.uid).first()
    if not c:
        return jsonify({'ok': False, 'error': 'Contact not found'})
    db.session.delete(c)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Contact removed'})

@app.route('/api/favorite_contact', methods=['POST'])
def favorite_contact():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    c = SavedContact.query.filter_by(id=d.get('contact_id'), owner_uid=me.uid).first()
    if not c:
        return jsonify({'ok': False, 'error': 'Contact not found'})
    c.is_favorite = not c.is_favorite
    db.session.commit()
    return jsonify({'ok': True, 'favorite': c.is_favorite})

@app.route('/api/create_reminder', methods=['POST'])
def create_reminder():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False, 'error': 'Login first'})
    title = clean(d.get('title'), 200)
    if not title:
        return jsonify({'ok': False, 'error': 'Enter reminder title'})
    r = Reminder(owner_uid=me.uid, title=title, detail=clean(d.get('detail'), 500), remind_date=clean(d.get('remind_date'), 20), remind_time=clean(d.get('remind_time'), 20))
    db.session.add(r)
    db.session.commit()
    return jsonify({'ok': True, 'reminder': pub_reminder(r)})

@app.route('/api/reminders', methods=['GET'])
def reminders_api():
    me = get_me()
    if not me:
        return jsonify({'reminders': []})
    show = clean(request.args.get('show'), 20) or 'pending'
    rows = Reminder.query.filter_by(owner_uid=me.uid).order_by(Reminder.id.desc()).all()
    out = []
    for r in rows:
        if show == 'pending' and r.is_done:
            continue
        if show == 'done' and not r.is_done:
            continue
        out.append(pub_reminder(r))
    return jsonify({'reminders': out})

@app.route('/api/done_reminder', methods=['POST'])
def done_reminder():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    r = Reminder.query.filter_by(id=d.get('reminder_id'), owner_uid=me.uid).first()
    if not r:
        return jsonify({'ok': False, 'error': 'Reminder not found'})
    r.is_done = True
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Reminder done'})

@app.route('/api/delete_reminder', methods=['POST'])
def delete_reminder():
    d = request.get_json(silent=True) or {}
    me = get_me()
    if not me:
        return jsonify({'ok': False})
    r = Reminder.query.filter_by(id=d.get('reminder_id'), owner_uid=me.uid).first()
    if not r:
        return jsonify({'ok': False, 'error': 'Reminder not found'})
    db.session.delete(r)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Reminder deleted'})FRONTEND_HEAD = '''
<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'><title>MyQchat</title><meta name='theme-color' content='#075e54'><style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f0f2f5;color:#111b21;padding-bottom:env(safe-area-inset-bottom)}
.top{background:#075e54;color:#fff;padding:14px 16px 12px;position:sticky;top:0;z-index:20;box-shadow:0 2px 8px rgba(0,0,0,.15);display:flex;justify-content:space-between;align-items:center}
.top b{font-size:21px;letter-spacing:.2px}
.top small{font-size:11px;opacity:.85;display:block;margin-top:1px;letter-spacing:.3px}
.top .live{font-size:11px;background:#25d366;color:#fff;padding:5px 9px;border-radius:20px;font-weight:600}
.card{background:#fff;margin:10px 10px 12px;padding:14px;border-radius:16px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
input,select,textarea{width:100%;padding:12px 13px;margin:7px 0;border:1px solid #d9dee3;border-radius:12px;font-size:15px;background:#f8f9fa;outline:none}
input:focus,select:focus,textarea:focus{border-color:#075e54;background:#fff;box-shadow:0 0 0 3px rgba(7,94,84,.10)}
textarea{min-height:74px;resize:vertical}
button{background:#075e54;color:#fff;border:none;padding:12px;border-radius:12px;width:100%;font-size:15px;font-weight:600;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.12)}
button:active{transform:scale(.98);opacity:.92}
button.danger{background:#e53935}
button.secondary{background:#eef2f2;color:#075e54;border:1px solid #d9dee3;box-shadow:none}
button.ghost{background:#fff;color:#111b21;border:1px solid #e5e8eb;box-shadow:none}
.msg{padding:9px 12px;border-radius:14px;margin:7px;max-width:80%;font-size:15px;line-height:1.45;word-break:break-word;box-shadow:0 1px 2px rgba(0,0,0,.08)}
.mine{background:#d9fdd3;margin-left:auto;text-align:left;border-bottom-right-radius:4px}
.other{background:#fff;border-bottom-left-radius:4px}
.tabs{display:flex;background:#075e54;color:#fff;position:sticky;top:57px;z-index:15;box-shadow:0 2px 6px rgba(0,0,0,.10)}
.tabs div{flex:1;text-align:center;padding:13px 2px;cursor:pointer;font-size:13px;letter-spacing:.2px;opacity:.85}
.tabs div.active{opacity:1;font-weight:700;border-bottom:3px solid #fff}
.hidden{display:none}
.small{font-size:12.5px;color:#667781;line-height:1.5}
.link{color:#008069;cursor:pointer;font-weight:600;text-decoration:none}
.flex{display:flex;gap:8px;align-items:center}
.flex button{width:auto;flex:1}
.avatar{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:18px;flex-shrink:0;box-shadow:inset 0 0 0 1px rgba(255,255,255,.4)}
.row{display:flex;gap:11px;align-items:center;padding:11px 4px;border-bottom:1px solid #f0f2f5;cursor:pointer}
.row:active{background:#f7f8f9;border-radius:12px}
.row:last-child{border-bottom:none}
.row b{font-size:15.5px;color:#111b21}
.row .sub{font-size:13px;color:#667781;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:230px;margin-top:1px}
.badge{background:#25d366;color:#fff;font-size:11px;padding:3px 8px;border-radius:20px;font-weight:700;min-width:20px;text-align:center}
.tick{color:#53bdeb;font-weight:800}
.tick-orange{color:#ff8c00;font-weight:800}
.tick-green{color:#00a884;font-weight:800}
.tick-scam{color:#e53935;font-weight:800;font-size:11px;background:#ffebee;padding:2px 7px;border-radius:10px}
.chip{display:inline-block;background:#e7f8ef;color:#075e54;padding:5px 11px;border-radius:20px;font-size:12px;margin:2px;font-weight:600}
.songrow{display:flex;gap:10px;align-items:center;padding:11px;border:1px solid #eef0f2;border-radius:14px;margin:7px 0;background:#fbfbfc}
.songrow button{width:72px;padding:9px}
.modal-bg{position:fixed;inset:0;background:rgba(11,20,26,.55);display:flex;align-items:flex-end;justify-content:center;z-index:50}
.modal-box{background:#fff;width:100%;max-width:540px;max-height:88vh;overflow:auto;padding:18px 16px 22px;border-radius:20px 20px 0 0}
.searchbox{position:sticky;top:0;background:#fff;padding-bottom:8px;z-index:5}
.pill{background:#e7f8ef;color:#075e54;font-size:12px;font-weight:700;padding:6px 10px;border-radius:20px}
.section-title{font-size:13px;font-weight:700;color:#667781;letter-spacing:.6px;text-transform:uppercase;margin:14px 2px 6px}
.divider{height:1px;background:#eef0f2;margin:14px 0}
.pro-header{display:flex;gap:12px;align-items:center;background:#075e54;color:#fff;padding:16px;border-radius:16px;margin-bottom:12px}
.pro-header h2{margin:0;font-size:20px}
.pro-header p{margin:4px 0 0;font-size:13px;opacity:.9}
</style></head><body>
<div class='top'><div><b>MyQchat</b><small>QWNG • Software Developer Team</small></div><span class='live'>● Live</span></div>
<div id='authPage' class='card'><div class='pro-header'><div><h2>Welcome to MyQchat</h2><p>Simple • Fast • Safe Chatting</p></div></div><p class='small'>Login with your Username and Password. New ho? Neeche account banao.</p><label class='small'><b>USERNAME</b></label><input id='loginUser' placeholder='Username — e.g. rahul123' autocomplete='username'><label class='small'><b>PASSWORD</b></label><input id='loginPass' type='password' placeholder='Password' autocomplete='current-password'><button onclick='doLogin()'>Login</button><div class='divider'></div><p style='text-align:center;margin:2px 0 8px'><span class='pill'>NEW ACCOUNT</span></p><label class='small'><b>NEW USERNAME</b></label><input id='suUser' placeholder='New Username'><label class='small'><b>YOUR NAME</b></label><input id='suName' placeholder='Your Name'><label class='small'><b>NEW PASSWORD</b></label><input id='suPass' type='password' placeholder='New Password'><button onclick='doSignup()'>Create Account</button><p class='small' style='text-align:center;margin-top:14px'>By continuing, you agree to our <span class='link' onclick='showTerms()'>Terms</span> and <span class='link' onclick='showPrivacy()'>Privacy</span> • <span class='link' onclick='showHelp()'>Help</span></p><p class='small' style='text-align:center'><span class='link' onclick='showForgot()'>Forgot Password?</span></p><p class='small' style='text-align:center'>Support: qwngofficial@gmail.com</p></div>
<div id='mainPage' class='hidden'>
<div class='tabs'><div id='tabChats' class='active' onclick='showTab("Chats")'>Chats</div><div id='tabGroups' onclick='showTab("Groups")'>Groups</div><div id='tabStatus' onclick='showTab("Status")'>Status</div><div id='tabCalls' onclick='showTab("Calls")'>Calls</div><div id='tabSettings' onclick='showTab("Settings")'>Settings</div></div>
<div id='pageChats' class='card'><div class='searchbox'><input id='searchBox' placeholder='Search by Username or 8-digit UID' oninput='searchUsers()'><div id='searchRes'></div></div><div style='display:flex;justify-content:space-between;align-items:center'><h3 style='margin:8px 0'>Chats</h3><span class='pill'>Online: <span id='onlineCount'>0</span></span></div><div id='chatList'></div><div id='broadcastBox'></div></div>
<div id='pageGroups' class='card hidden'><h3 style='margin:4px 0'>Groups</h3><p class='small'>Create group, add members by UID, chat together.</p><input id='grpName' placeholder='Group Name'><input id='grpDesc' placeholder='Group Description'><button onclick='createGroup()'>Create Group</button><div id='groupList' style='margin-top:10px'></div></div>
<div id='pageStatus' class='card hidden'><h3 style='margin:4px 0'>Status — 24 hours</h3><p class='small'>Status 24 hours me auto delete ho jayega.</p><textarea id='statusText' placeholder='Write status...'></textarea><label class='small'><b>CHOOSE SONG FROM LIBRARY</b></label><select id='statusSong'><option value=''>No Song</option></select><label class='small'><b>OR CUSTOM SONG URL</b></label><input id='statusCustomUrl' placeholder='Paste your song URL here'><input id='statusCustomTitle' placeholder='Custom Song Title'><button onclick='postStatus()'>Post Status</button><div id='statusList' style='margin-top:12px'></div><div class='section-title'>Music Library</div><input id='songSearch' placeholder='Search song...' oninput='loadSongs()'><div id='songList'></div></div>
<div id='pageCalls' class='card hidden'><h3 style='margin:4px 0'>Calls</h3><p class='small'>Voice and Video call history. Kisi user ko call karne ke liye Chats me jake uska chat kholo.</p><div id='callList'></div></div>
<div id='pageSettings' class='card hidden'><h3 style='margin:4px 0'>Settings</h3><label class='small'><b>NAME</b></label><input id='setName' placeholder='Name'><label class='small'><b>BIO</b></label><textarea id='setBio' placeholder='Bio - About you'></textarea><label class='small'><b>RECOVERY EMAIL (Forgot Password ke liye)</b></label><input id='setRecovery' placeholder='Recovery Email'><label class='small'><b>WALLPAPER</b></label><select id='setWallpaper'><option value='default'>Wallpaper Default</option><option value='green'>Wallpaper Green</option><option value='dark'>Wallpaper Dark</option><option value='blue'>Wallpaper Blue</option></select><label class='small'><b>FONT SIZE</b></label><select id='setFont'><option value='Small'>Font Small</option><option value='Medium'>Font Medium</option><option value='Large'>Font Large</option></select><label class='small'><b>CHAT COLOR</b></label><select id='setChatColor'><option value='Green'>Chat Green</option><option value='Blue'>Chat Blue</option><option value='Orange'>Chat Orange</option></select><label><input type='checkbox' id='setDark' style='width:auto'> Dark Mode</label><br><label><input type='checkbox' id='setRead' style='width:auto' checked> Read Receipts (Blue Tick)</label><br><label><input type='checkbox' id='setNotif' style='width:auto' checked> Notifications</label><label class='small'><b>LAST SEEN PRIVACY</b></label><select id='setLastSeen'><option value='Everyone'>Everyone</option><option value='Contacts'>My Contacts</option><option value='Nobody'>Nobody</option></select><button onclick='saveSettings()'>Save Settings</button><div class='divider'></div><h4 style='margin:4px 0'>Request Tick</h4><label class='small'><b>TICK TYPE</b></label><select id='tickType'><option value='Blue'>Blue Tick</option><option value='Orange'>Orange Tick</option><option value='Green'>Green Tick</option></select><input id='tickReason' placeholder='Reason for Tick - Why you need it?'><button onclick='requestTick()'>Request Tick</button><div id='myTickBox'></div><div class='divider'></div><h4 style='margin:4px 0'>Report User</h4><input id='reportUser' placeholder='Reported UID - 8 digit'><select id='reportReason'><option value='Scam'>Scam</option><option value='Harassment'>Harassment</option><option value='Fake'>Fake</option><option value='Spam'>Spam</option><option value='Abuse'>Abuse</option><option value='Other'>Other</option></select><textarea id='reportDetail' placeholder='Detail - 400 letters'></textarea><button onclick='sendReport()'>Report User</button><div id='adminBox' class='hidden'><div class='divider'></div><h3>Admin Panel</h3><p class='small'>Only Owner can see this.</p><label class='small'><b>SONG TITLE</b></label><input id='songTitle' placeholder='Song Title'><label class='small'><b>SONG ARTIST</b></label><input id='songArtist' placeholder='Song Artist'><label class='small'><b>SONG URL</b></label><input id='songUrl' placeholder='Song URL - https://...'><button onclick='addSong()'>Add Song</button><div class='divider'></div><label class='small'><b>BROADCAST MESSAGE</b></label><textarea id='broadcastText' placeholder='Broadcast Message to all users'></textarea><select id='broadcastType'><option value='Announcement'>Announcement</option><option value='Warning'>Warning</option><option value='Ad'>Ad</option></select><button onclick='sendBroadcast()'>Send Broadcast to All</button><div id='adminStats' style='margin-top:10px'></div><div id='tickList'></div><div id='reportList'></div><button onclick='loadAdminLists()'>Refresh Admin Lists</button></div><div class='divider'></div><button onclick='showTerms()' class='secondary'>Terms</button><br><br><button onclick='showPrivacy()' class='secondary'>Privacy</button><br><br><button onclick='showHelp()' class='secondary'>Help</button><br><br><button onclick='showStarred()' class='secondary'>Starred Messages</button><br><br><button onclick='showBlocked()' class='secondary'>Blocked Users</button><br><br><button onclick='doLogout()' class='secondary'>Logout</button><br><br><button onclick='deleteAccount()' class='danger'>Delete Account</button></div>
</div>
<div id='chatPage' class='card hidden'><button onclick='backToChats()' class='secondary' style='width:86px'>← Back</button><h3 id='chatTitle' style='margin:10px 0 2px'>Chat</h3><p class='small' id='chatSub'></p><div id='chatMsgs' style='max-height:420px;overflow:auto;background:#efeae2;padding:10px;border-radius:14px;min-height:220px'></div><div class='flex' style='margin-top:10px'><input id='chatInput' placeholder='Message' onkeydown='if(event.key==="Enter")sendChat()'><button onclick='sendChat()' style='width:84px'>Send</button></div><div class='flex' style='margin-top:8px'><button onclick='attachFile()' class='secondary'>Attach</button><button onclick='openEmoji()' class='secondary'>Emoji</button><button onclick='recordVoice()' class='secondary'>Voice</button><button onclick='startCall("voice")' class='secondary'>Call</button><button onclick='startCall("video")' class='secondary'>Video</button></div><div id='emojiBox' class='hidden' style='font-size:26px;padding:12px;cursor:pointer;background:#fff;border-radius:12px;margin-top:8px'><span onclick='pickEmoji("😊")'>😊</span> <span onclick='pickEmoji("😂")'>😂</span> <span onclick='pickEmoji("❤️")'>❤️</span> <span onclick='pickEmoji("👍")'>👍</span> <span onclick='pickEmoji("🙏")'>🙏</span> <span onclick='pickEmoji("🎉")'>🎉</span> <span onclick='pickEmoji("🔥")'>🔥</span> <span onclick='pickEmoji("🌸")'>🌸</span></div><div id='replyBox' class='hidden small' style='background:#fff;padding:8px;border-radius:10px;margin-top:8px'>Replying to: <span id='replyText'></span> <span class='link' onclick='cancelReply()'>Cancel</span></div></div>
<div id='modal' class='hidden'><div class='modal-bg' onclick='if(event.target===this)closeModal()'><div class='modal-box'><button onclick='closeModal()' class='secondary' style='width:84px'>Close</button><div id='modalBody'></div></div></div></div>
'''
  
