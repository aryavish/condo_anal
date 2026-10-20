import pandas as pd
import streamlit as st

from engine import run_model
from ui import money_fmt, render_sidebar

st.set_page_config(
    page_title="Cash Flows",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("30-Year Condo Investment Cash Flow Pro-Forma")
st.caption("Under-the-hood calculations through the selected exit year.")

assumptions = render_sidebar("cash_flows")
result = run_model(assumptions)
cf = result["cash_flows"]
metrics = result["metrics"]

st.page_link("app.py", label="Back to Sources / Uses & Returns")

st.subheader("Net Levered Cash Flow")
chart_df = pd.DataFrame(
    {
        "Year": cf["Year"],
        "Net Levered Cash Flow": cf["Net Levered Cash Flow"],
    }
).set_index("Year")
st.bar_chart(chart_df)

schedule = cf.set_index("Year").T
schedule.columns = [f"Year {int(year)}" for year in schedule.columns]
schedule.index.name = "Line item"
year_config = {
    col: st.column_config.NumberColumn(format="%,.0f") for col in schedule.columns
}

st.subheader("Cash Flow Schedule")
st.dataframe(
    schedule,
    column_config=year_config,
    width="stretch",
    alt="Cash flow line items across hold years",
)

st.caption(
    f"Loan {money_fmt(metrics['loan'])} · "
    f"Annual debt service {money_fmt(metrics['annual_pmt'])} · "
    f"Working capital {money_fmt(metrics['working_capital'])}"
)
