def detect_intent(question):
    q = question.lower()

    if "top" in q and "product" in q:
        return "top_products"
    if "lowest" in q and "profit" in q:
        return "lowest_profit"
    if "monthly" in q and "sales" in q:
        return "monthly_sales"
    if "region" in q and "sales" in q:
        return "region_sales"
    return "general"