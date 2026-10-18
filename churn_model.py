import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score

print("=== RETAILPULSE STEP 5: CUSTOMER CHURN PREDICTION ===")

os.makedirs("outputs", exist_ok=True)
df = pd.read_csv("outputs/retail_cleaned.csv")

df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

df = df.dropna(subset=["InvoiceDate", "CustomerID", "Quantity", "UnitPrice"])
df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0) & (~df["InvoiceNo"].astype(str).str.startswith("C"))].copy()
df["Sales"] = df["Quantity"] * df["UnitPrice"]

last_date = df["InvoiceDate"].max()
cutoff_date = last_date - pd.Timedelta(days=90)
history = df[df["InvoiceDate"] <= cutoff_date].copy()
future = df[df["InvoiceDate"] > cutoff_date].copy()

features = history.groupby("CustomerID").agg(
    Recency=("InvoiceDate", lambda x: (cutoff_date - x.max()).days),
    Frequency=("InvoiceNo", "nunique"),
    Monetary=("Sales", "sum")
)

features["AverageOrderValue"] = features["Monetary"] / features["Frequency"]
first_purchase = history.groupby("CustomerID")["InvoiceDate"].min()
features["TenureDays"] = (cutoff_date - first_purchase).dt.days

future_customers = set(future["CustomerID"].unique())
features["Churn"] = (~features.index.isin(future_customers)).astype(int)
features = features.replace([np.inf, -np.inf], np.nan).dropna()

if features["Churn"].nunique() < 2:
    raise ValueError("Only one churn class was found. Check the dataset and date range.")

X = features[["Recency", "Frequency", "Monetary", "AverageOrderValue", "TenureDays"]]
y = features["Churn"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

model = RandomForestClassifier(
    n_estimators=200, random_state=42, class_weight="balanced", min_samples_leaf=2
)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)[:, 1]

print("\nLast transaction date:", last_date)
print("Cutoff date:", cutoff_date)
print("Customers analysed:", len(features))
print("Churn rate:", round(y.mean() * 100, 2), "%")
print("Accuracy:", round(accuracy_score(y_test, predictions), 4))
if y_test.nunique() == 2:
    print("ROC-AUC:", round(roc_auc_score(y_test, probabilities), 4))
print("\nClassification Report:\n", classification_report(y_test, predictions, zero_division=0))
print("Confusion Matrix:\n", confusion_matrix(y_test, predictions))

with open("outputs/churn_metrics.txt", "w", encoding="utf-8") as f:
    f.write(f"Last transaction date: {last_date}\nCutoff date: {cutoff_date}\n")
    f.write(f"Customers analysed: {len(features)}\nChurn rate: {y.mean() * 100:.2f}%\n")
    f.write(f"Accuracy: {accuracy_score(y_test, predictions):.4f}\n")
    if y_test.nunique() == 2:
        f.write(f"ROC-AUC: {roc_auc_score(y_test, probabilities):.4f}\n")
    f.write("\nClassification Report:\n" + classification_report(y_test, predictions, zero_division=0))
    f.write("\nConfusion Matrix:\n" + str(confusion_matrix(y_test, predictions)))

importance = pd.DataFrame({
    "Feature": X.columns,
    "Importance": model.feature_importances_
}).sort_values("Importance", ascending=False)

importance.to_csv("outputs/churn_feature_importance.csv", index=False)

plt.figure(figsize=(9, 5))
plt.barh(importance["Feature"], importance["Importance"])
plt.gca().invert_yaxis()
plt.title("Customer Churn Prediction: Feature Importance")
plt.xlabel("Importance")
plt.tight_layout()
plt.savefig("outputs/churn_feature_importance.png", dpi=150)
plt.close()

results = features.copy()
results["ChurnProbability"] = model.predict_proba(X)[:, 1]
results["PredictedChurn"] = (results["ChurnProbability"] >= 0.5).astype(int)
results.index.name = "CustomerID"
results.reset_index().to_csv("outputs/churn_predictions.csv", index=False)

print("\nSaved churn predictions, metrics, feature importance CSV and graph.")
print("STEP 5 COMPLETED SUCCESSFULLY")
