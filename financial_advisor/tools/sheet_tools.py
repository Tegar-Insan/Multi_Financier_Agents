import os
from datetime import datetime
from typing import Optional
import gspread 
from google.oauth2.service_account import Credentials



SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_creds():
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    return Credentials.from_service_account_file(creds_path, scopes=SCOPES)


def _get_client() -> gspread.Client:
    return gspread.authorize(_get_creds())


def record_income_sources() -> dict:
    """
    Prompts the user to input all income sources for the month and calculates net income.

    Returns:
        dict: status, net_income, and confirmation message.
    """
    try:
        total_income = 0.0
        income_sources = []

        print("Please enter your income sources for this month.")
        print("Type 'done' when finished.")

        while True:
            source = input("Income Source (or 'done'): ").strip()
            if source.lower() == "done":
                break
            amount_str = input(f"Amount for {source} (MYR): ").strip()
            try:
                amount = float(amount_str)
                total_income += amount
                income_sources.append({"source": source, "amount": amount})
            except ValueError:
                print("Invalid amount. Please enter a numeric value.")

        return {
            "status": "success",
            "net_income": total_income,
            "income_sources": income_sources,
            "message": f"Total monthly income recorded: MYR {total_income:.2f}",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def switch_tabs(tab_name: str, spreadsheet_id: Optional[str] = None) -> dict:
    """
    Switches to a specific tab in the Google Spreadsheet (e.g. 'Expense', 'Income', 'Dashboard').

    Args:
        tab_name (str): The name of the tab to switch to.
        spreadsheet_id (str, optional): The master Google Spreadsheet ID. Defaults to the
            configured GOOGLE_MASTER_SHEET_ID env var — do not ask the user for this.

    Returns:
        dict: status and confirmation message or error.
    """
    try:
        gc = _get_client()
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        spreadsheet = gc.open_by_key(spreadsheet_id)

        try:
            ws = spreadsheet.worksheet(tab_name)
            return {
                "status": "success",
                "message": f"Switched to tab '{tab_name}' successfully.",
                "tab_name": tab_name,
            }
        except gspread.WorksheetNotFound:
            return {
                "status": "error",
                "error": f"Tab '{tab_name}' not found in the spreadsheet.",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _append_row(spreadsheet, tab_name: str, category: str, amount: float, description: str, date: Optional[str]) -> dict:
    if not date:
        date_obj = datetime.today()
    else:
        date_obj = datetime.strptime(date, "%Y-%m-%d")

    date_str = date_obj.strftime("%Y-%m-%d")
    month_str = date_obj.strftime("%B")
    week_num = date_obj.isocalendar()[1]

    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        return {
            "status": "error",
            "error": f"Tab '{tab_name}' not found in the spreadsheet.",
        }

    all_values = ws.col_values(1)
    next_row = max(len(all_values) + 1, 2)
    ws.update(
        f"A{next_row}:F{next_row}",
        [[date_str, month_str, week_num, category, amount, description]],
    )

    return {"status": "success", "row": next_row, "date": date_str, "month": month_str, "week": week_num}


def add_expense_entry(
    category: str,
    description: str,
    amount: float,
    date: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
) -> dict:
    """
    Adds a single expense entry to the 'Expense' tab.

    Args:
        category (str): Expense category e.g. 'food', 'transport', 'housing', 'daily'.
        description (str): Short description e.g. 'Lunch', 'Bus Pass'.
        amount (float): Expense amount in MYR.
        date (str, optional): Date as 'YYYY-MM-DD'. Defaults to today.
        spreadsheet_id (str, optional): The master Google Spreadsheet ID. Defaults to the
            configured GOOGLE_MASTER_SHEET_ID env var — do not ask the user for this.

    Returns:
        dict: status and confirmation message or error.
    """
    try:
        gc = _get_client()
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        spreadsheet = gc.open_by_key(spreadsheet_id)

        result = _append_row(spreadsheet, "Expense", category, amount, description, date)
        if result["status"] == "error":
            return result

        return {
            "status": "success",
            "message": f"Added expense: {category} | {description} | MYR {amount:.2f} on {result['date']}",
            "row": result["row"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def add_income_entry(
    category: str,
    amount: float,
    description: Optional[str] = "",
    date: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
) -> dict:
    """
    Adds a single income entry to the 'Income' tab.

    Args:
        category (str): Income source e.g. 'salary', 'allowance', 'freelance'.
        amount (float): Income amount in MYR.
        description (str, optional): Short description e.g. 'Monthly Allowance'.
        date (str, optional): Date as 'YYYY-MM-DD'. Defaults to today.
        spreadsheet_id (str, optional): The master Google Spreadsheet ID. Defaults to the
            configured GOOGLE_MASTER_SHEET_ID env var — do not ask the user for this.

    Returns:
        dict: status and confirmation message or error.
    """
    try:
        gc = _get_client()
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        spreadsheet = gc.open_by_key(spreadsheet_id)

        result = _append_row(spreadsheet, "Income", category, amount, description, date)
        if result["status"] == "error":
            return result

        return {
            "status": "success",
            "message": f"Added income: {category} | MYR {amount:.2f} on {result['date']}",
            "row": result["row"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _parse_amount(raw: str) -> Optional[float]:
    cleaned = raw.replace("RM", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _read_entries(ws, month: Optional[str]) -> tuple:
    rows = ws.get_all_values()[1:]
    entries = []
    total = 0.0
    category_totals: dict = {}

    for row in rows:
        if len(row) < 5 or not row[0]:
            continue
        if month and row[1].strip().lower() != month.strip().lower():
            continue
        amount = _parse_amount(row[4])
        if amount is None:
            continue

        category = row[3]
        entries.append({
            "date": row[0],
            "month": row[1],
            "week": row[2],
            "category": category,
            "amount": amount,
            "description": row[5] if len(row) > 5 else "",
        })
        total += amount
        category_totals[category] = category_totals.get(category, 0) + amount

    return entries, total, category_totals


def get_budget_summary(
    month: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
) -> dict:
    """
    Retrieves full budget summary from the 'Income' and 'Expense' tabs, including total
    income, total expenses, balance, and per-category expense breakdown.

    Args:
        month (str, optional): Filter entries by month name e.g. 'May'. Defaults to all months.
        spreadsheet_id (str, optional): The master Google Spreadsheet ID. Defaults to the
            configured GOOGLE_MASTER_SHEET_ID env var — do not ask the user for this.

    Returns:
        dict: status, total_income, total_expenses, balance, category_totals, income, expenses.
    """
    try:
        gc = _get_client()
        if not spreadsheet_id:
            spreadsheet_id = os.getenv("GOOGLE_MASTER_SHEET_ID")

        spreadsheet = gc.open_by_key(spreadsheet_id)

        try:
            income_ws = spreadsheet.worksheet("Income")
            expense_ws = spreadsheet.worksheet("Expense")
        except gspread.WorksheetNotFound as e:
            return {"status": "error", "error": f"Tab not found: {e}"}

        income_entries, total_income, income_category_totals = _read_entries(income_ws, month)
        expense_entries, total_expenses, expense_category_totals = _read_entries(expense_ws, month)

        balance = total_income - total_expenses

        return {
            "status": "success",
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "is_over_budget": balance < 0,
            "category_totals": expense_category_totals,
            "income_category_totals": income_category_totals,
            "income": income_entries,
            "expenses": expense_entries,
            "spreadsheet_url": spreadsheet.url,
            "month": month,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}