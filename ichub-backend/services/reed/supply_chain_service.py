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

"""Service managing the REED supply-chain graph."""

from typing import List

from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import ReedSupplyChainRelation
from models.services.reed.supply_chain import (
    SupplyChainRelationCreate,
    SupplyChainRelationRead,
)
from tools.exceptions import AlreadyExistsError


class SupplyChainService:
    """Manage and query the supply-chain relationship graph between BPNs."""

    @staticmethod
    def _to_read(entity: ReedSupplyChainRelation) -> SupplyChainRelationRead:
        return SupplyChainRelationRead(
            id=entity.id,
            parentBpn=entity.parent_bpn,
            childBpn=entity.child_bpn,
            relationType=entity.relation_type,
            project=entity.project,
            manufacturerPartId=entity.manufacturer_part_id,
        )

    def create_relation(self, payload: SupplyChainRelationCreate) -> SupplyChainRelationRead:
        with RepositoryManagerFactory.create() as repo:
            if repo.reed_supply_chain_relation_repository.exists_relation(
                payload.parent_bpn, payload.child_bpn
            ):
                raise AlreadyExistsError(
                    f"Relation {payload.parent_bpn} -> {payload.child_bpn} already exists."
                )
            entity = ReedSupplyChainRelation(
                parent_bpn=payload.parent_bpn,
                child_bpn=payload.child_bpn,
                relation_type=payload.relation_type,
                project=payload.project,
                manufacturer_part_id=payload.manufacturer_part_id,
            )
            repo.reed_supply_chain_relation_repository.create(entity)
            repo.commit()
            repo.refresh(entity)
            return self._to_read(entity)

    def list_relations(self) -> List[SupplyChainRelationRead]:
        with RepositoryManagerFactory.create() as repo:
            return [self._to_read(e) for e in repo.reed_supply_chain_relation_repository.find_all(limit=None)]

    def get_relations_for_bpn(self, bpn: str) -> List[SupplyChainRelationRead]:
        with RepositoryManagerFactory.create() as repo:
            return [self._to_read(e) for e in repo.reed_supply_chain_relation_repository.find_by_bpn(bpn)]

    def are_related(self, bpn_a: str, bpn_b: str) -> bool:
        with RepositoryManagerFactory.create() as repo:
            return repo.reed_supply_chain_relation_repository.are_related(bpn_a, bpn_b)
