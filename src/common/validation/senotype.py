from collections import defaultdict
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, model_validator
from requests import HTTPError

from common.context import (
    get_entity_api_service,
    get_eutils_api_service,
    get_scicrunch_api_service,
    get_ubkg_api_service,
)
from common.database.valuesets import find_valuesets
from common.decorator import TokenInfo

CellTypeCode = Annotated[str, StringConstraints(pattern=r"^CL:\d+$")]  # cell types
DatasetUUID = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")]  # datasets
HGNCCode = Annotated[str, StringConstraints(pattern=r"^HGNC:\d+$")]  # genes
PMIDCode = Annotated[str, StringConstraints(pattern=r"^PMID:\d+$")]  # citations
UNIPROTKBCode = Annotated[str, StringConstraints(pattern=r"^UNIPROTKB:[A-Z0-9]+$")]  # proteins


class BMI(BaseModel):
    value: float | int
    unit: Literal["kg/m^2"]
    lowerbound: Optional[float | int] = Field(default=None, gt=0)
    upperbound: Optional[float | int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_bounds(self) -> "BMI":
        lb = self.lowerbound
        ub = self.upperbound

        if lb is not None and ub is not None:
            if lb >= ub:
                raise ValueError(f"lowerbound {lb} must be less than upperbound {ub}")

        if lb is not None and self.value < lb:
            raise ValueError(f"value {self.value} must be >= lowerbound {lb}")

        if ub is not None and self.value > ub:
            raise ValueError(f"value {self.value} must be <= upperbound {ub}")

        return self


class Age(BaseModel):
    value: float | int
    unit: Literal["year"]
    lowerbound: Optional[float | int] = Field(default=None, gt=0)
    upperbound: Optional[float | int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_bounds(self) -> "Age":
        lb = self.lowerbound
        ub = self.upperbound

        if lb is not None and ub is not None:
            if lb >= ub:
                raise ValueError(f"lowerbound {lb} must be less than upperbound {ub}")

        if lb is not None and self.value < lb:
            raise ValueError(f"value {self.value} must be >= lowerbound {lb}")

        if ub is not None and self.value > ub:
            raise ValueError(f"value {self.value} must be <= upperbound {ub}")

        return self


class Diagnosis(BaseModel):
    code: str
    term: str


class RegMarker(BaseModel):
    action: Literal["up_regulates", "down_regulates", "inconclusively_regulates"]
    marker: HGNCCode | UNIPROTKBCode


class CreateSenotypeRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    bmi: Optional[BMI]
    age: Optional[Age]
    taxon: Optional[list[str]]
    organ: Optional[list[str]]
    cell_type: Optional[list[CellTypeCode]]
    microenvironment: Optional[list[str]]
    inducer: Optional[list[str]]
    hallmark: Optional[list[str]]
    assay: Optional[list[str]]
    sex: Optional[list[str]]
    diagnosis: Optional[list[Diagnosis]]
    citation: Optional[list[PMIDCode]]
    origin: Optional[list[str]]
    dataset: Optional[list[DatasetUUID]]
    characterizing_marker_set: Optional[list[HGNCCode | UNIPROTKBCode]]
    regulating_marker_set: Optional[list[RegMarker]]


def validate_create_senotype_request(
    req: CreateSenotypeRequest,
    token_info: TokenInfo,
) -> tuple[dict, dict]:
    results = dict()
    errors = dict()

    results["title"] = req.title.strip()
    results["description"] = req.description.strip()

    if req.bmi:
        results["bmi"] = req.bmi.model_dump()
    if req.age:
        results["age"] = req.age.model_dump()

    res, err = _validate_valuesets_fields(req)
    if err:
        errors.update(err)
    else:
        results.update(res)

    res, err = _validate_ubkg_fields(req)
    if err:
        errors.update(err)
    else:
        results.update(res)

    # citation
    res, err = _validate_citation(req)
    if err:
        errors.update(err)
    else:
        results.update(res)

    # origin
    res, err = _validate_origin(req)
    if err:
        errors.update(err)
    else:
        results.update(res)

    # dataset
    res, err = _validate_dataset(req, token_info)
    if err:
        errors.update(err)
    else:
        results.update(res)

    # markers and regmarkers
    res, err = _validate_marker(req)
    if err:
        errors.update(err)
    else:
        results.update(res)

    if errors:
        return {}, errors

    return results, errors


def _validate_valuesets_fields(req: CreateSenotypeRequest) -> tuple[dict, dict]:
    # Fetch for valuesets fields
    valueset_dict = {vs.code: vs for vs in find_valuesets()}
    results = defaultdict(list)
    errors = defaultdict(list)

    # taxon
    if req.taxon:
        for code in req.taxon:
            if code not in valueset_dict:
                errors["taxon"].append(f"Valueset '{code}' not found in valuesets")
                continue
            if valueset_dict[code].predicate_term != "in_taxon":
                errors["taxon"].append(f"Valueset '{code}' is not a taxon code")
                continue
            results["taxon"].append(
                {
                    "code": valueset_dict[code].code,
                    "term": valueset_dict[code].term,
                }
            )

    # microenvironment
    if req.microenvironment:
        for code in req.microenvironment:
            if code not in valueset_dict:
                errors["microenvironment"].append(f"Valueset '{code}' not found in valuesets")
                continue
            if valueset_dict[code].predicate_term != "has_microenvironment":
                errors["microenvironment"].append(
                    f"Valueset '{code}' is not a microenvironment code"
                )
                continue
            results["microenvironment"].append(
                {
                    "code": valueset_dict[code].code,
                    "term": valueset_dict[code].term,
                }
            )

    # inducer
    if req.inducer:
        for code in req.inducer:
            if code not in valueset_dict:
                errors["inducer"].append(f"Valueset '{code}' not found in valuesets")
                continue
            if valueset_dict[code].predicate_term != "has_inducer":
                errors["inducer"].append(f"Valueset '{code}' is not an inducer code")
                continue
            results["inducer"].append(
                {
                    "code": valueset_dict[code].code,
                    "term": valueset_dict[code].term,
                }
            )

    # hallmark
    if req.hallmark:
        for code in req.hallmark:
            if code not in valueset_dict:
                errors["hallmark"].append(f"Valueset '{code}' not found in valuesets")
                continue
            if valueset_dict[code].predicate_term != "has_hallmark":
                errors["hallmark"].append(f"Valueset '{code}' is not a hallmark code")
                continue
            results["hallmark"].append(
                {
                    "code": valueset_dict[code].code,
                    "term": valueset_dict[code].term,
                }
            )

    # assay
    if req.assay:
        for code in req.assay:
            if code not in valueset_dict:
                errors["assay"].append(f"Valueset '{code}' not found in valuesets")
                continue
            if valueset_dict[code].predicate_term != "has_assay":
                errors["assay"].append(f"Valueset '{code}' is not an assay code")
                continue
            results["assay"].append(
                {
                    "code": valueset_dict[code].code,
                    "term": valueset_dict[code].term,
                }
            )

    # sex
    if req.sex:
        for code in req.sex:
            if code not in valueset_dict:
                errors["sex"].append(f"Valueset '{code}' not found in valuesets")
                continue
            if valueset_dict[code].predicate_term != "has_sex":
                errors["sex"].append(f"Valueset '{code}' is not a sex code")
                continue
            results["sex"].append(
                {
                    "code": valueset_dict[code].code,
                    "term": valueset_dict[code].term,
                }
            )

    return dict(results), dict(errors)


def _validate_ubkg_fields(req: CreateSenotypeRequest) -> tuple[dict, dict]:
    ubkg_service = get_ubkg_api_service()
    results = defaultdict(list)
    errors = defaultdict(list)

    # organ
    organs = {org["organ_uberon"]: org for org in ubkg_service.get_organs()}

    if req.organ:
        for code in req.organ:
            if code not in organs:
                errors["organ"].append(f"Organ '{code}' not found in UBKG")
                continue
            organ = organs[code]
            results["organ"].append(
                {
                    "code": organ["organ_uberon"],
                    "term": organ["term"],
                }
            )

    # cell_type
    if req.cell_type:
        celltype_ids = [ct.split(":")[-1] for ct in req.cell_type]
        celltypes = {
            ct["cell_type"]["id"]: ct["cell_type"]
            for ct in ubkg_service.get_celltypes(celltype_ids)
        }

        for code in req.cell_type:
            if code not in celltypes:
                errors["cell_type"].append(f"Cell type '{code}' not found in UBKG")
                continue
            celltype = celltypes[code]
            results["cell_type"].append(
                {
                    "code": celltype["id"],
                    "term": celltype["name"],
                    "definition": celltype["definition"],
                }
            )

    # diagnosis
    if req.diagnosis:
        for diag in req.diagnosis:
            diag_terms = ubkg_service.get_diagnosis_terms(diag.code)
            if len(diag_terms) == 0:
                errors["diagnosis"].append(f"Diagnosis '{diag.code}' not found in UBKG")
                continue

            diag_info = diag_terms[0]
            term = next((term for term in diag_info["terms"] if term["term"] == diag.term), None)
            if term is None:
                errors["diagnosis"].append(
                    f"Diagnosis term mismatch for '{diag.code}': expected '{diag.term}'"
                )
                continue
            results["diagnosis"].append({"code": diag_info["code"], "term": term["term"]})

    return dict(results), dict(errors)


def _validate_citation(req: CreateSenotypeRequest) -> tuple[dict, dict]:
    results = defaultdict(list)
    errors = defaultdict(list)

    if req.citation:
        # PD
        citation_ids = [c.split(":")[-1] for c in req.citation]
        citations = get_eutils_api_service().get_citations(citation_ids).get("result", {})

        for pmid in req.citation:
            uid = pmid.split(":")[-1]
            if uid not in citations:
                errors["citation"].append(f"Citation '{uid}' not found in EUtils")
                continue
            citation = citations[uid]
            results["citation"].append(
                {
                    "code": pmid,
                    "term": citation.get("title"),
                }
            )

    return dict(results), dict(errors)


def _validate_origin(req: CreateSenotypeRequest) -> tuple[dict, dict]:
    scicrunch_service = get_scicrunch_api_service()
    results = defaultdict(list)
    errors = defaultdict(list)

    if req.origin:
        for rrid in req.origin:
            res = scicrunch_service.get_origin(rrid)

            hits = res.get("hits", {}).get("hits", [])
            if not hits:
                errors["origin"].append(f"Origin '{rrid}' not found in SciCrunch")
                continue
            origin_info = hits[0]["_source"]
            if not origin_info:
                errors["origin"].append(f"Origin '{rrid}' not found in SciCrunch")
                continue

            results["origin"].append(
                {
                    "code": rrid,
                    "term": origin_info.get("item", {}).get("name"),
                }
            )

    return dict(results), dict(errors)


def _validate_dataset(req: CreateSenotypeRequest, token_info: TokenInfo) -> tuple[dict, dict]:
    entity_service = get_entity_api_service()
    results = defaultdict(list)
    errors = defaultdict(list)

    if req.dataset:
        for ds_id in req.dataset:
            try:
                res = entity_service.get_entity(ds_id, token=token_info.token.get_secret_value())
                if res["entity_type"].lower() != "dataset":
                    errors["dataset"].append(f"Entity '{ds_id}' is not a dataset")
                    continue

                results["dataset"].append(
                    {
                        "uuid": res["uuid"],
                        "sennet_id": res["sennet_id"],
                        "title": res["title"],
                    }
                )
            except HTTPError as e:
                if e.response.status_code == 404:
                    errors["dataset"].append(f"Dataset '{ds_id}' not found in Entity API")
                elif e.response.status_code == 401:
                    errors["dataset"].append(
                        f"Unauthorized to access Entity API for dataset '{ds_id}'"
                    )
                elif e.response.status_code == 403:
                    errors["dataset"].append(
                        f"Unauthorized to access dataset '{ds_id}' in Entity API"
                    )
                else:
                    raise e

    return dict(results), dict(errors)


def _validate_marker(req: CreateSenotypeRequest) -> tuple[dict, dict]:
    if not req.characterizing_marker_set and not req.regulating_marker_set:
        return {}, {}

    req_markers = req.characterizing_marker_set or []
    req_regmarkers = req.regulating_marker_set or []

    ubkg_service = get_ubkg_api_service()
    results = defaultdict(list)
    errors = defaultdict(list)

    genes = set()
    proteins = set()
    for marker in req_markers:
        if marker.startswith("HGNC:"):
            genes.add(marker.split(":")[-1])
        elif marker.startswith("UNIPROTKB:"):
            proteins.add(marker.split(":")[-1])
        else:
            raise ValueError(f"Marker '{marker}' must start with 'HGNC:' or 'UNIPROTKB:'")

    for regmarker in req_regmarkers:
        if regmarker.marker.startswith("HGNC:"):
            genes.add(regmarker.marker.split(":")[-1])
        elif regmarker.marker.startswith("UNIPROTKB:"):
            proteins.add(regmarker.marker.split(":")[-1])
        else:
            raise ValueError(
                f"RegMarker '{regmarker.marker}' must start with 'HGNC:' or 'UNIPROTKB:'"
            )

    # fetch gene and protein information, combine into a single dict
    all_info = {}
    if genes:
        try:
            gene_info = ubkg_service.get_genes(list(genes))
        except HTTPError as e:
            if e.response.status_code == 404:
                gene_info = []
            else:
                raise e
        all_info.update(
            {
                f"HGNC:{g['hgnc_id']}": {
                    "code": f"HGNC:{g['hgnc_id']}",
                    "term": g["approved_symbol"].strip(),
                    "name": g["approved_name"].strip(),
                }
                for g in gene_info
            }
        )
    if proteins:
        # TODO: update this function when ubkg supports comma-separated list of protein ids
        for protein_id in proteins:
            try:
                protein_info = ubkg_service.get_proteins(protein_id)
            except HTTPError as e:
                if e.response.status_code == 404:
                    continue  # we'll handle missing proteins in the validation loop below
                else:
                    raise e

            if len(protein_info) == 0:
                continue
            p = protein_info[0]
            all_info[f"UNIPROTKB:{p['uniprotkb_id']}"] = {
                "code": f"UNIPROTKB:{p['uniprotkb_id']}",
                "term": p["entry_name"][0].strip(),  # a list in ubkg
                "name": p["recommended_name"][0].strip(),  # a list in ubkg
            }

    for marker in req_markers:
        if marker not in all_info:
            errors["characterizing_marker_set"].append(
                f"Characterizing marker '{marker}' not found in UBKG"
            )
            continue
        results["characterizing_marker_set"].append(all_info[marker])

    for regmarker in req_regmarkers:
        if regmarker.marker not in all_info:
            errors["regulating_marker_set"].append(
                f"Regulating marker '{regmarker.marker}' not found in UBKG"
            )
            continue
        results["regulating_marker_set"].append(
            {
                "action": regmarker.action,
                "marker": all_info[regmarker.marker],
            }
        )

    return dict(results), dict(errors)
