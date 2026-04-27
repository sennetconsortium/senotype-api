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

    def reindex_senotype(self, senotype_id: str) -> bool:
        url = f"{self._base_url}/senotypes/{senotype_id}"
        try:
            response = self._session.put(url, timeout=SERVICE_TIMEOUT)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to reindex senotype {senotype_id}: {e}")
            return False
