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

from services.reed.classification_service import ClassificationService
from models.metadata_database.reed.models import ReedAssetClass
from models.services.reed.classification import (
    AssetClassificationCreate,
    AssetClassificationRead,
    AssetClassificationUpdate,
)
from tools.exceptions import exception_responses
from utils.async_utils import AsyncManagerWrapper
from controllers.fastapi.routers.authentication.auth_api import get_authentication_dependency
from controllers.fastapi.routers.reed.reed_security import require_reed_admin

router = APIRouter(
    prefix="/reed/classification",
    tags=["REED Data Classification"],
    dependencies=[Depends(get_authentication_dependency())],
)

_service = ClassificationService()
_async = AsyncManagerWrapper(_service, "ReedClassification")


@router.get("", response_model=List[AssetClassificationRead], responses=exception_responses)
async def list_classifications() -> List[AssetClassificationRead]:
    return await _async.list_classifications()


@router.get("/{asset_class}", response_model=Optional[AssetClassificationRead], responses=exception_responses)
async def get_classification(asset_class: ReedAssetClass) -> Optional[AssetClassificationRead]:
    return await _async.get_classification(asset_class)


@router.post("", response_model=AssetClassificationRead, responses=exception_responses,
             dependencies=[Depends(require_reed_admin)])
async def create_classification(payload: AssetClassificationCreate) -> AssetClassificationRead:
    return await _async.create_classification(payload)


@router.patch("/{asset_class}", response_model=AssetClassificationRead, responses=exception_responses,
              dependencies=[Depends(require_reed_admin)])
async def update_classification(
    asset_class: ReedAssetClass, payload: AssetClassificationUpdate
) -> AssetClassificationRead:
    return await _async.update_classification(asset_class, payload)
