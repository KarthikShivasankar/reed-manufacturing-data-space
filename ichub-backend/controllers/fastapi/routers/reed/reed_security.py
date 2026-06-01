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
REED server-side security principal.

The stock Industry Core Hub authentication dependency only answers "is this
request authenticated?" (via API key OR a validated Keycloak bearer token). REED
additionally needs *who* the caller is to make authorization and ownership
decisions, and those identity facts must never be taken from the request body
(that would be trivially spoofable).

This module resolves a trusted ``ReedPrincipal`` from the authenticated request:

- **Keycloak bearer token** -> identity (user, BPN, roles, project groups,
  membership / framework-agreement / NDA state) is read from the *validated*
  token claims. These override anything supplied in the request body. A regular
  user therefore cannot claim a BPN, role or NDA state their IdP does not assert.
- **API key** (a shared secret used for trusted service-to-service / operator
  calls, exactly as the rest of ICH treats it) -> a *service principal* that is
  trusted to act on behalf of the platform and is granted the ``reed-admin``
  capability. In this mode body-supplied context is accepted because the API key
  itself is the trust anchor.

The token signature is validated upstream by the shared authentication
dependency (which calls Keycloak's userinfo endpoint); here we only decode the
already-validated claims to read identity.
"""

from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from managers.config.config_manager import ConfigManager
from managers.config.log_manager import LoggingManager
from controllers.fastapi.routers.authentication.auth_api import (
    get_authentication_dependency,
    oauth2_manager,
)

logger = LoggingManager.get_logger("staging")

REED_ADMIN_ROLE = "reed-admin"


class ReedPrincipal(BaseModel):
    """The trusted, server-resolved identity of a REED caller."""
    user: Optional[str] = Field(default=None, description="Subject / preferred_username.")
    bpn: Optional[str] = Field(default=None, description="Organization BPN from the token.")
    roles: List[str] = Field(default_factory=list, description="Realm roles from the token.")
    projects: List[str] = Field(default_factory=list, description="Project groups from the token.")
    membership_active: bool = Field(default=False)
    framework_agreement: Optional[str] = Field(default=None)
    nda_active: bool = Field(default=False)
    is_service: bool = Field(
        default=False, description="True when authenticated via the trusted API key."
    )

    @property
    def is_admin(self) -> bool:
        return self.is_service or REED_ADMIN_ROLE in self.roles


def _claim_config() -> dict:
    """Configurable mapping of token claims -> principal fields (with defaults)."""
    cfg = ConfigManager.get_config("reed.authorization.claims", default={}) or {}
    return {
        "bpn": cfg.get("bpn", "bpn"),
        "groups": cfg.get("groups", "groups"),
        "membership": cfg.get("membership", "membership_active"),
        "framework_agreement": cfg.get("framework_agreement", "framework_agreement"),
        "nda": cfg.get("nda", "nda_active"),
    }


def _decode_claims(token: str) -> dict:
    """Decode (already-validated) JWT claims to read identity. Best-effort."""
    try:
        from jose import jwt  # python-jose is a project dependency
        return jwt.get_unverified_claims(token)
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"[REED] Could not decode token claims: {e}")
        return {}


def _principal_from_claims(claims: dict) -> ReedPrincipal:
    mapping = _claim_config()
    realm_roles = (claims.get("realm_access") or {}).get("roles") or []
    raw_groups = claims.get(mapping["groups"]) or []
    projects = [g.lstrip("/") for g in raw_groups] if isinstance(raw_groups, list) else []
    return ReedPrincipal(
        user=claims.get("preferred_username") or claims.get("sub"),
        bpn=claims.get(mapping["bpn"]),
        roles=list(realm_roles),
        projects=projects,
        membership_active=bool(claims.get(mapping["membership"], False)),
        framework_agreement=claims.get(mapping["framework_agreement"]),
        nda_active=bool(claims.get(mapping["nda"], False)),
        is_service=False,
    )


def get_reed_principal(
    request: Request,
    _: bool = Depends(get_authentication_dependency()),
) -> ReedPrincipal:
    """
    FastAPI dependency that returns the trusted REED principal. The underlying
    ``get_authentication_dependency`` has already guaranteed the request is
    authenticated (or that auth is globally disabled).
    """
    authorization = request.headers.get("Authorization") or ""
    if oauth2_manager is not None and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        return _principal_from_claims(_decode_claims(token))

    # No bearer token => API key (or auth disabled). Trusted service principal.
    return ReedPrincipal(user="service", is_service=True)


def require_reed_admin(principal: ReedPrincipal = Depends(get_reed_principal)) -> ReedPrincipal:
    """Dependency enforcing the REED administrative capability."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This operation requires the '{REED_ADMIN_ROLE}' role.",
        )
    return principal
