"""
Custom exceptions for Investment Terminal.
"""


class InvestmentTerminalError(Exception):
    """Base exception for the application."""


class ConfigurationError(InvestmentTerminalError):
    """Raised when configuration is invalid."""


class APIError(InvestmentTerminalError):
    """Raised when an external API fails."""


class DatabaseError(InvestmentTerminalError):
    """Raised for database related errors."""