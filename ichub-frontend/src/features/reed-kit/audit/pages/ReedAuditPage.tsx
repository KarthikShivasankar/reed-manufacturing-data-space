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
  Paper, Chip, CircularProgress, Alert, Button, Stack,
} from '@mui/material';
import { Refresh } from '@mui/icons-material';
import reedApi, { AuditEvent } from '../../services/reedApi';

const outcomeColor: Record<string, 'success' | 'error' | 'warning' | 'default'> = {
  success: 'success', denied: 'error', failed: 'warning',
};

export default function ReedAuditPage() {
  const [rows, setRows] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await reedApi.queryAudit({ limit: 200 }));
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to load audit events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4">REED Audit Trail</Typography>
          <Typography variant="body2" color="text.secondary">
            Participant, user, BPN, asset, purpose, contract agreement, timestamp and outcome (T5.3 evidence).
          </Typography>
        </Box>
        <Button startIcon={<Refresh />} onClick={load} disabled={loading}>Refresh</Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading ? <CircularProgress /> : rows.length === 0 ? (
        <Alert severity="info">No audit events yet.</Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Outcome</TableCell>
                <TableCell>Actor BPN</TableCell>
                <TableCell>Owner BPN</TableCell>
                <TableCell>Asset</TableCell>
                <TableCell>Purpose</TableCell>
                <TableCell>Policy</TableCell>
                <TableCell>Detail</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((e) => (
                <TableRow key={e.eventId} hover>
                  <TableCell>{new Date(e.createdAt).toLocaleString()}</TableCell>
                  <TableCell>{e.action}</TableCell>
                  <TableCell><Chip size="small" color={outcomeColor[e.outcome] || 'default'} label={e.outcome} /></TableCell>
                  <TableCell>{e.actorBpn}</TableCell>
                  <TableCell>{e.ownerBpn}</TableCell>
                  <TableCell>{e.assetClass}</TableCell>
                  <TableCell>{e.usagePurpose}</TableCell>
                  <TableCell>{e.policyTemplate}</TableCell>
                  <TableCell>{e.detail}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
