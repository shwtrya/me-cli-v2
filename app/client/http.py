import logging
import time
from dataclasses import dataclass
from typing import Iterable, Mapping, Any

import requests

DEFAULT_TIMEOUT = 30
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)


@dataclass
class HttpClientError(Exception):
    user_message: str
    original_error: Exception | None = None

    def __str__(self) -> str:
        return self.user_message


def _map_exception_to_message(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        return "Permintaan ke server melewati batas waktu. Silakan coba lagi."
    if isinstance(exc, requests.ConnectionError):
        return "Tidak dapat terhubung ke server. Periksa koneksi Anda."
    if isinstance(exc, requests.HTTPError):
        return "Server mengembalikan kesalahan. Silakan coba lagi."
    return "Terjadi kesalahan saat menghubungi server. Silakan coba lagi."


def _sleep_with_backoff(backoff_factor: float, attempt: int) -> None:
    delay = backoff_factor * (2 ** attempt)
    time.sleep(delay)


def send_request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    data: Any | None = None,
    json: Any | None = None,
    timeout: int | float = DEFAULT_TIMEOUT,
    retries: int = 2,
    backoff_factor: float = 0.5,
    retry_statuses: Iterable[int] = RETRYABLE_STATUS_CODES,
    raise_for_status: bool = False,
) -> requests.Response:
    for attempt in range(retries + 1):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                timeout=timeout,
            )
            status = response.status_code
            logger.info("HTTP %s %s -> %s", method, url, status)

            if status in retry_statuses and attempt < retries:
                logger.warning(
                    "Retrying HTTP %s %s (status=%s, attempt=%s)",
                    method,
                    url,
                    status,
                    attempt + 1,
                )
                _sleep_with_backoff(backoff_factor, attempt)
                continue

            if raise_for_status:
                response.raise_for_status()

            return response
        except (requests.Timeout, requests.ConnectionError) as exc:
            logger.warning(
                "HTTP %s %s failed (attempt=%s): %s",
                method,
                url,
                attempt + 1,
                exc.__class__.__name__,
            )
            if attempt < retries:
                _sleep_with_backoff(backoff_factor, attempt)
                continue
            raise HttpClientError(_map_exception_to_message(exc), exc) from exc
        except requests.RequestException as exc:
            logger.warning(
                "HTTP %s %s error: %s",
                method,
                url,
                exc.__class__.__name__,
            )
            raise HttpClientError(_map_exception_to_message(exc), exc) from exc

    raise HttpClientError("Terjadi kesalahan saat menghubungi server.")
