"""
Finnhub API client.
"""

from dataclasses import dataclass, field
from typing import Any

import requests

from investment_terminal.config.settings import Settings
from investment_terminal.utils.exceptions import APIError, ConfigurationError
from datetime import datetime, timezone
from investment_terminal.models.quote import Quote
from investment_terminal.models.candle import Candle


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

    def get_candles(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> list[Candle]:
        """
        Download and validate historical OHLCV candles.
        """
        normalized_symbol = symbol.strip().upper()
        normalized_resolution = resolution.strip().upper()
        normalized_currency = currency.strip().upper()

        if not normalized_symbol:
            raise ValueError("Candle symbol must not be empty.")

        if not normalized_resolution:
            raise ValueError("Candle resolution must not be empty.")

        if not normalized_currency:
            raise ValueError("Candle currency must not be empty.")

        if not isinstance(start, datetime):
            raise TypeError("start must be a datetime")

        if not isinstance(end, datetime):
            raise TypeError("end must be a datetime")

        if start >= end:
            raise ValueError("start must be earlier than end")

        payload = self.get_json(
            "/stock/candle",
            params={
                "symbol": normalized_symbol,
                "resolution": normalized_resolution,
                "from": int(start.timestamp()),
                "to": int(end.timestamp()),
            },
        )

        status = payload.get("s")

        if status == "no_data":
            return []

        if status != "ok":
            raise APIError(
                "Finnhub candle response has an invalid status."
            )

        required_keys = ("o", "h", "l", "c", "v", "t")

        for key in required_keys:
            if key not in payload:
                raise APIError(
                    f"Finnhub candle response is missing '{key}'."
                )

            if not isinstance(payload[key], list):
                raise APIError(
                    f"Finnhub candle field '{key}' must be a list."
                )

        lengths = {
            len(payload[key])
            for key in required_keys
        }

        if len(lengths) != 1:
            raise APIError(
                "Finnhub candle arrays have inconsistent lengths."
            )

        candles: list[Candle] = []

        for index in range(len(payload["t"])):
            candle = Candle(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                timestamp=datetime.fromtimestamp(
                    payload["t"][index],
                    tz=timezone.utc,
                ),
                open_price=self._require_positive_list_number(
                    payload["o"],
                    index,
                    "open price",
                ),
                high_price=self._require_positive_list_number(
                    payload["h"],
                    index,
                    "high price",
                ),
                low_price=self._require_positive_list_number(
                    payload["l"],
                    index,
                    "low price",
                ),
                close_price=self._require_positive_list_number(
                    payload["c"],
                    index,
                    "close price",
                ),
                volume=self._require_non_negative_list_number(
                    payload["v"],
                    index,
                    "volume",
                ),
                currency=normalized_currency,
            )

            if candle.high_price < max(
                candle.open_price,
                candle.close_price,
                candle.low_price,
            ):
                raise APIError(
                    "Finnhub candle high price is inconsistent."
                )

            if candle.low_price > min(
                candle.open_price,
                candle.close_price,
                candle.high_price,
            ):
                raise APIError(
                    "Finnhub candle low price is inconsistent."
                )

            candles.append(candle)

        return candles

    @staticmethod
    def _require_positive_list_number(
        values: list[Any],
        index: int,
        field_name: str,
    ) -> float:
        value = values[index]

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise APIError(
                f"Finnhub candle {field_name} must be numeric."
            )

        numeric_value = float(value)

        if numeric_value <= 0:
            raise APIError(
                f"Finnhub candle {field_name} must be greater than zero."
            )

        return numeric_value

    @staticmethod
    def _require_non_negative_list_number(
        values: list[Any],
        index: int,
        field_name: str,
    ) -> float:
        value = values[index]

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise APIError(
                f"Finnhub candle {field_name} must be numeric."
            )

        numeric_value = float(value)

        if numeric_value < 0:
            raise APIError(
                f"Finnhub candle {field_name} must not be negative."
            )

        return numeric_value
        
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
        
    def get_quote(
        self,
        symbol: str,
        currency: str = "USD",
    ) -> Quote:
        """
        Download and validate the latest quote for a symbol.

        Finnhub's quote endpoint does not provide currency, so the
        caller must supply the expected currency when it is not USD.
        """
        normalized_symbol = symbol.strip().upper()
        normalized_currency = currency.strip().upper()

        if not normalized_symbol:
            raise ValueError("Quote symbol must not be empty.")

        if not normalized_currency:
            raise ValueError("Quote currency must not be empty.")

        payload = self.get_json(
            "/quote",
            params={"symbol": normalized_symbol},
        )

        price = self._require_positive_number(
            payload,
            key="c",
            field_name="current price",
        )

        timestamp_value = self._require_positive_number(
            payload,
            key="t",
            field_name="timestamp",
        )

        timestamp = datetime.fromtimestamp(
            timestamp_value,
            tz=timezone.utc,
        )

        return Quote(
            symbol=normalized_symbol,
            price=price,
            currency=normalized_currency,
            timestamp=timestamp,
        )

    @staticmethod
    def _require_positive_number(
        payload: dict[str, Any],
        key: str,
        field_name: str,
    ) -> float:
        """
        Read and validate a required positive numeric field.
        """
        if key not in payload:
            raise APIError(
                f"Finnhub response is missing {field_name}."
            )

        value = payload[key]

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise APIError(
                f"Finnhub {field_name} must be numeric."
            )

        numeric_value = float(value)

        if numeric_value <= 0:
            raise APIError(
                f"Finnhub {field_name} must be greater than zero."
            )

        return numeric_value

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