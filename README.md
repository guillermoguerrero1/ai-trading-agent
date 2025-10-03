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
# API available at http://localhost:8000

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
curl -s http://localhost:8000/v1/health
curl -s http://localhost:8000/v1/debug/config | jq
```

Place a paper bracket
```bash
curl -X POST http://localhost:8000/v1/orders \
 -H "Content-Type: application/json" \
 -d '{"symbol":"NQZ5","side":"SELL","qty":1,"entry":17895,"stop":17905,"target":17875,"paper":true}'
```

(If tick route exists) Push a price to drive fills
```bash
curl -X POST http://localhost:8000/v1/tick -H "Content-Type: application/json" \
 -d '{"symbol":"NQZ5","price":17894.75}'
```

## 📡 API Examples

### Health Check
```bash
curl http://localhost:8000/v1/health/
```

### Place Order
```bash
curl -X POST http://localhost:8000/v1/orders/ \
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
curl -X POST http://localhost:8000/v1/signal/ \
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
curl http://localhost:8000/v1/pnl/daily
```

### Get Configuration
```bash
curl http://localhost:8000/v1/config/
```

### Update Configuration
```bash
curl -X PUT http://localhost:8000/v1/config/ \
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
curl -s "http://localhost:8000/v1/logs/trades?limit=10" | jq
```

- Debug mounted routes:
```bash
curl -s http://localhost:8000/v1/debug/routes | jq
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

### Environment Variables
```bash
# Core settings
APP_ENV=dev
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

## 🚀 Next Steps

### 1. Add VectorBT Integration
```python
# For backtesting and analysis
pip install vectorbt
# Integrate with app/services/backtesting.py
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

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

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
