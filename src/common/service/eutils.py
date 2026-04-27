from typing import Union

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.service import SERVICE_TIMEOUT


class EUtilsAPIService:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._session = Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[408, 429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount(self._base_url, adapter)

    def get_citations(self, ids: Union[list[str], str]) -> dict:
        if isinstance(ids, list):
            query_uids = ",".join(ids)
        else:
            query_uids = ids

        url = f"{self._base_url}/entrez/eutils/esummary.fcgi"
        params = {"db": "pubmed", "retmode": "json", "id": query_uids}
        res = self._session.get(url, params=params, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()
