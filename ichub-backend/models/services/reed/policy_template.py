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

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from models.metadata_database.reed.models import ReedPolicyLayer


class PolicyConstraint(BaseModel):
    """A single abstract ODRL-style constraint."""
    left_operand: str = Field(alias="leftOperand", description="The constraint left operand (e.g. cx-policy:Membership).")
    operator: str = Field(default="odrl:eq", description="ODRL operator, e.g. odrl:eq, odrl:in.")
    right_operand: Any = Field(alias="rightOperand", description="The expected value.")

    model_config = {"populate_by_name": True}


class PolicyTemplateBase(BaseModel):
    layer: ReedPolicyLayer = Field(description="The REED policy layer this template belongs to.")
    description: Optional[str] = Field(default=None, description="What this template is for.")
    constraints: List[Dict[str, Any]] = Field(
        default_factory=list, description="Abstract constraints {leftOperand, operator, rightOperand}."
    )
    obligations: List[Dict[str, Any]] = Field(default_factory=list, description="Abstract obligations.")
    prohibitions: List[Dict[str, Any]] = Field(default_factory=list, description="Abstract prohibitions.")

    model_config = {"populate_by_name": True}


class PolicyTemplateCreate(PolicyTemplateBase):
    name: str = Field(description="Unique template name, e.g. 'simulation-service-only'.")


class PolicyTemplateRead(PolicyTemplateBase):
    name: str = Field(description="Unique template name.")
    is_builtin: bool = Field(default=False, alias="isBuiltin", description="Whether this is a built-in template.")


class RenderedPolicy(BaseModel):
    """An EDC/ODRL policy definition rendered from a REED policy template."""
    template_name: str = Field(alias="templateName", description="Source REED template name.")
    layer: ReedPolicyLayer = Field(description="The policy layer.")
    odrl: Dict[str, Any] = Field(description="The rendered EDC/ODRL policy body.")

    model_config = {"populate_by_name": True}
