"""
Budget analysis tools for the Budget Advisor Agent.
Handles income categorization, budget health scoring, and recommendations.
"""


def record_income_sources(
    wages_salary: float = 0.0,
    tips_bonuses: float = 0.0,
    commission: float = 0.0,
    freelancing: float = 0.0,
    rental_income: float = 0.0,
    royalties: float = 0.0,
    dividend_income: float = 0.0,
    interest_income: float = 0.0,
    capital_gains: float = 0.0,
    business_income: float = 0.0,
    government_assistance: float = 0.0,
    residual_income: float = 0.0,
    other_income: float = 0.0,
    tax_rate_percent: float = 0.0,
) -> dict:
    """
    Records and categorizes all income sources for the month. Computes gross income,
    net income after tax, disposable income, and breakdown by income type.

    Args:
        wages_salary (float): Regular salary or wages from employer.
        tips_bonuses (float): Tips, bonuses or performance rewards.
        commission (float): Commission earned from sales or tasks.
        freelancing (float): Income from freelance or contract work.
        rental_income (float): Revenue from renting out property.
        royalties (float): Income from licensing intellectual property.
        dividend_income (float): Payments from owning company shares.
        interest_income (float): Earnings from savings accounts or bonds.
        capital_gains (float): Profit from selling investment assets.
        business_income (float): Revenue from operating a business.
        government_assistance (float): Social security, unemployment, or disability.
        residual_income (float): Continued income after initial work e.g. subscriptions.
        other_income (float): Any other income not listed above.
        tax_rate_percent (float): Estimated tax rate percentage e.g. 15 for 15%.

    Returns:
        dict: status, gross_income, net_income, disposable_income, by_type breakdown.
    """
    earned    = {"Wages & Salary": wages_salary, "Tips & Bonuses": tips_bonuses,
                 "Commission": commission, "Freelancing": freelancing}
    passive   = {"Rental Income": rental_income, "Royalties": royalties,
                 "Dividend Income": dividend_income, "Interest Income": interest_income}
    portfolio = {"Capital Gains": capital_gains}
    business  = {"Business Income": business_income}
    other     = {"Government Assistance": government_assistance,
                 "Residual Income": residual_income, "Other Income": other_income}

    total_earned    = sum(earned.values())
    total_passive   = sum(passive.values())
    total_portfolio = sum(portfolio.values())
    total_business  = sum(business.values())
    total_other     = sum(other.values())

    gross_income = total_earned + total_passive + total_portfolio + total_business + total_other

    if gross_income <= 0:
        return {"status": "error", "error": "Total income must be greater than zero."}

    tax_amount       = gross_income * (tax_rate_percent / 100)
    net_income       = gross_income - tax_amount
    disposable       = net_income
    discretionary    = net_income * 0.50

    all_sources = {**earned, **passive, **portfolio, **business, **other}
    breakdown = {
        source: {
            "amount": amount,
            "pct_of_gross": round((amount / gross_income) * 100, 1),
        }
        for source, amount in all_sources.items()
        if amount > 0
    }

    type_totals = {
        "Earned (Active)": total_earned,
        "Passive":         total_passive,
        "Portfolio":       total_portfolio,
        "Business":        total_business,
        "Other":           total_other,
    }

    return {
        "status": "success",
        "gross_income":                  round(gross_income, 2),
        "tax_deducted":                  round(tax_amount, 2),
        "net_income":                    round(net_income, 2),
        "disposable_income":             round(disposable, 2),
        "discretionary_income_estimate": round(discretionary, 2),
        "by_type":                       type_totals,
        "breakdown":                     breakdown,
        "primary_income_type":           max(type_totals, key=lambda k: type_totals[k]),
        "message": (
            f"Gross: MYR {gross_income:,.2f} | "
            f"Tax ({tax_rate_percent}%): MYR {tax_amount:,.2f} | "
            f"Net: MYR {net_income:,.2f}"
        ),
    }


def analyze_budget_health(
    income: float,
    category_totals: dict[str, float],
    total_expenses: float,
) -> dict:
    """
    Analyzes monthly budget health by comparing spending against 50/30/20 benchmarks.

    Args:
        income (float): Total monthly net income in MYR.
        category_totals (dict[str, float]): Dictionary of category name to total amount.
        total_expenses (float): Sum of all expense amounts.

    Returns:
        dict: health_score 0-100, health_label, category_analysis, overspending_flags.
    """
    if income <= 0:
        return {"status": "error", "error": "Income must be greater than zero."}

    BENCHMARKS = {
        "Housing": 0.30, "Food": 0.15, "Transport": 0.10,
        "Entertainment": 0.05, "Healthcare": 0.05, "Education": 0.10,
        "Savings": 0.20, "Utilities": 0.08, "Others": 0.10,
    }

    category_analysis = {}
    overspending_flags = []
    score = 100

    for category, amount in category_totals.items():
        ratio = amount / income
        benchmark = BENCHMARKS.get(category, 0.10)
        pct_of_income = round(ratio * 100, 1)
        is_over = ratio > benchmark

        if is_over:
            penalty = min(20, int((ratio - benchmark) / benchmark * 30))
            score -= penalty
            overspending_flags.append({
                "category": category,
                "spent": amount,
                "ratio": pct_of_income,
                "recommended_max_ratio": round(benchmark * 100, 1),
            })

        category_analysis[category] = {
            "amount": amount,
            "pct_of_income": pct_of_income,
            "recommended_pct": round(benchmark * 100, 1),
            "status": "⚠️ Over" if is_over else "✅ OK",
        }

    if total_expenses > income:
        score -= 30

    score = max(0, min(100, score))

    if score >= 80:   health_label = "🟢 Excellent"
    elif score >= 60: health_label = "🟡 Fair"
    elif score >= 40: health_label = "🟠 Needs Attention"
    else:             health_label = "🔴 Critical"

    return {
        "status": "success",
        "health_score": score,
        "health_label": health_label,
        "savings_rate": round(((income - total_expenses) / income) * 100, 1),
        "category_analysis": category_analysis,
        "overspending_flags": overspending_flags,
    }


def generate_budget_recommendations(
    health_score: int,
    overspending_flags: list[dict],
    income: float,
    balance: float,
    category_totals: dict[str, float],
) -> dict:
    """
    Generates actionable budget recommendations based on spending analysis.

    Args:
        health_score (int): Budget health score from 0 to 100.
        overspending_flags (list[dict]): Categories where spending exceeded benchmarks.
        income (float): Monthly income in MYR.
        balance (float): Remaining balance after expenses.
        category_totals (dict[str, float]): Dictionary of category to amount.

    Returns:
        dict: recommendations grouped by priority — critical, moderate, positive.
    """
    critical = []
    moderate = []
    positive = []

    if balance < 0:
        critical.append({
            "action": "🚨 URGENT: Reduce spending immediately",
            "detail": f"You are MYR {abs(balance):.2f} over budget. Cut non-essentials now.",
        })

    for flag in overspending_flags:
        cat = flag["category"]
        over_by = flag["ratio"] - flag["recommended_max_ratio"]
        critical.append({
            "action": f"Reduce {cat} spending",
            "detail": (
                f"You spent {flag['ratio']}% of income on {cat}, "
                f"recommended max is {flag['recommended_max_ratio']}%. "
                f"Cut by MYR {(over_by / 100 * income):.2f} next month."
            ),
        })

    savings_rate = ((income - sum(category_totals.values())) / income) * 100 if income > 0 else 0
    if savings_rate < 10:
        moderate.append({
            "action": "Increase savings rate",
            "detail": f"Aim to save 20% of income (MYR {income * 0.20:.2f}). Automate savings on payday.",
        })

    if health_score >= 70:
        positive.append({
            "action": "✅ Great job staying on budget!",
            "detail": "Allocate your surplus to an emergency fund or investment (ASB, ETF).",
        })

    if balance > 0 and savings_rate >= 20:
        positive.append({
            "action": "💡 Invest your surplus",
            "detail": f"You have MYR {balance:.2f} left. Consider ASB, fixed deposit, or index funds.",
        })

    return {
        "status": "success",
        "recommendations": {
            "critical": critical,
            "moderate": moderate,
            "positive": positive,
        },
        "reusable_categories": [
            cat for cat in category_totals
            if cat not in [f["category"] for f in overspending_flags]
        ],
    }