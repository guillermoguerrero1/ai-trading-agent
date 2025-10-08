# AI Trading Agent

⚠️ **Scope**: This repo is a base scaffold (paper trading, risk guard, API, UI). It intentionally contains **no strategy logic** and **no default live trading**. Any new features must follow CONTRIBUTING.md and RFCs.md before implementation.

A production-ready AI Trading Agent built with FastAPI, Streamlit, and MLflow. Features comprehensive risk management, multiple broker support, and real-time monitoring.

## 🚀 Quickstart

### Setup
```bash
# Clone and setup
git clone <repository-url>
cd ai-trading-agent

# Install dependencies
make setup-dev

# Copy environment file
cp .env.example .env
```

### Run
```bash
# Start API server
make run-api
# API available at http://localhost:9001

# Start Streamlit dashboard (in another terminal)
make run-ui
# Dashboard available at http://localhost:8501

# Or run everything with Docker
make run-docker
```

### Test
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
python -m pytest tests/test_config.py -v
```

## 🔥 Smoke Test

Quick verification that the system is working:

1. Start API
```bash
make run-api
```

Health & config
```bash
curl -s http://localhost:9001/v1/health
curl -s http://localhost:9001/v1/debug/config | jq
```

Place a paper bracket
```bash
curl -X POST http://localhost:9001/v1/orders \
 -H "Content-Type: application/json" \
 -d '{"symbol":"NQZ5","side":"SELL","qty":1,"entry":17895,"stop":17905,"target":17875,"paper":true}'
```

(If tick route exists) Push a price to drive fills
```bash
curl -X POST http://localhost:9001/v1/tick -H "Content-Type: application/json" \
 -d '{"symbol":"NQZ5","price":17894.75}'
```

### Quick Trade (template)
1) Edit `trade_template.json` with side/entry/stop/target.
2) Submit: `make trade`
3) Archive: copies to `trades_submitted/` automatically.

## Quick Trade Entry (NQ)
- Edit `trade_template.json` (set side/entry/stop/target) then:
  ```bash
  make trade
  ```
- Or use interactive CLI:
  ```bash
  make trade-cli
  ```
  
  **CLI Options:**
  ```bash
  # Normal usage (current timestamp)
  python scripts/trade_cli.py
  
  # With custom entry timestamp
  python scripts/trade_cli.py --entered-at "2025-09-12T13:45:00Z"
  
  # Mark as backfilled trade
  python scripts/trade_cli.py --backfill
  
  # Both options together
  python scripts/trade_cli.py --entered-at "2025-09-12T13:45:00Z" --backfill
  ```
- Optional: Streamlit form at http://localhost:8501 (Quick Trade tab)
  - **Datetime Input**: Set custom entry timestamp (defaults to current UTC)
  - **Backfill Checkbox**: Mark trades as backfilled
  - **Validation**: Prevents future timestamps
- All methods use Idempotency-Key headers and auto-archive to `trades_submitted/`

### Backfilling Old Trades

When entering historical trades, include a custom timestamp with **UTC requirement**:

```json
"entered_at": "2025-09-12T13:45:00Z"
```

**UTC Requirement**: All timestamps must be in UTC timezone. The server validates this and will reject future timestamps.

**Supported formats:**
- `2025-09-12T13:45:00Z` (ISO 8601 UTC - **recommended**)
- `2025-09-12T13:45:00+00:00` (ISO 8601 with timezone)
- `2025-09-12 13:45:00` (Simple datetime - converted to UTC)

**Example curl with entered_at:**
```bash
curl -X POST http://localhost:9001/v1/orders \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: backfill-$(date +%Y%m%d-%H%M%S)" \
  -d '{
    "symbol": "NQZ5",
    "side": "BUY",
    "quantity": 1,
    "order_type": "LIMIT",
    "price": 17895,
    "stop_price": 17885,
    "target_price": 17915,
    "entered_at": "2025-09-12T13:45:00Z",
    "paper": true,
    "features": {
      "strategy_id": "ORB",
      "setup": "Backfill-Test",
      "is_backfill": true
    },
    "notes": "backfilled trade"
  }'
```

**Example backfilled trade JSON:**
```json
{
  "symbol": "NQZ5",
  "side": "BUY",
  "quantity": 1,
  "order_type": "LIMIT",
  "price": 17895,
  "stop_price": 17885,
  "target_price": 17915,
  "entered_at": "2025-09-12T13:45:00Z",
  "paper": true,
  "features": {
    "strategy_id": "ORB",
    "setup": "Backfill-Test",
    "is_backfill": true
  },
  "notes": "backfilled trade"
}
```

### Backfill Best Practices

**1. Prefer True Historical entered_at**
- Use actual historical timestamps when available
- Server auto-detects backfill if `entered_at` is >1 hour before submission
- More accurate temporal analysis and model training

**2. Set features.is_backfill=true (or let server auto-tag)**
- Explicitly mark: `"features": {"is_backfill": true}`
- Or let server auto-detect based on timestamp difference
- Enables proper filtering and weighting in training

**3. Training Strategy**
- **Initial Training**: Use `EXCLUDE_BACKFILL=1` to train on live data only
- **Blended Training**: Use `WEIGHT_BACKFILL=0.5` to include backfill with reduced weight
- **Environment Variables**:
  ```bash
  # Train excluding backfill data
  EXCLUDE_BACKFILL=1 make train
  
  # Train with backfill weighted at 50%
  EXCLUDE_BACKFILL=0 WEIGHT_BACKFILL=0.5 make train
  
  # Train with heavy backfill weighting (10%)
  EXCLUDE_BACKFILL=0 WEIGHT_BACKFILL=0.1 make train
  ```

**4. Validation**
- Server validates `entered_at` is not in the future
- Returns 400 error for invalid timestamps
- Auto-computes `is_backfill` flag if not provided
- Infers `source` from User-Agent header

**Direct database entry** (bypasses API limits):
```bash
python scripts/direct_trade_entry.py
# Follow prompts and enter custom timestamp when asked
```

## Telegram Bot Trade Entry (NQ only)

Send trade commands directly from Telegram:

### Setup
1) Create a bot with @BotFather → copy the token.
2) Set env vars:
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USER_IDS=123456789
TELEGRAM_ENABLE=true
TELEGRAM_WEBHOOK_URL=https://<your-domain-or-ngrok>/v1/hooks/telegram
```

### Usage
Send messages to your bot:
```
trade NQZ5 buy 1 @ 17895 stop 17885 target 17915
NQZ5 sell 2 @ 20450 stop 20460 target 20430 strat:ORB conf:0.8
```

### Webhook Management
```bash
# Set webhook URL
make telegram-webhook

# Remove webhook
make telegram-webhook-delete
```

See `docs/TELEGRAM_SETUP.md` for complete setup guide.

## NQ Dataset Audit
Run a quick quality check on your NQ trades:
```bash
make audit
```

This generates a timestamped report in `reports/audit/` with:

- **✅ PASS**: Dataset meets quality standards
- **⚠️ WARN**: Issues that should be addressed
- **❌ FAIL**: Critical problems requiring immediate attention

### Key Metrics
- **NQ Compliance**: Ensures all trades are NQ futures only
- **Feature Coverage**: Validates risk/R/R and technical indicators
- **Outcome Balance**: Checks win/loss distribution (target: 35-65% win rate)
- **Dataset Size**: Recommends 200-500 trades for stable training
- **Duplicates**: Detects potential duplicate entries
- **Backfill Analysis**: Shows backfill vs live/paper trade distribution
- **Source Tracking**: Displays trade sources (ui, manual_json, backfill_script, etc.)
- **Temporal Analysis**: Recent live trades, median/quantiles of entered_at timestamps
- **Data Quality Warnings**: Alerts for >80% backfill or <50 recent live trades

### Sample Report
```markdown
# NQ Dataset Audit
- Total trades: **74**
- Date range: **2025-01-01 to 2025-10-05**
- Outcomes: `{"stop": 70, "unknown": 4}`

## Backfill vs Live/Paper Analysis
- **Backfill trades**: 1 (1.35%)
- **Live/Paper trades**: 73 (98.7%)

## Source Analysis
| Source | Count | Percentage |
|--------|-------|------------|
| unknown | 72 | 97.3% |
| test | 1 | 1.4% |
| manual_json | 1 | 1.4% |

## Temporal Analysis (Live/Paper Trades)
- **Recent live trades (30d)**: 2
- **Median entered_at**: 2025-01-01 10:03:30+00:00
- **Q25 entered_at**: 2025-01-01 09:54:45+00:00
- **Q75 entered_at**: 2025-01-01 10:12:15+00:00

## Checks
- [OK] **PASS** - Backfill percentage is reasonable (1.4%)
- [WARN] **WARN** - Low recent live trade count (2 in last 30 days)
- [OK] **PASS** - All trades are NQ-only
- [OK] **PASS** - Core features present (risk, rr)
- [WARN] **WARN** - Outcome skewed (win rate ~ 0.0%)
```

## 📡 API Examples

### Health Check
```bash
curl http://localhost:9001/v1/health/
```

### Place Order
```bash
curl -X POST http://localhost:9001/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 100,
    "order_type": "MARKET"
  }'
```

### Submit Signal
```bash
curl -X POST http://localhost:9001/v1/signal/ \
  -H "Content-Type: application/json" \
  -d '{
    "signal_type": "BUY",
    "symbol": "AAPL",
    "quantity": 100,
    "price": 150.0,
    "confidence": 0.85,
    "metadata": {
      "strategy": "momentum",
      "timeframe": "1h"
    }
  }'
```

### Get Daily P&L
```bash
curl http://localhost:9001/v1/pnl/daily
```

### Get Configuration
```bash
curl http://localhost:9001/v1/config/
```

### Update Configuration
```bash
curl -X PUT http://localhost:9001/v1/config/ \
  -H "Content-Type: application/json" \
  -d '{
    "max_trades_per_day": 10,
    "daily_loss_cap_usd": 500.0,
    "session_windows": ["09:30-16:00"]
  }'
```

### Logs API
- List recent trades:
```bash
curl -s "http://localhost:9001/v1/logs/trades?limit=10" | jq
```

- Debug mounted routes:
```bash
curl -s http://localhost:9001/v1/debug/routes | jq
```

## 🧠 Strategy Integration

### Where to Plug in Your Strategy

The system is designed for easy strategy integration:

1. **Signal Processing** (`app/routes/signal.py`):
   - Receives trading signals via POST `/v1/signal/`
   - Validates signals against guardrails
   - Converts to orders for execution

2. **Strategy Service** (create `app/services/strategy.py`):
   ```python
   class StrategyService:
       async def process_signal(self, signal: SignalRequest) -> OrderRequest:
           # Your strategy logic here
           # - Technical analysis
           # - ML model predictions
           # - Risk assessment
           # - Position sizing
           pass
   ```

3. **Execution Pipeline**:
   ```
   Signal → Strategy → Risk Check → Order → Broker → Position
   ```

### Example Strategy Integration
```python
# app/services/strategy.py
from app.models.order import OrderRequest, OrderSide, OrderType
from app.models.base import SignalRequest

class MomentumStrategy:
    async def generate_signal(self, market_data: dict) -> SignalRequest:
        # Your momentum strategy logic
        if self.detect_momentum(market_data):
            return SignalRequest(
                signal_type="BUY",
                symbol=market_data["symbol"],
                quantity=100,
                confidence=0.8
            )
        return None
```

## 🛡️ Safety Features

### Paper Trading Default
- **Default Mode**: Paper trading with simulated market data
- **No Real Money**: All trades are simulated until you explicitly configure live brokers
- **Safe Testing**: Test strategies without financial risk

### Risk Management
- **Daily Loss Cap**: Automatic halt when daily losses exceed limit (default: $300)
- **Trade Limits**: Maximum trades per day (default: 5)
- **Session Windows**: Trading only allowed during specified hours
- **Position Limits**: Maximum contracts and position sizes
- **Real-time Monitoring**: Continuous risk assessment and violation tracking

### Guardrails
```bash
# Current safety limits (configurable via .env)
DAILY_LOSS_CAP_USD=300
MAX_TRADES_PER_DAY=5
SESSION_WINDOWS=06:30-08:00,08:30-10:00
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   FastAPI API   │    │   MLflow Ops    │
│   (Dashboard)   │    │   (Endpoints)   │    │   (Tracking)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Trading Core   │
                    │                 │
                    │ ┌─────────────┐ │
                    │ │ Supervisor  │ │
                    │ │ (Monitoring)│ │
                    │ └─────────────┘ │
                    │ ┌─────────────┐ │
                    │ │ Risk Guard  │ │
                    │ │ (Safety)    │ │
                    │ └─────────────┘ │
                    │ ┌─────────────┐ │
                    │ │ Execution   │ │
                    │ │ (Brokers)   │ │
                    │ └─────────────┘ │
                    └─────────────────┘
```

## 📊 Monitoring

### Streamlit Dashboard
- **Real-time Status**: Trading state, P&L, positions
- **Risk Monitoring**: Guardrail status, violations
- **Order Management**: View and manage orders
- **Event Log**: System events and alerts
- **Configuration**: Adjust settings and limits

### API Endpoints
- **Health**: `/v1/health/`
- **Config**: `/v1/config/`
- **Orders**: `/v1/orders/`
- **P&L**: `/v1/pnl/daily`
- **Signals**: `/v1/signal/`
- **Logs**: `/v1/logs/trades`
- **Debug**: `/v1/debug/routes`

## 🔧 Configuration

### Port Configuration
**Canonical API Port: 9001**
- The API server is standardized to run on port 9001
- This is the default port for all API endpoints and documentation
- Use `make cleanup-ports` to free up ports if needed

### Environment Variables
```bash
# Core settings
APP_ENV=dev
API_PORT=9001
TZ=America/Phoenix
BROKER=paper

# Risk management
DAILY_LOSS_CAP_USD=300
MAX_TRADES_PER_DAY=5
SESSION_WINDOWS=06:30-08:00,08:30-10:00

# Logging
LOG_LEVEL=INFO
```

### YAML Configuration
```yaml
# config/config.yaml
trading:
  default_broker: "paper"
  initial_capital: 100000.0

guardrails:
  max_trades_per_day: 5
  daily_loss_cap_usd: 300.0
  session_windows:
    - "06:30-08:00"
    - "08:30-10:00"
```

### Environment-Specific Configuration

The project includes environment-specific configuration files for different deployment scenarios:

#### Available Environments

- **Development** (`.env.dev`): Optimized for development and testing
- **Production** (`.env.prod`): Optimized for production deployment

#### Running with Specific Environments

```bash
# Development environment (extended hours, debug logging)
make run-dev

# Production environment (market hours, optimized performance)
make run-prod

# Default environment (uses built-in defaults)
make run-api
```

#### Key Environment Differences

| Setting | Development (`.env.dev`) | Production (`.env.prod`) | Default |
|---------|-------------------------|-------------------------|---------|
| **API Port** | `9001` | `8000` | `9001` |
| **API Workers** | `1` | `4` | `1` |
| **Database** | `trading_agent_dev.db` | `trading_agent.db` | `trading_agent.db` |
| **Database Echo** | `true` (SQL logging) | `false` | `false` |
| **Log Level** | `DEBUG` | `INFO` | `INFO` |
| **Debug Mode** | `true` | `false` | `true` |
| **Max Contracts** | `10` | `5` | `5` |
| **Max Trades/Day** | `10` | `5` | `5` |
| **Daily Loss Cap** | `$500` | `$200` | `$300` |
| **Trading Hours** | `06:00-20:00` (7 days) | `09:30-16:00` (weekdays) | `08:30-15:00` |
| **Position Limit** | `20%` | `10%` | `10%` |

#### Environment File Selection

The Makefile targets automatically:
1. **Copy** the appropriate `.env.{environment}` file to `.env`
2. **Start** the server with environment-specific settings
3. **Validate** that the environment file exists before starting

#### Custom Environment Files

You can create additional environment files (e.g., `.env.staging`) and use them:

```bash
# Create custom environment
cp .env.dev .env.staging
# Edit .env.staging with staging-specific values

# Run with custom environment
cp .env.staging .env && uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload
```

#### Environment Variables Priority

Configuration is loaded in this order:
1. **Environment variables** (highest priority)
2. **`.env` file** (copied from `.env.{environment}`)
3. **Default values** in `app/models/base.py` (lowest priority)

### Prometheus Metrics

The API exposes Prometheus metrics at `/v1/metrics/prom` for monitoring and alerting.

#### Available Metrics

- **`trading_orders_ok_total`**: Successful orders (labeled by symbol, side)
- **`trading_orders_blocked_total`**: Blocked orders (labeled by symbol, side, reason)
- **`trading_halts_total`**: Trading halts (labeled by reason)
- **`trading_model_blocks_total`**: Model blocks (labeled by model_version, reason)
- **`trading_process_uptime_seconds`**: Process uptime
- **`trading_process_version_info`**: Version information (labeled by version, environment)

#### Sample Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'ai-trading-agent'
    static_configs:
      - targets: ['localhost:9001']
    metrics_path: '/v1/metrics/prom'
    scrape_interval: 15s
    scrape_timeout: 10s
```

#### Sample Grafana Dashboard

```json
{
  "dashboard": {
    "title": "AI Trading Agent",
    "panels": [
      {
        "title": "Order Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(trading_orders_ok_total[5m]) / (rate(trading_orders_ok_total[5m]) + rate(trading_orders_blocked_total[5m])) * 100"
          }
        ]
      },
      {
        "title": "Orders Over Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(trading_orders_ok_total[1m])",
            "legendFormat": "Successful Orders"
          },
          {
            "expr": "rate(trading_orders_blocked_total[1m])",
            "legendFormat": "Blocked Orders"
          }
        ]
      }
    ]
  }
}
```

## 🚀 Next Steps

### 1. MLflow Integration

The training script now includes MLflow integration for experiment tracking and model management:

#### Features:
- **Experiment Tracking**: All training runs are logged to MLflow
- **Model Artifacts**: Models are saved as MLflow artifacts
- **Model Promotion**: Production models can be promoted via API
- **Fallback Support**: Works with or without MLflow server

#### Usage:

```bash
# Train with MLflow tracking (default: local file tracking)
make train

# Train with MLflow server
MLFLOW_TRACKING_URI=http://localhost:5000 make train

# Promote latest Production model
curl -X POST http://localhost:9001/v1/model/promote
```

#### MLflow Configuration:

```bash
# Set MLflow tracking URI
export MLFLOW_TRACKING_URI="http://localhost:5000"

# Or use local file tracking (default)
export MLFLOW_TRACKING_URI="file:./mlruns"
```

#### Model Lifecycle:

1. **Training**: Models are automatically logged to MLflow
2. **Tagging**: Best models are tagged as "Production"
3. **Promotion**: Use `/v1/model/promote` to switch to latest Production model
4. **Fallback**: If MLflow unavailable, falls back to local training

### 2. Backtesting Engine

A comprehensive backtesting engine is now available at `engines/backtest/run.py`:

#### Features:
- **Historical Data Loading**: Supports CSV and Parquet formats
- **Technical Indicators**: SMA, RSI, Bollinger Bands, MACD
- **Signal Generation**: Simple rule-based trading signals
- **Bracket Trading**: Stop loss and take profit management
- **Risk Management**: Position sizing, commission, slippage
- **HTML Reports**: Beautiful interactive reports with charts

#### Usage:

```bash
# Basic backtesting
python engines/backtest/run.py data/sample_btc_data.csv

# Custom parameters
python engines/backtest/run.py data/sample_btc_data.csv \
    --initial-capital 10000 \
    --position-size 0.1 \
    --stop-loss 0.02 \
    --take-profit 0.04

# Using Makefile (Linux/macOS)
make backtest DATA_FILE=data/sample_btc_data.csv CAPITAL=5000
```

#### Sample Data Format:

```csv
timestamp,open,high,low,close,volume
2025-09-03 09:00:00,50000.0,50500.0,49500.0,50200.0,1500
2025-09-03 09:15:00,50200.0,50800.0,50100.0,50700.0,1800
...
```

#### Report Features:

- **Performance Metrics**: Win rate, profit factor, Sharpe ratio
- **Risk Metrics**: Maximum drawdown, average trade duration
- **Interactive Charts**: Equity curve, drawdown, P&L distribution
- **Trade History**: Detailed trade-by-trade analysis
- **Configuration Summary**: All backtest parameters

#### Signal Rules:

**BUY Signals:**
- Price above SMA 20 and SMA 50
- RSI between 30 and 70
- MACD above signal line (bullish crossover)

**SELL Signals:**
- Price below SMA 20 and SMA 50
- RSI above 70 or below 30
- MACD below signal line (bearish crossover)

### 3. Interactive Brokers (IBKR) Integration

The AI Trading Agent now includes a comprehensive IBKR adapter with paper-compatible interface:

#### Features:
- **Environment Gating**: Only enabled when `BROKER=ibkr`
- **Stub Mode**: Logs trading intents when no credentials provided
- **Health Monitoring**: Dedicated health check endpoints
- **Paper-Compatible**: Same interface as paper broker
- **Graceful Degradation**: Falls back to paper broker when disabled

#### Configuration:

```bash
# Enable IBKR broker
export BROKER=ibkr

# IBKR connection settings
export IBKR_HOST=127.0.0.1
export IBKR_PORT=7497
export IBKR_CLIENT_ID=1
export IBKR_ACCOUNT=DU123456  # Required for full functionality
```

#### Usage:

```bash
# Check IBKR broker health
curl http://localhost:9001/v1/broker/ibkr/health

# Check all broker health
curl http://localhost:9001/v1/broker/health

# Enable IBKR and start server
BROKER=ibkr uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload
```

#### Health Check Response:

```json
{
  "status": "healthy",
  "message": "IBKR broker is connected and authenticated",
  "broker": "ibkr",
  "enabled": true,
  "connected": true,
  "authenticated": true,
  "credentials_provided": true,
  "host": "127.0.0.1",
  "port": 7497,
  "client_id": 1,
  "account": "DU123456",
  "orders_count": 0,
  "positions_count": 0
}
```

#### Stub Mode:

When `BROKER=ibkr` but no credentials are provided:
- Adapter logs trading intents instead of executing
- Orders marked as `PENDING` status
- Useful for testing trading logic without live connection

#### Implementation Status:

- ✅ **Environment Gating**: Only active when `BROKER=ibkr`
- ✅ **Health Checks**: Dedicated endpoints for monitoring
- ✅ **Stub Methods**: Logs intents when no credentials
- ✅ **Paper-Compatible**: Same interface as paper broker
- ✅ **Error Handling**: Graceful fallbacks and error messages
- 🔄 **Full Integration**: Ready for IBKR API integration

### 4. JWT Authentication

The AI Trading Agent now includes comprehensive JWT-based authentication for securing write endpoints:

#### Features:
- **JWT Validation**: HS256 algorithm with configurable secret
- **Token Validation**: Expiration, not-before, audience, and issuer validation
- **Endpoint Protection**: Write operations require authentication
- **User Context**: Extracted user information available in endpoints
- **Security**: Proper error handling and logging

#### Configuration:

```bash
# JWT settings (add to .env)
export JWT_SECRET="your-secret-key-change-in-production"
export JWT_ALGORITHM="HS256"
export JWT_AUDIENCE="ai-trading-agent"
export JWT_ISSUER="ai-trading-agent"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Token Creation:

```bash
# Create a JWT token
python scripts/create_jwt_token.py trader1 --roles trader admin --expires 60

# Create token with custom user ID
python scripts/create_jwt_token.py alice --user-id user-123 --roles trader

# Save token to file
python scripts/create_jwt_token.py bob --output token.txt
```

#### Protected Endpoints:

**Orders:**
- `POST /v1/orders/` - Create order (requires auth)
- `DELETE /v1/orders/{order_id}` - Cancel order (requires auth)

**Configuration:**
- `PUT /v1/config/` - Update configuration (requires auth)

**Model Control:**
- `POST /v1/model/reload` - Reload model (requires auth)
- `PUT /v1/model/threshold` - Update threshold (requires auth)
- `POST /v1/model/promote` - Promote model (requires auth)

#### Usage Examples:

```bash
# Get a token
TOKEN=$(python scripts/create_jwt_token.py trader1)

# Make authenticated requests
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:9001/v1/orders/ \
     -d '{"symbol": "AAPL", "side": "BUY", "quantity": 100, "order_type": "MARKET"}'

# Update configuration
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X PUT http://localhost:9001/v1/config/ \
     -d '{"session_windows": {"start": "09:30", "end": "16:00"}}'

# Reload model
curl -H "Authorization: Bearer $TOKEN" \
     -X POST http://localhost:9001/v1/model/reload
```

#### Token Structure:

```json
{
  "sub": "trader1",
  "username": "trader1", 
  "roles": ["trader", "admin"],
  "iat": 1696368000,
  "exp": 1696369800,
  "nbf": 1696368000,
  "aud": "ai-trading-agent",
  "iss": "ai-trading-agent"
}
```

#### Security Notes:

- **Change Default Secret**: Update `JWT_SECRET` in production
- **Token Expiration**: Tokens expire after 30 minutes by default
- **Role-Based Access**: User roles available in endpoint context
- **Audit Logging**: All authentication events are logged
- **Error Handling**: Proper HTTP status codes for auth failures

### 5. Enhanced Makefile Targets

The AI Trading Agent now includes comprehensive Makefile targets for system management and monitoring:

#### **System Validation:**
```bash
# Complete system check (recommended for production readiness)
make full-check
# Runs: reset -> health -> routes -> smoke -> dataset -> train -> model-status

# Smoke tests (quick validation)
make smoke
# Runs: open-trading + test-order + test-logs
```

#### **Log Monitoring:**
```bash
# Monitor API server logs
make logs-api
# Tails logs/api.log or logs/app.log

# Monitor Streamlit UI logs  
make logs-ui
# Tails logs/ui.log or logs/streamlit.log
```

#### **Individual Components:**
```bash
# System health
make health          # Check API health status
make routes          # List all API routes

# Testing
make open-trading    # Open trading hours for testing
make test-order      # Test paper order placement
make test-logs       # Test trade logs endpoints

# Data & ML
make dataset         # Build dataset from trade logs
make train           # Train baseline model
make model-status    # Check model status and metrics

# Training with Backfill Support
make train-with-backfill      # Train with backfill data (weighted at 0.5)
make train-exclude-backfill   # Train excluding backfill data
make train-heavy-backfill-weight # Train with heavy backfill weighting (0.1)
make dataset-with-backfill    # Build dataset with backfill data
make dataset-exclude-backfill # Build dataset excluding backfill data

# System management
make reset           # Complete system reset
make cleanup-ports   # Kill processes on ports 9001, 9012, 9014
```

#### **Full System Check Workflow:**

The `make full-check` target provides a comprehensive validation sequence:

1. **System Reset** - Clean slate with fresh database
2. **Health Check** - Verify API endpoints are responding
3. **Routes Check** - Confirm all API routes are available
4. **Smoke Tests** - Validate core trading functionality
5. **Dataset Building** - Process trade logs into training data
6. **Model Training** - Train ML model with latest data
7. **Model Status** - Verify model is ready for production

This ensures the entire system is operational and ready for live trading.

### 6. Add VectorBT Integration
```python
# For advanced backtesting and analysis
pip install vectorbt
# Integrate with engines/backtest/run.py
```

### 2. Add Optuna for Hyperparameter Optimization
```python
# For strategy optimization
pip install optuna
# Integrate with app/services/optimization.py
```

### 3. Add Supervised PyTorch Model
```python
# For ML-based trading signals
pip install torch torchvision
# Create app/models/ml_model.py
```

### 4. Configure Broker Credentials
```bash
# For live trading (when ready)
# Update .env with real broker credentials
TRADOVATE_API_KEY=your-real-api-key
TRADOVATE_SECRET=your-real-secret
IBKR_ACCOUNT=your-real-account
```

### 5. Production Deployment
```bash
# Docker deployment
docker-compose -f docker-compose.prod.yml up

# Kubernetes deployment
kubectl apply -f k8s/
```

## 🧪 Development

### Code Quality
```bash
# Format code
make format

# Lint code
make lint

# Type checking
mypy app/
```

### Testing
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific tests
pytest tests/test_risk.py -v
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
make pre-commit-install

# Run manually
make pre-commit-run
```

## 📚 Documentation

- **API Docs**: http://localhost:9001/docs (Swagger UI)
- **ReDoc**: http://localhost:9001/redoc
- **OpenAPI Spec**: http://localhost:9001/openapi.json

## 🔧 Stabilization Checklist

Use this checklist to verify the system is working correctly after setup or after making changes.

### Prerequisites
- API server running on port 9001
- Database accessible
- All dependencies installed

### Step-by-Step Verification

#### 1. System Reset
```bash
# Clean reset to ensure fresh state
make reset
```
**Expected**: System stops, database resets, services restart cleanly

#### 1.5. Environment Selection (Optional)
```bash
# Development environment (recommended for testing)
make run-dev

# Production environment (for production-like testing)
make run-prod
```
**Expected**: Server starts with appropriate configuration for the environment

#### 2. Health & Routes Check
```bash
# Verify API is healthy and routes are registered
make health
make routes
```
**Expected**: 
- Health returns `{"status": "healthy", ...}`
- Routes shows all available endpoints

#### 3. Trading Functionality
```bash
# Place a test paper order
make test-order
```
**Expected**: Order placed successfully, fill simulated, order response shows status

#### 4. Logs & Export Verification
```bash
# Test trade logs and CSV export
make test-logs
```
**Expected**: Both endpoints return 200 status, CSV contains proper headers

#### 5. Machine Learning Pipeline
```bash
# Build dataset and train model
make dataset
make train
```
**Expected**: Dataset builds successfully, model training completes without errors

#### 6. Model Status Check
```bash
# Verify model status and metrics
make model-status
```
**Expected**: Model status shows loaded model, metrics, and configuration

### Success Criteria

✅ **Clean Database**: Fresh schema, no stale data  
✅ **Single Server**: Only one process on port 9001  
✅ **Endpoints Healthy**: All API endpoints responding correctly  
✅ **Trading Working**: Orders can be placed and filled  
✅ **ML Pipeline Working**: Dataset builds, model trains, status accessible  

### Troubleshooting

If any step fails:

1. **Port Conflicts**: Run `make cleanup-ports` to free up ports
2. **Database Issues**: Run `make db-clean` to reset database
3. **API Not Responding**: Check if server is running with `make health`
4. **Model Issues**: Verify model files exist in `models/` directory
5. **Trading Hours**: Run `make open-trading` to enable 24/7 trading for testing

### Quick Verification Commands

```bash
# Full system check (run in sequence)
make reset && \
make health && \
make routes && \
make test-order && \
make test-logs && \
make dataset && \
make train && \
make model-status

echo "✅ System stabilization complete!"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always test thoroughly with paper trading before using real money.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: README and inline code comments
- **API Docs**: http://localhost:8000/docs

---

**Happy Trading! 🚀📈**
