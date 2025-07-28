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
def profile_edit_sidebar():
    user_data = get_user_data(st.session_state.username)
    if user_data:
        st.sidebar.header("Edit Profile")
        new_bio = st.sidebar.text_area("Bio", value=user_data.get("bio", ""))
        new_role = st.sidebar.selectbox("Role", ["Student", "Teacher"], index=["Student", "Teacher"].index(user_data.get("role", "Student")))
        if st.sidebar.button("Update Profile"):
            db.collection("users").document(st.session_state.username).update({"bio": new_bio, "role": new_role})
            st.sidebar.success("Profile updated!")

        st.sidebar.header("Your Skills")
        skills = st.sidebar.text_area("Skills (comma separated)", value=", ".join(user_data.get("skills", [])))
        if st.sidebar.button("Update Skills"):
            skill_list = [s.strip() for s in skills.split(",") if s.strip()]
            db.collection("users").document(st.session_state.username).update({"skills": skill_list})
            st.sidebar.success("Skills updated!")

# ---------------- PROFILES ----------------
def view_profiles():
    st.subheader("🧑‍🏫 Browse Users")
    search = st.text_input("Search by skill or role")
    docs = db.collection("users").stream()
    for doc in docs:
        username = doc.id
        if username == st.session_state.username:
            continue
        data = doc.to_dict()
        show = True
        if search:
            if search.lower() not in data.get("role", "").lower() and \
               not any(search.lower() in skill.lower() for skill in data.get("skills", [])):
                show = False
        if show:
            with st.container():
                st.markdown(f"### 👤 {username}")
                st.markdown(f"**Role**: {data.get('role', '')}")
                st.markdown(f"**Bio**: {data.get('bio', '')}")
                st.markdown(f"**Skills**: {', '.join(data.get('skills', []))}")
                st.markdown("---")

# ---------------- CHAT ----------------
def chat_interface():
    st.subheader("💬 Cloud Chat")
    users = [doc.id for doc in db.collection("users").stream()]
    other_users = [u for u in users if u != st.session_state.username]
    if not other_users:
        st.info("No other users to chat with.")
        return
    recipient = st.selectbox("Chat with", other_users)
    msg = st.text_input("Type your message")
    if st.button("Send"):
        try:
            db.collection("messages").add({
                "from": st.session_state.username,
                "to": recipient,
                "text": msg,
                "timestamp": datetime.now()
            })
            st.success("Message sent!")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("### 📥 Your Inbox")
    inbox = db.collection("messages") \
        .where("to", "==", st.session_state.username) \
        .order_by("timestamp", direction=firestore.Query.DESCENDING) \
        .stream()
    for m in inbox:
        d = m.to_dict()
        time_str = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"**From {d['from']}** ({time_str}): {d['text']}")

# ---------------- VIDEO ----------------
def video_room_interface():
    st.subheader("🎥 Create or Join a Video Room")

    # ---------------- CREATE ROOM ----------------
    new_room_name = st.text_input("Create New Room (give it a name):", key="create_room_input")
    if st.button("Create Room"):
        if new_room_name:
            room_id = new_room_name.strip().lower()
            room_ref = db.collection("live_rooms").document(room_id)
            if room_ref.get().exists:
                st.warning("Room already exists.")
            else:
                room_ref.set({
                    "created_by": st.session_state.username,
                    "created_at": datetime.now(),
                    "active": True
                })
                st.session_state["current_room"] = room_id
                st.success(f"Room '{room_id}' created. You're now live!")

    # ---------------- SHOW LIVE ROOMS ----------------
    st.markdown("### 🌐 Available Live Rooms")
    live_rooms = db.collection("live_rooms").where("active", "==", True).stream()
    room_list = []
    for room in live_rooms:
        room_data = room.to_dict()
        room_list.append(room.id)
        st.markdown(f"- **{room.id}** (hosted by {room_data.get('created_by', 'Unknown')})")

    # ---------------- JOIN ROOM ----------------
    selected_room = st.selectbox("Join a Live Room", room_list, key="join_room_select")
    if st.button("Join Room"):
        st.session_state["current_room"] = selected_room
        st.success(f"You joined room '{selected_room}'")

    # ---------------- VIDEO CALL IFRAME ----------------
    if "current_room" in st.session_state:
        room = st.session_state["current_room"]
        st.markdown(f"### ✅ You are in: **{room}**")
        st.markdown(f"""
        <iframe
            src="https://meet.jit.si/{room}#userInfo.displayName='{st.session_state.username}'"
            style="height: 600px; width: 100%; border: 0px;"
            allow="camera; microphone; fullscreen; display-capture"
        ></iframe>
        """, unsafe_allow_html=True)

        if st.button("Leave Room"):
            if db.collection("live_rooms").document(room).get().to_dict().get("created_by") == st.session_state.username:
                db.collection("live_rooms").document(room).update({"active": False})
            del st.session_state["current_room"]
            st.success("You left the room.")


# ---------------- BOOKING (AI ONLY) ----------------
def booking_interface():
    st.subheader("📅 Book an AI Teacher")
    ai_names = [f"{ai['name']} ({ai['skill']})" for ai in AI_TEACHERS]
    ai_choice = st.selectbox("Choose an AI Teacher", ai_names)
    ai_teacher = AI_TEACHERS[ai_names.index(ai_choice)]

    st.image(ai_teacher["avatar"], width=80)
    st.markdown(f"**{ai_teacher['name']}** — *{ai_teacher['skill']}*  \n{ai_teacher['bio']}")

    date = st.date_input("Date")
    time = st.time_input("Time")

    if st.button("Book Session"):
        db.collection("bookings").add({
            "student": st.session_state.username,
            "teacher": ai_teacher["name"],
            "skill": ai_teacher["skill"],
            "datetime": datetime.combine(date, time),
            "status": "confirmed",
            "ai": True
        })
        st.success(f"Session booked with {ai_teacher['name']}!")
        st.session_state["last_ai_teacher"] = ai_teacher

    st.markdown("### 🗓️ Your AI Bookings")
    bookings = db.collection("bookings") \
        .where("student", "==", st.session_state.username) \
        .where("ai", "==", True) \
        .order_by("datetime") \
        .stream()

    for b in bookings:
        d = b.to_dict()
        dt = d.get("datetime")
        if dt:
            st.markdown(f"🤖 **{d['teacher']}** ({d['skill']}) on {dt.strftime('%Y-%m-%d %H:%M')} (Status: {d['status']})")
            if st.button(f"Chat with {d['teacher']} ({dt.strftime('%Y-%m-%d %H:%M')})", key=f"chat_{d['teacher']}_{dt}"):
                st.session_state["active_ai_teacher"] = d['teacher']
                st.session_state["active_ai_skill"] = d['skill']
                st.session_state["active_ai_avatar"] = next(ai["avatar"] for ai in AI_TEACHERS if ai["name"] == d["teacher"])
                st.session_state["ai_chat_history"] = []

    # ---------------- REAL-TIME GEMINI AI CHAT ----------------
    if "active_ai_teacher" in st.session_state:
        ai_teacher_name = st.session_state["active_ai_teacher"]
        ai_skill = st.session_state["active_ai_skill"]
        ai_avatar = st.session_state["active_ai_avatar"]
        chat_id = f"{st.session_state.username}_{ai_teacher_name}"

        st.markdown(f"### 🤖 Chat with {ai_teacher_name} ({ai_skill})")
        st.image(ai_avatar, width=60)

        # Load chat history from Firestore
        messages_ref = db.collection("ai_chats").document(chat_id).collection("messages").order_by("timestamp")
        history = messages_ref.stream()

        st.session_state["ai_chat_history"] = []
        for h in history:
            d = h.to_dict()
            st.session_state["ai_chat_history"].append({"sender": d["sender"], "text": d["text"]})

        # Display chat bubbles
        for msg in st.session_state["ai_chat_history"]:
            is_user = msg["sender"] == "user"
            bubble_color = "#4CAF50" if is_user else "#444"
            align = "right" if is_user else "left"
            st.markdown(f"""
            <div style="background-color:{bubble_color}; color:white; padding:8px 12px;
                        border-radius:12px; margin:4px 0; max-width:70%; float:{align}; clear:both;">
                <b>{'You' if is_user else ai_teacher_name}:</b><br>{msg['text']}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='clear:both'></div>", unsafe_allow_html=True)

        # User input
        user_msg = st.text_input("Your message", key=f"ai_chat_input_{ai_teacher_name}")

        if st.button("Send to AI", key=f"send_{ai_teacher_name}"):
            if user_msg.strip():
                # Save user message
                db.collection("ai_chats").document(chat_id).collection("messages").add({
                    "sender": "user",
                    "text": user_msg,
                    "timestamp": datetime.now()
                })

                try:
                    # Configure Gemini with full model name
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel("gemini-1.5-pro-latest")

                    # Prepare chat history
                    gemini_history = [
                        {"role": "user", "parts": [m["text"]]} if m["sender"] == "user"
                        else {"role": "model", "parts": [m["text"]]}
                        for m in st.session_state["ai_chat_history"]
                    ]

                    chat = model.start_chat(history=gemini_history)
                    response = chat.send_message(user_msg)
                    gemini_response = response.text

                    # Save AI reply
                    db.collection("ai_chats").document(chat_id).collection("messages").add({
                        "sender": "ai",
                        "text": gemini_response,
                        "timestamp": datetime.now()
                    })

                    st.experimental_rerun()

                except Exception as e:
                    error_msg = str(e)
                    if "quota" in error_msg.lower() or "429" in error_msg:
                        st.warning("⚠️ AI is temporarily unavailable due to usage limits. Please try again in a few minutes.")
                    else:
                        st.warning("⚠️ AI is currently unavailable. Please try again later.")





# ---------------- ROOMS ----------------
def channel_interface():
    st.subheader("📢 Create or Join a Channel (WhatsApp Style)")
    channel_name = st.text_input("Channel Name")
    channel_desc = st.text_area("Channel Description")

    if st.button("Create Channel"):
        if channel_name:
            channel_id = channel_name.strip().lower()
            channel_ref = db.collection("channels").document(channel_id)
            if channel_ref.get().exists:
                st.warning("Channel already exists.")
            else:
                try:
                    channel_ref.set({
                        "name": channel_name,
                        "description": channel_desc,
                        "created_by": st.session_state.username,
                        "created_at": datetime.now(),
                        "followers": [st.session_state.username]
                    })
                    st.success(f"Channel '{channel_name}' created!")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("Please enter a channel name.")

    st.markdown("### 🔍 Browse Channels")
    channels = db.collection("channels").stream()
    available_channels = []
    for c in channels:
        data = c.to_dict()
        available_channels.append(c.id)
        st.markdown(f"**{data['name']}** — {data.get('description', '')}")

    if available_channels:
        selected_channel = st.selectbox("Select a channel to follow/view", available_channels)
        channel_ref = db.collection("channels").document(selected_channel)
        channel_doc = channel_ref.get()
        if channel_doc.exists:
            data = channel_doc.to_dict()
            st.info(f"Channel by: {data['created_by']}")
            st.markdown(f"### 📄 Description\n{data.get('description', 'No description')}")

            # Follow channel
            if st.session_state.username not in data.get("followers", []):
                if st.button("Follow Channel"):
                    channel_ref.update({"followers": firestore.ArrayUnion([st.session_state.username])})
                    st.success("You are now following this channel.")

            # Creator can post messages
            if st.session_state.username == data.get("created_by"):
                message = st.text_input("Post a message to followers")
                if st.button("Send Broadcast") and message.strip():
                    db.collection("channels").document(selected_channel).collection("messages").add({
                        "text": message.strip(),
                        "timestamp": datetime.now()
                    })
                    st.success("Message sent!")

            # Show messages
            st.markdown("### 💬 Channel Messages")
            messages = db.collection("channels").document(selected_channel).collection("messages").order_by("timestamp").stream()
            for msg in messages:
                d = msg.to_dict()
                ts = d['timestamp'].strftime('%Y-%m-%d %H:%M')
                st.markdown(f"🕒 **{ts}**: {d['text']}")
    else:
        st.info("No channels yet. Create one above!")




# ---------------- NOTIFICATIONS ----------------
def show_notifications():
    user_data = get_user_data(st.session_state.username)
    notifications = user_data.get("notifications", []) if user_data else []
    if notifications:
        st.sidebar.header("🔔 Notifications")
        for note in notifications:
            st.sidebar.info(note)
        if st.sidebar.button("Clear Notifications"):
            db.collection("users").document(st.session_state.username).update({"notifications": []})

# ---------------- THEME TOGGLE ----------------
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
theme_toggle()
st.title("🌐 SkillSwap Cloud")

if not st.session_state.logged_in:
    col1, col2 = st.columns(2)
    with col1:
        login_page()
    with col2:
        signup_page()
else:
    show_notifications()
    profile_edit_sidebar()
    st.sidebar.success(f"👋 Hello, {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat",
        "🎥 Video",
        "🧑‍💻 Profiles",
        "📅 Booking",
        "🚪 Rooms"
    ])
    with tab1:
        chat_interface()
    with tab2:
        video_interface()
    with tab3:
        view_profiles()
    with tab4:
        booking_interface()
    with tab5:
        channel_interface()

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption(f"""
✅ Logged in as: **{st.session_state.username}**  
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
🌐 SkillSwap Cloud – Connecting learners and teachers worldwide.
""")
