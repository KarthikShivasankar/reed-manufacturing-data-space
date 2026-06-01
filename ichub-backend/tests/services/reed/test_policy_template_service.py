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

"""Unit tests for REED policy template ODRL rendering (pure, no DB)."""

from models.metadata_database.reed.models import ReedPolicyLayer, ReedPolicyTemplate
from services.reed.policy_template_service import PolicyTemplateService, ODRL_CONTEXT


class TestPolicyTemplateRendering:
    def setup_method(self):
        self.service = PolicyTemplateService()

    def test_render_single_constraint_uses_single_constraint_object(self):
        template = ReedPolicyTemplate(
            name="consortium-only",
            layer=ReedPolicyLayer.CATALOGUE,
            description="members only",
            constraints=[
                {"leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active"}
            ],
            obligations=[],
            prohibitions=[],
        )
        rendered = self.service.render_entity(template)

        assert rendered.template_name == "consortium-only"
        assert rendered.layer == ReedPolicyLayer.CATALOGUE
        assert rendered.odrl["@context"] == ODRL_CONTEXT
        permission = rendered.odrl["policy"]["odrl:permission"][0]
        # A single constraint is emitted directly (no odrl:and wrapper).
        assert permission["action"] == "odrl:use"
        assert permission["constraint"]["leftOperand"] == "cx-policy:Membership"
        assert permission["constraint"]["rightOperand"] == "active"

    def test_render_multiple_constraints_uses_and(self):
        template = ReedPolicyTemplate(
            name="bilateral-supplier",
            layer=ReedPolicyLayer.CONTRACT,
            constraints=[
                {"leftOperand": "cx-policy:Membership", "operator": "odrl:eq", "rightOperand": "active"},
                {"leftOperand": "reed:Nda", "operator": "odrl:eq", "rightOperand": "active"},
            ],
            obligations=[{"action": "reed:audit"}],
            prohibitions=[{"action": "reed:onwardSharing"}],
        )
        rendered = self.service.render_entity(template)
        permission = rendered.odrl["policy"]["odrl:permission"][0]
        assert "and" in permission["constraint"]
        assert len(permission["constraint"]["and"]) == 2
        # Obligations and prohibitions are carried over.
        assert rendered.odrl["policy"]["odrl:obligation"][0]["action"] == "reed:audit"
        assert rendered.odrl["policy"]["odrl:prohibition"][0]["action"] == "reed:onwardSharing"

    def test_render_obligation_with_constraint(self):
        template = ReedPolicyTemplate(
            name="simulation-service-only",
            layer=ReedPolicyLayer.CONTRACT,
            constraints=[],
            obligations=[
                {"action": "reed:delete", "leftOperand": "reed:retentionDays",
                 "operator": "odrl:eq", "rightOperand": "90"}
            ],
            prohibitions=[],
        )
        rendered = self.service.render_entity(template)
        obligation = rendered.odrl["policy"]["odrl:obligation"][0]
        assert obligation["action"] == "reed:delete"
        assert obligation["constraint"]["rightOperand"] == "90"
