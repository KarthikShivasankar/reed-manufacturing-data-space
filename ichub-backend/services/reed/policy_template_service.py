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
Service managing REED policy templates and rendering them into EDC/ODRL policy
definitions.

A template stores abstract constraints/obligations/prohibitions. The renderer
turns them into the ODRL shape that the Tractus-X EDC management API understands,
using the standard ``cx-policy`` / ``odrl`` / ``edc`` JSON-LD contexts.
"""

from typing import Any, Dict, List, Optional

from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import ReedPolicyTemplate, ReedPolicyLayer
from models.services.reed.policy_template import (
    PolicyTemplateCreate,
    PolicyTemplateRead,
    RenderedPolicy,
)
from tools.exceptions import AlreadyExistsError, InvalidError, NotFoundError

# Standard JSON-LD context used by Tractus-X EDC policy definitions.
ODRL_CONTEXT: Dict[str, str] = {
    "tx": "https://w3id.org/tractusx/v0.0.1/ns/",
    "tx-auth": "https://w3id.org/tractusx/auth/",
    "cx-policy": "https://w3id.org/catenax/policy/",
    "reed": "https://w3id.org/reed/policy/",
    "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
    "edc": "https://w3id.org/edc/v0.0.1/ns/",
    "odrl": "http://www.w3.org/ns/odrl/2/",
}


class PolicyTemplateService:
    """CRUD plus ODRL rendering for REED policy templates."""

    @staticmethod
    def _to_read(entity: ReedPolicyTemplate) -> PolicyTemplateRead:
        return PolicyTemplateRead(
            name=entity.name,
            layer=entity.layer,
            description=entity.description,
            constraints=entity.constraints or [],
            obligations=entity.obligations or [],
            prohibitions=entity.prohibitions or [],
            isBuiltin=entity.is_builtin,
        )

    def list_templates(self, layer: Optional[ReedPolicyLayer] = None) -> List[PolicyTemplateRead]:
        with RepositoryManagerFactory.create() as repo:
            templates = repo.reed_policy_template_repository.find_all(limit=None)
            if layer is not None:
                templates = [t for t in templates if t.layer == layer]
            return [self._to_read(t) for t in templates]

    def get_template(self, name: str) -> Optional[PolicyTemplateRead]:
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_policy_template_repository.get_by_name(name)
            return self._to_read(entity) if entity else None

    def create_template(self, payload: PolicyTemplateCreate) -> PolicyTemplateRead:
        with RepositoryManagerFactory.create() as repo:
            if repo.reed_policy_template_repository.get_by_name(payload.name):
                raise AlreadyExistsError(f"Policy template '{payload.name}' already exists.")
            entity = ReedPolicyTemplate(
                name=payload.name,
                layer=payload.layer,
                description=payload.description,
                constraints=payload.constraints,
                obligations=payload.obligations,
                prohibitions=payload.prohibitions,
                is_builtin=False,
            )
            repo.reed_policy_template_repository.create(entity)
            repo.commit()
            repo.refresh(entity)
            return self._to_read(entity)

    def delete_template(self, name: str) -> None:
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_policy_template_repository.get_by_name(name)
            if not entity:
                raise NotFoundError(f"Policy template '{name}' not found.")
            if entity.is_builtin:
                raise InvalidError(f"Built-in policy template '{name}' cannot be deleted.")
            repo.reed_policy_template_repository.delete_obj(entity)
            repo.commit()

    # ----- ODRL rendering -----

    @staticmethod
    def _render_constraint(constraint: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "leftOperand": constraint.get("leftOperand") or constraint.get("left_operand"),
            "operator": constraint.get("operator", "odrl:eq"),
            "rightOperand": constraint.get("rightOperand", constraint.get("right_operand")),
        }

    def render(self, name: str) -> RenderedPolicy:
        """Render a stored template into an EDC/ODRL policy definition body."""
        with RepositoryManagerFactory.create() as repo:
            entity = repo.reed_policy_template_repository.get_by_name(name)
            if not entity:
                raise NotFoundError(f"Policy template '{name}' not found.")
            return self.render_entity(entity)

    def render_entity(self, entity: ReedPolicyTemplate) -> RenderedPolicy:
        constraints = [self._render_constraint(c) for c in (entity.constraints or [])]

        permission: Dict[str, Any] = {"action": "odrl:use"}
        if constraints:
            permission["constraint"] = (
                constraints[0] if len(constraints) == 1
                else {"and": constraints}
            )

        prohibitions: List[Dict[str, Any]] = []
        for p in (entity.prohibitions or []):
            entry: Dict[str, Any] = {"action": p.get("action", "odrl:use")}
            if p.get("leftOperand") or p.get("left_operand"):
                entry["constraint"] = self._render_constraint(p)
            prohibitions.append(entry)

        obligations: List[Dict[str, Any]] = []
        for o in (entity.obligations or []):
            entry = {"action": o.get("action", "reed:audit")}
            if o.get("leftOperand") or o.get("left_operand"):
                entry["constraint"] = self._render_constraint(o)
            obligations.append(entry)

        odrl: Dict[str, Any] = {
            "@context": ODRL_CONTEXT,
            "@type": "PolicyDefinitionRequest",
            "@id": f"reed-{entity.layer.value}-{entity.name}",
            "policy": {
                "@type": "odrl:Set",
                "odrl:permission": [permission],
                "odrl:prohibition": prohibitions,
                "odrl:obligation": obligations,
            },
        }
        return RenderedPolicy(templateName=entity.name, layer=entity.layer, odrl=odrl)
