# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **A-share (Chinese stock market) consecutive limit-up trading analysis system** that collects historical stock market data, processes it, and presents it through an interactive web visualization ("ladder" format). The system analyzes stocks that hit their daily limit-up (涨停) consecutively.

**Core workflow:**
1. Fetch historical limit-up/down/explode data from Zhitu API
2. Validate data completeness and retry failed dates
3. Transform JSON data into JavaScript format
4. View results in browser via `ladder.html`

**Note:** K-line chart functionality was previously implemented but has been removed. Current system focuses solely on the ladder visualization.

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

### Build Data for Web Viewing
```bash
# Transform JSON data into JavaScript format
python generate_ladder_data.py
# Outputs: ladder_data.js (loaded by ladder.html)
```

### View Results
```bash
# Option 1: Simple HTTP server (recommended)
python -m http.server 8000
# Then open: http://localhost:8000/ladder.html

# Option 2: Open ladder.html directly in browser (may have limitations)
# ⚠️ Some browsers restrict file:// protocol for JavaScript modules
```

### Skip Already-Checked Dates
If you have dates that are known to have missing data (e.g., limit-down API returns 404), you can manually edit:
- `data/.checked_dates.json` - JSON file mapping dates to skip with reasons

## High-Level Architecture

### File Structure (Current)
```
lbgpfx/
├── fetch_history_data.py     # Zhitu API client (multi-token support)
├── check_and_refetch.py      # Data validation + smart skip for failed dates
├── generate_ladder_data.py   # JSON → JavaScript transformer
├── data_fetcher.py           # AKShare integration library (fallback data source)
├── config.py                 # Configuration (scoring weights - not actively used)
├── ladder.html               # Main web interface (single-page app)
├── ladder_data.js            # Auto-generated data file (build output)
├── requirements.txt          # Python dependencies
├── data/
│   ├── history/
│   │   ├── limit_up/         # Per-date JSON: 涨停股池
│   │   ├── limit_down/       # Per-date JSON: 跌停股池
│   │   └── explode/          # Per-date JSON: 炸板股池
│   └── .checked_dates.json  # Marker file: dates to skip in validation
└── README.md / CLAUDE.md     # Documentation
```

### Data Flow
```
Zhitu API (zhituapi.com)
    ↓ (fetch_history_data.py)
Raw JSON: data/history/{limit_up|limit_down|explode}/{date}.json
    ↓ (check_and_refetch.py)
Validate counts > 0, retry if needed, mark permanently failed dates
    ↓ (generate_ladder_data.py)
Merged JS: ladder_data.js with helper functions
    ↓ (ladder.html via browser)
Interactive ladder visualization
```

### Key Components Deep Dive

**fetch_history_data.py**
- `ZhituAPIFetcher` class - main API client
- Features:
  - Multiple token support with round-robin failover
  - Auto-detects failed tokens (401/403/429) and skips them temporarily
  - Trading calendar generation (excludes weekends)
  - 0.2s delay between requests to respect rate limits
  - Debug mode: `ZhituAPIFetcher(debug=True)` prints token usage
- Important: Tokens are hardcoded (security risk for production). Consider env vars.

**check_and_refetch.py**
- Scans all dates in `data/history/limit_up/` (or specified directory)
- Validates each date has all 3 data pools with non-zero counts
- Interactive workflow:
  1. Check every date
  2. Show summary: complete vs incomplete
  3. Prompt to refetch incomplete dates
  4. After refetch, prompt to mark still-failed dates (saves to `.checked_dates.json`)
- CLI args:
  - `--date YYYY-MM-DD` - check single date
  - `--check-only` - dry-run (no refetch)
  - `--dir CUSTOM_DIR` - use different data directory
- Smart skip: Dates in `.checked_dates.json` are automatically skipped with reason shown

**generate_ladder_data.py**
- Scans `data/history/` and `data/today/` (if exists)
- Merges all JSON by date into `ladderData` object
- Generates helper functions:
  - `getDateList()` → returns sorted date array (newest first)
  - `getDataByDate(date)` → returns {limit_up, limit_down, explode} or null
  - `getLimitUpData(date)`, `getLimitDownData(date)`, `getExplodeData(date)`
- Output: `ladder_data.js` (UTF-8, formatted, ~5-6MB for 4 months)

**ladder.html**
- Single-page web app (vanilla JS, no frameworks)
- Loads `ladder_data.js` as script (creates global `ladderData`)
- Features:
  - Date selector dropdown (populated from `getDateList()`)
  - Prev/Next day navigation buttons
  - Info bar: total limit-up count, max consecutive days, explode rate, limit-down count
  - Ladder visualization: stocks grouped by consecutive limit-up days ("tiers")
  - Stock cards showing: name, code, price, %change, turnover, first/last limit time, seal amount, circulation cap, industry, explode count
  - Dark gradient theme, responsive grid layout
- No external dependencies (self-contained except for ladder_data.js)

**data_fetcher.py**
- `DataFetcher` class provides alternative data source via AKShare
- Used by `fetch_history_data.py` as fallback for historical K-line data (for calculating consecutive days)
- Current workflow: Zhitu API is primary; AKShare only used internally for limit-up history calculation
- Can be used standalone with `use_mock=True` for testing

**config.py**
- Contains scoring weights, thresholds, risk management settings
- Originally designed for trading signal generation (not used in current visualization-only system)
- Safe to edit if you want to add scoring logic back

### Important Notes

- **Source control**: `ladder_data.js` is intentionally tracked despite `.gitignore` containing `*.js` because it's the build output required by HTML.
- **Security**: Tokens in `fetch_history_data.py` lines 16-19 are hardcoded. In production, move to environment variables or encrypted config.
- **No build system**: Simple Python scripts only. No npm/webpack/etc.
- **No unit tests**: Manual validation via `check_and_refetch.py`.
- **Performance**: `ladder_data.js` can be large. Future optimization: compression, pagination, or on-demand loading.
- **API stability**: Zhitu API's `dtgc` (limit-down) endpoint often returns 404 for recent dates. This is normal. Most dates will have `limit_down` count = 0. The system already handles this via the `.checked_dates.json` skip mechanism.
- **Multi-token**: Two tokens configured for higher rate limits. They rotate automatically. If both hit limits, failures will be logged.

### Recent Changes

**2025-02-11 - Multi-token failover support**
- Added second token: `0381DE88-49B9-42D8-BC51-167C4626B7A1`
- Round-robin token selection with auto-skips on 401/403/429
- Improves API quota and resilience

**2025-02-11 - Smart date checking with skip markers**
- Added `data/.checked_dates.json` to permanently skip dates confirmed to have missing data
- `check_and_refetch.py` now skips marked dates automatically
- Reduces redundant API calls and speeds up validation

**Previously - K-line feature removal**
- Removed: `kline.html`, `server.py`, and related documentation
- Ladder.html no longer binds click events to stock cards
- System now focused exclusively on ladder visualization

## Development Workflow

### Typical Data Update Cycle

```bash
# 1. Fetch new data (last 60 days)
python fetch_history_data.py --days 60

# 2. Validate and fix gaps
python check_and_refetch.py
# - Review which dates failed
# - Choose to refetch (y) or skip (n) for each batch
# - Mark permanently failed dates to avoid future retries

# 3. Build JavaScript data file
python generate_ladder_data.py

# 4. View in browser
# Start server and open http://localhost:8000/ladder.html
```

### Modification Guide

- **Data source tweaks**: edit `fetch_history_data.py` (API endpoints, request params)
- **Validation logic**: edit `check_and_refetch.py` (what constitutes "complete" data)
- **Web UI changes**: edit `ladder.html` (CSS in `<style>`, JS in last `<script>` block)
- **Data transformation**: edit `generate_ladder_data.py` (output format, helper functions)
- **Token management**: edit `fetch_history_data.py` line 16-19 (API_CONFIG["tokens"])
- **Market sentiment analysis**:
  - `simple_sentiment.py` - 核心情绪分析器（不依赖AKShare）
  - `generate_sentiment_report.py` - 批量生成情绪报告脚本
  - `market_sentiment.py` - 增强版（含指数/涨跌家数，AKShare依赖，不稳定）

## Dependencies

Install from `requirements.txt`:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `akshare>=1.11.0` - A-share market data (East Money)
- `pandas>=2.0.0`, `numpy>=1.24.0` - Data processing
- `requests>=2.31.0` - HTTP for Zhitu API
- `python-dateutil>=2.8.2` - Date parsing utilities

Note: Flask and Plotly are listed in `requirements.txt` but not currently used (legacy from K-line feature).

## External APIs

- **Zhitu API** (`https://api.zhituapi.com`) - Primary data source
  - Endpoints:
    - `/hs/pool/ztgc/{date}` - limit-up pool (涨停股池)
    - `/hs/pool/dtgc/{date}` - limit-down pool (跌停股池) - often 404
    - `/hs/pool/zbgc/{date}` - explode pool (炸板股池)
  - Multi-token: 2 tokens configured, auto-rotate
  - Rate limit: ~5 requests/sec per token (0.2s delay enforced)
  - Tokens (in code):
    - `BA43E6E1-A30D-4FEA-BD23-7B2376FD6114`
    - `0381DE88-49B9-42D8-BC51-167C4626B7A1`

- **AKShare** (via `akshare` library) - Fallback/Supplementary data source
  - Used for:
    - Historical K-line data (calculating consecutive limit-up days)
    - Market sentiment analysis: index data (`stock_zh_index_hist`), market breadth (`stock_zh_a_rank_em`)
  - Requires internet connection; has rate limits

## Data Schema

Fields from Zhitu API (Chinese field names in raw JSON):

| Field | Type | Meaning |
|-------|------|---------|
| `dm` | string | Stock code (e.g., "000017" or "000017.SZ") |
| `mc` | string | Stock name |
| `p` | float | Current price |
| `zf` | float | Change percentage (%) |
| `cje` | float/string | Trading volume (in RMB yuan) |
| `lt` | float/string | Circulating market cap ( yuan) |
| `hs` | float/string | Turnover rate (%) |
| `lbc` | int | Consecutive limit-up days (连板天数) |
| `fbt` | string | First limit-up time (HH:MM:SS) |
| `lbt` | string | Last limit-up time (HH:MM:SS) |
| `zj` | float/string | Seal amount (封板额, yuan) |
| `zbc` | int | Explode count (炸板次数) |
| `hy` | string | Industry sector |
| `tj` | string | Statistics tag |

**Usage in ladder.html:**
- `s.dm` → stock code
- `s.mc` → stock name
- `s.p` → price
- `s.zf` → change %
- `s.hs` → turnover %
- `s.cje` → volume (divided by 10000 to show 万)
- `s.lt` → circulation cap (divided by 100000000 to show 亿)
- `s.lbc` → consecutive days
- `s.fbt`, `s.lbt` → times (formatted by `fmtTime()`)
- `s.zj` → seal amount
- `s.hy` → industry
- `s.zbc` → explode count

## Known Issues & Limitations

1. **Limit-down data often missing**: Zhitu API's `dtgc` endpoint frequently returns 404. This is expected for many dates. The system handles this by allowing limit-down count to be 0 and allowing you to mark such dates as "checked" to skip future validation.
2. **AKShare connectivity**: If AKShare is unreachable, fallback mock data may be used for some calculations (non-critical).
3. **Large JS bundle**: `ladder_data.js` for 4+ months of data is ~6MB. Consider pagination or date-range filtering for future improvements.
4. **Hardcoded tokens**: Security risk. Should use environment variables or config file outside version control.
5. **No authentication**: The simple HTTP server has no access control. Not suitable for public deployment without adding auth.
6. **Weekend handling**: The script skips weekends when generating trading calendars, but you must only fetch data for actual trading days. API calls on weekends return empty.

## Troubleshooting

**Problem**: `check_and_refetch.py` keeps retrying the same failed dates
- **Solution**: These dates likely have a permanent API issue (e.g., limit-down endpoint 404). Answer `y` when prompted to mark them as "confirmed no data" after a failed refetch attempt. They will be saved to `data/.checked_dates.json` and skipped in future runs.

**Problem**: `ladder.html` shows "该日期暂无涨停数据"
- **Cause**: The selected date has no limit-up data (可能假日或API未返回)
- **Solution**: Check the JSON file in `data/history/limit_up/`. If missing, fetch that date manually: `python fetch_history_data.py --date YYYY-MM-DD`

**Problem**: `generate_ladder_data.py` produces empty `ladder_data.js`
- **Cause**: No data files in `data/history/` subdirectories
- **Solution**: First fetch data, then run the generator

**Problem**: "token失效" or "请求频率限制" messages
- **Cause**: Zhitu API tokens have rate limits. Multi-token rotation helps.
- **Solution**: Wait a few seconds. Scripts already have 0.2s delays. If persistent, check token validity and possibly add more tokens to `API_CONFIG["tokens"]` in `fetch_history_data.py`

