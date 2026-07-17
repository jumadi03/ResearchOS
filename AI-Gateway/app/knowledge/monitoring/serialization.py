"""Lossless serialization for durable discovery monitoring baselines."""

from __future__ import annotations

from dataclasses import asdict

from app.knowledge.models import (
    DiscoveryContract, DiscoveryRun, LiteratureRecord, MatchKind,
    ProviderEnumeration, ProviderFailure, QueryConcept, QueryFamily,
    ScientificQuestion, SearchPlan, SourceDefinition, SourceQuery, SourceRecord,
)


def discovery_run_payload(run: DiscoveryRun) -> dict:
    run.validate_query_plan()
    return asdict(run)


def discovery_run_from_payload(value: dict) -> DiscoveryRun:
    question = ScientificQuestion(**value["question"])
    contract_data = dict(value["discovery_contract"])
    for name in (
        "source_categories", "inclusion_rules", "exclusion_rules", "languages",
        "document_types", "evidence_types", "stopping_conditions",
    ):
        contract_data[name] = tuple(contract_data[name])
    contract = DiscoveryContract(**contract_data)
    plan_data = dict(value["search_plan"])
    plan_data["providers"] = tuple(plan_data["providers"])
    plan_data["concepts"] = tuple(
        QueryConcept(
            **{
                **item,
                "synonyms": tuple(item["synonyms"]),
                "disciplines": tuple(item["disciplines"]),
            }
        )
        for item in plan_data["concepts"]
    )
    plan_data["query_families"] = tuple(
        QueryFamily(
            item["family_id"], tuple(item["concept_ids"]),
            tuple(item["terms"]), item["purpose"],
        )
        for item in plan_data["query_families"]
    )
    plan_data["source_queries"] = tuple(
        SourceQuery(**item) for item in plan_data["source_queries"]
    )
    plan = SearchPlan(**plan_data)
    records = tuple(
        LiteratureRecord(
            record_id=item["record_id"], title=item["title"],
            authors=tuple(item["authors"]), year=item["year"], doi=item["doi"],
            abstract=item["abstract"], venue=item["venue"],
            work_type=item["work_type"],
            source_records=tuple(SourceRecord(**source) for source in item["source_records"]),
            match_kind=MatchKind(item["match_kind"]),
            possible_matches=tuple(item["possible_matches"]),
        )
        for item in value["records"]
    )
    return DiscoveryRun(
        run_id=value["run_id"], question=question, discovery_contract=contract,
        source_definitions=tuple(
            SourceDefinition(
                **{
                    **item,
                    "disciplines": tuple(item["disciplines"]),
                    "content_types": tuple(item["content_types"]),
                }
            )
            for item in value["source_definitions"]
        ),
        search_plan=plan, started_at=value["started_at"],
        enumerations=tuple(ProviderEnumeration(**item) for item in value["enumerations"]),
        records=records,
        failures=tuple(ProviderFailure(**item) for item in value.get("failures", ())),
        schema_version=value.get("schema_version", "1.0"),
    )
