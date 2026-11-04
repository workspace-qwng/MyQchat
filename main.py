
import flet as ft
import sqlite3
from datetime import datetime
DB="myqchat_real.db"
def init_db():
    con=sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT UNIQUE, about TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, time TEXT)")
    con.commit(); con.close()
def main(page: ft.Page):
    page.title="MyQchat REAL - No Fake"
    page.theme_mode=ft.ThemeMode.DARK
    init_db()
    my_name = ft.TextField(label="Your Real Name", autofocus=True)
    chat_list = ft.ListView(expand=True)
    msg_input = ft.TextField(label="Real message...", expand=True)
    def load_chats():
        chat_list.controls.clear()
        con=sqlite3.connect(DB)
        users=con.execute("SELECT name FROM users WHERE name!=?", (my_name.value or "Me",)).fetchall()
        for (u,) in users:
            chat_list.controls.append(ft.ListTile(title=ft.Text(u, size=17), subtitle=ft.Text("Real chat - Tap"), leading=ft.Icon(ft.Icons.PERSON), on_click=lambda e, name=u: open_chat(name)))
        con.close(); page.update()
    def open_chat(name):
        page.clean()
        msgs=ft.ListView(expand=True)
        con=sqlite3.connect(DB)
        rows=con.execute("SELECT sender,text,time FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id", (my_name.value, name, name, my_name.value)).fetchall()
        for s,t,ti in rows:
            is_me = s==my_name.value
            msgs.controls.append(ft.Container(content=ft.Text(f"{t} {ti}", size=14), bgcolor="#005c4b" if is_me else "#202c33", padding=10, border_radius=10, margin=ft.margin.only(left=50 if is_me else 10, right=10 if is_me else 50, top=5)))
        con.close()
        def send(e):
            if msg_input.value.strip()=="": return
            con=sqlite3.connect(DB)
            con.execute("INSERT INTO messages (sender,receiver,text,time) VALUES (?,?,?,?)", (my_name.value, name, msg_input.value, datetime.now().strftime("%H:%M")))
            con.commit(); con.close()
            open_chat(name)
        page.add(ft.AppBar(title=ft.Text(name), leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_home())), msgs, ft.Row([msg_input, ft.IconButton(ft.Icons.SEND, on_click=send)]))
    def show_home():
        page.clean()
        page.add(ft.Text("MyQchat REAL", size=28, weight="bold"), ft.Text("No Fake Chats - Phone is Server - Real APK", color="#00a884"), my_name, ft.ElevatedButton("Start MyQchat", bgcolor="#00a884", color="white", on_click=lambda e: (init_user(), load_chats(), page.add(chat_list, ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=add_contact)))),)
    def init_user():
        con=sqlite3.connect(DB)
        con.execute("INSERT OR IGNORE INTO users (name,about) VALUES (?,?)", (my_name.value, "Real MyQchat User"))
        con.commit(); con.close()
    def add_contact(e):
        def save_contact(ev):
            con=sqlite3.connect(DB)
            con.execute("INSERT OR IGNORE INTO users (name,about) VALUES (?,?)", (contact_name.value, "Real User"))
            con.commit(); con.close()
            page.dialog.open=False; page.update(); load_chats()
        contact_name=ft.TextField(label="Friend Real Name")
        page.dialog=ft.AlertDialog(title=ft.Text("Add Real Friend"), content=contact_name, actions=[ft.TextButton("Add", on_click=save_contact)])
        page.dialog.open=True; page.update()
    show_home()
ft.app(target=main)
