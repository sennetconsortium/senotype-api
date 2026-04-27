from typing import Union

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.service import SERVICE_TIMEOUT


class UBKGAPIService:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._session = Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[401, 403, 408, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount(self._base_url, adapter)

    def get_genes_info(self, page: int = 1, per_page: int = 100) -> dict:
        url = f"{self._base_url}/genes-info"
        params = {"page": page, "genes_per_page": per_page}
        response = self._session.get(url, params=params, timeout=SERVICE_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def get_proteins_info(self, page: int = 1, per_page: int = 100) -> dict:
        url = f"{self._base_url}/proteins-info"
        params = {"page": page, "proteins_per_page": per_page}
        response = self._session.get(url, params=params, timeout=SERVICE_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def get_genes(self, gene_ids: Union[list[str], str]) -> list[dict]:
        if isinstance(gene_ids, list):
            url_ids = ",".join(gene_ids)
        else:
            url_ids = gene_ids
        url = f"{self._base_url}/genes/{url_ids}"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def get_proteins(self, protein_ids: Union[list[str], str]) -> list[dict]:
        if isinstance(protein_ids, list):
            url_ids = ",".join(protein_ids)
        else:
            url_ids = protein_ids
        url = f"{self._base_url}/proteins/{url_ids}"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def get_organs(self) -> list[dict]:
        url = f"{self._base_url}/organs?application_context=sennet"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def get_celltypes(self, ids: Union[list[str], str]) -> list[dict]:
        if isinstance(ids, list):
            url_ids = ",".join(ids)
        else:
            url_ids = ids
        url = f"{self._base_url}/celltypes/{url_ids}"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def get_diagnosis_terms(self, code: str) -> list[dict]:
        url = f"{self._base_url}/codes/{code}/terms"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()
