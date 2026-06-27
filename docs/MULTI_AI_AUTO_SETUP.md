# Multi-AI Auto-Setup (All 5 Providers)

System automatically detects and initializes all 5 AI providers without any manual configuration beyond setting environment variables for cloud APIs.

## Supported AI Providers (Auto-Detected)

| Provider | Type | Status | Setup |
|----------|------|--------|-------|
| **Ollama** | Local | Auto-launch | Install once, then automatic |
| **OpenAI** | Cloud | Auto-detect via API key | Set `OPENAI_API_KEY` environment variable |
| **Anthropic** | Cloud | Auto-detect via API key | Set `ANTHROPIC_API_KEY` environment variable |
| **DeepSeek** | Cloud | Auto-detect via API key | Set `DEEPSEEK_API_KEY` environment variable |
| **Qwen** | Cloud | Auto-detect via API key | Set `QWEN_API_KEY` environment variable |

## Automatic Startup Flow

When you run the system:

```
1. Read config file (only MT5 credentials needed)
   ↓
2. AUTO-DETECT ALL 5 PROVIDERS
   ├─ Check if Ollama is running → Launch if not
   ├─ Check if OpenAI API key is set → Verify connectivity
   ├─ Check if Anthropic API key is set → Verify connectivity
   ├─ Check if DeepSeek API key is set → Verify connectivity
   └─ Check if Qwen API key is set → Verify connectivity
   ↓
3. SELECT BEST PROVIDER
   ├─ Prefer Ollama (local = no rate limits, no costs)
   └─ Fallback to first available cloud API
   ↓
4. AUTO-SETUP OLLAMA (if selected)
   ├─ Launch if not running
   └─ Auto-pull model if missing
   ↓
5. AUTO-LAUNCH MT5
   ├─ Check if running → Launch if not
   ├─ Connect with credentials from config
   ↓
6. START TRADING PIPELINE
   └─ Begin hourly analysis cycles
```

## Example Startup Output

```
======================================================================
AUTOMATED AI PROVIDER DETECTION & SETUP
======================================================================

[*] Starting auto-detection of all 5 AI providers...
[+] ollama: READY
[+] openai: READY (API key found and validated)
[-] anthropic: Not available (API key not set)
[-] deepseek: Not available (API key not set)
[-] qwen: Not available (API key not set)

[+] Successfully initialized 2 AI provider(s):
    ✓ ollama
    ✓ openai

[+] Primary provider: OLLAMA
======================================================================

[*] Setting up MetaTrader 5 connection...
[+] MT5 auto-launch successful
[+] Connected to MetaTrader 5 (balance: $10,000)

======================================================================
STARTING TRADING PIPELINE
======================================================================

[*] Pipeline runner started [DRY-RUN]
[+] Analysis cycle 1: EURUSD H1 → NO_TRADE (0.52 confidence)
[+] Analysis cycle 2: GBPUSD H1 → BUY (0.78 confidence)
...
```

## Setup Options

### Option 1: Only Ollama (Recommended for Local Development)

```bash
# Install Ollama from https://ollama.ai
# That's it. No other setup needed.

# Run the system
.\run.ps1 -Mode pipeline

# System will:
# - Find Ollama (or launch it)
# - Pull model if needed
# - Launch MT5
# - Start trading
```

### Option 2: Ollama + Cloud Backup

```bash
# Install Ollama
# Setup API keys (choose one or more)

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Or Linux/Mac
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run the system
.\run.ps1 -Mode pipeline

# System will:
# - Auto-detect all available providers
# - Use Ollama (primary)
# - Fall back to OpenAI or Anthropic if Ollama fails
```

### Option 3: Cloud Only (No Ollama)

```bash
# Set at least one API key
export OPENAI_API_KEY="sk-..."

# Run the system
.\run.ps1 -Mode pipeline

# System will:
# - Skip Ollama (not available)
# - Use OpenAI (or next available cloud API)
# - Start trading
```

## Environment Variables

### Cloud API Keys

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."

# Qwen (Alibaba)
export QWEN_API_KEY="..."

# All together (permanent in .env file)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
QWEN_API_KEY=...
```

### Load from .env

The system automatically reads from `.env` file in project root:

```bash
# Copy and edit
cp .env.example .env

# Add your keys
nano .env

# Run
.\run.ps1 -Mode pipeline
```

## Provider Selection Priority

System chooses providers in this order:

1. **Ollama** (if running or can be launched)
   - No API keys needed
   - No rate limits
   - No costs
   - Best for production

2. **OpenAI** (if `OPENAI_API_KEY` is set)
   - Expensive
   - Rate limits
   - Excellent quality

3. **Anthropic** (if `ANTHROPIC_API_KEY` is set)
   - More expensive than OpenAI
   - Good for special use cases

4. **DeepSeek** (if `DEEPSEEK_API_KEY` is set)
   - Cost-effective alternative

5. **Qwen** (if `QWEN_API_KEY` is set)
   - Chinese alternative
   - Good performance-to-cost ratio

## Fallback Chain

If primary provider fails:

```
Try Primary (e.g., Ollama)
  ↓
If fails → Try Fallback 1 (OpenAI)
  ↓
If fails → Try Fallback 2 (Anthropic)
  ↓
If fails → Try Fallback 3 (DeepSeek)
  ↓
If fails → Try Fallback 4 (Qwen)
  ↓
If all fail → Stop with error message
```

## Switching Providers

To switch primary provider, change the order of availability:

```bash
# To force OpenAI (even if Ollama is available):
# Option 1: Stop/uninstall Ollama
# Option 2: Comment out/stop Ollama process
# Option 3: Edit runner.py _select_primary_provider() method
```

## Troubleshooting

### "No AI providers available"

```bash
# Make sure at least one is available:

# Option A: Install Ollama
https://ollama.ai

# Option B: Set at least one API key
export OPENAI_API_KEY="sk-..."

# Then run
.\run.ps1 -Mode pipeline
```

### "API key validation failed"

```bash
# Check your API key:
echo $OPENAI_API_KEY  # (Linux/Mac)
echo %OPENAI_API_KEY%  # (Windows)

# If empty, set it:
export OPENAI_API_KEY="sk-..."

# Then run again
.\run.ps1 -Mode pipeline
```

### "Ollama not found"

```bash
# Install Ollama:
https://ollama.ai

# Verify installation:
ollama --version

# Then run
.\run.ps1 -Mode pipeline
```

### "Model download is slow"

This happens only on first run. Subsequent runs use the cached model.

```bash
# To speed up, manually pull model first:
ollama pull qwen2.5:14b

# Then run
.\run.ps1 -Mode pipeline
```

## Configuration

Edit `config/pipeline.yaml`:

```yaml
ai:
  # These are defaults, system auto-detects and overrides
  provider: "ollama"
  model: "qwen2.5:14b"
  auto_launch: true
  auto_pull_model: true
```

## Advanced: Custom Provider Setup

### Adding a New Provider

Edit `ai_providers_manager.py`:

```python
PROVIDERS = {
    "your_provider": {
        "url": "https://api.yourprovider.com",
        "health_check": True,
        "default_model": "your-model",
        "env_key": "YOUR_PROVIDER_API_KEY",
    },
    ...
}
```

Then implement in `_setup_cloud_provider()` and add the API key logic.

## Performance

**First Run:** ~20 minutes (Ollama model download)
**Subsequent Runs:** <10 seconds (model cached)
**Cloud APIs:** Always fast (except for API rate limits)

## Costs

- **Ollama:** Free (runs locally on your machine)
- **OpenAI:** ~$0.01-0.05 per analysis cycle
- **Anthropic:** ~$0.02-0.10 per analysis cycle
- **DeepSeek:** ~$0.001-0.01 per analysis cycle (cheapest)
- **Qwen:** ~$0.001-0.01 per analysis cycle (cheapest)

Hourly analysis = ~20-200 API calls per day on cloud APIs

## Summary

✅ **All 5 AI providers supported**
✅ **Automatic detection and setup**
✅ **No manual configuration needed**
✅ **Automatic fallback chain**
✅ **Works offline with Ollama**
✅ **Works with any cloud API**
✅ **Zero provider switching overhead**
