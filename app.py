import pandas as pd
import streamlit as st

from engine import run_model
from ui import irr_fmt, moic_fmt, money_fmt, pct_fmt, render_sidebar

st.set_page_config(
    page_title="Condo Investment Model",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Rent to Own Web App!")

assumptions = render_sidebar("home")
result = run_model(assumptions)
metrics = result["metrics"]

st.page_link("pages/1_Cash_Flows.py", label="Open Cash Flows (under-the-hood calculations)")

if not metrics["buydown_schedule_valid"]:
    st.warning(
        "Rate buydown dollars and the year 1–5 buydown schedule must both be used "
        "or both be zero (Excel error check)."
    )

left, right = st.columns(2)


def _su_table(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    display = pd.DataFrame(
        {
            "Item": df["item"],
            "Amount ($)": df["amount"].map(lambda x: f"{x:,.0f}"),
            "% of Total": df["pct"].map(lambda x: f"{x * 100:.1f}%"),
        }
    )
    return display


with left:
    st.subheader("Sources of Funds")
    st.dataframe(_su_table(result["sources"]), hide_index=True, width="stretch")

with right:
    st.subheader("Uses of Funds")
    st.dataframe(_su_table(result["uses"]), hide_index=True, width="stretch")

if metrics["balanced"]:
    st.success("Sources & Uses Balance Check: BALANCED")
else:
    st.error(f"Sources & Uses Balance Check: OUT OF BALANCE ({money_fmt(metrics['balance'])})")

st.subheader("Executive Return Summary")
c1, c2, c3 = st.columns(3)
c1.metric(
    "Holding Period",
    f"{metrics['holding_period']} Years",
    help="Target investment holding horizon, through the planned exit year.",
)
c2.metric(
    "Initial Equity Invested",
    money_fmt(metrics["equity"]),
    help="Total cash required at acquisition (year 0).",
)
c3.metric(
    "Project Levered IRR",
    irr_fmt(metrics["irr"]),
    help="Annualized internal rate of return on levered cash flows over the hold.",
)

_, c5, c6 = st.columns(3)
c5.metric(
    "Total Levered Cash Flows",
    money_fmt(metrics["total_levered_cf"]),
    help="Sum of positive levered cash flows received over the hold, including disposition.",
)
c6.metric(
    "Equity Multiple (MOIC)",
    moic_fmt(metrics["moic"]),
    help="Total levered cash flows divided by initial equity invested.",
)

c7, c8, c9 = st.columns(3)
c7.metric(
    "Projected Gross Exit Price",
    money_fmt(metrics["exit_price"]),
    help="Estimated gross sale price at exit, before selling costs and loan payoff.",
)
c8.metric(
    "Asset Growth (gross YoY)",
    pct_fmt(metrics["asset_growth"]),
    help="Compound annual growth from the purchase price to the projected exit price.",
)
c9.metric(
    "Per Annum Carrying Cost",
    pct_fmt(metrics["carrying_cost"]),
    help="Annual HOA, property taxes, and insurance as a percent of the purchase price.",
)
