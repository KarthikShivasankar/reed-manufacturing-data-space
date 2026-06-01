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

from models.metadata_database.reed.models import (
    ReedAssetClass,
    ReedSensitivity,
    ReedDiscoverability,
)


class AssetClassificationBase(BaseModel):
    submodel_semantic_id: Optional[str] = Field(
        default=None, alias="submodelSemanticId",
        description="AAS submodel semantic ID for this asset class."
    )
    sensitivity: ReedSensitivity = Field(
        default=ReedSensitivity.CONFIDENTIAL, description="DMP-derived sensitivity."
    )
    discoverability: ReedDiscoverability = Field(
        default=ReedDiscoverability.CONSORTIUM, description="Who may discover the metadata."
    )
    payload_storage: Optional[str] = Field(
        default=None, alias="payloadStorage", description="Where the payload is stored."
    )
    default_policy_template: Optional[str] = Field(
        default=None, alias="defaultPolicyTemplate",
        description="Default REED policy template applied to assets of this class."
    )
    allowed_purposes: List[str] = Field(
        default_factory=list, alias="allowedPurposes", description="Permitted usage purposes."
    )
    obligations: List[str] = Field(default_factory=list, description="Obligations attached to the data.")
    prohibitions: List[str] = Field(default_factory=list, description="Prohibitions attached to the data.")
    description: Optional[str] = Field(default=None, description="Human-readable description.")

    model_config = {"populate_by_name": True}


class AssetClassificationCreate(AssetClassificationBase):
    asset_class: ReedAssetClass = Field(alias="assetClass", description="The REED asset class.")


class AssetClassificationUpdate(AssetClassificationBase):
    """All fields optional for partial updates."""
    sensitivity: Optional[ReedSensitivity] = None
    discoverability: Optional[ReedDiscoverability] = None


class AssetClassificationRead(AssetClassificationBase):
    asset_class: ReedAssetClass = Field(alias="assetClass", description="The REED asset class.")
