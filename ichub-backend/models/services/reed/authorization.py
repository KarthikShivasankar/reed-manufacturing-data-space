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

from models.metadata_database.reed.models import ReedAssetClass


class AuthorizationContext(BaseModel):
    """
    The combined identity + dynamic context evaluated by the REED authorization
    engine before any EDC/DTR call.

    Identity claims normally come from the Keycloak/OIDC token; dynamic context
    (project membership, NDA state, supply-chain relationship, requested purpose)
    is resolved by the REED backend.
    """
    # Identity claims (from Keycloak token)
    user: Optional[str] = Field(default=None, description="Subject / preferred_username of the caller.")
    bpn: str = Field(description="Organization BPN of the caller.")
    roles: List[str] = Field(default_factory=list, description="Realm roles, e.g. ['oem-manager'].")
    projects: List[str] = Field(default_factory=list, description="Project groups the caller belongs to.")
    membership_active: bool = Field(
        default=False, alias="membershipActive", description="Whether dataspace membership is active."
    )
    framework_agreement: Optional[str] = Field(
        default=None, alias="frameworkAgreement", description="Accepted framework agreement, if any."
    )
    nda_active: bool = Field(default=False, alias="ndaActive", description="Whether an NDA is in place.")

    # Request context
    owner_bpn: str = Field(alias="ownerBpn", description="BPN of the data owner being accessed.")
    asset_class: ReedAssetClass = Field(alias="assetClass", description="The REED asset class being accessed.")
    usage_purpose: Optional[str] = Field(
        default=None, alias="usagePurpose", description="Declared usage purpose of the access."
    )
    project: Optional[str] = Field(default=None, description="REED project the access is scoped to.")

    model_config = {"populate_by_name": True}


class AuthorizationDecision(BaseModel):
    """Result of a REED authorization evaluation."""
    allowed: bool = Field(description="Whether the action is permitted.")
    reasons: List[str] = Field(
        default_factory=list, description="Human-readable reasons supporting the decision."
    )
    matched_policy_template: Optional[str] = Field(
        default=None, alias="matchedPolicyTemplate",
        description="The policy template that would govern the inter-company contract."
    )
    required_obligations: List[str] = Field(
        default_factory=list, alias="requiredObligations",
        description="Obligations that will be attached to the data on transfer."
    )

    model_config = {"populate_by_name": True}
