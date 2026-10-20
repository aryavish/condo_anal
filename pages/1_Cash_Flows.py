import altair as alt
import pandas as pd
import streamlit as st

from engine import run_model
from ui import money_fmt, render_sidebar

st.set_page_config(
    page_title="Cash Flows",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Rent to Own Cash Flow Projected!")

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
st.bar_chart(chart_df, alt="Net levered cash flow by year through the exit")

st.subheader("Equity Built over the Hold")
st.caption(
    "Principal paydown is the portion of debt service covered by NOI. "
    "Asset appreciation compounds the purchase price at the gross year-over-year growth rate."
)
growth = metrics["asset_growth"] if metrics["asset_growth"] is not None else 0.0
equity_df = pd.DataFrame(
    {
        "Year": cf["Year"],
        "Equity built from principal paydown": (-cf["Principal Paydown"]).cumsum(),
        "Equity from asset appreciation": assumptions.purchase_price * ((1.0 + growth) ** cf["Year"] - 1.0),
    }
)
equity_long = equity_df.melt("Year", var_name="Source", value_name="Equity built ($)")
last_year = int(equity_df["Year"].max())
equity_chart = (
    alt.Chart(equity_long)
    .mark_line()
    .encode(
        x=alt.X(
            "Year:Q",
            title="Year",
            scale=alt.Scale(domain=[0, last_year], nice=False, clamp=True),
            axis=alt.Axis(tickMinStep=1),
        ),
        y=alt.Y("Equity built ($):Q", title="Equity built ($)"),
        color=alt.Color("Source:N", title=None),
    )
)
st.altair_chart(
    equity_chart,
    alt="Equity from principal paydown and from asset appreciation over the hold",
)

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
