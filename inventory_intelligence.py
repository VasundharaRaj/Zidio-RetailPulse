import pandas as pd
import numpy as np
import os

print("=== RETAILPULSE INVENTORY INTELLIGENCE ===")

os.makedirs("outputs", exist_ok=True)

data_path = "outputs/retail_cleaned.csv"
if not os.path.exists(data_path):
    raise FileNotFoundError(f"Required dataset not found: {data_path}")

df = pd.read_csv(data_path, low_memory=False)

required = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Dataset is missing required columns: {missing}")

df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")

df = df.dropna(subset=["InvoiceDate", "StockCode", "Quantity"]).copy()
df = df[
    (df["Quantity"] > 0) &
    (~df["InvoiceNo"].astype(str).str.startswith("C"))
].copy()

if df.empty:
    raise ValueError("No valid positive-quantity sales transactions were found.")

reference_date = df["InvoiceDate"].max()
window_start = reference_date - pd.Timedelta(days=89)
recent = df[df["InvoiceDate"] >= window_start].copy()

# Calculate product demand over a 90-calendar-day window.
recent_demand = recent.groupby("StockCode").agg(
    RecentUnitsSold=("Quantity", "sum"),
    ProductDescription=("Description", "first")
).reset_index()

all_time = df.groupby("StockCode").agg(
    TotalUnitsSold=("Quantity", "sum"),
    LastSoldDate=("InvoiceDate", "max")
).reset_index()

inventory = all_time.merge(recent_demand, on="StockCode", how="left")
inventory["RecentUnitsSold"] = inventory["RecentUnitsSold"].fillna(0)
inventory["ProductDescription"] = inventory["ProductDescription"].fillna("Unknown product")

inventory["AverageDailyDemand"] = inventory["RecentUnitsSold"] / 90.0

# The following inventory and supplier values are SIMULATED.
# They are not actual warehouse counts or verified supplier lead times.
def stable_number(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits[-6:] or "1")

inventory["SimulatedLeadTimeDays"] = inventory["StockCode"].apply(
    lambda x: 3 + stable_number(x) % 12
)

inventory["SimulatedStockOnHand"] = inventory.apply(
    lambda row: int(round(
        row["AverageDailyDemand"] *
        (1 + stable_number(row["StockCode"]) % 40)
    )),
    axis=1
)

inventory["SafetyStock"] = np.ceil(
    inventory["AverageDailyDemand"] *
    inventory["SimulatedLeadTimeDays"] * 0.5
).astype(int)

inventory["ReorderPoint"] = np.ceil(
    inventory["AverageDailyDemand"] *
    inventory["SimulatedLeadTimeDays"] +
    inventory["SafetyStock"]
).astype(int)

inventory["DaysOfCover"] = np.where(
    inventory["AverageDailyDemand"] > 0,
    inventory["SimulatedStockOnHand"] / inventory["AverageDailyDemand"],
    np.inf
)

def risk_level(row):
    if row["AverageDailyDemand"] <= 0:
        return "No recent demand"
    if row["SimulatedStockOnHand"] <= row["ReorderPoint"]:
        return "High"
    if row["DaysOfCover"] <= row["SimulatedLeadTimeDays"] + 7:
        return "Medium"
    return "Low"

inventory["StockoutRisk"] = inventory.apply(risk_level, axis=1)

inventory["RecommendedReorderQty"] = np.where(
    inventory["AverageDailyDemand"] > 0,
    np.maximum(
        0,
        np.ceil(
            inventory["AverageDailyDemand"] * 30 -
            inventory["SimulatedStockOnHand"]
        )
    ),
    0
).astype(int)

inventory["DataType"] = "DEMO ONLY: simulated stock and lead time"
inventory["ReferenceDate"] = reference_date.strftime("%Y-%m-%d")

inventory = inventory.sort_values(
    ["StockoutRisk", "DaysOfCover"],
    ascending=[True, True]
)

output_path = "outputs/inventory_intelligence.csv"
inventory.to_csv(output_path, index=False)

alerts = inventory[
    inventory["StockoutRisk"].isin(["High", "Medium"])
].copy()
alerts.to_csv("outputs/stockout_risk_alerts.csv", index=False)

summary_path = "outputs/inventory_intelligence_notes.txt"
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("RETAILPULSE INVENTORY INTELLIGENCE\n")
    f.write("Historical demand is calculated from transaction data.\n")
    f.write("Stock-on-hand and supplier lead times are simulated demonstration values.\n")
    f.write("These results must not be treated as actual warehouse inventory.\n")
    f.write(f"Reference date in historical dataset: {reference_date}\n")
    f.write(f"Products analysed: {len(inventory)}\n")
    f.write(f"High-risk products: {(inventory['StockoutRisk'] == 'High').sum()}\n")
    f.write(f"Medium-risk products: {(inventory['StockoutRisk'] == 'Medium').sum()}\n")

print("Historical data reference date:", reference_date)
print("Products analysed:", len(inventory))
print("High-risk products:", int((inventory["StockoutRisk"] == "High").sum()))
print("Medium-risk products:", int((inventory["StockoutRisk"] == "Medium").sum()))
print("Saved outputs/inventory_intelligence.csv")
print("Saved outputs/stockout_risk_alerts.csv")
print("Saved outputs/inventory_intelligence_notes.txt")
print("IMPORTANT: simulated inventory values are for demonstration only.")
