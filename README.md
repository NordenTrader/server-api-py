<div align="center">

# NordenTrader Server Api Py

**Ultra-low latency Python TCP client for [NordenTrader](https://nordentrader.com)**  
Real-time market data, trade execution, balance & user management via TCP.

![PyPI](https://img.shields.io/pypi/v/nordentrader-server-api-py?color=green)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)
![Downloads](https://img.shields.io/pypi/dm/nordentrader-server-api-py)

> **Server-to-Server (S2S) integration** — ideal for brokers, CRMs, HFT bots, and back-office systems.

[Documentation](https://nordentrader.com/tcp) · [Examples](./example.py) · [Report Bug](https://github.com/nordentrader/server-api-py/issues)

</div>

---

## Features

| Feature | Description |
|-------|-------------|
| **TCP S2S** | Direct TCP connection — no HTTP overhead |
| **Real-time Events** | Quotes, trades, balance, user & symbol updates |
| **Optimized Subscribe** | `await platform.subscribe()` / `unsubscribe()` |
| **Dynamic Commands** | `await platform.call("AddUser", data)` |
| **Auto-reconnect** | Robust reconnection with backoff |
| **Event Filtering** | `ignore_events`, per-symbol listeners |
| **extID Tracking** | Reliable command responses |
| **JSON Repair** | Handles malformed packets gracefully |
| **Async/Await** | Full asyncio support |
| **Zero Dependencies** | Pure Python 3.8+ standard library |

---

## Installation

```bash
pip install nordentrader-server-api-py
```

### From Source

```bash
git clone https://github.com/nordentrader/server-api-py
cd server-api-py
pip install -e .
```

---

## Quick Start

```python
import asyncio
from nt_platform import NTPlatform

async def main():
    # Initialize with minimal config
    platform = NTPlatform(
        "broker.nordentrader.com:8080",      # Host:port
        "my-trading-bot",                  # Name
        options={
            'auto_subscribe': ['EURUSD', 'BTCUSD']
        },
        token="your-jwt-auth-token"
    )
    
    # Real-time quotes
    def on_quote(q):
        print(f"{q['symbol']}: {q['bid']}/{q['ask']}")
    
    platform.emitter.on('quote', on_quote)
    
    # Trade events
    def on_trade(e):
        d = e['data']
        cmd = 'BUY' if d['cmd'] == 0 else 'SELL'
        print(f"#{d['order']} {cmd} {d['volume']} {d['symbol']}")
    
    platform.emitter.on('trade:event', on_trade)
    
    # Subscribe to new symbol
    await platform.subscribe('XAUUSD')
    
    # Create user
    await platform.add_user(
        name='John Doe',
        group='VIP',
        leverage=500,
        email='john@example.com'
    )
    
    # Keep running
    await asyncio.sleep(3600)
    platform.destroy()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Supported Events

| Event | Description | Example Data |
|------|-------------|--------------|
| `quote` | Real-time tick | `{ 'symbol': 'EURUSD', 'bid': 1.085, 'ask': 1.086 }` |
| `quote:SYMBOL` | Per-symbol | `quote:EURUSD` |
| `notify` | System alerts | `{ 'message', 'level', 'code', 'data' }` |
| `notify:LEVEL` | By level | `notify:20` (warning) |
| `trade:event` | Order open/close/modify | `{ 'order', 'profit', 'volume', 'symbol' }` |
| `trade:event:LOGIN` | Per-user trades | `trade:event:12345` |
| `balance:event` | Balance & margin update | `{ 'equity', 'margin_level', 'balance' }` |
| `balance:event:LOGIN` | Per-user balance | `balance:event:12345` |
| `user:event` | User profile change | `{ 'leverage', 'group', 'name' }` |
| `user:event:LOGIN` | Per-user updates | `user:event:12345` |
| `symbol:event` | Symbol settings update | `{ 'spread', 'swap_long', 'swap_short' }` |
| `symbol:event:SYMBOL` | Per-symbol updates | `symbol:event:EURUSD` |
| `group:event` | Group config change | `{ 'default_leverage', 'margin_call' }` |
| `group:event:GROUP` | Per-group updates | `group:event:VIP` |
| `symbols:reindex` | Symbol index map | `[['symbol', sym_index, sort_index], ...]` |
| `security:reindex` | Security group map | `[[sec_index, sort_index], ...]` |

---

## Methods

| Method | Description | Returns |
|-------|-------------|---------|
| `subscribe(channels)` | Fast subscribe to symbols | `Dict` (awaitable) |
| `unsubscribe(channels)` | Fast unsubscribe | `Dict` (awaitable) |
| `call(command, data)` | Execute any command | `Dict` (awaitable) |
| `send(payload)` | Low-level send | `Dict` (awaitable) |
| `emitter.on(event, listener)` | Register event listener | - |
| `destroy()` | Close connection | - |
| `is_connected()` | Check connection status | `bool` |

### Convenience Methods

| Method | Description |
|-------|-------------|
| `add_user(**kwargs)` | Create user |
| `get_users(**kwargs)` | Get users list |
| `get_trades(**kwargs)` | Get trades list |

---

## Examples

### Subscribe & Unsubscribe

```python
# Single symbol
resp = await platform.subscribe('GBPUSD')
print(f"Subscribed: {resp}")

# Multiple symbols
await platform.subscribe(['GBPUSD', 'USDJPY'])

# Unsubscribe
await platform.unsubscribe('BTCUSD')
```

### Get All Users

```python
try:
    resp = await platform.call('GetUsers', {})
    print(f"Users: {resp}")
except Exception as e:
    print(f"Error: {e}")
```

### Listen to Balance Changes

```python
def on_balance(e):
    d = e['data']
    print(f"User {d['login']}: Equity = {d['equity']}")

platform.emitter.on('balance:event', on_balance)

# Listen to specific user
platform.emitter.on('balance:event:12345', lambda e: print("User 12345 balance updated"))
```

### Per-Symbol Quote Listener

```python
# Listen to specific symbol
def on_eurusd(q):
    print(f"EUR/USD: {q['bid']}")

platform.emitter.on('quote:EURUSD', on_eurusd)

# Listen to all quotes
def on_all_quotes(q):
    print(f"{q['symbol']}: {q['bid']}/{q['ask']}")

platform.emitter.on('quote', on_all_quotes)
```

### Handle Notifications

```python
def on_notify(n):
    level_map = {10: 'INFO', 20: 'WARN', 30: 'ERROR', 40: 'PROMO'}
    level = level_map.get(n['level'], str(n['level']))
    print(f"[{level}] {n['message']}")

platform.emitter.on('notify', on_notify)

# Listen to specific level
def on_error(n):
    print(f"ERROR: {n['message']}")

platform.emitter.on('notify:30', on_error)
```

### Symbol & Group Events

```python
# Symbol updates (spread, swap, etc.)
def on_symbol(e):
    d = e['data']
    print(f"Symbol {d['symbol']} updated: spread={d.get('spread', 'N/A')}")

platform.emitter.on('symbol:event', on_symbol)

# Group updates
def on_group(e):
    d = e['data']
    print(f"Group {d['group']}: leverage={d.get('default_leverage')}")

platform.emitter.on('group:event', on_group)
```

### Async Event Handlers

```python
# Event handlers can be async
async def on_trade(e):
    d = e['data']
    # Do async operations
    await some_async_function(d['order'])

platform.emitter.on('trade:event', on_trade)
```

### Full Example

See [`example.py`](./example.py)

---

## Configuration

### Options

```python
options = {
    'auto_subscribe': ['EURUSD', 'GBPUSD'],  # Auto-subscribe on connect
    'ignore_events': False,                   # Disable all event emission
    'prefix': 'nor',                          # Event prefix (reserved)
    'mode': 'live'                            # Environment: 'live' or 'demo'
}

platform = NTPlatform(
    "broker.nordentrader.com:8080",
    "my-bot",
    options=options,
    token="your-jwt-token"
)
```

---

## Error Handling

```python
try:
    resp = await platform.call('AddUser', {'name': 'John'})
    if 'error' in resp:
        print(f"Error: {resp['error']}")
    else:
        print(f"Success: {resp}")
except TimeoutError as e:
    print(f"Request timeout: {e}")
except ConnectionError as e:
    print(f"Not connected: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Asyncio Integration

### Running with Other Tasks

```python
async def main():
    platform = NTPlatform(...)
    
    # Run multiple tasks concurrently
    await asyncio.gather(
        platform.subscribe('EURUSD'),
        platform.get_users(),
        my_other_task()
    )
```

### Background Tasks

```python
async def price_monitor():
    while True:
        await asyncio.sleep(1)
        # Do something

async def main():
    platform = NTPlatform(...)
    
    # Start background task
    task = asyncio.create_task(price_monitor())
    
    # Keep running
    await asyncio.sleep(3600)
    
    # Cleanup
    task.cancel()
    platform.destroy()
```

---

## Documentation

- **TCP API**: [https://nordentrader.com/tcp](https://nordentrader.com/tcp)
- **Client API**: [https://nordentrader.com/client-api](https://nordentrader.com/client-api)
- **FIX API**: [https://nordentrader.com/fix-api](https://nordentrader.com/fix-api)

---

## Requirements

- **Python 3.8 or higher**
- Valid **NordenTrader JWT token**
- No external dependencies (pure stdlib)

---

## Building and Testing

```bash
# Clone repository
git clone https://github.com/nordentrader/server-api-py
cd server-api-py

# Install in development mode
pip install -e .

# Run example
python example.py
```

---

## License

Distributed under the **MIT License**.  
See [`LICENSE`](LICENSE) for more information.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<div align="center">

**Made with passion for high-frequency trading**

[nordentrader.com](https://nordentrader.com) · [GitHub](https://github.com/nordentrader/server-api-py)

</div>
