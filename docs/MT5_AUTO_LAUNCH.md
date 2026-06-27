# MT5 Auto-Launch функціональність

## Огляд

Система автоматично запускає MetaTrader 5 terminal, якщо він закритий, або підключається до нього, якщо він вже відкритий.

## Як це працює

### 1. **Автоматичний запуск** (за замовчуванням увімкнено)

```python
from src.metatrader_client import MT5Client

# Конфіг з auto_launch=True (за замовчуванням)
config = {
    "login": 12345678,
    "password": "your_password",
    "server": "MetaQuotes-Demo",
    "auto_launch": True  # ← Це включено за замовчуванням
}

client = MT5Client(config)
client.connect()  # Якщо MT5 закритий → запустить його
                  # Якщо відкритий → підключиться
```

### 2. **Вимкнення автозапуску**

```python
config = {
    "login": 12345678,
    "password": "your_password",
    "server": "MetaQuotes-Demo",
    "auto_launch": False  # ← Не запускати MT5
}

client = MT5Client(config)
client.connect()  # Лише спроба підключитися до вже запущеного MT5
```

## Де знаходиться MT5?

Система автоматично шукає terminal.exe в наступних місцях:

### Windows
1. **Змінна середовища `METATRADER5_PATH`** (якщо встановлена)
   ```powershell
   setx METATRADER5_PATH "C:\Program Files\MetaTrader 5"
   ```

2. **Program Files (x86) / MetaTrader 5**
   ```
   C:\Program Files (x86)\MetaTrader 5\terminal.exe
   ```

3. **Program Files / MetaTrader 5**
   ```
   C:\Program Files\MetaTrader 5\terminal.exe
   ```

4. **AppData / MetaTrader 5**
   ```
   C:\Users\YourUser\AppData\Roaming\MetaTrader 5\terminal.exe
   ```

### Або явно вказати

```python
config = {
    "path": "C:\\Program Files\\MetaTrader 5\\terminal.exe",
    "login": 12345678,
    "password": "your_password",
    "server": "MetaQuotes-Demo",
}

client = MT5Client(config)
client.connect()
```

## Процес підключення

```
client.connect()
    ↓
_initialize_terminal()
    ↓
ensure_mt5_running(auto_launch=True)
    ↓
    ├─→ _is_mt5_running()  ← Перевіряє наявність процесу
    │
    ├─ Якщо запущений: ✓ повертає (True, None)
    │
    └─ Якщо не запущений:
        ├→ _find_mt5_executable()  ← Шукає terminal.exe
        ├→ subprocess.Popen()        ← Запускає процес
        ├→ Чекає 30 сек на старт
        └→ Повертає (True, None) або (False, error_msg)
    ↓
mt5.initialize()  ← Підключення до терміналу
    ↓
_login()  ← Авторизація за логіном/паролем
    ↓
✓ Успішне підключення
```

## Код модуля

### `src/metatrader_client/connection/_process_manager.py`

Основні функції:

- **`_is_mt5_running()`** — перевіряє, чи запущений процес terminal.exe
- **`_launch_mt5(terminal_path)`** — запускає MT5 та чекає на старт (30 сек)
- **`_find_mt5_executable()`** — шукає terminal.exe в стандартних місцях
- **`ensure_mt5_running(terminal_path, auto_launch)`** — гарантує, що MT5 працює

### Логування

Усі операції логуються в logger `"MT5ProcessManager"`:

```python
import logging

# Увімкнути debug логи
logging.getLogger("MT5ProcessManager").setLevel(logging.DEBUG)
logging.getLogger("MT5Connection").setLevel(logging.DEBUG)

# Запустити підключення
client.connect()

# Побачити детальні логи про процес
```

Приклад логів:
```
INFO: MT5 terminal is already running
INFO: Launching MT5 terminal from: C:\Program Files\MetaTrader 5\terminal.exe
INFO: Waiting for MT5 terminal to start...
INFO: MT5 terminal successfully launched and started (2.3 seconds)
INFO: Successfully connected to MetaTrader 5 terminal
```

## Приклади використання

### Базовий приклад

```python
from src.metatrader_client import MT5Client

config = {
    "login": 12345678,
    "password": "your_password",
    "server": "MetaQuotes-Demo",
}

client = MT5Client(config)

try:
    client.connect()  # Запустить MT5 якщо потрібно
    print("Connected!")
    
    # Працювати з MT5...
    account_info = client.get_account_info()
    print(account_info)
    
finally:
    client.disconnect()
```

### Контроль за процесом

```python
from src.metatrader_client.connection import ensure_mt5_running

# Переконатися, що MT5 запущений
success, error = ensure_mt5_running(
    terminal_path=None,  # Шукати автоматично
    auto_launch=True     # Запустити якщо потрібно
)

if success:
    print("MT5 is running!")
else:
    print(f"MT5 launch failed: {error}")
```

### Без автозапуску (manual mode)

```python
config = {
    "login": 12345678,
    "password": "your_password",
    "server": "MetaQuotes-Demo",
    "auto_launch": False,  # Вимкнути автозапуск
}

client = MT5Client(config)

try:
    client.connect()  # Лише спроба підключитися до вже запущеного MT5
except Exception as e:
    print(f"MT5 not running: {e}")
    print("Please launch MetaTrader 5 manually and try again")
```

## Помилки та рішення

### "MT5 terminal not found"

**Причина:** terminal.exe не знайдена в стандартних місцях.

**Рішення:**
1. Встановити змінну середовища `METATRADER5_PATH`
2. Явно вказати `path` у конфігу
3. Встановити MetaTrader 5 у стандартну папку

### "MT5 process not detected after 30 seconds"

**Причина:** Процес запустився, але не став готовий до підключення за 30 сек.

**Рішення:**
1. Збільшити timeout в конфігу
2. Переконатися, що на системі достатньо ресурсів
3. Відключити інші програми, які блокують MT5

### "Authorization failed (Error code: -6)"

**Причина:** Логін/пароль/сервер неправильний.

**Рішення:**
1. Перевірити реквізити входу
2. Переконатися, що акаунт активний
3. Спробувати з іншого сервера (Demo vs Live)

## Налаштування для pipeline

У файлі `config/pipeline.yaml` додай:

```yaml
mt5_connection:
  login: 12345678
  password: "your_password"
  server: "MetaQuotes-Demo"
  auto_launch: true      # ← Автоматичний запуск
  timeout: 60000
  max_retries: 3
```

Тоді у коді pipeline:

```python
from src.trading_ai_pipeline.core.config.settings import PipelineConfig
from src.metatrader_client import MT5Client

config = PipelineConfig.load_from_yaml('config/pipeline.yaml')

# MT5 автоматично запуститься та підключиться
mt5_client = MT5Client(config.mt5_connection)
mt5_client.connect()

print("Ready to trade!")
```
