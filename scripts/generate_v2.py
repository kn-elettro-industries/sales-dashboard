import pandas as pd
import sqlite3
import os
import sys

# Add parent directory to path to find config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def generate_v2_excel():
    print("--- Generating Sales Master V2 (Bypassing Lock) ---")
    
    conn = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM sales_master", conn)
        print(f"Loaded {len(df)} records from Database.")
    except Exception as e:
        print(f"Error reading DB: {e}")
        conn.close()
        return

    conn.close()
    
    # Save to V2 file to avoid permission error on the original
    output_path = os.path.join(config.MASTER_FOLDER, "sales_master_v2.xlsx")
    
    try:
        df.to_excel(output_path, index=False)
        print(f"[OK] Successfully created {output_path}")
        print(f"Verify Row 1: Qty={df['QTY'].iloc[0]}, Rate={df['RATE'].iloc[0]}, Amount={df['AMOUNT'].iloc[0]}")
    except Exception as e:
        print(f"[FAILED] Error writing Excel: {e}")

if __name__ == "__main__":
    generate_v2_excel()
