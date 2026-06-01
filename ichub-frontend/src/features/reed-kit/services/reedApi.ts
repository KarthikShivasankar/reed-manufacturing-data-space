/********************************************************************************
 * Eclipse Tractus-X - Industry Core Hub Frontend
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
 * distributed under the License is distributed on an "AS IS" BASIS
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the
 * License for the specific language govern in permissions and limitations
 * under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 ********************************************************************************/

/**
 * REED Manufacturing Data Space API client.
 *
 * Thin wrapper over the shared httpClient (which injects auth headers and the
 * backend base URL) for the `/v1/reed/*` endpoints implemented in the backend.
 */

import httpClient from '@/services/HttpClient';

const BASE = '/v1/reed';

// ---------------------------------------------------------------------------
// Types (mirror the backend Pydantic models)
// ---------------------------------------------------------------------------

export type ReedAssetClass =
  | 'PartDigitalTwin'
  | 'BillOfMaterial'
  | 'DigitalProductPassport'
  | 'ProcessCapability'
  | 'FixtureHandlingStrategy'
  | 'ProductionStatus'
  | 'QualityEvidence'
  | 'SimulationResult';

export type ReedSensitivity = 'public' | 'consortium' | 'restricted' | 'confidential' | 'regulated';
export type ReedDiscoverability = 'public' | 'consortium' | 'project' | 'bilateral' | 'hidden';
export type ReedPolicyLayer = 'catalogue' | 'contract' | 'usage';
export type ReedAccessRequestStatus =
  | 'submitted' | 'under_review' | 'approved' | 'rejected'
  | 'contracted' | 'transferred' | 'expired' | 'revoked';

export interface AssetClassification {
  assetClass: ReedAssetClass;
  submodelSemanticId?: string;
  sensitivity: ReedSensitivity;
  discoverability: ReedDiscoverability;
  payloadStorage?: string;
  defaultPolicyTemplate?: string;
  allowedPurposes: string[];
  obligations: string[];
  prohibitions: string[];
  description?: string;
}

export interface PolicyTemplate {
  name: string;
  layer: ReedPolicyLayer;
  description?: string;
  constraints: Record<string, unknown>[];
  obligations: Record<string, unknown>[];
  prohibitions: Record<string, unknown>[];
  isBuiltin: boolean;
}

export interface RenderedPolicy {
  templateName: string;
  layer: ReedPolicyLayer;
  odrl: Record<string, unknown>;
}

export interface SupplyChainRelation {
  id: number;
  parentBpn: string;
  childBpn: string;
  relationType: string;
  project?: string;
  manufacturerPartId?: string;
}

export interface AuthorizationContext {
  bpn: string;
  ownerBpn: string;
  assetClass: ReedAssetClass;
  usagePurpose?: string;
  project?: string;
  projects?: string[];
  roles?: string[];
  membershipActive?: boolean;
  frameworkAgreement?: string;
  ndaActive?: boolean;
  user?: string;
}

export interface AuthorizationDecision {
  allowed: boolean;
  reasons: string[];
  matchedPolicyTemplate?: string;
  requiredObligations: string[];
}

export interface AccessRequest {
  requestId: string;
  requestingBpn: string;
  requestingUser?: string;
  ownerBpn: string;
  assetClass: ReedAssetClass;
  manufacturerPartId?: string;
  usagePurpose: string;
  project?: string;
  policyTemplate?: string;
  status: ReedAccessRequestStatus;
  decisionReason?: string;
  edcAgreementId?: string;
  edcTransferId?: string;
  createdAt: string;
  updatedAt: string;
  expiresAt?: string;
}

export interface AuditEvent {
  eventId: string;
  createdAt: string;
  action: string;
  outcome: string;
  actorUser?: string;
  actorBpn?: string;
  ownerBpn?: string;
  assetClass?: ReedAssetClass;
  manufacturerPartId?: string;
  usagePurpose?: string;
  policyTemplate?: string;
  edcAgreementId?: string;
  accessRequestId?: string;
  detail?: string;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const reedApi = {
  // Classification
  listClassifications: async (): Promise<AssetClassification[]> =>
    (await httpClient.get(`${BASE}/classification`)).data,

  // Policy templates
  listPolicyTemplates: async (layer?: ReedPolicyLayer): Promise<PolicyTemplate[]> =>
    (await httpClient.get(`${BASE}/policy-templates`, { params: layer ? { layer } : {} })).data,
  renderPolicy: async (name: string): Promise<RenderedPolicy> =>
    (await httpClient.get(`${BASE}/policy-templates/${encodeURIComponent(name)}/odrl`)).data,

  // Supply chain
  listRelations: async (): Promise<SupplyChainRelation[]> =>
    (await httpClient.get(`${BASE}/supply-chain/relations`)).data,
  createRelation: async (payload: Partial<SupplyChainRelation>): Promise<SupplyChainRelation> =>
    (await httpClient.post(`${BASE}/supply-chain/relations`, payload)).data,

  // Authorization
  evaluate: async (ctx: AuthorizationContext): Promise<AuthorizationDecision> =>
    (await httpClient.post(`${BASE}/authorization/evaluate`, ctx)).data,

  // Access requests
  listAccessRequests: async (params?: {
    ownerBpn?: string; requestingBpn?: string; status?: ReedAccessRequestStatus;
  }): Promise<AccessRequest[]> =>
    (await httpClient.get(`${BASE}/access-requests`, { params })).data,
  submitAccessRequest: async (payload: Partial<AccessRequest>): Promise<AccessRequest> =>
    (await httpClient.post(`${BASE}/access-requests`, payload)).data,
  decideAccessRequest: async (
    requestId: string, approve: boolean, reason?: string,
  ): Promise<AccessRequest> =>
    (await httpClient.post(`${BASE}/access-requests/${requestId}/decision`, { approve, reason })).data,
  contractAccessRequest: async (
    requestId: string, edcAgreementId: string, edcTransferId?: string,
  ): Promise<AccessRequest> =>
    (await httpClient.post(`${BASE}/access-requests/${requestId}/contract`, null, {
      params: { edcAgreementId, edcTransferId },
    })).data,

  // Audit
  queryAudit: async (params?: {
    actorBpn?: string; ownerBpn?: string; accessRequestId?: string; limit?: number;
  }): Promise<AuditEvent[]> =>
    (await httpClient.get(`${BASE}/audit/events`, { params })).data,

  // Admin
  seedDefaults: async (overwrite = false): Promise<Record<string, number>> =>
    (await httpClient.post(`${BASE}/admin/seed`, null, { params: { overwrite } })).data,
};

export default reedApi;
