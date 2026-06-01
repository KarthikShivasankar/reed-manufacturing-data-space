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
Seeds the default REED policy catalogue and DMP-derived data classification
matrix described in docs/architecture/reed-manufacturing-data-space.md.

Seeding is idempotent: existing entries (matched by name / asset class) are left
untouched unless ``overwrite=True`` is passed. The built-in templates and
classifications give a working pilot configuration out of the box.
"""

from typing import Any, Dict, List

from managers.config.log_manager import LoggingManager
from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import (
    ReedAssetClass,
    ReedAssetClassification,
    ReedDiscoverability,
    ReedPolicyLayer,
    ReedPolicyTemplate,
    ReedSensitivity,
)

logger = LoggingManager.get_logger(__name__)


# ----- Default policy templates (catalogue / contract / usage layers) -----

DEFAULT_POLICY_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "public-metadata",
        "layer": ReedPolicyLayer.CATALOGUE,
        "description": "Non-sensitive catalogue discovery; payload is not exposed.",
        "constraints": [],
        "obligations": [],
        "prohibitions": [],
    },
    {
        "name": "consortium-only",
        "layer": ReedPolicyLayer.CATALOGUE,
        "description": "REED pilot members discovering shared metadata.",
        "constraints": [
            {"leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active"},
        ],
        "obligations": [],
        "prohibitions": [],
    },
    {
        "name": "bilateral-supplier",
        "layer": ReedPolicyLayer.CONTRACT,
        "description": "OEM and a named supplier exchange under NDA.",
        "constraints": [
            {"leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active"},
            {"leftOperand": "cx-policy:FrameworkAgreement", "operator": "odrl:eq",
             "rightOperand": "DataExchangeGovernance:1.0"},
            {"leftOperand": "reed:Nda", "operator": "odrl:eq", "rightOperand": "active"},
        ],
        "obligations": [{"action": "reed:audit"}],
        "prohibitions": [{"action": "reed:onwardSharing"}],
    },
    {
        "name": "oem-only",
        "layer": ReedPolicyLayer.CONTRACT,
        "description": "Supplier exposes sensitive engineering/quality data to an OEM.",
        "constraints": [
            {"leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active"},
            {"leftOperand": "reed:Role", "operator": "odrl:eq", "rightOperand": "oem-manager"},
        ],
        "obligations": [{"action": "reed:audit"}],
        "prohibitions": [{"action": "reed:onwardSharing"}],
    },
    {
        "name": "simulation-service-only",
        "layer": ReedPolicyLayer.CONTRACT,
        "description": "Service provider processes a specific simulation/optimization dataset.",
        "constraints": [
            {"leftOperand": "cx-policy:UsagePurpose", "operator": "odrl:eq",
             "rightOperand": "reed.pilot.process-simulation:1"},
        ],
        "obligations": [
            {"action": "reed:audit"},
            {"action": "reed:delete", "leftOperand": "reed:retentionDays", "operator": "odrl:eq",
             "rightOperand": "90"},
        ],
        "prohibitions": [
            {"action": "reed:aiTraining"},
            {"action": "reed:onwardSharing"},
        ],
    },
    {
        "name": "dpp-read-only",
        "layer": ReedPolicyLayer.USAGE,
        "description": "DPP/DMP traceability and compliance evidence, read-only.",
        "constraints": [
            {"leftOperand": "cx-policy:UsagePurpose", "operator": "odrl:eq",
             "rightOperand": "reed.dpp.read:1"},
        ],
        "obligations": [{"action": "reed:audit"}],
        "prohibitions": [{"action": "reed:onwardSharing"}],
    },
    {
        "name": "time-limited-pilot-access",
        "layer": ReedPolicyLayer.CONTRACT,
        "description": "Short-lived pilot exchange within a validity window.",
        "constraints": [
            {"leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active"},
            {"leftOperand": "reed:ContractExpiry", "operator": "odrl:lteq",
             "rightOperand": "P30D"},
        ],
        "obligations": [{"action": "reed:audit"}],
        "prohibitions": [],
    },
    {
        "name": "anonymized-benchmark-access",
        "layer": ReedPolicyLayer.USAGE,
        "description": "Aggregated benchmark / sustainability reporting only.",
        "constraints": [
            {"leftOperand": "cx-policy:UsagePurpose", "operator": "odrl:eq",
             "rightOperand": "reed.benchmark.aggregate:1"},
        ],
        "obligations": [{"action": "reed:aggregateOnly"}],
        "prohibitions": [
            {"action": "reed:reIdentification"},
            {"action": "reed:rawDownload"},
        ],
    },
]


# ----- Default data classification matrix (8 REED asset classes) -----

DEFAULT_CLASSIFICATIONS: List[Dict[str, Any]] = [
    {
        "asset_class": ReedAssetClass.PART_DIGITAL_TWIN,
        "submodel_semantic_id": "urn:samm:io.catenax.serial_part:3.0.0#SerialPart",
        "sensitivity": ReedSensitivity.CONSORTIUM,
        "discoverability": ReedDiscoverability.CONSORTIUM,
        "default_policy_template": "consortium-only",
        "allowed_purposes": ["reed.supply-chain.planning:1", "reed.dpp.read:1"],
        "obligations": ["audit"],
        "prohibitions": ["no onward sharing"],
        "description": "Catalog/serialized/bulky part identity, BPN ownership, lifecycle state.",
    },
    {
        "asset_class": ReedAssetClass.BILL_OF_MATERIAL,
        "submodel_semantic_id": "urn:samm:io.catenax.single_level_bom_as_built:3.0.0#SingleLevelBomAsBuilt",
        "sensitivity": ReedSensitivity.CONFIDENTIAL,
        "discoverability": ReedDiscoverability.BILATERAL,
        "default_policy_template": "bilateral-supplier",
        "allowed_purposes": ["reed.supply-chain.planning:1"],
        "obligations": ["audit"],
        "prohibitions": ["no onward sharing"],
        "description": "Parent/child part relationships and supplier links.",
    },
    {
        "asset_class": ReedAssetClass.DIGITAL_PRODUCT_PASSPORT,
        "submodel_semantic_id": "urn:samm:io.catenax.generic.digital_product_passport:5.0.0#DigitalProductPassport",
        "sensitivity": ReedSensitivity.CONSORTIUM,
        "discoverability": ReedDiscoverability.CONSORTIUM,
        "default_policy_template": "dpp-read-only",
        "allowed_purposes": ["reed.dpp.read:1", "reed.sustainability.reporting:1"],
        "obligations": ["audit"],
        "prohibitions": ["no onward sharing"],
        "description": "Materials, recyclability, carbon footprint, compliance evidence.",
    },
    {
        "asset_class": ReedAssetClass.PROCESS_CAPABILITY,
        "submodel_semantic_id": "urn:samm:io.catenax.reed.process_capability:1.0.0#ProcessCapability",
        "sensitivity": ReedSensitivity.CONFIDENTIAL,
        "discoverability": ReedDiscoverability.BILATERAL,
        "default_policy_template": "oem-only",
        "allowed_purposes": ["reed.supply-chain.planning:1", "reed.pilot.process-simulation:1"],
        "obligations": ["audit"],
        "prohibitions": ["no onward sharing", "no AI training"],
        "description": "Machine envelope, operations, tolerances, lead time, available processes.",
    },
    {
        "asset_class": ReedAssetClass.FIXTURE_HANDLING_STRATEGY,
        "submodel_semantic_id": "urn:samm:io.catenax.reed.fixture_handling_strategy:1.0.0#FixtureHandlingStrategy",
        "sensitivity": ReedSensitivity.CONFIDENTIAL,
        "discoverability": ReedDiscoverability.BILATERAL,
        "default_policy_template": "bilateral-supplier",
        "allowed_purposes": ["reed.supply-chain.planning:1"],
        "obligations": ["audit"],
        "prohibitions": ["no onward sharing"],
        "description": "Fixture design, lifting/handling constraints, setup instructions.",
    },
    {
        "asset_class": ReedAssetClass.PRODUCTION_STATUS,
        "submodel_semantic_id": "urn:samm:io.catenax.reed.production_status:1.0.0#ProductionStatus",
        "sensitivity": ReedSensitivity.RESTRICTED,
        "discoverability": ReedDiscoverability.PROJECT,
        "default_policy_template": "time-limited-pilot-access",
        "allowed_purposes": ["reed.supply-chain.planning:1"],
        "obligations": ["audit"],
        "prohibitions": ["no onward sharing"],
        "description": "Capacity, order status, quality gates, delivery status.",
    },
    {
        "asset_class": ReedAssetClass.QUALITY_EVIDENCE,
        "submodel_semantic_id": "urn:samm:io.catenax.reed.quality_evidence:1.0.0#QualityEvidence",
        "sensitivity": ReedSensitivity.REGULATED,
        "discoverability": ReedDiscoverability.BILATERAL,
        "default_policy_template": "oem-only",
        "allowed_purposes": ["reed.quality.audit:1"],
        "obligations": ["audit", "retain logs"],
        "prohibitions": ["no onward sharing"],
        "description": "Inspection reports, certificates, non-conformance summaries.",
    },
    {
        "asset_class": ReedAssetClass.SIMULATION_RESULT,
        "submodel_semantic_id": "urn:samm:io.catenax.reed.simulation_result:1.0.0#SimulationResult",
        "sensitivity": ReedSensitivity.CONFIDENTIAL,
        "discoverability": ReedDiscoverability.BILATERAL,
        "default_policy_template": "simulation-service-only",
        "allowed_purposes": ["reed.pilot.process-simulation:1"],
        "obligations": ["audit", "delete after 90 days"],
        "prohibitions": ["no AI training", "no onward sharing"],
        "description": "Process simulation, energy usage, risk/lead-time estimation.",
    },
]


class SeedService:
    """Seeds the default REED policy templates and classification matrix."""

    def seed_defaults(self, overwrite: bool = False) -> Dict[str, int]:
        """
        Ensure the default policy templates and classifications exist.

        Returns a small summary dict with how many entries were created/updated.
        """
        created_templates = 0
        created_classifications = 0
        with RepositoryManagerFactory.create() as repo:
            for tpl in DEFAULT_POLICY_TEMPLATES:
                existing = repo.reed_policy_template_repository.get_by_name(tpl["name"])
                if existing and not overwrite:
                    continue
                if existing:
                    existing.layer = tpl["layer"]
                    existing.description = tpl["description"]
                    existing.constraints = tpl["constraints"]
                    existing.obligations = tpl["obligations"]
                    existing.prohibitions = tpl["prohibitions"]
                    existing.is_builtin = True
                else:
                    repo.reed_policy_template_repository.create(ReedPolicyTemplate(
                        name=tpl["name"],
                        layer=tpl["layer"],
                        description=tpl["description"],
                        constraints=tpl["constraints"],
                        obligations=tpl["obligations"],
                        prohibitions=tpl["prohibitions"],
                        is_builtin=True,
                    ))
                    created_templates += 1

            for cls in DEFAULT_CLASSIFICATIONS:
                existing = repo.reed_asset_classification_repository.get_by_asset_class(cls["asset_class"])
                if existing and not overwrite:
                    continue
                if existing:
                    for field, value in cls.items():
                        setattr(existing, field, value)
                else:
                    repo.reed_asset_classification_repository.create(ReedAssetClassification(**cls))
                    created_classifications += 1

            repo.commit()

        summary = {
            "templates_created": created_templates,
            "classifications_created": created_classifications,
        }
        logger.info("[REED] Seed defaults complete: %s", summary)
        return summary
