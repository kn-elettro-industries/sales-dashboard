import sqlite3
import pandas as pd
import config

conn = sqlite3.connect(config.DB_PATH)
try:
    df = pd.read_sql("SELECT * FROM sales_master LIMIT 5", conn)
    print("Columns:", df.columns.tolist())
    if "CITY" in df.columns:
        print("Unique Cities:", df["CITY"].unique())
    else:
        print("CITY column is MISSING")
        
    if "STATE" in df.columns:
        print("Unique States:", df["STATE"].unique())
except Exception as e:
    print(e)
finally:
    conn.close()
