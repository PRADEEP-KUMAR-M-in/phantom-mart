import textwrap
from pdf_export import SHOP_NAME, SHOP_ADDRESS, SHOP_PHONE, SHOP_GST

# how many characters fit on one line for each paper size
PAPER_WIDTHS = {"80mm": 48, "58mm": 32}

# thermal printers use old code pages, so we swap the symbols they can't print
def clean(text):
    text = str(text)
    for old, new in (("₹", "Rs."), ("—", "-"), ("–", "-"), ("·", "-"), ("×", "x"), ("’", "'")):
        text = text.replace(old, new)
    return text

def center(text, width):
    return text.center(width).rstrip()

# left text and right text on the same line
def two_cols(left, right, width):
    space = width - len(left) - len(right)
    if space < 1:
        left = left[:max(width - len(right) - 1, 0)]
        space = 1
    return left + " " * space + right

def wrap(text, width, indent=""):
    return textwrap.wrap(text, width, initial_indent=indent, subsequent_indent=indent) or [""]

# data = {
#   "bill_number", "customer_name", "date", "time", "cashier",
#   "items": [(name, qty, price), ...],
#   "subtotal", "discount", "gst", "grand_total",
#   "payments": [(method, amount, detail), ...],
#   "loyalty": {"earned", "redeemed", "balance"} (optional)
# }
# gives back a list of (text, bold) lines
def build_receipt_lines(data, width=48):
    lines = []

    def add(text="", bold=False):
        lines.append((clean(text), bold))

    def separator(char="-"):
        add(char * width)

    # shop header
    add(center(SHOP_NAME.upper(), width), True)
    for part in wrap(SHOP_ADDRESS, width):
        add(center(part, width))
    add(center(f"Ph: {SHOP_PHONE}", width))
    add(center(f"GSTIN: {SHOP_GST}", width))
    separator("=")

    # bill info
    add(two_cols(f"Bill: {data['bill_number']}", data["date"], width))
    add(two_cols(f"Cust: {data['customer_name']}", data["time"], width))
    add(f"Cashier: {data['cashier']}")
    separator()

    add(two_cols("ITEM", "AMOUNT", width), True)
    separator()

    total_qty = 0
    for name, qty, price in data["items"]:
        for part in wrap(name, width):
            add(part)
        add(two_cols(f"  {qty} x {price:.2f}", f"{qty * price:.2f}", width))
        total_qty += qty
    separator()

    add(two_cols(f"Items: {len(data['items'])}", f"Qty: {total_qty}", width))
    add(two_cols("Subtotal", f"{data['subtotal']:.2f}", width))
    if data["discount"]:
        add(two_cols("Discount", f"-{data['discount']:.2f}", width))
    add(two_cols("GST", f"{data['gst']:.2f}", width))
    separator("=")
    add(two_cols("TOTAL", f"Rs.{data['grand_total']:.2f}", width), True)
    separator("=")

    # how it was paid
    payments = data.get("payments") or []
    for method, amount, detail in payments:
        add(two_cols(method, f"{amount:.2f}", width))
    if len(payments) == 1 and payments[0][2]:
        for part in wrap(payments[0][2], width):
            add(part)

    # loyalty points
    loyalty = data.get("loyalty")
    if loyalty and (loyalty.get("earned") or loyalty.get("redeemed")):
        separator()
        if loyalty.get("redeemed"):
            add(two_cols("Points used", str(loyalty["redeemed"]), width))
        if loyalty.get("earned"):
            add(two_cols("Points earned", str(loyalty["earned"]), width))
        if loyalty.get("balance") is not None:
            add(two_cols("Points balance", str(loyalty["balance"]), width))

    separator()
    add(center("Thank you! Visit again.", width))
    return lines

# what the printer will really print (characters it can't print become ?)
def lines_to_text(lines):
    text = "\n".join(line for line, bold in lines)
    return text.encode("cp437", errors="replace").decode("cp437")

# raw ESC/POS bytes, send this file straight to the printer
def lines_to_escpos(lines):
    ESC = b"\x1b"
    GS = b"\x1d"

    out = bytearray()
    out += ESC + b"@"           # reset the printer
    out += ESC + b"t\x00"       # code page 437

    for text, bold in lines:
        if bold:
            out += ESC + b"E\x01"
        out += text.encode("cp437", errors="replace") + b"\n"
        if bold:
            out += ESC + b"E\x00"

    out += b"\n\n\n"            # feed some paper
    out += GS + b"V\x42\x00"    # cut
    return bytes(out)
