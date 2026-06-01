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

"""Service managing the REED data classification matrix (DMP-derived)."""

from typing import List, Optional

from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import ReedAssetClass, ReedAssetClassification
from models.services.reed.classification import (
    AssetClassificationCreate,
    AssetClassificationRead,
    AssetClassificationUpdate,
)
from tools.exceptions import AlreadyExistsError, NotFoundError


class ClassificationService:
    """CRUD for the REED asset classification matrix."""

    @staticmethod
    def _to_read(entity: ReedAssetClassification) -> AssetClassificationRead:
        return AssetClassificationRead(
            assetClass=entity.asset_class,
            submodelSemanticId=entity.submodel_semantic_id,
            sensitivity=entity.sensitivity,
            discoverability=entity.discoverability,
            payloadStorage=entity.payload_storage,
            defaultPolicyTemplate=entity.default_policy_template,
            allowedPurposes=entity.allowed_purposes or [],
            obligations=entity.obligations or [],
            prohibitions=entity.prohibitions or [],
            description=entity.description,
        )

    def list_classifications(self) -> List[AssetClassificationRead]:
        with RepositoryManagerFactory.create() as repo:
            return [self._to_read(e) for e in repo.reed_asset_classification_repository.find_all(limit=None)]

    def get_classification(self, asset_class: ReedAssetClass) -> Optional[AssetClassificationRead]:
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_asset_classification_repository.get_by_asset_class(asset_class)
            return self._to_read(entity) if entity else None

    def create_classification(self, payload: AssetClassificationCreate) -> AssetClassificationRead:
        with RepositoryManagerFactory.create() as repo:
            existing = repo.reed_asset_classification_repository.get_by_asset_class(payload.asset_class)
            if existing:
                raise AlreadyExistsError(
                    f"Classification for asset class '{payload.asset_class.value}' already exists."
                )
            entity = ReedAssetClassification(
                asset_class=payload.asset_class,
                submodel_semantic_id=payload.submodel_semantic_id,
                sensitivity=payload.sensitivity,
                discoverability=payload.discoverability,
                payload_storage=payload.payload_storage,
                default_policy_template=payload.default_policy_template,
                allowed_purposes=payload.allowed_purposes,
                obligations=payload.obligations,
                prohibitions=payload.prohibitions,
                description=payload.description,
            )
            repo.reed_asset_classification_repository.create(entity)
            repo.commit()
            repo.refresh(entity)
            return self._to_read(entity)

    def update_classification(
        self, asset_class: ReedAssetClass, payload: AssetClassificationUpdate
    ) -> AssetClassificationRead:
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_asset_classification_repository.get_by_asset_class(asset_class)
            if not entity:
                raise NotFoundError(f"Classification for asset class '{asset_class.value}' not found.")
            data = payload.model_dump(exclude_unset=True, by_alias=False)
            for field, value in data.items():
                setattr(entity, field, value)
            repo.commit()
            repo.refresh(entity)
            return self._to_read(entity)
