import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
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


# ---------------- AI TEACHERS ----------------
AI_TEACHERS = [
    {
        "name": "Ada AI",
        "skill": "Python Programming",
        "bio": "Expert in Python and data science.",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Ada"
    },
    {
        "name": "Leo AI",
        "skill": "Digital Marketing",
        "bio": "Marketing strategist and growth hacker.",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Leo"
    },
    {
        "name": "Marie AI",
        "skill": "French Language",
        "bio": "Native French speaker and language coach.",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Marie"
    },
    {
        "name": "Arturo AI",
        "skill": "Graphic Design",
        "bio": "Creative designer with 10+ years experience.",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Arturo"
    }
]

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

# ---------------- AUTH ----------------
def login_page():
    st.subheader("🔐 Login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        user_data = get_user_data(username)
        if user_data and user_data["password"] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Logged in as {username}")
            st.rerun()
            return
        st.error("Invalid credentials.")
        
def signup_page():
    st.subheader("📝 Sign Up")
    username = st.text_input("New Username", key="signup_user")
    password = st.text_input("New Password", type="password", key="signup_pass")
    role = st.selectbox("Role", ["Student", "Teacher"])
    bio = st.text_area("Bio")
    if st.button("Sign Up"):
        if not username.strip():
            st.error("Username cannot be empty.")
        elif not password:
            st.error("Password cannot be empty.")
        elif get_user_data(username):
            st.error("Username already taken")
        else:
            db.collection("users").document(username).set({
                "password": hash_password(password),
                "role": role,
                "bio": bio,
                "skills": [],
                "notifications": []
            })
            st.success("Account created. Please login.")

# ---------------- PROFILE EDIT ----------------
# Placeholder for main navigation
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='clearfix'></div>", unsafe_allow_html=True)
        user_msg = st.text_input("Type a message:", key="msg_input")
        if st.button("Send"):
            if user_msg.strip():
                db.collection("chats").document(chat_id).collection("messages").add({
                    "sender": username,
                    "receiver": chat_partner,
                    "text": user_msg.strip(),
                    "timestamp": datetime.now()
                })
                st.experimental_rerun()

    elif section == "Video Rooms":
        st.markdown(f"<div class='chat-header'><h4>🎥 Video Rooms</h4></div>", unsafe_allow_html=True)
        # Room UI (simplified)
        new_room = st.text_input("New Room Name")
        if st.button("Create Room"):
            room_id = new_room.strip().lower()
            db.collection("live_rooms").document(room_id).set({
                "created_by": username,
                "created_at": datetime.now(),
                "active": True
            })
            st.success(f"Room '{room_id}' created.")
        live_rooms = db.collection("live_rooms").where("active", "==", True).stream()
        for room in live_rooms:
            info = room.to_dict()
            st.markdown(f"**Room:** {room.id} by {info['created_by']}")

    elif section == "AI Booking":
        st.markdown(f"<div class='chat-header'><h4>🤖 Book AI Teacher</h4></div>", unsafe_allow_html=True)
        # Basic AI booking UI
        ai_teacher = "Gemini Teacher"
        date = st.date_input("Choose a date")
        time = st.time_input("Choose a time")
        if st.button("Book"):
            db.collection("bookings").add({
                "student": username,
                "teacher": ai_teacher,
                "datetime": datetime.combine(date, time),
                "ai": True
            })
            st.success("Session booked!")

    elif section == "Channels":
        st.markdown(f"<div class='chat-header'><h4>📢 Channels</h4></div>", unsafe_allow_html=True)
        # Channel list and simple post
        channels = db.collection("channels").stream()
        for c in channels:
            ch = c.to_dict()
            st.markdown(f"**{ch['name']}** - by {ch['created_by']}")
            if st.button(f"Follow {ch['name']}", key=f"follow_{c.id}"):
                db.collection("channels").document(c.id).update({
                    "followers": firestore.ArrayUnion([username])
                })
                st.success("Now following.")

    elif section == "Profile":
        st.markdown(f"<div class='chat-header'><h4>👤 Edit Profile</h4></div>", unsafe_allow_html=True)
        data = get_user_data(username)
        if data:
            new_bio = st.text_area("Bio", value=data.get("bio", ""))
            new_role = st.selectbox("Role", ["Student", "Teacher"], index=["Student", "Teacher"].index(data.get("role", "Student")))
            if st.button("Update Profile"):
                db.collection("users").document(username).update({"bio": new_bio, "role": new_role})
                st.success("Profile updated.")

    elif section == "Notifications":
        st.markdown(f"<div class='chat-header'><h4>🔔 Notifications</h4></div>", unsafe_allow_html=True)
        data = get_user_data(username)
        if data and data.get("notifications"):
            for note in data["notifications"]:
                st.info(note)
            if st.button("Clear All"):
                db.collection("users").document(username).update({"notifications": []})
                st.success("Cleared.")
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

def theme_toggle():
    theme = st.sidebar.checkbox("🌗 Dark Mode", value=st.session_state.dark_mode)
    st.session_state.dark_mode = theme
    if theme:
        st.markdown("<style>body{color:white; background-color:#222;} .stButton>button{color:white; background:#5c5c8a;}</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>body{color:black; background-color:#f5f5fa;} .stButton>button{color:black; background:#e0e0e0;}</style>", unsafe_allow_html=True)

# ---------------- MAIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2 = st.columns(2)
    with col1:
        login_page()
    with col2:
        signup_page()
else:
    # Header bar styled like WhatsApp
    st.markdown(f"""
        <div style='background-color:#075e54; padding:15px; color:white; border-radius:0 0 5px 5px;'>
            <h2 style='margin:0;'>🌐 SkillSwap Chat</h2>
            <span style='font-size: 14px;'>Hello, {st.session_state.username}</span>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar navigation like WhatsApp
    section = st.sidebar.radio("📂 Menu", ["💬 Chat", "🎥 Video", "🧑‍💻 Profiles", "📅 Booking", "🚪 Rooms", "👤 Profile", "🔔 Notifications"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", help="Click to log out."):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

    # Section logic (matching updated layout)
    if section == "💬 Chat":
        chat_interface()
    elif section == "🎥 Video":
        video_room_interface()
    elif section == "🧑‍💻 Profiles":
        view_profiles()
    elif section == "📅 Booking":
        booking_interface()
    elif section == "🚪 Rooms":
        channel_interface()
    elif section == "👤 Profile":
        profile_edit_sidebar()
    elif section == "🔔 Notifications":
        show_notifications()

# ---------------- FOOTER ----------------
if st.session_state.get("logged_in", False):
    st.markdown("---")
    st.caption(f"""
    ✅ Logged in as: **{st.session_state.username}**  
    📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
    🌐 SkillSwap – Inspired by WhatsApp. Peer-to-peer learning, real-time chat & AI teachers.
    """)
