import os
import json
import re
import numpy as np
import pandas as pd
from typing import Dict, List, Any

try:
    from google import genai as google_genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False


def _build_context(datasets: Dict[str, pd.DataFrame], summaries: Dict[str, Any]) -> str:
    """Build a rich context string with schema + statistics + sample rows for the LLM."""
    ctx = "=== AVAILABLE DATASETS ===\n\n"
    for filename, df in datasets.items():
        summary = summaries.get(filename, {})
        ctx += f"FILE: {filename}\n"
        ctx += f"Shape: {summary.get('rows')} rows x {summary.get('columns')} columns\n"
        ctx += f"Missing values: {summary.get('missing_values')} | Duplicate rows: {summary.get('duplicate_rows')}\n\n"

        # Column schema with stats
        ctx += "COLUMNS:\n"
        for col in summary.get("columns_info", []):
            samples = ", ".join([f"'{s}'" for s in col.get("samples", [])])
            ctx += f"  - {col['name']} ({col['type']}): missing={col['missing']}, samples=[{samples}]\n"

        # Numeric statistics
        num_df = df.select_dtypes(include=[np.number])
        if not num_df.empty:
            ctx += "\nNUMERIC STATISTICS:\n"
            stats = num_df.describe().round(2)
            for col in stats.columns:
                s = stats[col]
                ctx += (f"  - {col}: min={s['min']}, max={s['max']}, "
                        f"mean={s['mean']:.2f}, std={s['std']:.2f}, "
                        f"25%={s['25%']}, 75%={s['75%']}\n")

        # Categorical value counts
        cat_df = df.select_dtypes(include=["object", "category"])
        if not cat_df.empty:
            ctx += "\nCATEGORICAL VALUE COUNTS (top 5 per column):\n"
            for col in cat_df.columns[:6]:
                counts = df[col].value_counts().head(5)
                counts_str = ", ".join([f"{k}:{v}" for k, v in counts.items()])
                ctx += f"  - {col}: [{counts_str}]\n"

        # Sample rows
        ctx += "\nSAMPLE ROWS (first 5):\n"
        ctx += df.head(5).to_string(index=False) + "\n"
        ctx += "\n" + "=" * 50 + "\n\n"

    return ctx


SYSTEM_PROMPT = """You are an expert AI Data Analyst with deep knowledge of statistics, business intelligence, and data science.

You analyze CSV datasets and answer user questions with precision, citing actual numbers from the data.

You MUST respond with a single valid JSON object (no markdown fences, no extra text) with this exact structure:
{
  "answer": "Clear, detailed markdown answer with actual numbers. Use **bold** for key figures. Use bullet lists where helpful.",
  "reasoning": "Step-by-step explanation of how you derived the answer (e.g., grouped by region, summed sales, sorted descending).",
  "sql_code": "ANSI SQL query answering this question. Use the filename as table name. Always include this unless the question is purely conversational.",
  "pandas_code": "Complete Python/Pandas code snippet. Always include this unless the question is purely conversational.",
  "chart": {
    "chart_type": "bar" | "line" | "pie" | "scatter",
    "title": "Descriptive chart title",
    "x_axis": "column name for X axis",
    "y_axis": "column name for Y axis",
    "data": [{"name": "label", "value": 123.45}, ...]
  }
}

RULES:
1. Always compute actual values from the data statistics provided — never make up numbers.
2. Include sql_code and pandas_code for every analytical question.
3. Include a chart whenever the answer involves comparisons, trends, distributions, or rankings.
4. For scatter charts use: {"x": number, "y": number} format in data array.
5. Chart data values must be numbers (int or float), never strings.
6. If the question asks for anomalies, explain each one with the actual value and why it's anomalous.
7. Keep answers concise but complete. Reference the filename in your answer.
8. For "generate SQL" or "generate pandas" requests, provide thorough, runnable code.
"""


def query_llm(
    query: str,
    datasets: Dict[str, pd.DataFrame],
    summaries: Dict[str, Any],
    chat_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    context = _build_context(datasets, summaries)

    history_str = ""
    if chat_history:
        history_str = "=== CONVERSATION HISTORY ===\n"
        for msg in chat_history[-8:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            # Truncate long assistant messages in history
            content = msg["content"][:300] + "..." if len(msg["content"]) > 300 else msg["content"]
            history_str += f"{role}: {content}\n"
        history_str += "\n"

    user_prompt = f"{context}\n{history_str}=== USER QUESTION ===\n{query}\n"

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    # Validate keys — skip placeholder/empty values
    def _is_valid_key(key: str) -> bool:
        return bool(key) and len(key) > 20 and "your_" not in key.lower() and "placeholder" not in key.lower()

    # ── Diagnostics: print exactly why each provider is or isn't attempted ────
    print(f"[LLM] GEMINI_API_KEY present={bool(gemini_key)} valid={_is_valid_key(gemini_key)} pkg_installed={HAS_GEMINI}")
    print(f"[LLM] GROQ_API_KEY present={bool(groq_key)} valid={_is_valid_key(groq_key)} pkg_installed={HAS_GROQ}")
    print(f"[LLM] OPENAI_API_KEY present={bool(openai_key)} valid={_is_valid_key(openai_key)} pkg_installed={HAS_OPENAI}")

    if _is_valid_key(gemini_key) and HAS_GEMINI:
        try:
            return _call_gemini(gemini_key, user_prompt)
        except Exception as e:
            import traceback
            print(f"[Gemini] Failed: {e}")
            traceback.print_exc()
    elif gemini_key and not HAS_GEMINI:
        print("[LLM] GEMINI_API_KEY is set but the 'google-genai' package is not installed.")
    elif gemini_key and not _is_valid_key(gemini_key):
        print("[LLM] GEMINI_API_KEY is set but failed validation (too short, or contains 'your_'/'placeholder').")

    # Groq is intentionally second: it is used whenever Gemini is unavailable,
    # rejects a request, or returns an invalid response.
    if _is_valid_key(groq_key) and HAS_GROQ:
        try:
            print(f"[Groq] Attempting model={os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')}")
            return _call_groq(groq_key, user_prompt)
        except Exception as e:
            import traceback
            print(f"[Groq] Failed: {e}")
            traceback.print_exc()
    elif groq_key and not HAS_GROQ:
        print("[LLM] GROQ_API_KEY is set but the 'groq' package is not installed.")
    elif groq_key and not _is_valid_key(groq_key):
        print("[LLM] GROQ_API_KEY is set but failed validation (too short, or contains 'your_'/'placeholder').")

    if _is_valid_key(openai_key) and HAS_OPENAI:
        try:
            return _call_openai(openai_key, user_prompt)
        except Exception as e:
            import traceback
            print(f"[OpenAI] Failed: {e}")
            traceback.print_exc()
    elif openai_key and not HAS_OPENAI:
        print("[LLM] OPENAI_API_KEY is set but the 'openai' package is not installed.")
    elif openai_key and not _is_valid_key(openai_key):
        print("[LLM] OPENAI_API_KEY is set but failed validation (too short, or contains 'your_'/'placeholder').")

    print("[LLM] Falling back to rule-based engine.")
    return _rule_based_fallback(query, datasets, summaries)


def _call_gemini(api_key: str, user_prompt: str) -> Dict[str, Any]:
    client = google_genai.Client(api_key=api_key)
    full_prompt = SYSTEM_PROMPT + "\n\n" + user_prompt
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
        }
    )
    return _parse_json(response.text)


def _call_openai(api_key: str, user_prompt: str) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    return _parse_json(response.choices[0].message.content)


def _call_groq(api_key: str, user_prompt: str) -> Dict[str, Any]:
    """Calls Groq's OpenAI-compatible chat API and requests strict JSON."""
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return _parse_json(response.choices[0].message.content)


def _parse_json(text: str) -> Dict[str, Any]:
    txt = text.strip()
    # Strip markdown fences if present
    txt = re.sub(r"^```(?:json)?\s*", "", txt)
    txt = re.sub(r"\s*```$", "", txt)
    return json.loads(txt.strip())


def _find_col(patterns: List[str], columns: List[str]) -> str | None:
    for pat in patterns:
        for col in columns:
            if re.search(pat, col.lower()):
                return col
    return None


def _rule_based_fallback(
    query: str,
    datasets: Dict[str, pd.DataFrame],
    summaries: Dict[str, Any]
) -> Dict[str, Any]:
    """Smart data analysis engine — dynamically parses questions and runs real pandas computations."""
    q = query.lower().strip()

    if not datasets:
        return {
            "answer": "No dataset uploaded yet. Please upload a CSV file to get started.",
            "reasoning": "No data files found in session.",
            "sql_code": None, "pandas_code": None, "chart": None
        }

    # ── Pick most relevant dataset ────────────────────────────────────────────
    filename = list(datasets.keys())[0]
    for fn in datasets:
        if fn.lower().replace(".csv", "").replace("_", " ") in q:
            filename = fn
            break

    df = datasets[filename]
    num_cols = list(df.select_dtypes(include=[np.number]).columns)
    cat_cols = list(df.select_dtypes(include=["object", "category"]).columns)
    all_cols = list(df.columns)

    # ── Dynamic column resolution ─────────────────────────────────────────────
    # Find ALL columns mentioned in the user's question (fuzzy match)
    def _resolve_columns(question: str, columns: List[str]) -> List[str]:
        found = []
        q_words = question.lower()
        for col in columns:
            col_lower = col.lower()
            col_readable = col_lower.replace("_", " ").replace("-", " ")
            # Exact match
            if col_lower in q_words or col_readable in q_words:
                found.append(col)
                continue
            # Partial match (each word of column name)
            col_parts = col_readable.split()
            if len(col_parts) > 1 and all(p in q_words for p in col_parts):
                found.append(col)
                continue
            # Single-word partial match if word is 4+ chars (avoid false positives)
            if len(col_lower) >= 4 and col_lower in q_words:
                found.append(col)
        return found

    mentioned_cols = _resolve_columns(q, all_cols)
    mentioned_num = [c for c in mentioned_cols if c in num_cols]
    mentioned_cat = [c for c in mentioned_cols if c in cat_cols]

    # Smart defaults for value/grouping columns
    def _best_value_col():
        if mentioned_num:
            return mentioned_num[0]
        return _find_col(["sales", "revenue", "amount", "total_price", "total", "price", "profit", "value", "cost", "income", "score", "rating", "quantity"], num_cols) or (num_cols[0] if num_cols else None)

    def _best_group_col():
        if mentioned_cat:
            return mentioned_cat[0]
        return _find_col(["category", "dept", "department", "type", "segment", "region", "country", "product", "item", "name", "city", "state", "group", "team", "brand", "class"], cat_cols) or (cat_cols[0] if cat_cols else None)

    def _best_date_col():
        return _find_col(["date", "time", "month", "year", "period", "week", "day", "timestamp", "created"], all_cols)

    val_col = _best_value_col()
    grp_col = _best_group_col()
    date_col = _best_date_col()

    # Extract N (e.g., "top 10" → 10)
    n_match = re.search(r'\b(\d+)\b', q)
    user_n = int(n_match.group(1)) if n_match else 5

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _resp(answer, reasoning, sql=None, pandas_code=None, chart=None):
        return {"answer": answer, "reasoning": reasoning, "sql_code": sql, "pandas_code": pandas_code, "chart": chart}

    def _make_chart(chart_type, data_dict, title, x_label, y_label):
        return {
            "chart_type": chart_type, "title": title,
            "x_axis": x_label, "y_axis": y_label,
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in data_dict.items()]
        }

    # ── Intent detection ──────────────────────────────────────────────────────
    # Detect what the user wants to do with priority ordering
    INTENTS = {
        "sql":         ["sql", "write sql", "sql query", "generate sql", "database query"],
        "code":        ["pandas", "python", "code", "script", "generate code", "snippet", "how to code"],
        "missing":     ["missing", "null", "nan", "empty", "incomplete", "data quality", "clean"],
        "anomaly":     ["anomaly", "anomalies", "outlier", "unusual", "weird", "abnormal", "spike", "extreme"],
        "correlation": ["correlat", "relationship", "depend", "relation between"],
        "distribution":["distribut", "histogram", "spread", "frequencies"],
        "trend":       ["trend", "over time", "time series", "growth", "decline", "monthly", "yearly", "weekly", "daily"],
        "compare":     ["compare", "versus", "vs ", "difference between", "which is better", "contrast"],
        "bottom":      ["bottom", "worst", "lowest", "least", "minimum", "smallest", "fewest", "weakest"],
        "top":         ["top", "highest", "best", "most", "largest", "maximum", "biggest", "leading", "greatest"],
        "total":       ["total", "sum ", "how much", "overall", "grand total", "altogether", "combined", "aggregate"],
        "average":     ["average", "mean", "avg ", "typical", "per unit", "per record"],
        "count":       ["count", "how many", "number of", "records", "rows", "entries", "frequency"],
        "profit":      ["profit", "margin", "loss", "gain", "net income", "profitability"],
        "unique":      ["unique", "distinct", "different", "categories", "list of", "show me all", "what are the"],
        "filter":      ["where", "filter", "only", "greater than", "less than", "more than", "above", "below", "equal"],
        "summary":     ["summarize", "summary", "overview", "describe", "tell me about", "explain", "analyze", "insight", "what is this"],
    }

    detected_intent = None
    for intent, keywords in INTENTS.items():
        if any(kw in q for kw in keywords):
            detected_intent = intent
            break

    # ── INTENT HANDLERS ───────────────────────────────────────────────────────

    # SQL generation
    if detected_intent == "sql":
        target = val_col or (num_cols[0] if num_cols else "*")
        group = grp_col
        if group and target != "*":
            sql = f"SELECT {group},\n       SUM({target}) AS total_{target},\n       AVG({target}) AS avg_{target},\n       COUNT(*) AS records\nFROM   `{filename}`\nGROUP  BY {group}\nORDER  BY total_{target} DESC;"
        else:
            sql = f"SELECT * FROM `{filename}` LIMIT 10;"
        return _resp(f"Here is the SQL query for **{filename}**:", "Generated SQL based on detected columns.", sql,
                     f"import pandas as pd\ndf = pd.read_csv('{filename}')\n" + (f"df.groupby('{group}')['{target}'].agg(['sum','mean','count']).sort_values('sum', ascending=False)" if group and target != "*" else "df.head(10)"))

    # Python/Pandas code
    if detected_intent == "code":
        target = val_col or (num_cols[0] if num_cols else None)
        group = grp_col
        code = f"import pandas as pd\nimport numpy as np\n\ndf = pd.read_csv('{filename}')\nprint(f'Shape: {{df.shape}}')\nprint(df.dtypes)\n\n"
        if target and group:
            code += f"# Analysis of {target} by {group}\nsummary = df.groupby('{group}')['{target}'].agg(['sum','mean','count','min','max'])\nsummary = summary.sort_values('sum', ascending=False)\nprint(summary)\n\n# Overall\nprint(f'Total {target}: {{df[\"{target}\"].sum():,.2f}}')\nprint(f'Average {target}: {{df[\"{target}\"].mean():,.2f}}')"
        elif target:
            code += f"print(df['{target}'].describe())\n"
        else:
            code += "print(df.describe())\nprint(df.head())"
        return _resp(f"Here is Python/Pandas code for **{filename}**:", "Generated code for the detected columns.", None, code)

    # Missing values
    if detected_intent == "missing":
        missing = df.isnull().sum()
        missing = missing[missing > 0].sort_values(ascending=False)
        total_m = int(df.isnull().sum().sum())
        total_c = df.shape[0] * df.shape[1]
        pct = ((total_c - total_m) / total_c) * 100 if total_c > 0 else 100
        if missing.empty:
            answer = f"✅ **{filename}** has **no missing values** — fully complete ({len(df):,} rows × {len(df.columns)} cols)."
        else:
            lines = [f"- **{c}**: {int(v):,} missing ({v/len(df)*100:.1f}%)" for c, v in missing.head(15).items()]
            answer = f"**Missing Values in `{filename}`:**\n\n" + "\n".join(lines) + f"\n\n**Data completeness: {pct:.1f}%** ({total_m:,} missing out of {total_c:,} cells)"
        return _resp(answer, "Counted nulls per column.", None,
                     f"import pandas as pd\ndf = pd.read_csv('{filename}')\nprint(df.isnull().sum().sort_values(ascending=False))")

    # Anomalies
    if detected_intent == "anomaly":
        target_cols = mentioned_num if mentioned_num else num_cols[:6]
        findings = []
        for col in target_cols:
            s = df[col].dropna()
            if len(s) < 4:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lb, ub = q1 - 2.5 * iqr, q3 + 2.5 * iqr
                out = s[(s > ub) | (s < lb)]
                if len(out):
                    findings.append(f"- **{col}**: {len(out)} outlier(s) — [{out.min():.2f}, {out.max():.2f}] (normal: [{lb:.2f}, {ub:.2f}])")
            mean, std_dev = s.mean(), s.std()
            if std_dev > 0:
                z_out = s[np.abs((s - mean) / std_dev) > 3]
                if len(z_out):
                    findings.append(f"- **{col}**: {len(z_out)} extreme value(s) via Z-score >3 (mean={mean:.2f})")
        answer = f"**Anomaly Report — `{filename}`:**\n\n" + ("\n".join(findings) if findings else "✅ No anomalies detected (IQR 2.5× and Z-score >3).")
        return _resp(answer, "IQR and Z-score analysis on numeric columns.", None,
                     f"import pandas as pd, numpy as np\ndf = pd.read_csv('{filename}')\nfor col in df.select_dtypes('number'):\n    q1,q3 = df[col].quantile([.25,.75])\n    iqr=q3-q1\n    print(col, ((df[col]<q1-2.5*iqr)|(df[col]>q3+2.5*iqr)).sum(), 'outliers')")

    # Correlation
    if detected_intent == "correlation":
        if len(num_cols) >= 2:
            target_nums = mentioned_num if len(mentioned_num) >= 2 else num_cols
            corr = df[target_nums].corr()
            pairs = []
            for i, c1 in enumerate(target_nums):
                for c2 in target_nums[i+1:]:
                    r = corr.loc[c1, c2]
                    if not np.isnan(r):
                        pairs.append((abs(r), c1, c2, r))
            pairs.sort(reverse=True)
            lines = [f"- **{c1}** ↔ **{c2}**: r = {r:.3f} ({'strong' if abs(r)>0.7 else 'moderate' if abs(r)>0.4 else 'weak'})"
                     for _, c1, c2, r in pairs[:8]]
            x, y = pairs[0][1], pairs[0][2]
            sample = df[[x, y]].dropna().head(150)
            scatter = [{"x": float(row[x]), "y": float(row[y]), "name": f"#{i}"} for i, (_, row) in enumerate(sample.iterrows())]
            return _resp(f"**Correlations in `{filename}`:**\n\n" + "\n".join(lines), "Pearson correlation matrix.",
                         None, f"import pandas as pd\ndf = pd.read_csv('{filename}')\nprint(df[{target_nums}].corr().round(3))",
                         {"chart_type": "scatter", "title": f"{y} vs {x}", "x_axis": x, "y_axis": y, "data": scatter})
        return _resp("Need at least 2 numeric columns for correlation analysis.", "Insufficient numeric columns.")

    # Distribution
    if detected_intent == "distribution":
        target = mentioned_num[0] if mentioned_num else (val_col or (num_cols[0] if num_cols else None))
        if target:
            s = df[target].dropna()
            desc = s.describe()
            bins = pd.cut(s, bins=8).value_counts().sort_index()
            chart_data = [{"name": str(k), "value": int(v)} for k, v in bins.items()]
            return _resp(
                f"**Distribution of `{target}` in `{filename}`:**\n\n"
                f"- Count: **{int(desc['count']):,}** | Min: **{desc['min']:,.2f}** | Max: **{desc['max']:,.2f}**\n"
                f"- Mean: **{desc['mean']:,.2f}** | Median: **{s.median():,.2f}** | Std: **{desc['std']:,.2f}**\n"
                f"- 25%: {desc['25%']:,.2f} | 75%: {desc['75%']:,.2f}",
                f"describe() and binning of '{target}'.", None,
                f"import pandas as pd\ndf = pd.read_csv('{filename}')\nprint(df['{target}'].describe())",
                {"chart_type": "bar", "title": f"Distribution of {target}", "x_axis": "Range", "y_axis": "Count", "data": chart_data})

    # Trend / time series
    if detected_intent == "trend":
        target = mentioned_num[0] if mentioned_num else (val_col or (num_cols[0] if num_cols else None))
        d_col = _best_date_col()
        if d_col and target:
            try:
                tmp = df.copy()
                tmp["_dt"] = pd.to_datetime(tmp[d_col], errors="coerce")
                tmp = tmp.dropna(subset=["_dt"])
                tmp["_p"] = tmp["_dt"].dt.strftime("%Y-%m")
                monthly = tmp.groupby("_p")[target].sum().sort_index()
                best, worst = monthly.idxmax(), monthly.idxmin()
                g = ((monthly.iloc[-1] - monthly.iloc[0]) / abs(monthly.iloc[0]) * 100) if len(monthly) > 1 and monthly.iloc[0] != 0 else 0
                return _resp(
                    f"**{target} Trend Over Time — `{filename}`:**\n\n"
                    f"- **Peak:** {best} → {monthly[best]:,.2f}\n"
                    f"- **Lowest:** {worst} → {monthly[worst]:,.2f}\n"
                    f"- **Avg/month:** {monthly.mean():,.2f}\n"
                    f"- **Growth:** {g:+.1f}% | **Periods:** {len(monthly)}",
                    f"Parsed '{d_col}' as dates, grouped by month, summed '{target}'.",
                    f"SELECT strftime('%Y-%m', {d_col}) AS month, SUM({target}) FROM `{filename}` GROUP BY month ORDER BY month;",
                    f"import pandas as pd\ndf = pd.read_csv('{filename}')\ndf['{d_col}']=pd.to_datetime(df['{d_col}'])\nprint(df.groupby(df['{d_col}'].dt.to_period('M'))['{target}'].sum())",
                    _make_chart("line", monthly, f"{target} Monthly Trend", "Month", target))
            except Exception:
                pass

    # Compare
    if detected_intent == "compare":
        target = mentioned_num[0] if mentioned_num else val_col
        group = mentioned_cat[0] if mentioned_cat else grp_col
        if group and target:
            agg = df.groupby(group)[target].agg(["sum", "mean", "count", "min", "max"])
            agg.columns = ["Total", "Average", "Count", "Min", "Max"]
            agg = agg.sort_values("Total", ascending=False)
            lines = [f"- **{k}**: Total={row['Total']:,.2f}, Avg={row['Average']:,.2f}, Count={int(row['Count'])}" for k, row in agg.head(10).iterrows()]
            return _resp(
                f"**Comparison of `{target}` by `{group}` — `{filename}`:**\n\n" + "\n".join(lines),
                f"Grouped '{target}' by '{group}' with sum/mean/count.",
                f"SELECT {group}, SUM({target}), AVG({target}), COUNT(*) FROM `{filename}` GROUP BY {group} ORDER BY 2 DESC;",
                f"import pandas as pd\ndf = pd.read_csv('{filename}')\nprint(df.groupby('{group}')['{target}'].agg(['sum','mean','count']).sort_values('sum', ascending=False))",
                _make_chart("bar", df.groupby(group)[target].sum().sort_values(ascending=False).head(10), f"{target} by {group}", group, target))

    # Bottom / worst
    if detected_intent == "bottom":
        target = mentioned_num[0] if mentioned_num else val_col
        group = mentioned_cat[0] if mentioned_cat else grp_col
        if group and target:
            grouped = df.groupby(group)[target].sum().sort_values(ascending=True).head(user_n)
            total = df[target].sum()
            lines = [f"- **{k}**: {v:,.2f} ({v/total*100:.1f}%)" for k, v in grouped.items()]
            return _resp(
                f"**Bottom {user_n} `{group}` by `{target}` — `{filename}`:**\n\n" + "\n".join(lines),
                f"Grouped, summed, sorted ascending.", None, None,
                _make_chart("bar", grouped, f"Bottom {user_n} {group} by {target}", group, target))
        if num_cols:
            t = mentioned_num[0] if mentioned_num else num_cols[0]
            min_v = df[t].min()
            row = df[df[t] == min_v].iloc[0]
            detail = ", ".join([f"**{k}**: {v}" for k, v in list(row.to_dict().items())[:6]])
            return _resp(f"**Minimum `{t}`** in `{filename}`: **{min_v:,.2f}**\n\n{detail}", f"df['{t}'].min().")

    # Top / best / highest
    if detected_intent == "top":
        target = mentioned_num[0] if mentioned_num else val_col
        group = mentioned_cat[0] if mentioned_cat else grp_col
        if group and target:
            grouped = df.groupby(group)[target].sum().sort_values(ascending=False).head(user_n)
            total = df[target].sum()
            lines = [f"- **{k}**: {v:,.2f} ({v/total*100:.1f}%)" for k, v in grouped.items()]
            return _resp(
                f"**Top {user_n} `{group}` by `{target}` — `{filename}`:**\n\n" + "\n".join(lines) + f"\n\n**Total:** {total:,.2f}",
                f"Grouped '{target}' by '{group}', sorted descending.",
                f"SELECT {group}, SUM({target}) AS total FROM `{filename}` GROUP BY {group} ORDER BY total DESC LIMIT {user_n};",
                f"import pandas as pd\ndf = pd.read_csv('{filename}')\ndf.groupby('{group}')['{target}'].sum().sort_values(ascending=False).head({user_n})",
                _make_chart("bar", grouped, f"Top {user_n} {group} by {target}", group, target))
        if num_cols:
            t = mentioned_num[0] if mentioned_num else (val_col or num_cols[0])
            max_v = df[t].max()
            row = df[df[t] == max_v].iloc[0]
            detail = ", ".join([f"**{k}**: {v}" for k, v in list(row.to_dict().items())[:6]])
            return _resp(f"**Maximum `{t}`** in `{filename}`: **{max_v:,.2f}**\n\n{detail}", f"df['{t}'].max().")

    # Total / sum
    if detected_intent == "total":
        target = mentioned_num[0] if mentioned_num else val_col
        group = mentioned_cat[0] if mentioned_cat else grp_col
        if target:
            total = df[target].sum()
            answer = f"**Total `{target}`** in `{filename}`: **{total:,.2f}**\n\n"
            chart = None
            if group:
                by_g = df.groupby(group)[target].sum().sort_values(ascending=False).head(10)
                answer += f"**By {group}:**\n" + "\n".join([f"- {k}: {v:,.2f} ({v/total*100:.1f}%)" for k, v in by_g.items()])
                chart = _make_chart("bar", by_g, f"Total {target} by {group}", group, target)
            return _resp(answer, f"Summed '{target}'.", f"SELECT SUM({target}) FROM `{filename}`;", None, chart)

    # Average
    if detected_intent == "average":
        target = mentioned_num[0] if mentioned_num else val_col
        group = mentioned_cat[0] if mentioned_cat else grp_col
        if target:
            avg = df[target].mean()
            med = df[target].median()
            answer = f"**Average `{target}`** in `{filename}`: **{avg:,.2f}** (median: {med:,.2f})\n\n"
            chart = None
            if group:
                by_g = df.groupby(group)[target].mean().sort_values(ascending=False)
                answer += f"**By {group}:**\n" + "\n".join([f"- {k}: {v:,.2f}" for k, v in by_g.head(12).items()])
                chart = _make_chart("bar", by_g.head(10), f"Average {target} by {group}", group, target)
            return _resp(answer, f"df['{target}'].mean().", f"SELECT AVG({target}) FROM `{filename}`;", None, chart)

    # Count
    if detected_intent == "count":
        group = mentioned_cat[0] if mentioned_cat else grp_col
        if group:
            counts = df[group].value_counts()
            lines = [f"- **{k}**: {v:,} ({v/len(df)*100:.1f}%)" for k, v in counts.head(user_n).items()]
            return _resp(
                f"**Count by `{group}`** in `{filename}` ({len(df):,} total):\n\n" + "\n".join(lines),
                f"value_counts() on '{group}'.", None, None,
                _make_chart("pie", counts.head(8), f"Records by {group}", group, "Count"))
        return _resp(f"`{filename}` has **{len(df):,} records** and **{len(df.columns)} columns**.",
                     "df.shape.", f"SELECT COUNT(*) FROM `{filename}`;", None)

    # Profit
    if detected_intent == "profit":
        p_col = _find_col(["profit", "margin", "gain", "net"], num_cols)
        if p_col:
            tp = df[p_col].sum()
            neg = (df[p_col] < 0).sum()
            answer = f"**Profit Analysis — `{filename}`:**\n\n- **Total:** {tp:,.2f}\n- **Average:** {df[p_col].mean():,.2f}\n- **Losses:** {neg:,} records\n- **Profitable:** {(df[p_col]>=0).sum():,} records"
            s_col = _find_col(["sales", "revenue", "amount", "total", "price"], num_cols)
            if s_col and df[s_col].sum() > 0:
                answer += f"\n- **Margin:** {tp/df[s_col].sum()*100:.1f}%"
            chart = None
            if grp_col:
                by_g = df.groupby(grp_col)[p_col].sum().sort_values(ascending=False)
                chart = _make_chart("bar", by_g.head(10), f"{p_col} by {grp_col}", grp_col, p_col)
            return _resp(answer, f"Summed '{p_col}'.", None, None, chart)

    # Unique values
    if detected_intent == "unique":
        target = mentioned_cat[0] if mentioned_cat else grp_col
        if target:
            uniq = df[target].dropna().unique()
            counts = df[target].value_counts()
            vals = ", ".join([str(u) for u in sorted(uniq)[:25]])
            if len(uniq) > 25:
                vals += f"... (+{len(uniq)-25} more)"
            return _resp(
                f"**`{target}` in `{filename}`** — {len(uniq)} unique values:\n\n{vals}\n\n**Most frequent:** {counts.index[0]} ({counts.iloc[0]:,})",
                f"df['{target}'].unique().", None, None,
                _make_chart("pie", counts.head(8), f"Distribution of {target}", target, "Count"))

    # Filter
    if detected_intent == "filter":
        # Try to extract a filter condition from the question
        target = mentioned_num[0] if mentioned_num else val_col
        if target:
            if "greater than" in q or "more than" in q or "above" in q:
                threshold = float(n_match.group(1)) if n_match else df[target].mean()
                filtered = df[df[target] > threshold]
                return _resp(
                    f"**{len(filtered):,} records** where `{target}` > {threshold:,.2f} (out of {len(df):,} total)\n\n"
                    f"Average in filtered set: **{filtered[target].mean():,.2f}**",
                    f"Filtered df['{target}'] > {threshold}.", None, None)
            if "less than" in q or "below" in q or "under" in q:
                threshold = float(n_match.group(1)) if n_match else df[target].mean()
                filtered = df[df[target] < threshold]
                return _resp(
                    f"**{len(filtered):,} records** where `{target}` < {threshold:,.2f} (out of {len(df):,} total)\n\n"
                    f"Average in filtered set: **{filtered[target].mean():,.2f}**",
                    f"Filtered df['{target}'] < {threshold}.", None, None)

    # Summary / overview
    if detected_intent == "summary":
        num_stats = df[num_cols].describe().round(2).to_string() if num_cols else "No numeric columns."
        answer = (f"**Dataset: `{filename}`**\n\n"
                  f"- **Size:** {len(df):,} rows × {len(df.columns)} columns\n"
                  f"- **Numeric ({len(num_cols)}):** {', '.join(num_cols[:6]) or 'None'}\n"
                  f"- **Categorical ({len(cat_cols)}):** {', '.join(cat_cols[:6]) or 'None'}\n"
                  f"- **Missing:** {int(df.isnull().sum().sum()):,} | **Duplicates:** {int(df.duplicated().sum()):,}\n\n"
                  f"```\n{num_stats}\n```")
        chart = None
        if grp_col and val_col:
            by_g = df.groupby(grp_col)[val_col].sum().sort_values(ascending=False).head(8)
            chart = _make_chart("bar", by_g, f"{val_col} by {grp_col}", grp_col, val_col)
        return _resp(answer, "df.describe() + df.info().", f"SELECT COUNT(*) FROM `{filename}`;", None, chart)

    # ── SPECIFIC COLUMN QUERY (catch-all for mentioned columns) ───────────────
    if mentioned_num:
        col = mentioned_num[0]
        s = df[col].dropna()
        desc = s.describe()
        answer = (f"**`{col}` in `{filename}`:**\n\n"
                  f"- **Sum:** {s.sum():,.2f} | **Mean:** {desc['mean']:,.2f} | **Median:** {s.median():,.2f}\n"
                  f"- **Min:** {desc['min']:,.2f} | **Max:** {desc['max']:,.2f} | **Std:** {desc['std']:,.2f}\n"
                  f"- **Count:** {int(desc['count']):,} | **Missing:** {df[col].isnull().sum()}")
        chart = None
        if grp_col:
            by_g = df.groupby(grp_col)[col].sum().sort_values(ascending=False).head(10)
            chart = _make_chart("bar", by_g, f"{col} by {grp_col}", grp_col, col)
        return _resp(answer, f"Statistics for '{col}'.", f"SELECT SUM({col}), AVG({col}), MIN({col}), MAX({col}) FROM `{filename}`;", None, chart)

    if mentioned_cat:
        col = mentioned_cat[0]
        counts = df[col].value_counts()
        lines = [f"- **{k}**: {v:,} ({v/len(df)*100:.1f}%)" for k, v in counts.head(12).items()]
        return _resp(
            f"**`{col}` in `{filename}`** ({df[col].nunique()} unique):\n\n" + "\n".join(lines),
            f"value_counts() for '{col}'.", None, None,
            _make_chart("pie", counts.head(8), f"Distribution of {col}", col, "Count"))

    # ── SMART GENERIC (answers about ANY asking pattern) ──────────────────────
    # If nothing else matched, provide a rich overview + auto-analysis
    answer = f"**`{filename}`** — {len(df):,} rows × {len(df.columns)} columns\n\n"

    # Auto-generate key metrics
    if val_col:
        answer += f"**Key Metric — `{val_col}`:** Total={df[val_col].sum():,.2f}, Avg={df[val_col].mean():,.2f}, Max={df[val_col].max():,.2f}\n\n"

    if grp_col and val_col:
        top3 = df.groupby(grp_col)[val_col].sum().sort_values(ascending=False).head(3)
        answer += f"**Top {grp_col}s:** " + ", ".join([f"{k} ({v:,.0f})" for k, v in top3.items()]) + "\n\n"

    answer += "**Try asking:**\n"
    suggestions = []
    if val_col:
        suggestions.append(f"- *What is the total {val_col}?*")
    if grp_col and val_col:
        suggestions.append(f"- *Which {grp_col} has the highest {val_col}?*")
        suggestions.append(f"- *Compare {val_col} by {grp_col}*")
    if date_col and val_col:
        suggestions.append(f"- *Show {val_col} trend over time*")
    suggestions.append("- *Find anomalies in the data*")
    suggestions.append("- *Summarize the dataset*")
    answer += "\n".join(suggestions[:6])

    chart = None
    if grp_col and val_col:
        by_g = df.groupby(grp_col)[val_col].sum().sort_values(ascending=False).head(8)
        chart = _make_chart("bar", by_g, f"{val_col} by {grp_col}", grp_col, val_col)

    return _resp(answer, "Auto-analysis with key metrics.", f"SELECT * FROM `{filename}` LIMIT 10;",
                 f"import pandas as pd\ndf = pd.read_csv('{filename}')\ndf.describe()", chart)


DASHBOARD_SYSTEM_PROMPT = """You are an expert AI Business Analyst. 
You analyze the provided dataset schemas and summaries to generate a high-level executive business dashboard report.

You MUST respond with a single valid JSON object (no markdown fences, no extra text) with this exact structure:
{
  "executive_summary": "High-level summary of the datasets, their completeness, and their general business significance. Write in professional, engaging markdown.",
  "key_findings": [
    "Key numerical finding 1 (e.g. average, max, counts) with business meaning. Use **bold** for metrics.",
    "Key numerical finding 2...",
    ...
  ],
  "recommendations": [
    "Actionable recommendation 1 based on findings.",
    "Actionable recommendation 2...",
    ...
  ]
}
"""


def query_dashboard_narrative(
    datasets: Dict[str, pd.DataFrame],
    summaries: Dict[str, Any]
) -> Dict[str, Any]:
    context = _build_context(datasets, summaries)
    user_prompt = f"{context}\n=== GENERATE EXECUTIVE DASHBOARD REPORT ===\n"

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    # Validate keys
    def _is_valid_key(key: str) -> bool:
        return bool(key) and len(key) > 20 and "your_" not in key.lower() and "placeholder" not in key.lower()

    if _is_valid_key(gemini_key) and HAS_GEMINI:
        try:
            return _call_dashboard_gemini(gemini_key, user_prompt)
        except Exception as e:
            print(f"[Dashboard Gemini] Failed: {e}")

    if _is_valid_key(groq_key) and HAS_GROQ:
        try:
            print(f"[Dashboard Groq] Attempting model={os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')}")
            return _call_dashboard_groq(groq_key, user_prompt)
        except Exception as e:
            import traceback
            print(f"[Dashboard Groq] Failed: {e}")
            traceback.print_exc()
    
    if _is_valid_key(openai_key) and HAS_OPENAI:
        try:
            return _call_dashboard_openai(openai_key, user_prompt)
        except Exception as e:
            print(f"[Dashboard OpenAI] Failed: {e}")

    print("[Dashboard] Falling back to rule-based dashboard generator.")
    return _dashboard_fallback(datasets, summaries)


def _call_dashboard_gemini(api_key: str, user_prompt: str) -> Dict[str, Any]:
    client = google_genai.Client(api_key=api_key)
    full_prompt = DASHBOARD_SYSTEM_PROMPT + "\n\n" + user_prompt
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
        }
    )
    return _parse_json(response.text)


def _call_dashboard_openai(api_key: str, user_prompt: str) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": DASHBOARD_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    return _parse_json(response.choices[0].message.content)


def _call_dashboard_groq(api_key: str, user_prompt: str) -> Dict[str, Any]:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": DASHBOARD_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return _parse_json(response.choices[0].message.content)


def _dashboard_fallback(datasets: Dict[str, pd.DataFrame], summaries: Dict[str, Any]) -> Dict[str, Any]:
    # Aggregated KPI details
    total_files = len(datasets)
    findings = []
    recommendations = []
    
    # Loop files
    for filename, df in datasets.items():
        summary = summaries.get(filename, {})
        rows = summary.get("rows", 0)
        cols = summary.get("columns", 0)
        missing = summary.get("missing_values", 0)
        
        # Let's find numeric columns
        num_cols = list(df.select_dtypes(include=[np.number]).columns)
        cat_cols = list(df.select_dtypes(include=[object, "category"]).columns)
        
        findings.append(f"Analyzed dataset **{filename}** featuring **{rows:,}** rows and **{cols}** attributes.")
        if missing > 0:
            pct = (missing / (rows * cols)) * 100 if (rows * cols) > 0 else 0
            findings.append(f"Dataset **{filename}** contains **{missing:,}** empty fields ({pct:.1f}% missingness), suggesting some data cleaning operations are needed.")
            recommendations.append(f"Implement a structured standard imputation logic or data entry validation for **{filename}** to resolve the {missing:,} empty records.")
            
        # Select best numerical metric
        best_num = None
        for pat in ["sales", "revenue", "amount", "total", "price", "profit", "value", "score", "rating"]:
            for col in num_cols:
                if pat in col.lower():
                    best_num = col
                    break
            if best_num:
                break
        if not best_num and num_cols:
            best_num = num_cols[0]
            
        if best_num:
            mean_v = df[best_num].mean()
            max_v = df[best_num].max()
            min_v = df[best_num].min()
            findings.append(f"For **{filename}**, the attribute **{best_num}** shows an average of **{mean_v:,.2f}**, ranging between **{min_v:,.2f}** and **{max_v:,.2f}**.")
            
            # Check for negative values
            negatives = (df[best_num] < 0).sum()
            if negatives > 0:
                findings.append(f"Identified **{negatives}** negative values in the key column **{best_num}** mapping to losses or potential data entry anomalies.")
                recommendations.append(f"Audit the **{negatives}** negative values in **{best_num}** to distinguish genuine performance decreases from recording issues.")
            else:
                recommendations.append(f"Track the performance of **{best_num}** closely since it serves as a central indicator of operations in **{filename}**.")
                
        # Top group in categorical
        best_cat = None
        for pat in ["category", "dept", "type", "region", "country", "product", "item", "brand"]:
            for col in cat_cols:
                if pat in col.lower():
                    best_cat = col
                    break
            if best_cat:
                break
        if not best_cat and cat_cols:
            best_cat = cat_cols[0]
            
        if best_cat:
            top_val = df[best_cat].value_counts().index[0]
            top_cnt = df[best_cat].value_counts().values[0]
            pct = (top_cnt / rows) * 100 if rows > 0 else 0
            findings.append(f"The most dominant **{best_cat}** category is **'{top_val}'** representing **{top_cnt:,}** entries ({pct:.1f}% of total).")
            recommendations.append(f"Leverage the popularity of top segment **'{top_val}'** in **{best_cat}** while seeking ways to grow the lower-performing categories.")

    # Defaults
    if not recommendations:
        recommendations = [
            "Conduct routine data validation checks to preserve high quality across all datasets.",
            "Establish recurring automated reports matching these specific analytics insights.",
            "Integrate third-party source variables to cross-correlate performance metrics."
        ]
        
    executive_summary = f"This unified dashboard covers **{total_files} active files** containing a multi-dimensional view of your business records. The structure has been verified with total file counts and quality checks, presenting actionable insights below."
    
    return {
        "executive_summary": executive_summary,
        "key_findings": findings[:5],
        "recommendations": recommendations[:4]
    }
