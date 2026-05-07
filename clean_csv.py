import csv
import re
from datetime import datetime

input_file = r"C:\Users\rebec\Documents\Demo\sales_pipeline\data\raw\sales_data.csv"
output_file = r"C:\Users\rebec\Documents\sales_pipeline_clean\sales_data_clean.csv"

def parse_date(date_str):
    date_str = str(date_str).strip()
    for fmt in ["%m/%d/%Y", "%d-%m-%Y", "%d-%b-%y", "%d.%m.%Y", "%d/%m/%Y", "%b/%d/%Y", "%d-%b-%Y", "%m.%d.%Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue
    return ""

def clean_price(price_str):
    if str(price_str).lower() in ["", "na", "error"]:
        return ""
    cleaned = re.sub(r"[^\d\.]", "", str(price_str))
    try:
        return str(float(cleaned))
    except:
        return ""

def clean_discount(discount_str):
    if str(discount_str).strip() == "":
        return "0"
    cleaned = re.sub(r"[^\d\.]", "", str(discount_str))
    try:
        return str(float(cleaned))
    except:
        return "0"

with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    
    header = next(reader)
    writer.writerow(["date", "store_id", "product_name", "quantity", "price", "customer_type", "payment_method", "transaction_id", "discount_pct", "region"])
    
    for row in reader:
        if len(row) < 10:
            continue
            
        date = parse_date(row[0])
        store_id = str(row[1]).strip().upper()
        product_name = str(row[2]).strip()
        quantity = str(row[3]).strip()
        quantity = quantity if quantity.isdigit() and int(quantity) > 0 else ""
        price = clean_price(row[4])
        customer_type = str(row[5]).strip().capitalize() if row[5] else ""
        payment_method = str(row[6]).strip() if row[6] else "Unknown"
        transaction_id = str(row[7]).strip() if row[7] else ""
        discount_pct = clean_discount(row[8])
        region = str(row[9]).strip().upper()
        
        writer.writerow([date, store_id, product_name, quantity, price, customer_type, payment_method, transaction_id, discount_pct, region])

print(f"Cleaned file saved to: {output_file}")