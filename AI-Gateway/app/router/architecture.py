"""FastAPI routes for staged ResearchOS architecture governance."""

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.architecture.models import ArchitectureLaw, ArchitectureLawBundle, LawScope
from app.architecture.authentication import ArchitectureRole, AuthenticatedPrincipal
from app.architecture.pipeline_service import ArchitecturePipelineRun
from app.models.architecture import (
    ARCRequest, ComplianceRequest, FinalizeReviewRequest, LawBundleRequest,
    OpenReviewRequest, ReviewDecisionRequest, ScanRequest,
)


router = APIRouter(prefix="/architecture", tags=["architecture"])
bearer = HTTPBearer(auto_error=False)


def _service(request: Request):
    return request.app.state.architecture_service


def _audit(
    request: Request,
    event_type: str,
    *,
    actor: str | None,
    outcome: str,
    details: dict[str, object] | None = None,
) -> None:
    trail = getattr(request.app.state, "audit_trail", None)
    if trail is not None:
        trail.record(
            event_type,
            actor=actor,
            outcome=outcome,
            details=details,
        )


def _principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthenticatedPrincipal:
    try:
        authorization = (
            f"{credentials.scheme} {credentials.credentials}"
            if credentials is not None
            else None
        )
        principal = request.app.state.architecture_authenticator.authenticate(
            authorization
        )
        return principal
    except PermissionError as exc:
        _audit(
            request,
            "architecture_authentication",
            actor=None,
            outcome="denied",
            details={"reason": str(exc)},
        )
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _authorize(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    role: ArchitectureRole,
) -> AuthenticatedPrincipal:
    principal = _principal(request, credentials)
    if not principal.has_role(role):
        _audit(
            request,
            "architecture_authorization",
            actor=principal.actor_id,
            outcome="denied",
            details={"required_role": role.value},
        )
        raise HTTPException(
            status_code=403,
            detail=f"Role required: {role.value}",
        )
    return principal


def _summary(run: ArchitecturePipelineRun) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "graph": {
            "graph_id": run.graph.graph_id,
            "content_hash": run.graph.content_hash,
            "nodes": len(run.graph.nodes),
            "edges": len(run.graph.edges),
        },
        "law_bundle": (
            {"bundle_id": run.law_bundle.bundle_id,
             "content_hash": run.law_bundle.content_hash,
             "laws": len(run.law_bundle.laws)}
            if run.law_bundle else None
        ),
        "compliance": (
            {"status": run.compliance_report.status,
             "is_compliant": run.compliance_report.is_compliant,
             "findings": sum(len(item.violations) for item in run.compliance_report.validation_results)}
            if run.compliance_report else None
        ),
        "review": (
            {"review_id": run.review.review_id, "status": run.review.status.value,
             "findings": len(run.review.findings), "decisions": len(run.review.decisions)}
            if run.review else None
        ),
        "arc": (
            {"arc_id": run.arc_package.manifest.arc_id,
             "verified": run.arc_package.verify(),
             "artifacts": sorted(run.arc_package.all_files())}
            if run.arc_package else None
        ),
    }


def _execute(action):
    try:
        return _summary(action())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/runs", status_code=201)
def scan(req: ScanRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    _authorize(request, credentials, ArchitectureRole.SCANNER)
    return _execute(lambda: _service(request).scan(
        project_name=req.project_name, source_revision=req.source_revision
    ))


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    _authorize(request, credentials, ArchitectureRole.AUDITOR)
    return _execute(lambda: _service(request).get(run_id))


@router.put("/runs/{run_id}/laws")
def register_laws(run_id: str, req: LawBundleRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    _authorize(request, credentials, ArchitectureRole.LAW_ADMIN)
    bundle = ArchitectureLawBundle(
        "", req.version,
        tuple(
            ArchitectureLaw(
                law.law_id, law.title, law.description, law.version,
                category=law.category, severity=law.severity,
                scope=LawScope(tuple(law.scope.node_types), tuple(law.scope.path_patterns)),
                condition=law.condition, remediation=law.remediation,
                effective_from=law.effective_from, effective_until=law.effective_until,
                enabled=law.enabled,
            )
            for law in req.laws
        ),
    ).finalized()
    return _execute(lambda: _service(request).register_laws(run_id, bundle))


@router.post("/runs/{run_id}/compliance")
def compliance(run_id: str, req: ComplianceRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    _authorize(request, credentials, ArchitectureRole.SCANNER)
    result = _execute(lambda: _service(request).run_compliance(run_id, as_of=req.as_of))
    registry = getattr(request.app.state, "metrics_registry", None)
    if registry is not None:
        registry.increment(
            "researchos_compliance_runs_total",
            labels={"status": result["compliance"]["status"]},
        )
        registry.increment(
            "researchos_compliance_findings_total",
            value=result["compliance"]["findings"],
        )
    return result


@router.post("/runs/{run_id}/review", status_code=201)
def open_review(run_id: str, req: OpenReviewRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    actor = _authorize(
        request, credentials, ArchitectureRole.REVIEWER
    ).actor_id
    return _execute(lambda: _service(request).open_review(
        run_id, reviewer=actor, opened_at=req.opened_at
    ))


@router.post("/runs/{run_id}/review/decisions")
def decide(run_id: str, req: ReviewDecisionRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    actor = _authorize(
        request, credentials, ArchitectureRole.REVIEWER
    ).actor_id
    return _execute(lambda: _service(request).decide(
        run_id, finding_id=req.finding_id, decision_type=req.decision_type,
        rationale=req.rationale, reviewer=actor, decided_at=req.decided_at,
        expires_at=req.expires_at,
    ))


@router.post("/runs/{run_id}/review/finalize")
def finalize_review(run_id: str, req: FinalizeReviewRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    actor = _authorize(
        request, credentials, ArchitectureRole.APPROVER
    ).actor_id
    result = _execute(lambda: _service(request).finalize_review(
        run_id, actor=actor, occurred_at=req.occurred_at, as_of=req.as_of
    ))
    registry = getattr(request.app.state, "metrics_registry", None)
    if registry is not None:
        registry.increment(
            "researchos_reviews_finalized_total",
            labels={"status": result["review"]["status"]},
        )
    return result


@router.post("/runs/{run_id}/arc", status_code=201)
def generate_arc(run_id: str, req: ARCRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    actor = _authorize(
        request, credentials, ArchitectureRole.PUBLISHER
    ).actor_id
    _audit(
        request,
        "arc_publication",
        actor=actor,
        outcome="attempted",
        details={"run_id": run_id, "publish": req.publish},
    )
    try:
        result = _execute(lambda: _service(request).generate_arc(
            run_id, generated_at=req.generated_at, publish=req.publish,
            actor=actor,
        ))
    except HTTPException as exc:
        _audit(
            request,
            "arc_publication",
            actor=actor,
            outcome="failed",
            details={"run_id": run_id, "status_code": exc.status_code},
        )
        raise
    _audit(
        request,
        "arc_publication",
        actor=actor,
        outcome="succeeded",
        details={"run_id": run_id, "arc_id": result["arc"]["arc_id"]},
    )
    registry = getattr(request.app.state, "metrics_registry", None)
    if registry is not None:
        registry.increment("researchos_arc_publications_total", labels={"status": "success"})
    return result
