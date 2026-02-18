import sqlite3
import pandas as pd
import sys
import os

# Add parent directory to path to find config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def check_data():
    conn = sqlite3.connect(config.DB_PATH)
    df = pd.read_sql("SELECT * FROM sales_master", conn)
    conn.close()
    
    print(f"Columns: {list(df.columns)}")
    print(f"Total Rows: {len(df)}")
    print(f"Unique Invoices: {df['INVOICE_NO'].nunique()}")
    
    if "AMOUNT" in df.columns:
        print(f"Total Revenue (Taxable) in DB: {df['AMOUNT'].sum():,.2f}")
    if "TOTALAMOUNT" in df.columns:
        print(f"Total Invoice Value (Inc. Tax) in DB: {df['TOTALAMOUNT'].sum():,.2f}")
        
    print("\n--- Math Check ---")
    if "QTY" in df.columns and "RATE" in df.columns and "AMOUNT" in df.columns:
        df["CALC_AMOUNT"] = df["QTY"] * df["RATE"]
        diff = (df["CALC_AMOUNT"] - df["AMOUNT"]).abs().sum()
        print(f"Difference between (Qty * Rate) and Amount: {diff:,.2f}")
        
    if "AMOUNT" in df.columns and "TAX" in df.columns and "TOTALAMOUNT" in df.columns:
        # Check if TAX column is actually filled, otherwise use SGST+CGST+IGST
        tax_sum = df["TAX"].sum()
        if tax_sum == 0 and "IGST" in df.columns:
             tax_sum = df["IGST"].fillna(0).sum() + df["CGST"].fillna(0).sum() + df["SGST"].fillna(0).sum()
        
        calc_total = df["AMOUNT"].sum() + tax_sum
        actual_total = df["TOTALAMOUNT"].sum()
        print(f"Calculated Total (Amt + Tax): {calc_total:,.2f}")
        print(f"Actual Total Amount: {actual_total:,.2f}")
        print(f"Difference: {abs(calc_total - actual_total):,.2f}")

    print("\nSample Mismatched Rows (Qty * Rate != Amount):")
    if "CALC_AMOUNT" in df.columns:
        mismatched = df[abs(df["CALC_AMOUNT"] - df["AMOUNT"]) > 100].head(5)
        print(mismatched[["ITEMNAME", "QTY", "RATE", "CALC_AMOUNT", "AMOUNT"]])
    
    print("\n--- Financials Check ---")
    zero_total_count = len(df[df["TOTALAMOUNT"] == 0])
    print(f"Rows with 0 Total Amount: {zero_total_count}")
    if zero_total_count == 0:
        print("[OK] All rows have Total Amount populated.")

    if len(df) > df['INVOICE_NO'].nunique():
        print("[OK] GOOD: Multiple rows per invoice detected (Item Level Data).")
    else:
        print("[WARN] WARNING: Row count equals Invoice count (Invoice Level Data - Potential Data Loss!)")
        
    print("\nSample Duplicated Invoices:")
    print(df[df.duplicated(subset=['INVOICE_NO'], keep=False)].head(10))

if __name__ == "__main__":
    check_data()
