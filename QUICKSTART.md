# MetaTrader MCP Server + AI Trading Pipeline — Quick Start

## Option 1: Run MCP Server (for Claude Desktop / ChatGPT integration)

### Setup
```bash
# Install dependencies
pip install -e .

# Create .env file with your MT5 credentials
cat > .env << EOF
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo
MT5_PATH=C:\Program Files\MetaTrader 5\terminal.exe
EOF
```

### Run
```bash
metatrader-mcp-server \
  --login 12345678 \
  --password your_password \
  --server MetaQuotes-Demo
```

**Output:** Server starts on `http://localhost:8080` (SSE transport)  
Use in Claude Desktop: Add MCP server endpoint to config.

---

## Option 2: Run AI Trading Pipeline (Automated Trading System)

### Setup
```bash
# Install pipeline dependencies
pip install pydantic pyyaml anthropic ollama requests pandas numpy

# Create config/pipeline.yaml
cat > config/pipeline.yaml << 'EOF'
# AI Provider
ai_provider: "ollama"  # or: openai, anthropic, deepseek, qwen
ai_model: "qwen:7b"

# MT5 Connection (auto-launches if needed)
mt5_login: 12345678
mt5_password: "your_password"
mt5_server: "MetaQuotes-Demo"
auto_launch: true  # Auto-start MT5 if closed

# Trading Mode
dry_run: true  # true = no real orders; false = live trading

# Risk Management
max_daily_loss_percent: 2.0
max_position_size_percent: 1.0
min_rr_ratio: 2.0

# AI Agents
technical_confidence_threshold: 0.6
price_action_confidence_threshold: 0.6
smart_money_confidence_threshold: 0.6
consensus_threshold: 0.65
EOF
```

### Run Single Analysis
```bash
python << 'EOF'
import asyncio
from src.trading_ai_pipeline.pipeline.orchestrator import PipelineOrchestrator
from src.trading_ai_pipeline.core.config.settings import PipelineConfig

async def run_single_analysis():
    config = PipelineConfig.load_from_yaml('config/pipeline.yaml')
    orchestrator = PipelineOrchestrator(config)
    result = await orchestrator.run(
        symbol='EURUSD',
        timeframe='H1',
        run_id='test_001'
    )
    print(result)

asyncio.run(run_single_analysis())
EOF
```

### Run Continuous Trading (Recommended)
```bash
python -m trading_ai_pipeline.pipeline.runner \
  --config config/pipeline.yaml \
  --symbol EURUSD \
  --timeframe H1 \
  --interval 3600  # Run every hour
```

---

## Option 3: Run Both (MCP Server + Trading Pipeline)

### Terminal 1: MCP Server
```bash
metatrader-mcp-server \
  --login 12345678 \
  --password your_password \
  --server MetaQuotes-Demo
```

### Terminal 2: Trading Pipeline
```bash
python -m trading_ai_pipeline.pipeline.runner \
  --config config/pipeline.yaml \
  --symbol EURUSD \
  --timeframe H1
```

---

## Available Commands

### MCP Server Commands
```bash
# SSE transport (default)
metatrader-mcp-server --login 12345678 --password pwd --server demo

# Stdio transport (Claude Desktop)
metatrader-mcp-server --login 12345678 --password pwd --server demo --transport stdio

# Custom host/port
metatrader-mcp-server --login 12345678 --password pwd --server demo --host 127.0.0.1 --port 9000

# HTTP API Server (separate)
metatrader-http-server --login 12345678 --password pwd --server demo

# Real-time Quote WebSocket (separate)
metatrader-quote-server --login 12345678 --password pwd --server demo
```

### Trading Pipeline Commands
```bash
# Dry-run mode (test without real trades)
python -m trading_ai_pipeline.pipeline.runner \
  --config config/pipeline.yaml \
  --symbol EURUSD \
  --timeframe H1 \
  --dry-run

# Live trading
python -m trading_ai_pipeline.pipeline.runner \
  --config config/pipeline.yaml \
  --symbol EURUSD \
  --timeframe H1 \
  --live

# Custom interval (minutes)
python -m trading_ai_pipeline.pipeline.runner \
  --config config/pipeline.yaml \
  --symbol EURUSD \
  --timeframe H1 \
  --interval 1800  # Every 30 minutes
```

---

## Troubleshooting

### MT5 Auto-Launch Not Working
```yaml
# Disable auto-launch and start MT5 manually
auto_launch: false

# Or specify exact MT5 path
mt5_path: "C:\\Program Files\\MetaTrader 5\\terminal.exe"
```

### AI Provider Connection Failed
```bash
# For Ollama: Start local server
ollama serve

# For OpenAI: Set API key
export OPENAI_API_KEY="sk-..."

# For Anthropic (Claude): Set API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### No Trades Generated
Check logs:
```bash
cat logs/pipeline/latest.jsonl
tail -f logs/trade_memory.jsonl
```

---

## File Structure

```
.
├── config/
│   └── pipeline.yaml          # Main configuration
├── src/
│   ├── metatrader_client/     # MT5 connection layer
│   ├── metatrader_mcp/        # MCP server
│   └── trading_ai_pipeline/   # AI trading system
│       ├── data/              # Market data collectors & indicators
│       ├── agents/            # AI agents (Technical, PA, SMC)
│       ├── pipeline/          # Orchestrator & runner
│       └── ...
├── logs/
│   ├── pipeline/              # Per-run JSONL logs
│   └── trade_memory.jsonl     # Trade history & statistics
└── docs/
    ├── MT5_AUTO_LAUNCH.md
    └── ...
```

---

## Next Steps

1. **Dry-Run Phase** (1-2 weeks)
   - Set `dry_run: true` in config
   - Monitor logs and statistics
   - Tune AI confidence thresholds

2. **Live Trading** (after validation)
   - Set `dry_run: false`
   - Start with small position sizes
   - Monitor daily losses

3. **Optimization**
   - Adjust risk parameters
   - Backtest on historical data
   - Add more symbols/timeframes

