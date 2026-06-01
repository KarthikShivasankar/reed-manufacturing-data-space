/********************************************************************************
* Eclipse Tractus-X - Industry Core Hub
*
* Copyright (c) 2026 Contributors to the Eclipse Foundation
*
* See the NOTICE file(s) distributed with this work for additional
* information regarding copyright ownership.
*
* This program and the accompanying materials are made available under the
* terms of the Apache License, Version 2.0 which is available at
* https://www.apache.org/licenses/LICENSE-2.0.
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
* License for the specific language governing permissions and limitations
* under the License.
*
* SPDX-License-Identifier: Apache-2.0
*********************************************************************************/

-- ===========================================================================
-- REED Manufacturing Data Space tables.
--
-- These tables are ADDITIVE on top of the Industry Core Hub metadata schema
-- (see Metadata-DDL-public.sql). At runtime the backend creates them
-- automatically via SQLModel (only missing tables are created) during startup
-- in controllers/fastapi/app.py -> _ensure_reed_tables_on_startup().
--
-- This script is provided for operators who provision the schema out-of-band
-- (e.g. via an init container or migration) and want the REED tables created
-- explicitly. Running it is OPTIONAL when the backend has DDL privileges.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS public.reed_asset_classification (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_class character varying NOT NULL UNIQUE,
    submodel_semantic_id character varying,
    sensitivity character varying NOT NULL,
    discoverability character varying NOT NULL,
    payload_storage character varying,
    default_policy_template character varying,
    allowed_purposes json,
    obligations json,
    prohibitions json,
    description character varying
);

CREATE TABLE IF NOT EXISTS public.reed_policy_template (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name character varying NOT NULL UNIQUE,
    layer character varying NOT NULL,
    description character varying,
    constraints json,
    obligations json,
    prohibitions json,
    is_builtin boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS public.reed_supply_chain_relation (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_bpn character varying NOT NULL,
    child_bpn character varying NOT NULL,
    relation_type character varying NOT NULL,
    project character varying,
    manufacturer_part_id character varying,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.reed_access_request (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    requesting_bpn character varying NOT NULL,
    requesting_user character varying,
    owner_bpn character varying NOT NULL,
    asset_class character varying NOT NULL,
    manufacturer_part_id character varying,
    usage_purpose character varying NOT NULL,
    project character varying,
    policy_template character varying,
    status character varying NOT NULL,
    decision_reason character varying,
    edc_agreement_id character varying,
    edc_transfer_id character varying,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    updated_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    expires_at timestamp without time zone
);

CREATE TABLE IF NOT EXISTS public.reed_audit_event (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    action character varying NOT NULL,
    outcome character varying NOT NULL,
    actor_user character varying,
    actor_bpn character varying,
    owner_bpn character varying,
    asset_class character varying,
    manufacturer_part_id character varying,
    usage_purpose character varying,
    policy_template character varying,
    edc_agreement_id character varying,
    access_request_id uuid,
    detail character varying
);

CREATE INDEX IF NOT EXISTS ix_reed_access_request_request_id ON public.reed_access_request (request_id);
CREATE INDEX IF NOT EXISTS ix_reed_access_request_owner_bpn ON public.reed_access_request (owner_bpn);
CREATE INDEX IF NOT EXISTS ix_reed_access_request_status ON public.reed_access_request (status);
CREATE INDEX IF NOT EXISTS ix_reed_audit_event_created_at ON public.reed_audit_event (created_at);
CREATE INDEX IF NOT EXISTS ix_reed_supply_chain_parent ON public.reed_supply_chain_relation (parent_bpn);
CREATE INDEX IF NOT EXISTS ix_reed_supply_chain_child ON public.reed_supply_chain_relation (child_bpn);
