import streamlit as st
import json
import os
import time

# File Path
USER_DB_FILE = "data/users.json"

def load_users():
    """Loads users from Local JSON file."""
    if not os.path.exists(USER_DB_FILE):
        default_users = {
            "admin": {"password": "admin123", "role": "Admin", "name": "System Administrator", "status": "Active"},
            "manager": {"password": "manager123", "role": "Manager", "name": "Sales Manager", "status": "Active"},
            "user": {"password": "user123", "role": "Viewer", "name": "Sales Representative", "status": "Active"}
        }
        os.makedirs(os.path.dirname(USER_DB_FILE), exist_ok=True)
        with open(USER_DB_FILE, "w") as f:
            json.dump(default_users, f, indent=4)
        return default_users
    
    try:
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """Saves users to JSON file."""
    os.makedirs(os.path.dirname(USER_DB_FILE), exist_ok=True)
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=4)

def register_user(username, password, name):
    """Registers a new user."""
    users = load_users()
    if username in users:
        return False, "Username already exists."
    
    users[username] = {
        "password": password,
        "role": "Viewer",
        "name": name,
        "status": "Pending"
    }
    save_users(users)
    return True, "Request sent! Please wait for Admin approval."

def update_user_details(username, role, status):
    """Updates user role/status locally."""
    users = load_users()
    if username in users:
        users[username]["role"] = role
        users[username]["status"] = status
        save_users(users)
        return True, "Updated locally"
    return False, "User not found locally"

def check_password():
    """Returns `True` if the user is authenticated."""
    
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    # Login UI
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #1a1a1a;
            border-radius: 10px;
            border: 1px solid #333;
        }
        </style>
        """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("assets/logo_white_text.png", width=200)
        st.markdown("### Secure Intelligence Hub")
        
        tab1, tab2 = st.tabs(["🔒 Login", "📝 Request Access"])
        
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login", use_container_width=True):
                users = load_users()
                if username in users and users[username]["password"] == password:
                    user_data = users[username]
                    
                    if user_data.get("status") == "Pending":
                        st.warning("⏳ Account is pending confirmation from Admin.")
                    elif user_data.get("status") == "Blocked":
                        st.error("🚫 Account has been blocked.")
                    else:
                        # Success
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.session_state["role"] = user_data["role"]
                        st.session_state["user_name"] = user_data["name"]
                        st.rerun()
                else:
                    st.error("Invalid Username or Password")
        
        with tab2:
            new_user = st.text_input("New Username", key="reg_user")
            new_pass = st.text_input("New Password", type="password", key="reg_pass")
            full_name = st.text_input("Full Name", key="reg_name")
            
            if st.button("Submit Request", use_container_width=True):
                if new_user and new_pass and full_name:
                    success, msg = register_user(new_user, new_pass, full_name)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill all fields.")

    return False

def logout():
    for key in ["authenticated", "role", "user_name", "username"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
