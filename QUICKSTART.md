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

## Option 2: Run AI Trading Pipeline (100% FREE AI - Automated Trading System)

### Choose Your FREE AI Provider (Pick ONE)

#### Option 2A: Ollama (Recommended - LOCAL & 100% FREE)
```bash
# 1. Download: https://ollama.ai
# 2. Install and run:
ollama serve

# That's it! System auto-detects. No setup needed.
```

#### Option 2B: Groq (FREE Cloud - 30k tokens/min)
```bash
# 1. Signup: https://console.groq.com (no credit card)
# 2. Get API key
# 3. Set environment variable:
export GROQ_API_KEY="gsk_xxx"

# Or add to .env
echo "GROQ_API_KEY=gsk_xxx" >> .env
```

#### Option 2C: OpenRouter (FREE Cloud - $5 Credit, 200+ Models)
```bash
# 1. Signup: https://openrouter.ai (no credit card)
# 2. Get API key from dashboard
# 3. Set environment variable:
export OPENROUTER_API_KEY="sk-or-xxx"

# Or add to .env
echo "OPENROUTER_API_KEY=sk-or-xxx" >> .env
```

### Setup (5 minutes - Fully Automatic)
```bash
# 1. Install dependencies
pip install -e .

# 2. Copy example configuration
cp config/pipeline.yaml.example config/pipeline.yaml

# 3. Edit with your MT5 credentials ONLY (everything else is automatic)
cat > config/pipeline.yaml << 'EOF'
mt5:
  login: 12345678
  password: "your_password"
  server: "MetaQuotes-Demo"

dry_run: true  # true = paper trade; false = live
EOF
```

**That's all. Everything else happens automatically:**
- ✅ FREE AI provider detected/launched
- ✅ MT5 auto-launched if closed
- ✅ Trading pipeline starts

### Run (Everything Automatic - 100% FREE)

**Windows:**
```powershell
.\run.ps1 -Mode pipeline
```

**Linux/Mac:**
```bash
./run.sh pipeline
```

**What happens automatically:**
1. System detects available FREE AI providers (Ollama, Groq, OpenRouter, HF)
2. Launches Ollama if you're using local (and it's installed)
3. Verifies API keys for cloud providers
4. Selects best provider (prefers local Ollama first)
5. Launches MT5 if closed
6. Starts trading analysis loop

**Output:**
```
======================================================================
AUTOMATED FREE AI PROVIDER DETECTION & SETUP
======================================================================

[+] Successfully initialized 1 FREE provider(s):
    ✓ ollama

[+] Primary provider: OLLAMA

[*] Setting up MetaTrader 5 connection...
[+] Connected to MT5

======================================================================
STARTING TRADING PIPELINE (FREE AI MODE)
======================================================================
```

**Cost: $0 - Completely FREE**

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

### "No FREE AI providers found"
Choose one and setup (5 min):
- **Ollama:** https://ollama.ai (then `ollama serve`)
- **Groq:** https://console.groq.com (then `export GROQ_API_KEY=...`)
- **OpenRouter:** https://openrouter.ai (then `export OPENROUTER_API_KEY=...`)

### Ollama not detected
```bash
# Check if running
ollama list

# If not running, start it
ollama serve

# Wait 5 seconds for system to detect
```

### API key not working
```bash
# Check it's set
echo $GROQ_API_KEY  # Should print your key

# Verify format (Groq starts with gsk_)
# Get new key: https://console.groq.com/keys
```

### "No trades are being generated"
Check logs:
```bash
# Windows
Get-Content logs/pipeline/*.jsonl -Wait

# Linux/Mac
tail -f logs/pipeline/*.jsonl
```

## More Help

See [FREE_AI_PROVIDERS.md](../docs/FREE_AI_PROVIDERS.md) for detailed provider setup and comparison.

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

