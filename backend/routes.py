import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from analyzer import DatasetAnalyzer
from utils import query_llm, query_dashboard_narrative

router = APIRouter()
# Keep uploaded files beside the backend regardless of the directory used to
# start Uvicorn.  This makes the API behave the same from the project root,
# the backend folder, or a deployment service.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
upload_dir = os.path.join(BASE_DIR, "uploads")
analyzer = DatasetAnalyzer(upload_dir)

# Global in-memory chat history representing the single session
SESSION_CHAT_HISTORY: List[Dict[str, str]] = []

class AskRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None
    filename: Optional[str] = None

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Uploads single or multiple CSV files to the server and refreshes the analyzer schema."""
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    results = []
    for file in files:
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file.filename}. Only CSV files are allowed."
            )

        # UploadFile.filename is user-controlled; retain only its basename.
        filename = os.path.basename(file.filename)
        if not filename:
            raise HTTPException(status_code=400, detail="A CSV filename is required.")
        file_path = os.path.join(upload_dir, filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Load file in analyzer
            analyzer.load_file(file_path)
            summary = analyzer.get_summary(filename)
            results.append({
                "filename": filename,
                "rows": summary["rows"],
                "columns": summary["columns"],
                "status": "Uploaded Successfully"
            })
        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to upload or parse {file.filename}: {str(e)}"
            )

    return {"uploaded_files": results}


@router.delete("/files/{filename}")
async def delete_uploaded_file(filename: str):
    """Deletes one uploaded CSV and its in-memory analysis state."""
    filename = os.path.basename(filename)
    if filename not in analyzer.datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    analyzer.delete_file(filename)
    return {"message": f"Deleted {filename}", "filename": filename}

@router.get("/summary")
async def get_summary(filename: Optional[str] = None):
    """Retrieves columns info, row/column counts, and missing/duplicate stats."""
    if not analyzer.datasets:
        return {"error": "No CSV files uploaded yet. Please upload a CSV first."}

    if filename:
        if filename not in analyzer.datasets:
            raise HTTPException(status_code=404, detail="Dataset not found or loaded")
        return analyzer.get_summary(filename)
    
    return analyzer.get_all_summaries()

@router.get("/insights")
async def get_insights(filename: Optional[str] = None):
    """Retrieves automatically extracted data insights."""
    if not analyzer.datasets:
        return []

    if filename:
        if filename not in analyzer.datasets:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return analyzer.generate_insights(filename)
    
    # Return aggregated logs or first dataset
    first_fn = list(analyzer.datasets.keys())[0]
    return analyzer.generate_insights(first_fn)

@router.get("/anomalies")
async def get_anomalies(filename: Optional[str] = None):
    """Performs statistical checks for outliers and anomalies."""
    if not analyzer.datasets:
        return []

    if filename:
        if filename not in analyzer.datasets:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return analyzer.detect_anomalies(filename)
    
    first_fn = list(analyzer.datasets.keys())[0]
    return analyzer.detect_anomalies(first_fn)

@router.get("/charts")
async def get_charts(filename: Optional[str] = None):
    """Suggests clean visualizations representing numeric distributions or categorical groupings."""
    if not analyzer.datasets:
        return []

    if filename:
        if filename not in analyzer.datasets:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return analyzer.suggest_charts(filename)
    
    first_fn = list(analyzer.datasets.keys())[0]
    return analyzer.suggest_charts(first_fn)

@router.post("/ask")
async def ask_question(request: AskRequest):
    """Evaluates question using LLMs or Python rules engine."""
    if not analyzer.datasets:
        raise HTTPException(
            status_code=400, 
            detail="No CSV file loaded. Please upload a CSV first."
        )

    # Use user provided history if given, else fall back to session store
    history = request.chat_history if request.chat_history is not None else SESSION_CHAT_HISTORY

    # ── Scope to selected dataset ─────────────────────────────────────────────
    # If the frontend passes a filename, restrict context to that dataset only
    # so the LLM answers specifically about the file the user is viewing.
    if request.filename:
        if request.filename not in analyzer.datasets:
            raise HTTPException(status_code=404, detail="Selected dataset not found")
        active_datasets = {request.filename: analyzer.datasets[request.filename]}
    else:
        # Preserve backwards compatibility for clients that do not yet send a
        # selected filename, while the UI always sends one after selection.
        active_datasets = analyzer.datasets

    try:
        summaries = {fn: analyzer.get_summary(fn) for fn in active_datasets}
        response_data = query_llm(request.query, active_datasets, summaries, history)
        
        # Append exchange to global store
        if request.chat_history is None:
            SESSION_CHAT_HISTORY.append({"role": "user", "content": request.query})
            SESSION_CHAT_HISTORY.append({"role": "assistant", "content": response_data.get("answer", "")})
            
        return response_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while analyzing the dataset: {str(e)}"
        )

@router.post("/clear")
async def clear_session():
    """Clears uploaded datasets and conversation history."""
    global SESSION_CHAT_HISTORY
    SESSION_CHAT_HISTORY = []
    
    # Delete uploaded files
    filenames = list(analyzer.datasets.keys())
    for fn in filenames:
        analyzer.delete_file(fn)
        
    return {"message": "Session and uploads cleared successfully."}


@router.get("/dashboard-data")
async def get_dashboard_data(filename: Optional[str] = None):
    """Gathers summaries, insights, charts, anomalies, and AI executive narrative for dashboard."""
    if not analyzer.datasets:
        return {
            "error": "No CSV files uploaded yet. Please upload a CSV first."
        }
    
    if filename:
        if filename not in analyzer.datasets:
            raise HTTPException(status_code=404, detail="Dataset not found")
        active_datasets = {filename: analyzer.datasets[filename]}
    else:
        active_datasets = analyzer.datasets

    summaries = {fn: analyzer.get_summary(fn) for fn in active_datasets}
    
    # Gather insights, charts, anomalies for each dataset
    all_insights = []
    all_charts = []
    all_anomalies = []
    
    for filename in active_datasets:
        try:
            all_insights.extend(analyzer.generate_insights(filename))
        except Exception:
            pass
        try:
            all_charts.extend(analyzer.suggest_charts(filename))
        except Exception:
            pass
        try:
            all_anomalies.extend(analyzer.detect_anomalies(filename))
        except Exception:
            pass
            
    try:
        narrative = query_dashboard_narrative(active_datasets, summaries)
    except Exception as e:
        narrative = {
            "executive_summary": "Failed to generate AI narrative: " + str(e),
            "key_findings": ["Error generating narrative findings."],
            "recommendations": ["Ensure API access is working or check network logs."]
        }
        
    return {
        "summaries": summaries,
        "insights": all_insights,
        "charts": all_charts,
        "anomalies": all_anomalies,
        "narrative": narrative
    }


@router.get("/columns")
async def get_columns(filename: Optional[str] = None):
    """Returns column names and types for all or a specific dataset."""
    if not analyzer.datasets:
        return {"error": "No datasets loaded."}

    if filename and filename not in analyzer.datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    target = filename or list(analyzer.datasets.keys())[0]
    df = analyzer.datasets[target]

    import numpy as np
    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
    all_cols = list(df.columns)

    return {
        "filename": target,
        "all_columns": all_cols,
        "numeric_columns": numeric_cols,
        "categorical_columns": [c for c in all_cols if c not in numeric_cols],
    }


class BuildChartRequest(BaseModel):
    filename: Optional[str] = None
    x_col: str
    y_col: str
    chart_type: str  # "bar" | "line" | "pie" | "scatter"
    aggregation: str = "sum"  # "sum" | "mean" | "count" | "none"


@router.post("/build-chart")
async def build_chart(req: BuildChartRequest):
    """Generates custom chart data based on user-selected columns, chart type, and aggregation."""
    import numpy as np

    if not analyzer.datasets:
        raise HTTPException(status_code=400, detail="No dataset loaded. Please upload a CSV first.")

    if req.filename and req.filename not in analyzer.datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    filename = req.filename or list(analyzer.datasets.keys())[0]
    df = analyzer.datasets[filename]

    if req.x_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.x_col}' not found in dataset.")
    if req.y_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.y_col}' not found in dataset.")

    chart_data = []

    try:
        if req.chart_type == "scatter" or req.aggregation == "none":
            # Scatter: raw x/y pairs, sample up to 200 rows
            sample = df[[req.x_col, req.y_col]].dropna().head(200)
            chart_data = [{"x": float(row[req.x_col]), "y": float(row[req.y_col]), "name": f"#{i}"} 
                          for i, (_, row) in enumerate(sample.iterrows())]
        else:
            # Grouped aggregation
            agg_func = {"sum": "sum", "mean": "mean", "count": "count"}.get(req.aggregation, "sum")
            grouped = df.groupby(req.x_col)[req.y_col].agg(agg_func).sort_values(ascending=False)
            chart_data = [{"name": str(k), "value": round(float(v), 4)} for k, v in grouped.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build chart: {str(e)}")

    return {
        "filename": filename,
        "chart_type": req.chart_type,
        "title": f"{req.aggregation.capitalize()} of {req.y_col} by {req.x_col}",
        "x_axis": req.x_col,
        "y_axis": req.y_col,
        "data": chart_data
    }
