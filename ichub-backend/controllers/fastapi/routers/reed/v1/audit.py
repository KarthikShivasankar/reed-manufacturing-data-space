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

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.reed.audit_service import AuditService
from models.services.reed.audit import AuditEventRead
from tools.exceptions import exception_responses
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.reed.reed_security import ReedPrincipal, get_reed_principal

router = APIRouter(
    prefix="/reed/audit",
    tags=["REED Audit"],
)

_service = AuditService()
_async = AsyncManagerWrapper(_service, "ReedAudit")


@router.get("/events", response_model=List[AuditEventRead], responses=exception_responses)
async def query_audit_events(
    principal: ReedPrincipal = Depends(get_reed_principal),
    actor_bpn: Optional[str] = Query(default=None, alias="actorBpn"),
    owner_bpn: Optional[str] = Query(default=None, alias="ownerBpn"),
    access_request_id: Optional[UUID] = Query(default=None, alias="accessRequestId"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> List[AuditEventRead]:
    """
    Query the REED audit trail. REED admins see all events; a regular participant
    only sees events their own organization is the actor or owner of.
    """
    if not principal.is_admin:
        if not principal.bpn:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caller has no BPN; cannot query the audit trail.",
            )
        events = await _async.query(access_request_id=access_request_id, limit=limit)
        return [e for e in events if principal.bpn in (e.actor_bpn, e.owner_bpn)]
    return await _async.query(
        actor_bpn=actor_bpn,
        owner_bpn=owner_bpn,
        access_request_id=access_request_id,
        limit=limit,
    )
