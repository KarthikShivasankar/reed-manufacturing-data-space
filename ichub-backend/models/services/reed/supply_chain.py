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
from pydantic import BaseModel, Field

from models.metadata_database.reed.models import ReedRelationType


class SupplyChainRelationCreate(BaseModel):
    parent_bpn: str = Field(alias="parentBpn", description="BPN of the parent/customer/OEM side.")
    child_bpn: str = Field(alias="childBpn", description="BPN of the child/supplier/service-provider side.")
    relation_type: ReedRelationType = Field(
        default=ReedRelationType.SUPPLIES_TO, alias="relationType",
        description="The type of supply-chain relationship."
    )
    project: Optional[str] = Field(default=None, description="REED project this relation belongs to.")
    manufacturer_part_id: Optional[str] = Field(
        default=None, alias="manufacturerPartId", description="Optional part this relation is scoped to."
    )

    model_config = {"populate_by_name": True}


class SupplyChainRelationRead(SupplyChainRelationCreate):
    id: int = Field(description="Database identifier of the relation.")
