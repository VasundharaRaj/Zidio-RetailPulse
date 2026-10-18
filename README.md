# RetailPulse

Python retail analytics project covering data cleaning, demand forecasting, RFM customer segmentation, churn-risk estimation, product movement analysis and an interactive Streamlit dashboard.

## Run the dashboard
From the project root, install dependencies with `python -m pip install -r submission/requirements.txt`, then run `python -m streamlit run dashboard.py`.

## Important limitations
The data is historical (2010-2011). Forecasting is a simple baseline, churn uses an inactivity-window proxy, and inventory analysis does not include actual stock-on-hand or supplier lead times.
