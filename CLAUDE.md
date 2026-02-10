# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **A-share (Chinese stock market) consecutive limit-up trading analysis system** that collects historical stock market data, processes it, and presents it through an interactive web interface. The system is designed for analyzing limit-up (涨停) patterns and visualizing them in a "ladder" format.

**Core workflow:**
1. Fetch historical data from Zhitu API
2. Validate data completeness
3. Transform JSON data into JavaScript format
4. View results in browser via `ladder_fixed.html`

## Common Commands

### Data Acquisition
```bash
# Fetch last 60 days of data (default)
python fetch_history_data.py

# Fetch specific number of days
python fetch_history_data.py --days 30

# Fetch date range
python fetch_history_data.py --start 2024-01-01 --end 2024-01-31

# Fetch single date
python fetch_history_data.py --date 2024-01-15
```

### Data Quality Assurance
```bash
# Check all data and interactively refetch incomplete entries
python check_and_refetch.py

# Dry-run (check only, no refetch)
python check_and_refetch.py --check-only

# Check specific date
python check_and_refetch.py --date 2024-01-15
```

### Build/Publish
```bash
# Transform data into JavaScript format for web viewing
python generate_ladder_data.py
# Outputs: ladder_data.js (loaded by ladder_fixed.html)
```

### View Results
```bash# Start local server (optional but recommended)
python -m http.server 8000
# Then open: http://localhost:8000/ladder_fixed.html

# Or open ladder_fixed.html directly in browser
```

## High-Level Architecture

### File Structure
```
lbgpfx/
├── fetch_history_data.py     # Zhitu API client for historical pools
├── check_and_refetch.py      # Data validation and auto-refetch
├── generate_ladder_data.py   # JSON → JavaScript transformer
├── data_fetcher.py           # Core data fetcher (AKShare integration)
├── config.py                 # System configuration and weights
├── ladder_fixed.html         # Interactive web visualization
├── ladder_data.js            # Auto-generated data file (gitignored but tracked)
├── data/
│   ├── history/
│   │   ├── limit_up/         # Per-date JSON files
│   │   ├── limit_down/
│   │   └── explode/
│   └── today/               # Current day data (optional)
└── README.md                # Original project description (outdated)
```

### Data Flow
```
Zhitu API (zhituapi.com)
    ↓ (fetch_history_data.py)
JSON files in data/history/{pool_type}/{date}.json
    ↓ (check_and_refetch.py)
Validation completeness check
    ↓ (generate_ladder_data.py)
Merged JavaScript: ladder_data.js
    ↓ (ladder_fixed.html)
Interactive ladder visualization in browser
```

### Key Components

**fetch_history_data.py** - Zhitu API Client
- `ZhituAPIFetcher` class handles all API calls
- Three pool types: limit-up (ztgc), limit-down (dtgc), explode (zbgc)
- Generates trading day calendar (excludes weekends)
- 0.2s interval between requests to avoid rate limits
- Token hardcoded (consider moving to config)

**check_and_refetch.py** - Quality Control
- Scans all dates in `data/history/`
- Validates each date has all 3 pools with non-zero counts
- Interactive refetch capability with --check-only dry-run
- Command-line args: `--date`, `--check-only`, `--dir`

**generate_ladder_data.py** - Data Transformer
- Reads all JSON files from `data/history/` and `data/today/`
- Merges by date into single JavaScript object
- Exports with helper functions: `getDateList()`, `getDataByDate()`, `getLimitUpData()`, etc.
- Used by `ladder_fixed.html` for client-side rendering

**ladder_fixed.html** - Web Interface
- Standalone HTML with embedded CSS/JS
- Loads `ladder_data.js` dynamically
- Features: date selector, navigation, market summary bar, stock cards grid
- Dark gradient theme, responsive layout
- Displays stocks grouped by consecutive limit-up days ("tiers")
- Shows: price, % change, turnover, first/last limit time, explode flag, etc.

**data_fetcher.py** - AKShare Integration (library)
- `DataFetcher` class provides mock and real data fetching
- Supports `use_mock=True` for synthetic data generation
- Not directly used by current workflow but provides alternative data source

**config.py** - Configuration
- Scoring weights and thresholds (for buy signals in original design)
- Red flags, position sizing, stop-loss settings
- Not actively used in current simplified workflow

### Important Notes

- **README.md is outdated**: Describes features (trading simulation, buy signals, web app) that are not present in current codebase. Current system is data-only visualization.
- **ladder_data.js is tracked** despite `.gitignore` having `*.js` - this is intentional as it's the build output loaded by HTML.
- **API token hardcoded** in `fetch_history_data.py` line 17 - security risk, should move to environment variable.
- **No build system**: Simple Python scripts, no npm/complex dependencies.
- **No unit tests**: Manual validation only via `check_and_refetch.py`.
- **Large JS file**: `ladder_data.js` can be several MB (5.9MB for ~4 months). Consider compression for production.

### Recent Bug Fix

**Time display issue** in `ladder_fixed.html` (2026-02-10):
- `fmtTime()` assumed 6-digit numeric input (e.g., "092502")
- Data actually contains colon-separated format (e.g., "09:25:02")
- Fixed by adding check for existing colon before formatting.

## Development Workflow

1. **Add new data**: `python fetch_history_data.py --days N`
2. **Validate**: `python check_and_refetch.py` (fix any gaps)
3. **Build**: `python generate_ladder_data.py`
4. **View**: Open `ladder_fixed.html` in browser

To modify scoring logic or rules: edit `config.py`.
To modify data source: edit `fetch_history_data.py`.
To modify web UI: edit `ladder_fixed.html`.

## Dependencies

From `requirements.txt`:
- `akshare>=1.11.0` - Primary A-share data source (East Money)
- `pandas>=2.0.0`, `numpy>=1.24.0` - Data processing
- `requests>=2.31.0` - HTTP for Zhitu API
- `python-dateutil>=2.8.2` - Date parsing
- `Flask`, `plotly` - Mentioned but not actively used

Install: `pip install -r requirements.txt`

## External APIs

- **Zhitu API** (`https://api.zhituapi.com`) - Historical pool data
  - Requires token: `BA43E6E1-A30D-4FEA-BD23-7B2376FD6114`
  - Endpoints: `/hs/pool/ztgc/{date}`, `/hs/pool/dtgc/{date}`, `/hs/pool/zbgc/{date}`
- **AKShare** - Real-time data source (commented out/fallback)

## Data Schema

Field names in JSON (Chinese):
- `dm` - Stock code
- `mc` - Stock name
- `p` - Price
- `zf` - Change percentage
- `cje` - Trading volume (in RMB)
- `lt` - Circulating market cap
- `hs` - Turnover rate %
- `lbc` - Consecutive limit-up days
- `fbt` - First limit-up time (HH:MM:SS)
- `lbt` - Last limit-up time (HH:MM:SS)
- `zj` - Seal amount (封板额)
- `zbc` - Explode count (炸板)
- `hy` - Industry sector
- `tj` - Statistics tag
