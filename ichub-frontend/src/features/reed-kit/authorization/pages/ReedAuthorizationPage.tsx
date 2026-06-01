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

import { useState } from 'react';
import {
  Box, Typography, TextField, MenuItem, Button, Grid, Card, CardContent, Alert,
  FormControlLabel, Switch, Stack, Chip, Divider, List, ListItem, ListItemText,
} from '@mui/material';
import { Gavel } from '@mui/icons-material';
import reedApi, {
  AuthorizationContext, AuthorizationDecision, ReedAssetClass,
} from '../../services/reedApi';

const ASSET_CLASSES: ReedAssetClass[] = [
  'PartDigitalTwin', 'BillOfMaterial', 'DigitalProductPassport', 'ProcessCapability',
  'FixtureHandlingStrategy', 'ProductionStatus', 'QualityEvidence', 'SimulationResult',
];

export default function ReedAuthorizationPage() {
  const [ctx, setCtx] = useState<AuthorizationContext>({
    bpn: '', ownerBpn: '', assetClass: 'ProcessCapability',
    usagePurpose: 'reed.supply-chain.planning:1', project: 'reed-pilot',
    projects: ['reed-pilot'], roles: [], membershipActive: true,
    frameworkAgreement: 'DataExchangeGovernance:1.0', ndaActive: true,
  });
  const [decision, setDecision] = useState<AuthorizationDecision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const set = (k: keyof AuthorizationContext, v: unknown) => setCtx((p) => ({ ...p, [k]: v }));

  const evaluate = async () => {
    setLoading(true);
    setError(null);
    setDecision(null);
    try {
      setDecision(await reedApi.evaluate(ctx));
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Evaluation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4">REED Authorization Simulator</Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Evaluate the context-based authorization decision that REED makes before any EDC/DTR call.
        For Keycloak users the backend overrides identity from the token; this form is most useful with
        an API-key (service) caller or for understanding the policy logic.
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>Request context</Typography>
              <Stack spacing={2}>
                <TextField label="Caller BPN" value={ctx.bpn}
                  onChange={(e) => set('bpn', e.target.value)} fullWidth size="small" />
                <TextField label="Owner BPN" value={ctx.ownerBpn}
                  onChange={(e) => set('ownerBpn', e.target.value)} fullWidth size="small" />
                <TextField select label="Asset class" value={ctx.assetClass}
                  onChange={(e) => set('assetClass', e.target.value)} fullWidth size="small">
                  {ASSET_CLASSES.map((a) => <MenuItem key={a} value={a}>{a}</MenuItem>)}
                </TextField>
                <TextField label="Usage purpose" value={ctx.usagePurpose}
                  onChange={(e) => set('usagePurpose', e.target.value)} fullWidth size="small" />
                <TextField label="Project" value={ctx.project}
                  onChange={(e) => set('project', e.target.value)} fullWidth size="small" />
                <TextField label="Projects (comma-separated)" value={(ctx.projects || []).join(',')}
                  onChange={(e) => set('projects', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                  fullWidth size="small" />
                <TextField label="Roles (comma-separated)" value={(ctx.roles || []).join(',')}
                  onChange={(e) => set('roles', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                  fullWidth size="small" />
                <TextField label="Framework agreement" value={ctx.frameworkAgreement}
                  onChange={(e) => set('frameworkAgreement', e.target.value)} fullWidth size="small" />
                <Stack direction="row" spacing={2}>
                  <FormControlLabel control={
                    <Switch checked={!!ctx.membershipActive}
                      onChange={(e) => set('membershipActive', e.target.checked)} />
                  } label="Membership active" />
                  <FormControlLabel control={
                    <Switch checked={!!ctx.ndaActive}
                      onChange={(e) => set('ndaActive', e.target.checked)} />
                  } label="NDA active" />
                </Stack>
                <Button variant="contained" startIcon={<Gavel />} onClick={evaluate} disabled={loading}>
                  Evaluate
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          {error && <Alert severity="error">{error}</Alert>}
          {decision && (
            <Card variant="outlined">
              <CardContent>
                <Stack direction="row" alignItems="center" spacing={2}>
                  <Typography variant="h6">Decision</Typography>
                  <Chip color={decision.allowed ? 'success' : 'error'}
                    label={decision.allowed ? 'ALLOWED' : 'DENIED'} />
                </Stack>
                {decision.matchedPolicyTemplate && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Matched policy template: <strong>{decision.matchedPolicyTemplate}</strong>
                  </Typography>
                )}
                {decision.requiredObligations?.length > 0 && (
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    {decision.requiredObligations.map((o) => <Chip key={o} size="small" label={o} />)}
                  </Stack>
                )}
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle2">Reasons</Typography>
                <List dense>
                  {decision.reasons.map((r, i) => (
                    <ListItem key={i}><ListItemText primary={r} /></ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
