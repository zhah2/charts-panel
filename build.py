#!/usr/bin/env python3
"""
Re-build the static dashboard.

  $ python build.py
"""

import json, pathlib, re, sys
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse, quote          # Added import for URL parsing
from datetime import datetime  # Added for datetime handling
import base64  # For base64 encoding
import os  # For file operations

# Import configuration
try:
    from config import CLOUDFLARE_PROXY_URL, USE_CLOUDFLARE_PROXY
except ImportError:
    # Fallback if config.py doesn't exist
    CLOUDFLARE_PROXY_URL = ""
    USE_CLOUDFLARE_PROXY = False
    print("[build] ⚠️ config.py not found, using default settings")

ROOT      = pathlib.Path(__file__).parent.absolute()
CHART_DIR = ROOT / "panel-charts"
XL_FILE   = ROOT / "charts_catalog.xlsx"        # adjust if the name differs
TARGETS_FILE = ROOT / "targets.xlsx"  # Path to the targets file
RETURNS_FILE = ROOT / "asset_return_history.xlsx"  # Add this new constant

# CORS Proxy Configuration
ALLORIGINS_PROXY_BASE = "https://api.allorigins.win/raw?url="
DEFAULT_CLOUDFLARE_PROXY = "https://img-cors-proxy.haining-zha.workers.dev"

# Use configured proxy or fallback to default
ACTIVE_CLOUDFLARE_PROXY = CLOUDFLARE_PROXY_URL if CLOUDFLARE_PROXY_URL else DEFAULT_CLOUDFLARE_PROXY

# Print configuration status
if USE_CLOUDFLARE_PROXY:
    print(f"[build] 🌐 Using Cloudflare Workers proxy as primary: {ACTIVE_CLOUDFLARE_PROXY}")
    print(f"[build] 🌐 Using AllOrigins as fallback proxy: {ALLORIGINS_PROXY_BASE}")
else:
    print(f"[build] 🔄 CORS proxy available but disabled in config")
    print(f"[build] 📝 Charts will use original URLs (may have CORS issues)")

# ──────────────────────────────────────────────────────────────────────────────
# CORS PROXY HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def create_proxy_urls(original_url):
    """
    Create proxy URLs for Cloudflare Workers and AllOrigins.
    
    Args:
        original_url (str): The original image URL
    
    Returns:
        dict: Dictionary with proxy URLs and metadata
    """
    proxy_urls = {
        'original': original_url,
        'cloudflare': f"{ACTIVE_CLOUDFLARE_PROXY}?url={quote(original_url)}",
        'allorigins': f"{ALLORIGINS_PROXY_BASE}{quote(original_url)}",
        'proxy_enabled': USE_CLOUDFLARE_PROXY
    }
    
    return proxy_urls

def process_chart_sources(charts_data):
    """
    Process chart data and add CORS proxy URLs for remote images.
    """
    processed_charts = []
    refinitiv_found = 0
    refinitiv_processed = 0
    
    for chart in charts_data:
        processed_chart = chart.copy()
        
        # Check if this is a remote image that needs proxy configuration
        if chart['kind'] == 'remote_img':
            original_src = chart['src']
            
            # Check if it's a Refinitiv URL or other remote image
            if any(domain in original_src.lower() for domain in ['refini.tv', 'refinitiv.com']):
                refinitiv_found += 1
                
                # Add proxy configuration
                proxy_urls = create_proxy_urls(original_src)
                
                # Update chart with proxy information
                processed_chart.update({
                    'original_src': original_src,
                    'proxy_urls': proxy_urls,
                    'cors_proxy_enabled': USE_CLOUDFLARE_PROXY,
                    'primary_proxy': 'cloudflare',
                    'fallback_proxy': 'allorigins'
                })
                
                # If proxy is enabled, use the proxy URL as the main src
                if USE_CLOUDFLARE_PROXY:
                    processed_chart['src'] = proxy_urls['cloudflare']
                    processed_chart['proxy_type'] = 'cloudflare'
                
                refinitiv_processed += 1
        
        processed_charts.append(processed_chart)
    
    # Print summary
    if refinitiv_found > 0:
        if USE_CLOUDFLARE_PROXY:
            print(f"[build] ✅ Configured {refinitiv_found} Refinitiv images with CORS proxy support")
            print(f"[build] 🎯 Primary: Cloudflare Workers, Fallback: AllOrigins")
        else:
            print(f"[build] ⚠️ Found {refinitiv_found} Refinitiv images but CORS proxy disabled")
            print(f"[build] 💡 Enable with: USE_CLOUDFLARE_PROXY = True in config.py")
    else:
        print(f"[build] ℹ️ No Refinitiv images found to process")
    
    return processed_charts

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
# 4)  PROCESS REMOTE IMAGES WITH CORS PROXY SUPPORT
# ──────────────────────────────────────────────────────────────────────────────
print(f"[build] Processing {len(chart_meta)} charts for CORS proxy configuration...")
chart_meta = process_chart_sources(chart_meta)

# ──────────────────────────────────────────────────────────────────────────────
# 5)  OPTIONAL: WRITE DEBUG JSON
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
# 6)  RENDER index.html (switch Jinja delimiters)
# ──────────────────────────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader(str(ROOT)))
env.variable_start_string = "[["
env.variable_end_string   = "]]"

# Specify the template to use
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

# Create CORS proxy configuration for the frontend
cors_config = {
    "enabled": USE_CLOUDFLARE_PROXY,
    "primary_proxy": {
        "name": "cloudflare",
        "url": ACTIVE_CLOUDFLARE_PROXY,
        "format": "{proxy_url}?url={encoded_url}"
    },
    "fallback_proxy": {
        "name": "allorigins", 
        "url": ALLORIGINS_PROXY_BASE.rstrip('='),
        "format": "{proxy_url}={encoded_url}"
    }
}

out_html = tpl.render(
    charts=json.dumps(chart_meta,    separators=(",", ":")),
    cats  =json.dumps(categories_raw, separators=(",", ":")),
    allocation=json.dumps(allocation_data, separators=(",", ":"), cls=DateTimeEncoder),
    returns=json.dumps(asset_returns, separators=(",", ":"), cls=DateTimeEncoder),
    cors_config=json.dumps(cors_config, separators=(",", ":"))
)
(ROOT / "index.html").write_text(out_html, encoding="utf-8")

# Final summary
charts_with_proxy = len([c for c in chart_meta if c.get('cors_proxy_enabled')])
proxy_status = "enabled" if USE_CLOUDFLARE_PROXY else "available but disabled"

print(f"[build] ✅ wrote index.html ({len(chart_meta)} charts, {len(allocation_data)} allocation categories)")
print(f"[build] 🌐 CORS proxy {proxy_status}, {charts_with_proxy} charts configured with proxy support")

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
