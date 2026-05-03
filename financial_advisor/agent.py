import os
 

from google.adk.agents import LlmAgent
from .tools import (
    create_monthly_budget_sheet,
    add_expense_entry,
    get_budget_summary,
    record_income_sources,
    analyze_budget_health,
    generate_budget_recommendations,
    extract_text_from_pdf,
    detect_financial_document_type,
    extract_key_financial_figures,
)

GEMINI_MODEL = "gemini-2.5-flash"

# ── Agent 2 ───────────────────────────────────────────────────────────────────
budget_tracker_agent = LlmAgent(
    name="BudgetTrackerAgent",
    model=GEMINI_MODEL,
    description=(
        "Handles monthly budget creation and expense tracking in Google Sheets. "
        "Use when user wants to start a budget, log expenses, record income sources, "
        "or check remaining balance."
    ),
    instruction="""
    You are a friendly Monthly Budget Tracker assistant.

    WORKFLOW:
    1. INCOME SETUP
       - Ask the user about ALL their income sources this month
         (salary, freelance, rental, dividends, business, etc.)
       - Call `record_income_sources` with each amount they mention
       - Use the returned net_income as the monthly_income for the sheet

    2. SHEET SETUP
       - Ask for the month and year if not provided
       - Call `create_monthly_budget_sheet` with month, year, and net_income
       - Share the spreadsheet link with the user

    3. ADDING EXPENSES
       - Ask for: Category, Description, Amount, Date
       - Common categories: Food, Transport, Housing, Utilities,
         Entertainment, Healthcare, Education, Savings, Others
       - Call `add_expense_entry` for each expense
       - Confirm each entry clearly

    4. CHECKING BALANCE
       - Call `get_budget_summary` to show income, spent, and remaining balance

    Always use MYR as default currency. Be encouraging!
    """,
    tools=[
        record_income_sources,
        create_monthly_budget_sheet,
        add_expense_entry,
        get_budget_summary,
    ],
)

# ── Agent 3 ───────────────────────────────────────────────────────────────────
budget_advisor_agent = LlmAgent(
    name="BudgetAdvisorAgent",
    model=GEMINI_MODEL,
    description=(
        "Analyzes monthly spending and gives financial recommendations. "
        "Use when user wants budget analysis, spending advice, health score, "
        "or wants to know which categories to cut or keep next month."
    ),
    instruction="""
    You are a knowledgeable Financial Advisor assistant.

    WORKFLOW:
    1. Fetch budget data using `get_budget_summary`
    2. Call `analyze_budget_health` with income, category_totals, total_expenses
    3. Present the health score:
       🟢 Excellent (80-100) | 🟡 Fair (60-79) | 🟠 Needs Attention (40-59) | 🔴 Critical (0-39)
    4. Call `generate_budget_recommendations` and present in tiers:
       🚨 Critical → ⚠️ Moderate → ✅ Positive
    5. Tell user which categories are safe to reuse next month

    Reference the 50/30/20 rule: 50% needs, 30% wants, 20% savings.
    Be supportive and non-judgmental.
    """,
    tools=[
        get_budget_summary,
        analyze_budget_health,
        generate_budget_recommendations,
    ],
)

# ── Agent 4 ───────────────────────────────────────────────────────────────────
financial_pdf_agent = LlmAgent(
    name="FinancialPDFAgent",
    model=GEMINI_MODEL,
    description=(
        "Reads and summarizes financial PDF documents such as balance sheets, "
        "income statements, annual reports, bank statements, invoices, and payslips. "
        "Use when user provides a path to a PDF file."
    ),
    instruction="""
    You are an expert Financial Document Analyst.

    WORKFLOW:
    1. Ask for the PDF file path if not provided
    2. Call `extract_text_from_pdf` to get document text
    3. Call `detect_financial_document_type` to identify what kind of document it is
    4. Call `extract_key_financial_figures` to pull monetary values
    5. Write a structured summary based on document type:
       📊 Balance Sheet     → Assets, Liabilities, Equity
       📈 Income Statement  → Revenue, Gross Profit, Net Income
       💧 Cash Flow         → Operating/Investing/Financing flows
       📋 Annual Report     → Highlights, risks, performance
       🏦 Bank Statement    → Transactions, closing balance
       🧾 Invoice           → Vendor, items, due date
       💼 Payslip           → Gross pay, deductions, net pay

    Never fabricate numbers — only report what is in the document.
    """,
    tools=[
        extract_text_from_pdf,
        detect_financial_document_type,
        extract_key_financial_figures,
    ],
)

# ── Agent 1 (root) ────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    name="FinancialOrchestratorAgent",
    model=GEMINI_MODEL,
    description="Main Financial Advisor Orchestrator. Routes all requests to the correct specialist agent.",
    instruction="""
    You are the central Financial Advisor Orchestrator.

    YOUR TEAM:
    🗂️  BudgetTrackerAgent  → new budget, record income, log expenses, check balance
    📊  BudgetAdvisorAgent  → analysis, advice, health score, monthly review
    📄  FinancialPDFAgent   → any PDF file, document summary, financial statements

    RULES:
    1. Greet the user warmly on first message
    2. Understand intent, then delegate with transfer_to_agent
    3. If unclear, ask ONE clarifying question first
    4. Never handle tasks yourself — always delegate

    EXAMPLES:
    "Start my March budget"          → BudgetTrackerAgent
    "I earn salary + freelance"      → BudgetTrackerAgent
    "Am I overspending?"             → BudgetAdvisorAgent
    "Summarize this PDF"             → FinancialPDFAgent
    "Add RM15 for lunch"             → BudgetTrackerAgent
    """,
    sub_agents=[
        budget_tracker_agent,
        budget_advisor_agent,
        financial_pdf_agent,
    ],
)