def format_indian_currency(value, currency_symbol="₹"):
    """
    Formats a number using Indian numbering system (Cr, L, K).
    Example: 15000000 -> "₹ 1.50 Cr"
    """
    sym = f"{currency_symbol} " if currency_symbol else ""
    
    if value >= 10000000:
        return f"{sym}{value/10000000:.2f} Cr"
    elif value >= 100000:
        return f"{sym}{value/100000:.2f} L"
    elif value >= 1000:
        return f"{sym}{value/1000:.2f} K"
    else:
        return f"{sym}{value:,.0f}"
