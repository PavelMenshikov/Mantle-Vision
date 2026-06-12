# Mantle Vision — Сводка сессии (10 июня 2026)

## ✅ Что было починено

### 1. `get_latest_block` — мёртвый код
**Файл:** `backend/app/services/mantle_scanner.py:64-76`
**Проблема:** Метод `get_latest_block()` был случайно вложен внутрь property `whale_min_value` после `return`. Код никогда не выполнялся.
**Фикс:** Выделен в отдельный метод.

### 2. `is_connected` — несуществующий атрибут
**Файл:** `backend/app/services/mantle_scanner.py` (6 мест)
**Проблема:** Везде использовалось `self.is_connected`, но такого property нет. Правильное поле — `self._connected`.
**Фикс:** `self.is_connected` → `self._connected` во всех 6 методах.

### 3. `/api/txs/recent` — 500 ошибка
**Причина:** Вызывал `mantle_scanner.get_latest_block()` → падал из-за бага №1.
**Статус:** Должен работать после рестарта (оба фикса выше).

## 🟡 Что не работает (будет после перезагрузки)

### 1. Бэкенд (uvicorn) не запущен
**Симптом:** `ECONNREFUSED 127.0.0.1:8000` — порт не слушается.
**Команда для запуска:**
```bash
cd D:\projects\DoraHacks\mantle-vision\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Фронтенд Vite proxy error
**Причина:** Vite стартовал раньше бэкенда, закешировал ошибку.
**Фикс:** Перезапустить Vite ПОСЛЕ запуска бэкенда:
```bash
cd D:\projects\DoraHacks\mantle-vision\frontend
npx vite
```

### 3. "Сканнер не грузится" в UI
**Причина:** Фронтенд не получает данные от `/api/scanner/status`.
**Статус:** После запуска бэкенда и перезапуска Vite — должно заработать.

## 📊 Наблюдения

- **Сканер работает** — после фиксов в логе было: `Trigger: 1 whale tx, 0 protocol events`.
- Но находит **очень мало** транзакций (порог 10 MNT, 1 трансфер за 100 блоков).
- `protocol_events` всегда пустые — адреса в `KNOWN_PROTOCOLS` фейковые.

## 🔜 Возможные улучшения (не срочно)

1. **Понизить порог whale tx** — сейчас 10 MNT (хардкод в `main.py:88`).
2. **Добавить ERC-20 сканирование** — ловить USDC/mETH трансферы, а не только нативный MNT.
3. **Обновить KNOWN_PROTOCOLS** — прописать реальные адреса контрактов Mantle DeFi.
