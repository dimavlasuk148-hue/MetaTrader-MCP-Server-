# Ollama Auto-Setup

Система автоматично знаходить, запускає та завантажує моделі Ollama. Вам не потрібно нічого налаштовувати вручну.

## Як це працює

### 1. Auto-Launch
При запуску pipeline:
```
[*] Checking Ollama availability...
[+] Ollama is already running
```

Якщо Ollama закритий, система автоматично:
1. Знаходить виконавчий файл (`ollama.exe` або `ollama`)
2. Запускає його у фоновому режимі
3. Чекає поки сервер не буде готовий

### 2. Auto-Pull Model
Якщо вибрана модель не завантажена:
```
[*] Model qwen2.5:14b not found. Attempting to pull...
[+] Model qwen2.5:14b pulled successfully
```

Система автоматично завантажує модель з ollama.ai.

## Установка

### Перший раз - встановіть Ollama

**Windows:**
```powershell
# Завантажити і запустити інсталятор з ollama.ai
# Або через Winget (якщо встановлено):
winget install Ollama.Ollama
```

**macOS:**
```bash
# Завантажити з ollama.ai
# Або через Homebrew:
brew install ollama
```

**Linux:**
```bash
# Ubuntu/Debian
curl https://ollama.ai/install.sh | sh

# Або вручну:
# https://ollama.ai/download
```

## Налаштування

### Стандартне (все автоматично)

```bash
# Просто запусти pipeline, і все буде налаштовано
./run.ps1 -Mode pipeline
```

Система автоматично:
- ✅ Запустить Ollama якщо не запущена
- ✅ Завантажить модель `qwen2.5:14b` якщо потрібна
- ✅ Перевірить у разі потреби

### Налаштування в конфігу

Отримуєш `.env`:

```bash
# Ollama базовий URL (за замовчуванням localhost:11434)
# Зміни тільки якщо Ollama на іншій машині
OLLAMA_BASE_URL=http://localhost:11434

# Модель для використання
OLLAMA_MODEL=qwen2.5:14b

# Автоматичний запуск Ollama (true/false)
OLLAMA_AUTO_LAUNCH=true

# Автоматичне завантаження моделей (true/false)
OLLAMA_AUTO_PULL=true
```

## Поширені проблеми

### "Ollama executable not found"

**Причина:** Ollama не встановлена або встановлена в нестандартне місце.

**Рішення:**
```bash
# 1. Встаньте Ollama з ollama.ai
# 2. Встановіть переменну окружения OLLAMA_HOME або шлях в PATH

# Windows - встановити PATH
setx PATH "%PATH%;C:\Users\YourUser\AppData\Local\Programs\Ollama"

# Linux/Mac
export PATH="$HOME/.ollama/bin:$PATH"
```

### "Ollama did not become responsive within 30 seconds"

**Причина:** Ollama запускається довго або залипла.

**Рішення:**
```bash
# 1. Перезавантажити Ollama вручну
# 2. Перевірити чи є місце на диску
# 3. Збільшити timeout в конфігу:
#    ollama_launch_timeout: 60
```

### "Model not found and auto_pull is disabled"

**Причина:** Модель не встановлена та `auto_pull: false`.

**Рішення:**
```bash
# 1. Увімкнути auto_pull в конфігу:
ollama_auto_pull: true

# 2. Або встановити модель вручну:
ollama pull qwen2.5:14b
ollama pull mistral
ollama pull llama2
```

## Доступні моделі

Система автоматично перевіряє коїх моделей доступно:

```bash
# Переглянути локально встановлені моделі
ollama list

# Завантажити модель
ollama pull qwen2.5:14b    # Рекомендується, якісна і швидка
ollama pull mistral         # Альтернатива, легша
ollama pull llama2          # Альтернатива, більша
```

## Використання іншого провайдера

Якщо хочеш замість Ollama використовувати OpenAI, Anthropic, DeepSeek:

```yaml
# config/pipeline.yaml

ai:
  provider: "openai"  # замість "ollama"
  model: "gpt-4-turbo"
  api_key: "${OPENAI_API_KEY}"
  # auto_launch and auto_pull ігноруються для OpenAI/Anthropic
```

## Виключення авто-запуску

Якщо хочеш вручну управляти Ollama:

```yaml
ai:
  auto_launch: false      # Не запускати автоматично
  auto_pull_model: false  # Не завантажувати модель автоматично
```

Тоді перед запуском pipeline запусти Ollama вручну:

```bash
ollama serve
```

## Перевірка статусу

```bash
# Перевірити чи запущена Ollama
curl http://localhost:11434/api/tags

# Переглянути логи (залежить від системи)
# Windows: Event Viewer
# macOS: ~/Library/Logs/Ollama
# Linux: journalctl -u ollama
```

## Продуктивність

### Рекомендовані моделі за швидкістю

| Модель | Розмір | Швидкість | Якість | GPU |
|--------|--------|-----------|--------|-----|
| `qwen2.5:7b` | 4.7GB | Швидка | Добра | 6GB VRAM |
| `qwen2.5:14b` | 8.6GB | Середня | Більш добра | 10GB VRAM |
| `mistral:7b` | 4.1GB | Дуже швидка | Задовільна | 5GB VRAM |
| `llama2:7b` | 3.8GB | Швидка | Задовільна | 4GB VRAM |

### Налаштування GPU

Ollama автоматично використовує GPU якщо доступна. Для явного налаштування:

```bash
# Windows - встановити CUDA
# Завантажити CUDA Toolkit з nvidia.com

# Linux
export OLLAMA_NUM_GPU=1

# macOS
# Автоматично використовує Metal (GPU Apple)
```

## Дебагування

```bash
# Увімкнути debug логи в конфігу
logging:
  level: "DEBUG"  # замість "INFO"

# Тоді переглянути логи
cat logs/pipeline/latest.jsonl | grep -i ollama
```
