# Contributing to AI Trading Agent

## Development Rules

### Non-goals
Do not add strategy logic, indicators, backtests, or live routing by default.

### Config Contract
Keep Settings fields as-is (BROKER, DAILY_LOSS_CAP_USD, MAX_TRADES_PER_DAY, MAX_CONTRACTS, session_windows_normalized). Use aliases only in the Settings model.

### Scope Creep
Any new file must fit one of: API route, broker adapter, risk guard, persistence, logging, UI, or config provider. Otherwise, open a TODO in docs/RFCs.md.

### Versioned API
All new routes under /v1.

### Paper-first
Default broker = paper. Live adapters are stubs until explicitly enabled by env.

### Definition of Done
Tests pass (pytest -q), make run launches API+UI, /v1/health and /v1/debug/config work, and docs updated.
