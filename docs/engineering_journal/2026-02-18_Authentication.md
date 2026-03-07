# Engineering Log: 2026-02-18

## Feature: Authentication & RBAC System

### Context
Application required restricting access based on user roles (Admin, Manager, Viewer) to protect sensitive sales data.

### Implementation
1.  **Authentication Module (`auth.py`)**
    *   Implemented a standalone `Auth` class handling login/logout logic.
    *   **Security**: integrated `hashlib` for SHA-256 password hashing. Plain text passwords are no longer stored in memory.
    *   **Persistence**: Utilized `st.session_state` to maintain session validity across re-runs.

2.  **Role-Based Access Control (RBAC) (`app.py`)**
    *   **Routing**: Sidebar menu options are now dynamically generated based on `st.session_state['role']`.
    *   **ACL**:
        *   `Admin`: Full system access + User Management.
        *   `Manager`: Read-only access to Executive Reports.
        *   `Viewer`: Restricted to basic dashboards.

### Notes
*   Hardcoded credentials in `users.json` (or dict) should be migrated to a database for production.
