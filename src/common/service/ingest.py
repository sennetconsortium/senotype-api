from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.service import SERVICE_TIMEOUT


class IngestAPIService:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._session = Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[408, 429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount(self._base_url, adapter)

    def get_senotype_privs(self, token: str) -> dict:
        headers = {"Authorization": f"Bearer {token}"}

        url = f"{self._base_url}/privs/senotype"
        res = self._session.get(url, headers=headers, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def get_token_info(self, token: str) -> dict:
        headers = {"Authorization": f"Bearer {token}"}

        url = f"{self._base_url}/token-introspect"
        res = self._session.get(url, headers=headers, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        return data
