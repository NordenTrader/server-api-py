"""
scaletrade-server-api-py
Ultra-low latency Python TCP client for ScaleTrade platform
"""

from .st_platform import STPlatform, EventEmitter

__version__ = "1.0.2"
__author__ = "ScaleTrade"
__all__ = ["STPlatform", "EventEmitter"]