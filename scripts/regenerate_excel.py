import pandas as pd
import sqlite3
import os
import sys

# Add parent directory to path to find config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def regenerate_excel():
    print("--- Regenerating Sales Master Excel from DB ---")
    
    conn = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM sales_master", conn)
        print(f"Loaded {len(df)} records from Database.")
    except Exception as e:
        print(f"Error reading DB: {e}")
        conn.close()
        return

    conn.close()
    
    # Apply Improvements for Non-Tech Users
    # 1. Sort by Date Descending
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"])
        df = df.sort_values(by="DATE", ascending=False)
    
    # 2. Reorder Columns
    preferred_order = ["DATE", "MONTH", "FINANCIAL_YEAR", "INVOICE_NO", "CUSTOMER_NAME", "ITEMNAME", "QTY", "RATE", "AMOUNT"]
    existing_cols = df.columns.tolist()
    new_order = [c for c in preferred_order if c in existing_cols] + [c for c in existing_cols if c not in preferred_order]
    df = df[new_order]
    
    output_path = config.SALES_MASTER_FILE
    
    try:
        df.to_excel(output_path, index=False)
        print(f"[OK] Successfully updated {output_path}")
    except PermissionError:
        print(f"[FAILED] Permission denied for {output_path}. File is OPEN. Please close it.")
    except Exception as e:
        print(f"[FAILED] Error writing Excel: {e}")

if __name__ == "__main__":
    regenerate_excel()
