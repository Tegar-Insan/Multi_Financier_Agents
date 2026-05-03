import os
from datetime import datetime
from typing import Optional
import gspread 
from google.auth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_creds():
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    return Credentials.from_service_account_file(creds_path, scopes=SCOPES)


def _get_client() -> gspread.Client:
    return gspread.authorize(_get_creds())


def create_monthly_budget_sheet(month: str, year: int, monthly_income: float) -> dict:
    """
    Creates a new tab inside the master Google Spreadsheet for the specified month.
    Sets up headers and records the user's total monthly income.

    Args:
        month (str): Full month name e.g. 'January', 'March'.
        year (int): The 4-digit year e.g. 2026.
        monthly_income (float): Total money available this month in MYR.

    Returns:
        dict: status, spreadsheet_url, spreadsheet_id, tab_name or error.
    """
    try:
        gc = _get_client()
        master_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        if not master_id:
            return {"status": "error", "error": "GOOGLE_MASTER_SHEET_ID not set in .env"}

        spreadsheet = gc.open_by_key(master_id)
        tab_name = f"{month} {year}"

        existing_tabs = [ws.title for ws in spreadsheet.worksheets()]
        if tab_name in existing_tabs:
            ws = spreadsheet.worksheet(tab_name)
        else:
            ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=10)

        headers = [
            ["💰 MONTHLY BUDGET TRACKER", "", "", ""],
            [f"Month: {tab_name}", "", f"Income: {monthly_income}", ""],
            [""],
            ["Category", "Description", "Amount (MYR)", "Date"],
        ]
        ws.update("A1:D4", headers)
        ws.update("F1:G1", [["📊 SUMMARY", ""]])
        ws.update("F2:G6", [
            ["Total Income", monthly_income],
            ["Total Expenses", "=SUM(C5:C1000)"],
            ["Remaining Balance", f"={monthly_income}-SUM(C5:C1000)"],
            [""],
            ["Status", "=IF(G4>=0,\"✅ On Track\",\"❌ Over Budget\")"],
        ])

        return {
            "status": "success",
            "spreadsheet_url": spreadsheet.url,
            "spreadsheet_id": master_id,
            "tab_name": tab_name,
            "message": f"Created budget tab '{tab_name}' with income MYR {monthly_income}.",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def add_expense_entry(
    spreadsheet_id: str,
    category: str,
    description: str,
    amount: float,
    date: Optional[str] = None,
    tab_name: Optional[str] = None,
) -> dict:
    """
    Adds a single expense entry to an existing monthly budget tab.

    Args:
        spreadsheet_id (str): The master Google Spreadsheet ID.
        category (str): Expense category e.g. 'Food', 'Transport', 'Utilities'.
        description (str): Short description e.g. 'Grab to office'.
        amount (float): Expense amount in MYR.
        date (str, optional): Date as 'YYYY-MM-DD'. Defaults to today.
        tab_name (str, optional): Tab name e.g. 'March 2026'. Defaults to current month.

    Returns:
        dict: status and confirmation message or error.
    """
    try:
        gc = _get_client()
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        spreadsheet = gc.open_by_key(spreadsheet_id)

        if not date:
            date = datetime.today().strftime("%Y-%m-%d")
        if not tab_name:
            tab_name = datetime.today().strftime("%B %Y")

        try:
            ws = spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            return {
                "status": "error",
                "error": f"Tab '{tab_name}' not found. Create this month's budget first.",
            }

        all_values = ws.col_values(1)
        next_row = max(len(all_values) + 1, 5)
        ws.update(f"A{next_row}:D{next_row}", [[category, description, amount, date]])

        return {
            "status": "success",
            "message": f"Added: {category} | {description} | MYR {amount:.2f} on {date}",
            "row": next_row,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_budget_summary(
    spreadsheet_id: str,
    tab_name: Optional[str] = None,
) -> dict:
    """
    Retrieves full summary of monthly budget including income, expenses, and balance.

    Args:
        spreadsheet_id (str): The master Google Spreadsheet ID.
        tab_name (str, optional): Tab name e.g. 'March 2026'. Defaults to current month.

    Returns:
        dict: status, income, total_expenses, balance, category_totals, expenses list.
    """
    try:
        gc = _get_client()
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        spreadsheet = gc.open_by_key(spreadsheet_id)

        if not tab_name:
            tab_name = datetime.today().strftime("%B %Y")

        try:
            ws = spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            return {
                "status": "error",
                "error": f"Tab '{tab_name}' not found. Create this month's budget first.",
            }

        income_cell = ws.acell("C2").value or "0"
        income = float(str(income_cell).replace("Income:", "").strip())

        all_data = ws.get_all_values()
        expense_rows = all_data[4:]

        expenses = []
        total_expenses = 0.0
        category_totals: dict = {}

        for row in expense_rows:
            if len(row) >= 3 and row[0] and row[2]:
                try:
                    amount = float(row[2])
                    expenses.append({
                        "category": row[0],
                        "description": row[1] if len(row) > 1 else "",
                        "amount": amount,
                        "date": row[3] if len(row) > 3 else "",
                    })
                    total_expenses += amount
                    category_totals[row[0]] = category_totals.get(row[0], 0) + amount
                except ValueError:
                    continue

        balance = income - total_expenses

        return {
            "status": "success",
            "income": income,
            "total_expenses": total_expenses,
            "balance": balance,
            "is_over_budget": balance < 0,
            "category_totals": category_totals,
            "expenses": expenses,
            "spreadsheet_url": spreadsheet.url,
            "tab_name": tab_name,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}