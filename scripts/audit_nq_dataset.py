#!/usr/bin/env python3
from __future__ import annotations
import os, json, math, statistics, datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

# Prefer DB via SQLModel; fallback to parquet if DB not available.
USE_DB = True

def load_from_db() -> pd.DataFrame:
    import sqlite3
    import json
    
    # Direct SQLite access for simplicity
    conn = sqlite3.connect('trading_agent.db')
    cursor = conn.cursor()
    
    # Get all trade logs
    cursor.execute("SELECT * FROM trade_logs")
    rows = cursor.fetchall()
    
    # Get column names
    cursor.execute("PRAGMA table_info(trade_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    conn.close()
    
    if not rows:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=columns)
    
    # Parse JSON fields
    if 'features' in df.columns:
        df['features'] = df['features'].apply(lambda x: json.loads(x) if x else {})
    
    return df

def load_from_parquet() -> Optional[pd.DataFrame]:
    p = Path("data/processed/trades_dataset.parquet")
    if p.exists():
        return pd.read_parquet(p)
    return None

def ensure_dt(x):
    try:
        return pd.to_datetime(x, utc=True)
    except Exception:
        return pd.NaT

def pct(n, d): 
    return 0.0 if (d or 0) == 0 else round(100.0 * n / d, 2)

def audit(df: pd.DataFrame) -> Dict[str, Any]:
    report: Dict[str, Any] = {"checks": []}
    n = len(df)
    report["summary"] = {"total_trades": int(n)}

    # Basic shape
    if n == 0:
        report["checks"].append(("FAIL","No trades found. Run backfill or add manual trades."))
        return report

    # Parse backfill and source information from features
    backfill_data = []
    source_data = []
    
    if "features" in df.columns:
        for idx, features in df["features"].items():
            # Parse features JSON
            try:
                if isinstance(features, dict):
                    feat_dict = features
                elif isinstance(features, str):
                    feat_dict = json.loads(features) if features else {}
                else:
                    feat_dict = {}
                
                is_backfill = feat_dict.get("is_backfill", False)
                source = feat_dict.get("source", "unknown")
                
                backfill_data.append(is_backfill)
                source_data.append(source)
            except Exception:
                backfill_data.append(False)
                source_data.append("unknown")
    else:
        backfill_data = [False] * n
        source_data = ["unknown"] * n
    
    # Add backfill and source columns
    df["is_backfill"] = backfill_data
    df["source"] = source_data
    
    # Backfill vs Live/Paper analysis
    backfill_count = sum(backfill_data)
    live_count = n - backfill_count
    backfill_pct = pct(backfill_count, n)
    
    report["summary"]["backfill_analysis"] = {
        "backfill_count": int(backfill_count),
        "live_count": int(live_count),
        "backfill_percentage": round(backfill_pct, 2)
    }
    
    # Source analysis
    source_counts = pd.Series(source_data).value_counts().to_dict()
    report["summary"]["source_analysis"] = source_counts
    
    # Temporal analysis for live trades
    live_df = df[~df["is_backfill"]].copy()
    recent_live_count = 0
    
    if len(live_df) > 0 and "entered_at" in df.columns:
        # Use entered_at for temporal analysis
        live_df["entered_at"] = live_df["entered_at"].apply(ensure_dt)
        now = pd.Timestamp.now(tz='UTC')
        thirty_days_ago = now - pd.Timedelta(days=30)
        
        # Count recent live trades (within last 30 days)
        recent_live = live_df[live_df["entered_at"] >= thirty_days_ago]
        recent_live_count = len(recent_live)
        
        # Calculate temporal statistics
        entered_at_series = live_df["entered_at"].dropna()
        if len(entered_at_series) > 0:
            temporal_stats = {
                "median_entered_at": str(entered_at_series.median()),
                "q25_entered_at": str(entered_at_series.quantile(0.25)),
                "q75_entered_at": str(entered_at_series.quantile(0.75)),
                "min_entered_at": str(entered_at_series.min()),
                "max_entered_at": str(entered_at_series.max()),
                "recent_live_count_30d": int(recent_live_count)
            }
            report["summary"]["temporal_analysis"] = temporal_stats
    
    # Warnings
    if backfill_pct > 80:
        report["checks"].append(("WARN", f"High backfill percentage ({backfill_pct:.1f}%). Consider adding more live/paper trades."))
    else:
        report["checks"].append(("PASS", f"Backfill percentage is reasonable ({backfill_pct:.1f}%)."))
    
    if recent_live_count < 50:
        report["checks"].append(("WARN", f"Low recent live trade count ({recent_live_count} in last 30 days). Consider more live trading."))
    else:
        report["checks"].append(("PASS", f"Recent live trade count is adequate ({recent_live_count} in last 30 days)."))

    # Normalize core columns
    # Try to align naming whether reading from DB or parquet
    col_map = {
        "created_at": "created_at",
        "entered_at": "entered_at",
        "exited_at": "exited_at",
        "symbol": "symbol",
        "side": "side",
        "qty": "qty",
        "entry_price": "entry_price",
        "stop_price": "stop_price",
        "target_price": "target_price",
        "exit_price": "exit_price",
        "pnl_usd": "pnl_usd",
        "r_multiple": "r_multiple",
        "outcome": "outcome",
        "features": "features",
    }
    for k,v in col_map.items():
        if k not in df.columns and v in df.columns:
            continue
    # Coerce datetimes if present
    for c in ["created_at","entered_at","exited_at"]:
        if c in df.columns:
            df[c] = df[c].apply(ensure_dt)

    # NQ-only filter check
    if "symbol" in df.columns:
        non_nq = df[~df["symbol"].astype(str).str.startswith("NQ")]
        if len(non_nq) == 0:
            report["checks"].append(("PASS", "All trades are NQ-only."))
        else:
            report["checks"].append(("WARN", f"{len(non_nq)} trades are non-NQ symbols. Recommend filtering to NQ* only."))

    # Date range
    date_col = "created_at" if "created_at" in df.columns else ("entered_at" if "entered_at" in df.columns else None)
    if date_col:
        dmin = pd.to_datetime(df[date_col].min(), utc=True)
        dmax = pd.to_datetime(df[date_col].max(), utc=True)
        report["summary"]["date_range_utc"] = [str(dmin), str(dmax)]
        report["checks"].append(("PASS", f"Date range: {dmin} to {dmax} (UTC)"))

    # Outcome balance
    outcome_col = "outcome" if "outcome" in df.columns else None
    r_col = "r_multiple" if "r_multiple" in df.columns else None
    win_est = None
    if outcome_col:
        counts = df[outcome_col].fillna("unknown").value_counts().to_dict()
        report["summary"]["outcomes"] = counts
        wins = counts.get("target", 0)
        stops = counts.get("stop", 0)
        total_labeled = wins + stops
        if total_labeled >= int(0.4*n):
            wr = pct(wins, total_labeled)
            win_est = wr
            if 35 <= wr <= 65:
                report["checks"].append(("PASS", f"Outcome balance OK (win rate ~ {wr}%)."))
            else:
                report["checks"].append(("WARN", f"Outcome skewed (win rate ~ {wr}%). Consider adding more trades."))
        else:
            report["checks"].append(("WARN", "Many trades lack target/stop outcomes; consider increasing horizon or labeling."))
    elif r_col:
        wins = (df[r_col] > 0).sum()
        total = len(df)
        wr = pct(wins, total)
        win_est = wr
        report["checks"].append(("INFO", f"Estimated win rate from R>0: {wr}%."))

    # Feature coverage (JSON)
    feat_cols = ["risk","rr","atr14","body_pct","upper_wick_pct","lower_wick_pct","htf_trend","in_session","strategy_id","setup"]
    coverage = {}
    if "features" in df.columns:
        # Parse dicts
        def getf(x, k):
            if isinstance(x, dict):
                return x.get(k, None)
            try:
                d = json.loads(x) if isinstance(x, str) else {}
                return d.get(k, None)
            except Exception:
                return None
        for k in feat_cols:
            vals = df["features"].apply(lambda x: getf(x,k))
            na = vals.isna().sum()
            coverage[k] = {"non_null": int(len(vals)-na), "pct_non_null": pct(len(vals)-na, len(vals))}
        report["summary"]["feature_coverage"] = coverage
        # Key features presence
        must = ["risk","rr"]
        missing_must = [m for m in must if coverage.get(m,{}).get("non_null",0) < n]
        if not missing_must:
            report["checks"].append(("PASS","Core features present (risk, rr)."))
        else:
            report["checks"].append(("FAIL", f"Missing required features: {missing_must}"))

        # Nice-to-have warning thresholds
        soft = ["atr14","body_pct","upper_wick_pct","lower_wick_pct","htf_trend","in_session"]
        weak = [k for k in soft if coverage.get(k,{}).get("pct_non_null",0) < 50.0]
        if weak:
            report["checks"].append(("WARN", f"Low coverage on price-action/context features: {', '.join(weak)}."))
        else:
            report["checks"].append(("PASS", "Price-action/context features coverage looks good."))
    else:
        report["checks"].append(("WARN","No features column found. Add features JSON to each trade."))

    # Duplicates (naive)
    dup = 0
    keys = [c for c in ["symbol","side","entry_price","created_at"] if c in df.columns]
    if len(keys) >= 2:
        dup = int(df.duplicated(subset=keys, keep=False).sum())
        if dup == 0:
            report["checks"].append(("PASS", "No obvious duplicate trades by (symbol, side, entry_price, created_at)."))
        else:
            report["checks"].append(("WARN", f"Found {dup} potential duplicate rows (by {keys})."))
    # Outliers (risk/rr/atr14)
    def qstats(series):
        s = series.dropna().astype(float)
        if len(s) == 0:
            return None
        q = s.quantile([0.01,0.25,0.5,0.75,0.99])
        return {str(k): float(v) for k,v in q.items()}
    dist = {}
    # Pull feature fields out of JSON for distributions
    def fcol(name):
        if "features" in df.columns:
            def getf(x):
                try:
                    d = x if isinstance(x, dict) else (json.loads(x) if isinstance(x,str) else {})
                except Exception:
                    d = {}
                return d.get(name, None)
            return df["features"].apply(getf)
        return pd.Series(dtype=float)
    dist["risk"] = qstats(fcol("risk"))
    dist["rr"] = qstats(fcol("rr"))
    dist["atr14"] = qstats(fcol("atr14"))
    report["summary"]["distributions"] = dist

    # Suggestions
    suggestions = []
    if n < 200:
        suggestions.append("Increase dataset to 200–500 trades for more stable training.")
    if win_est is not None and (win_est < 35 or win_est > 65):
        suggestions.append("Improve outcome balance (add more sessions or adjust backfill parameters).")
    if "feature_coverage" in report["summary"]:
        cov = report["summary"]["feature_coverage"]
        for k in ["atr14","body_pct","upper_wick_pct","lower_wick_pct","htf_trend"]:
            if cov.get(k,{}).get("pct_non_null",0) < 50.0:
                suggestions.append(f"Enhance feature coverage for {k} (compute at backfill/order time).")
    report["suggestions"] = suggestions
    return report

def to_markdown(rep: Dict[str,Any]) -> str:
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []
    lines.append(f"# NQ Dataset Audit\nGenerated: {ts}\n")
    s = rep.get("summary", {})
    lines.append(f"- Total trades: **{s.get('total_trades',0)}**")
    if "date_range_utc" in s:
        a,b = s["date_range_utc"]
        lines.append(f"- Date range (UTC): **{a} to {b}**")
    if "outcomes" in s:
        lines.append(f"- Outcomes: `{json.dumps(s['outcomes'])}`")
    
    # Backfill vs Live Analysis
    if "backfill_analysis" in s:
        ba = s["backfill_analysis"]
        lines.append("\n## Backfill vs Live/Paper Analysis")
        lines.append(f"- **Backfill trades**: {ba['backfill_count']} ({ba['backfill_percentage']}%)")
        lines.append(f"- **Live/Paper trades**: {ba['live_count']} ({100-ba['backfill_percentage']:.1f}%)")
    
    # Source Analysis
    if "source_analysis" in s:
        lines.append("\n## Source Analysis")
        lines.append("| Source | Count | Percentage |")
        lines.append("|--------|-------|------------|")
        total = s.get('total_trades', 1)
        for source, count in sorted(s["source_analysis"].items(), key=lambda x: x[1], reverse=True):
            pct = round(100.0 * count / total, 1)
            lines.append(f"| {source} | {count} | {pct}% |")
    
    # Temporal Analysis
    if "temporal_analysis" in s:
        ta = s["temporal_analysis"]
        lines.append("\n## Temporal Analysis (Live/Paper Trades)")
        lines.append(f"- **Recent live trades (30d)**: {ta.get('recent_live_count_30d', 0)}")
        lines.append(f"- **Median entered_at**: {ta.get('median_entered_at', 'N/A')}")
        lines.append(f"- **Q25 entered_at**: {ta.get('q25_entered_at', 'N/A')}")
        lines.append(f"- **Q75 entered_at**: {ta.get('q75_entered_at', 'N/A')}")
        lines.append(f"- **Min entered_at**: {ta.get('min_entered_at', 'N/A')}")
        lines.append(f"- **Max entered_at**: {ta.get('max_entered_at', 'N/A')}")
    
    if "feature_coverage" in s:
        lines.append("\n## Feature Coverage")
        for k,v in s["feature_coverage"].items():
            lines.append(f"- {k}: {v['non_null']} non-null ({v['pct_non_null']}%)")
    if "distributions" in s:
        lines.append("\n## Distributions (quantiles)")
        for k,v in s["distributions"].items():
            lines.append(f"- {k}: {json.dumps(v) if v else 'n/a'}")
    lines.append("\n## Checks")
    for level, msg in rep.get("checks", []):
        badge = {"PASS":"[OK]","WARN":"[WARN]","FAIL":"[FAIL]","INFO":"[INFO]"}.get(level, "[•]")
        lines.append(f"- {badge} **{level}** - {msg}")
    if rep.get("suggestions"):
        lines.append("\n## Suggestions")
        for s in rep["suggestions"]:
            lines.append(f"- {s}")
    return "\n".join(lines)

def main():
    Path("reports/audit").mkdir(parents=True, exist_ok=True)
    df = None
    if USE_DB:
        try:
            df = load_from_db()
        except Exception as e:
            print("DB load failed:", e)
    if df is None or len(df)==0:
        df = load_from_parquet()
    if df is None:
        print("No data sources found (DB/parquet)."); return 1

    rep = audit(df)
    md = to_markdown(rep)
    ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out = Path(f"reports/audit/audit_{ts}.md")
    out.write_text(md, encoding='utf-8')
    print(f"Wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
