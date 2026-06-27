# MetaTrader MCP Server + AI Trading Pipeline

Professional-grade multi-agent AI trading system for MetaTrader 5. Choose between MCP integration (Claude Desktop, ChatGPT) or autonomous trading with the AI pipeline.

## Quick Start (Fully Automatic - No Configuration Needed)

### Prerequisites (One-Time)
1. **Install Ollama** from https://ollama.ai (5 min)
2. **Install dependencies**: `pip install pyyaml httpx pydantic python-dotenv MetaTrader5`
3. **Install project**: `pip install -e .`

### Run (Everything Auto-Launches)

**Windows:**
```powershell
# Copy config template and edit with your MT5 credentials
cp config/pipeline.yaml.example config/pipeline.yaml
# nano config/pipeline.yaml
#   mt5.login: YOUR_LOGIN
#   mt5.password: YOUR_PASSWORD
#   mt5.server: MetaQuotes-Demo

# Run (Ollama & MT5 auto-launch, model auto-pulled)
.\run.ps1 -Mode pipeline
```

**Linux/Mac:**
```bash
cp config/pipeline.yaml.example config/pipeline.yaml
# Edit config with your MT5 credentials
./run.sh pipeline
```

### What Happens Automatically
✅ System finds or launches Ollama  
✅ Model `qwen2.5:14b` is downloaded if needed  
✅ MetaTrader 5 terminal launches if closed  
✅ MT5 connection established  
✅ Trading analysis starts (hourly)  

**Output:**
```
[*] Checking Ollama availability...
[+] Ollama is running
[+] Model qwen2.5:14b is available
[*] Connecting to MT5...
[+] Connected to MetaTrader 5 (balance: $10,000)
[*] Pipeline started [DRY-RUN]
[+] EURUSD H1 analysis: NO_TRADE
[+] GBPUSD H1 analysis: BUY (confidence: 0.78)
```

**Total setup time: ~20 minutes (first run), instant (after that)**

See [TESTING.md](TESTING.md) to verify system, [QUICKSTART.md](QUICKSTART.md) for troubleshooting.

## Features

**Fully Automatic:**
- **Ollama Auto-Discovery & Launch**: Finds and launches local AI automatically
- **Model Auto-Pull**: Downloads required AI models without user intervention
- **MT5 Auto-Launch**: Opens MetaTrader 5 if closed
- **Zero Configuration**: Just set MT5 credentials, everything else is automatic

**Trading Intelligence:**
- **3 AI Analysts**: Technical, Price Action, Smart Money (multi-perspective analysis)
- **Python Indicators**: EMA, RSI, MACD, ATR, ADX, Bollinger Bands, VWAP (no AI involved)
- **Consensus Engine**: Weighted voting between 3 analysts
- **Devil's Advocate**: AI reviewer checks for risks before trading

**Risk Management:**
- **ATR-Based Stops**: Dynamic stop loss based on volatility
- **Position Sizing**: Kelly criterion + fixed % sizing
- **Risk/Reward Validation**: 2:1 minimum ratio
- **Daily Loss Limit**: Stops trading if max loss reached

**Production Ready:**
- **Dry-Run Mode**: Paper trade before going live
- **Structured Logging**: JSON audit trail of every decision
- **Trade Memory**: Win-rate tracking, agent performance metrics
- **Flexible AI**: Ollama (local), OpenAI, Anthropic, DeepSeek, Qwen
- **11-Step Pipeline**: Market data → AI analysis → Risk check → Execution → Logging

## System Verification

Check if everything is working:

```bash
# Run integration test (tests all components)
python tests/test_full_integration.py
```

Expected output if all systems operational:
```
TEST 1: Ollama Auto-Discovery & Health Check ✓
TEST 2: Model Management & Auto-Pull ✓
TEST 3: Configuration Loading ✓
TEST 4: AI Agent Initialization ✓
TEST 5: AI Communication ✓
TEST 6: MT5 Auto-Launch & Connectivity ✓
TEST 7: System Readiness Check ✓

Total: 7/7 test groups passed
🎯 All systems operational - ready for trading!
```

See [TESTING.md](TESTING.md) for detailed diagnostics and troubleshooting.

## 11-Step Pipeline Architecture

```
Market Data (MT5)
    ↓
1. Market Data Collector (Python)
    ↓
2-4. Python Indicators (EMA, RSI, MACD, ATR, ADX, BB, VWAP)
    ↓
5. Technical Analyst (AI) → trend, confidence, indicator summary
6. Price Action Analyst (AI) → support/resistance, patterns, breakouts
7. Smart Money Analyst (AI) → BOS, CHoCH, FVG, order blocks
    ↓
8. Consensus Builder (Python) → weighted vote, final direction
9. Reviewer (AI) → devil's advocate, risk check, veto if needed
10. Probability Estimator (AI) → final Buy/Sell/No-Trade odds
    ↓
11. Risk Manager (Python) → SL, TP, position size, spread check
12. Rule Validator (Python) → hard rules gate (time, news, etc)
    ↓
13. Trade Executor (MT5 API) → place order (if approved)
14. Logger & Memory → JSON audit trail + statistics
```

## Running Both Systems Simultaneously

```bash
# Terminal 1: MCP Server (for Claude Desktop / ChatGPT)
.\run.ps1 -Mode mcp

# Terminal 2: Trading Pipeline (autonomous)
.\run.ps1 -Mode pipeline
```

Both systems share MT5 connection and run independently. Can trade autonomously while also accepting commands from Claude/ChatGPT via MCP.
