import os
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Any, Optional

class DatasetAnalyzer:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.load_all_existing()

    def load_all_existing(self):
        """Loads all CSV files from the upload directory into memory."""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
            return

        for filename in os.listdir(self.upload_dir):
            if filename.lower().endswith(".csv"):
                file_path = os.path.join(self.upload_dir, filename)
                try:
                    df = pd.read_csv(file_path)
                    self.datasets[filename] = df
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

    def load_file(self, file_path: str) -> str:
        """Loads a specific CSV file and saves it in memory with strict validation."""
        filename = os.path.basename(file_path)
        if not os.path.exists(file_path):
            raise ValueError(f"File {filename} does not exist on disk.")
        if os.path.getsize(file_path) == 0:
            raise ValueError(f"File {filename} is completely empty (0 bytes).")
            
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                raise ValueError("The CSV file contains no data rows.")
            if len(df.columns) == 0:
                raise ValueError("The CSV file does not contain any column headers.")
            
            # Check if all column headers are unnamed or empty
            unnamed_cols = [col for col in df.columns if str(col).startswith("Unnamed:")]
            if len(unnamed_cols) == len(df.columns):
                raise ValueError("The CSV file lacks readable column names (headers appear to be missing).")
                
            self.datasets[filename] = df
            return filename
        except pd.errors.EmptyDataError:
            raise ValueError(f"File {filename} contains no data.")
        except pd.errors.ParserError as pe:
            raise ValueError(f"Failed to parse CSV syntax in {filename}: {str(pe)}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"Failed to read CSV file: {str(e)}")

    def delete_file(self, filename: str):
        """Removes dataset from memory and disk."""
        if filename in self.datasets:
            del self.datasets[filename]
        file_path = os.path.join(self.upload_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    def get_all_summaries(self) -> Dict[str, Any]:
        """Gets metadata summary for all loaded datasets."""
        summaries = {}
        for filename, df in self.datasets.items():
            summaries[filename] = self.get_summary(filename)
        return summaries

    def get_summary(self, filename: str) -> Dict[str, Any]:
        """Generates rows, columns, data types, missing statistics for a single DataFrame."""
        if filename not in self.datasets:
            raise ValueError(f"Dataset {filename} not loaded.")

        df = self.datasets[filename]
        rows, cols = df.shape
        missing_total = int(df.isnull().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        missing_by_col = df.isnull().sum().to_dict()
        data_types = {col: str(dtype) for col, dtype in df.dtypes.items()}

        columns_meta = []
        for col in df.columns:
            null_count = int(missing_by_col[col])
            col_type = data_types[col]
            sample_vals = df[col].dropna().head(3).tolist()
            sample_vals = [str(x) for x in sample_vals]
            columns_meta.append({
                "name": col,
                "type": col_type,
                "missing": null_count,
                "samples": sample_vals
            })

        # Generate logical suggested questions
        suggested = []
        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        categorical_cols = list(df.select_dtypes(include=[object, "category"]).columns)
        
        suggested.append(f"Give me a summary of {filename}")
        
        if numeric_cols:
            best_num = numeric_cols[0]
            for pat in ["sales", "revenue", "amount", "total", "price", "profit", "value", "score", "rating"]:
                found = False
                for col in numeric_cols:
                    if pat in col.lower():
                        best_num = col
                        found = True
                        break
                if found:
                    break
            suggested.append(f"What is the average {best_num}?")
            suggested.append(f"Find anomalies in the {best_num} column")
            
            if categorical_cols:
                best_cat = categorical_cols[0]
                for pat in ["category", "dept", "type", "region", "country", "product", "item", "brand", "team", "club"]:
                    found = False
                    for col in categorical_cols:
                        if pat in col.lower():
                            best_cat = col
                            found = True
                            break
                    if found:
                        break
                suggested.append(f"Compare {best_num} by {best_cat}")
                suggested.append(f"What are the top 5 {best_cat} segments by total {best_num}?")
                suggested.append(f"Generate SQL for {best_num} by {best_cat}")
        
        if categorical_cols and len(suggested) < 6:
            suggested.append(f"Show distinct values of {categorical_cols[0]}")
            
        if len(suggested) < 3:
            suggested = [
                f"Summarize the dataset {filename}",
                "Find anomalies in the data",
                "Show details of the columns"
            ]

        return {
            "filename": filename,
            "rows": rows,
            "columns": cols,
            "missing_values": missing_total,
            "duplicate_rows": duplicate_rows,
            "columns_info": columns_meta,
            "suggested_questions": suggested
        }

    def detect_anomalies(self, filename: str) -> List[Dict[str, Any]]:
        """Identifies anomalies such as extreme outliers (IQR), negative values, and high null counts."""
        if filename not in self.datasets:
            raise ValueError(f"Dataset {filename} not loaded.")

        df = self.datasets[filename]
        anomalies = []

        # 1. Missing value counts per column
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                pct = (null_count / len(df)) * 100
                if pct > 10:  # Warn if > 10% values are null
                    anomalies.append({
                        "anomaly_type": "High Percentage of Missing Values",
                        "column": col,
                        "description": f"Column '{col}' has {null_count} missing values ({pct:.1f}%).",
                        "severity": "Warning"
                    })

        # 2. Duplicate rows
        duplicates = int(df.duplicated().sum())
        if duplicates > 0:
            anomalies.append({
                "anomaly_type": "Duplicate Records Detected",
                "column": "All Columns",
                "description": f"The dataset contains {duplicates} exact duplicate rows. These could skew calculations.",
                "severity": "Warning"
            })

        # 3. Numeric check (outliers & negative values)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            non_null_df = df[col].dropna()
            if non_null_df.empty:
                continue

            # Check for negative values in fields like sales, revenue, profit, quantity, price
            col_lower = col.lower()
            negative_count = int((non_null_df < 0).sum())
            if negative_count > 0:
                is_ok = False
                # profit can be negative (financial loss). sales, revenue, quantity, price should not.
                if "profit" in col_lower or "margin" in col_lower or "net_income" in col_lower:
                    is_ok = True  # Negative profit is normal, though still worth highlighting as a performance note

                if not is_ok:
                    anomalies.append({
                        "anomaly_type": "Negative Values in Positive-Only Column",
                        "column": col,
                        "description": f"Column '{col}' has {negative_count} negative values, which is atypical.",
                        "severity": "High"
                    })
                else:
                    anomalies.append({
                        "anomaly_type": "Negative Profit (Loss)",
                        "column": col,
                        "description": f"Column '{col}' contains {negative_count} negative entries representing financial losses.",
                        "severity": "Info"
                    })

            # Check for outliers using IQR method (interquartile range)
            q1 = non_null_df.quantile(0.25)
            q3 = non_null_df.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower_bound = q1 - 2.5 * iqr  # Using 2.5 for more extreme outliers
                upper_bound = q3 + 2.5 * iqr
                outliers = non_null_df[(non_null_df < lower_bound) | (non_null_df > upper_bound)]
                outlier_count = len(outliers)

                if outlier_count > 0:
                    anomalies.append({
                        "anomaly_type": "Extreme Outliers Detected",
                        "column": col,
                        "description": f"Column '{col}' has {outlier_count} values outside normal range (IQR 2.5). Min: {outliers.min()}, Max: {outliers.max()}.",
                        "severity": "Medium"
                    })

        return anomalies

    def generate_insights(self, filename: str) -> List[Dict[str, Any]]:
        """Automatically generates insights based on data values and structures."""
        if filename not in self.datasets:
            raise ValueError(f"Dataset {filename} not loaded.")

        df = self.datasets[filename]
        insights = []

        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        categorical_cols = list(df.select_dtypes(include=[object, "category"]).columns)

        def find_best_col(choices, columns):
            for pattern in choices:
                for c in columns:
                    if re.search(pattern, c.lower()):
                        return c
            return None

        # ── Date parsing ──────────────────────────────────────────────────────
        date_col = find_best_col(["date", "time", "year", "month"], list(df.columns))
        if date_col:
            try:
                date_parsed = pd.to_datetime(df[date_col], errors="coerce")
                if date_parsed.notnull().sum() > len(df) * 0.5:
                    df = df.copy()
                    df["_parsed_date"] = date_parsed
            except:
                pass

        # ── 1. Dataset overview ───────────────────────────────────────────────
        insights.append({
            "title": "Total Records",
            "value": f"{len(df):,}",
            "description": f"{filename} contains {len(df):,} rows and {len(df.columns)} columns.",
            "icon": "rows"
        })

        # ── 2. Primary numeric metric (highest-variance column) ───────────────
        primary_num = None
        if numeric_cols:
            # Prefer well-known metric columns, else pick highest-variance
            primary_num = find_best_col(
                ["score", "goal", "rating", "sales", "revenue", "amount", "total",
                 "price", "profit", "value", "count", "screen", "hour", "minute",
                 "age", "salary", "income", "point", "assist", "pass", "shot"],
                numeric_cols
            ) or max(numeric_cols, key=lambda c: df[c].std() if df[c].std() > 0 else 0)

            col_mean = df[primary_num].mean()
            col_max  = df[primary_num].max()
            col_min  = df[primary_num].min()
            insights.append({
                "title": f"Avg {primary_num.replace('_', ' ').title()}",
                "value": f"{col_mean:,.2f}",
                "description": f"Range: {col_min:,.2f} – {col_max:,.2f} across all records.",
                "icon": "sales"
            })

        # ── 3. Top group by primary numeric ──────────────────────────────────
        primary_cat = find_best_col(
            ["category", "dept", "department", "type", "genre", "position",
             "country", "region", "state", "city", "team", "club", "platform",
             "product", "item", "name", "brand", "segment", "group"],
            categorical_cols
        ) or (categorical_cols[0] if categorical_cols else None)

        if primary_cat and primary_num:
            grouped = df.groupby(primary_cat)[primary_num].mean().sort_values(ascending=False)
            if not grouped.empty:
                top_name = grouped.index[0]
                top_val  = grouped.values[0]
                insights.append({
                    "title": f"Top {primary_cat.replace('_', ' ').title()}",
                    "value": str(top_name),
                    "description": f"Highest avg {primary_num.replace('_', ' ')} at {top_val:,.2f}.",
                    "icon": "category"
                })

        # ── 4. Second numeric column insight ─────────────────────────────────
        second_num_candidates = [c for c in numeric_cols if c != primary_num]
        if second_num_candidates:
            second_num = find_best_col(
                ["assist", "pass", "shot", "goal", "profit", "margin", "gain",
                 "anxiety", "depression", "stress", "sleep", "hour", "minute",
                 "like", "comment", "follower", "engagement", "click", "view"],
                second_num_candidates
            ) or second_num_candidates[0]

            s_mean = df[second_num].mean()
            s_max  = df[second_num].max()
            insights.append({
                "title": f"Avg {second_num.replace('_', ' ').title()}",
                "value": f"{s_mean:,.2f}",
                "description": f"Peak value: {s_max:,.2f}. Reflects overall {second_num.replace('_', ' ')} level.",
                "icon": "product"
            })

        # ── 5. Distribution of top categorical column ─────────────────────────
        if primary_cat:
            dist = df[primary_cat].value_counts()
            top_label = dist.index[0]
            top_count = dist.values[0]
            pct = (top_count / len(df)) * 100
            insights.append({
                "title": f"{primary_cat.replace('_', ' ').title()} Breakdown",
                "value": str(top_label),
                "description": f"Most frequent: '{top_label}' with {top_count:,} records ({pct:.1f}%).",
                "icon": "columns"
            })

        # ── 6. Trend over time ────────────────────────────────────────────────
        if primary_num and "_parsed_date" in df.columns:
            try:
                temp_df = df.copy()
                temp_df["_ym"] = temp_df["_parsed_date"].dt.to_period("M")
                monthly = temp_df.groupby("_ym")[primary_num].mean().sort_index()
                if len(monthly) >= 2:
                    best_m  = str(monthly.idxmax())
                    best_v  = monthly.max()
                    insights.append({
                        "title": f"Peak Month ({primary_num.replace('_', ' ').title()})",
                        "value": best_m,
                        "description": f"Highest avg {primary_num.replace('_', ' ')} of {best_v:,.2f} recorded in {best_m}.",
                        "icon": "trend"
                    })
            except:
                pass

        return insights[:6]

    def suggest_charts(self, filename: str) -> List[Dict[str, Any]]:
        """Propoposes chart formats that fit the dataset structure."""
        if filename not in self.datasets:
            raise ValueError(f"Dataset {filename} not loaded.")

        df = self.datasets[filename]
        charts = []

        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        categorical_cols = list(df.select_dtypes(include=[object, "category"]).columns)

        def find_best_col(choices, columns):
            for pattern in choices:
                for c in columns:
                    if re.search(pattern, c.lower()):
                        return c
            return None

        sales_col = find_best_col(["sales", "revenue", "amount", "total", "price", "profit", "quantity"], numeric_cols)
        cat_col = find_best_col(["category", "dept", "department", "type", "region", "country", "segment", "product", "item"], categorical_cols)
        date_col = find_best_col(["date", "time", "year", "month"], df.columns)

        # 1. Bar Chart suggestion
        if cat_col and sales_col:
            grouped = df.groupby(cat_col)[sales_col].sum().sort_values(ascending=False).head(8)
            chart_data = [{"name": str(k), "value": float(v)} for k, v in grouped.items()]
            charts.append({
                "chart_type": "bar",
                "title": f"{sales_col} by {cat_col}",
                "x_axis": cat_col,
                "y_axis": sales_col,
                "data": chart_data
            })

        # 2. Line Chart suggestion (over date)
        if date_col and sales_col:
            try:
                temp_df = df.copy()
                temp_df["_dt"] = pd.to_datetime(temp_df[date_col], errors="coerce")
                temp_df = temp_df.dropna(subset=["_dt"])
                # Resample by month if plenty of dates, else by date
                temp_df["_dt_str"] = temp_df["_dt"].dt.strftime("%Y-%m-%d")
                if len(temp_df["_dt_str"].unique()) > 15:
                    temp_df["_dt_str"] = temp_df["_dt"].dt.strftime("%Y-%m")

                grouped = temp_df.groupby("_dt_str")[sales_col].sum().sort_index()
                chart_data = [{"name": str(k), "value": float(v)} for k, v in grouped.items()]
                charts.append({
                    "chart_type": "line",
                    "title": f"Trend of {sales_col} Over Time",
                    "x_axis": "Date",
                    "y_axis": sales_col,
                    "data": chart_data
                })
            except Exception as e:
                print("Line chart creation failed:", e)

        # 3. Pie Chart suggestion
        if cat_col and sales_col:
            grouped = df.groupby(cat_col)[sales_col].sum().sort_values(ascending=False).head(5)
            # Add 'Other' category if there are more
            total_sales = df[sales_col].sum()
            grouped_sum = grouped.sum()
            chart_data = [{"name": str(k), "value": float(v)} for k, v in grouped.items()]
            if total_sales > grouped_sum and total_sales > 0:
                chart_data.append({"name": "Other", "value": float(total_sales - grouped_sum)})

            charts.append({
                "chart_type": "pie",
                "title": f"Distribution of {sales_col} by {cat_col}",
                "x_axis": cat_col,
                "y_axis": sales_col,
                "data": chart_data
            })

        # 4. Scatter suggestion if 2 numeric columns
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            # Take a sample of 100 records max for performance
            sample_df = df[[x_col, y_col]].dropna().head(100)
            chart_data = [{"x": float(row[x_col]), "y": float(row[y_col]), "name": f"Record {idx}"} for idx, row in sample_df.iterrows()]
            charts.append({
                "chart_type": "scatter",
                "title": f"{y_col} vs {x_col}",
                "x_axis": x_col,
                "y_axis": y_col,
                "data": chart_data
            })

        return charts
