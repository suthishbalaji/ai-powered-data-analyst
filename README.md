# AI-Powered Data Analyst

> Upload a CSV, choose a dataset, and turn its data into answers, insights, anomaly checks, and charts.

![Python](https://img.shields.io/badge/Python-FastAPI-0b7285?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-149eca?logo=react&logoColor=white)
![CSV](https://img.shields.io/badge/Data-CSV-2f9e44)

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#how-to-use">How to Use</a>
</p>

---

## What it does

AI-Powered Data Analyst is a full-stack application for exploring CSV files without writing analysis code. Each uploaded CSV remains independent: when you select a dataset, the chat, insights, anomalies, charts, custom chart builder, and dashboard all use that file only.

## Features

| Area | Included capabilities |
| --- | --- |
| CSV management | Upload multiple CSV files, select one dataset, and remove files when finished. |
| AI analysis | Ask questions in plain language and receive dataset-specific answers, reasoning, code, and chart data where relevant. |
| Instant insight | View data summaries, missing values, duplicates, key metrics, trends, and category breakdowns. |
| Visual analysis | See suggested charts or build bar, line, pie, and scatter charts from selected columns. |
| Data quality | Detect missing-value issues, duplicates, negative values, and numerical outliers. |
| Reliable responses | Uses Gemini, then Groq, then OpenAI, then a local Pandas-based fallback. |

## Architecture

```mermaid
flowchart LR
    User["User"] --> Web["React + Vite frontend"]
    Web -->|"Upload, select CSV, ask question"| API["FastAPI backend"]
    API <--> Data["DatasetAnalyzer\nPandas DataFrames"]
    API --> Files["backend/uploads\nCSV storage"]

    API -->|"AI answer / dashboard"| Gemini["Gemini"]
    Gemini -->|"Unavailable or quota exceeded"| Groq["Groq"]
    Groq -->|"Unavailable"| OpenAI["OpenAI"]
    OpenAI -->|"Unavailable or no key"| Local["Local rule-based\nPandas analysis"]

    Data --> API
    Local --> API
    API -->|"Answers, insights, charts"| Web
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- An API key for Gemini, Groq, or OpenAI is optional. The local fallback remains available without one.

### 1. Install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

### 2. Configure an AI provider

Create `backend/.env`:

```env
# Add one or more providers. They are tried in this order.
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key

# Optional: this is the default Groq model.
GROQ_MODEL=llama-3.3-70b-versatile
```

> Keep this file private. It is already excluded by `.gitignore`.

### 3. Start the backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API is now available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 4. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite address shown in the terminal, usually [http://localhost:5173](http://localhost:5173).

## Configuration

The frontend connects to `http://localhost:8000` by default. To point it to a different backend, create `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
```

### AI fallback order

```text
Gemini  →  Groq  →  OpenAI  →  Local Pandas analysis
```

Provider availability and errors are logged by the backend without printing API key values. If a provider is unavailable, the application automatically moves to the next one.

## How to Use

1. Upload one or more `.csv` files.
2. Use the **Dataset Summary** dropdown to choose the file to analyze.
3. Ask a suggested question or enter your own in **Ask AI**.
4. Review file-specific insights, anomaly checks, and suggested charts.
5. Create a custom chart or generate a dashboard for the selected CSV.

## Useful Commands

| Task | Command |
| --- | --- |
| Run backend | `cd backend; ..\.venv\Scripts\python.exe -m uvicorn main:app --reload` |
| Run frontend | `cd frontend; npm run dev` |
| Build frontend | `cd frontend; npm run build` |
| Check backend syntax | `.\.venv\Scripts\python.exe -m compileall -q backend` |

## Project Structure

```text
AI-Powered-Data-Analyst/
├── backend/
│   ├── main.py          FastAPI application and environment loading
│   ├── routes.py        Upload, chat, chart, and dashboard endpoints
│   ├── analyzer.py      CSV summaries, insights, anomalies, and chart suggestions
│   ├── utils.py         Gemini → Groq → OpenAI → local fallback chain
│   └── uploads/         Runtime CSV uploads (ignored by Git)
├── frontend/
│   ├── src/             React UI components and API client
│   └── package.json     Frontend dependencies and scripts
├── .gitignore
└── README.md
```

---

Built with FastAPI, Pandas, React, Vite, and Recharts.