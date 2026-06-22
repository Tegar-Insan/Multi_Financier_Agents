import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP

from financial_advisor.tools.fmp_tools import (
    get_stock_quote,
    get_financial_news,
    get_financial_statements,
    get_income_statements,
    get_balance_sheets,
    get_cashflow_statements,
    get_earnings,
    get_company_metrics,
    get_market_data,
    get_crypto_data,
)

mcp = FastMCP("FinancialDataServer")


@mcp.tool()
def stock_quote(symbol: str) -> str:
    """Real-time stock price snapshot. Example: stock_quote('AAPL')"""
    return get_stock_quote(symbol)


@mcp.tool()
def financial_news(keywords: str = "", limit: int = 8) -> str:
    """
    Latest financial news. Pass a ticker as keywords for company news.
    Example: financial_news('AAPL') or financial_news() for market-wide news.
    """
    return get_financial_news(keywords, limit)


@mcp.tool()
def financial_statements(symbol: str, statement_type: str = "income") -> str:
    """
    Financial statements from SEC filings via Financial Datasets API.
    statement_type options: 'income' | 'balance' | 'cashflow'
    Example: financial_statements('TSLA', 'income')
    """
    return get_financial_statements(symbol, statement_type)


@mcp.tool()
def earnings(symbol: str, limit: int = 4) -> str:
    """
    Earnings reports: EPS actuals vs estimates, revenue, and market signals.
    Covers the last N periods (limit 1-40).
    Example: earnings('AAPL', 4)
    """
    return get_earnings(symbol, limit)


@mcp.tool()
def company_metrics(symbol: str) -> str:
    """
    Financial health snapshot: valuation ratios, profitability, growth, liquidity.
    Example: company_metrics('MSFT')
    """
    return get_company_metrics(symbol)


@mcp.tool()
def market_data(filter_type: str = "actives") -> str:
    """
    Stock market movers via FMP. filter_type: 'gainers' | 'losers' | 'actives'
    Example: market_data('gainers')
    """
    return get_market_data(filter_type)


@mcp.tool()
def crypto_data(symbol: str = "BTCUSD") -> str:
    """
    Cryptocurrency price via FMP. Examples: 'BTCUSD', 'ETHUSD', 'XRPUSD'
    Example: crypto_data('BTCUSD')
    """
    return get_crypto_data(symbol)

@mcp.tool()
def income_statements(symbol: str, period: str = "annual", limit: int = 4) -> str:
    """
    Detailed income statements (revenue, margins, EPS, shares outstanding, etc.)
    from SEC filings via Financial Datasets API.
    period: 'annual' | 'quarterly' | 'ttm'. limit: number of periods (1-10).
    Example: income_statements('AAPL', 'quarterly', 4)
    """
    return get_income_statements(symbol, period, limit)


@mcp.tool()
def balance_sheets(symbol: str, period: str = "annual", limit: int = 4) -> str:
    """
    Detailed balance sheets (assets, liabilities, equity, debt) from SEC filings
    via Financial Datasets API.
    period: 'annual' | 'quarterly' | 'ttm'. limit: number of periods (1-10).
    Example: balance_sheets('AAPL', 'annual', 4)
    """
    return get_balance_sheets(symbol, period, limit)


@mcp.tool()
def cashflow_statements(symbol: str, period: str = "annual", limit: int = 4) -> str:
    """
    Detailed cash flow statements (operating/investing/financing cash flow,
    capex, free cash flow) from SEC filings via Financial Datasets API.
    period: 'annual' | 'quarterly' | 'ttm'. limit: number of periods (1-10).
    Example: cashflow_statements('AAPL', 'quarterly', 4)
    """
    return get_cashflow_statements(symbol, period, limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
