"""
nordentrader-server-api-py
High-performance TCP client for NordenTrader platform
Supports real-time quotes, trades, balance, user & symbol events
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from collections import defaultdict


RECONNECT_DELAY_MS = 4000
RESPONSE_TIMEOUT_MS = 30000
AUTO_SUBSCRIBE_DELAY_MS = 500


class EventEmitter:
    """Simple event emitter for handling events"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def on(self, event: str, listener: Callable) -> 'EventEmitter':
        """Register an event listener"""
        self._listeners[event].append(listener)
        return self

    def emit(self, event: str, data: Any = None):
        """Emit an event to all registered listeners"""
        for listener in self._listeners.get(event, []):
            try:
                if asyncio.iscoroutinefunction(listener):
                    asyncio.create_task(listener(data))
                else:
                    listener(data)
            except Exception as e:
                print(f"[EventEmitter] Error in listener for '{event}': {e}")


class NTPlatform:
    """
    NTPlatform - TCP client for NordenTrader

    Args:
        url: Host and port (e.g., 'host:8080')
        name: Identifier for logging
        options: Configuration dict with keys:
            - auto_subscribe: List[str] - Auto-subscribe channels
            - ignore_events: bool - Disable event emission
            - prefix: str - Event prefix (default: 'nor')
            - mode: str - 'live' || 'demo' || ...
        broker: Optional broker object
        ctx: Optional context object
        token: JWT authentication token
        emitter: Optional custom EventEmitter
    """

    def __init__(
        self,
        url: str,
        name: str,
        options: Optional[Dict[str, Any]] = None,
        broker: Any = None,
        ctx: Any = None,
        token: str = "",
        emitter: Optional[EventEmitter] = None
    ):
        self.url = url
        self.name = name
        self.token = token
        self.broker = broker or {}
        self.ctx = ctx or {}

        options = options or {}
        self.ignore_events = options.get('ignore_events', False)
        self.prefix = options.get('prefix', 'nor')
        self.mode = options.get('mode', 'live')
        self.auto_subscribe_channels = options.get('auto_subscribe', [])

        self.emitter = emitter or EventEmitter()
        self.connected = False
        self.alive = True
        self.recv = ""
        self.seen_notify_tokens = set()
        self.pending: Dict[str, asyncio.Future] = {}

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._read_task: Optional[asyncio.Task] = None

        # Start connection
        asyncio.create_task(self._create_socket())

    async def _create_socket(self):
        """Establish TCP connection and set up event handlers"""
        self.connected = False
        self.seen_notify_tokens.clear()

        host, port = self.url.split(':')
        port = int(port)

        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.connected = True
            print(f"[NT:{self.name}] Connected to {self.url}")

            # Start reading first
            self._read_task = asyncio.create_task(self._read_loop())

            # Auto-subscribe after connection is stable
            if self.auto_subscribe_channels:
                asyncio.create_task(self._auto_subscribe())

        except Exception as e:
            print(f"[NT:{self.name}] Connection failed: {e}")
            if self.alive:
                await self._reconnect()

    async def _read_loop(self):
        """Read incoming data from socket"""
        try:
            while self.alive and self.connected:
                data = await self.reader.read(4096)
                if not data:
                    break

                self.recv += data.decode('utf-8', errors='ignore')

                # Process complete messages
                while '\r\n' in self.recv:
                    pos = self.recv.index('\r\n')
                    line = self.recv[:pos]
                    self.recv = self.recv[pos + 2:]

                    if line.strip():
                        self._handle_data(line)
        except Exception as e:
            print(f"[NT:{self.name}] Read error: {e}")
        finally:
            self.connected = False
            print(f"[NT:{self.name}] Connection closed")
            if self.alive:
                await self._reconnect()

    async def _auto_subscribe(self):
        """Auto-subscribe after connection is stable"""
        await asyncio.sleep(AUTO_SUBSCRIBE_DELAY_MS / 1000)
        try:
            await self.subscribe(self.auto_subscribe_channels)
            print(f"[NT:{self.name}] Auto-subscribed: {', '.join(self.auto_subscribe_channels)}")
        except Exception as e:
            print(f"[NT:{self.name}] Auto-subscribe failed: {e}")

    def _handle_data(self, data: str):
        """Handle incoming TCP data"""
        try:
            cleaned = data.replace('\n', '').replace('\r', '').replace('\t', '').strip()
            parsed = json.loads(cleaned)

            # === ARRAY MESSAGES ===
            if isinstance(parsed, list):
                if len(parsed) == 0:
                    return

                marker = parsed[0]

                # Quote: ["t", symbol, bid, ask, timestamp]
                if marker == 't' and len(parsed) >= 4:
                    self._handle_quote(parsed)

                # Notify: ["n", msg, desc, token, status, level, user_id, time, data?, code]
                elif marker == 'n' and len(parsed) >= 8:
                    self._handle_notify(parsed)

                # Symbols Reindex: ["sr", [[symbol, sym_index, sort_index], ...]]
                elif marker == 'sr' and len(parsed) == 2:
                    self._emit('symbols:reindex', parsed[1])

                # Security Reindex: ["sc", [[sec_index, sort_index], ...]]
                elif marker == 'sc' and len(parsed) == 2:
                    self._emit('security:reindex', parsed[1])

                else:
                    print(f"[NT:{self.name}] Unknown array message: {parsed}")

                return

            # === JSON EVENT OBJECTS ===
            if isinstance(parsed, dict):
                if 'event' in parsed:
                    self._handle_event(parsed)
                    return

                # === COMMAND RESPONSES (extID) ===
                if 'extID' in parsed:
                    ext_id = parsed['extID']
                    if ext_id in self.pending:
                        future = self.pending.pop(ext_id)
                        if not future.done():
                            future.set_result(parsed)
                    return

                print(f"[NT:{self.name}] Unknown message: {parsed}")

        except json.JSONDecodeError as e:
            print(f"[NT:{self.name}] Parse error: {e} | Data: {data}")
        except Exception as e:
            print(f"[NT:{self.name}] Handle error: {e}")

    def _handle_quote(self, arr: List):
        """Handle quote message: ["t", symbol, bid, ask, timestamp]"""
        if len(arr) < 4:
            return

        symbol = arr[1]
        bid = arr[2]
        ask = arr[3]

        if not isinstance(symbol, str) or not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
            return

        quote = {
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'timestamp': datetime.fromtimestamp(arr[4]) if len(arr) >= 5 and arr[4] else None
        }

        self._emit('quote', quote)
        self._emit(f'quote:{symbol.upper()}', quote)

    def _handle_notify(self, arr: List):
        """Handle notify message: ["n", msg, desc, token, status, level, user_id, time, data?, code]"""
        if len(arr) < 8:
            return

        token = arr[3]
        if token in self.seen_notify_tokens:
            return
        self.seen_notify_tokens.add(token)

        notify = {
            'message': arr[1] if len(arr) > 1 else '',
            'description': arr[2] if len(arr) > 2 else '',
            'token': token,
            'status': arr[4] if len(arr) > 4 else '',
            'level': int(arr[5]) if len(arr) > 5 else 0,
            'user_id': arr[6] if len(arr) > 6 else '',
            'create_time': datetime.fromtimestamp(arr[7]) if len(arr) > 7 and arr[7] else None,
            'data': {},
            'code': 0
        }

        # Parse data and code
        if len(arr) >= 9:
            if isinstance(arr[8], dict):
                notify['data'] = arr[8]
                if len(arr) >= 10:
                    notify['code'] = int(arr[9])
            else:
                notify['code'] = int(arr[8])

        self._emit('notify', notify)
        self._emit(f'notify:{notify["level"]}', notify)

    def _handle_event(self, obj: Dict):
        """Handle event object: {event, type, data}"""
        event = obj.get('event')
        event_type = obj.get('type')
        data = obj.get('data', {})

        event_obj = {
            'event': event,
            'type': event_type,
            'data': data
        }

        self._emit(event, event_obj)

        # Additional routing
        if isinstance(data, dict):
            if 'login' in data:
                self._emit(f'{event}:{data["login"]}', event_obj)
            if 'symbol' in data:
                self._emit(f'{event}:{data["symbol"]}', event_obj)
            if 'group' in data:
                self._emit(f'{event}:{data["group"]}', event_obj)

    def _emit(self, event: str, data: Any = None):
        """Emit event if not ignored"""
        if not self.ignore_events:
            self.emitter.emit(event, data)

    async def call(self, command: str, data: Any = None) -> Dict[str, Any]:
        """
        Send command and wait for response

        Args:
            command: Command name (e.g., "AddUser", "GetTrades")
            data: Command payload

        Returns:
            Response dictionary
        """
        payload = {
            'command': command,
            'data': data if data is not None else {}
        }
        return await self.send(payload)

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Low-level send method

        Args:
            payload: Dictionary with command, data, optional extID

        Returns:
            Response dictionary
        """
        if not self.connected:
            raise ConnectionError(f"[NT:{self.name}] Not connected")

        ext_id = payload.get('extID', str(uuid.uuid4())[:12])
        payload['extID'] = ext_id
        payload['__token'] = self.token

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending[ext_id] = future

        # Set timeout
        async def timeout_handler():
            await asyncio.sleep(RESPONSE_TIMEOUT_MS / 1000)
            if ext_id in self.pending:
                fut = self.pending.pop(ext_id)
                if not fut.done():
                    fut.set_exception(TimeoutError(f"[NT:{self.name}] Timeout for extID: {ext_id}"))

        asyncio.create_task(timeout_handler())

        # Send
        try:
            message = json.dumps(payload) + "\r\n"
            self.writer.write(message.encode('utf-8'))
            await self.writer.drain()
        except Exception as e:
            if ext_id in self.pending:
                self.pending.pop(ext_id)
            raise e

        # Wait for response
        return await future

    async def subscribe(self, channels: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Subscribe to market data channels

        Args:
            channels: String or list of symbols/channels

        Returns:
            Response dictionary
        """
        chanels = [channels] if isinstance(channels, str) else channels
        return await self.call('Subscribe', {'chanels': chanels})

    async def unsubscribe(self, channels: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Unsubscribe from channels

        Args:
            channels: String or list of symbols to unsubscribe

        Returns:
            Response dictionary
        """
        chanels = [channels] if isinstance(channels, str) else channels
        return await self.call('Unsubscribe', {'chanels': chanels})

    async def _reconnect(self):
        """Reconnect with backoff"""
        if self._reconnect_task and not self._reconnect_task.done():
            return

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass

        self.seen_notify_tokens.clear()

        async def do_reconnect():
            await asyncio.sleep(RECONNECT_DELAY_MS / 1000)
            print(f"[NT:{self.name}] Reconnecting...")
            await self._create_socket()

        self._reconnect_task = asyncio.create_task(do_reconnect())

    def destroy(self):
        """Gracefully close connection"""
        self.alive = False

        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()

        if self.writer:
            try:
                self.writer.close()
            except:
                pass

        self.seen_notify_tokens.clear()

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected

    # Convenience methods for common commands
    async def add_user(self, **kwargs) -> Dict[str, Any]:
        """Create a new user"""
        return await self.call('AddUser', kwargs)

    async def get_users(self, **kwargs) -> Dict[str, Any]:
        """Get users list"""
        return await self.call('GetUsers', kwargs)

    async def get_trades(self, **kwargs) -> Dict[str, Any]:
        """Get trades list"""
        return await self.call('GetTrades', kwargs)