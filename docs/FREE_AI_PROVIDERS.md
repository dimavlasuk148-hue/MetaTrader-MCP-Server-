# FREE AI Providers Setup Guide

System now uses **100% FREE AI providers** with no credit card required for core functionality.

## 4 FREE Options

### 1. Ollama (Recommended - 100% Local & Free)

**Cost:** FREE (no internet needed after download)

**Setup:**
```bash
# Download from https://ollama.ai

# Windows: Run installer
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull default model (one time, ~5 min)
ollama pull qwen2.5:14b
```

**Advantages:**
- No internet required
- Completely private (data never leaves your PC)
- Instant startup (after download)
- Zero API limits

**Disadvantages:**
- Requires local GPU or CPU (slower on CPU)
- Higher disk space (~7GB for model)

---

### 2. Groq (FREE Tier - 30k tokens/min)

**Cost:** FREE (generous free tier, no credit card needed)

**Setup:**
```bash
# 1. Signup: https://console.groq.com
# 2. Create API key
# 3. Set environment variable

# Windows (PowerShell)
$env:GROQ_API_KEY = "gsk_xxx"

# Linux/Mac
export GROQ_API_KEY="gsk_xxx"

# Add to .env for permanent
echo "GROQ_API_KEY=gsk_xxx" >> .env
```

**Advantages:**
- Very fast inference (fastest of all)
- Generous free tier (30k tokens/min)
- No credit card required
- Cloud-based (works anywhere)

**Disadvantages:**
- Requires internet
- Rate limited on free tier
- Limited to Groq's models

**Get started:** https://console.groq.com

---

### 3. Together AI (FREE Tier + $1 credit/month)

**Cost:** FREE ($1 monthly credit)

**Setup:**
```bash
# 1. Signup: https://www.together.ai
# 2. Create API key
# 3. Set environment variable

export TOGETHER_API_KEY="xxx"

# Or in .env
echo "TOGETHER_API_KEY=xxx" >> .env
```

**Advantages:**
- Free tier with $1 monthly credit
- Good model selection
- Reasonable rate limits
- No credit card needed (for free tier)

**Disadvantages:**
- Requires internet
- Limited to Together's models
- Need to manage monthly credit

**Get started:** https://www.together.ai

---

### 4. HuggingFace (FREE Tier - Rate Limited)

**Cost:** FREE (rate limited)

**Setup:**
```bash
# 1. Signup: https://huggingface.co
# 2. Create API token
# 3. Set environment variable

export HUGGINGFACE_API_KEY="hf_xxx"

# Or in .env
echo "HUGGINGFACE_API_KEY=hf_xxx" >> .env
```

**Advantages:**
- Completely free
- Huge model library
- No credit card needed
- Easy signup

**Disadvantages:**
- Heavily rate limited (free tier)
- Slow inference
- Best for offline/batch processing

**Get started:** https://huggingface.co

---

## Recommended Setup

### Option A: Local Only (Ollama)
```bash
# Single setup, never pay, never need internet
ollama serve
# Done! System auto-detects
```

### Option B: Local + Cloud Backup (Ollama + Groq)
```bash
# Start Ollama
ollama serve

# Add Groq as backup
export GROQ_API_KEY="gsk_xxx"

# System prefers local, uses Groq if Ollama down
```

### Option C: Cloud Only (Groq)
```bash
# No local setup needed
export GROQ_API_KEY="gsk_xxx"

# Run system, Groq provides AI
```

---

## Automatic Provider Selection

System tries providers in this order:

1. **Ollama** (if running locally)
2. **Groq** (if GROQ_API_KEY set)
3. **Together** (if TOGETHER_API_KEY set)
4. **HuggingFace** (if HUGGINGFACE_API_KEY set)

Uses first available provider automatically.

---

## Startup Output

```
======================================================================
AUTOMATED FREE AI PROVIDER DETECTION & SETUP
======================================================================

[+] Successfully initialized 2 FREE provider(s):
    ✓ ollama
    ✓ groq

[+] Primary provider: OLLAMA

[*] Setting up MetaTrader 5 connection...
[+] Connected to MT5

======================================================================
STARTING TRADING PIPELINE (FREE AI MODE)
======================================================================
```

---

## Cost Comparison

| Provider | Cost | Speed | Setup | Internet |
|----------|------|-------|-------|----------|
| Ollama | FREE | Slow-Medium | 5 min | No |
| Groq | FREE (tier) | Very Fast | 2 min | Yes |
| Together | FREE+$1/mo | Fast | 2 min | Yes |
| HuggingFace | FREE | Slow | 2 min | Yes |

---

## Troubleshooting

### "No FREE AI providers found"

1. Install Ollama (recommended):
   ```bash
   https://ollama.ai
   ollama serve
   ```

2. OR set Groq API key:
   ```bash
   export GROQ_API_KEY="gsk_xxx"
   ```

### Ollama not detected

- Check if running: `ollama list`
- Start Ollama: `ollama serve`
- Wait 5 seconds for system to detect

### Groq API key not working

- Check at: https://console.groq.com/keys
- Format: `gsk_xxx` (starts with gsk_)
- Verify: `echo $GROQ_API_KEY`

### Model not available on Ollama

```bash
# Check available
ollama list

# Pull model
ollama pull qwen2.5:14b
```

---

## FAQs

**Q: Can I use multiple providers?**
A: Yes! Set multiple API keys, system uses first available.

**Q: Is my data private?**
A: Only with Ollama (local). Cloud providers see prompts.

**Q: Can I switch providers?**
A: Yes, set different API keys or restart Ollama.

**Q: Which is best?**
A: Ollama (local + free) if you have GPU, else Groq (fastest free cloud).

**Q: Do I need to pay?**
A: No. Ollama is completely free. Groq/Together have generous free tiers.

---

## Next Steps

1. Choose provider above
2. Install/setup (5 minutes)
3. Run: `.\run.ps1 -Mode pipeline`
4. System auto-detects and starts trading!

No additional configuration needed beyond provider setup.
