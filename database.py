import sqlite3
import pandas as pd

import config

def load_data():
    conn = sqlite3.connect(config.DB_PATH)
    df = pd.read_sql("SELECT * FROM sales_master", conn)
    conn.close()
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df
