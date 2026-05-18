"""
Sales Intelligence Query Engine
Handles natural language questions about sales data without an external LLM.
Supports 15+ intents with fuzzy entity matching and rich formatted responses.
"""
import re
import difflib
import pandas as pd
from typing import Optional

# ─────────────────────────── helpers ───────────────────────────

def _fmt_inr(val: float) -> str:
    """Format a rupee amount with Cr/L suffix for readability."""
    if val >= 1_00_00_000:
        return f"₹{val / 1_00_00_000:.2f} Cr"
    if val >= 1_00_000:
        return f"₹{val / 1_00_000:.2f} L"
    return f"₹{val:,.0f}"

def _fmt_num(val: float) -> str:
    return f"{val:,.0f}"

def _pct(part: float, total: float) -> str:
    if not total:
        return "—"
    return f"{part / total * 100:.1f}%"

def _table(rows: list[tuple], headers: list[str]) -> str:
    """Build a compact text table."""
    col_widths = [len(h) for h in headers]
    str_rows = []
    for row in rows:
        sr = [str(c) for c in row]
        str_rows.append(sr)
        for i, c in enumerate(sr):
            col_widths[i] = max(col_widths[i], len(c))

    def pad(s, w): return s.ljust(w)

    sep = "  │  ".join("─" * w for w in col_widths)
    header_line = "  │  ".join(pad(h, col_widths[i]) for i, h in enumerate(headers))
    lines = [header_line, sep]
    for sr in str_rows:
        lines.append("  │  ".join(pad(c, col_widths[i]) for i, c in enumerate(sr)))
    return "\n".join(lines)


# ─────────────────────────── entity lookup ───────────────────────────

class EntityIndex:
    def __init__(self, df: pd.DataFrame):
        self.entries: dict[str, tuple[str, str]] = {}  # lower_key -> (col, actual_val)

        mappings = [
            ("STATE", "STATE"),
            ("CITY", "CITY"),
            ("CUSTOMER_NAME", "CUSTOMER_NAME"),
            ("MATERIALGROUP", "MATERIALGROUP"),
            ("ITEMNAME", "ITEMNAME"),
            ("ITEM_NAME_GROUP", "ITEM_NAME_GROUP"),
        ]
        for col, tag in mappings:
            if col in df.columns:
                for val in df[col].dropna().unique():
                    self.entries[str(val).lower().strip()] = (col, str(val))

    def fuzzy_find(self, text: str, threshold: float = 0.72) -> Optional[tuple[str, str]]:
        """Find the best matching entity in text using n-gram sliding window + difflib."""
        text = text.lower()
        words = text.split()
        best_score, best_match = 0.0, None

        for length in range(min(6, len(words)), 0, -1):
            for i in range(len(words) - length + 1):
                chunk = " ".join(words[i:i + length]).strip("?.,!:;\"'")
                # Exact match first
                if chunk in self.entries:
                    return self.entries[chunk]
                # Fuzzy match
                for key, val in self.entries.items():
                    score = difflib.SequenceMatcher(None, chunk, key).ratio()
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = val
        return best_match

    def find_all(self, text: str) -> list[tuple[str, str]]:
        """Find all entity references in text (returns list of (col, val))."""
        text_lower = text.lower()
        found: list[tuple[str, str]] = []
        seen_cols: set[str] = set()

        for length in range(min(6, len(text_lower.split())), 0, -1):
            words = text_lower.split()
            for i in range(len(words) - length + 1):
                chunk = " ".join(words[i:i + length]).strip("?.,!:;\"'")
                if chunk in self.entries:
                    col, val = self.entries[chunk]
                    if col not in seen_cols:
                        found.append((col, val))
                        seen_cols.add(col)

        # Fuzzy fallback for any unmatched entity type
        if not found:
            result = self.fuzzy_find(text_lower)
            if result:
                found.append(result)

        return found


# ─────────────────────────── intent detection ───────────────────────────

def _contains(text: str, *keywords) -> bool:
    return any(k in text for k in keywords)


def detect_intent(q: str) -> str:
    q = q.lower()

    if _contains(q, "trend", "over time", "by month", "monthly", "by quarter", "quarterly", "by year", "yearly", "annually", "over months"):
        return "trend"
    if _contains(q, "growth", "grew", "increase", "decreased", "change", "vs last year", "year over year", "yoy", "mom"):
        return "growth"
    if _contains(q, "compare", "comparison", "versus", " vs ", "against", "diff between", "difference between"):
        return "compare"
    if _contains(q, "best month", "peak month", "highest month", "worst month", "lowest month", "best quarter", "best year", "peak period", "best period", "highest period", "best week"):
        return "best_period"
    if _contains(q, "how many customer", "number of customer", "count of customer", "unique customer"):
        return "customer_count"
    if _contains(q, "how many order", "number of order", "count of order", "total order", "invoice count", "number of invoice"):
        return "order_count"
    if _contains(q, "average order", "avg order", "mean order", "aov", "average sale", "avg sale"):
        return "avg_order"
    if _contains(q, "average revenue per customer", "revenue per customer", "avg revenue per customer"):
        return "revenue_per_customer"
    if _contains(q, "percent", "percentage", "share", "contribution", "% of", "proportion"):
        return "percentage"
    if _contains(q, "top", "best", "highest", "leading", "most", "largest", "biggest", "rank"):
        return "top_n"
    if _contains(q, "bottom", "lowest", "worst", "least", "smallest", "lagging"):
        return "bottom_n"
    if _contains(q, "total revenue", "total sales", "how much", "revenue", "sales amount", "turnover", "what is the revenue", "show revenue"):
        return "total_revenue"
    if _contains(q, "total quantity", "total qty", "units sold", "how many units", "quantity"):
        return "total_quantity"
    if _contains(q, "list", "show all", "all customers", "all states", "all products", "all cities", "available"):
        return "list_entities"
    if _contains(q, "summary", "overview", "snapshot", "brief", "dashboard", "kpi", "key metrics", "highlights"):
        return "summary"

    return "total_revenue"  # safe default


# ─────────────────────────── column helpers ───────────────────────────

def _product_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("MATERIALGROUP", "ITEM_NAME_GROUP", "ITEMNAME", "ITEM_NAME"):
        if c in df.columns:
            return c
    return None

def _qty_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("QTY", "QUANTITY", "UNITS", "VOLUME"):
        if c in df.columns:
            return c
    return None

def _date_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("DATE", "INVOICE_DATE", "ORDER_DATE", "TRANS_DATE"):
        if c in df.columns and pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
    return None

def _invoice_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("INVOICE_NO", "INVOICE_NUMBER", "ORDER_ID", "TRANSACTION_ID"):
        if c in df.columns:
            return c
    return None

def _group_col_for_intent(q: str, df: pd.DataFrame) -> str:
    """Infer the grouping dimension from query keywords."""
    q = q.lower()
    prod_col = _product_col(df)

    if _contains(q, "customer", "client", "buyer", "account"):
        return "CUSTOMER_NAME"
    if _contains(q, "product", "material", "item", "sku", "group"):
        return prod_col or "CUSTOMER_NAME"
    if _contains(q, "state", "region"):
        return "STATE" if "STATE" in df.columns else "CUSTOMER_NAME"
    if _contains(q, "city", "town", "location"):
        return "CITY" if "CITY" in df.columns else "STATE" if "STATE" in df.columns else "CUSTOMER_NAME"
    return "CUSTOMER_NAME"


# ─────────────────────────── filter application ───────────────────────────

def _apply_entity_filters(df: pd.DataFrame, entities: list[tuple[str, str]]) -> tuple[pd.DataFrame, list[str]]:
    desc = []
    for col, val in entities:
        if col in df.columns:
            df = df[df[col] == val]
            label = col.replace("_", " ").title()
            desc.append(f"{label}: {val}")
    return df, desc

def _apply_year_filter(df: pd.DataFrame, q: str, desc: list[str]) -> tuple[pd.DataFrame, list[str]]:
    match = re.search(r"\b(20\d{2})\b", q)
    if match:
        year = int(match.group(1))
        dcol = _date_col(df)
        if dcol:
            df = df[df[dcol].dt.year == year]
            desc.append(f"Year: {year}")
    return df, desc


# ─────────────────────────── intent handlers ───────────────────────────

def _handle_total_revenue(df, desc, q):
    total = df["AMOUNT"].sum() if "AMOUNT" in df.columns else 0
    orders = df[_invoice_col(df)].nunique() if _invoice_col(df) else len(df)
    custs = df["CUSTOMER_NAME"].nunique() if "CUSTOMER_NAME" in df.columns else "—"
    label = f" ({', '.join(desc)})" if desc else ""
    return (
        f"**Total Revenue{label}:** {_fmt_inr(total)}\n"
        f"Orders: {_fmt_num(orders)}  •  Unique customers: {custs}"
    )

def _handle_total_quantity(df, desc, q):
    qcol = _qty_col(df)
    if not qcol:
        return "⚠️ Quantity column not found in the data."
    total = df[qcol].sum()
    label = f" ({', '.join(desc)})" if desc else ""
    return f"**Total Quantity{label}:** {_fmt_num(total)} units"

def _handle_top_n(df, desc, q, ascending=False):
    match = re.search(r"\b(\d+)\b", q)
    limit = int(match.group(1)) if match else 5
    limit = min(limit, 25)

    group_col = _group_col_for_intent(q, df)
    if group_col not in df.columns:
        return f"⚠️ Column '{group_col}' not found in data."

    metric = "AMOUNT" if "AMOUNT" in df.columns else None
    if metric is None:
        return "⚠️ Revenue column not found."

    direction = "Bottom" if ascending else "Top"
    agg = df.groupby(group_col)[metric].sum().sort_values(ascending=ascending).head(limit)
    grand_total = df[metric].sum()

    headers = ["#", group_col.replace("_", " ").title(), "Revenue", "Share"]
    rows = [
        (i + 1, name, _fmt_inr(val), _pct(val, grand_total))
        for i, (name, val) in enumerate(agg.items())
    ]
    label = f" ({', '.join(desc)})" if desc else ""
    return f"**{direction} {limit} {group_col.replace('_', ' ').title()}{label}:**\n\n" + _table(rows, headers)

def _handle_trend(df, desc, q):
    dcol = _date_col(df)
    if not dcol:
        return "⚠️ No date column available for trend analysis."

    if _contains(q, "year", "annual"):
        df["_period"] = df[dcol].dt.year.astype(str)
        label = "Yearly"
    elif _contains(q, "quarter"):
        df = df.copy()
        df["_period"] = df[dcol].dt.to_period("Q").astype(str)
        label = "Quarterly"
    else:
        df = df.copy()
        df["_period"] = df[dcol].dt.to_period("M").astype(str)
        label = "Monthly"

    agg = df.groupby("_period")["AMOUNT"].sum().sort_index().tail(24)
    peak_period = agg.idxmax()
    peak_val = agg.max()

    headers = ["Period", "Revenue"]
    rows = [(p, _fmt_inr(v)) for p, v in agg.items()]
    filter_str = f" ({', '.join(desc)})" if desc else ""
    return (
        f"**{label} Revenue Trend{filter_str}:**\n\n" +
        _table(rows, headers) +
        f"\n\n📈 Peak: {peak_period} ({_fmt_inr(peak_val)})"
    )

def _handle_growth(df, desc, q):
    dcol = _date_col(df)
    if not dcol or "AMOUNT" not in df.columns:
        return "⚠️ Date and revenue data needed for growth analysis."

    df = df.copy()
    df["_year"] = df[dcol].dt.year
    yearly = df.groupby("_year")["AMOUNT"].sum().sort_index()

    if len(yearly) < 2:
        return f"⚠️ Need at least 2 years of data for growth analysis. Currently have: {list(yearly.index)}"

    rows = []
    years = list(yearly.index)
    for i in range(1, len(years)):
        prev, curr = years[i-1], years[i]
        prev_val, curr_val = yearly[prev], yearly[curr]
        growth = (curr_val - prev_val) / prev_val * 100 if prev_val else 0
        arrow = "↑" if growth >= 0 else "↓"
        rows.append((curr, _fmt_inr(curr_val), f"{arrow} {abs(growth):.1f}%"))

    headers = ["Year", "Revenue", "YoY Growth"]
    filter_str = f" ({', '.join(desc)})" if desc else ""
    return f"**Year-over-Year Revenue Growth{filter_str}:**\n\n" + _table(rows, headers)

def _handle_best_period(df, desc, q):
    dcol = _date_col(df)
    if not dcol or "AMOUNT" not in df.columns:
        return "⚠️ Date and revenue data needed."

    df = df.copy()
    worst = _contains(q, "worst", "lowest", "weakest", "poor")

    if _contains(q, "year"):
        df["_period"] = df[dcol].dt.year.astype(str)
        label = "year"
    elif _contains(q, "quarter"):
        df["_period"] = df[dcol].dt.to_period("Q").astype(str)
        label = "quarter"
    else:
        df["_period"] = df[dcol].dt.to_period("M").astype(str)
        label = "month"

    agg = df.groupby("_period")["AMOUNT"].sum()
    if agg.empty:
        return "⚠️ No data for that period."

    if worst:
        period, val = agg.idxmin(), agg.min()
        prefix = "Worst"
    else:
        period, val = agg.idxmax(), agg.max()
        prefix = "Best"

    filter_str = f" ({', '.join(desc)})" if desc else ""
    return f"**{prefix} {label.title()}{filter_str}:** {period}\n\nRevenue: {_fmt_inr(val)}"

def _handle_customer_count(df, desc, q):
    if "CUSTOMER_NAME" not in df.columns:
        return "⚠️ Customer name column not found."
    count = df["CUSTOMER_NAME"].nunique()
    label = f" ({', '.join(desc)})" if desc else ""
    return f"**Unique Customers{label}:** {_fmt_num(count)}"

def _handle_order_count(df, desc, q):
    icol = _invoice_col(df)
    if not icol:
        return "⚠️ Order/invoice column not found."
    count = df[icol].nunique()
    label = f" ({', '.join(desc)})" if desc else ""
    return f"**Total Orders{label}:** {_fmt_num(count)}"

def _handle_avg_order(df, desc, q):
    if "AMOUNT" not in df.columns:
        return "⚠️ Revenue column not found."
    icol = _invoice_col(df)
    if icol:
        aov = df.groupby(icol)["AMOUNT"].sum().mean()
    else:
        aov = df["AMOUNT"].mean()
    label = f" ({', '.join(desc)})" if desc else ""
    return f"**Average Order Value{label}:** {_fmt_inr(aov)}"

def _handle_revenue_per_customer(df, desc, q):
    if "AMOUNT" not in df.columns or "CUSTOMER_NAME" not in df.columns:
        return "⚠️ Revenue and customer columns needed."
    rpc = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().mean()
    label = f" ({', '.join(desc)})" if desc else ""
    return f"**Avg Revenue per Customer{label}:** {_fmt_inr(rpc)}"

def _handle_percentage(df, desc, q, full_df):
    """What % of total revenue comes from a filtered entity."""
    group_col = _group_col_for_intent(q, df)
    if group_col not in df.columns or "AMOUNT" not in df.columns:
        return "⚠️ Required columns not found for percentage analysis."

    grand = full_df["AMOUNT"].sum() if "AMOUNT" in full_df.columns else 1

    if desc:
        part = df["AMOUNT"].sum()
        label = ', '.join(desc)
        return f"**Revenue Share — {label}:**\n{_fmt_inr(part)} = {_pct(part, grand)} of total ({_fmt_inr(grand)})"

    agg = df.groupby(group_col)["AMOUNT"].sum().sort_values(ascending=False).head(10)
    headers = [group_col.replace("_", " ").title(), "Revenue", "Share %"]
    rows = [(name, _fmt_inr(val), _pct(val, grand)) for name, val in agg.items()]
    return f"**Revenue Share by {group_col.replace('_', ' ').title()}:**\n\n" + _table(rows, headers)

def _handle_compare(df, desc, q, index: EntityIndex):
    """Compare two named entities."""
    if "AMOUNT" not in df.columns:
        return "⚠️ Revenue column not found."

    # Try to find exactly 2 entity groups
    all_entities = index.find_all(q)
    if len(all_entities) < 2:
        return (
            "⚠️ Could not identify two entities to compare. "
            "Try: \"compare [Customer A] vs [Customer B]\" or \"compare [State A] vs [State B]\"."
        )

    (col1, val1), (col2, val2) = all_entities[0], all_entities[1]

    def get_stats(col, val):
        sub = df[df[col] == val] if col in df.columns else pd.DataFrame()
        rev = sub["AMOUNT"].sum()
        ord_c = sub[_invoice_col(sub)].nunique() if _invoice_col(sub) else len(sub)
        cust = sub["CUSTOMER_NAME"].nunique() if "CUSTOMER_NAME" in sub.columns else "—"
        return rev, ord_c, cust

    rev1, ord1, cust1 = get_stats(col1, val1)
    rev2, ord2, cust2 = get_stats(col2, val2)

    winner = val1 if rev1 >= rev2 else val2
    headers = ["Metric", val1[:20], val2[:20]]
    rows = [
        ("Revenue", _fmt_inr(rev1), _fmt_inr(rev2)),
        ("Orders", _fmt_num(ord1), _fmt_num(ord2)),
        ("Customers", str(cust1), str(cust2)),
    ]
    return f"**Comparison: {val1} vs {val2}**\n\n" + _table(rows, headers) + f"\n\n🏆 Higher revenue: **{winner}**"

def _handle_list_entities(df, desc, q):
    group_col = _group_col_for_intent(q, df)
    if group_col not in df.columns:
        return f"⚠️ Column '{group_col}' not available."
    vals = sorted(df[group_col].dropna().unique().tolist())
    label = f" ({', '.join(desc)})" if desc else ""
    if len(vals) > 30:
        return f"**{group_col.replace('_', ' ').title()}{label}:** {len(vals)} total (showing first 30)\n" + ", ".join(str(v) for v in vals[:30]) + "..."
    return f"**{group_col.replace('_', ' ').title()}{label}:** {len(vals)} found\n" + ", ".join(str(v) for v in vals)

def _handle_summary(df, desc, q):
    if "AMOUNT" not in df.columns:
        return "⚠️ Revenue column not found."

    total_rev = df["AMOUNT"].sum()
    icol = _invoice_col(df)
    total_orders = df[icol].nunique() if icol else len(df)
    total_custs = df["CUSTOMER_NAME"].nunique() if "CUSTOMER_NAME" in df.columns else 0
    aov = total_rev / total_orders if total_orders else 0

    filter_str = f" ({', '.join(desc)})" if desc else ""

    lines = [f"**Sales Snapshot{filter_str}**\n"]
    lines.append(f"Revenue   : {_fmt_inr(total_rev)}")
    lines.append(f"Orders    : {_fmt_num(total_orders)}")
    lines.append(f"Customers : {_fmt_num(total_custs)}")
    lines.append(f"Avg Order : {_fmt_inr(aov)}")

    # Top customer
    if "CUSTOMER_NAME" in df.columns:
        top_cust = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().idxmax()
        top_cust_rev = df.groupby("CUSTOMER_NAME")["AMOUNT"].sum().max()
        lines.append(f"\nTop Customer: {top_cust} ({_fmt_inr(top_cust_rev)})")

    # Top product
    prod_col = _product_col(df)
    if prod_col and prod_col in df.columns:
        top_prod = df.groupby(prod_col)["AMOUNT"].sum().idxmax()
        top_prod_rev = df.groupby(prod_col)["AMOUNT"].sum().max()
        lines.append(f"Top Product : {top_prod} ({_fmt_inr(top_prod_rev)})")

    # Best state
    if "STATE" in df.columns:
        top_state = df.groupby("STATE")["AMOUNT"].sum().idxmax()
        top_state_rev = df.groupby("STATE")["AMOUNT"].sum().max()
        lines.append(f"Top State   : {top_state} ({_fmt_inr(top_state_rev)})")

    return "\n".join(lines)


# ─────────────────────────── main engine ───────────────────────────

class SalesQueryEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.index = EntityIndex(df)

    def process_query(self, query: str) -> str:
        q = query.strip()
        if not q:
            return "Please ask a question about your sales data."

        intent = detect_intent(q)
        entities = self.index.find_all(q)
        filtered, desc = _apply_entity_filters(self.df.copy(), entities)
        filtered, desc = _apply_year_filter(filtered, q, desc)

        if filtered.empty and entities:
            return f"⚠️ No data found for: {', '.join(v for _, v in entities)}. Check spelling or try a broader filter."

        try:
            if intent == "total_revenue":
                return _handle_total_revenue(filtered, desc, q)
            if intent == "total_quantity":
                return _handle_total_quantity(filtered, desc, q)
            if intent == "top_n":
                return _handle_top_n(filtered, desc, q, ascending=False)
            if intent == "bottom_n":
                return _handle_top_n(filtered, desc, q, ascending=True)
            if intent == "trend":
                return _handle_trend(filtered, desc, q)
            if intent == "growth":
                return _handle_growth(filtered, desc, q)
            if intent == "best_period":
                return _handle_best_period(filtered, desc, q)
            if intent == "customer_count":
                return _handle_customer_count(filtered, desc, q)
            if intent == "order_count":
                return _handle_order_count(filtered, desc, q)
            if intent == "avg_order":
                return _handle_avg_order(filtered, desc, q)
            if intent == "revenue_per_customer":
                return _handle_revenue_per_customer(filtered, desc, q)
            if intent == "percentage":
                return _handle_percentage(filtered, desc, q, self.df)
            if intent == "compare":
                return _handle_compare(self.df, desc, q, self.index)
            if intent == "list_entities":
                return _handle_list_entities(filtered, desc, q)
            if intent == "summary":
                return _handle_summary(filtered, desc, q)
            return _handle_total_revenue(filtered, desc, q)
        except Exception as e:
            return f"⚠️ Could not compute that: {str(e)}"


# ─────────────────────────── singleton ───────────────────────────

_engine: Optional[SalesQueryEngine] = None
_engine_df_id: Optional[int] = None

def process_query(query: str, df: pd.DataFrame) -> str:
    global _engine, _engine_df_id
    df_id = id(df)
    if _engine is None or _engine_df_id != df_id:
        _engine = SalesQueryEngine(df)
        _engine_df_id = df_id
    try:
        return _engine.process_query(query)
    except Exception as e:
        return f"⚠️ Error: {str(e)}"
