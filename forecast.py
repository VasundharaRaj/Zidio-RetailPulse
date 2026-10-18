import pandas as pd
import matplotlib.pyplot as plt
import os

print("=== RETAILPULSE STEP 3: DEMAND FORECASTING ===")

df = pd.read_csv("outputs/retail_cleaned.csv")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

# Use positive-quantity, positive-price sales for demand analysis
sales_df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)].copy()
sales_df["Sales"] = sales_df["Quantity"] * sales_df["UnitPrice"]

monthly_sales = (
    sales_df.set_index("InvoiceDate")["Sales"]
    .resample("MS")
    .sum()
)

print("\nMonthly sales:")
print(monthly_sales)

# Simple baseline forecast using the average of the latest 3 available months
forecast_value = monthly_sales.tail(3).mean()

future_dates = pd.date_range(
    start=monthly_sales.index.max() + pd.offsets.MonthBegin(1),
    periods=3,
    freq="MS"
)

forecast = pd.DataFrame({
    "Month": future_dates,
    "ForecastSales": [forecast_value] * 3
})

os.makedirs("outputs", exist_ok=True)
forecast.to_csv("outputs/demand_forecast.csv", index=False)

plt.figure(figsize=(12, 5))
plt.plot(monthly_sales.index, monthly_sales.values, marker="o", label="Historical sales")
plt.plot(future_dates, forecast["ForecastSales"], marker="o", linestyle="--", label="Baseline forecast")
plt.title("RetailPulse: Monthly Sales and 3-Month Baseline Forecast")
plt.xlabel("Month")
plt.ylabel("Sales")
plt.legend()
plt.tight_layout()
plt.savefig("outputs/demand_forecast.png")
plt.close()

print("\n3-month baseline forecast:")
print(forecast.to_string(index=False))
print("\nForecast CSV: outputs/demand_forecast.csv")
print("Forecast graph: outputs/demand_forecast.png")
print("\nSTEP 3 COMPLETED SUCCESSFULLY")
