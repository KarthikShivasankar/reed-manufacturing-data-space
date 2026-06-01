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

"""Unit tests for the REED context-based authorization engine."""

from unittest.mock import MagicMock, patch

import pytest

from models.metadata_database.reed.models import (
    ReedAssetClass,
    ReedAssetClassification,
    ReedDiscoverability,
    ReedSensitivity,
)
from models.services.reed.authorization import AuthorizationContext
from services.reed.authorization_service import AuthorizationService


def _classification(**overrides):
    base = dict(
        asset_class=ReedAssetClass.PROCESS_CAPABILITY,
        sensitivity=ReedSensitivity.CONFIDENTIAL,
        discoverability=ReedDiscoverability.BILATERAL,
        default_policy_template="oem-only",
        allowed_purposes=["reed.supply-chain.planning:1"],
        obligations=["audit"],
        prohibitions=["no onward sharing"],
    )
    base.update(overrides)
    return ReedAssetClassification(**base)


def _patched_repo(classification=None, related=False):
    """Return a context-manager mock for RepositoryManagerFactory.create()."""
    repo = MagicMock()
    repo.reed_asset_classification_repository.get_by_asset_class.return_value = classification
    repo.reed_supply_chain_relation_repository.are_related.return_value = related
    factory = MagicMock()
    factory.return_value.__enter__.return_value = repo
    factory.return_value.__exit__.return_value = False
    return factory


class TestAuthorizationService:
    def setup_method(self):
        self.service = AuthorizationService()

    def _ctx(self, **overrides):
        base = dict(
            user="alice",
            bpn="BPNL000000000AAA",
            roles=[],
            projects=["reed-pilot"],
            membershipActive=True,
            frameworkAgreement="DataExchangeGovernance:1.0",
            ndaActive=True,
            ownerBpn="BPNL000000000BBB",
            assetClass=ReedAssetClass.PROCESS_CAPABILITY,
            usagePurpose="reed.supply-chain.planning:1",
            project="reed-pilot",
        )
        base.update(overrides)
        return AuthorizationContext(**base)

    def test_owner_can_always_access_own_data(self):
        ctx = self._ctx(bpn="BPNL000000000BBB")  # same as ownerBpn
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo()):
            decision = self.service.authorize(ctx)
        assert decision.allowed is True

    def test_admin_role_bypasses_checks(self):
        ctx = self._ctx(roles=["reed-admin"])
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo()):
            decision = self.service.authorize(ctx)
        assert decision.allowed is True

    def test_unknown_classification_is_denied(self):
        ctx = self._ctx()
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=None)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is False

    def test_bilateral_requires_supply_chain_relation(self):
        ctx = self._ctx()
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=_classification(), related=False)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is False
        assert any("supply-chain" in r for r in decision.reasons)

    def test_bilateral_confidential_full_context_allows(self):
        ctx = self._ctx()
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=_classification(), related=True)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is True
        assert decision.matched_policy_template == "oem-only"
        assert "audit" in decision.required_obligations

    def test_confidential_requires_nda(self):
        ctx = self._ctx(ndaActive=False)
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=_classification(), related=True)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is False
        assert any("NDA" in r for r in decision.reasons)

    def test_disallowed_usage_purpose_is_denied(self):
        ctx = self._ctx(usagePurpose="reed.benchmark.aggregate:1")
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=_classification(), related=True)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is False
        assert any("purpose" in r.lower() for r in decision.reasons)

    def test_consortium_requires_active_membership(self):
        ctx = self._ctx(membershipActive=False)
        classification = _classification(
            discoverability=ReedDiscoverability.CONSORTIUM,
            sensitivity=ReedSensitivity.CONSORTIUM,
            default_policy_template="consortium-only",
        )
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=classification, related=False)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is False
        assert any("membership" in r.lower() for r in decision.reasons)

    def test_hidden_asset_denied_for_non_owner(self):
        ctx = self._ctx()
        classification = _classification(discoverability=ReedDiscoverability.HIDDEN)
        with patch("services.reed.authorization_service.RepositoryManagerFactory.create",
                   _patched_repo(classification=classification, related=True)):
            decision = self.service.authorize(ctx)
        assert decision.allowed is False
