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

### Prerequisites (One-Time)
```bash
# 1. Install Ollama from https://ollama.ai
# That's it! No manual configuration needed.

# Verify installation
ollama --version
```

### Setup (Fully Automatic)
```bash
# Install pipeline dependencies
pip install -e .

# Copy example configuration
cp config/pipeline.yaml.example config/pipeline.yaml

# Edit with your MT5 credentials only (everything else is automatic)
cat > config/pipeline.yaml << 'EOF'
mt5:
  login: 12345678
  password: "your_password"
  server: "MetaQuotes-Demo"

ai:
  provider: "ollama"  # Automatic: discovers, launches, and pulls model
  model: "qwen2.5:14b"
  auto_launch: true   # Automatically starts Ollama if closed
  auto_pull_model: true  # Automatically downloads model if missing

dry_run: true  # true = no real orders; false = live trading
EOF
```

**That's all. Everything else happens automatically:**
- ✅ Ollama is detected/launched
- ✅ Model is downloaded if needed
- ✅ MT5 is launched if closed
- ✅ Trading pipeline starts

### Run (Everything Automatic)

**Windows:**
```powershell
.\run.ps1 -Mode pipeline
```

**Linux/Mac:**
```bash
./run.sh pipeline
```

**What happens automatically:**
1. System checks if Ollama is running
2. If not, launches Ollama automatically
3. If model not found, downloads it automatically
4. Checks if MT5 is running
5. If not, launches MT5 automatically
6. Connects and starts trading analysis loop

**Output:**
```
[*] Checking Ollama availability...
[+] Ollama is running
[+] Model qwen2.5:14b is available
[*] Connecting to MT5...
[+] Connected to MT5 account
[*] Pipeline runner started [DRY-RUN]
[+] Analysis cycle 1: EURUSD H1 - NO_TRADE (3.2s)
[+] Analysis cycle 2: EURUSD H1 - BUY signal (confidence: 0.78)
...
```

No IP addresses, no manual setup. Just run and it works.

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

## Quick Commands

```bash
# Run Trading Pipeline (automatic Ollama + MT5)
.\run.ps1 -Mode pipeline

# Run MCP Server (for Claude Desktop)
.\run.ps1 -Mode mcp

# Run Both simultaneously
.\run.ps1 -Mode both

# Check Ollama models
ollama list

# Download a model
ollama pull mistral
ollama pull llama2

# Manual Ollama start (if auto-launch disabled)
ollama serve
```

---

## Troubleshooting

### "Ollama executable not found"
1. Download Ollama from https://ollama.ai
2. Install it
3. Restart terminal/PowerShell
4. Try again

### "Ollama did not become responsive"
1. Check if Ollama is already running: `ollama list`
2. If frozen, restart: Kill `ollama.exe` and try again
3. Check disk space: `ollama` needs 5GB+ for models

### "Model not found"
Auto-pull should handle it, but you can manually:
```bash
ollama pull qwen2.5:14b
```

### "No trades are being generated"
Check the analysis logs:
```bash
# Live logs (Windows)
Get-Content logs/pipeline/*.jsonl -Wait

# Or check latest analysis
cat logs/pipeline/latest.jsonl | Select-String "confidence"
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

