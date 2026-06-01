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

"""Service that records and queries REED audit events (T5.3 evidence trail)."""

from typing import List, Optional
from uuid import UUID

from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import (
    ReedAssetClass,
    ReedAuditAction,
    ReedAuditEvent,
    ReedAuditOutcome,
)
from models.services.reed.audit import AuditEventRead


class AuditService:
    """Append-only audit log for REED data-space activity."""

    @staticmethod
    def _to_read(entity: ReedAuditEvent) -> AuditEventRead:
        return AuditEventRead.model_validate(entity)

    def record(
        self,
        action: ReedAuditAction,
        outcome: ReedAuditOutcome = ReedAuditOutcome.SUCCESS,
        actor_user: Optional[str] = None,
        actor_bpn: Optional[str] = None,
        owner_bpn: Optional[str] = None,
        asset_class: Optional[ReedAssetClass] = None,
        manufacturer_part_id: Optional[str] = None,
        usage_purpose: Optional[str] = None,
        policy_template: Optional[str] = None,
        edc_agreement_id: Optional[str] = None,
        access_request_id: Optional[UUID] = None,
        detail: Optional[str] = None,
    ) -> AuditEventRead:
        """Persist a single audit event. Used by all REED flows."""
        with RepositoryManagerFactory.create() as repo:
            entity = ReedAuditEvent(
                action=action,
                outcome=outcome,
                actor_user=actor_user,
                actor_bpn=actor_bpn,
                owner_bpn=owner_bpn,
                asset_class=asset_class,
                manufacturer_part_id=manufacturer_part_id,
                usage_purpose=usage_purpose,
                policy_template=policy_template,
                edc_agreement_id=edc_agreement_id,
                access_request_id=access_request_id,
                detail=detail,
            )
            repo.reed_audit_event_repository.create(entity)
            repo.commit()
            repo.refresh(entity)
            return self._to_read(entity)

    def query(
        self,
        actor_bpn: Optional[str] = None,
        owner_bpn: Optional[str] = None,
        access_request_id: Optional[UUID] = None,
        limit: Optional[int] = 200,
    ) -> List[AuditEventRead]:
        with RepositoryManagerFactory.create() as repo:
            events = repo.reed_audit_event_repository.find_filtered(
                actor_bpn=actor_bpn,
                owner_bpn=owner_bpn,
                access_request_id=access_request_id,
                limit=limit,
            )
            return [self._to_read(e) for e in events]
