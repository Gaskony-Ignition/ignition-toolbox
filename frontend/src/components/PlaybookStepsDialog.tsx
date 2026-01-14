/**
 * PlaybookStepsDialog - Display all steps in a playbook
 */

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Typography,
  Box,
} from '@mui/material';
import type { PlaybookInfo } from '../types/api';

interface PlaybookStepsDialogProps {
  open: boolean;
  playbook: PlaybookInfo | null;
  onClose: () => void;
}

export function PlaybookStepsDialog({ open, playbook, onClose }: PlaybookStepsDialogProps) {
  if (!playbook) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box>
          <Typography variant="h6">{playbook.name} - Steps</Typography>
          <Typography variant="caption" color="text.secondary">
            {playbook.step_count} total steps
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width="5%">#</TableCell>
                <TableCell width="25%">Step Name</TableCell>
                <TableCell width="25%">Type</TableCell>
                <TableCell width="15%">Timeout</TableCell>
                <TableCell width="15%">Retries</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {playbook.steps && playbook.steps.length > 0 ? (
                playbook.steps.map((step, index) => (
                  <TableRow key={step.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {index + 1}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{step.name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={step.type}
                        size="small"
                        variant="outlined"
                        color={
                          step.type.startsWith('gateway') ? 'primary' :
                          step.type.startsWith('browser') ? 'secondary' :
                          step.type.startsWith('ai') ? 'success' :
                          'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {step.timeout}s
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {step.retry_count}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <Typography variant="body2" color="text.secondary">
                      No step details available
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
