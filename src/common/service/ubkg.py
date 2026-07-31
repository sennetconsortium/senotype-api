from typing import Literal, Optional, Union

from requests import HTTPError, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.service import SERVICE_TIMEOUT


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class UBKGAPIService:
    def __init__(self, base_url: str, batch_size: int = 100):
        self._base_url = base_url.rstrip("/")
        self._batch_size = batch_size
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

    def get_genes(
        self,
        gene_ids: Union[list[str], str],
        organism: Optional[Literal["human", "mouse"]] = None,
    ) -> list[dict]:
        ids = gene_ids if isinstance(gene_ids, list) else [gene_ids]
        params = {"organism": organism} if organism else None
        return self._get_batched("genes", ids, params=params)

    def get_proteins(self, protein_ids: Union[list[str], str]) -> list[dict]:
        ids = protein_ids if isinstance(protein_ids, list) else [protein_ids]
        return self._get_batched("proteins", ids)

    def get_organs(self) -> list[dict]:
        url = f"{self._base_url}/organs?application_context=sennet"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def get_celltypes(self, ids: Union[list[str], str]) -> list[dict]:
        id_list = ids if isinstance(ids, list) else [ids]
        return self._get_batched("celltypes", id_list)

    def get_diagnosis_terms(self, code: str) -> list[dict]:
        url = f"{self._base_url}/codes/{code}/terms"
        res = self._session.get(url, timeout=SERVICE_TIMEOUT)
        res.raise_for_status()
        return res.json()

    def _get_batched(self, path: str, ids: list[str], params: Optional[dict] = None) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(ids, self._batch_size):
            url = f"{self._base_url}/{path}/{','.join(chunk)}"
            try:
                res = self._session.get(url, params=params, timeout=SERVICE_TIMEOUT)
                res.raise_for_status()
                results.extend(res.json())
            except HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
        return results
