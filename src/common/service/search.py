from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.service import SERVICE_TIMEOUT


class SearchAPIService:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._session = Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[408, 429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount(self._base_url, adapter)

    def reindex_senotype(self, uuid: str, token: str | None = None):
        headers = None
        if token:
            headers = {"Authorization": f"Bearer {token}"}

        # TODO: Remove todo suffix once senotypes are fully implemented
        url = f"{self._base_url}/senotypes/reindex/test/{uuid}"
        response = self._session.put(url, headers=headers, timeout=SERVICE_TIMEOUT)
        response.raise_for_status()
