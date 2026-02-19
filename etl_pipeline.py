import pandas as pd
import os
import sqlite3
import logging
from datetime import datetime
import config
import pipeline_monitor

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(config.MASTER_FOLDER, "pipeline.log")),
        logging.StreamHandler()
    ]
)

def standardize(df):
    """
    Standardizes column names and text values:
    - Strips spaces
    - Converts column names to uppercase
    - Converts all string values to uppercase
    - Sanitizes column names for SQL
    """
    if df.empty:
        return df

    # Standardize column names
    df.columns = df.columns.str.strip().str.upper()
    
    # SQL Safe column names
    df.columns = (
        df.columns
        .str.replace(".", "", regex=False)
        .str.replace(" ", "_")
    )
    
    # fuzzy column matching for critical fields
    for col in df.columns:
        col_upper = col.upper()
        
        # CITY Synonyms
        if any(x in col_upper for x in ["CITY", "TOWN", "DISTRICT", "LOCATION", "STATION", "DESTINATION", "PLACE"]):
            if "CITY" not in df.columns:
                df.rename(columns={col: "CITY"}, inplace=True)
        
        # STATE Synonyms
        elif any(x in col_upper for x in ["STATE", "REGION", "PROVINCE", "TERRITORY", "POS", "SUPPLY"]):
            if "STATE" not in df.columns:
                df.rename(columns={col: "STATE"}, inplace=True)
                
        # CUSTOMER Synonyms
        elif any(x in col_upper for x in ["CUSTOMER", "PARTY", "BILL TO", "BUYER", "DEBTOR"]):
            if "CUSTOMER_NAME" not in df.columns:
                 df.rename(columns={col: "CUSTOMER_NAME"}, inplace=True)
                 
        # ITEM Synonyms
        elif any(x in col_upper for x in ["ITEM", "MATERIAL", "PRODUCT", "DESCRIPTION", "PART"]):
            if "ITEMNAME" not in df.columns and "GROUP" not in col_upper:
                df.rename(columns={col: "ITEMNAME"}, inplace=True)

        # INVOICE Synonyms
        elif any(x in col_upper for x in ["INVOICE", "BILL NO", "DOC NO", "VOUCHER"]):
            if "INVOICE_NO" not in df.columns and "DATE" not in col_upper:
                df.rename(columns={col: "INVOICE_NO"}, inplace=True)

    return df

def calculate_fy(date):
    """Calculates Financial Year from a date object."""
    if pd.isna(date):
        return "UNKNOWN"
    
    if date.month >= config.FY_START_MONTH:
        return f"FY{date.year % 100}-{(date.year + 1) % 100}"
    else:
        return f"FY{(date.year - 1) % 100}-{date.year % 100}"

def ingest_raw_data():
    """Reads all Excel files from the raw folder and combines them."""
    pipeline_monitor.update_status("Ingest", "Running", "Scanning raw folder...", 10)
    
    all_files = [f for f in os.listdir(config.RAW_FOLDER) if f.endswith(".xlsx")]
    
    if not all_files:
        logging.info("No new raw files found.")
        pipeline_monitor.update_status("Ingest", "Idle", "No new files found", 0)
        return None

    logging.info(f"files detected: {all_files}")
    pipeline_monitor.update_status("Ingest", "Running", f"Found {len(all_files)} files", 20)
    
    dataframes = []
    for i, file in enumerate(all_files):
        try:
            path = os.path.join(config.RAW_FOLDER, file)
            df = pd.read_excel(path)
            dataframes.append(df)
            logging.info(f"Loaded {file} ({len(df)} rows)")
            pipeline_monitor.update_status("Ingest", "Running", f"Loaded {file}", 20 + int((i/len(all_files))*20))
        except Exception as e:
            logging.error(f"Error loading {file}: {e}")

    if not dataframes:
        return None

    combined_df = pd.concat(dataframes, ignore_index=True)
    return combined_df

def clean_and_transform(df):
    """Applies filters, standardization, and enrichment logic."""
    pipeline_monitor.update_status("Transform", "Running", "Standardizing and cleaning data...", 50)
    
    if df is None or df.empty:
        return df

    # 1. Standardize
    df = standardize(df)

    initial_count = len(df)

    # 2. Exclude Keywords
    for keyword in config.EXCLUDE_KEYWORDS:
        if "MATERIALGROUP" in df.columns:
            df = df[~df["MATERIALGROUP"].str.contains(keyword, case=False, na=False)]
    
    logging.info(f"Rows excluded by keywords: {initial_count - len(df)}")

    # 3. Apply Mappings
    if "MATERIALGROUP" in df.columns:
        for pattern, replacement in config.MATERIAL_GROUP_MAPPINGS.items():
            df.loc[df["MATERIALGROUP"].str.contains(pattern, case=False, na=False), "MATERIALGROUP"] = replacement

    # 4. Add Financial Year
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"])
        df["FINANCIAL_YEAR"] = df["DATE"].apply(calculate_fy)
        # Create Month column for easy grouping
        # Create Month column for easy grouping (MMM-YY)
        df["MONTH"] = df["DATE"].dt.strftime("%b-%y").str.upper()

    # 5. Clean & Recalculate Financials
    # A. Drop unwanted columns from raw data (as per user request)
    # We DO NOT drop AMOUNT anymore, we trust the Excel value (28cr vs 76cr)
    cols_to_drop = ["TOTALAMOUNT", "TAX", "IGST", "CGST", "SGST"]
    df = df.drop(columns=cols_to_drop, errors="ignore")
    
    # B. Auto-Calculate Taxes & Total based on Excel's AMOUNT
    # Default State to 'MAHARASHTRA' if missing for calculation
    company_state = "MAHARASHTRA"
    
    # Initialize columns
    df["IGST"] = 0.0
    df["CGST"] = 0.0
    df["SGST"] = 0.0
    df["TAX"] = 0.0
    df["TOTALAMOUNT"] = 0.0

    if "AMOUNT" in df.columns:
        logging.info("Recalculating Financials for all rows.")
        
        # Clean state column for comparison
        # CRITICAL FIX: Do NOT overwrite actual data with default yet.
        # We need to know if it's truly missing to check Customer Master later.
        
        calc_state_series = df["STATE"].copy() if "STATE" in df.columns else pd.Series(["Unknown"] * len(df))
        calc_state_series = calc_state_series.fillna("Unknown").str.upper().str.strip()
        
        # If State is Unknown, we assume Intra-State (Maharashtra) for TAX purposes only?
        # Or we can leave tax 0. Let's assume Intra-state for safety so totals aren't wrong.
        # BUT we must NOT save "MAHARASHTRA" to the df["STATE"] unless it was there.
        
        # 18% Tax Rate
        tax_rate = 0.18
        
        # Logic: If State is Company State OR Unknown -> CGST/SGST (Intra)
        # Else -> IGST (Inter)
        intra_state = calc_state_series.isin([company_state, "UNKNOWN", "MAHARASHTRA"])
        inter_state = ~intra_state
        
        # IGST
        df.loc[inter_state, "IGST"] = df.loc[inter_state, "AMOUNT"] * tax_rate
        
        # CGST + SGST
        df.loc[intra_state, "CGST"] = df.loc[intra_state, "AMOUNT"] * (tax_rate / 2)
        df.loc[intra_state, "SGST"] = df.loc[intra_state, "AMOUNT"] * (tax_rate / 2)
        
        # Total Tax
        df["TAX"] = df["IGST"] + df["CGST"] + df["SGST"]
        
        # Total Amount
        df["TOTALAMOUNT"] = df["AMOUNT"] + df["TAX"]

    # 6. Ensure CITY column exists
    if "CITY" not in df.columns:
        df["CITY"] = "City Not Found"
        
    return df

def merge_customer_master(sales_df):
    """Merges sales data with customer master."""
    pipeline_monitor.update_status("Reference", "Running", "Merging Customer Master...", 60)
    
    if not os.path.exists(config.CUSTOMER_MASTER_FILE):
        logging.warning("Customer Master file not found. Skipping merge.")
        return sales_df

    master_df = pd.read_excel(config.CUSTOMER_MASTER_FILE)
    master_df = standardize(master_df)

    # Ensure join key exists
    if "CUSTOMER_NAME" in sales_df.columns and "CUSTOMER_NAME" in master_df.columns:
        sales_df = pd.merge(sales_df, master_df, on="CUSTOMER_NAME", how="left")
        
        # Clean up Merge Suffixes (x/y)
        # Prioritize Master (y) then Raw (x)
        for col in ["STATE", "CITY"]:
            if f"{col}_y" in sales_df.columns and f"{col}_x" in sales_df.columns:
                sales_df[col] = sales_df[f"{col}_y"].fillna(sales_df[f"{col}_x"])
                sales_df = sales_df.drop(columns=[f"{col}_y", f"{col}_x"])
            elif f"{col}_y" in sales_df.columns:
                 sales_df[col] = sales_df[f"{col}_y"]
                 sales_df = sales_df.drop(columns=[f"{col}_y"])
            elif f"{col}_x" in sales_df.columns:
                 sales_df[col] = sales_df[f"{col}_x"]
                 sales_df = sales_df.drop(columns=[f"{col}_x"])
        
        logging.info("Customer Master merged and columns cleaned.")
    else:
        logging.warning("CUSTOMER_NAME column missing in sales or master data.")

    return sales_df

def update_database(new_df):
    """Updates the SQLite database with new records only."""
    pipeline_monitor.update_status("Load", "Running", "Updating Database...", 75)
    
    if new_df is None or new_df.empty:
        return 0

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales_master'")
    table_exists = cursor.fetchone()

    if table_exists:
        # Schema Evolution: Check if CITY column exists
        cursor.execute("PRAGMA table_info(sales_master)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "CITY" not in columns:
            logging.info("Adding missing CITY column to sales_master")
            try:
                cursor.execute("ALTER TABLE sales_master ADD COLUMN CITY TEXT DEFAULT 'City Not Found'")
                conn.commit()
            except Exception as e:
                logging.error(f"Failed to add CITY column: {e}")

    new_records_count = 0

    if not table_exists:
        new_df.to_sql("sales_master", conn, index=False)
        new_records_count = len(new_df)
        logging.info(f"Created new table with {new_records_count} records.")
    else:
        # Get existing invoices to avoid duplicates
        existing_invoices = pd.read_sql("SELECT INVOICE_NO FROM sales_master", conn)
        existing_set = set(existing_invoices["INVOICE_NO"])
        
        # Filter new records
        to_insert = new_df[~new_df["INVOICE_NO"].isin(existing_set)]
        new_records_count = len(to_insert)

        if new_records_count > 0:
            to_insert.to_sql("sales_master", conn, if_exists="append", index=False)
            logging.info(f"Appended {new_records_count} new records.")
        else:
            logging.info("No new records to append to DB.")

    conn.close()
    return new_records_count

def archive_files():
    """Moves processed files to the archive folder."""
    pipeline_monitor.update_status("Archive", "Running", "Moving files to archive...", 90)
    
    files = [f for f in os.listdir(config.RAW_FOLDER) if f.endswith(".xlsx")]
    for file in files:
        src = os.path.join(config.RAW_FOLDER, file)
        dst = os.path.join(config.PROCESSED_FOLDER, file)
        try:
            os.rename(src, dst)
            logging.info(f"Archived {file}")
        except Exception as e:
            logging.error(f"Failed to archive {file}: {e}")

def run_pipeline():
    logging.info("--- Starting ETL Pipeline ---")
    pipeline_monitor.update_status("Start", "Running", "Initializing pipeline...", 0)
    
    try:
        # 1. Ingest
        raw_df = ingest_raw_data()
        if raw_df is None:
            logging.info("Pipeline finished: No data to process.")
            pipeline_monitor.update_status("Done", "Completed", "No new data", 100)
            return

        # 2. Transform
        clean_df = clean_and_transform(raw_df)
        
        # 3. Merge Master
        final_df = merge_customer_master(clean_df)

        # 4. Update Database
        added_count = update_database(final_df)

        # 5. Update Excel Master (Optional, for backward compatibility)
        try:
            if os.path.exists(config.SALES_MASTER_FILE):
                existing_master = pd.read_excel(config.SALES_MASTER_FILE)
                combined_master = pd.concat([existing_master, final_df], ignore_index=True).drop_duplicates(subset=["INVOICE_NO"])
                
                # Sort by Date Descending
                if "DATE" in combined_master.columns:
                    combined_master["DATE"] = pd.to_datetime(combined_master["DATE"])
                    combined_master = combined_master.sort_values(by="DATE", ascending=False)
                
                # Reorder Columns for User Friendliness
                preferred_order = ["DATE", "MONTH", "FINANCIAL_YEAR", "INVOICE_NO", "CUSTOMER_NAME", "ITEMNAME", "QTY", "RATE", "AMOUNT"]
                existing_cols = combined_master.columns.tolist()
                new_order = [c for c in preferred_order if c in existing_cols] + [c for c in existing_cols if c not in preferred_order]
                combined_master = combined_master[new_order]
                
                combined_master.to_excel(config.SALES_MASTER_FILE, index=False)
            else:
                # Sort by Date Descending
                if "DATE" in final_df.columns:
                    final_df["DATE"] = pd.to_datetime(final_df["DATE"])
                    final_df = final_df.sort_values(by="DATE", ascending=False)
                
                # Reorder Columns
                preferred_order = ["DATE", "MONTH", "FINANCIAL_YEAR", "INVOICE_NO", "CUSTOMER_NAME", "ITEMNAME", "QTY", "RATE", "AMOUNT"]
                existing_cols = final_df.columns.tolist()
                new_order = [c for c in preferred_order if c in existing_cols] + [c for c in existing_cols if c not in preferred_order]
                final_df = final_df[new_order]
                
                final_df.to_excel(config.SALES_MASTER_FILE, index=False)
            logging.info("Excel Master updated successfully.")
        except PermissionError:
            logging.warning(f"Could not update {config.SALES_MASTER_FILE} (File open?). Skipping Excel export.")
        except Exception as e:
            logging.error(f"Failed to update Excel Master: {e}")

        # 6. Archive
        if added_count > 0:
            archive_files()

        logging.info("--- Pipeline Completed Successfully ---")
        pipeline_monitor.update_status("Done", "Completed", f"Processed {added_count} records", 100)
        
    except Exception as e:
        logging.error(f"Pipeline Failed: {e}")
        pipeline_monitor.update_status("Error", "Failed", str(e), 0)

if __name__ == "__main__":
    run_pipeline()
