"""
Voice Authentication Adapters.

This package contains adapters for voice authentication implementations,
connecting Clean Architecture ports with concrete implementations.
"""

from .voice_authentication_adapter import VoiceAuthenticationAdapter

__all__ = [
    'VoiceAuthenticationAdapter'
]
