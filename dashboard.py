import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="RetailPulse Dashboard",
    page_icon="📊",
    layout="wide"
)

BASE = "outputs"

@st.cache_data
def load_data():
    sales = pd.read_csv(os.path.join(BASE, "retail_cleaned.csv"), low_memory=False)
    sales["InvoiceDate"] = pd.to_datetime(sales["InvoiceDate"], errors="coerce")
    for col in ["Quantity", "UnitPrice"]:
        sales[col] = pd.to_numeric(sales[col], errors="coerce")
    sales["Sales"] = sales["Quantity"] * sales["UnitPrice"]
    return sales

st.title("📊 RetailPulse")
st.subheader("Retail Analytics and Decision Support Dashboard")
st.caption("Historical sales • Demand forecasting • Customer insights • Inventory analysis")

sales = load_data()

valid = sales.dropna(subset=["InvoiceDate", "Quantity", "UnitPrice"]).copy()
valid = valid[
    (valid["Quantity"] > 0) &
    (valid["UnitPrice"] > 0) &
    (~valid["InvoiceNo"].astype(str).str.startswith("C"))
].copy()

if "CustomerID" in valid.columns:
    valid["CustomerID"] = pd.to_numeric(valid["CustomerID"], errors="coerce")

min_date = valid["InvoiceDate"].min().date()
max_date = valid["InvoiceDate"].max().date()

with st.sidebar:
    st.header("Dashboard Filters")
    date_range = st.date_input(
        "Select transaction dates",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    st.caption("Filters apply to sales charts and KPIs.")

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = valid[
        (valid["InvoiceDate"].dt.date >= start_date) &
        (valid["InvoiceDate"].dt.date <= end_date)
    ].copy()
else:
    filtered = valid.copy()

total_sales = filtered["Sales"].sum()
total_units = filtered["Quantity"].sum()
total_orders = filtered["InvoiceNo"].nunique()
total_customers = (
    filtered["CustomerID"].nunique()
    if "CustomerID" in filtered.columns else 0
)

a, b, c, d = st.columns(4)
a.metric("Total Sales", f"£{total_sales:,.2f}")
b.metric("Units Sold", f"{total_units:,.0f}")
c.metric("Orders", f"{total_orders:,}")
d.metric("Unique Customers", f"{total_customers:,}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Monthly Sales Trend")
    monthly = (
        filtered.set_index("InvoiceDate")
        .resample("MS")["Sales"]
        .sum()
        .reset_index()
    )
    monthly.columns = ["Month", "Sales"]
    fig = px.line(
        monthly, x="Month", y="Sales",
        markers=True, title="Monthly Revenue"
    )
    st.plotly_chart(fig, width='stretch')

with right:
    st.subheader("Top-Selling Products")
    if os.path.exists(os.path.join(BASE, "inventory_analysis.csv")):
        inventory = pd.read_csv(os.path.join(BASE, "inventory_analysis.csv"))
        if "UnitsSold" in inventory.columns and "StockCode" in inventory.columns:
            top = inventory.nlargest(10, "UnitsSold").sort_values("UnitsSold")
            fig = px.bar(
                top, x="UnitsSold", y="StockCode",
                orientation="h", title="Top 10 by Units Sold"
            )
            st.plotly_chart(fig, width='stretch')
            st.dataframe(top.head(10), width='stretch')
        else:
            st.warning("The inventory file does not contain the expected columns.")
    else:
        st.info("Run inventory_analysis.py to generate product insights.")

st.divider()
st.subheader("Demand Forecast")

forecast_path = os.path.join(BASE, "demand_forecast.csv")
if os.path.exists(forecast_path):
    forecast = pd.read_csv(forecast_path)
    st.dataframe(forecast, width='stretch')

    date_col = next(
        (col for col in forecast.columns if col.lower() in ["month", "date", "ds"]),
        None
    )
    forecast_col = next(
        (col for col in forecast.columns
         if any(word in col.lower() for word in ["forecast", "predicted", "prediction", "yhat"])),
        None
    )

    if date_col and forecast_col:
        forecast[date_col] = pd.to_datetime(forecast[date_col], errors="coerce")
        forecast[forecast_col] = pd.to_numeric(forecast[forecast_col], errors="coerce")
        chart_data = forecast.dropna(subset=[date_col, forecast_col])
        if not chart_data.empty:
            fig = px.line(
                chart_data, x=date_col, y=forecast_col,
                markers=True, title="Forecasted Sales"
            )
            st.plotly_chart(fig, width='stretch')
    else:
        st.caption("Forecast results are displayed above; the file's column names did not match the automatic chart detector.")
else:
    st.warning("Demand forecast file not found.")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Customer Segmentation")
    segment_path = os.path.join(BASE, "customer_segments.csv")
    if os.path.exists(segment_path):
        segments = pd.read_csv(segment_path)
        segment_col = next(
            (col for col in segments.columns if "segment" in col.lower()),
            None
        )
        if segment_col:
            counts = segments[segment_col].fillna("Unknown").value_counts().reset_index()
            counts.columns = ["Segment", "Customers"]
            fig = px.bar(
                counts, x="Segment", y="Customers",
                title="Customers by Segment"
            )
            st.plotly_chart(fig, width='stretch')
            st.dataframe(counts, width='stretch')
        else:
            st.warning("No segment column was detected.")
            st.dataframe(segments.head(10), width='stretch')
    else:
        st.info("Customer segmentation file not found.")

with right:
    st.subheader("Customer Churn Risk")
    churn_path = os.path.join(BASE, "churn_predictions.csv")
    if os.path.exists(churn_path):
        churn = pd.read_csv(churn_path)
        prob_col = next(
            (col for col in churn.columns if "churnprobability" in col.lower()),
            None
        )
        pred_col = next(
            (col for col in churn.columns if col.lower() == "predictedchurn"),
            None
        )
        if prob_col:
            churn[prob_col] = pd.to_numeric(churn[prob_col], errors="coerce")
            st.metric(
                "Customers predicted at risk",
                f"{int((churn[prob_col] >= 0.5).sum()):,}"
            )
            fig = px.histogram(
                churn.dropna(subset=[prob_col]),
                x=prob_col, nbins=20,
                title="Distribution of Churn Probabilities"
            )
            st.plotly_chart(fig, width='stretch')
        elif pred_col:
            st.metric("Customers predicted at risk", f"{int((churn[pred_col] == 1).sum()):,}")
        st.dataframe(churn.head(10), width='stretch')
    else:
        st.info("Churn prediction file not found.")

st.divider()
st.subheader("Slow-Moving Products")
slow_path = os.path.join(BASE, "slow_moving_products.csv")
if os.path.exists(slow_path):
    slow = pd.read_csv(slow_path)
    st.dataframe(slow.head(20), width='stretch')
else:
    st.info("Slow-moving product report not found.")

st.caption(
    "RetailPulse prototype | Forecasts and churn predictions are model estimates, "
    "not guarantees. Sales transaction data does not provide current warehouse stock levels."
)


# RETAILPULSE INVENTORY INTELLIGENCE DASHBOARD SECTION
st.divider()
st.header("📦 Smart Inventory & Stockout Risk")
st.warning(
    "DEMONSTRATION MODE: Historical demand uses transaction data. "
    "Stock-on-hand and supplier lead times are simulated, not actual warehouse records."
)

smart_inventory_path = os.path.join(BASE, "inventory_intelligence.csv")
if os.path.exists(smart_inventory_path):
    smart_inventory = pd.read_csv(smart_inventory_path, low_memory=False)

    risk_counts = (
        smart_inventory["StockoutRisk"]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("Risk Level")
        .reset_index(name="Products")
    )

    high_risk = int((smart_inventory["StockoutRisk"] == "High").sum())
    medium_risk = int((smart_inventory["StockoutRisk"] == "Medium").sum())
    reorder_count = int((smart_inventory["RecommendedReorderQty"] > 0).sum())
    total_products = len(smart_inventory)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Products Analysed", f"{total_products:,}")
    k2.metric("High-Risk Products", f"{high_risk:,}")
    k3.metric("Medium-Risk Products", f"{medium_risk:,}")
    k4.metric("Products to Reorder", f"{reorder_count:,}")

    left, right = st.columns(2)

    with left:
        st.subheader("Products by Stockout Risk")
        risk_chart = px.bar(
            risk_counts,
            x="Risk Level",
            y="Products",
            color="Risk Level",
            title="Inventory Risk Distribution"
        )
        st.plotly_chart(risk_chart, width="stretch")

    with right:
        st.subheader("Products Needing Replenishment")
        reorder_top = smart_inventory[
            smart_inventory["RecommendedReorderQty"] > 0
        ].nlargest(10, "RecommendedReorderQty")

        if not reorder_top.empty:
            reorder_chart = px.bar(
                reorder_top.sort_values("RecommendedReorderQty"),
                x="RecommendedReorderQty",
                y="StockCode",
                orientation="h",
                title="Top 10 Suggested Reorder Quantities",
                hover_data=["ProductDescription", "StockoutRisk"]
            )
            st.plotly_chart(reorder_chart, width="stretch")
        else:
            st.info("No products currently have a positive suggested reorder quantity.")

    st.subheader("Inventory Risk Explorer")

    risk_options = ["All"] + sorted(
        smart_inventory["StockoutRisk"].dropna().astype(str).unique().tolist()
    )
    chosen_risk = st.selectbox("Filter by risk level", risk_options)

    search_product = st.text_input(
        "Search by product code or description",
        placeholder="Enter a product code or product name"
    )

    display_inventory = smart_inventory.copy()

    if chosen_risk != "All":
        display_inventory = display_inventory[
            display_inventory["StockoutRisk"].astype(str) == chosen_risk
        ]

    if search_product.strip():
        query = search_product.strip().lower()
        matches = (
            display_inventory["StockCode"].astype(str).str.lower().str.contains(query, na=False) |
            display_inventory["ProductDescription"].astype(str).str.lower().str.contains(query, na=False)
        )
        display_inventory = display_inventory[matches]

    display_columns = [
        "StockCode",
        "ProductDescription",
        "AverageDailyDemand",
        "SimulatedStockOnHand",
        "DaysOfCover",
        "SimulatedLeadTimeDays",
        "ReorderPoint",
        "StockoutRisk",
        "RecommendedReorderQty",
        "DataType"
    ]
    display_columns = [
        col for col in display_columns if col in display_inventory.columns
    ]

    st.dataframe(
        display_inventory[display_columns].head(500),
        width="stretch",
        hide_index=True
    )
    st.caption(
        f"Showing {min(len(display_inventory), 500):,} of "
        f"{len(display_inventory):,} matching products."
    )

    st.download_button(
        "Download filtered inventory CSV",
        data=display_inventory.to_csv(index=False).encode("utf-8"),
        file_name="retailpulse_inventory_intelligence.csv",
        mime="text/csv"
    )

    alert_path = os.path.join(BASE, "stockout_risk_alerts.csv")
    if os.path.exists(alert_path):
        with open(alert_path, "rb") as alert_file:
            st.download_button(
                "Download stockout risk alerts CSV",
                data=alert_file.read(),
                file_name="retailpulse_stockout_risk_alerts.csv",
                mime="text/csv"
            )
else:
    st.info(
        "Inventory intelligence file not found. "
        "Run inventory_intelligence.py first."
    )

import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.markdown("---")
st.header("Forecast Accuracy Evaluation")

metrics_path = os.path.join("outputs", "forecast_metrics.txt")
backtest_path = os.path.join("outputs", "forecast_backtest.csv")

if os.path.exists(metrics_path) and os.path.exists(backtest_path):
    with open(metrics_path, "r", encoding="utf-8") as f:
        st.text(f.read())

    backtest = pd.read_csv(backtest_path)
    backtest["Month"] = pd.to_datetime(backtest["Month"])

    fig = px.line(
        backtest,
        x="Month",
        y=["ActualSales", "PredictedSales"],
        markers=True,
        title="Actual vs Predicted Monthly Sales"
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Sales",
        legend_title="Series"
    )
    st.plotly_chart(fig, width="stretch")

    st.download_button(
        "Download Forecast Backtest CSV",
        data=backtest.to_csv(index=False).encode("utf-8"),
        file_name="forecast_backtest.csv",
        mime="text/csv"
    )
else:
    st.info("Run forecast_evaluation.py to generate the forecast evaluation files.")
