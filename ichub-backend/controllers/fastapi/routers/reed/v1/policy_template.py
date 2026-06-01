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
from fastapi import APIRouter, Depends

from services.reed.policy_template_service import PolicyTemplateService
from models.metadata_database.reed.models import ReedPolicyLayer
from models.services.reed.policy_template import (
    PolicyTemplateCreate,
    PolicyTemplateRead,
    RenderedPolicy,
)
from tools.exceptions import exception_responses
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.authentication.auth_api import get_authentication_dependency
from controllers.fastapi.routers.reed.reed_security import require_reed_admin

router = APIRouter(
    prefix="/reed/policy-templates",
    tags=["REED Policy Templates"],
    dependencies=[Depends(get_authentication_dependency())],
)

_service = PolicyTemplateService()
_async = AsyncManagerWrapper(_service, "ReedPolicyTemplate")


@router.get("", response_model=List[PolicyTemplateRead], responses=exception_responses)
async def list_templates(layer: Optional[ReedPolicyLayer] = None) -> List[PolicyTemplateRead]:
    return await _async.list_templates(layer)


@router.get("/{name}", response_model=Optional[PolicyTemplateRead], responses=exception_responses)
async def get_template(name: str) -> Optional[PolicyTemplateRead]:
    return await _async.get_template(name)


@router.get("/{name}/odrl", response_model=RenderedPolicy, responses=exception_responses)
async def render_template(name: str) -> RenderedPolicy:
    """Render the template into an EDC/ODRL policy definition body."""
    return await _async.render(name)


@router.post("", response_model=PolicyTemplateRead, responses=exception_responses,
             dependencies=[Depends(require_reed_admin)])
async def create_template(payload: PolicyTemplateCreate) -> PolicyTemplateRead:
    return await _async.create_template(payload)


@router.delete("/{name}", responses=exception_responses,
               dependencies=[Depends(require_reed_admin)])
async def delete_template(name: str) -> dict:
    await _async.delete_template(name)
    return {"deleted": name}
