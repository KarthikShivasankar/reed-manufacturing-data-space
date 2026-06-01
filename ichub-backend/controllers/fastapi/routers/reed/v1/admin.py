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

from fastapi import APIRouter, Depends, Query

from services.reed.seed_service import SeedService
from tools.exceptions import exception_responses
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.reed.reed_security import require_reed_admin

router = APIRouter(
    prefix="/reed/admin",
    tags=["REED Administration"],
    dependencies=[Depends(require_reed_admin)],
)

_service = SeedService()
_async = AsyncManagerWrapper(_service, "ReedSeed")


@router.post("/seed", responses=exception_responses)
async def seed_defaults(overwrite: bool = Query(default=False)) -> dict:
    """
    Seed (or refresh, when overwrite=true) the default REED policy templates and
    DMP-derived data classification matrix.
    """
    return await _async.seed_defaults(overwrite=overwrite)
