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
            if st.button("Process Files", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                current_tenant = st.session_state.get("tenant_id", "default_elettro")
                
                success_count = 0
                total_files = len(uploaded_files)
                
                status_text.text(f"Preparing to upload {total_files} files...")
                
                # Chunk files into batches of 3 to avoid timeouts
                chunk_size = 3
                file_chunks = [uploaded_files[i:i + chunk_size] for i in range(0, total_files, chunk_size)]
                
                for idx, chunk in enumerate(file_chunks):
                    status_text.text(f"Uploading batch {idx + 1} of {len(file_chunks)} ({len(chunk)} files)...")
                    
                    # Prepare Multipart Form Data for this chunk
                    files = [
                        ("files", (f.name, f.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) 
                        for f in chunk
                    ]
                    data = {"tenant_id": current_tenant}
                    
                    try:
                        # Send to FastAPI Batch Endpoint
                        response = requests.post(
                            f"{config.API_URL}/api/v1/upload_batch", 
                            data=data, 
                            files=files,
                            timeout=90 # Prevent Render 100s drops
                        )
                        
                        if response.status_code == 200:
                            success_count += len(chunk)
                        else:
                            st.error(f"Failed on batch {idx + 1}: {response.text}")
                            break # Stop on error
                    except Exception as e:
                        st.error(f"Backend Integration Error on batch {idx + 1}: {e}")
                        break # Stop on error
                        
                    # Update progress
                    progress = min(1.0, (idx + 1) / len(file_chunks))
                    progress_bar.progress(progress)
                
                if success_count == total_files:
                    progress_bar.progress(100)
                    status_text.success(f"✅ Successfully processed all {success_count} files!")
                    st.cache_data.clear()
                    time.sleep(1) # Give user time to see success
                    st.rerun()
                elif success_count > 0:
                    status_text.warning(f"⚠️ Partially processed {success_count} out of {total_files} files.")
                    st.cache_data.clear()
                else:
                    status_text.error("No files were successfully processed.")
