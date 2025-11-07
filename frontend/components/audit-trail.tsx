/**
 * Audit Trail Viewer
 * Displays complete audit log for EVF processing
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { History, DollarSign, Clock, User } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDate, formatCurrency, formatDuration } from '@/lib/utils';
import apiClient, { AuditLog } from '@/lib/api-client';

interface AuditTrailProps {
  evfId: string;
}

export function AuditTrail({ evfId }: AuditTrailProps) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-logs', evfId],
    queryFn: () => apiClient.getAuditLogs(evfId),
  });

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-6 w-48 bg-gray-200 rounded" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-gray-500">
            Nenhum registo de auditoria disponível
          </p>
        </CardContent>
      </Card>
    );
  }

  // Calculate totals
  const totalTokens = logs.reduce((sum, log) => sum + (log.tokens_used || 0), 0);
  const totalCost = logs.reduce((sum, log) => sum + (log.cost_euros || 0), 0);
  const totalTime = logs.reduce((sum, log) => sum + (log.processing_time_ms || 0), 0);

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total de Tokens</p>
                <p className="text-2xl font-bold mt-1">
                  {totalTokens.toLocaleString()}
                </p>
              </div>
              <History className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Custo Total</p>
                <p className="text-2xl font-bold mt-1">
                  {formatCurrency(totalCost)}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Tempo Total</p>
                <p className="text-2xl font-bold mt-1">
                  {formatDuration(totalTime)}
                </p>
              </div>
              <Clock className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle>Registo de Auditoria</CardTitle>
          <CardDescription>
            Histórico completo de operações e agentes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Data/Hora</TableHead>
                <TableHead>Agente</TableHead>
                <TableHead>Ação</TableHead>
                <TableHead>Tokens</TableHead>
                <TableHead>Custo</TableHead>
                <TableHead>Tempo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log: AuditLog) => (
                <TableRow key={log.id}>
                  <TableCell className="text-sm">
                    {formatDate(log.timestamp, true)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{log.agent}</Badge>
                  </TableCell>
                  <TableCell className="font-medium">
                    {log.action}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.tokens_used?.toLocaleString() || '-'}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.cost_euros ? formatCurrency(log.cost_euros) : '-'}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.processing_time_ms
                      ? formatDuration(log.processing_time_ms)
                      : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Technical Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Detalhes Técnicos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {logs.slice(0, 3).map((log: AuditLog) => (
              <div
                key={log.id}
                className="p-4 bg-gray-50 rounded-lg text-xs font-mono"
              >
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-gray-500">ID:</span>{' '}
                    <span className="text-gray-900">{log.id}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">User ID:</span>{' '}
                    <span className="text-gray-900">{log.user_id}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
