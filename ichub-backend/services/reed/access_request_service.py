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
REED access-request workflow service.

Implements the consumer access workflow from the MVP data-exchange flow:
submit -> review/decision -> contracted -> transferred. Each transition records
an audit event and (on approval) resolves the REED policy template that governs
the downstream EDC contract definition.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import (
    ReedAccessRequest,
    ReedAccessRequestStatus,
    ReedAuditAction,
    ReedAuditOutcome,
)
from models.services.reed.access_request import (
    AccessRequestCreate,
    AccessRequestDecision,
    AccessRequestRead,
)
from services.reed.audit_service import AuditService
from tools.exceptions import InvalidError, NotFoundError


class AccessRequestService:
    """Manage the lifecycle of consumer access requests."""

    def __init__(self) -> None:
        self._audit = AuditService()

    @staticmethod
    def _to_read(entity: ReedAccessRequest) -> AccessRequestRead:
        return AccessRequestRead.model_validate(entity)

    def submit(self, payload: AccessRequestCreate) -> AccessRequestRead:
        with RepositoryManagerFactory.create() as repo:
            # Default the policy template to the asset class default if not provided.
            policy_template = payload.policy_template
            if policy_template is None:
                classification = repo.reed_asset_classification_repository.get_by_asset_class(
                    payload.asset_class
                )
                if classification:
                    policy_template = classification.default_policy_template

            entity = ReedAccessRequest(
                requesting_bpn=payload.requesting_bpn,
                requesting_user=payload.requesting_user,
                owner_bpn=payload.owner_bpn,
                asset_class=payload.asset_class,
                manufacturer_part_id=payload.manufacturer_part_id,
                usage_purpose=payload.usage_purpose,
                project=payload.project,
                policy_template=policy_template,
                status=ReedAccessRequestStatus.SUBMITTED,
            )
            repo.reed_access_request_repository.create(entity)
            repo.commit()
            repo.refresh(entity)
            result = self._to_read(entity)

        self._audit.record(
            action=ReedAuditAction.ACCESS_REQUESTED,
            actor_user=payload.requesting_user,
            actor_bpn=payload.requesting_bpn,
            owner_bpn=payload.owner_bpn,
            asset_class=payload.asset_class,
            manufacturer_part_id=payload.manufacturer_part_id,
            usage_purpose=payload.usage_purpose,
            policy_template=result.policy_template,
            access_request_id=result.request_id,
        )
        return result

    def get(self, request_id: UUID) -> Optional[AccessRequestRead]:
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_access_request_repository.get_by_request_id(request_id)
            return self._to_read(entity) if entity else None

    def list(
        self,
        owner_bpn: Optional[str] = None,
        requesting_bpn: Optional[str] = None,
        status: Optional[ReedAccessRequestStatus] = None,
    ) -> List[AccessRequestRead]:
        with RepositoryManagerFactory.create() as repo:
            return [
                self._to_read(e)
                for e in repo.reed_access_request_repository.find_filtered(
                    owner_bpn=owner_bpn, requesting_bpn=requesting_bpn, status=status
                )
            ]

    def decide(self, request_id: UUID, decision: AccessRequestDecision) -> AccessRequestRead:
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_access_request_repository.get_by_request_id(request_id)
            if not entity:
                raise NotFoundError(f"Access request '{request_id}' not found.")
            if entity.status not in (
                ReedAccessRequestStatus.SUBMITTED,
                ReedAccessRequestStatus.UNDER_REVIEW,
            ):
                raise InvalidError(
                    f"Access request '{request_id}' cannot be decided from status '{entity.status.value}'."
                )
            entity.status = (
                ReedAccessRequestStatus.APPROVED if decision.approve
                else ReedAccessRequestStatus.REJECTED
            )
            entity.decision_reason = decision.reason
            entity.updated_at = datetime.now(timezone.utc)
            repo.commit()
            repo.refresh(entity)
            result = self._to_read(entity)

        self._audit.record(
            action=(
                ReedAuditAction.ACCESS_APPROVED if decision.approve
                else ReedAuditAction.ACCESS_REJECTED
            ),
            outcome=ReedAuditOutcome.SUCCESS if decision.approve else ReedAuditOutcome.DENIED,
            actor_user=decision.decided_by,
            actor_bpn=result.owner_bpn,
            owner_bpn=result.owner_bpn,
            asset_class=result.asset_class,
            manufacturer_part_id=result.manufacturer_part_id,
            usage_purpose=result.usage_purpose,
            policy_template=result.policy_template,
            access_request_id=result.request_id,
            detail=decision.reason,
        )
        return result

    def mark_contracted(
        self, request_id: UUID, edc_agreement_id: str, edc_transfer_id: Optional[str] = None
    ) -> AccessRequestRead:
        """Record the EDC contract agreement (and optional transfer) for an approved request."""
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_access_request_repository.get_by_request_id(request_id)
            if not entity:
                raise NotFoundError(f"Access request '{request_id}' not found.")
            if entity.status not in (
                ReedAccessRequestStatus.APPROVED,
                ReedAccessRequestStatus.CONTRACTED,
            ):
                raise InvalidError(
                    f"Access request '{request_id}' must be approved before it can be contracted."
                )
            entity.edc_agreement_id = edc_agreement_id
            if edc_transfer_id:
                entity.edc_transfer_id = edc_transfer_id
                entity.status = ReedAccessRequestStatus.TRANSFERRED
            else:
                entity.status = ReedAccessRequestStatus.CONTRACTED
            entity.updated_at = datetime.now(timezone.utc)
            repo.commit()
            repo.refresh(entity)
            result = self._to_read(entity)

        self._audit.record(
            action=(
                ReedAuditAction.DATA_TRANSFERRED if edc_transfer_id
                else ReedAuditAction.CONTRACT_NEGOTIATED
            ),
            actor_bpn=result.requesting_bpn,
            owner_bpn=result.owner_bpn,
            asset_class=result.asset_class,
            manufacturer_part_id=result.manufacturer_part_id,
            usage_purpose=result.usage_purpose,
            policy_template=result.policy_template,
            edc_agreement_id=edc_agreement_id,
            access_request_id=result.request_id,
        )
        return result
