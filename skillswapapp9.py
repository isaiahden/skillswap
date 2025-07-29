import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth
from datetime import datetime
import json
import google.generativeai as genai
from gtts import gTTS
import base64
import hashlib
import os
# ---------------- FIREBASE SETUP ----------------
# ---------------- FIREBASE SETUP ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE"]))
    firebase_admin.initialize_app(cred)

# Always set db after Firebase is initialized (even if it was already initialized)
db = firestore.client()

# Always configure Gemini API (even on rerun)
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Gemini API key not found in secrets or environment variable.")
else:
    genai.configure(api_key=api_key)



# ---------------- UTILS ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_data(username):
    if not username or not username.strip():
        return None
    user_ref = db.collection("users").document(username).get()
    return user_ref.to_dict() if user_ref.exists else None

# ---------------- SESSION ----------------
st.set_page_config(page_title="SkillSwap Cloud", layout="wide")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# === AI TEACHERS LIST ===
AI_TEACHERS = [
    {"name":"Ada AI","skill":"Python Programming","bio":"Expert in Python and data science.","avatar":"https://api.dicebear.com/7.x/bottts/svg?seed=Ada"},
    {"name":"Leo AI","skill":"Digital Marketing","bio":"Marketing strategist and growth hacker.","avatar":"https://api.dicebear.com/7.x/bottts/svg?seed=Leo"},
    {"name":"Marie AI","skill":"French Language","bio":"Native French speaker and language coach.","avatar":"https://api.dicebear.com/7.x/bottts/svg?seed=Marie"},
    {"name":"Arturo AI","skill":"Graphic Design","bio":"Creative designer with 10+ years experience.","avatar":"https://api.dicebear.com/7.x/bottts/svg?seed=Arturo"}
]

# === UTILS ===
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def get_user_data(u): 
    if not u or not u.strip(): return None
    doc = db.collection("users").document(u).get()
    return doc.to_dict() if doc.exists else None

# === SESSION SETUP & THEME ===
st.set_page_config(page_title="SkillSwap Cloud", layout="wide")
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "dark_mode" not in st.session_state: st.session_state.dark_mode = True

def theme_toggle():
    theme = st.sidebar.checkbox("🌗 Dark Mode", value=st.session_state.dark_mode)
    st.session_state.dark_mode = theme
    css = "<style>"
    if theme:
        css += "body{color:white;background-color:#222;} .stButton>button{color:white;background:#5c5c8a;}"
    else:
        css += "body{color:black;background-color:#f5f5fa;} .stButton>button{color:black;background:#e0e0e0;}"
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

theme_toggle()

# === GLOBAL CSS for WhatsApp style ===
st.markdown("""
<style>
body {font-family:'Segoe UI',sans-serif;background-color:#e5ddd5;}
.sidebar .sidebar-content{background:#075e54;color:white;}
.chat-header{background:#075e54;padding:15px;color:white;border-radius:0 0 5px 5px;}
.message-bubble{padding:10px 14px;border-radius:12px;margin:6px 0;max-width:75%;box-shadow:0 1px 3px rgba(0,0,0,0.1);clear:both;}
.message-sent{background:#dcf8c6;float:right;}
.message-received{background:white;float:left;}
.clearfix::after{content:'';clear:both;display:table;}
</style>
""", unsafe_allow_html=True)

def send_password_reset(email):
    try:
        action_code_settings = auth.ActionCodeSettings(
            url="https://skillswap-worldwide.streamlit.app",  # ✅ Your deployed app URL
            handle_code_in_app=False
        )
        link = auth.generate_password_reset_link(email, action_code_settings)
        st.success("📧 Password reset link generated!")
        st.markdown(f"🔗 [Click here to reset your password]({link})")
    except Exception as e:
        st.error("❌ Failed to send reset link.")
        st.exception(e)

def send_email_verification(email):
    try:
        link = auth.generate_email_verification_link(email)
        st.info("📧 Verification email sent. Please check your inbox.")
        st.write(f"🔗 [Click here to verify your email]({link})")
    except Exception as e:
        st.error(f"❌ Failed to send verification email: {e}")


def login_page():
    st.subheader("🔐 Login")
    u = st.text_input("Username", key="login_user")
    p = st.text_input("Password", type="password", key="login_pass")

 if st.button("Login"):
    d = get_user_data(u)
    if d and d.get("password") == hash_password(p):
        try:
            user_record = auth.get_user_by_email(d["email"])
            if not user_record.email_verified:
                st.warning("⚠️ Please verify your email before logging in.")
                return
            # Email is verified
            st.session_state.logged_in = True
            st.session_state.username = u
            st.success(f"✅ Logged in as {u}")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
    else:
        st.error("❌ Invalid username or password.")

# 🔐 Forgot Password Section
with st.expander("🔑 Forgot Password?"):
    email_reset = st.text_input("Enter your registered email", key="reset_email")
    if st.button("Send Reset Link"):
        if email_reset.strip():
            send_password_reset(email_reset)
        else:
            st.warning("⚠️ Please enter your email address.")

def signup_page():
    st.subheader("📝 Sign Up")
    u = st.text_input("New Username", key="signup_user")
    email = st.text_input("Email Address", key="signup_email")
    p = st.text_input("New Password", type="password", key="signup_pass")
    role = st.selectbox("Role", ["Student", "Teacher"])
    bio = st.text_area("Bio")

    if st.button("Sign Up"):
        if not u.strip() or not p or not email.strip():
            st.error("All fields are required.")
        elif get_user_data(u):
            st.error("Username already taken.")
        else:
            # Create user in Firestore
            db.collection("users").document(u).set({
                "email": email,
                "password": hash_password(p),
                "role": role,
                "bio": bio,
                "skills": [],
                "notifications": [],
                "email_verified": False
            })
            st.success("✅ Account created! A verification link has been sent to your email.")
            send_email_verification(email)




# === INTERFACE FUNCTIONS ===
def profile_edit():
    d = get_user_data(st.session_state.username)
    if d:
        st.sidebar.header("👤 Edit Profile")
        bio = st.sidebar.text_area("Bio", value=d.get("bio", ""), key="profile_bio")
        role = st.sidebar.selectbox(
            "Role", ["Student", "Teacher"],
            index=["Student", "Teacher"].index(d.get("role", "Student")),
            key="profile_role"
        )
        if st.sidebar.button("Update Profile", key="update_profile_btn"):
            db.collection("users").document(st.session_state.username).update({
                "bio": bio,
                "role": role
            })
            st.sidebar.success("Profile updated!", icon="✅")
            
def show_notifications():
    d = get_user_data(st.session_state.username)
    if d and d.get("notifications"):
        st.sidebar.header("🔔 Notifications")
        for n in d["notifications"]:
            st.sidebar.info(n)
        if st.sidebar.button("Clear All"):
            db.collection("users").document(st.session_state.username).update({"notifications":[]})
            st.sidebar.success("Cleared!")

def chat_interface():
    st.markdown("<div class='chat-header'><h4>💬 Chat</h4></div>", unsafe_allow_html=True)
    users = [doc.id for doc in db.collection("users").stream() if doc.id!=st.session_state.username]
    partner = st.selectbox("Partner:", users)
    chat_id = "_".join(sorted([st.session_state.username, partner]))
    msgs = db.collection("chats").document(chat_id).collection("messages").order_by("timestamp").stream()
    for m in msgs:
        d = m.to_dict()
        sent = d["sender"]==st.session_state.username
        cls = "message-sent" if sent else "message-received"
        name = "You" if sent else d["sender"]
        st.markdown(f"<div class='message-bubble {cls} clearfix'><b>{name}</b><br>{d['text']}<br><small>{d['timestamp'].strftime('%H:%M')}</small></div>", unsafe_allow_html=True)
    st.markdown("<div class='clearfix'></div>", unsafe_allow_html=True)
    txt = st.text_input("Type a message", key="msg_input")
    if st.button("Send"):
        if txt.strip():
            db.collection("chats").document(chat_id).collection("messages").add({
                "sender":st.session_state.username,"receiver":partner,
                "text":txt.strip(),"timestamp":datetime.now()
            })
            st.rerun()



def view_profiles():
    st.subheader("🧑‍🏫 Browse Users")
    search = st.text_input("Search skill or role")
    us = [(doc.id,doc.to_dict()) for doc in db.collection("users").stream()]
    us = [u for u in us if u[0]!=st.session_state.username]
    us = sorted(us, key=lambda x: (x[1].get("skills",[""])[0].lower() if x[1].get("skills") else ""))
    for uname,d in us:
        if search and search.lower() not in d.get("role","").lower() and not any(search.lower() in s.lower() for s in d.get("skills",[])):
            continue
        st.markdown(f"### 👤 {uname}\n**Role**: {d.get('role','N/A')}\n**Bio**: {d.get('bio','')}\n**Skills**: {', '.join(d.get('skills',[])) or 'None'}\n---")

def booking_interface():
    st.markdown("<div class='chat-header'><h4>🤖 Book AI Teacher</h4></div>", unsafe_allow_html=True)
    ai_names = [f"{ai['name']} ({ai['skill']})" for ai in AI_TEACHERS]
    choice = st.selectbox("Choose an AI Teacher", ai_names)
    ai = AI_TEACHERS[ai_names.index(choice)]
    st.image(ai["avatar"], width=80)
    st.markdown(f"<b>{ai['name']}</b> – <i>{ai['skill']}</i><br>{ai['bio']}", unsafe_allow_html=True)
    date = st.date_input("Select Date")
    time = st.time_input("Select Time")
    if st.button("Book Session"):
        db.collection("bookings").add({
            "student":st.session_state.username,"teacher":ai["name"],
            "skill":ai["skill"],"datetime":datetime.combine(date,time),
            "status":"confirmed","ai":True
        })
        st.success(f"✅ Booked with {ai['name']} on {date} at {time}")
        st.session_state.active_ai_teacher=ai["name"]
        st.session_state.active_ai_skill=ai["skill"]
        st.session_state.active_ai_avatar=ai["avatar"]
        st.session_state.ai_chat_history=[]
    st.markdown("### 💬 Your AI Chat")
    if "active_ai_teacher" in st.session_state:
        name=st.session_state.active_ai_teacher
        chat_id = f"{st.session_state.username}_{name}"
        msgs = db.collection("ai_chats").document(chat_id).collection("messages").order_by("timestamp").stream()
        st.session_state.ai_chat_history = []
        for m in msgs:
            d=m.to_dict(); st.session_state.ai_chat_history.append({"sender":d["sender"],"text":d["text"]})
        for msg in st.session_state.ai_chat_history:
            sent = msg["sender"]=="user"
            align = "right" if sent else "left"
            clr = "#dcf8c6" if sent else "#fff"
            sender = "You" if sent else name
            st.markdown(f"<div style='background-color:{clr};padding:10px;border-radius:12px; margin:6px 0; float:{align};max-width:75%;clear:both;box-shadow:0 1px 3px rgba(0,0,0,0.1);'><b>{sender}:</b><br>{msg['text']}</div>", unsafe_allow_html=True)
        st.markdown("<div style='clear:both'></div>", unsafe_allow_html=True)
        inp = st.text_input("Message", key="ai_input")
        if st.button("Send"):
            if inp.strip():
                db.collection("ai_chats").document(chat_id).collection("messages").add({
                    "sender":"user","text":inp.strip(),"timestamp":datetime.now()
                })
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel("gemini-1.5-pro-latest")
                    history = [{"role":"user","parts":[m["text"]]} if m["sender"]=="user" else {"role":"model","parts":[m["text"]]} for m in st.session_state.ai_chat_history]
                    chat = model.start_chat(history=history)
                    resp = chat.send_message(inp)
                    db.collection("ai_chats").document(chat_id).collection("messages").add({
                        "sender":"ai","text":resp.text,"timestamp":datetime.now()
                    })
                    st.rerun()
                except Exception as e:
                    st.error("AI Error: "+str(e))

def channel_interface():
    st.markdown("<div class='chat-header'><h4>📢 SkillSwap Channels</h4></div>", unsafe_allow_html=True)
    channels = [c.to_dict() for c in db.collection("channels").stream()]
    st.sidebar.markdown("---")
    st.markdown("### Available Channels")
    for ch in channels:
        st.markdown(f"**{ch['name']}** — by {ch['created_by']}")
        if st.button(f"Follow {ch['name']}", key=f"follow_{ch['name']}"):
            db.collection("channels").document(ch['name'].lower()).update({"followers":firestore.ArrayUnion([st.session_state.username])})
            st.success("Now following.")

# === MAIN ===
if not st.session_state.logged_in:
    col1, col2 = st.columns(2)
    with col1: login_page()
    with col2: signup_page()
else:
    st.markdown(f"<div class='chat-header'><h2 style='margin:0;'>🌐 SkillSwap</h2><span style='font-size:14px;'>Hello, {st.session_state.username}</span></div>", unsafe_allow_html=True)

    section = st.sidebar.radio(
        "📂 Menu",
        ["💬 Chat", "🧑‍💻 Profiles", "📅 Booking", "🚪 Rooms", "👤 Profile", "🔔 Notifications"],
        key="main_menu_radio"
    )

    st.sidebar.markdown("---")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # Render only the selected section
    if section == "💬 Chat":
        chat_interface()
    elif section == "🧑‍💻 Profiles":
        view_profiles()
    elif section == "📅 Booking":
        booking_interface()
    elif section == "🚪 Rooms":
        channel_interface()
    elif section == "👤 Profile":
        profile_edit()
    elif section == "🔔 Notifications":
        show_notifications()

    st.markdown("---")
    st.caption(f"✅ Logged in as: **{st.session_state.username}**  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Peer‑to‑peer learning with WhatsApp‑style UI")
