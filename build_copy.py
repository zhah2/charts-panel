#!/usr/bin/env python3
"""
Re-build the static dashboard.

  $ python build.py
"""

import json, pathlib, re, sys
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse          # Added import for URL parsing
from datetime import datetime  # Added for datetime handling

ROOT      = pathlib.Path(__file__).parent.absolute()
CHART_DIR = ROOT / "panel-charts"
XL_FILE   = ROOT / "charts_catalog.xlsx"        # adjust if the name differs
TARGETS_FILE = ROOT / "targets.xlsx"  # Path to the targets file
RETURNS_FILE = ROOT / "asset_return_history.xlsx"  # Add this new constant

# ──────────────────────────────────────────────────────────────────────────────
# 1)  LOAD & NORMALISE SHEETS
# ──────────────────────────────────────────────────────────────────────────────
def tidy_cols(df):
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r"\s+", "", regex=True)
    )
    return df

try:
    labels_df = tidy_cols(pd.read_excel(XL_FILE, sheet_name="labels"))
    charts_df = tidy_cols(pd.read_excel(XL_FILE, sheet_name="charts"))
except Exception as e:
    sys.exit(f"[build] ❌ cannot read {XL_FILE}: {e}")

if not {"name", "type"}.issubset(labels_df.columns):
    sys.exit("[build] ❌ 'labels' sheet must have columns Name & Type")

if not {"id", "name", "label", "location"}.issubset(charts_df.columns):
    sys.exit("[build] ❌ 'charts' sheet must have columns ID, Name, Label, Location")

# ──────────────────────────────────────────────────────────────────────────────
# 2)  CATEGORY STRUCTURE
# ──────────────────────────────────────────────────────────────────────────────
# Original categories from label types
categories_raw = (
    labels_df.groupby("type")["name"]
             .apply(list)
             .reset_index()
             .rename(columns={"type": "name", "name": "labels"})
             .to_dict(orient="records")
)

# Add Source category
sources = charts_df["source"].dropna().unique().tolist()
sources = [src.strip() for src in sources if src.strip()]
if sources:
    categories_raw.append({"name": "Source", "labels": sorted(sources)})

# Add Status category
statuses = charts_df["status"].dropna().unique().tolist()
statuses = [status.strip() for status in statuses if status.strip()]
if statuses:
    categories_raw.append({"name": "Status", "labels": sorted(statuses)})

# ──────────────────────────────────────────────────────────────────────────────
# 3)  CHART METADATA
# ──────────────────────────────────────────────────────────────────────────────
def kind_and_src(loc: str):
    loc = str(loc).strip()

    # 1) true remote (http / https)
    if re.match(r"^https?://", loc):
        # Handle remote resources as before...
        ext = pathlib.Path(urlparse(loc).path).suffix.lower()
        return ("remote_img" if ext in {".png", ".jpg", ".jpeg",
                                      ".gif", ".svg"} or "refini.tv" in loc.lower()
                else "remote_iframe", loc)

    # 2) remote image on a share – already a file URI
    if loc.startswith("file://"):
        return "remote_img", loc

    # 3) local path - use as-is for relative paths
    # Don't modify the path structure for local resources
    if not loc.startswith('/'):
        # It's already a relative path, use as-is
        src_path = loc
    else:
        # It's an absolute path, keep the leading slash
        src_path = loc
        
    kind = "local_png" if loc.lower().endswith((".png", ".jpg", ".jpeg", ".gif")) else "local_html"
    return kind, src_path

chart_meta = []
for _, r in charts_df.iterrows():
    labels = [lbl.strip() for lbl in str(r["label"]).split(",") if lbl.strip()]
    kind, src = kind_and_src(r["location"])
    
    # Get source and status
    source = str(r.get("source", "")).strip()
    status = str(r.get("status", "")).strip()
    
    # Add source and status to labels if they exist
    all_labels = labels.copy()
    if source:
        all_labels.append(source)
    if status:
        all_labels.append(status)
    
    chart_meta.append({
        "id":    str(r["id"]),
        "title": str(r["name"]),
        "labels": all_labels,  # Use combined labels including source and status
        "kind":  kind,
        "src":   src,
        "description": str(r.get("description", "")).strip(),
        "status":      status,
        "source":      source,
    })

# ──────────────────────────────────────────────────────────────────────────────
# 4)  OPTIONAL: WRITE DEBUG JSON
# ──────────────────────────────────────────────────────────────────────────────
(ROOT / "charts.json"    ).write_text(json.dumps(chart_meta,    indent=2))
(ROOT / "categories.json").write_text(json.dumps(categories_raw, indent=2))

# ──────────────────────────────────────────────────────────────────────────────
# LOAD ALLOCATION TARGET DATA
# ──────────────────────────────────────────────────────────────────────────────
def load_allocation_targets():
    # Check if targets file exists
    if not TARGETS_FILE.exists():
        print(f"[build] ⚠️ targets file not found: {TARGETS_FILE}")
        return {}
    
    try:
        # Define the sheets to process
        sheets = [
            "Cross Assets", 
            "Equities-Region", "Equities-Sector",
            "Bonds-Region", "Bonds-Sector", 
            "FX", 
            "Commodities"
        ]
        
        targets_data = {}
        
        # Process each sheet
        for sheet in sheets:
            try:
                # Read data, standardize column names
                df = pd.read_excel(TARGETS_FILE, sheet_name=sheet)
                
                # Ensure first column is Date
                if not "Date" in df.columns[0]:
                    df = df.rename(columns={df.columns[0]: "Date"})
                
                # Convert dates to ISO format strings for JSON serialization
                if pd.api.types.is_datetime64_any_dtype(df["Date"]):
                    df["Date"] = df["Date"].dt.strftime('%Y-%m-%d')
                
                # Get list of assets (all columns except Date)
                assets = [col for col in df.columns if col != "Date"]
                
                # Convert to list of records for JSON
                data = []
                for _, row in df.iterrows():
                    date = row["Date"]
                    asset_values = []
                    for asset in assets:
                        value = row[asset]
                        # Ensure numeric values (handle NaN)
                        if pd.isna(value):
                            value = 0
                        asset_values.append({
                            "name": asset,
                            "value": float(value)
                        })
                    data.append({
                        "date": date,
                        "assets": asset_values
                    })
                
                # Store data for this sheet
                targets_data[sheet] = {
                    "data": data,
                    "assets": assets
                }
            
            except Exception as e:
                print(f"[build] ⚠️ error processing sheet {sheet}: {e}")
        
        return targets_data
    
    except Exception as e:
        print(f"[build] ⚠️ cannot read targets file: {e}")
        return {}

# Load allocation targets
allocation_data = load_allocation_targets()

# ──────────────────────────────────────────────────────────────────────────────
# 5)  RENDER index.html (switch Jinja delimiters)
# ──────────────────────────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader(str(ROOT)))
env.variable_start_string = "[["
env.variable_end_string   = "]]"

tpl = env.get_template("index_template_new.html")

# Add this function to load asset returns
def load_asset_returns():
    # Check if returns file exists
    if not RETURNS_FILE.exists():
        print(f"[build] ⚠️ asset returns file not found: {RETURNS_FILE}")
        return {}
    
    try:
        # Read both tabs from the Excel file
        assets_df = pd.read_excel(RETURNS_FILE, sheet_name="assets")
        reference_df = pd.read_excel(RETURNS_FILE, sheet_name="reference_series")
        
        def process_sheet(df, sheet_name):
            # Get asset names from first row (headers)
            asset_names = df.columns.tolist()
            
            # Skip the second row (detailed descriptions) and start from row 3
            data_df = df.iloc[1:].reset_index(drop=True)
            
            # Convert dates to ISO format strings for JSON serialization
            date_col = asset_names[0]  # First column is date
            if pd.api.types.is_datetime64_any_dtype(data_df[date_col]):
                data_df[date_col] = data_df[date_col].dt.strftime('%Y-%m-%d')
            
            # Extract dates and ensure they are all strings
            dates = []
            for date_val in data_df[date_col].tolist():
                if isinstance(date_val, (pd.Timestamp, datetime)):
                    dates.append(date_val.strftime('%Y-%m-%d'))
                else:
                    dates.append(str(date_val))
            
            # Prepare assets data with JSON-serializable values and create date index
            assets_data = {}
            date_index = {}  # For faster date lookups
            
            for i, date in enumerate(dates):
                date_index[str(date)] = i  # Ensure key is string
            
            for asset in asset_names[1:]:  # Skip date column
                # Convert any datetime values to strings and ensure all values are JSON serializable
                asset_values = []
                for val in data_df[asset]:
                    # Handle different types of values
                    if pd.isna(val):
                        asset_values.append(None)  # Preserve missing data as null in JSON
                    elif isinstance(val, (pd.Timestamp, datetime)):
                        asset_values.append(None)  # Date values marked as missing for returns
                    else:
                        # Convert to float for numerical values
                        try:
                            asset_values.append(float(val))
                        except (TypeError, ValueError):
                            # If conversion fails, mark as missing
                            asset_values.append(None)
                
                assets_data[asset] = asset_values
            
            # Pre-calculate some common statistics for performance
            summary_stats = {}
            for asset in asset_names[1:]:
                # Only include non-null values for statistics
                values = [v for v in assets_data[asset] if v is not None]
                if values:
                    summary_stats[asset] = {
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                        "missing_count": len([v for v in assets_data[asset] if v is None])
                    }
            
            return {
                "dates": dates,
                "assets": assets_data,
                "asset_names": asset_names[1:],  # Asset names without date column
                "date_index": date_index,  # For O(1) date lookups
                "summary_stats": summary_stats,  # Pre-calculated statistics
                "date_range": {
                    "start": dates[0] if dates else None,
                    "end": dates[-1] if dates else None,
                    "count": len(dates)
                }
            }
        
        # Process both sheets
        assets_data = process_sheet(assets_df, "assets")
        reference_data = process_sheet(reference_df, "reference_series")
        
        # Combine into final structure
        returns_data = {
            "assets": assets_data,
            "reference": reference_data
        }
        
        return returns_data
    
    except Exception as e:
        print(f"[build] ⚠️ cannot read asset returns file: {e}")
        import traceback
        traceback.print_exc()  # Print the full traceback for debugging
        return {}

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

# Load asset returns data
asset_returns = load_asset_returns()

# Write returns data to separate JSON file for debugging and external use
if asset_returns:
    (ROOT / "returns.json").write_text(json.dumps(asset_returns, indent=2, cls=DateTimeEncoder))
    print(f"[build] ✅ wrote returns.json with {len(asset_returns.get('assets', {}).get('asset_names', []))} assets")

out_html = tpl.render(
    charts=json.dumps(chart_meta,    separators=(",", ":")),
    cats  =json.dumps(categories_raw, separators=(",", ":")),
    allocation=json.dumps(allocation_data, separators=(",", ":"), cls=DateTimeEncoder),
    returns=json.dumps(asset_returns, separators=(",", ":"), cls=DateTimeEncoder)
)
(ROOT / "index.html").write_text(out_html, encoding="utf-8")
print(f"[build] ✅ wrote index.html ({len(chart_meta)} charts, {len(allocation_data)} allocation categories)")

# ──────────────────────────────────────────────────────────────────────────────
# LOAD RETURN DATA
# ──────────────────────────────────────────────────────────────────────────────
def load_return_data():
    # Read from a CSV/Excel file containing historical returns
    returns_df = pd.read_excel(RETURNS_FILE, sheet_name="returns")
    
    # Process into proper format
    returns_data = {
        "dates": returns_df["Date"].dt.strftime('%Y-%m-%d').tolist(),
        "assets": {
            asset: returns_df[asset].tolist() 
            for asset in returns_df.columns if asset != "Date"
        },
        # Add reference portfolios
        "benchmarks": {
            "All_Cash": returns_df["Cash"].tolist(),
            "All_Bonds": returns_df["US Bond"].tolist(),
            "All_Stocks": returns_df["MSCI World"].tolist(),
            "Inflation": returns_df["Inflation"].tolist() if "Inflation" in returns_df.columns else [0.02/12] * len(returns_df)
        }
    }
    return returns_data
