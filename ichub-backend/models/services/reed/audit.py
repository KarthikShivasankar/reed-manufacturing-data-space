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

from models.metadata_database.reed.models import (
    ReedAssetClass,
    ReedAuditAction,
    ReedAuditOutcome,
)


class AuditEventRead(BaseModel):
    event_id: UUID = Field(alias="eventId")
    created_at: datetime = Field(alias="createdAt")
    action: ReedAuditAction
    outcome: ReedAuditOutcome
    actor_user: Optional[str] = Field(default=None, alias="actorUser")
    actor_bpn: Optional[str] = Field(default=None, alias="actorBpn")
    owner_bpn: Optional[str] = Field(default=None, alias="ownerBpn")
    asset_class: Optional[ReedAssetClass] = Field(default=None, alias="assetClass")
    manufacturer_part_id: Optional[str] = Field(default=None, alias="manufacturerPartId")
    usage_purpose: Optional[str] = Field(default=None, alias="usagePurpose")
    policy_template: Optional[str] = Field(default=None, alias="policyTemplate")
    edc_agreement_id: Optional[str] = Field(default=None, alias="edcAgreementId")
    access_request_id: Optional[UUID] = Field(default=None, alias="accessRequestId")
    detail: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True}
