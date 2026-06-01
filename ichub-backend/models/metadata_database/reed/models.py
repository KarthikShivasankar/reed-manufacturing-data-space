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

"""
Database models for the REED Manufacturing Data Space layer.

REED builds a domain-specific manufacturing data space on top of the Tractus-X
stack (EDC, DTR, submodel services, Keycloak). These SQLModel entities persist
the REED-owned use-case layer:

- ``ReedAssetClassification``: the DMP-derived data classification matrix entries
  that map a REED asset class to a sensitivity, discoverability, payload location
  and default policy template.
- ``ReedPolicyTemplate``: named catalogue/contract/usage policy templates that are
  rendered into EDC/ODRL policy definitions.
- ``ReedSupplyChainRelation``: edges of the supply-chain graph between BPNs.
- ``ReedAccessRequest``: consumer access-request workflow state (submitted,
  approved, rejected, ...), including the selected policy template and the
  resulting EDC contract agreement reference.
- ``ReedAuditEvent``: tamper-evident audit records linking participant, user,
  BPN, asset, purpose, contract agreement, timestamp and transfer outcome.

The actual confidential payloads are never stored here - they live in the
submodel service and are only referenced by location, exactly like the PCF
exchange tracking model.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class ReedAssetClass(str, Enum):
    """First-class REED manufacturing asset types (see the data classification matrix)."""
    PART_DIGITAL_TWIN = "PartDigitalTwin"
    BILL_OF_MATERIAL = "BillOfMaterial"
    DIGITAL_PRODUCT_PASSPORT = "DigitalProductPassport"
    PROCESS_CAPABILITY = "ProcessCapability"
    FIXTURE_HANDLING_STRATEGY = "FixtureHandlingStrategy"
    PRODUCTION_STATUS = "ProductionStatus"
    QUALITY_EVIDENCE = "QualityEvidence"
    SIMULATION_RESULT = "SimulationResult"


class ReedSensitivity(str, Enum):
    """Sensitivity classification derived from the WP2 Data Management Plan."""
    PUBLIC = "public"
    CONSORTIUM = "consortium"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"


class ReedDiscoverability(str, Enum):
    """Who may discover that the metadata exists in DTR/EDC catalogues."""
    PUBLIC = "public"
    CONSORTIUM = "consortium"
    PROJECT = "project"
    BILATERAL = "bilateral"
    HIDDEN = "hidden"


class ReedPolicyLayer(str, Enum):
    """The three REED policy layers aligned with Task 5.3."""
    CATALOGUE = "catalogue"   # can a partner discover that metadata exists?
    CONTRACT = "contract"     # can a partner negotiate access?
    USAGE = "usage"           # obligations/prohibitions attached to the data


class ReedRelationType(str, Enum):
    """Type of edge in the REED supply-chain graph."""
    SUPPLIES_TO = "supplies_to"        # provider supplies a part to a customer
    SUB_SUPPLIER_OF = "sub_supplier_of"
    SERVICE_PROVIDER_FOR = "service_provider_for"
    OEM_OF = "oem_of"


class ReedAccessRequestStatus(str, Enum):
    """Workflow state of a consumer access request."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONTRACTED = "contracted"   # EDC contract agreement reached
    TRANSFERRED = "transferred" # data transferred through the EDC data plane
    EXPIRED = "expired"
    REVOKED = "revoked"


class ReedAuditAction(str, Enum):
    """Auditable REED actions."""
    ASSET_PUBLISHED = "asset_published"
    CATALOGUE_VIEWED = "catalogue_viewed"
    ACCESS_REQUESTED = "access_requested"
    ACCESS_APPROVED = "access_approved"
    ACCESS_REJECTED = "access_rejected"
    CONTRACT_NEGOTIATED = "contract_negotiated"
    DATA_TRANSFERRED = "data_transferred"
    AUTHORIZATION_DENIED = "authorization_denied"


class ReedAuditOutcome(str, Enum):
    """Outcome recorded against an audit event."""
    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"


class ReedAssetClassification(SQLModel, table=True):
    """
    A single entry in the REED data classification matrix.

    Maps a REED asset class to its AAS/submodel mapping, sensitivity,
    discoverability, payload location, allowed purposes, obligations,
    prohibitions and the default policy template used when an EDC asset of
    this class is published. The catalogue/EDC only exposes discoverable
    metadata; the confidential payload stays in the submodel service.
    """
    __tablename__ = "reed_asset_classification"
    __table_args__ = {"schema": "public"}

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_class: ReedAssetClass = Field(
        index=True, unique=True,
        description="The REED asset class this classification applies to."
    )
    submodel_semantic_id: Optional[str] = Field(
        default=None,
        description="The AAS submodel semantic ID (semanticId) used for this asset class."
    )
    sensitivity: ReedSensitivity = Field(
        default=ReedSensitivity.CONFIDENTIAL,
        description="DMP-derived sensitivity classification."
    )
    discoverability: ReedDiscoverability = Field(
        default=ReedDiscoverability.CONSORTIUM,
        description="Who may discover the metadata of this asset class."
    )
    payload_storage: Optional[str] = Field(
        default=None,
        description="Where the payload lives (submodel service endpoint, object store, external system)."
    )
    default_policy_template: Optional[str] = Field(
        default=None, index=True,
        description="Name of the default REED policy template applied to assets of this class."
    )
    allowed_purposes: List[str] = Field(
        default_factory=list, sa_column=Column(JSON),
        description="Permitted usage purposes (e.g. DPP read, simulation, quality audit)."
    )
    obligations: List[str] = Field(
        default_factory=list, sa_column=Column(JSON),
        description="Obligations attached to the data (audit, delete-after, watermark, aggregate-only)."
    )
    prohibitions: List[str] = Field(
        default_factory=list, sa_column=Column(JSON),
        description="Prohibitions attached to the data (no onward sharing, no AI training, no raw download)."
    )
    description: Optional[str] = Field(
        default=None, description="Human-readable description of this classification entry."
    )


class ReedPolicyTemplate(SQLModel, table=True):
    """
    A named REED policy template for one of the three policy layers.

    The ``constraints`` and ``obligations``/``prohibitions`` fields hold the
    abstract REED business rules. They are rendered into EDC/ODRL policy
    definitions by the policy template service when an asset is published or a
    contract is negotiated.
    """
    __tablename__ = "reed_policy_template"
    __table_args__ = {"schema": "public"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True, unique=True,
        description="Unique template name, e.g. 'simulation-service-only'."
    )
    layer: ReedPolicyLayer = Field(
        index=True,
        description="Which REED policy layer this template belongs to."
    )
    description: Optional[str] = Field(default=None, description="What this template is for.")
    constraints: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON),
        description="Abstract constraints, each {leftOperand, operator, rightOperand}."
    )
    obligations: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON),
        description="Abstract obligations rendered into the ODRL obligation list."
    )
    prohibitions: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON),
        description="Abstract prohibitions rendered into the ODRL prohibition list."
    )
    is_builtin: bool = Field(
        default=False,
        description="True for templates seeded by REED; built-in templates cannot be deleted."
    )


class ReedSupplyChainRelation(SQLModel, table=True):
    """
    A directed edge of the REED supply-chain graph between two BPNs, optionally
    scoped to a project and a manufacturer part.
    """
    __tablename__ = "reed_supply_chain_relation"
    __table_args__ = {"schema": "public"}

    id: Optional[int] = Field(default=None, primary_key=True)
    parent_bpn: str = Field(index=True, description="BPN of the parent/customer/OEM side of the relation.")
    child_bpn: str = Field(index=True, description="BPN of the child/supplier/service-provider side.")
    relation_type: ReedRelationType = Field(
        default=ReedRelationType.SUPPLIES_TO,
        description="The type of supply-chain relationship."
    )
    project: Optional[str] = Field(default=None, index=True, description="REED project this relation belongs to.")
    manufacturer_part_id: Optional[str] = Field(
        default=None, description="Optional part this relation is scoped to."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp."
    )


class ReedAccessRequest(SQLModel, table=True):
    """
    A consumer access request flowing through the REED access workflow.

    The request captures the requesting/owning BPNs, the requested asset class,
    the declared usage purpose, the selected policy template and the resulting
    EDC contract agreement / transfer references once negotiation completes.
    """
    __tablename__ = "reed_access_request"
    __table_args__ = {"schema": "public"}

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: UUID = Field(
        default_factory=uuid4, index=True,
        description="Stable public identifier for the access request."
    )
    requesting_bpn: str = Field(index=True, description="BPN of the consumer requesting access.")
    requesting_user: Optional[str] = Field(default=None, description="User/subject who submitted the request.")
    owner_bpn: str = Field(index=True, description="BPN of the data owner/provider.")
    asset_class: ReedAssetClass = Field(description="The REED asset class being requested.")
    manufacturer_part_id: Optional[str] = Field(default=None, description="Optional part identifier in scope.")
    usage_purpose: str = Field(description="Declared usage purpose for the request.")
    project: Optional[str] = Field(default=None, index=True, description="REED project context.")
    policy_template: Optional[str] = Field(
        default=None, description="Selected REED policy template name."
    )
    status: ReedAccessRequestStatus = Field(
        default=ReedAccessRequestStatus.SUBMITTED, index=True,
        description="Current workflow status."
    )
    decision_reason: Optional[str] = Field(default=None, description="Reason for approval/rejection.")
    edc_agreement_id: Optional[str] = Field(default=None, description="EDC contract agreement ID after negotiation.")
    edc_transfer_id: Optional[str] = Field(default=None, description="EDC transfer process ID after transfer.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the request was submitted."
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the request was last updated."
    )
    expires_at: Optional[datetime] = Field(default=None, description="Optional expiry of the granted access.")


class ReedAuditEvent(SQLModel, table=True):
    """
    A REED audit record. Provides the T5.3 evidence trail: participant, user,
    BPN, asset, purpose, contract agreement, timestamp and transfer outcome.
    """
    __tablename__ = "reed_audit_event"
    __table_args__ = {"schema": "public"}

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: UUID = Field(default_factory=uuid4, index=True, description="Stable public identifier.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True,
        description="When the event occurred."
    )
    action: ReedAuditAction = Field(index=True, description="The audited action.")
    outcome: ReedAuditOutcome = Field(
        default=ReedAuditOutcome.SUCCESS, index=True, description="Outcome of the action."
    )
    actor_user: Optional[str] = Field(default=None, description="User/subject who performed the action.")
    actor_bpn: Optional[str] = Field(default=None, index=True, description="BPN of the acting participant.")
    owner_bpn: Optional[str] = Field(default=None, index=True, description="BPN of the data owner.")
    asset_class: Optional[ReedAssetClass] = Field(default=None, description="Asset class involved.")
    manufacturer_part_id: Optional[str] = Field(default=None, description="Part identifier involved.")
    usage_purpose: Optional[str] = Field(default=None, description="Declared usage purpose.")
    policy_template: Optional[str] = Field(default=None, description="Policy template applied.")
    edc_agreement_id: Optional[str] = Field(default=None, description="EDC contract agreement reference.")
    access_request_id: Optional[UUID] = Field(default=None, description="Related access request, if any.")
    detail: Optional[str] = Field(default=None, description="Free-text detail / denial reason.")


# Convenience list of all REED tables so they can be created without touching
# the externally managed DDL for the rest of the metadata database.
REED_TABLES = [
    ReedAssetClassification,
    ReedPolicyTemplate,
    ReedSupplyChainRelation,
    ReedAccessRequest,
    ReedAuditEvent,
]
