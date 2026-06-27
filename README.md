# MetaTrader MCP Server + AI Trading Pipeline

Professional-grade multi-agent AI trading system for MetaTrader 5. Choose between MCP integration (Claude Desktop, ChatGPT) or autonomous trading with the AI pipeline.

## Quick Start (5 minutes)

### 1. Setup
```bash
# Install
pip install -e .

# Create credentials file
cp .env.example .env
# Edit .env with your MT5 login/password
```

### 2. Run MCP Server (for Claude Desktop / ChatGPT)
```bash
# Windows
.\run.ps1 -Mode mcp

# Linux/Mac
./run.sh mcp
```

### 3. Run AI Trading Pipeline (autonomous)
```bash
# Copy example config
cp config/pipeline.yaml.example config/pipeline.yaml
# Edit config/pipeline.yaml with your settings

# Windows
.\run.ps1 -Mode pipeline

# Linux/Mac
./run.sh pipeline
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup.**

## Features

- **MT5 Auto-Launch**: Automatically opens MetaTrader 5 if closed
- **Multi-Agent AI**: Technical, Price Action, Smart Money analyzers
- **Structured Analysis**: Python indicators + AI interpretation
- **Risk Management**: ATR-based stops, position sizing, daily loss limits
- **Dry-Run Mode**: Test without real trades
- **Structured Logging**: JSON audit trail of all decisions
- **Flexible AI**: Ollama (local), OpenAI, Anthropic, DeepSeek, Qwen

## Architecture

```
11-Step Trading Pipeline:
1. Market Data Collector (Python)
2. Technical Analyst (AI) → trend, EMA, RSI, MACD, ATR, ADX
3. Price Action Analyst (AI) → support, resistance, patterns, breakouts
4. Smart Money Analyst (AI) → BOS, CHoCH, FVG, order blocks, liquidity
5. Consensus Builder (Python) → weighted vote
6. Reviewer (AI) → devil's advocate, veto check
7. Probability Estimator (AI) → final Buy/Sell/No-Trade odds
8. Risk Manager (Python) → SL/TP, position size
9. Rule Validator (Python) → hard rules gate
10. Trade Executor (MT5 API) → place order
11. Logging & Memory → audit trail + statistics
```

## Running Both Systems

```bash
# Terminal 1: MCP Server
.\run.ps1 -Mode mcp

# Terminal 2: Trading Pipeline
.\run.ps1 -Mode pipeline
```

Both systems share MT5 connection and can run simultaneously.
