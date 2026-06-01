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

"""Tests for the REED server-side security principal and admin guard."""

import pytest
from fastapi import HTTPException

from controllers.fastapi.routers.reed.reed_security import (
    ReedPrincipal,
    require_reed_admin,
    _principal_from_claims,
)


class TestReedPrincipal:
    def test_service_principal_is_admin(self):
        assert ReedPrincipal(user="service", is_service=True).is_admin is True

    def test_reed_admin_role_is_admin(self):
        assert ReedPrincipal(bpn="BPNL1", roles=["reed-admin"]).is_admin is True

    def test_plain_user_is_not_admin(self):
        assert ReedPrincipal(bpn="BPNL1", roles=["viewer"]).is_admin is False

    def test_require_admin_allows_admin(self):
        principal = ReedPrincipal(bpn="BPNL1", roles=["reed-admin"])
        assert require_reed_admin(principal) is principal

    def test_require_admin_rejects_non_admin(self):
        with pytest.raises(HTTPException) as exc:
            require_reed_admin(ReedPrincipal(bpn="BPNL1", roles=["supplier-owner"]))
        assert exc.value.status_code == 403


class TestClaimMapping:
    def test_identity_is_read_from_token_claims(self):
        claims = {
            "preferred_username": "alice",
            "bpn": "BPNL000000000AAA",
            "realm_access": {"roles": ["oem-manager", "reed-admin"]},
            "groups": ["/reed-pilot", "/oem-team"],
            "membership_active": True,
            "framework_agreement": "DataExchangeGovernance:1.0",
            "nda_active": True,
        }
        p = _principal_from_claims(claims)
        assert p.user == "alice"
        assert p.bpn == "BPNL000000000AAA"
        assert "reed-admin" in p.roles
        assert p.projects == ["reed-pilot", "oem-team"]  # leading slash stripped
        assert p.membership_active is True
        assert p.framework_agreement == "DataExchangeGovernance:1.0"
        assert p.nda_active is True
        assert p.is_service is False

    def test_missing_claims_default_safely(self):
        p = _principal_from_claims({})
        assert p.bpn is None
        assert p.roles == []
        assert p.membership_active is False
        assert p.is_admin is False
