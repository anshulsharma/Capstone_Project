import csv

def sql_val(v):
    if v is None or v.strip() == "":
        return "NULL"
    try:
        float(v)
        return v
    except ValueError:
        return "'" + v.replace("'", "''") + "'"

out = []
for table, path in [("customers", "data/customers.csv"),
                    ("products", "data/products.csv"),
                    ("orders", "data/orders.csv")]:
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            cols = ", ".join(row.keys())
            vals = ", ".join(sql_val(v) for v in row.values())
            out.append(f"INSERT INTO {table} ({cols}) VALUES ({vals});")

with open("sql/seed_data.sql", "w") as f:
    f.write("\n".join(out) + "\n")