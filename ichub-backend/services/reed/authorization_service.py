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
REED context-based authorization engine.

This is the REED-owned UI/API authorization layer that runs *before* any EDC or
DTR call. It combines Keycloak token claims (identity, roles, project groups,
membership) with REED dynamic context (asset classification, supply-chain
relationship, NDA/framework-agreement state, declared usage purpose) and the
data classification matrix to produce an allow/deny decision plus the policy
template that would govern the inter-company EDC contract.

The engine is deliberately deterministic and side-effect free so it is easy to
unit test; callers persist the audit trail separately via the AuditService.
"""

from typing import List

from managers.metadata_database.manager import RepositoryManagerFactory
from models.metadata_database.reed.models import (
    ReedDiscoverability,
    ReedSensitivity,
)
from models.services.reed.authorization import AuthorizationContext, AuthorizationDecision

# Roles that bypass fine-grained checks (platform operators / auditors).
REED_ADMIN_ROLE = "reed-admin"
AUDITOR_ROLE = "auditor"


class AuthorizationService:
    """Evaluates whether a caller may discover / negotiate / consume a REED asset."""

    def authorize(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        reasons: List[str] = []

        # 1. A participant can always access its own data.
        if ctx.bpn and ctx.bpn == ctx.owner_bpn:
            return AuthorizationDecision(
                allowed=True,
                reasons=["Caller is the data owner."],
            )

        # 2. Platform admins are always allowed (operations / break-glass).
        if REED_ADMIN_ROLE in ctx.roles:
            return AuthorizationDecision(
                allowed=True,
                reasons=[f"Caller holds the '{REED_ADMIN_ROLE}' role."],
            )

        # 3. Resolve the data classification for the requested asset class.
        #    Read every field we need *inside* the session scope - the ORM
        #    instance is detached once the context manager commits/closes.
        with RepositoryManagerFactory.create() as repo:
            classification = repo.reed_asset_classification_repository.get_by_asset_class(ctx.asset_class)
            if classification is None:
                return AuthorizationDecision(
                    allowed=False,
                    reasons=[
                        f"No REED classification is defined for asset class "
                        f"'{ctx.asset_class.value}'; defaulting to deny."
                    ],
                )
            disc = classification.discoverability
            sensitivity = classification.sensitivity
            matched_template = classification.default_policy_template
            required_obligations = list(classification.obligations or [])
            allowed_purposes = list(classification.allowed_purposes or [])
            related = (
                repo.reed_supply_chain_relation_repository.are_related(ctx.bpn, ctx.owner_bpn)
                if ctx.bpn and ctx.owner_bpn else False
            )

        # 4. Discoverability gate.
        if disc == ReedDiscoverability.HIDDEN:
            return AuthorizationDecision(
                allowed=False,
                reasons=["Asset is hidden; only the owner or a platform admin may access it."],
                matchedPolicyTemplate=matched_template,
            )
        if disc == ReedDiscoverability.PUBLIC:
            reasons.append("Asset metadata is public.")
        elif disc == ReedDiscoverability.CONSORTIUM:
            if not ctx.membership_active:
                return self._deny(
                    "Consortium asset requires an active dataspace membership.", matched_template
                )
            reasons.append("Active consortium membership verified.")
        elif disc == ReedDiscoverability.PROJECT:
            if not ctx.project or ctx.project not in ctx.projects:
                return self._deny(
                    "Project-scoped asset requires membership in the matching REED project.",
                    matched_template,
                )
            reasons.append(f"Project membership '{ctx.project}' verified.")
        elif disc == ReedDiscoverability.BILATERAL:
            if not related:
                return self._deny(
                    "Bilateral asset requires an existing supply-chain relationship with the owner.",
                    matched_template,
                )
            reasons.append("Supply-chain relationship with the owner verified.")

        # 5. Sensitivity escalation: confidential/regulated data needs NDA +
        #    an accepted framework agreement.
        if sensitivity in (ReedSensitivity.CONFIDENTIAL, ReedSensitivity.REGULATED):
            if not ctx.nda_active:
                return self._deny(
                    f"{sensitivity.value} data requires an active NDA.", matched_template
                )
            if not ctx.framework_agreement:
                return self._deny(
                    f"{sensitivity.value} data requires an accepted framework agreement.",
                    matched_template,
                )
            reasons.append("NDA and framework agreement verified for sensitive data.")

        # 6. Purpose binding: the declared usage purpose must be permitted.
        if allowed_purposes:
            if not ctx.usage_purpose:
                return self._deny(
                    "A usage purpose is required for this asset class.", matched_template
                )
            if ctx.usage_purpose not in allowed_purposes:
                return self._deny(
                    f"Usage purpose '{ctx.usage_purpose}' is not permitted for this asset class. "
                    f"Allowed: {', '.join(allowed_purposes)}.",
                    matched_template,
                )
            reasons.append(f"Usage purpose '{ctx.usage_purpose}' is permitted.")

        return AuthorizationDecision(
            allowed=True,
            reasons=reasons,
            matchedPolicyTemplate=matched_template,
            requiredObligations=required_obligations,
        )

    @staticmethod
    def _deny(reason: str, matched_template) -> AuthorizationDecision:
        return AuthorizationDecision(
            allowed=False, reasons=[reason], matchedPolicyTemplate=matched_template
        )
