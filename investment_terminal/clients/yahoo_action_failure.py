"""Typed privacy-safe action-request diagnoses; never inspect exception text."""

from curl_cffi.requests import exceptions as curl
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError, YFTzMissingError


def classify_action_failure(error):
    if isinstance(error, YFRateLimitError):
        return "RATE_LIMIT"
    if isinstance(error, (curl.Timeout, TimeoutError)):
        return "TIMEOUT"
    if isinstance(error, YFPricesMissingError):
        return "PRICE_DATA_MISSING"
    if isinstance(error, YFTzMissingError):
        return "TIMEZONE_MISSING"
    if isinstance(error, curl.SSLError):
        return "TLS_ERROR"
    if isinstance(error, curl.ConnectionError):
        return "CONNECTION_ERROR"
    if isinstance(error, curl.HTTPError):
        status = getattr(getattr(error, "response", None), "status_code", None)
        if type(status) is int and status == 429:
            return "RATE_LIMIT"
        if type(status) is int and status in (401, 403):
            return "HTTP_ACCESS_DENIED"
        if type(status) is int and 500 <= status <= 599:
            return "HTTP_SERVER_ERROR"
        return "HTTP_ERROR"
    if isinstance(error, curl.RequestException):
        return "TRANSPORT_ERROR"
    return "UNKNOWN_PROVIDER_ERROR"
