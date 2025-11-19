"""
nordentrader-server-api-py
Ultra-low latency Python TCP client for NordenTrader platform
"""

from .nt_platform import NTPlatform, EventEmitter

__version__ = "1.0.1"
__author__ = "NordenTrader"
__all__ = ["NTPlatform", "EventEmitter"]