import os
import pandas as pd
import matplotlib.pyplot as plt

print("=== RETAILPULSE STEP 6: INVENTORY ANALYSIS ===")

os.makedirs("outputs", exist_ok=True)

df = pd.read_csv("outputs/retail_cleaned.csv")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

df = df.dropna(subset=["InvoiceDate", "StockCode", "Quantity", "UnitPrice"])
df = df[
    (df["Quantity"] > 0) &
    (df["UnitPrice"] > 0) &
    (~df["InvoiceNo"].astype(str).str.startswith("C"))
].copy()

df["Sales"] = df["Quantity"] * df["UnitPrice"]

inventory = df.groupby("StockCode").agg(
    ProductDescription=("Description", "first"),
    UnitsSold=("Quantity", "sum"),
    TotalSales=("Sales", "sum"),
    NumberOfOrders=("InvoiceNo", "nunique"),
    LastSoldDate=("InvoiceDate", "max")
).reset_index()

reference_date = df["InvoiceDate"].max()
inventory["DaysSinceLastSale"] = (
    reference_date - inventory["LastSoldDate"]
).dt.days

inventory = inventory.sort_values("UnitsSold", ascending=False)
inventory.to_csv("outputs/inventory_analysis.csv", index=False)

top_products = inventory.head(10).sort_values("UnitsSold")

plt.figure(figsize=(11, 6))
plt.barh(
    top_products["StockCode"].astype(str),
    top_products["UnitsSold"]
)
plt.title("Top 10 Products by Units Sold")
plt.xlabel("Units Sold")
plt.ylabel("Product Code")
plt.tight_layout()
plt.savefig("outputs/top_products.png", dpi=150)
plt.close()

slow_products = inventory.sort_values(
    ["DaysSinceLastSale", "UnitsSold"],
    ascending=[False, True]
).head(20)

slow_products.to_csv("outputs/slow_moving_products.csv", index=False)

monthly = df.set_index("InvoiceDate").resample("MS")["Quantity"].sum()
monthly.to_csv("outputs/monthly_units_sold.csv", header=["UnitsSold"])

plt.figure(figsize=(11, 5))
plt.plot(monthly.index, monthly.values, marker="o")
plt.title("Monthly Units Sold")
plt.xlabel("Month")
plt.ylabel("Units Sold")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("outputs/monthly_units_sold.png", dpi=150)
plt.close()

print("\nProducts analysed:", len(inventory))
print("Total units sold:", int(inventory["UnitsSold"].sum()))
print("\nTop 10 products by units sold:")
print(inventory[["StockCode", "ProductDescription", "UnitsSold"]].head(10).to_string(index=False))

print("\nSaved files:")
print("- outputs/inventory_analysis.csv")
print("- outputs/slow_moving_products.csv")
print("- outputs/monthly_units_sold.csv")
print("- outputs/top_products.png")
print("- outputs/monthly_units_sold.png")
print("\nSTEP 6 COMPLETED SUCCESSFULLY")
