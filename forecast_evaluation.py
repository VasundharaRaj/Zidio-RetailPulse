import os
import numpy as np
import pandas as pd

print("=== RETAILPULSE FORECAST EVALUATION ===")
os.makedirs("outputs", exist_ok=True)

path = "outputs/retail_cleaned.csv"
if not os.path.exists(path):
    raise FileNotFoundError(f"Dataset not found: {path}")

df = pd.read_csv(path, low_memory=False)
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

df = df.dropna(subset=["InvoiceDate", "Quantity", "UnitPrice"])
df = df[
    (df["Quantity"] > 0) &
    (df["UnitPrice"] > 0) &
    (~df["InvoiceNo"].astype(str).str.startswith("C"))
].copy()

df["Sales"] = df["Quantity"] * df["UnitPrice"]

monthly = (
    df.set_index("InvoiceDate")["Sales"]
    .resample("MS")
    .sum()
    .asfreq("MS", fill_value=0)
)

if len(monthly) < 6:
    raise ValueError("At least six months of data are required for this evaluation.")

# Hold out the final three months; do not use them to fit the baseline.
train = monthly.iloc[:-3]
test = monthly.iloc[-3:]

baseline_value = train.tail(3).mean()
predictions = np.repeat(baseline_value, len(test))

comparison = pd.DataFrame({
    "Month": test.index,
    "ActualSales": test.values,
    "PredictedSales": predictions
})

comparison["AbsoluteError"] = (
    comparison["ActualSales"] - comparison["PredictedSales"]
).abs()
comparison["SquaredError"] = (
    comparison["ActualSales"] - comparison["PredictedSales"]
) ** 2

mae = comparison["AbsoluteError"].mean()
rmse = np.sqrt(comparison["SquaredError"].mean())

nonzero = comparison["ActualSales"] != 0
if nonzero.any():
    mape = (
        comparison.loc[nonzero, "AbsoluteError"] /
        comparison.loc[nonzero, "ActualSales"].abs()
    ).mean() * 100
else:
    mape = np.nan

comparison.to_csv("outputs/forecast_backtest.csv", index=False)

with open("outputs/forecast_metrics.txt", "w", encoding="utf-8") as f:
    f.write("RETAILPULSE FORECAST BACKTEST\n")
    f.write("Model: mean of the previous three training months\n")
    f.write("Evaluation: final three months held out from training\n")
    f.write("MAE: {:.2f}\n".format(mae))
    f.write("RMSE: {:.2f}\n".format(rmse))
    f.write("MAPE: {}\n".format("undefined (zero actual values)" if pd.isna(mape) else "{:.2f}%".format(mape)))
    f.write("\nThese are historical holdout metrics, not a guarantee of future accuracy.\n")

print("\nTraining months:", len(train))
print("Holdout months:", len(test))
print("\nActual vs predicted:")
print(comparison[["Month", "ActualSales", "PredictedSales", "AbsoluteError"]].to_string(index=False))
print("\nMAE:", round(mae, 2))
print("RMSE:", round(rmse, 2))
print("MAPE:", "undefined" if pd.isna(mape) else f"{mape:.2f}%")
print("\nSaved outputs/forecast_backtest.csv")
print("Saved outputs/forecast_metrics.txt")
print("\nFORECAST EVALUATION COMPLETED")
