import pandas as pd
import os
import config

data = {
    "FINANCIAL_YEAR": ["FY2024", "FY2024", "FY2025", "FY2025"],
    "MONTH": ["APR-24", "MAY-24", "APR-25", "MAY-25"],
    "TARGET_AMOUNT": [5000000, 5500000, 6000000, 6500000],
    "CUSTOMER_NAME": ["All", "All", "All", "All"],
    "MATERIAL_GROUP": ["All", "All", "All", "All"]
}

df = pd.DataFrame(data)
target_file = config.TARGETS_FILE

if not os.path.exists(target_file):
    df.to_excel(target_file, index=False)
    print(f"Created template targets.xlsx at {target_file}")
else:
    print(f"targets.xlsx already exists at {target_file}")
