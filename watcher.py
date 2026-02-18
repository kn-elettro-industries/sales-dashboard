import time
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import etl_pipeline
import config

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        if filename.endswith(".xlsx") and not filename.startswith("~$"):
            logging.info(f"📂 New file detected: {filename}")
            
            # Small delay to ensure file copy is complete
            time.sleep(2)
            
            try:
                logging.info("🚀 Triggering ETL Pipeline...")
                etl_pipeline.run_pipeline()
                logging.info("✅ Pipeline finished successfully.")
            except Exception as e:
                logging.error(f"❌ ETL Pipeline failed: {e}")

def start_watcher():
    path_to_watch = config.RAW_FOLDER
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=False)
    
    logging.info(f"Watching directory: {path_to_watch}")
    logging.info("Waiting for new Excel files... (Press Ctrl+C to stop)")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watcher()
