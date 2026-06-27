# Full System Testing Guide

## Overview

The trading AI pipeline has been fully integrated with automatic startup capabilities for:
1. **Ollama** (Local AI) - auto-discovery, launch, model pulling
2. **MetaTrader 5** - auto-launch and connection
3. **AI Agents** - automatic initialization and communication
4. **Configuration** - automatic loading and validation

## Prerequisites

```bash
# 1. Install Ollama (one-time)
# Download from https://ollama.ai
# Windows: Run installer
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# 2. Install Python dependencies in your venv
pip install pyyaml httpx pydantic python-dotenv MetaTrader5

# 3. Install the package
cd /path/to/metatrader-mcp-server
pip install -e .
```

## Quick System Check

Run the full integration test:

```bash
python tests/test_full_integration.py
```

Expected output:
```
================================================================
  TRADING AI PIPELINE - FULL INTEGRATION TEST
================================================================

TEST 1: Ollama Auto-Discovery & Health Check
[✓] Ollama Discovery: PASS
[✓] Ollama Running: PASS or INFO (auto-launches)

TEST 2: Model Management & Auto-Pull
[✓] List Models: PASS
[✓] Model Available: PASS

TEST 3: Configuration Loading
[✓] Load YAML: PASS

TEST 4: AI Agent Initialization
[✓] Agent Config: PASS
[✓] Initialize TechnicalAgent: PASS
[✓] Initialize PriceActionAgent: PASS
[✓] Initialize SmartMoneyAgent: PASS

TEST 5: AI Communication (Mock Test)
[✓] AI Communication: PASS or INFO (if Ollama is running)

TEST 6: MT5 Auto-Launch & Connectivity
[✓] Find MT5: PASS or INFO
[✓] MT5 Running: PASS or INFO (auto-launches)

TEST 7: System Readiness Check
[✓] Ollama Manager: PASS
[✓] MT5 Manager: PASS
[✓] Config System: PASS
[✓] Pipeline Runner: PASS
[✓] AI Agents: PASS

================================================================
  TEST SUMMARY
================================================================

Total: 7/7 test groups passed

🎯 All systems operational - ready for trading!
================================================================
```

## Running the System

### Option 1: PowerShell (Windows)

```powershell
# Automatic everything
.\run.ps1 -Mode pipeline
```

**What happens automatically:**
1. Ollama is discovered or launched
2. Model `qwen2.5:14b` is pulled if missing
3. MT5 terminal is launched if closed
4. MT5 connection is established
5. Trading analysis loop starts

### Option 2: Bash (Linux/macOS)

```bash
./run.sh pipeline
```

### Option 3: Direct Python

```bash
python -m trading_ai_pipeline.pipeline.runner --config config/pipeline.yaml
```

## Monitoring the Pipeline

Watch the live output:

```bash
# Windows PowerShell
Get-Content logs/pipeline/*.jsonl -Wait

# Linux/Mac
tail -f logs/pipeline/*.jsonl
```

## Test Scenarios

### Scenario 1: Ollama Not Installed
```
[*] Checking Ollama availability...
[!] Ollama executable not found
[!] Please install Ollama from https://ollama.ai
```
**Fix:** Install Ollama and restart

### Scenario 2: Ollama Running, Model Missing
```
[*] Checking Ollama availability...
[+] Ollama is running
[*] Checking model qwen2.5:14b...
[*] Auto-pulling model (this takes 3-5 minutes)...
[+] Model qwen2.5:14b ready
```
**Fix:** System auto-pulls the model (wait 5 minutes)

### Scenario 3: MT5 Not Running
```
[*] Connecting to MT5...
[*] MT5 terminal not found, auto-launching...
[+] MT5 launching (this takes 30-60 seconds)
[+] Connected to MetaTrader 5
```
**Fix:** System auto-launches MT5

### Scenario 4: Everything Running
```
[+] Ollama is running
[+] Model qwen2.5:14b is available
[+] Connected to MetaTrader 5
[*] Pipeline runner started [DRY-RUN]
[+] Analysis cycle 1: EURUSD H1 → NO_TRADE (3.2s)
[+] Analysis cycle 2: EURUSD H1 → BUY signal (confidence: 0.78)
[+] Analysis cycle 3: EURUSD H1 → NO_TRADE (2.8s)
...
```
**Status:** ✅ Everything working!

## Troubleshooting

### "Ollama process failed to start"
- Check Windows Task Manager - is `ollama.exe` running?
- Try manually: `ollama serve`
- Check disk space: Ollama needs 10GB+ for models

### "Model pull timed out"
- Internet connection issue
- Model server busy
- Manually pull: `ollama pull qwen2.5:14b`

### "MT5 connection failed"
- Is MT5 running?
- Check credentials in `.env`
- Try manually launching: `C:\Program Files\MetaTrader 5\terminal.exe`

### "No trades generated"
- Dry-run mode: Check the settings
- Check logs: `logs/pipeline/latest.jsonl`
- Market might be in consolidation (NO_TRADE is correct)

## Configuration Customization

Edit `config/pipeline.yaml`:

```yaml
# AI Provider
ai:
  provider: "ollama"  # or: openai, anthropic, deepseek
  model: "qwen2.5:14b"
  auto_launch: true
  auto_pull_model: true

# MT5
mt5:
  login: 12345678
  password: "your_password"
  server: "MetaQuotes-Demo"
  auto_launch: true

# Trading
dry_run: true  # false = real trades
symbols:
  - EURUSD
  - GBPUSD
timeframes:
  - H1
  - H4

# Risk Management
risk:
  max_daily_loss_percent: 2.0
  max_position_size_lots: 1.0
  min_rr_ratio: 2.0
```

## Expected Timeline

**First Run:**
- Ollama install: 10 minutes
- Model download: 5 minutes
- MT5 launch: 60 seconds
- First analysis: 30 seconds
- **Total:** ~20 minutes

**Subsequent Runs:**
- Ollama already running: instant
- Model cached: instant
- MT5 already running: instant
- Analysis cycle: 3-5 seconds per symbol
- **Total:** Immediate

## System Architecture

```
User runs: .\run.ps1 -Mode pipeline
    ↓
PipelineRunner.main()
    ├─ ensure_ollama_running()
    │   ├─ Find ollama.exe in standard paths
    │   ├─ Health check (HTTP)
    │   └─ Auto-launch if needed
    │
    ├─ ensure_model_available()
    │   ├─ List available models
    │   └─ Auto-pull if needed
    │
    ├─ ensure_mt5_running()
    │   ├─ Find terminal.exe in standard paths
    │   ├─ Process check
    │   └─ Auto-launch if needed
    │
    └─ PipelineOrchestrator.run() [loop every hour]
        ├─ Step 1: MarketDataCollector
        ├─ Step 2-4: Python Indicators (EMA, RSI, MACD, ATR, ADX, BB, VWAP)
        ├─ Step 5: TechnicalAgent (AI)
        ├─ Step 6: PriceActionAgent (AI)
        ├─ Step 7: SmartMoneyAgent (AI)
        ├─ Step 8: ConsensusBuilder
        ├─ Step 9: ReviewerAgent (AI - devil's advocate)
        ├─ Step 10: ProbabilityEstimator (AI)
        ├─ Step 11: RiskManager
        ├─ Step 12: RuleValidator
        ├─ Step 13: TradeExecutor (MT5 API)
        └─ Step 14: Logging & Memory
```

## System Status Dashboard

Create a status script:

```bash
# Windows
@echo off
echo [*] Checking system status...
tasklist | find /i "ollama.exe" >nul && echo [+] Ollama running || echo [-] Ollama stopped
tasklist | find /i "terminal.exe" >nul && echo [+] MT5 running || echo [-] MT5 stopped
echo [*] Latest analysis:
powershell -Command "Get-Content logs/pipeline/*.jsonl -Tail 1"
```

## Next Steps

1. ✅ Install Ollama (`https://ollama.ai`)
2. ✅ Run integration test (`python tests/test_full_integration.py`)
3. ✅ Copy config example (`cp config/pipeline.yaml.example config/pipeline.yaml`)
4. ✅ Edit config with your MT5 credentials
5. ✅ Run pipeline (`.\run.ps1 -Mode pipeline`)
6. ✅ Monitor logs (tail or Get-Content)

**All done! System should be fully operational.** 🚀
