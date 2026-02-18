import pandas as pd
import re

class SalesQueryEngine:
    def __init__(self, df):
        self.df = df
        self.index = {}
        self.prepare_indices()
    
    def prepare_indices(self):
        """Builds a reverse index for fast entity lookup."""
        # 1. States
        if "STATE" in self.df.columns:
            for val in self.df["STATE"].dropna().unique():
                self.index[str(val).lower()] = ("STATE", val)

        # 2. Customers (Index parts of names too for fuzzy-ish matching)
        if "CUSTOMER_NAME" in self.df.columns:
            for val in self.df["CUSTOMER_NAME"].dropna().unique():
                val_str = str(val).lower()
                self.index[val_str] = ("CUSTOMER_NAME", val)
                # Heuristic: Index first word if meaningful (e.g. "K.N. Elettro" -> "k.n. elettro")
        
        # 3. Products
        prod_col = "MATERIALGROUP" if "MATERIALGROUP" in self.df.columns else "ITEMNAME"
        if prod_col in self.df.columns:
            for val in self.df[prod_col].dropna().unique():
                self.index[str(val).lower()] = (prod_col, val)

    def extract_filters(self, query):
        """Finds entities in the query and returns filters."""
        query = query.lower()
        filters = {}
        
        # Naive N-gram matching (sliding window of 1-4 words)
        # We start with largest n-grams to match full names first
        words = query.split()
        n = len(words)
        
        # Iterate n-grams from length 4 down to 1
        for length in range(min(4, n), 0, -1):
            for i in range(n - length + 1):
                chunk = " ".join(words[i:i+length])
                # Remove punctuation from chunk end
                chunk_clean = chunk.strip("?,.!:")
                
                if chunk_clean in self.index:
                    col, val = self.index[chunk_clean]
                    if col not in filters:
                        filters[col] = val
        
        # Year Detection
        match_year = re.search(r"\b(20\d{2})\b", query)
        if match_year:
            filters["YEAR"] = match_year.group(1)
            
        return filters

    def process_query(self, query):
        query = query.lower().strip()
        df_filtered = self.df.copy()
        
        # 1. Apply Filters
        detected_filters = self.extract_filters(query)
        filter_desc = []
        
        for col, val in detected_filters.items():
            if col == "YEAR":
                if "DATE" in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered["DATE"].dt.year == int(val)]
                    filter_desc.append(f"Year: {val}")
            else:
                df_filtered = df_filtered[df_filtered[col] == val]
                filter_desc.append(f"{col}: {val}")
        
        if df_filtered.empty:
            return "⚠️ No data found for that combination."

        # 2. Determine Intent & Metric
        metric = "AMOUNT"
        metric_name = "Revenue"
        
        if any(x in query for x in ["quantity", "qty", "volume", "units"]):
            metric = "QTY"
            metric_name = "Quantity"
        elif any(x in query for x in ["count", "orders", "invoices"]):
            metric = "INVOICE_NO"
            metric_name = "Orders"
            
        # 3. Execute
        
        # Context: "Top 5"
        if "top" in query or "best" in query:
            match = re.search(r"top (\d+)", query)
            limit = int(match.group(1)) if match else 5
            
            # Grouping inference
            group_col = "CUSTOMER_NAME"
            if "customer" in query: group_col = "CUSTOMER_NAME"
            elif "product" in query or "item" in query: group_col = "MATERIALGROUP" if "MATERIALGROUP" in self.df.columns else "ITEMNAME"
            elif "state" in query or "region" in query: group_col = "STATE"
            
            # Aggregation
            if metric == "INVOICE_NO":
                res = df_filtered.groupby(group_col)[metric].nunique().sort_values(ascending=False).head(limit)
            else:
                res = df_filtered.groupby(group_col)[metric].sum().sort_values(ascending=False).head(limit)
                
            response = f"🏆 **Top {limit} {group_col.replace('_', ' ').title()}**"
            if filter_desc: response += f" ({', '.join(filter_desc)})"
            response += ":\n"
            
            for i, (name, val) in enumerate(res.items(), 1):
                fmt_val = f"{val:,.0f}" if metric != "AMOUNT" else f"₹ {val:,.0f}"
                response += f"{i}. {name}: {fmt_val}\n"
            return response

        # Default: Single Value Aggregation
        if metric == "INVOICE_NO":
            val = df_filtered[metric].nunique()
            fmt = f"{val}"
        else:
            val = df_filtered[metric].sum()
            fmt = f"₹ {val:,.2f}" if metric == "AMOUNT" else f"{val:,.0f}"

        response = f"**Total {metric_name}**"
        if filter_desc: response += f" ({', '.join(filter_desc)})"
        response += f": {fmt}"
        
        return response

# Singleton
engine = None
def process_query(query, df):
    global engine
    if engine is None or engine.df is not df:
        engine = SalesQueryEngine(df)
    try:
        return engine.process_query(query)
    except Exception as e:
        return f"🤖 Error: {str(e)}"
