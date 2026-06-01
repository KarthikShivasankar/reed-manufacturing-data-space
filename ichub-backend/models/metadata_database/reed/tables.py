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
Idempotent creation of the REED metadata tables.

The rest of the Industry Core Hub metadata database is provisioned from an
externally managed DDL script (``docs/database/Metadata-DDL-public.sql``). The
REED tables are additive, so we create just those tables via SQLModel's
``create_all`` (which only creates missing tables) rather than editing the
shared bootstrap DDL. This mirrors how the consumer connector/DTR memory
managers create their own tables on startup.
"""

from managers.config.log_manager import LoggingManager
from models.metadata_database.reed.models import REED_TABLES

logger = LoggingManager.get_logger(__name__)


def create_reed_tables() -> None:
    """
    Create the REED tables if they do not already exist.

    Failures are logged but do not abort startup, consistent with the other
    best-effort startup hooks in the backend.
    """
    try:
        from database import engine

        tables = [model.__table__ for model in REED_TABLES]
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine, tables=tables)
        logger.info("[REED] Metadata tables ensured: %s", ", ".join(t.name for t in tables))
    except Exception as e:  # pragma: no cover - defensive startup guard
        logger.error("[REED] Failed to ensure REED tables: %s", e, exc_info=True)
