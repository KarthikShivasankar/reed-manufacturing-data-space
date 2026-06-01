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

from services.reed.access_request_service import AccessRequestService
from models.metadata_database.reed.models import ReedAccessRequestStatus
from models.services.reed.access_request import (
    AccessRequestCreate,
    AccessRequestDecision,
    AccessRequestRead,
)
from tools.exceptions import exception_responses, NotFoundError
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.reed.reed_security import ReedPrincipal, get_reed_principal

router = APIRouter(
    prefix="/reed/access-requests",
    tags=["REED Access Requests"],
)

_service = AccessRequestService()
_async = AsyncManagerWrapper(_service, "ReedAccessRequest")


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


@router.post("", response_model=AccessRequestRead, responses=exception_responses)
async def submit_access_request(
    payload: AccessRequestCreate,
    principal: ReedPrincipal = Depends(get_reed_principal),
) -> AccessRequestRead:
    """
    Submit an access request. For Keycloak users the requesting BPN/user are taken
    from the token so a caller cannot submit on behalf of another organization.
    """
    if not principal.is_service:
        if principal.bpn:
            payload = payload.model_copy(update={"requesting_bpn": principal.bpn})
        payload = payload.model_copy(update={"requesting_user": principal.user})
    return await _async.submit(payload)


@router.get("", response_model=List[AccessRequestRead], responses=exception_responses)
async def list_access_requests(
    principal: ReedPrincipal = Depends(get_reed_principal),
    owner_bpn: Optional[str] = Query(default=None, alias="ownerBpn"),
    requesting_bpn: Optional[str] = Query(default=None, alias="requestingBpn"),
    status: Optional[ReedAccessRequestStatus] = None,
) -> List[AccessRequestRead]:
    # Non-admin callers may only see requests their own organization is party to.
    if not principal.is_admin:
        if not principal.bpn:
            raise _forbidden("Caller has no BPN; cannot list access requests.")
        results = await _async.list(owner_bpn=owner_bpn, requesting_bpn=requesting_bpn, status=status)
        return [
            r for r in results
            if principal.bpn in (r.owner_bpn, r.requesting_bpn)
        ]
    return await _async.list(owner_bpn=owner_bpn, requesting_bpn=requesting_bpn, status=status)


@router.get("/{request_id}", response_model=Optional[AccessRequestRead], responses=exception_responses)
async def get_access_request(
    request_id: UUID,
    principal: ReedPrincipal = Depends(get_reed_principal),
) -> Optional[AccessRequestRead]:
    entity = await _async.get(request_id)
    if entity is None:
        return None
    if not principal.is_admin and principal.bpn not in (entity.owner_bpn, entity.requesting_bpn):
        raise _forbidden("You are not a party to this access request.")
    return entity


@router.post("/{request_id}/decision", response_model=AccessRequestRead, responses=exception_responses)
async def decide_access_request(
    request_id: UUID,
    decision: AccessRequestDecision,
    principal: ReedPrincipal = Depends(get_reed_principal),
) -> AccessRequestRead:
    """
    Approve or reject a request. Only the data owner (or a REED admin) may decide,
    and the decider identity is taken from the authenticated principal.
    """
    entity = await _async.get(request_id)
    if entity is None:
        raise NotFoundError(f"Access request '{request_id}' not found.")
    if not principal.is_admin and principal.bpn != entity.owner_bpn:
        raise _forbidden("Only the data owner may decide this access request.")
    if not principal.is_service:
        decision = decision.model_copy(update={"decided_by": principal.user})
    return await _async.decide(request_id, decision)


@router.post("/{request_id}/contract", response_model=AccessRequestRead, responses=exception_responses)
async def mark_access_request_contracted(
    request_id: UUID,
    principal: ReedPrincipal = Depends(get_reed_principal),
    edc_agreement_id: str = Query(alias="edcAgreementId"),
    edc_transfer_id: Optional[str] = Query(default=None, alias="edcTransferId"),
) -> AccessRequestRead:
    """Record the EDC contract agreement (and optional transfer) for an approved request.

    Only a party to the request (owner or requester) or a REED admin may do this.
    """
    entity = await _async.get(request_id)
    if entity is None:
        raise NotFoundError(f"Access request '{request_id}' not found.")
    if not principal.is_admin and principal.bpn not in (entity.owner_bpn, entity.requesting_bpn):
        raise _forbidden("You are not a party to this access request.")
    return await _async.mark_contracted(request_id, edc_agreement_id, edc_transfer_id)
