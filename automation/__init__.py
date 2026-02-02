"""
Automation module for CLI control of the MTGO Tools application.

This module provides:
- AutomationServer: Socket server that runs inside the wxPython app
- AutomationClient: Client library for sending commands
- CLI: Command-line interface for manual testing and scripting
"""

from automation.client import AutomationClient
from automation.server import AutomationServer

__all__ = ["AutomationServer", "AutomationClient"]
