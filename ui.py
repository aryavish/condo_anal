"""Shared Streamlit sidebar for yellow Assumption inputs."""

from __future__ import annotations

import streamlit as st

from engine import Assumptions

STORE = "_assumption_store"
_STAMP = "_defaults_stamp"


def _pct_points(rate: float) -> float:
    return round(rate * 100.0, 6)


def _defaults_from_assumptions() -> dict:
    assumptions = Assumptions()
    defaults = {
        "purchase_price": float(assumptions.purchase_price),
        "closing_costs": float(assumptions.closing_costs),
        "initial_renovation": float(assumptions.initial_renovation),
        "seller_concessions": float(assumptions.seller_concessions),
        "ltv_pct": _pct_points(assumptions.ltv),
        "mortgage_rate_pct": _pct_points(assumptions.mortgage_rate),
        "loan_term_years": int(assumptions.loan_term_years),
        "rate_buydown": float(assumptions.rate_buydown),
        "gross_annual_rent": float(assumptions.gross_annual_rent),
        "vacancy_rate_pct": _pct_points(assumptions.vacancy_rate),
        "annual_hoa": float(assumptions.annual_hoa),
        "annual_taxes": float(assumptions.annual_taxes),
        "annual_insurance": float(assumptions.annual_insurance),
        "growth_rate_pct": _pct_points(assumptions.growth_rate),
        "exit_year": int(assumptions.exit_year),
        "exit_price": float(assumptions.exit_price),
        "cost_of_sale_rate_pct": _pct_points(assumptions.cost_of_sale_rate),
    }
    for year in range(1, 6):
        defaults[f"buydown_y{year}_pct"] = _pct_points(assumptions.buydown_by_year.get(year, 0.0))
    return defaults


DEFAULTS = _defaults_from_assumptions()


def _store() -> dict:
    stored = st.session_state.setdefault(STORE, {})
    stamp = tuple(sorted(DEFAULTS.items()))
    if stored.get(_STAMP) != stamp:
        stored.update(DEFAULTS)
        stored[_STAMP] = stamp
        for name, value in DEFAULTS.items():
            suffix = f"__{name}"
            for key in list(st.session_state.keys()):
                if str(key).endswith(suffix):
                    st.session_state[key] = value
    for key, value in DEFAULTS.items():
        stored.setdefault(key, value)
    return stored


def _widget_key(page: str, name: str) -> str:
    return f"{page}__{name}"


def _number(
    page: str,
    name: str,
    label: str,
    *,
    min_value,
    max_value=None,
    step,
    format: str,
    help_text: str,
    as_int: bool = False,
):
    stored = _store()
    wk = _widget_key(page, name)
    kwargs = {
        "label": label,
        "min_value": min_value,
        "step": step,
        "format": format,
        "key": wk,
    }
    if help_text:
        kwargs["help"] = help_text
    if max_value is not None:
        kwargs["max_value"] = max_value
    if wk not in st.session_state:
        value = stored[name]
        kwargs["value"] = int(value) if as_int else float(value)
    result = st.number_input(**kwargs)
    stored[name] = int(result) if as_int else float(result)
    return stored[name]


def _money(page: str, name: str, label: str, help_text: str) -> float:
    return float(
        _number(
            page,
            name,
            label,
            min_value=0.0,
            step=1000.0,
            format="%.0f",
            help_text=help_text,
        )
    )


def _pct(page: str, name: str, label: str, help_text: str) -> float:
    return (
        float(
            _number(
                page,
                name,
                label,
                min_value=0.0,
                max_value=100.0,
                step=0.25,
                format="%.2f",
                help_text=help_text,
            )
        )
        / 100.0
    )


def render_sidebar(page: str) -> Assumptions:
    with st.sidebar:
        st.header("Input Parameters")

        st.subheader("Acquisition")
        purchase_price = _money(page, "purchase_price", "Purchase Price ($)", "Agreed purchase contract price")
        closing_costs = _money(page, "closing_costs", "Closing Costs ($)", "Escrow, title, legal & transfer tax")
        initial_renovation = _money(
            page,
            "initial_renovation",
            "Initial Renovation & Setup ($)",
            "Immediate unit repairs & capital setup",
        )
        seller_concessions = _money(
            page,
            "seller_concessions",
            "Seller Concessions ($)",
            "Seller credit toward buyer closing costs",
        )

        st.subheader("Financing")
        ltv = _pct(page, "ltv_pct", "Loan-to-Value (%)", "Senior mortgage debt financing ratio")
        mortgage_rate = _pct(
            page,
            "mortgage_rate_pct",
            "Annual Mortgage Interest Rate (%)",
            "Fixed annual mortgage loan interest rate",
        )
        loan_term_years = int(
            _number(
                page,
                "loan_term_years",
                "Loan Term (Years)",
                min_value=1,
                max_value=40,
                step=1,
                format="%d",
                help_text="Mortgage amortization term",
                as_int=True,
            )
        )
        rate_buydown = _money(
            page,
            "rate_buydown",
            "Rate Buydown ($)",
            "Points or upfront fee to buy down interest rate",
        )

        st.subheader("Operations")
        gross_annual_rent = _money(
            page,
            "gross_annual_rent",
            "Gross Annual Rental Income ($ / yr)",
            "Base market rent",
        )
        vacancy_rate = _pct(
            page,
            "vacancy_rate_pct",
            "Vacancy & Credit Loss Rate (%)",
            "Allowance for tenant turnover / vacancy",
        )
        annual_hoa = _money(page, "annual_hoa", "Annual HOA Dues ($ / yr)", "Condominium association dues")
        annual_taxes = _money(
            page,
            "annual_taxes",
            "Annual Property Taxes ($ / yr)",
            "Local municipal property assessment",
        )
        annual_insurance = _money(
            page,
            "annual_insurance",
            "Annual Property Insurance ($ / yr)",
            "Condo hazard & liability insurance",
        )
        growth_rate = _pct(
            page,
            "growth_rate_pct",
            "Annual Rent & Expense Growth (%)",
            "Annual inflation & market growth rate",
        )

        st.subheader("Exit")
        exit_year = int(
            _number(
                page,
                "exit_year",
                "Target Exit Year",
                min_value=1,
                max_value=30,
                step=1,
                format="%d",
                help_text="Planned disposition year within 30-year horizon",
                as_int=True,
            )
        )
        exit_price = _money(
            page,
            "exit_price",
            "Projected Exit Price ($)",
            "Estimated gross disposition value at exit",
        )
        cost_of_sale_rate = _pct(
            page,
            "cost_of_sale_rate_pct",
            "Cost of Sale Rate (%)",
            "Broker commissions & closing legal at exit",
        )

        with st.expander("Rate buydown schedule (years 1–5)", expanded=False):
            st.caption("Interest-rate reduction applied in each hold year (Excel A24:B28).")
            buydown_by_year = {}
            for year in range(1, 6):
                name = f"buydown_y{year}_pct"
                pct_val = _number(
                    page,
                    name,
                    f"Year {year} buydown (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.25,
                    format="%.2f",
                    help_text="",
                )
                buydown_by_year[year] = float(pct_val) / 100.0

    return Assumptions(
        purchase_price=purchase_price,
        closing_costs=closing_costs,
        initial_renovation=initial_renovation,
        ltv=ltv,
        mortgage_rate=mortgage_rate,
        loan_term_years=loan_term_years,
        gross_annual_rent=gross_annual_rent,
        vacancy_rate=vacancy_rate,
        annual_hoa=annual_hoa,
        annual_taxes=annual_taxes,
        annual_insurance=annual_insurance,
        growth_rate=growth_rate,
        exit_year=exit_year,
        exit_price=exit_price,
        cost_of_sale_rate=cost_of_sale_rate,
        rate_buydown=rate_buydown,
        seller_concessions=seller_concessions,
        buydown_by_year=buydown_by_year,
    )


def money_fmt(value: float) -> str:
    return f"${value:,.0f}"


def pct_fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def irr_fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def moic_fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}x"
