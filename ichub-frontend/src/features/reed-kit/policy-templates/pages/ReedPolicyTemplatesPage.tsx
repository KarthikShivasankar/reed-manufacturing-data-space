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
  Box, Typography, Card, CardContent, Chip, CircularProgress, Alert, Stack, Button,
  Dialog, DialogTitle, DialogContent, Grid,
} from '@mui/material';
import { Code, Refresh } from '@mui/icons-material';
import reedApi, { PolicyTemplate, ReedPolicyLayer, RenderedPolicy } from '../../services/reedApi';

const layerColor: Record<ReedPolicyLayer, 'info' | 'warning' | 'success'> = {
  catalogue: 'info',
  contract: 'warning',
  usage: 'success',
};

export default function ReedPolicyTemplatesPage() {
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState<RenderedPolicy | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setTemplates(await reedApi.listPolicyTemplates());
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to load policy templates');
    } finally {
      setLoading(false);
    }
  };

  const showOdrl = async (name: string) => {
    try {
      setRendered(await reedApi.renderPolicy(name));
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Failed to render policy');
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4">REED Policy Templates</Typography>
          <Typography variant="body2" color="text.secondary">
            Catalogue, contract and usage policy templates. Each renders to an EDC/ODRL policy definition.
          </Typography>
        </Box>
        <Button startIcon={<Refresh />} onClick={load} disabled={loading}>Refresh</Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading ? <CircularProgress /> : (
        <Grid container spacing={2}>
          {templates.map((t) => (
            <Grid item xs={12} md={6} lg={4} key={t.name}>
              <Card variant="outlined" sx={{ height: '100%' }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">{t.name}</Typography>
                    <Chip size="small" color={layerColor[t.layer]} label={t.layer} />
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1, minHeight: 40 }}>
                    {t.description}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <Chip size="small" variant="outlined" label={`${t.constraints.length} constraints`} />
                    <Chip size="small" variant="outlined" label={`${t.obligations.length} obligations`} />
                    <Chip size="small" variant="outlined" label={`${t.prohibitions.length} prohibitions`} />
                  </Stack>
                  <Button size="small" startIcon={<Code />} sx={{ mt: 2 }} onClick={() => showOdrl(t.name)}>
                    View ODRL
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={!!rendered} onClose={() => setRendered(null)} maxWidth="md" fullWidth>
        <DialogTitle>EDC/ODRL — {rendered?.templateName}</DialogTitle>
        <DialogContent>
          <Box component="pre" sx={{
            bgcolor: 'grey.900', color: 'grey.100', p: 2, borderRadius: 1,
            overflow: 'auto', fontSize: 12,
          }}>
            {rendered ? JSON.stringify(rendered.odrl, null, 2) : ''}
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
}
