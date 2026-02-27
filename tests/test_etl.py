import pandas as pd
import pytest
import sys
import os

# Add parent to path to allow importing etl_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl_pipeline import standardize, calculate_taxes, merge_customer_master

def test_standardize_columns():
    """Test that weird column names from Excel are properly standardized to SQL-safe strings."""
    raw_data = {
        "  Item.Name. ": ["A"],
        "City/Town": ["B"],
        "Invoice No.": ["C"]
    }
    df = pd.DataFrame(raw_data)
    clean_df = standardize(df)
    
    assert "ITEMNAME" in clean_df.columns, "Item Name not fuzzy matched"
    assert "CITY" in clean_df.columns, "City not fuzzy matched"
    assert "INVOICE_NO" in clean_df.columns, "Invoice No not fuzzy matched"
    assert "CITY/TOWN" not in clean_df.columns, "Special characters not stripped"

def test_tax_calculations():
    """Test that IGST/CGST/SGST split properly based on State logic."""
    data = {
        "AMOUNT": [1000, 2000],
        "STATE": ["MAHARASHTRA", "DELHI"] # Row 0 is Intra (CGST), Row 1 is Inter (IGST)
    }
    df = pd.DataFrame(data)
    tax_df = calculate_taxes(df)
    
    # 1000 -> 18% = 180 total tax (90 CGST / 90 SGST)
    assert tax_df.loc[0, "CGST"] == 90.0, "Intra-state CGST incorrect"
    assert tax_df.loc[0, "SGST"] == 90.0, "Intra-state SGST incorrect"
    assert tax_df.loc[0, "IGST"] == 0.0,  "Intra-state IGST should be zero"
    assert tax_df.loc[0, "TOTALAMOUNT"] == 1180.0
    
    # 2000 -> 18% = 360 total tax (360 IGST)
    assert tax_df.loc[1, "IGST"] == 360.0, "Inter-state IGST incorrect"
    assert tax_df.loc[1, "CGST"] == 0.0,  "Inter-state CGST should be zero"
    assert tax_df.loc[1, "TOTALAMOUNT"] == 2360.0

def test_missing_state_fallback():
    """Test that missing states are guessed correctly based on the city dictionary."""
    data = {
        "CUSTOMER_NAME": ["CUST1", "CUST2"],
        "CITY": ["MUMBAI", "UNKNOWN_CITY"]
    }
    # Pretend it merged but STATE is missing
    df = pd.DataFrame(data)
    
    # Run the merge function logic (which includes the snippet for guessing state)
    merged_df = merge_customer_master(df)
    
    assert merged_df.loc[0, "STATE"] == "MAHARASHTRA", "Mumbai should map to Maharashtra"
    assert "NOT FOUND" in merged_df.loc[1, "STATE"], "Unknown city should trigger fallback warning"
