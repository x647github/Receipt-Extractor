TOLERANCE = 0.02  # allow 2 cents for rounding


def check_receipt(r):
    warnings = []
    if r.total is None:
        warnings.append("No total found")
    if r.line_items and r.subtotal is not None:
        items_sum = round(sum(item.total for item in r.line_items), 2)
        if abs(items_sum - r.subtotal) > TOLERANCE:
            warnings.append(f"Items add up to {items_sum:.2f}, but subtotal is {r.subtotal:.2f}")
    if r.subtotal is not None and r.total is not None:
        expected = round(r.subtotal + (r.tax or 0) + (r.tip or 0), 2)
        if abs(expected - r.total) > TOLERANCE:
            warnings.append(f"Subtotal + tax + tip = {expected:.2f}, but total is {r.total:.2f}")
    return warnings