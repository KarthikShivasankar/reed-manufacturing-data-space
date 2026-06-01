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

"""Repositories for the REED metadata tables, built on the shared BaseRepository."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlmodel import select, desc

from managers.metadata_database.repositories import BaseRepository
from models.metadata_database.reed.models import (
    ReedAssetClassification,
    ReedPolicyTemplate,
    ReedSupplyChainRelation,
    ReedAccessRequest,
    ReedAuditEvent,
    ReedAssetClass,
    ReedAccessRequestStatus,
)


class ReedAssetClassificationRepository(BaseRepository[ReedAssetClassification]):

    def get_by_asset_class(self, asset_class: ReedAssetClass) -> Optional[ReedAssetClassification]:
        stmt = select(ReedAssetClassification).where(
            ReedAssetClassification.asset_class == asset_class)
        return self._session.scalars(stmt).first()


class ReedPolicyTemplateRepository(BaseRepository[ReedPolicyTemplate]):

    def get_by_name(self, name: str) -> Optional[ReedPolicyTemplate]:
        stmt = select(ReedPolicyTemplate).where(ReedPolicyTemplate.name == name)
        return self._session.scalars(stmt).first()


class ReedSupplyChainRelationRepository(BaseRepository[ReedSupplyChainRelation]):

    def find_by_bpn(self, bpn: str) -> List[ReedSupplyChainRelation]:
        """Return all relations where the BPN is on either side of the edge."""
        stmt = select(ReedSupplyChainRelation).where(
            (ReedSupplyChainRelation.parent_bpn == bpn)
            | (ReedSupplyChainRelation.child_bpn == bpn)
        )
        return list(self._session.scalars(stmt).unique())

    def exists_relation(self, parent_bpn: str, child_bpn: str) -> bool:
        stmt = select(ReedSupplyChainRelation).where(
            ReedSupplyChainRelation.parent_bpn == parent_bpn,
            ReedSupplyChainRelation.child_bpn == child_bpn,
        )
        return self._session.scalars(stmt).first() is not None

    def are_related(self, bpn_a: str, bpn_b: str) -> bool:
        """True if an edge exists between the two BPNs in either direction."""
        return self.exists_relation(bpn_a, bpn_b) or self.exists_relation(bpn_b, bpn_a)


class ReedAccessRequestRepository(BaseRepository[ReedAccessRequest]):

    def get_by_request_id(self, request_id: UUID) -> Optional[ReedAccessRequest]:
        stmt = select(ReedAccessRequest).where(ReedAccessRequest.request_id == request_id)
        return self._session.scalars(stmt).first()

    def find_filtered(
        self,
        owner_bpn: Optional[str] = None,
        requesting_bpn: Optional[str] = None,
        status: Optional[ReedAccessRequestStatus] = None,
    ) -> List[ReedAccessRequest]:
        stmt = select(ReedAccessRequest)
        if owner_bpn is not None:
            stmt = stmt.where(ReedAccessRequest.owner_bpn == owner_bpn)
        if requesting_bpn is not None:
            stmt = stmt.where(ReedAccessRequest.requesting_bpn == requesting_bpn)
        if status is not None:
            stmt = stmt.where(ReedAccessRequest.status == status)
        stmt = stmt.order_by(desc(ReedAccessRequest.created_at))
        return list(self._session.scalars(stmt).unique())


class ReedAuditEventRepository(BaseRepository[ReedAuditEvent]):

    def find_filtered(
        self,
        actor_bpn: Optional[str] = None,
        owner_bpn: Optional[str] = None,
        access_request_id: Optional[UUID] = None,
        limit: Optional[int] = 200,
    ) -> List[ReedAuditEvent]:
        stmt = select(ReedAuditEvent)
        if actor_bpn is not None:
            stmt = stmt.where(ReedAuditEvent.actor_bpn == actor_bpn)
        if owner_bpn is not None:
            stmt = stmt.where(ReedAuditEvent.owner_bpn == owner_bpn)
        if access_request_id is not None:
            stmt = stmt.where(ReedAuditEvent.access_request_id == access_request_id)
        stmt = stmt.order_by(desc(ReedAuditEvent.created_at))
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self._session.scalars(stmt).unique())
