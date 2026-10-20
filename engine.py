"""Condo investment cash-flow engine (port of inv condo analysis.xlsx)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
import pandas as pd

HORIZON = 30


def excel_pmt(rate: float, nper: float, pv: float) -> float:
    """Excel PMT(rate, nper, pv) with type=0 and fv=0."""
    if nper == 0:
        return 0.0
    if rate == 0:
        return -pv / nper
    return -pv * rate * (1.0 + rate) ** nper / ((1.0 + rate) ** nper - 1.0)


def excel_irr(cashflows, guess: float = 0.1) -> float | None:
    """Newton IRR matching Excel IRR() on a regular annual series."""
    cfs = np.asarray(cashflows, dtype=float)
    if cfs.size < 2 or not np.any(cfs > 0) or not np.any(cfs < 0):
        return None

    periods = np.arange(cfs.size, dtype=float)

    def npv(rate: float) -> float:
        return float(np.sum(cfs / (1.0 + rate) ** periods))

    def dnpv(rate: float) -> float:
        return float(np.sum(-periods * cfs / (1.0 + rate) ** (periods + 1.0)))

    rate = guess
    for _ in range(100):
        f = npv(rate)
        df = dnpv(rate)
        if abs(df) < 1e-16:
            break
        nxt = rate - f / df
        if abs(nxt - rate) < 1e-14:
            rate = nxt
            break
        rate = nxt
    if abs(npv(rate)) > 1e-6 or not np.isfinite(rate):
        return None
    return float(rate)


@dataclass
class Assumptions:
    purchase_price: float = 480_000.0
    closing_costs: float = 12_000.0
    initial_renovation: float = 0.0
    ltv: float = 0.75
    mortgage_rate: float = 0.0725
    loan_term_years: int = 30
    gross_annual_rent: float = 45_000.0
    vacancy_rate: float = 0.05
    annual_hoa: float = 7_200.0
    annual_taxes: float = 4_000.0
    annual_insurance: float = 3_000.0
    growth_rate: float = 0.03
    exit_year: int = 5
    exit_price: float = 560_000.0
    cost_of_sale_rate: float = 0.03
    rate_buydown: float = 0
    seller_concessions: float = 0
    buydown_by_year: Dict[int, float] = field(
        default_factory=lambda: {1: 0.00, 2: 0.00, 3: 0.00, 4: 0.0, 5: 0.0}
    )

    def buydown_schedule_valid(self) -> bool:
        schedule_sum = sum(self.buydown_by_year.get(y, 0.0) for y in range(1, 6))
        both_zero = schedule_sum == 0 and self.rate_buydown == 0
        both_used = schedule_sum > 0 and self.rate_buydown > 0
        return both_zero or both_used


def _grow(base: float, growth: float, year: int) -> float:
    return base * (1.0 + growth) ** (year - 1)


def run_model(a: Assumptions) -> dict:
    exit_year = int(max(1, min(HORIZON, a.exit_year)))
    loan = a.purchase_price * a.ltv

    years = list(range(0, HORIZON + 1))
    rent = np.zeros(HORIZON + 1)
    vacancy = np.zeros(HORIZON + 1)
    egi = np.zeros(HORIZON + 1)
    hoa = np.zeros(HORIZON + 1)
    taxes = np.zeros(HORIZON + 1)
    insurance = np.zeros(HORIZON + 1)
    opex = np.zeros(HORIZON + 1)
    noi = np.zeros(HORIZON + 1)
    begin_bal = np.zeros(HORIZON + 1)
    debt_service = np.zeros(HORIZON + 1)
    interest = np.zeros(HORIZON + 1)
    principal = np.zeros(HORIZON + 1)
    end_bal = np.zeros(HORIZON + 1)
    gross_exit = np.zeros(HORIZON + 1)
    cost_of_sale = np.zeros(HORIZON + 1)
    net_exit = np.zeros(HORIZON + 1)
    loan_payoff = np.zeros(HORIZON + 1)
    terminal = np.zeros(HORIZON + 1)
    levered_cf = np.zeros(HORIZON + 1)

    annual_pmt = excel_pmt(a.mortgage_rate, a.loan_term_years, loan) if loan else 0.0
    end_bal[0] = loan

    for t in range(1, HORIZON + 1):
        if t > exit_year:
            continue

        rent[t] = _grow(a.gross_annual_rent, a.growth_rate, t)
        vacancy[t] = -rent[t] * a.vacancy_rate
        egi[t] = rent[t] + vacancy[t]
        hoa[t] = -_grow(a.annual_hoa, a.growth_rate, t)
        taxes[t] = -_grow(a.annual_taxes, a.growth_rate, t)
        insurance[t] = -_grow(a.annual_insurance, a.growth_rate, t)
        opex[t] = hoa[t] + taxes[t] + insurance[t]
        noi[t] = egi[t] + opex[t]

        begin_bal[t] = end_bal[t - 1]
        if begin_bal[t] > 0:
            debt_service[t] = annual_pmt
            buydown_pct = a.buydown_by_year.get(t, 0.0)
            interest[t] = -begin_bal[t] * (a.mortgage_rate - buydown_pct)
            principal[t] = debt_service[t] - interest[t]
        end_bal[t] = max(0.0, begin_bal[t] + principal[t])

        if t == exit_year:
            gross_exit[t] = a.exit_price
            cost_of_sale[t] = -gross_exit[t] * a.cost_of_sale_rate
            net_exit[t] = gross_exit[t] + cost_of_sale[t]
            loan_payoff[t] = -end_bal[t]
            terminal[t] = net_exit[t] + loan_payoff[t]

        levered_cf[t] = noi[t] + debt_service[t] + terminal[t]

    working_capital = -float(np.sum(np.minimum(levered_cf[1:], 0.0)))
    uses_purchase = a.purchase_price
    uses_closing = a.closing_costs
    uses_reno = a.initial_renovation
    uses_buydown = a.rate_buydown
    total_uses = uses_purchase + uses_closing + uses_reno + uses_buydown + working_capital

    sources_loan = loan
    sources_concessions = a.seller_concessions
    equity = total_uses - sources_loan - sources_concessions
    total_sources = sources_loan + sources_concessions + equity
    balance = total_sources - total_uses

    levered_cf[0] = -equity
    cumulative = np.cumsum(levered_cf)

    hold_cf = levered_cf[: exit_year + 1]
    irr = excel_irr(hold_cf)

    year1_coc = (levered_cf[1] / equity) if equity else None
    total_net_cf = float(np.sum(hold_cf))
    # Operating levered cash flow over the hold, separate from the sale.
    holding_period_cf = float(np.sum(noi[1 : exit_year + 1] + debt_service[1 : exit_year + 1]))
    reversion_year_cf = float(terminal[exit_year])
    moic = (float(np.sum(levered_cf[1 : exit_year + 1])) / equity) if equity else None
    if a.purchase_price:
        asset_growth = (a.exit_price / a.purchase_price) ** (1.0 / exit_year) - 1.0
        carrying_cost = (a.annual_hoa + a.annual_taxes + a.annual_insurance) / a.purchase_price
    else:
        asset_growth = None
        carrying_cost = None

    def pct(amount: float, total: float) -> float:
        return amount / total if total else 0.0

    sources = [
        {"item": "Senior Mortgage Loan", "amount": sources_loan, "pct": pct(sources_loan, total_sources)},
        {"item": "Seller Concessions", "amount": sources_concessions, "pct": pct(sources_concessions, total_sources)},
        {"item": "Investor Equity (Cash Required)", "amount": equity, "pct": pct(equity, total_sources)},
        {"item": "Total Sources", "amount": total_sources, "pct": 1.0},
    ]
    uses = [
        {"item": "Property Purchase Price", "amount": uses_purchase, "pct": pct(uses_purchase, total_uses)},
        {"item": "Closing Costs & Fees", "amount": uses_closing, "pct": pct(uses_closing, total_uses)},
        {"item": "Initial Renovation & Setup", "amount": uses_reno, "pct": pct(uses_reno, total_uses)},
        {"item": "Rate Buydown", "amount": uses_buydown, "pct": pct(uses_buydown, total_uses)},
        {"item": "Working Capital", "amount": working_capital, "pct": pct(working_capital, total_uses)},
        {"item": "Total Uses", "amount": total_uses, "pct": 1.0},
    ]

    records: List[dict] = []
    for t in years:
        if t > exit_year:
            continue
        records.append(
            {
                "Year": t,
                "Gross Scheduled Rental Income": rent[t],
                "Vacancy & Credit Loss": vacancy[t],
                "Effective Gross Income (EGI)": egi[t],
                "Condominium HOA Dues": hoa[t],
                "Property Taxes": taxes[t],
                "Property Insurance": insurance[t],
                "Total Operating Expenses": opex[t],
                "Net Operating Income (NOI)": noi[t],
                "Beginning Loan Balance": begin_bal[t] if t else 0.0,
                "Annual Debt Service": debt_service[t],
                "Interest Payment": interest[t],
                "Principal Paydown": principal[t],
                "Ending Loan Balance": end_bal[t],
                "Gross Exit Disposition Price": gross_exit[t],
                "Cost of Sale": cost_of_sale[t],
                "Net Exit Disposition Proceeds": net_exit[t],
                "Senior Mortgage Payoff at Exit": loan_payoff[t],
                "Net Terminal Capital Proceeds": terminal[t],
                "Net Levered Cash Flow": levered_cf[t],
                "Cumulative Net Cash Flow": cumulative[t],
            }
        )
    cash_flows = pd.DataFrame.from_records(records)

    metrics = {
        "holding_period": exit_year,
        "equity": equity,
        "irr": irr,
        "year1_coc": year1_coc,
        "total_net_cf": total_net_cf,
        "holding_period_cf": holding_period_cf,
        "reversion_year_cf": reversion_year_cf,
        "moic": moic,
        "exit_price": a.exit_price,
        "asset_growth": asset_growth,
        "carrying_cost": carrying_cost,
        "loan": loan,
        "working_capital": working_capital,
        "annual_pmt": annual_pmt,
        "buydown_schedule_valid": a.buydown_schedule_valid(),
        "balance": balance,
        "balanced": abs(balance) < 1e-6,
    }

    return {
        "assumptions": a,
        "sources": sources,
        "uses": uses,
        "metrics": metrics,
        "cash_flows": cash_flows,
        "levered_cf": levered_cf[: exit_year + 1],
    }
