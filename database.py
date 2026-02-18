import sqlite3
import pandas as pd

import config

def load_data():
    conn = sqlite3.connect(config.DB_PATH)
    df = pd.read_sql("SELECT * FROM sales_master", conn)
    conn.close()
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df

def clear_all_data():
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS sales_master")
    conn.commit()
    conn.close()
