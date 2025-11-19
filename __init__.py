"""
ion-server-api-py
Ultra-low latency Python TCP client for IonTrader platform
"""

from .ion_platform import IONPlatform, EventEmitter

__version__ = "1.0.0"
__author__ = "IonTrader"
__all__ = ["IONPlatform", "EventEmitter"]