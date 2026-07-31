"""
Finnhub API client.
"""

from dataclasses import dataclass, field
from typing import Any

import requests

from investment_terminal.config.settings import Settings
from investment_terminal.utils.exceptions import APIError, ConfigurationError


@dataclass(slots=True)
class FinnhubClient:
    """
    HTTP client for the Finnhub REST API.
    """

    api_key: str
    timeout: float = 10.0
    base_url: str = "https://finnhub.io/api/v1"
    session: requests.Session = field(
        default_factory=requests.Session,
        repr=False,
    )

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

    def get_json(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Perform an authenticated GET request and return a JSON object.

        Raises:
            APIError: If the request, HTTP response or JSON parsing fails.
        """
        request_params = dict(params or {})
        request_params["token"] = self.api_key

        try:
            response = self.session.get(
                self.build_url(endpoint),
                params=request_params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise APIError(
                f"Finnhub request timed out after {self.timeout} seconds."
            ) from exc
        except requests.ConnectionError as exc:
            raise APIError(
                "Could not connect to Finnhub."
            ) from exc
        except requests.HTTPError as exc:
            status_code = (
                exc.response.status_code
                if exc.response is not None
                else "unknown"
            )
            raise APIError(
                f"Finnhub returned HTTP status {status_code}."
            ) from exc
        except requests.RequestException as exc:
            raise APIError(
                "Finnhub request failed."
            ) from exc

        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise APIError(
                "Finnhub returned invalid JSON."
            ) from exc
        except ValueError as exc:
            raise APIError(
                "Finnhub returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise APIError(
                "Finnhub response must be a JSON object."
            )

        if payload.get("error"):
            raise APIError(
                f"Finnhub API error: {payload['error']}"
            )

        return payload

    def close(self) -> None:
        """
        Close the underlying HTTP session.
        """
        self.session.close()

    def __enter__(self) -> "FinnhubClient":
        """
        Enter the client context manager.
        """
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """
        Close the HTTP session when leaving a context manager.
        """
        self.close()