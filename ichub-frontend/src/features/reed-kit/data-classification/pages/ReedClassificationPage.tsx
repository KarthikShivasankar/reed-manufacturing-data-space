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
  Paper, Chip, CircularProgress, Alert, Button, Stack, Tooltip,
} from '@mui/material';
import { Refresh, CloudDownload } from '@mui/icons-material';
import reedApi, { AssetClassification, ReedSensitivity, ReedDiscoverability } from '../../services/reedApi';

const sensitivityColor: Record<ReedSensitivity, 'default' | 'info' | 'warning' | 'error'> = {
  public: 'default',
  consortium: 'info',
  restricted: 'warning',
  confidential: 'error',
  regulated: 'error',
};

const discoverabilityColor: Record<ReedDiscoverability, 'default' | 'success' | 'info' | 'warning'> = {
  public: 'success',
  consortium: 'info',
  project: 'info',
  bilateral: 'warning',
  hidden: 'default',
};

export default function ReedClassificationPage() {
  const [rows, setRows] = useState<AssetClassification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await reedApi.listClassifications());
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to load classifications');
    } finally {
      setLoading(false);
    }
  };

  const seed = async () => {
    setSeeding(true);
    try {
      await reedApi.seedDefaults(false);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Seeding failed (requires reed-admin).');
    } finally {
      setSeeding(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4">REED Data Classification Matrix</Typography>
          <Typography variant="body2" color="text.secondary">
            DMP-derived classification mapping each manufacturing asset class to its sensitivity,
            discoverability and default policy template. Only metadata is published to DTR/EDC; payloads
            stay in the submodel service.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<Refresh />} onClick={load} disabled={loading}>Refresh</Button>
          <Tooltip title="Seed the default 8 classes + 8 policy templates (reed-admin)">
            <span>
              <Button variant="contained" startIcon={<CloudDownload />} onClick={seed} disabled={seeding}>
                Seed defaults
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading ? <CircularProgress /> : rows.length === 0 ? (
        <Alert severity="info">No classifications yet. Click “Seed defaults” to load the REED matrix.</Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Asset Class</TableCell>
                <TableCell>Sensitivity</TableCell>
                <TableCell>Discoverability</TableCell>
                <TableCell>Default Policy</TableCell>
                <TableCell>Allowed Purposes</TableCell>
                <TableCell>Obligations</TableCell>
                <TableCell>Prohibitions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.assetClass} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>{r.assetClass}</Typography>
                    <Typography variant="caption" color="text.secondary">{r.submodelSemanticId}</Typography>
                  </TableCell>
                  <TableCell><Chip size="small" color={sensitivityColor[r.sensitivity]} label={r.sensitivity} /></TableCell>
                  <TableCell><Chip size="small" color={discoverabilityColor[r.discoverability]} label={r.discoverability} /></TableCell>
                  <TableCell>{r.defaultPolicyTemplate}</TableCell>
                  <TableCell>{(r.allowedPurposes || []).join(', ')}</TableCell>
                  <TableCell>{(r.obligations || []).join(', ')}</TableCell>
                  <TableCell>{(r.prohibitions || []).join(', ')}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
