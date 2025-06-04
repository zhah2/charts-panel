#!/usr/bin/env python3
"""
Charts Panel Dashboard Builder

This script rebuilds the static dashboard by:
1. Reading chart catalog and configuration from Excel files
2. Processing chart metadata and categories
3. Loading allocation targets and asset returns data
4. Generating the final HTML dashboard with Vue.js integration

Usage:
    $ python build.py

Input Files:
    - charts_catalog.xlsx: Chart definitions and metadata
    - targets.xlsx: Portfolio allocation targets (optional)
    - asset_return_history.xlsx: Historical returns data (optional)

Output Files:
    - index.html: Final dashboard HTML file
    - charts.json: Chart metadata (debug)
    - categories.json: Category definitions (debug)
    - returns.json: Asset returns data (debug, if available)
"""

import json, pathlib, re, sys
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse          # For URL parsing in chart location detection
from datetime import datetime              # For datetime handling in data processing

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & FILE PATHS
# ──────────────────────────────────────────────────────────────────────────────

# Define project paths
ROOT         = pathlib.Path(__file__).parent.absolute()
CHART_DIR    = ROOT / "panel-charts"
XL_FILE      = ROOT / "charts_catalog.xlsx"        # Main chart catalog
TARGETS_FILE = ROOT / "targets.xlsx"               # Portfolio allocation targets
RETURNS_FILE = ROOT / "asset_return_history.xlsx"  # Historical returns data

print(f"[build] 🔧 Starting dashboard build process...")
print(f"[build] 📁 Working directory: {ROOT}")

# ──────────────────────────────────────────────────────────────────────────────
# 1) LOAD & NORMALIZE EXCEL SHEETS
# ──────────────────────────────────────────────────────────────────────────────

def tidy_cols(df):
    """
    Normalize DataFrame column names by:
    - Removing leading/trailing whitespace
    - Converting to lowercase  
    - Removing internal whitespace
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with normalized column names
    """
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r"\s+", "", regex=True)
    )
    return df

# Load main chart catalog
print(f"[build] 📖 Reading chart catalog from: {XL_FILE}")
try:
    labels_df = tidy_cols(pd.read_excel(XL_FILE, sheet_name="labels"))
    charts_df = tidy_cols(pd.read_excel(XL_FILE, sheet_name="charts"))
    print(f"[build] ✅ Loaded {len(labels_df)} label definitions and {len(charts_df)} chart records")
except Exception as e:
    sys.exit(f"[build] ❌ Cannot read {XL_FILE}: {e}")

# Validate required columns
if not {"name", "type"}.issubset(labels_df.columns):
    sys.exit("[build] ❌ 'labels' sheet must have columns Name & Type")

if not {"id", "name", "label", "location"}.issubset(charts_df.columns):
    sys.exit("[build] ❌ 'charts' sheet must have columns ID, Name, Label, Location")

print(f"[build] ✅ Schema validation passed")

# ──────────────────────────────────────────────────────────────────────────────
# 2) BUILD CATEGORY STRUCTURE
# ──────────────────────────────────────────────────────────────────────────────

print(f"[build] 🏷️  Building category structure...")

# Create categories from label types (e.g., Asset Class, Strategy, etc.)
categories_raw = (
    labels_df.groupby("type")["name"]
             .apply(list)
             .reset_index()
             .rename(columns={"type": "name", "name": "labels"})
             .to_dict(orient="records")
)

# Add dynamic Source category from chart sources
sources = charts_df["source"].dropna().unique().tolist()
sources = [src.strip() for src in sources if src.strip()]
if sources:
    categories_raw.append({"name": "Source", "labels": sorted(sources)})
    print(f"[build] 📊 Added Source category with {len(sources)} sources")

# Add dynamic Status category from chart statuses
statuses = charts_df["status"].dropna().unique().tolist()
statuses = [status.strip() for status in statuses if status.strip()]
if statuses:
    categories_raw.append({"name": "Status", "labels": sorted(statuses)})
    print(f"[build] 📈 Added Status category with {len(statuses)} statuses")

print(f"[build] ✅ Built {len(categories_raw)} categories")

# ──────────────────────────────────────────────────────────────────────────────
# 3) PROCESS CHART METADATA
# ──────────────────────────────────────────────────────────────────────────────

def kind_and_src(loc: str):
    """
    Determine chart type and source path from location string.
    
    Handles:
    - Remote URLs (http/https) - detects images vs iframes
    - File URIs (file://) 
    - Local relative/absolute paths
    
    Args:
        loc (str): Chart location/path
        
    Returns:
        tuple: (chart_type, source_path)
    """
    loc = str(loc).strip()

    # 1) Remote HTTP/HTTPS resources
    if re.match(r"^https?://", loc):
        ext = pathlib.Path(urlparse(loc).path).suffix.lower()
        # Detect if it's an image or iframe content
        return ("remote_img" if ext in {".png", ".jpg", ".jpeg", ".gif", ".svg"} 
                or "refini.tv" in loc.lower()
                else "remote_iframe", loc)

    # 2) File URI - treat as remote image
    if loc.startswith("file://"):
        return "remote_img", loc

    # 3) Local paths - preserve structure
    src_path = loc if not loc.startswith('/') else loc
    kind = "local_png" if loc.lower().endswith((".png", ".jpg", ".jpeg", ".gif")) else "local_html"
    return kind, src_path

print(f"[build] 🔍 Processing chart metadata...")

chart_meta = []
for _, r in charts_df.iterrows():
    # Parse comma-separated labels
    labels = [lbl.strip() for lbl in str(r["label"]).split(",") if lbl.strip()]
    
    # Determine chart type and source
    kind, src = kind_and_src(r["location"])
    
    # Extract additional metadata
    source = str(r.get("source", "")).strip()
    status = str(r.get("status", "")).strip()
    
    # Combine all labels including source and status for filtering
    all_labels = labels.copy()
    if source:
        all_labels.append(source)
    if status:
        all_labels.append(status)
    
    # Build chart metadata object
    chart_meta.append({
        "id":          str(r["id"]),
        "title":       str(r["name"]),
        "labels":      all_labels,
        "kind":        kind,
        "src":         src,
        "description": str(r.get("description", "")).strip(),
        "status":      status,
        "source":      source,
    })

print(f"[build] ✅ Processed {len(chart_meta)} charts")

# ──────────────────────────────────────────────────────────────────────────────
# 4) EXPORT DEBUG JSON FILES  
# ──────────────────────────────────────────────────────────────────────────────

print(f"[build] 💾 Writing debug JSON files...")

# Export chart metadata and categories for debugging
charts_json_path = ROOT / "charts.json"
categories_json_path = ROOT / "categories.json"

charts_json_path.write_text(json.dumps(chart_meta, indent=2))
categories_json_path.write_text(json.dumps(categories_raw, indent=2))

print(f"[build] ✅ Written: {charts_json_path}")
print(f"[build] ✅ Written: {categories_json_path}")

# ──────────────────────────────────────────────────────────────────────────────
# 5) LOAD ALLOCATION TARGET DATA
# ──────────────────────────────────────────────────────────────────────────────

def load_allocation_targets():
    """
    Load portfolio allocation targets from Excel file.
    
    Processes multiple sheets representing different asset classes:
    - Cross Assets, Equities-Region, Equities-Sector
    - Bonds-Region, Bonds-Sector, FX, Commodities
    
    Returns:
        dict: Nested structure with allocation data by sheet and date
    """
    # Check if targets file exists
    if not TARGETS_FILE.exists():
        print(f"[build] ⚠️  Targets file not found: {TARGETS_FILE}")
        return {}
    
    print(f"[build] 📊 Loading allocation targets from: {TARGETS_FILE}")
    
    try:
        # Define sheets to process
        sheets = [
            "Cross Assets", 
            "Equities-Region", "Equities-Sector",
            "Bonds-Region", "Bonds-Sector", 
            "FX", 
            "Commodities"
        ]
        
        targets_data = {}
        total_records = 0
        
        # Process each sheet
        for sheet in sheets:
            try:
                # Read and standardize data
                df = pd.read_excel(TARGETS_FILE, sheet_name=sheet)
                
                # Ensure first column is Date
                if "Date" not in df.columns[0]:
                    df = df.rename(columns={df.columns[0]: "Date"})
                
                # Convert dates to ISO format for JSON serialization
                if pd.api.types.is_datetime64_any_dtype(df["Date"]):
                    df["Date"] = df["Date"].dt.strftime('%Y-%m-%d')
                
                # Get asset list (all columns except Date)
                assets = [col for col in df.columns if col != "Date"]
                
                # Convert to records format
                data = []
                for _, row in df.iterrows():
                    date = row["Date"]
                    asset_values = []
                    for asset in assets:
                        value = row[asset]
                        # Handle NaN values
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
                
                # Store processed data
                targets_data[sheet] = {
                    "data": data,
                    "assets": assets
                }
                
                total_records += len(data)
                print(f"[build] ✅ Processed sheet '{sheet}': {len(data)} records, {len(assets)} assets")
            
            except Exception as e:
                print(f"[build] ⚠️  Error processing sheet {sheet}: {e}")
        
        print(f"[build] ✅ Loaded allocation targets: {len(targets_data)} sheets, {total_records} total records")
        return targets_data
    
    except Exception as e:
        print(f"[build] ❌ Cannot read targets file: {e}")
        return {}

# Load allocation targets
allocation_data = load_allocation_targets()

# ──────────────────────────────────────────────────────────────────────────────
# 6) LOAD ASSET RETURNS DATA
# ──────────────────────────────────────────────────────────────────────────────

def load_asset_returns():
    """
    Load historical asset returns from Excel file.
    
    Processes two sheets:
    - assets: Main asset return series
    - reference_series: Benchmark/reference return series
    
    Returns:
        dict: Structured data with dates, assets, and pre-calculated statistics
    """
    # Check if returns file exists
    if not RETURNS_FILE.exists():
        print(f"[build] ⚠️  Asset returns file not found: {RETURNS_FILE}")
        return {}
    
    print(f"[build] 📈 Loading asset returns from: {RETURNS_FILE}")
    
    try:
        # Read both sheets
        assets_df = pd.read_excel(RETURNS_FILE, sheet_name="assets")
        reference_df = pd.read_excel(RETURNS_FILE, sheet_name="reference_series")
        
        def process_sheet(df, sheet_name):
            """Process individual sheet data"""
            # Get asset names from headers
            asset_names = df.columns.tolist()
            
            # Skip description row and start from data
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
            
            # Build date index for O(1) lookups
            date_index = {str(date): i for i, date in enumerate(dates)}
            
            # Process asset data
            assets_data = {}
            for asset in asset_names[1:]:  # Skip date column
                asset_values = []
                for val in data_df[asset]:
                    # Handle different value types
                    if pd.isna(val):
                        asset_values.append(None)
                    elif isinstance(val, (pd.Timestamp, datetime)):
                        asset_values.append(None)  # Date values marked as missing
                    else:
                        try:
                            asset_values.append(float(val))
                        except (TypeError, ValueError):
                            asset_values.append(None)
                
                assets_data[asset] = asset_values
            
            # Pre-calculate summary statistics for performance
            summary_stats = {}
            for asset in asset_names[1:]:
                values = [v for v in assets_data[asset] if v is not None]
                if values:
                    summary_stats[asset] = {
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                        "missing_count": len([v for v in assets_data[asset] if v is None])
                    }
            
            print(f"[build] ✅ Processed '{sheet_name}' sheet: {len(dates)} periods, {len(asset_names)-1} assets")
            
            return {
                "dates": dates,
                "assets": assets_data,
                "asset_names": asset_names[1:],
                "date_index": date_index,
                "summary_stats": summary_stats,
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
        
        print(f"[build] ✅ Loaded asset returns: {assets_data['date_range']['count']} periods total")
        return returns_data
    
    except Exception as e:
        print(f"[build] ❌ Cannot read asset returns file: {e}")
        import traceback
        traceback.print_exc()
        return {}

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

# Load asset returns data
print(f"[build] 📊 Processing asset returns data...")
asset_returns = load_asset_returns()

# Export returns data for debugging and external use
if asset_returns:
    returns_json_path = ROOT / "returns.json"
    returns_json_path.write_text(json.dumps(asset_returns, indent=2, cls=DateTimeEncoder))
    asset_count = len(asset_returns.get('assets', {}).get('asset_names', []))
    print(f"[build] ✅ Written: {returns_json_path} ({asset_count} assets)")

# ──────────────────────────────────────────────────────────────────────────────
# 7) CONFIGURE CORS PROXY FOR REMOTE IMAGES
# ──────────────────────────────────────────────────────────────────────────────

# Create CORS proxy configuration for handling remote images (e.g., refini.tv)
cors_config = {
    "enabled": True,
    "primary_proxy": {
        "name": "cloudflare",
        "url": "https://img-cors-proxy.haining-zha.workers.dev",
        "format": "{proxy_url}?url={encoded_url}"
    },
    "fallback_proxy": {
        "name": "allorigins", 
        "url": "https://api.allorigins.win/raw",
        "format": "{proxy_url}?url={encoded_url}"
    }
}

print(f"[build] 🌐 Configured CORS proxy for remote image handling")

# ──────────────────────────────────────────────────────────────────────────────
# 8) RENDER FINAL HTML DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

print(f"[build] 🎨 Rendering HTML dashboard...")

# Configure Jinja2 environment with custom delimiters (to avoid Vue.js conflicts)
env = Environment(loader=FileSystemLoader(str(ROOT)))
env.variable_start_string = "[["  # Use [[ ]] instead of {{ }}
env.variable_end_string   = "]]"  # to avoid Vue.js template conflicts

# Load template
template_path = "index_template_new.html"
print(f"[build] 📄 Using template: {template_path}")
tpl = env.get_template(template_path)

# Render final HTML with all data
output_html_path = ROOT / "index.html"
out_html = tpl.render(
    charts=json.dumps(chart_meta, separators=(",", ":")),
    cats=json.dumps(categories_raw, separators=(",", ":")),
    allocation=json.dumps(allocation_data, separators=(",", ":"), cls=DateTimeEncoder),
    returns=json.dumps(asset_returns, separators=(",", ":"), cls=DateTimeEncoder),
    cors_config=json.dumps(cors_config, separators=(",", ":"))
)

# Write final HTML file
output_html_path.write_text(out_html, encoding="utf-8")

# ──────────────────────────────────────────────────────────────────────────────
# 9) BUILD SUMMARY
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n[build] 🎉 Dashboard build completed successfully!")
print(f"[build] ✅ Output: {output_html_path}")
print(f"[build] 📊 Summary:")
print(f"         • {len(chart_meta)} charts processed")
print(f"         • {len(categories_raw)} categories created")
print(f"         • {len(allocation_data)} allocation datasets loaded")
print(f"         • {'Asset returns loaded' if asset_returns else 'No asset returns data'}")
print(f"[build] 🚀 Ready to serve!")

# ──────────────────────────────────────────────────────────────────────────────
# DEPRECATED: Legacy return data loading function (kept for reference)
# ──────────────────────────────────────────────────────────────────────────────

def load_return_data():
    """
    DEPRECATED: Legacy function for loading return data.
    Replaced by load_asset_returns() for better structure and performance.
    """
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
