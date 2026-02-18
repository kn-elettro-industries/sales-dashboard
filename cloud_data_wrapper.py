import streamlit as st
import os
import pandas as pd
from etl_pipeline import run_pipeline
import config

def render_cloud_uploader():
    """
    Adds a file uploader to the sidebar for Cloud Deployments.
    Replaces the local 'Watcher' functionality.
    """
    with st.sidebar.expander("☁️ Cloud Data Upload", expanded=False):
        st.caption("Upload new Excel files here to update the dashboard.")
        
        uploaded_files = st.file_uploader(
            "Drop Sales Excel Here", 
            type=['xlsx'], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("Process Files"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 1. Save Files
                saved_count = 0
                for uploaded_file in uploaded_files:
                    try:
                        save_path = os.path.join(config.RAW_FOLDER, uploaded_file.name)
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        saved_count += 1
                    except Exception as e:
                        st.error(f"Failed to save {uploaded_file.name}: {e}")
                
                if saved_count > 0:
                    status_text.text(f"Saved {saved_count} files. Starting Pipeline...")
                    progress_bar.progress(30)
                    
                    # 2. Run ETL Pipeline
                    try:
                        # We run the pipeline function directly
                        # Capture logs or return value if possible, but for now just run it
                        run_pipeline()
                        progress_bar.progress(100)
                        status_text.success("✅ Data Updated Successfully!")
                        
                        # 3. Clear Cache to show new data
                        st.cache_data.clear()
                        if st.button("Refresh Dashboard"):
                            st.rerun()
                            
                    except Exception as e:
                        status_text.error(f"Pipeline Failed: {e}")
                else:
                    st.warning("No valid files to process.")
