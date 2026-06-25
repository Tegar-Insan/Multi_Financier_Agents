import os

import httpx
from dotenv import load_dotenv

from .fmp_cache import (
    _cache,
    TTL_QUOTE,
    TTL_MARKET,
    TTL_CRYPTO,
    TTL_NEWS,
    TTL_STATEMENTS,
    TTL_EARNINGS,
    TTL_METRICS,
)

load_dotenv()

_FD_BASE = "https://api.financialdatasets.ai"
_FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _get_fd(path: str, params: dict = None) -> dict | list | None:
    key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if not key:
        return None
    try:
        resp = httpx.get(
            f"{_FD_BASE}{path}",
            params=params or {},
            headers={"X-API-KEY": key},
            timeout=10,
        )
        if resp.status_code == 429:
            return "RATE_LIMIT"
        if resp.status_code in (401, 403):
            return "INVALID_KEY"
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        return "TIMEOUT"
    except Exception:
        return None


def _get_fmp(path: str, params: dict = None) -> dict | list | None:
    key = os.getenv("FMP_API_KEY")
    if not key:
        return None
    all_params = {"apikey": key, **(params or {})}
    try:
        resp = httpx.get(f"{_FMP_BASE}{path}", params=all_params, timeout=10)
        if resp.status_code == 429:
            return "RATE_LIMIT"
        if resp.status_code in (401, 403):
            return "INVALID_KEY"
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        return "TIMEOUT"
    except Exception:
        return None


def _err_msg(data, source: str = "") -> str | None:
    if data == "RATE_LIMIT":
        return f"{source}Rate limit reached. Try again in a few minutes."
    if data == "INVALID_KEY":
        return f"{source}Invalid API key. Check your credentials in .env."
    if data == "TIMEOUT":
        return f"{source}Request timed out. Try again shortly."
    return None


def _fmt_money(val) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        if abs(val) >= 1e12:
            return f"${val/1e12:.2f}T"
        if abs(val) >= 1e9:
            return f"${val/1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val/1e6:.2f}M"
        return f"${val:,.0f}"
    return str(val)


# ── Tool 1: Real-time stock price ─────────────────────────────────────────────
def get_stock_quote(symbol: str) -> str:
    """Real-time stock price snapshot for a ticker symbol (e.g. AAPL, MSFT)."""
    if not os.getenv("FINANCIAL_DATASETS_API_KEY") and not os.getenv("FMP_API_KEY"):
        return "No API key set. Add FINANCIAL_DATASETS_API_KEY or FMP_API_KEY to .env."

    symbol = symbol.upper().strip()
    cache_key = f"quote:{symbol}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd("/prices/snapshot", {"ticker": symbol})

    if isinstance(data, dict) and "snapshot" in data:
        snap = data["snapshot"]
        price = snap.get("price")
        day_change = snap.get("day_change", 0)
        day_change_pct = snap.get("day_change_percent", 0)
        ts = snap.get("time", "")
        direction = "▲" if isinstance(day_change, (int, float)) and day_change >= 0 else "▼"
        lines = [
            f"📈 {symbol} — Real-Time Price",
            f"Price:   ${price:,.2f}" if isinstance(price, (int, float)) else f"Price:   {price}",
            (
                f"Change:  {direction} ${abs(day_change):,.2f} ({day_change_pct:+.2f}%)"
                if isinstance(day_change, (int, float))
                else ""
            ),
            f"As of:   {ts}" if ts else "",
        ]
        result = "\n".join(line for line in lines if line)
        _cache.set(cache_key, result, TTL_QUOTE)
        return result

    err = _err_msg(data)
    if err:
        return err

    # FMP fallback
    fmp_data = _get_fmp(f"/quote/{symbol}")
    fmp_err = _err_msg(fmp_data, "FMP ")
    if fmp_err:
        return fmp_err
    if not fmp_data or not isinstance(fmp_data, list) or len(fmp_data) == 0:
        return f"No quote data found for '{symbol}'."

    q = fmp_data[0]
    price = q.get("price", "N/A")
    change = q.get("change", 0)
    change_pct = q.get("changesPercentage", 0)
    name = q.get("name", symbol)
    direction = "▲" if isinstance(change, (int, float)) and change >= 0 else "▼"
    lines = [
        f"📈 {name} ({symbol})",
        f"Price:   ${price:,.2f}" if isinstance(price, (int, float)) else f"Price:   {price}",
        (
            f"Change:  {direction} ${abs(change):,.2f} ({change_pct:+.2f}%)"
            if isinstance(change, (int, float)) and isinstance(change_pct, (int, float))
            else ""
        ),
    ]
    result = "\n".join(line for line in lines if line)
    _cache.set(cache_key, result, TTL_QUOTE)
    return result


# ── Tool 2: Financial news ────────────────────────────────────────────────────
def get_financial_news(keywords: str = "", limit: int = 8) -> str:
    """
    Latest financial news from Financial Datasets API.
    Pass a ticker symbol as keywords for company-specific news.
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY") and not os.getenv("FMP_API_KEY"):
        return "No API key set. Add FINANCIAL_DATASETS_API_KEY or FMP_API_KEY to .env."

    limit = min(max(1, int(limit)), 10)
    ticker = keywords.strip().upper() if keywords.strip() else None
    cache_key = f"news:{ticker or 'market'}:{limit}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    params = {"limit": limit}
    if ticker:
        params["ticker"] = ticker
    data = _get_fd("/news", params)

    if isinstance(data, dict) and "news" in data:
        articles = data["news"]
        if not articles:
            return "No news articles found."
        label = f"📰 News for {ticker}" if ticker else "📰 Latest Market News"
        lines = [label + "\n"]
        for i, a in enumerate(articles, 1):
            title = a.get("title", "No title")
            date = str(a.get("date", ""))[:10]
            source = a.get("source", "")
            url = a.get("url", "")
            lines.append(f"{i}. [{date}] {title}")
            if source:
                lines.append(f"   Source: {source}")
            if url:
                lines.append(f"   {url}")
            lines.append("")
        result = "\n".join(lines)
        _cache.set(cache_key, result, TTL_NEWS)
        return result

    err = _err_msg(data)
    if err:
        return err

    # FMP fallback (general news only)
    fmp_data = _get_fmp("/fmp/articles", {"page": 0, "size": limit})
    fmp_err = _err_msg(fmp_data, "FMP ")
    if fmp_err:
        return fmp_err
    if not fmp_data or not isinstance(fmp_data, dict):
        return "No financial news available at this time."

    articles = fmp_data.get("content", [])
    if not articles:
        return "No news articles found."
    lines = ["📰 Latest Financial News (FMP)\n"]
    for i, a in enumerate(articles[:limit], 1):
        title = a.get("title", "No title")
        date = a.get("date", "")[:10]
        site = a.get("site", "")
        text = a.get("text", "")[:150].rstrip()
        lines.append(f"{i}. [{date}] {title}")
        if site:
            lines.append(f"   Source: {site}")
        if text:
            lines.append(f"   {text}...")
        lines.append("")
    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_NEWS)
    return result


# ── Tool 3: Financial statements ──────────────────────────────────────────────
def get_financial_statements(symbol: str, statement_type: str = "income") -> str:
    """
    Financial statements for a company from Financial Datasets API.
    statement_type: 'income' | 'balance' | 'cashflow'
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY") and not os.getenv("FMP_API_KEY"):
        return "No API key set. Add FINANCIAL_DATASETS_API_KEY or FMP_API_KEY to .env."

    symbol = symbol.upper().strip()
    type_map = {
        "income": ("income-statements", "income_statements", "income-statement"),
        "balance": ("balance-sheets", "balance_sheets", "balance-sheet-statement"),
        "cashflow": ("cash-flow-statements", "cash_flow_statements", "cash-flow-statement"),
        "cash": ("cash-flow-statements", "cash_flow_statements", "cash-flow-statement"),
    }
    fd_endpoint, fd_key, fmp_endpoint = type_map.get(statement_type.lower(), type_map["income"])

    cache_key = f"stmt:{symbol}:{fd_endpoint}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd(f"/financials/{fd_endpoint}", {"ticker": symbol, "period": "annual", "limit": 1})

    s = None
    if isinstance(data, dict):
        records = data.get(fd_key) or []
        if records and isinstance(records, list):
            s = records[0]

    if not s:
        err = _err_msg(data)
        if err:
            return err
        fmp_data = _get_fmp(f"/{fmp_endpoint}/{symbol}", {"limit": 1})
        fmp_err = _err_msg(fmp_data, "FMP ")
        if fmp_err:
            return fmp_err
        if fmp_data and isinstance(fmp_data, list) and len(fmp_data) > 0:
            s = fmp_data[0]

    if not s:
        return f"No {statement_type} statement found for '{symbol}'."

    date = s.get("report_period") or s.get("date", "N/A")
    period = s.get("fiscal_period") or s.get("period", "")
    currency = s.get("currency") or s.get("reportedCurrency", "USD")

    if "income" in fd_endpoint:
        lines = [
            f"📊 Income Statement — {symbol} ({period} {date}) [{currency}]",
            f"Revenue:          {_fmt_money(s.get('revenue') or s.get('totalRevenue'))}",
            f"Gross Profit:     {_fmt_money(s.get('gross_profit') or s.get('grossProfit'))}",
            f"Operating Income: {_fmt_money(s.get('operating_income') or s.get('operatingIncome'))}",
            f"Net Income:       {_fmt_money(s.get('net_income') or s.get('netIncome'))}",
            f"EPS:              {s.get('earnings_per_share') or s.get('eps', 'N/A')}",
            f"EPS Diluted:      {s.get('earnings_per_share_diluted', 'N/A')}",
            f"EBITDA:           {_fmt_money(s.get('ebitda'))}",
        ]
    elif "balance" in fd_endpoint:
        lines = [
            f"🏦 Balance Sheet — {symbol} ({period} {date}) [{currency}]",
            f"Total Assets:       {_fmt_money(s.get('total_assets') or s.get('totalAssets'))}",
            f"Current Assets:     {_fmt_money(s.get('current_assets') or s.get('totalCurrentAssets'))}",
            f"Cash & Equivalents: {_fmt_money(s.get('cash_and_equivalents') or s.get('cashAndCashEquivalents'))}",
            f"Total Liabilities:  {_fmt_money(s.get('total_liabilities') or s.get('totalLiabilities'))}",
            f"Current Liabilities:{_fmt_money(s.get('current_liabilities') or s.get('totalCurrentLiabilities'))}",
            f"Shareholders Equity:{_fmt_money(s.get('shareholders_equity') or s.get('totalStockholdersEquity'))}",
            f"Total Debt:         {_fmt_money(s.get('total_debt') or s.get('totalDebt'))}",
        ]
    else:
        lines = [
            f"💧 Cash Flow Statement — {symbol} ({period} {date}) [{currency}]",
            f"Operating CF:   {_fmt_money(s.get('operating_cash_flow') or s.get('operatingCashFlow'))}",
            f"Investing CF:   {_fmt_money(s.get('investing_activities') or s.get('netCashUsedForInvestingActivites'))}",
            f"Financing CF:   {_fmt_money(s.get('financing_activities') or s.get('netCashUsedProvidedByFinancingActivities'))}",
            f"Free Cash Flow: {_fmt_money(s.get('free_cash_flow') or s.get('freeCashFlow'))}",
            f"Net Change:     {_fmt_money(s.get('net_change_in_cash') or s.get('netChangeInCash'))}",
        ]

    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_STATEMENTS)
    return result

def get_income_statements(symbol: str, limit: int = 1) -> str:
    """
    Fetches the income statements for a given company symbol.
    limit: number of recent statements to retrieve (
    default 1)
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY") and not os.getenv("FMP_API_KEY"):
        return "No API key set. Add FINANCIAL_DATASETS_API_KEY or FMP_API_KEY to .env."

    symbol = symbol.upper().strip()
    limit = min(max(1, int(limit)), 10)
    cache_key = f"income_statements:{symbol}:{limit}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd("/financials/income-statements", {"ticker": symbol, "period": "annual", "limit": limit})

    records = None
    if isinstance(data, dict) and "income_statements" in data:
        records = data["income_statements"]
    else:
        err = _err_msg(data)
        if err:
            return err

    if not records:
        fmp_data = _get_fmp(f"/income-statement/{symbol}", {"period": "annual", "limit": limit})
        fmp_err = _err_msg(fmp_data, "FMP ")
        if fmp_err:
            return fmp_err
        records = fmp_data if isinstance(fmp_data, list) else None

    if not records:
        return f"No income statements found for '{symbol}'."

    lines = [f"📊 Income Statements — {symbol}\n"]
    for s in records:
        date = s.get("report_period") or s.get("date", "N/A")
        period = s.get("fiscal_period") or s.get("period", "")
        currency = s.get("currency") or s.get("reportedCurrency", "USD")
        lines.append(f"Period: {period} {date} [{currency}]")
        lines.append(f"Revenue:          {_fmt_money(s.get('revenue') or s.get('totalRevenue'))}")
        lines.append(f"Gross Profit:     {_fmt_money(s.get('gross_profit') or s.get('grossProfit'))}")
        lines.append(f"Operating Income: {_fmt_money(s.get('operating_income') or s.get('operatingIncome'))}")
        lines.append(f"Net Income:       {_fmt_money(s.get('net_income') or s.get('netIncome'))}")
        lines.append(f"EPS:              {s.get('earnings_per_share') or s.get('eps', 'N/A')}")
        lines.append(f"EPS Diluted:      {s.get('earnings_per_share_diluted', 'N/A')}")
        lines.append(f"EBITDA:           {_fmt_money(s.get('ebitda'))}")
        lines.append("")
    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_STATEMENTS)
    return result


# ── Tool: Balance sheets ──────────────────────────────────────────────────────
def get_balance_sheets(symbol: str, limit: int = 1) -> str:
    """
    Fetches the balance sheets for a given company symbol.
    limit: number of recent statements to retrieve (default 1)
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY") and not os.getenv("FMP_API_KEY"):
        return "No API key set. Add FINANCIAL_DATASETS_API_KEY or FMP_API_KEY to .env."

    symbol = symbol.upper().strip()
    limit = min(max(1, int(limit)), 10)
    cache_key = f"balance_sheets:{symbol}:{limit}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd("/financials/balance-sheets", {"ticker": symbol, "period": "annual", "limit": limit})

    records = None
    if isinstance(data, dict) and "balance_sheets" in data:
        records = data["balance_sheets"]
    else:
        err = _err_msg(data)
        if err:
            return err

    if not records:
        fmp_data = _get_fmp(f"/balance-sheet-statement/{symbol}", {"period": "annual", "limit": limit})
        fmp_err = _err_msg(fmp_data, "FMP ")
        if fmp_err:
            return fmp_err
        records = fmp_data if isinstance(fmp_data, list) else None

    if not records:
        return f"No balance sheets found for '{symbol}'."

    lines = [f"🏦 Balance Sheets — {symbol}\n"]
    for s in records:
        date = s.get("report_period") or s.get("date", "N/A")
        period = s.get("fiscal_period") or s.get("period", "")
        currency = s.get("currency") or s.get("reportedCurrency", "USD")
        lines.append(f"Period: {period} {date} [{currency}]")
        lines.append(f"Total Assets:        {_fmt_money(s.get('total_assets') or s.get('totalAssets'))}")
        lines.append(f"Current Assets:      {_fmt_money(s.get('current_assets') or s.get('totalCurrentAssets'))}")
        lines.append(f"Cash & Equivalents:  {_fmt_money(s.get('cash_and_equivalents') or s.get('cashAndCashEquivalents'))}")
        lines.append(f"Total Liabilities:   {_fmt_money(s.get('total_liabilities') or s.get('totalLiabilities'))}")
        lines.append(f"Current Liabilities: {_fmt_money(s.get('current_liabilities') or s.get('totalCurrentLiabilities'))}")
        lines.append(f"Total Debt:          {_fmt_money(s.get('total_debt') or s.get('totalDebt'))}")
        lines.append(f"Shareholders Equity: {_fmt_money(s.get('shareholders_equity') or s.get('totalStockholdersEquity'))}")
        lines.append(f"Retained Earnings:   {_fmt_money(s.get('retained_earnings') or s.get('retainedEarnings'))}")
        lines.append("")
    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_STATEMENTS)
    return result


# ── Tool: Cash flow statements ────────────────────────────────────────────────
def get_cashflow_statements(symbol: str, limit: int = 1) -> str:
    """
    Fetches the cash flow statements for a given company symbol.
    limit: number of recent statements to retrieve (default 1)
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY") and not os.getenv("FMP_API_KEY"):
        return "No API key set. Add FINANCIAL_DATASETS_API_KEY or FMP_API_KEY to .env."

    symbol = symbol.upper().strip()
    limit = min(max(1, int(limit)), 10)
    cache_key = f"cashflow_statements:{symbol}:{limit}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd("/financials/cash-flow-statements", {"ticker": symbol, "period": "annual", "limit": limit})

    records = None
    if isinstance(data, dict) and "cash_flow_statements" in data:
        records = data["cash_flow_statements"]
    else:
        err = _err_msg(data)
        if err:
            return err

    if not records:
        fmp_data = _get_fmp(f"/cash-flow-statement/{symbol}", {"period": "annual", "limit": limit})
        fmp_err = _err_msg(fmp_data, "FMP ")
        if fmp_err:
            return fmp_err
        records = fmp_data if isinstance(fmp_data, list) else None

    if not records:
        return f"No cash flow statements found for '{symbol}'."

    lines = [f"💧 Cash Flow Statements — {symbol}\n"]
    for s in records:
        date = s.get("report_period") or s.get("date", "N/A")
        period = s.get("fiscal_period") or s.get("period", "")
        currency = s.get("currency") or s.get("reportedCurrency", "USD")
        lines.append(f"Period: {period} {date} [{currency}]")
        lines.append(f"Operating CF:   {_fmt_money(s.get('net_cash_flow_from_operations') or s.get('operatingCashFlow'))}")
        lines.append(f"Investing CF:   {_fmt_money(s.get('net_cash_flow_from_investing') or s.get('netCashUsedForInvestingActivites'))}")
        lines.append(f"Financing CF:   {_fmt_money(s.get('net_cash_flow_from_financing') or s.get('netCashUsedProvidedByFinancingActivities'))}")
        lines.append(f"Capital Expenditure: {_fmt_money(s.get('capital_expenditure') or s.get('capitalExpenditure'))}")
        lines.append(f"Free Cash Flow: {_fmt_money(s.get('free_cash_flow') or s.get('freeCashFlow'))}")
        lines.append(f"Net Change:     {_fmt_money(s.get('change_in_cash_and_equivalents') or s.get('netChangeInCash'))}")
        lines.append("")
    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_STATEMENTS)
    return result


# ── Tool 4: Earnings ──────────────────────────────────────────────────────────
def get_earnings(symbol: str, limit: int = 4) -> str:
    """
    Recent earnings reports: EPS actuals vs estimates, revenue, and market signals.
    Uses Financial Datasets /earnings endpoint.
    limit: 1-40 periods (default 4)
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY"):
        return "FINANCIAL_DATASETS_API_KEY not set. Add it to your .env file."

    symbol = symbol.upper().strip()
    limit = min(max(1, int(limit)), 40)
    cache_key = f"earnings:{symbol}:{limit}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd("/earnings", {"ticker": symbol, "limit": limit})
    err = _err_msg(data)
    if err:
        return err

    if not isinstance(data, dict) or "earnings" not in data:
        return f"No earnings data found for '{symbol}'."

    records = data["earnings"]
    if not records:
        return f"No earnings records available for '{symbol}'."

    lines = [f"📋 Earnings — {symbol}\n"]
    for e in records:
        report_period = e.get("report_period", "N/A")
        fiscal_period = e.get("fiscal_period", "")
        source_type = e.get("source_type", "")
        filing_window = e.get("filing_window", "")

        q = e.get("quarterly") or {}
        a = e.get("annual") or {}

        eps_act = q.get("earnings_per_share") if q else a.get("earnings_per_share")
        eps_est = q.get("earnings_per_share_estimated") if q else a.get("earnings_per_share_estimated")
        rev_act = q.get("revenue") if q else a.get("revenue")
        rev_est = q.get("revenue_estimated") if q else a.get("revenue_estimated")

        eps_str = f"{eps_act:.2f}" if isinstance(eps_act, (int, float)) else "N/A"
        eps_est_str = f"{eps_est:.2f}" if isinstance(eps_est, (int, float)) else "N/A"

        filing_info = " | ".join(x for x in [source_type, filing_window] if x)
        lines.append(f"▸ {report_period} ({fiscal_period})" + (f" [{filing_info}]" if filing_info else ""))
        lines.append(f"  EPS:     Actual {eps_str} | Estimate {eps_est_str}")
        lines.append(f"  Revenue: Actual {_fmt_money(rev_act)} | Estimate {_fmt_money(rev_est)}")

        signals = e.get("market_signals") or []
        if signals:
            signal_types = ", ".join(s.get("type", "") for s in signals[:4] if s.get("type"))
            if signal_types:
                lines.append(f"  Signals: {signal_types}")
        lines.append("")

    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_EARNINGS)
    return result


# ── Tool 5: Company financial metrics ─────────────────────────────────────────
def get_company_metrics(symbol: str) -> str:
    """
    Financial health metrics snapshot: valuation, profitability, growth, liquidity.
    Uses Financial Datasets /financial-metrics/snapshot endpoint.
    """
    if not os.getenv("FINANCIAL_DATASETS_API_KEY"):
        return "FINANCIAL_DATASETS_API_KEY not set. Add it to your .env file."

    symbol = symbol.upper().strip()
    cache_key = f"metrics:{symbol}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fd("/financial-metrics/snapshot", {"ticker": symbol})
    err = _err_msg(data)
    if err:
        return err

    if not isinstance(data, dict) or "snapshot" not in data:
        return f"No financial metrics found for '{symbol}'."

    s = data["snapshot"]

    def pct(val) -> str:
        if val is None:
            return "N/A"
        if isinstance(val, (int, float)):
            return f"{val * 100:.2f}%"
        return str(val)

    def ratio(val) -> str:
        if val is None:
            return "N/A"
        return f"{val:.2f}x" if isinstance(val, (int, float)) else str(val)

    lines = [
        f"📊 Financial Metrics — {symbol}",
        "",
        "Valuation",
        f"  Market Cap:  {_fmt_money(s.get('market_cap'))}",
        f"  P/E Ratio:   {ratio(s.get('price_to_earnings_ratio'))}",
        f"  P/B Ratio:   {ratio(s.get('price_to_book_ratio'))}",
        f"  P/S Ratio:   {ratio(s.get('price_to_sales_ratio'))}",
        f"  EV/EBITDA:   {ratio(s.get('enterprise_value_to_ebitda_ratio'))}",
        f"  PEG Ratio:   {ratio(s.get('peg_ratio'))}",
        "",
        "Profitability",
        f"  Gross Margin:  {pct(s.get('gross_margin'))}",
        f"  Net Margin:    {pct(s.get('net_margin'))}",
        f"  ROE:           {pct(s.get('return_on_equity'))}",
        f"  ROA:           {pct(s.get('return_on_assets'))}",
        f"  ROIC:          {pct(s.get('return_on_invested_capital'))}",
        "",
        "Growth (YoY)",
        f"  Revenue Growth: {pct(s.get('revenue_growth'))}",
        f"  EPS Growth:     {pct(s.get('earnings_per_share_growth'))}",
        f"  FCF Growth:     {pct(s.get('free_cash_flow_growth'))}",
        "",
        "Liquidity & Leverage",
        f"  Current Ratio:  {ratio(s.get('current_ratio'))}",
        f"  Debt/Equity:    {ratio(s.get('debt_to_equity'))}",
        f"  Interest Cover: {ratio(s.get('interest_coverage'))}",
        "",
        "Per Share",
        f"  EPS:     {s.get('earnings_per_share', 'N/A')}",
        f"  Book Value: {s.get('book_value_per_share', 'N/A')}",
    ]

    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_METRICS)
    return result


def get_market_data(filter_type: str = "actives") -> str:
    """Top gainers, losers, or most active stocks via FMP."""
    if not os.getenv("FMP_API_KEY"):
        return "FMP_API_KEY not set. Market movers data requires FMP_API_KEY in .env."

    filter_type = filter_type.lower().strip()
    if filter_type not in ("gainers", "losers", "actives"):
        filter_type = "actives"

    cache_key = f"market:{filter_type}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    data = _get_fmp(f"/stock_market/{filter_type}")
    err = _err_msg(data, "FMP ")
    if err:
        return err
    if not data or not isinstance(data, list):
        return f"No {filter_type} data available right now."

    label_map = {"gainers": "📈 Top Gainers", "losers": "📉 Top Losers", "actives": "🔥 Most Active"}
    lines = [f"{label_map[filter_type]} Today\n"]
    for i, stock in enumerate(data[:10], 1):
        sym = stock.get("symbol", "")
        name = stock.get("name", sym)
        price = stock.get("price", "N/A")
        change = stock.get("change", 0)
        pct = stock.get("changesPercentage", 0)
        direction = "▲" if isinstance(change, (int, float)) and change >= 0 else "▼"
        lines.append(
            f"{i:2}. {sym:<6} {name[:28]:<28}  ${price:>8.2f}  {direction}{abs(pct):.2f}%"
            if isinstance(price, (int, float)) and isinstance(pct, (int, float))
            else f"{i:2}. {sym} — {name}"
        )

    result = "\n".join(lines)
    _cache.set(cache_key, result, TTL_MARKET)
    return result


