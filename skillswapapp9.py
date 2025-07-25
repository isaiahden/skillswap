import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import hashlib

# ---------------- FIREBASE SETUP ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- UTILS ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_data(username):
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
        if get_user_data(username):
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
def video_interface():
    st.subheader("🎥 Video Call Room")
    room = f"{st.session_state.username}-room"
    st.markdown(f"""
    <iframe src="https://meet.jit.si/{room}" width="100%" height="500" allow="camera; microphone; fullscreen" style="border:0;"></iframe>
    """, unsafe_allow_html=True)
    st.info("Others can join this room by entering the same room name.")

# ---------------- BOOKING ----------------
def booking_interface():
    st.subheader("📅 Schedule a Session")
    users = [doc.id for doc in db.collection("users").stream() if doc.id != st.session_state.username]
    teacher = st.selectbox("Choose a teacher", users)
    date = st.date_input("Date")
    time = st.time_input("Time")
    if st.button("Book Session"):
        try:
            db.collection("bookings").add({
                "student": st.session_state.username,
                "teacher": teacher,
                "datetime": datetime.combine(date, time),
                "status": "pending"
            })
            # Notify teacher
            db.collection("users").document(teacher).update({
                "notifications": firestore.ArrayUnion([f"New booking from {st.session_state.username} on {date} at {time}"])
            })
            st.success("Session booked!")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("### 🗓️ Your Bookings as Student")
    bookings = db.collection("bookings") \
        .where("student", "==", st.session_state.username) \
        .order_by("datetime") \
        .stream()
    for b in bookings:
        d = b.to_dict()
        st.markdown(f"📌 With **{d['teacher']}** on {d['datetime'].strftime('%Y-%m-%d %H:%M')} (Status: {d['status']})")

    st.markdown("### 🗓️ Your Bookings as Teacher")
    bookings_teacher = db.collection("bookings") \
        .where("teacher", "==", st.session_state.username) \
        .order_by("datetime") \
        .stream()
    for b in bookings_teacher:
        d = b.to_dict()
        st.markdown(f"📌 With **{d['student']}** on {d['datetime'].strftime('%Y-%m-%d %H:%M')} (Status: {d['status']})")

# ---------------- ROOMS ----------------
def create_room_interface():
    st.subheader("🚪 Create or Join a Room")
    room_name = st.text_input("Room Name")
    if st.button("Create Room"):
        if room_name:
            room_name_clean = room_name.strip().lower()
            room_ref = db.collection("rooms").document(room_name_clean)
            if room_ref.get().exists:
                st.warning("Room already exists.")
            else:
                try:
                    room_ref.set({
                        "created_by": st.session_state.username,
                        "created_at": datetime.now(),
                        "participants": [st.session_state.username]
                    })
                    st.success(f"Room '{room_name_clean}' created!")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("Please enter a room name.")

    st.markdown("### 🌍 Available Rooms")
    rooms = db.collection("rooms").stream()
    room_list = []
    for r in rooms:
        data = r.to_dict()
        room_list.append(r.id)
        st.markdown(f"- **{r.id}** (by {data.get('created_by', 'unknown')}) | Participants: {', '.join(data.get('participants', []))}")
    if room_list:
        selected_room = st.selectbox("Join a room", room_list)
        if st.button("Join Selected Room"):
            room_ref = db.collection("rooms").document(selected_room)
            room_ref.update({"participants": firestore.ArrayUnion([st.session_state.username])})
            room_doc = room_ref.get()
            participants = room_doc.to_dict().get("participants", [])
            st.markdown(f"**Participants:** {', '.join(participants)}")
            st.markdown(f"""
            <iframe src="https://meet.jit.si/{selected_room}" width="100%" height="500" allow="camera; microphone; fullscreen" style="border:0;"></iframe>
            """, unsafe_allow_html=True)
            st.info(f"You are in room: {selected_room}")
        # Room deletion for creator
        room_ref = db.collection("rooms").document(selected_room)
        room_doc = room_ref.get()
        if room_doc.exists and room_doc.to_dict().get("created_by") == st.session_state.username:
            if st.button("Delete Room"):
                room_ref.delete()
                st.success("Room deleted. Please refresh.")
    else:
        st.info("No rooms available. Create one above!")

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
        st.rerun()

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
        create_room_interface()

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption(f"""
✅ Logged in as: **{st.session_state.username}**  
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
🌐 SkillSwap Cloud – Connecting learners and teachers worldwide.
""")
