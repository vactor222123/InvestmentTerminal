"""
Finnhub API client.
"""

from dataclasses import dataclass

from investment_terminal.config.settings import Settings
from investment_terminal.utils.exceptions import ConfigurationError


@dataclass(slots=True)
class FinnhubClient:
    """
    Base client for the Finnhub REST API.

    The actual HTTP request logic will be added in Sprint 2.2.
    """

    api_key: str
    timeout: float = 10.0
    base_url: str = "https://finnhub.io/api/v1"

    def __post_init__(self) -> None:
        """
        Validate client configuration.
        """
        self.api_key = self.api_key.strip()

        if not self.api_key:
            raise ConfigurationError("Finnhub API key must not be empty.")

        if self.timeout <= 0:
            raise ConfigurationError(
                "Finnhub timeout must be greater than zero."
            )

        self.base_url = self.base_url.rstrip("/")

        if not self.base_url.startswith(("https://", "http://")):
            raise ConfigurationError(
                "Finnhub base URL must use HTTP or HTTPS."
            )

    @classmethod
    def from_settings(cls) -> "FinnhubClient":
        """
        Create a Finnhub client from application settings.
        """
        api_key = Settings.FINNHUB_API_KEY

        if not api_key:
            raise ConfigurationError(
                "FINNHUB_API_KEY not found in application settings."
            )

        return cls(api_key=api_key)

    def build_url(self, endpoint: str) -> str:
        """
        Build a normalized Finnhub endpoint URL.
        """
        normalized_endpoint = endpoint.strip().lstrip("/")

        if not normalized_endpoint:
            raise ValueError("Finnhub endpoint must not be empty.")

        return f"{self.base_url}/{normalized_endpoint}"