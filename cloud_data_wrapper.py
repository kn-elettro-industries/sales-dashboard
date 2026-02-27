import streamlit as st
import pandas as pd
import requests
import config

def render_cloud_uploader():
    """
    Adds a file uploader to the sidebar for Cloud Deployments.
    Replaces the local 'Watcher' functionality.
    """
    with st.sidebar.expander("☁️ Cloud Data Upload", expanded=False):
        st.caption("Upload new Excel files here to update the dashboard via API.")
        
        uploaded_files = st.file_uploader(
            "Drop Sales Excel Here", 
            type=['xlsx'], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("Process Files"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                current_tenant = st.session_state.get("tenant_id", "default_elettro")
                
                success_count = 0
                
                status_text.text(f"Uploading {len(uploaded_files)} files to Backend...")
                
                # Prepare Multipart Form Data for multiple files
                files = [
                    ("files", (f.name, f.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) 
                    for f in uploaded_files
                ]
                data = {"tenant_id": current_tenant}
                
                try:
                    # Send to FastAPI Batch Endpoint
                    response = requests.post(
                        f"{config.API_URL}/api/v1/upload_batch", 
                        data=data, 
                        files=files,
                        timeout=300 # 5 minute timeout for large bulk pipeline execution
                    )
                    
                    if response.status_code == 200:
                        success_count = len(uploaded_files)
                    else:
                        st.error(f"Failed to process files: {response.text}")
                except Exception as e:
                    st.error(f"Backend Integration Error: {e}")
                
                if success_count > 0:
                    progress_bar.progress(100)
                    status_text.success(f"✅ Successfully processed {success_count} files via Data API!")
                    
                    # Clear Cache to show new data fetched from DB
                    st.cache_data.clear()
                    if st.button("Refresh Dashboard"):
                        st.rerun()
                else:
                    st.warning("No files were successfully processed.")
