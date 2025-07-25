import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# ---------------- FIREBASE SETUP ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

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
        user_ref = db.collection("users").document(username).get()
        if user_ref.exists:
            user_data = user_ref.to_dict()
            if user_data["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Logged in as {username}")
                return
        st.error("Invalid credentials.")

def signup_page():
    st.subheader("📝 Sign Up")
    username = st.text_input("New Username", key="signup_user")
    password = st.text_input("New Password", type="password", key="signup_pass")
    role = st.selectbox("Role", ["Student", "Teacher"])
    bio = st.text_area("Bio")
    if st.button("Sign Up"):
        if db.collection("users").document(username).get().exists:
            st.error("Username already taken")
        else:
            db.collection("users").document(username).set({
                "password": password,
                "role": role,
                "bio": bio
            })
            st.success("Account created. Please login.")

# ---------------- PROFILES ----------------
def view_profiles():
    st.subheader("🧑‍🏫 Browse Users")
    docs = db.collection("users").stream()
    for doc in docs:
        username = doc.id
        if username == st.session_state.username:
            continue
        data = doc.to_dict()
        with st.container():
            st.markdown(f"### 👤 {username}")
            st.markdown(f"**Role**: {data.get('role', '')}")
            st.markdown(f"**Bio**: {data.get('bio', '')}")
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
        db.collection("messages").add({
            "from": st.session_state.username,
            "to": recipient,
            "text": msg,
            "timestamp": datetime.now()
        })
        st.success("Message sent!")

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
        db.collection("bookings").add({
            "student": st.session_state.username,
            "teacher": teacher,
            "datetime": datetime.combine(date, time),
            "status": "pending"
        })
        st.success("Session booked!")

    st.markdown("### 🗓️ Your Bookings")
    bookings = db.collection("bookings") \
        .where("student", "==", st.session_state.username) \
        .order_by("datetime") \
        .stream()
    for b in bookings:
        d = b.to_dict()
        st.markdown(f"📌 With **{d['teacher']}** on {d['datetime'].strftime('%Y-%m-%d %H:%M')} (Status: {d['status']})")

# ---------------- ROOMS ----------------
def create_room_interface():
    st.subheader("🚪 Create or Join a Room")
    room_name = st.text_input("Room Name")
    if st.button("Create Room"):
        if room_name:
            room_ref = db.collection("rooms").document(room_name)
            if room_ref.get().exists:
                st.warning("Room already exists.")
            else:
                room_ref.set({
                    "created_by": st.session_state.username,
                    "created_at": datetime.now()
                })
                st.success(f"Room '{room_name}' created!")
        else:
            st.error("Please enter a room name.")

    st.markdown("### 🌍 Available Rooms")
    rooms = db.collection("rooms").stream()
    room_list = []
    for r in rooms:
        data = r.to_dict()
        room_list.append(r.id)
        st.markdown(f"- **{r.id}** (by {data.get('created_by', 'unknown')})")
    if room_list:
        selected_room = st.selectbox("Join a room", room_list)
        if st.button("Join Selected Room"):
            st.markdown(f"""
            <iframe src="https://meet.jit.si/{selected_room}" width="100%" height="500" allow="camera; microphone; fullscreen" style="border:0;"></iframe>
            """, unsafe_allow_html=True)
            st.info(f"You are in room: {selected_room}")
    else:
        st.info("No rooms available. Create one above!")

# ---------------- MAIN ----------------
st.markdown("<style>body{color:white; background-color:#222;} .stButton>button{color:white; background:#5c5c8a;}</style>", unsafe_allow_html=True)
st.title("🌐 SkillSwap Cloud")

if not st.session_state.logged_in:
    col1, col2 = st.columns(2)
    with col1:
        login_page()
    with col2:
        signup_page()
else:
    st.sidebar.success(f"👋 Hello, {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Chat", "🎥 Video", "🧑‍💻 Profiles", "📅 Booking", "🚪 Rooms"])
    with tab1:
        chat_interface()
    with tab2:
        video_interface()
    with tab3:
        view_profiles()
    with tab4:
        booking_interface()
