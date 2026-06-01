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

import { useEffect, useState } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, CircularProgress, Alert, Button, Stack, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem,
} from '@mui/material';
import { Refresh, Add, Check, Close } from '@mui/icons-material';
import reedApi, {
  AccessRequest, ReedAccessRequestStatus, ReedAssetClass,
} from '../../services/reedApi';

const ASSET_CLASSES: ReedAssetClass[] = [
  'PartDigitalTwin', 'BillOfMaterial', 'DigitalProductPassport', 'ProcessCapability',
  'FixtureHandlingStrategy', 'ProductionStatus', 'QualityEvidence', 'SimulationResult',
];

const statusColor: Record<ReedAccessRequestStatus, 'default' | 'info' | 'success' | 'error' | 'warning'> = {
  submitted: 'info', under_review: 'info', approved: 'success', rejected: 'error',
  contracted: 'success', transferred: 'success', expired: 'default', revoked: 'error',
};

export default function ReedAccessRequestsPage() {
  const [rows, setRows] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Partial<AccessRequest>>({
    requestingBpn: '', ownerBpn: '', assetClass: 'ProcessCapability',
    usagePurpose: 'reed.supply-chain.planning:1', project: 'reed-pilot',
  });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await reedApi.listAccessRequests());
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to load access requests');
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    try {
      await reedApi.submitAccessRequest(form);
      setOpen(false);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Submit failed');
    }
  };

  const decide = async (id: string, approve: boolean) => {
    try {
      await reedApi.decideAccessRequest(id, approve, approve ? 'Approved via portal' : 'Rejected via portal');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Decision failed (only the data owner may decide).');
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4">REED Access Requests</Typography>
          <Typography variant="body2" color="text.secondary">
            Consumer access-request workflow: submit → decide → contract → transfer.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<Refresh />} onClick={load} disabled={loading}>Refresh</Button>
          <Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>New request</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading ? <CircularProgress /> : rows.length === 0 ? (
        <Alert severity="info">No access requests yet.</Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Requester</TableCell>
                <TableCell>Owner</TableCell>
                <TableCell>Asset</TableCell>
                <TableCell>Purpose</TableCell>
                <TableCell>Policy</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.requestId} hover>
                  <TableCell>{r.requestingBpn}</TableCell>
                  <TableCell>{r.ownerBpn}</TableCell>
                  <TableCell>{r.assetClass}</TableCell>
                  <TableCell>{r.usagePurpose}</TableCell>
                  <TableCell>{r.policyTemplate}</TableCell>
                  <TableCell><Chip size="small" color={statusColor[r.status]} label={r.status} /></TableCell>
                  <TableCell align="right">
                    {(r.status === 'submitted' || r.status === 'under_review') && (
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button size="small" color="success" startIcon={<Check />}
                          onClick={() => decide(r.requestId, true)}>Approve</Button>
                        <Button size="small" color="error" startIcon={<Close />}
                          onClick={() => decide(r.requestId, false)}>Reject</Button>
                      </Stack>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New access request</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Requesting BPN" value={form.requestingBpn || ''}
              onChange={(e) => setForm({ ...form, requestingBpn: e.target.value })} fullWidth size="small" />
            <TextField label="Owner BPN" value={form.ownerBpn || ''}
              onChange={(e) => setForm({ ...form, ownerBpn: e.target.value })} fullWidth size="small" />
            <TextField select label="Asset class" value={form.assetClass}
              onChange={(e) => setForm({ ...form, assetClass: e.target.value as ReedAssetClass })} fullWidth size="small">
              {ASSET_CLASSES.map((a) => <MenuItem key={a} value={a}>{a}</MenuItem>)}
            </TextField>
            <TextField label="Usage purpose" value={form.usagePurpose || ''}
              onChange={(e) => setForm({ ...form, usagePurpose: e.target.value })} fullWidth size="small" />
            <TextField label="Project" value={form.project || ''}
              onChange={(e) => setForm({ ...form, project: e.target.value })} fullWidth size="small" />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={submit}>Submit</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
