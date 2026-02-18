import pandas as pd
import os
import sys

# Add parent directory to path to find config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def check_exclusions():
    # Pick a sample file
    # Check processed folder since files are archived
    folder = config.PROCESSED_FOLDER
    files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
    
    if not files:
        print(f"No files found in {folder}.")
        return

    sample_file = files[-1] # Newest file
    path = os.path.join(folder, sample_file)
    print(f"Analyzing {sample_file}...")
    
    df = pd.read_excel(path)
    
    # Standardize columns
    df.columns = df.columns.str.strip().str.upper()
    df.columns = df.columns.str.replace(".", "", regex=False).str.replace(" ", "_")
    
    total_revenue = df["AMOUNT"].sum()
    print(f"Total Amount in File: {total_revenue:,.2f}")
    
    excluded_sum = 0
    excluded_count = 0    -                                                                                              
    
    print("\n--- Excluded Items ---")
    if "MATERIALGROUP" in df.columns:
        for keyword in config.EXCLUDE_KEYWORDS:
            mask = df["MATERIALGROUP"].str.contains(keyword, case=False, na=False)
            excluded = df[mask]
            
            if not excluded.empty:
                amt = excluded["AMOUNT"].sum()
                count = len(excluded)
                excluded_sum += amt
                excluded_count += count
                print(f"Keyword '{keyword}': {count} rows, INR {amt:,.2f}")
                
    print(f"\nTotal Excluded: INR {excluded_sum:,.2f} ({excluded_count} rows)")
    print(f"Impact: {excluded_sum/total_revenue*100:.1f}% of total revenue")

if __name__ == "__main__":
    check_exclusions()
