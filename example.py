"""
ScaleTrade API Example
Demonstrates full event handling and subscribe/unsubscribe
"""

import asyncio
import time
from st_platform import STPlatform


async def main():
    url = "example.host:8080"
    name = "scaletrade-example-python"
    token = "your-jwt-auth-token"

    platform = STPlatform(
        url,
        name,
        options={
            'auto_subscribe': ['EURUSD', 'BTCUSD']
        },
        token=token
    )

    # === EVENTS ===

    # All quotes
    def on_quote(q):
        print(f"[QUOTE] {q['symbol']}: {q['bid']}/{q['ask']}")

    platform.emitter.on('quote', on_quote)

    # Specific symbol quote
    def on_eurusd(q):
        print(f"[EURUSD] Bid: {q['bid']}")

    platform.emitter.on('quote:EURUSD', on_eurusd)

    # Notifications
    def on_notify(n):
        level_map = {10: 'INFO', 20: 'WARN', 30: 'ERROR', 40: 'PROMO'}
        level = level_map.get(n['level'], str(n['level']))
        print(f"[NOTIFY:{level}] {n['message']}")

    platform.emitter.on('notify', on_notify)

    # Trade events
    def on_trade(e):
        d = e['data']
        cmd = 'BUY' if d.get('cmd') == 0 else 'SELL' if d.get('cmd') == 1 else 'UNKNOWN'
        print(f"[TRADE #{d.get('order')}] {cmd} {d.get('volume')} {d.get('symbol')} @ {d.get('open_price')} (P&L: {d.get('profit')})")

    platform.emitter.on('trade:event', on_trade)

    # Balance events
    def on_balance(e):
        d = e['data']
        print(f"[BALANCE] {d.get('login')} | Balance: {d.get('balance')} | Equity: {d.get('equity')} | Margin: {d.get('margin_level')}%")

    platform.emitter.on('balance:event', on_balance)

    # User events
    def on_user(e):
        d = e['data']
        print(f"[USER] {d.get('login')} | {d.get('name')} | Group: {d.get('group')} | Leverage: {d.get('leverage')}")

    platform.emitter.on('user:event', on_user)

    # Symbol events
    def on_symbol(e):
        d = e['data']
        spread = d.get('spread', 'N/A')
        swap_long = d.get('swap_long', 'N/A')
        print(f"[SYMBOL] {d.get('symbol')} | Spread: {spread} | Swap Long: {swap_long}")

    platform.emitter.on('symbol:event', on_symbol)

    # Group events
    def on_group(e):
        d = e['data']
        leverage = d.get('default_leverage', 'N/A')
        print(f"[GROUP] {d.get('group')} | Default Leverage: {leverage}")

    platform.emitter.on('group:event', on_group)

    # Symbols reindex
    def on_symbols_reindex(data):
        print(f"[SYMBOLS:REINDEX] {len(data)} symbols updated")

    platform.emitter.on('symbols:reindex', on_symbols_reindex)

    # Security reindex
    def on_security_reindex(data):
        print(f"[SECURITY:REINDEX] {len(data)} groups updated")

    platform.emitter.on('security:reindex', on_security_reindex)

    # === COMMANDS ===
    await asyncio.sleep(2)

    if not platform.is_connected():
        print("Not connected")
        return

    try:
        # Subscribe to additional symbol
        resp = await platform.subscribe('GBPUSD')
        print(f"✓ Subscribed to GBPUSD: {resp}")

        # Create user
        resp = await platform.add_user(
            group="TestGroup",
            name="John Doe",
            password="pass123",
            leverage=100,
            enable=1,
            email=f"john@example{int(time.time())}.com"
        )
        print(f"✓ User created: {resp}")

        # Unsubscribe after 10s
        await asyncio.sleep(10)
        resp = await platform.unsubscribe('BTCUSD')
        print(f"✓ Unsubscribed from BTCUSD: {resp}")

    except Exception as e:
        print(f"✗ Command error: {e}")

    # Auto shutdown after 30s
    await asyncio.sleep(30)
    print("Shutting down...")
    platform.destroy()


if __name__ == '__main__':
    asyncio.run(main())