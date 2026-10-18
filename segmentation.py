import pandas as pd
import matplotlib.pyplot as plt
import os

print("=== RETAILPULSE STEP 4: CUSTOMER SEGMENTATION ===")

df = pd.read_csv("outputs/retail_cleaned.csv")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

# Exclude cancellations and non-positive purchases
df = df[
    (~df["IsCancelled"].astype(str).str.lower().isin(["true", "1"])) &
    (df["Quantity"] > 0) &
    (df["UnitPrice"] > 0) &
    (df["CustomerID"].notna())
].copy()

df["Sales"] = df["Quantity"] * df["UnitPrice"]

snapshot_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)

rfm = df.groupby("CustomerID").agg(
    Recency=("InvoiceDate", lambda x: (snapshot_date - x.max()).days),
    Frequency=("InvoiceNo", "nunique"),
    Monetary=("Sales", "sum")
).reset_index()

# Rank customers into 4 groups for each RFM measure
rfm["R_Score"] = pd.qcut(
    rfm["Recency"].rank(method="first"),
    4, labels=[4, 3, 2, 1]
).astype(int)

rfm["F_Score"] = pd.qcut(
    rfm["Frequency"].rank(method="first"),
    4, labels=[1, 2, 3, 4]
).astype(int)

rfm["M_Score"] = pd.qcut(
    rfm["Monetary"].rank(method="first"),
    4, labels=[1, 2, 3, 4]
).astype(int)

rfm["RFM_Score"] = (
    rfm["R_Score"].astype(str) +
    rfm["F_Score"].astype(str) +
    rfm["M_Score"].astype(str)
)

def assign_segment(row):
    if row["R_Score"] >= 3 and row["F_Score"] >= 3 and row["M_Score"] >= 3:
        return "Best Customers"
    elif row["R_Score"] >= 3 and row["F_Score"] >= 2:
        return "Loyal Customers"
    elif row["R_Score"] <= 2 and row["F_Score"] >= 3:
        return "At Risk"
    elif row["R_Score"] >= 3:
        return "Recent Customers"
    else:
        return "Other Customers"

rfm["Segment"] = rfm.apply(assign_segment, axis=1)

os.makedirs("outputs", exist_ok=True)
rfm.to_csv("outputs/customer_segments.csv", index=False)

segment_counts = rfm["Segment"].value_counts()
segment_counts.plot(kind="bar", figsize=(10, 5), title="Customer Segmentation")
plt.xlabel("Customer Segment")
plt.ylabel("Number of Customers")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig("outputs/customer_segments.png")
plt.close()

print("\nTotal customers segmented:", len(rfm))
print("\nCustomer segment counts:")
print(segment_counts)
print("\nSaved: outputs/customer_segments.csv")
print("Saved: outputs/customer_segments.png")
print("\nSTEP 4 COMPLETED SUCCESSFULLY")
