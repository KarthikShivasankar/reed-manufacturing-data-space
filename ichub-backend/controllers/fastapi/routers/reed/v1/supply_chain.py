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

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from services.reed.supply_chain_service import SupplyChainService
from models.services.reed.supply_chain import (
    SupplyChainRelationCreate,
    SupplyChainRelationRead,
)
from tools.exceptions import exception_responses
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.authentication.auth_api import get_authentication_dependency
from controllers.fastapi.routers.reed.reed_security import ReedPrincipal, get_reed_principal

router = APIRouter(
    prefix="/reed/supply-chain",
    tags=["REED Supply Chain"],
    dependencies=[Depends(get_authentication_dependency())],
)

_service = SupplyChainService()
_async = AsyncManagerWrapper(_service, "ReedSupplyChain")


@router.get("/relations", response_model=List[SupplyChainRelationRead], responses=exception_responses)
async def list_relations() -> List[SupplyChainRelationRead]:
    return await _async.list_relations()


@router.get("/relations/{bpn}", response_model=List[SupplyChainRelationRead], responses=exception_responses)
async def get_relations_for_bpn(bpn: str) -> List[SupplyChainRelationRead]:
    """All relations where the BPN appears on either side of the edge."""
    return await _async.get_relations_for_bpn(bpn)


@router.post("/relations", response_model=SupplyChainRelationRead, responses=exception_responses)
async def create_relation(
    payload: SupplyChainRelationCreate,
    principal: ReedPrincipal = Depends(get_reed_principal),
) -> SupplyChainRelationRead:
    """
    Create a supply-chain relation edge. A REED admin may declare any edge; a
    regular participant may only declare an edge their own organization is part
    of (counterparty acknowledgement remains a future workflow enhancement).
    """
    if not principal.is_admin and principal.bpn not in (payload.parent_bpn, payload.child_bpn):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only declare supply-chain relations involving your own BPN.",
        )
    return await _async.create_relation(payload)
