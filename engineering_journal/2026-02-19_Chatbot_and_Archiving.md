# Engineering Log: 2026-02-19

## Feature: Floating Chatbot & PDF Archiving

### Context
User required ubiquitous access to the AI assistant and a mechanism to snapshot daily reports for offline analysis.

### Implementation
1.  **Floating Chatbot (`app.py`)**
    *   Injecting a persistent FAB (Floating Action Button) using `st.markdown` with fixed positioning.
    *   **Constraint**: Streamlit's layout flow renders elements sequentially.
    *   **Solution**: CSS Injection with `!important` to override default styling and z-index positioning (Layer 999999).
    *   **Logic**: Hooked into `st.popover` for the chat interface. State is managed via `st.session_state['messages']`.

2.  **PDF Archiving (`analytics/reporting.py`)**
    *   **Mechanism**: Extended `FPDF` generation logic to support multi-file output.
    *   **Storage**: Files are committed to local disk under `reports/{date}/`.
    *   **Artifacts**:
        *   `Executive_Summary.pdf`: High-level KPI aggregations.
        *   `Customer_Overview.pdf`: Client-specific metrics.

### Technical Debt / Notes
*   **CSS Fragility**: The floating button relies on Streamlit's internal DOM classes (`[data-testid="stPopover"]`). This may break in future Streamlit updates.
*   **File Permissions**: Ensure write access to the `reports` directory in production environments.
