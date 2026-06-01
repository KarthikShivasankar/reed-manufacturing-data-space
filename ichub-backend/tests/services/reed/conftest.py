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
Local test setup for the REED test package.

Importing any REED router module (e.g. ``reed_security``) pulls in the
``controllers.fastapi`` package ``__init__``, which eagerly imports the full
FastAPI app. That app instantiates services that bind ``connector_manager`` /
``dtr_manager`` at import time. This conftest runs before the REED test modules
are collected and pre-imports the app with those references mocked, mirroring the
notifications test conftest. The imported app is then cached for subsequent
imports during collection.
"""

import sys
from unittest.mock import MagicMock, patch

# Ensure the database module is mocked before any import below pulls in the real
# ``database`` module (which would call create_engine on an empty DSN). This makes
# the conftest order-independent w.r.t. the root conftest's pytest_configure hook.
if not isinstance(sys.modules.get("database"), MagicMock):
    _db_mock = MagicMock()
    _db_mock.engine = MagicMock()
    sys.modules["database"] = _db_mock

# Mock the submodel service manager so app import does not touch the filesystem.
if not isinstance(sys.modules.get("managers.enablement_services.submodel_service_manager"), MagicMock):
    sys.modules["managers.enablement_services.submodel_service_manager"] = MagicMock()

# Other test modules may have permanently replaced critical modules with mocks
# (via module-level sys.modules assignment). Restore real implementations so the
# app can build router prefixes / exception models correctly.
_MODULES_NEEDING_REAL_IMPL = [
    "managers.config.config_manager",
    "managers.config.log_manager",
    "tools.exceptions",
    "tools.constants",
]
for _mod_name in _MODULES_NEEDING_REAL_IMPL:
    if isinstance(sys.modules.get(_mod_name), MagicMock):
        del sys.modules[_mod_name]

# Some SDK extension submodules are optional at test time.
for _mod in [
    "tractusx_sdk.dataspace.tools.validate_submodels",
    "tractusx_sdk.extensions",
    "tractusx_sdk.extensions.notification_api",
    "tractusx_sdk.extensions.notification_api.models",
]:
    sys.modules.setdefault(_mod, MagicMock())

# Pre-import the app with infrastructure references mocked so the module-level
# service singletons in the routers can be constructed without real connectors,
# DTR, or Keycloak.
_patchers = [
    patch("services.notifications.notifications_management_service.connector_manager", MagicMock()),
    patch("services.notifications.notifications_management_service.dtr_manager", MagicMock()),
    patch("controllers.fastapi.routers.authentication.auth_api.api_key_manager", None),
    patch("controllers.fastapi.routers.authentication.auth_api.oauth2_manager", None),
]
for _p in _patchers:
    _p.start()
try:
    _mock_conn = sys.modules[
        "services.notifications.notifications_management_service"
    ].connector_manager
    _mock_conn.consumer.connector_service = MagicMock()
    import controllers.fastapi.app  # noqa: F401  (builds + caches the app)
except Exception:
    pass
finally:
    for _p in _patchers:
        _p.stop()
