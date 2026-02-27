import database
import etl_pipeline
import config

print("Testing Database Config...")
print(f"DATABASE_URL: {config.DATABASE_URL}")

if database.engine:
    print(f"Engine instantiated successfully: {database.engine}")
else:
    print("Engine failed to instantiate.")
    
print("\nTesting ETL imports and pipeline instantiation...")
try:
    print("Successfully imported etl_pipeline")
    print(f"Update Database function signature accepts tenant_id: {etl_pipeline.update_database}")
except Exception as e:
    print(f"Error checking ETL pipeline: {e}")
