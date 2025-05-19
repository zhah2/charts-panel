#!/usr/bin/env python3
"""
Re-build the static dashboard.

  $ python build.py
"""

import json, pathlib, re, sys
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse          # Added import for URL parsing

ROOT      = pathlib.Path(__file__).parent.absolute()
CHART_DIR = ROOT / "panel-charts"
XL_FILE   = ROOT / "charts_catalog.xlsx"        # adjust if the name differs
TARGETS_FILE = ROOT / "targets.xlsx"  # Path to the targets file

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

tpl = env.get_template("index_template.html")
out_html = tpl.render(
    charts=json.dumps(chart_meta,    separators=(",", ":")),
    cats  =json.dumps(categories_raw, separators=(",", ":")),
    allocation=json.dumps(allocation_data, separators=(",", ":"))
)
(ROOT / "index.html").write_text(out_html, encoding="utf-8")
print(f"[build] ✅ wrote index.html ({len(chart_meta)} charts, {len(allocation_data)} allocation categories)")
