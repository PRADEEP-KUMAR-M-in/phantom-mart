import os
import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)

# ---------------------------------------------------------------------
# Shop header details — edit these to change what appears on every PDF
# ---------------------------------------------------------------------
SHOP_NAME = "Phantom Mart"
SHOP_ADDRESS = "Global Mart, Chennai, Tamil Nadu, India"
SHOP_PHONE = "+91 1234567890"
SHOP_GST = "33ABCDE1234F1Z5"

# brand purple used for accents (matches styles.py PURPLE)
BRAND_COLOR = colors.HexColor("#6d28d9")
BRAND_LIGHT = colors.HexColor("#ede9fe")
TEXT_DIM = colors.HexColor("#555555")

# ---------------------------------------------------------------------
# Fonts
# The built in PDF fonts don't have the rupee sign, so we look for a
# normal font on the computer. You can also put DejaVuSans.ttf and
# DejaVuSans-Bold.ttf in a folder called "fonts" next to this file.
# If nothing is found we fall back to plain Helvetica and write "Rs."
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_CANDIDATES = [
    (os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf"), os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
CURRENCY = "Rs. "

for regular_path, bold_path in FONT_CANDIDATES:
    if os.path.exists(regular_path) and os.path.exists(bold_path):
        try:
            pdfmetrics.registerFont(TTFont("ShopFont", regular_path))
            pdfmetrics.registerFont(TTFont("ShopFont-Bold", bold_path))
        except Exception:
            continue
        FONT = "ShopFont"
        FONT_BOLD = "ShopFont-Bold"
        CURRENCY = "₹"
        break

def money(amount):
    return f"{CURRENCY}{amount:,.2f}"

_shop_title_style = ParagraphStyle(
    "ShopTitle", fontName=FONT_BOLD,
    fontSize=18, leading=22, textColor=BRAND_COLOR, alignment=TA_CENTER, spaceAfter=2,
)
_shop_sub_style = ParagraphStyle(
    "ShopSub", fontName=FONT,
    fontSize=9, textColor=TEXT_DIM, alignment=TA_CENTER, leading=12,
)
_doc_title_style = ParagraphStyle(
    "DocTitle", fontName=FONT_BOLD,
    fontSize=13, leading=16, textColor=colors.HexColor("#111111"), spaceBefore=10, spaceAfter=6,
)
_normal_style = ParagraphStyle("Normal2", fontName=FONT, fontSize=10, leading=12)
_small_style = ParagraphStyle("Small", fontName=FONT, fontSize=8.5, leading=11, textColor=TEXT_DIM)


def _shop_header():
    # letterhead used on every PDF
    elems = [
        Paragraph(SHOP_NAME.upper(), _shop_title_style),
        Paragraph(
            f"{SHOP_ADDRESS}<br/>Phone: {SHOP_PHONE} &nbsp;|&nbsp; GSTIN: {SHOP_GST}",
            _shop_sub_style,
        ),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.2, color=BRAND_COLOR),
        Spacer(1, 10),
    ]
    return elems


def _footer(text="Thank you for shopping with Phantom Mart!"):
    return [
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cccccc")),
        Spacer(1, 6),
        Paragraph(text, ParagraphStyle(
            "Footer", fontName=FONT, fontSize=9,
            textColor=TEXT_DIM, alignment=TA_CENTER,
        )),
    ]


# ---------------------------------------------------------------------
# 1. BILL / RECEIPT PDF
# ---------------------------------------------------------------------
def generate_bill_pdf(filepath, bill_number, customer_name, payment_method,
                       payment_detail, cart_items, subtotal, discount,
                       gst, grand_total, cashier_name,
                       sale_date=None, sale_time=None, payments=None, loyalty=None):

    # payments = list of (method, amount, detail), shown only when the bill was split
    # loyalty = {"earned": n, "redeemed": n, "balance": n (optional)}
    now = datetime.datetime.now()
    sale_date = sale_date or now.strftime("%d %b %Y")
    sale_time = sale_time or now.strftime("%I:%M %p")

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"Bill {bill_number}",
    )

    elements = []
    elements += _shop_header()
    elements.append(Paragraph("SALES INVOICE / BILL", _doc_title_style))

    # bill meta info (two columns)
    meta_style = ParagraphStyle("Meta", fontName=FONT, fontSize=9.5, leading=11)

    meta_data = [
        ["Bill Number:", bill_number, "Date:", sale_date],
        ["Customer:", customer_name, "Time:", sale_time],
        ["Cashier:", cashier_name, "Payment:", payment_method],
    ]
    if payment_detail:
        meta_data.append(["", "", "Detail:", Paragraph(payment_detail, meta_style)])

    meta_table = Table(meta_data, colWidths=[80, 150, 55, 185])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
        ("TEXTCOLOR", (0, 0), (0, -1), TEXT_DIM),
        ("TEXTCOLOR", (2, 0), (2, -1), TEXT_DIM),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # cart items table, long product names wrap instead of running into the next column
    cell_style = ParagraphStyle("Cell", fontName=FONT, fontSize=9.5, leading=11)

    item_rows = [["#", "Product", "Qty", f"Unit Price ({CURRENCY.strip()})", f"Total ({CURRENCY.strip()})"]]
    for i, item in enumerate(cart_items, start=1):
        item_total = item["price"] * item["qty"]
        item_rows.append([
            str(i), Paragraph(item["name"], cell_style), str(item["qty"]),
            f"{item['price']:.2f}", f"{item_total:.2f}",
        ])

    items_table = Table(item_rows, colWidths=[22, 218, 40, 90, 90], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # totals summary (right aligned block)
    totals_data = [["Subtotal", money(subtotal)]]
    if discount > 0:
        totals_data.append(["Discount", "-" + money(discount)])
    totals_data.append(["GST", money(gst)])
    totals_data.append(["Grand Total", money(grand_total)])

    totals_table = Table(totals_data, colWidths=[100, 100], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -2), 10),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("TEXTCOLOR", (0, -1), (-1, -1), BRAND_COLOR),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, BRAND_COLOR),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(totals_table)

    # split bills show how much was paid with each method
    if payments and len(payments) > 1:
        elements.append(Spacer(1, 8))
        paid_rows = [["Paid by", ""]]
        for payment in payments:
            paid_rows.append([payment[0], money(payment[1])])

        paid_table = Table(paid_rows, colWidths=[100, 100], hAlign="RIGHT")
        paid_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_DIM),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#cccccc")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(paid_table)

    # loyalty points used / earned on this bill
    if loyalty and (loyalty.get("earned") or loyalty.get("redeemed")):
        parts = []
        if loyalty.get("redeemed"):
            parts.append(f"used {loyalty['redeemed']}")
        if loyalty.get("earned"):
            parts.append(f"earned {loyalty['earned']}")
        if loyalty.get("balance") is not None:
            parts.append(f"balance {loyalty['balance']}")

        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            "Loyalty points: " + ", ".join(parts),
            ParagraphStyle("Loyalty", fontName=FONT, fontSize=9, textColor=TEXT_DIM, alignment=TA_RIGHT)
        ))

    elements += _footer()

    doc.build(elements)
    return filepath


# ---------------------------------------------------------------------
# 2. SALES REPORT PDF
# ---------------------------------------------------------------------
def generate_report_pdf(filepath, filter_label, sales_rows,
                         total_amount, total_discount, bill_count, avg_bill):
    """
    sales_rows: list of tuples
        (bill_number, customer_name, sale_date, sale_time,
         subtotal, discount, gst, grand_total, payment_method, cashier_name)
    """

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=16 * mm, bottomMargin=16 * mm,
        leftMargin=14 * mm, rightMargin=14 * mm,
        title="Sales Report",
    )

    elements = []
    elements += _shop_header()
    elements.append(Paragraph(f"SALES REPORT &nbsp;—&nbsp; {filter_label}", _doc_title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        _small_style,
    ))
    elements.append(Spacer(1, 10))

    # summary stat cards as a small table
    summary_data = [
        ["Total Sales", "Total Bills", "Total Discount", "Avg Bill Value"],
        [money(total_amount), str(bill_count), money(total_discount), money(avg_bill)],
    ]
    usable_width = doc.width - 12
    summary_width = usable_width / 4
    summary_table = Table(summary_data, colWidths=[summary_width] * 4)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_LIGHT),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, 1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 12),
        ("TEXTCOLOR", (0, 1), (-1, 1), BRAND_COLOR),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    # full sales table
    table_rows = [["Bill No", "Customer", "Date", "Time", "Subtotal", "Discount", "GST", "Grand Total", "Payment", "Cashier"]]
    for s in sales_rows:
        table_rows.append([
            s[0], s[1], s[2], s[3],
            f"{s[4]:.2f}", f"{s[5]:.2f}", f"{s[6]:.2f}", f"{s[7]:.2f}",
            s[8], s[9],
        ])

    if len(table_rows) == 1:
        elements.append(Paragraph("No sales found for this filter.", _normal_style))
    else:
        # these widths add up to more than the page, so shrink them to fit inside the margins
        col_widths = [55, 78, 55, 45, 48, 45, 40, 55, 48, 55]
        scale = usable_width / sum(col_widths)
        col_widths = [w * scale for w in col_widths]

        sales_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        sales_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(sales_table)

    elements += _footer("Phantom Mart POS System — Internal Sales Report")

    doc.build(elements)
    return filepath


# ---------------------------------------------------------------------
# 3. PRODUCTS / INVENTORY PDF
# ---------------------------------------------------------------------
def generate_products_pdf(filepath, filter_label, products_rows):
    """
    products_rows: list of tuples (name, category, selling_price, quantity)
    """

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title="Product List",
    )

    elements = []
    elements += _shop_header()
    elements.append(Paragraph(f"PRODUCT / INVENTORY LIST &nbsp;—&nbsp; {filter_label}", _doc_title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')} &nbsp;|&nbsp; {len(products_rows)} product(s)",
        _small_style,
    ))
    elements.append(Spacer(1, 10))

    cell_style = ParagraphStyle("ProdCell", fontName=FONT, fontSize=9, leading=11)

    table_rows = [["#", "Product Name", "Category", f"Price ({CURRENCY.strip()})", "Stock Qty"]]
    for i, p in enumerate(products_rows, start=1):
        name, category, price, qty = p[0], p[1], p[2], p[3]
        table_rows.append([str(i), Paragraph(name, cell_style), category, f"{price:.2f}", str(qty)])

    if len(table_rows) == 1:
        elements.append(Paragraph("No products found for this filter.", _normal_style))
    else:
        prod_table = Table(table_rows, colWidths=[25, 200, 110, 80, 65], repeatRows=1)
        prod_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(prod_table)

    elements += _footer("Phantom Mart POS System — Internal Inventory Report")

    doc.build(elements)
    return filepath
