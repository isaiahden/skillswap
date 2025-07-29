import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth
import json
import google.generativeai as genai
from gtts import gTTS
import base64
import smtplib
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import hashlib
import os
            
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

# === STREAMLIT NATIVE STYLING ===
st.markdown("""
<style>
/* Keep Streamlit's native styling with minimal enhancements */
.main > div {
    padding-top: 2rem;
}

/* Enhance cards with subtle styling */
.user-card {
    padding: 1.5rem;
    border-radius: 0.5rem;
    border: 1px solid #e1e5e9;
    margin-bottom: 1rem;
    background-color: #ffffff;
}

.ai-teacher-card {
    padding: 1.5rem;
    border-radius: 0.5rem;
    border: 1px solid #e1e5e9;
    margin-bottom: 1rem;
    background-color: #f8f9fa;
}

/* Chat message styling - keeping it simple */
.chat-message {
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    border-radius: 0.5rem;
    border-left: 4px solid #0066cc;
    background-color: #f0f2f6;
}

.chat-message.sent {
    border-left: 4px solid #28a745;
    background-color: #d4edda;
    margin-left: 2rem;
}

/* Status badges */
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.875rem;
    font-weight: 500;
}

.status-online {
    background-color: #d4edda;
    color: #155724;
}

.status-offline {
    background-color: #f8d7da;
    color: #721c24;
}
</style>
""", unsafe_allow_html=True)

# === SESSION SETUP ===
st.set_page_config(
    page_title="SkillSwap Cloud", 
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_data(username):
    if not username.strip(): return None
    doc = db.collection("users").document(username).get()
    return doc.to_dict() if doc.exists else None

def generate_otp():
    return str(random.randint(100000, 999999))

def send_email_otp(receiver_email, otp_code):
    sender_email = st.secrets["EMAIL_SENDER"]
    sender_password = st.secrets["EMAIL_PASSWORD"]

    msg = MIMEText(f"Your SkillSwap verification code is: {otp_code}")
    msg['Subject'] = "SkillSwap OTP Verification"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send OTP: {e}")
        return False

def send_password_reset_otp(email):
    users = db.collection("users").stream()
    for user in users:
        data = user.to_dict()
        if data.get("email") == email:
            otp = generate_otp()
            db.collection("reset_otps").document(email).set({
                "code": otp,
                "timestamp": datetime.utcnow().isoformat()
            })
            return send_email_otp(email, otp)
    st.error("Email not found.")
    return False

def verify_reset_otp(email, entered_code):
    doc = db.collection("reset_otps").document(email).get()
    if doc.exists:
        data = doc.to_dict()
        timestamp = datetime.fromisoformat(data["timestamp"])
        if (datetime.utcnow() - timestamp).total_seconds() > 600:
            st.error("Code expired.")
            return False
        if entered_code == data["code"]:
            db.collection("reset_otps").document(email).delete()
            return True
        st.error("Incorrect code.")
    else:
        st.error("No OTP request found.")
    return False

# === AUTHENTICATION PAGES ===
def login_page():
    st.title("🔐 Login to SkillSwap")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("Please fill in all fields.")
                return
                
            user_data = get_user_data(username)
            if user_data and user_data.get("password") == hash_password(password):
                if not user_data.get("verified"):
                    st.warning("⚠️ Please verify your email before logging in.")
                    return
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome back, {username}! 🎉")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

def signup_page():
    st.title("📝 Create Your SkillSwap Account")
    
    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username", placeholder="Choose a unique username")
        with col2:
            email = st.text_input("Email", placeholder="your.email@example.com")
        
        password = st.text_input("Password", type="password", placeholder="Create a strong password")
        submitted = st.form_submit_button("Create Account", use_container_width=True)
        
        if submitted:
            if not username or not email or not password:
                st.error("Please fill in all fields.")
                return
            
            if get_user_data(username):
                st.error("❌ Username already exists. Please choose another.")
                return
            
            # Send verification code
            now = datetime.utcnow()
            code = generate_otp()
            if send_email_otp(email, code):
                db.collection("email_verifications").document(username).set({
                    "email": email,
                    "code": code,
                    "password": hash_password(password),
                    "verified": False,
                    "timestamp": now.isoformat()
                })
                st.session_state.signup_user = username
                st.success("📧 Verification code sent to your email!")
    
    # Verification section
    if "signup_user" in st.session_state:
        st.info(f"📝 Verify your account: **{st.session_state.signup_user}**")
        
        with st.form("verification_form"):
            verification_code = st.text_input("Verification Code", placeholder="Enter 6-digit code")
            verify_submitted = st.form_submit_button("Verify Account", use_container_width=True)
            
            if verify_submitted:
                doc = db.collection("email_verifications").document(st.session_state.signup_user).get()
                if doc.exists:
                    data = doc.to_dict()
                    if verification_code == data.get("code"):
                        # Create verified user account
                        db.collection("users").document(st.session_state.signup_user).set({
                            "email": data["email"],
                            "password": data["password"],
                            "verified": True,
                            "role": "Student",
                            "bio": "",
                            "skills": [],
                            "notifications": []
                        })
                        db.collection("email_verifications").document(st.session_state.signup_user).delete()
                        st.success("✅ Account created successfully! You can now login.")
                        del st.session_state.signup_user
                    else:
                        st.error("❌ Incorrect verification code.")

def password_reset():
    st.title("🔑 Reset Your Password")
    
    step = st.session_state.get("reset_step", "request")
    
    if step == "request":
        st.subheader("Step 1: Enter your email")
        with st.form("reset_request_form"):
            email = st.text_input("Email Address", placeholder="Enter your registered email")
            submitted = st.form_submit_button("Send Reset Code", use_container_width=True)
            
            if submitted:
                if send_password_reset_otp(email):
                    st.session_state.reset_email = email
                    st.session_state.reset_step = "verify"
                    st.rerun()
    
    elif step == "verify":
        st.subheader("Step 2: Enter verification code")
        st.info(f"Code sent to: **{st.session_state.reset_email}**")
        
        with st.form("reset_verify_form"):
            code = st.text_input("Verification Code", placeholder="Enter 6-digit code")
            submitted = st.form_submit_button("Verify Code", use_container_width=True)
            
            if submitted:
                if verify_reset_otp(st.session_state.reset_email, code.strip()):
                    st.session_state.reset_step = "set_password"
                    st.rerun()
    
    elif step == "set_password":
        st.subheader("Step 3: Set new password")
        with st.form("reset_password_form"):
            new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
            submitted = st.form_submit_button("Update Password", use_container_width=True)
            
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords don't match.")
                    return
                
                users = db.collection("users").stream()
                for user in users:
                    data = user.to_dict()
                    if data.get("email") == st.session_state.reset_email:
                        db.collection("users").document(user.id).update({
                            "password": hash_password(new_password)
                        })
                        st.success("✅ Password updated successfully! You can now login.")
                        del st.session_state.reset_email
                        st.session_state.reset_step = "request"
                        break

# === MAIN APP FUNCTIONS ===
def profile_edit():
    st.header("👤 Your Profile")
    
    user_data = get_user_data(st.session_state.username)
    if not user_data:
        st.error("Unable to load profile data.")
        return
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            bio = st.text_area("Bio", value=user_data.get("bio", ""), placeholder="Tell others about yourself...")
            role = st.selectbox(
                "Role", 
                ["Student", "Teacher"],
                index=["Student", "Teacher"].index(user_data.get("role", "Student"))
            )
        
        with col2:
            current_skills = user_data.get("skills", [])
            skills_text = st.text_area(
                "Skills (one per line)", 
                value="\n".join(current_skills),
                placeholder="Python\nGraphic Design\nFrench Language"
            )
        
        if st.form_submit_button("Update Profile", use_container_width=True):
            new_skills = [skill.strip() for skill in skills_text.split('\n') if skill.strip()]
            
            db.collection("users").document(st.session_state.username).update({
                "bio": bio,
                "role": role,
                "skills": new_skills
            })
            st.success("✅ Profile updated successfully!")
            st.rerun()
    
    # Display current profile
    st.subheader("Current Profile")
    st.info(f"**Username:** {st.session_state.username}")
    st.info(f"**Email:** {user_data.get('email', 'N/A')}")
    st.info(f"**Role:** {user_data.get('role', 'Student')}")
    
    if user_data.get('skills'):
        st.info(f"**Skills:** {', '.join(user_data['skills'])}")

def show_notifications():
    st.header("🔔 Notifications")
    
    user_data = get_user_data(st.session_state.username)
    if not user_data:
        return
    
    notifications = user_data.get("notifications", [])
    
    if not notifications:
        st.info("📭 No new notifications")
        return
    
    st.subheader(f"You have {len(notifications)} notifications")
    
    for i, notification in enumerate(notifications):
        with st.container():
            st.markdown(f"**{i+1}.** {notification}")
    
    if st.button("Clear All Notifications", use_container_width=True):
        db.collection("users").document(st.session_state.username).update({"notifications": []})
        st.success("✅ All notifications cleared!")
        st.rerun()

def chat_interface():
    st.header("💬 Chat with Users")
    
    # Get all users except current user
    users = []
    for doc in db.collection("users").stream():
        if doc.id != st.session_state.username:
            user_data = doc.to_dict()
            users.append({
                "username": doc.id,
                "role": user_data.get("role", "Student"),
                "skills": user_data.get("skills", [])
            })
    
    if not users:
        st.info("No other users available for chat.")
        return
    
    # Partner selection
    partner_options = [f"{user['username']} ({user['role']})" for user in users]
    selected_partner = st.selectbox("Select a chat partner:", partner_options)
    
    if not selected_partner:
        return
    
    partner_username = selected_partner.split(" (")[0]
    
    # Display partner info
    partner_info = next(user for user in users if user['username'] == partner_username)
    st.info(f"💬 Chatting with **{partner_username}** ({partner_info['role']})")
    
    # Chat messages
    chat_id = "_".join(sorted([st.session_state.username, partner_username]))
    
    st.subheader("Messages")
    
    # Display chat history
    try:
        messages = db.collection("chats").document(chat_id).collection("messages").order_by("timestamp").stream()
        
        chat_container = st.container()
        with chat_container:
            for msg in messages:
                msg_data = msg.to_dict()
                is_sent = msg_data["sender"] == st.session_state.username
                sender_name = "You" if is_sent else msg_data["sender"]
                
                css_class = "sent" if is_sent else ""
                st.markdown(f"""
                <div class="chat-message {css_class}">
                    <strong>{sender_name}:</strong> {msg_data['text']}<br>
                    <small>{msg_data['timestamp'].strftime('%H:%M - %d/%m/%Y')}</small>
                </div>
                """, unsafe_allow_html=True)
        
    except Exception as e:
        st.info("No messages yet. Start the conversation!")
    
    # Message input
    with st.form("message_form"):
        col1, col2 = st.columns([4, 1])
        with col1:
            message_text = st.text_input("Type your message...", placeholder="Enter your message here")
        with col2:
            send_clicked = st.form_submit_button("Send")
        
        if send_clicked and message_text.strip():
            db.collection("chats").document(chat_id).collection("messages").add({
                "sender": st.session_state.username,
                "receiver": partner_username,
                "text": message_text.strip(),
                "timestamp": datetime.now()
            })
            st.rerun()

def view_profiles():
    st.header("🧑‍🏫 Browse User Profiles")
    
    # Search and filter
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("🔍 Search by skill or username", placeholder="e.g., Python, Design")
    with col2:
        role_filter = st.selectbox("Filter by role", ["All", "Student", "Teacher"])
    
    # Get all users
    users = []
    for doc in db.collection("users").stream():
        if doc.id != st.session_state.username:
            user_data = doc.to_dict()
            users.append({
                "username": doc.id,
                "role": user_data.get("role", "Student"),
                "bio": user_data.get("bio", ""),
                "skills": user_data.get("skills", [])
            })
    
    # Apply filters
    filtered_users = []
    for user in users:
        # Role filter
        if role_filter != "All" and user["role"] != role_filter:
            continue
        
        # Search filter
        if search_term:
            search_lower = search_term.lower()
            if (search_lower not in user["username"].lower() and 
                search_lower not in user["bio"].lower() and
                not any(search_lower in skill.lower() for skill in user["skills"])):
                continue
        
        filtered_users.append(user)
    
    # Display results
    st.subheader(f"Found {len(filtered_users)} users")
    
    if not filtered_users:
        st.info("No users match your search criteria.")
        return
    
    # Display users in cards
    for user in filtered_users:
        with st.container():
            st.markdown(f"""
            <div class="user-card">
                <h4>👤 {user['username']}</h4>
                <p><strong>Role:</strong> <span class="status-badge status-online">{user['role']}</span></p>
                <p><strong>Bio:</strong> {user['bio'] or 'No bio available'}</p>
                <p><strong>Skills:</strong> {', '.join(user['skills']) if user['skills'] else 'No skills listed'}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Start Chat with {user['username']}", key=f"chat_{user['username']}"):
                st.session_state.selected_chat_partner = user['username']
                st.switch_page("chat")  # This would switch to chat tab if using multipage

def booking_interface():
    st.header("🤖 AI Teacher Booking")
    
    # Display available AI teachers
    st.subheader("Available AI Teachers")
    
    for ai in AI_TEACHERS:
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                st.image(ai["avatar"], width=80)
            
            with col2:
                st.markdown(f"""
                <div class="ai-teacher-card">
                    <h4>{ai['name']}</h4>
                    <p><strong>Specialty:</strong> {ai['skill']}</p>
                    <p>{ai['bio']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                if st.button(f"Book {ai['name']}", key=f"book_{ai['name']}"):
                    st.session_state.selected_ai = ai
                    st.session_state.show_booking_form = True
    
    # Booking form
    if st.session_state.get("show_booking_form") and st.session_state.get("selected_ai"):
        ai = st.session_state.selected_ai
        
        st.subheader(f"📅 Book Session with {ai['name']}")
        
        with st.form("booking_form"):
            col1, col2 = st.columns(2)
            with col1:
                session_date = st.date_input("Select Date", min_value=datetime.now().date())
            with col2:
                session_time = st.time_input("Select Time")
            
            notes = st.text_area("Session Notes (Optional)", placeholder="What would you like to learn?")
            
            if st.form_submit_button("Confirm Booking", use_container_width=True):
                booking_data = {
                    "student": st.session_state.username,
                    "teacher": ai["name"],
                    "skill": ai["skill"],
                    "datetime": datetime.combine(session_date, session_time),
                    "status": "confirmed",
                    "ai": True,
                    "notes": notes
                }
                
                db.collection("bookings").add(booking_data)
                
                st.success(f"✅ Session booked with {ai['name']} on {session_date} at {session_time}")
                st.session_state.active_ai_teacher = ai["name"]
                st.session_state.active_ai_skill = ai["skill"]
                st.session_state.show_booking_form = False
                st.rerun()
    
    # AI Chat Section
    if st.session_state.get("active_ai_teacher"):
        st.markdown("---")
        st.subheader(f"💬 Chat with {st.session_state.active_ai_teacher}")
        
        chat_id = f"{st.session_state.username}_{st.session_state.active_ai_teacher}"
        
        # Display chat history
        try:
            messages = db.collection("ai_chats").document(chat_id).collection("messages").order_by("timestamp").stream()
            
            for msg in messages:
                msg_data = msg.to_dict()
                is_user = msg_data["sender"] == "user"
                sender_name = "You" if is_user else st.session_state.active_ai_teacher
                
                css_class = "sent" if is_user else ""
                st.markdown(f"""
                <div class="chat-message {css_class}">
                    <strong>{sender_name}:</strong> {msg_data['text']}
                </div>
                """, unsafe_allow_html=True)
        
        except Exception:
            st.info("Start your conversation with the AI teacher!")
        
        # Message input
        with st.form("ai_message_form"):
            user_message = st.text_input("Ask your AI teacher...", placeholder="Type your question or message")
            if st.form_submit_button("Send", use_container_width=True):
                if user_message.strip():
                    # Save user message
                    db.collection("ai_chats").document(chat_id).collection("messages").add({
                        "sender": "user",
                        "text": user_message.strip(),
                        "timestamp": datetime.now()
                    })
                    
                    # Generate AI response
                    try:
                        model = genai.GenerativeModel("gemini-1.5-pro-latest")
                        prompt = f"You are {st.session_state.active_ai_teacher}, an expert in {st.session_state.active_ai_skill}. Respond helpfully to this student question: {user_message}"
                        response = model.generate_content(prompt)
                        
                        # Save AI response
                        db.collection("ai_chats").document(chat_id).collection("messages").add({
                            "sender": "ai",
                            "text": response.text,
                            "timestamp": datetime.now()
                        })
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"AI Error: {str(e)}")
    
    # Display user's bookings
    st.markdown("---")
    st.subheader("📋 Your Bookings")
    
    bookings = db.collection("bookings").where("student", "==", st.session_state.username).stream()
    booking_list = []
    
    for booking in bookings:
        booking_data = booking.to_dict()
        booking_list.append(booking_data)
    
    if booking_list:
        for i, booking in enumerate(booking_list):
            status_color = "status-online" if booking["status"] == "confirmed" else "status-offline"
            st.markdown(f"""
            **{booking['teacher']}** - {booking['skill']}<br>
            📅 {booking['datetime'].strftime('%Y-%m-%d %H:%M')}<br>
            <span class="status-badge {status_color}">{booking['status'].upper()}</span>
            """, unsafe_allow_html=True)
            st.markdown("---")
    else:
        st.info("No bookings yet. Book your first AI teacher session!")

def channel_interface():
    st.header("📢 SkillSwap Community Channels")
    
    # Create new channel
    with st.expander("➕ Create New Channel"):
        with st.form("create_channel_form"):
            channel_name = st.text_input("Channel Name", placeholder="e.g., Python Beginners")
            channel_description = st.text_area("Description", placeholder="What's this channel about?")
            
            if st.form_submit_button("Create Channel"):
                if channel_name.strip():
                    channel_id = channel_name.lower().replace(" ", "_")
                    db.collection("channels").document(channel_id).set({
                        "name": channel_name,
                        "description": channel_description,
                        "created_by": st.session_state.username,
                        "created_at": datetime.now(),
                        "followers": [st.session_state.username]
                    })
                    st.success(f"✅ Channel '{channel_name}' created!")
                    st.rerun()
    
    # Display existing channels
    st.subheader("Available Channels")
    
    channels = []
    for doc in db.collection("channels").stream():
        channel_data = doc.to_dict()
        channel_data["id"] = doc.id
        channels.append(channel_data)
    
    if not channels:
        st.info("No channels available. Create the first one!")
        return
    
    for channel in channels:
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                **📢 {channel['name']}**<br>
                *Created by {channel['created_by']}*<br>
                {channel.get('description', 'No description')}
                """)
                
                followers = channel.get('followers', [])
                st.caption(f"👥 {len(followers)} followers")
            
            with col2:
                is_following = st.session_state.username in channel.get('followers', [])
                
                if is_following:
                    if st.button("Unfollow", key=f"unfollow_{channel['id']}"):
                        db.collection("channels").document(channel['id']).update({
                            "followers": firestore.ArrayRemove([st.session_state.username])
                        })
                        st.rerun()
                else:
                    if st.button("Follow", key=f"follow_{channel['id']}"):
                        db.collection("channels").document(channel['id']).update({
                            "followers": firestore.ArrayUnion([st.session_state.username])
                        })
                        st.success(f"Now following {channel['name']}!")
                        st.rerun()
            
            st.markdown("---")

# === MAIN APPLICATION ===
def main():
    if not st.session_state.logged_in:
        # Authentication pages
        st.title("🌐 Welcome to SkillSwap Cloud")
        st.markdown("**Connect, Learn, and Grow with Peer-to-Peer Learning**")
        
        tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Sign Up", "🔑 Reset Password"])
        
        with tab1:
            login_page()
        
        with tab2:
            signup_page()
        
        with tab3:
            password_reset()
    
    else:
        # Main application
        st.title("🌐 SkillSwap Cloud")
        st.markdown(f"Welcome back, **{st.session_state.username}**! 👋")
        
        # Sidebar navigation
        with st.sidebar:
            st.header("📂 Navigation")
            
            # Display user info
            user_data = get_user_data(st.session_state.username)
            if user_data:
                st.info(f"**{st.session_state.username}**\n\n{user_data.get('role', 'Student')}")
                
                # Show notifications count
                notifications_count = len(user_data.get('notifications', []))
                if notifications_count > 0:
                    st.warning(f"🔔 {notifications_count} new notifications")
            
            # Navigation menu
            page = st.radio(
                "Choose a section:",
                [
                    "💬 Chat",
                    "🧑‍💻 Browse Profiles", 
                    "🤖 AI Teachers",
                    "📢 Channels",
                    "👤 Profile",
                    "🔔 Notifications"
                ]
            )
            
            st.markdown("---")
            
            # Logout button
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                # Clear other session state variables
                for key in list(st.session_state.keys()):
                    if key.startswith(('selected_', 'active_', 'show_', 'reset_')):
                        del st.session_state[key]
                st.rerun()
        
        # Main content area
        if page == "💬 Chat":
            chat_interface()
        elif page == "🧑‍💻 Browse Profiles":
            view_profiles()
        elif page == "🤖 AI Teachers":
            booking_interface()
        elif page == "📢 Channels":
            channel_interface()
        elif page == "👤 Profile":
            profile_edit()
        elif page == "🔔 Notifications":
            show_notifications()

if __name__ == "__main__":
    main()
