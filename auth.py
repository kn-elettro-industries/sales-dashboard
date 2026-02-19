import streamlit as st
import time

# Simple User Database (In Production, use a real DB or Hash)
USERS = {
    "admin": {"password": "admin123", "role": "Admin", "name": "System Administrator"},
    "manager": {"password": "manager123", "role": "Manager", "name": "Sales Manager"},
    "user": {"password": "user123", "role": "Viewer", "name": "Sales Representative"}
}

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in USERS and st.session_state["password"] == USERS[st.session_state["username"]]["password"]:
            st.session_state["authenticated"] = True
            # Set Role
            user_info = USERS[st.session_state["username"]]
            st.session_state["role"] = user_info["role"]
            st.session_state["user_name"] = user_info["name"]
            
            del st.session_state["password"]  # Clean up
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        # Login Form
        st.markdown("""
        <style>
        .login-box {
            padding: 20px;
            background-color: #1E1E1E;
            border-radius: 10px;
            border: 1px solid #333;
            max-width: 400px;
            margin: 0 auto;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.image("assets/logo_white_text.png", width=200)
            st.markdown("### Secure Intelligence Access")
            
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            
            if st.button("Login", use_container_width=True):
                password_entered()
                if not st.session_state["authenticated"]:
                    st.error("😕 User not found or password incorrect")
                else:
                    st.rerun()

        return False
    else:
        return True

def logout():
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = None
    st.rerun()
