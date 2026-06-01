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

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from models.metadata_database.reed.models import ReedAssetClass, ReedAccessRequestStatus


class AccessRequestCreate(BaseModel):
    requesting_bpn: str = Field(alias="requestingBpn", description="BPN of the consumer requesting access.")
    requesting_user: Optional[str] = Field(
        default=None, alias="requestingUser", description="User/subject who submitted the request."
    )
    owner_bpn: str = Field(alias="ownerBpn", description="BPN of the data owner/provider.")
    asset_class: ReedAssetClass = Field(alias="assetClass", description="The REED asset class being requested.")
    manufacturer_part_id: Optional[str] = Field(
        default=None, alias="manufacturerPartId", description="Optional part identifier in scope."
    )
    usage_purpose: str = Field(alias="usagePurpose", description="Declared usage purpose for the request.")
    project: Optional[str] = Field(default=None, description="REED project context.")
    policy_template: Optional[str] = Field(
        default=None, alias="policyTemplate", description="Selected REED policy template name."
    )

    model_config = {"populate_by_name": True}


class AccessRequestDecision(BaseModel):
    approve: bool = Field(description="True to approve, false to reject the request.")
    reason: Optional[str] = Field(default=None, description="Reason for the decision.")
    decided_by: Optional[str] = Field(
        default=None, alias="decidedBy", description="User/subject making the decision."
    )

    model_config = {"populate_by_name": True}


class AccessRequestRead(BaseModel):
    request_id: UUID = Field(alias="requestId", description="Public identifier for the access request.")
    requesting_bpn: str = Field(alias="requestingBpn")
    requesting_user: Optional[str] = Field(default=None, alias="requestingUser")
    owner_bpn: str = Field(alias="ownerBpn")
    asset_class: ReedAssetClass = Field(alias="assetClass")
    manufacturer_part_id: Optional[str] = Field(default=None, alias="manufacturerPartId")
    usage_purpose: str = Field(alias="usagePurpose")
    project: Optional[str] = None
    policy_template: Optional[str] = Field(default=None, alias="policyTemplate")
    status: ReedAccessRequestStatus
    decision_reason: Optional[str] = Field(default=None, alias="decisionReason")
    edc_agreement_id: Optional[str] = Field(default=None, alias="edcAgreementId")
    edc_transfer_id: Optional[str] = Field(default=None, alias="edcTransferId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")

    model_config = {"populate_by_name": True, "from_attributes": True}
