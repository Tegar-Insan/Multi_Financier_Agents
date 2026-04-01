# 💰 Financial Agent — AI-Powered Personal Finance Assistant

> A multi-agent AI system built with **Google ADK** to help you track, analyze, and learn about your personal finances — all through natural language.

---

## 🤖 Agent Architecture

| Agent | Role | Responsibilities |
|-------|------|-----------------|
| 🧠 **OrchestratorAgent** | Delegator | Routes user queries to the right sub-agent |
| 📊 **BudgetTrackerAgent** | Data Input | Logs expenses (food, transport, salary, etc.) into Google Sheets |
| 📈 **FinancialAdvisorAgent** | Summarizer | Generates financial insights & spending perspectives |
| 📚 **FinancialPDFAgent** | Knowledge Base | Answers questions about stocks, crypto & financial literacy |

---

## ⚙️ Tech Stack

![Google ADK](https://img.shields.io/badge/Google%20ADK-Web-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API-green?style=flat-square)
![Google Drive](https://img.shields.io/badge/Google%20Drive-API-blue?style=flat-square)
![Status](https://img.shields.io/badge/Status-In%20Development-orange?style=flat-square)

---

## 🚀 Features

- 💬 **Natural language input** — just type your expenses, no forms needed
- 📋 **Auto-logging to Google Sheets** — budget tracked in real time
- 🧾 **Financial summaries** — understand where your money goes
- 📖 **Learn about finance** — ask about stocks, crypto, and investing

---

## 🗺️ How It Works
```
User Query
    ↓
OrchestratorAgent
    ├── Budget question?     → BudgetTrackerAgent   → Google Sheets
    ├── Financial summary?   → FinancialAdvisorAgent → Insights
    └── Learn about stocks?  → FinancialPDFAgent     → Knowledge
```

---

## 🛠️ Setup
```bash
git clone https://github.com/your-username/Financial_Agent.git
cd Financial_Agent
pip install -r requirements.txt
```

> Configure your Google Sheets API credentials before running.

---

## 🔮 Roadmap

- [x] Multi-agent architecture
- [x] Google Sheets integration
- [ ] Expense categorization with AI
- [ ] Monthly report generation
- [ ] Crypto portfolio tracker
- [ ] Web dashboard UI

---

## 🙌 Built With

- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- Google Sheets & Drive API
- Gemini 2.5 Flash

---

> ⚡ Still in active development — exciting new features coming soon!
