#################################################################################
# Eclipse Tractus-X - Industry Core Hub Backend
#
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the
# License for the specific language govern in permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
#################################################################################

from fastapi import APIRouter, Depends

from services.reed.authorization_service import AuthorizationService
from services.reed.audit_service import AuditService
from models.metadata_database.reed.models import ReedAuditAction, ReedAuditOutcome
from models.services.reed.authorization import AuthorizationContext, AuthorizationDecision
from tools.exceptions import exception_responses
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.reed.reed_security import ReedPrincipal, get_reed_principal

router = APIRouter(
    prefix="/reed/authorization",
    tags=["REED Authorization"],
)

_service = AuthorizationService()
_audit = AuditService()
_async = AsyncManagerWrapper(_service, "ReedAuthorization")
_async_audit = AsyncManagerWrapper(_audit, "ReedAudit")


@router.post("/evaluate", response_model=AuthorizationDecision, responses=exception_responses)
async def evaluate(
    ctx: AuthorizationContext,
    principal: ReedPrincipal = Depends(get_reed_principal),
) -> AuthorizationDecision:
    """
    Evaluate the REED context-based authorization decision for a caller against a
    target asset. This is the check the REED backend performs before calling EDC
    or exposing DTR/submodel metadata. Denied evaluations are recorded in the
    audit log.

    For Keycloak-authenticated users the caller identity (BPN, roles, projects,
    membership / framework-agreement / NDA state) is taken from the validated
    token and overrides any identity supplied in the body, so it cannot be
    spoofed. Only the request context (owner BPN, asset class, usage purpose,
    project) is honoured from the body. API-key (service) callers are trusted and
    may supply identity directly.
    """
    if not principal.is_service:
        ctx = ctx.model_copy(update={
            "user": principal.user,
            "bpn": principal.bpn,
            "roles": principal.roles,
            "projects": principal.projects,
            "membership_active": principal.membership_active,
            "framework_agreement": principal.framework_agreement,
            "nda_active": principal.nda_active,
        })

    decision: AuthorizationDecision = await _async.authorize(ctx)
    if not decision.allowed:
        await _async_audit.record(
            action=ReedAuditAction.AUTHORIZATION_DENIED,
            outcome=ReedAuditOutcome.DENIED,
            actor_user=ctx.user,
            actor_bpn=ctx.bpn,
            owner_bpn=ctx.owner_bpn,
            asset_class=ctx.asset_class,
            usage_purpose=ctx.usage_purpose,
            policy_template=decision.matched_policy_template,
            detail="; ".join(decision.reasons),
        )
    return decision
