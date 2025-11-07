/**
 * EVF Projects List Component
 * Table view with filtering, sorting, and status indicators
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { FileText, Download, Eye, Trash2, MoreVertical } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  formatDate,
  formatCurrency,
  formatPercent,
  getStatusColor,
  getFundTypeLabel,
} from '@/lib/utils';
import apiClient, { EVFProject } from '@/lib/api-client';

export function EVFList() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [fundTypeFilter, setFundTypeFilter] = useState<string>('all');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['evf-list', statusFilter, fundTypeFilter],
    queryFn: () =>
      apiClient.getEVFList({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        fund_type: fundTypeFilter !== 'all' ? fundTypeFilter : undefined,
      }),
    refetchInterval: 5000, // Refresh every 5 seconds for processing status
  });

  const handleDownloadExcel = async (evfId: string, companyName?: string) => {
    try {
      const blob = await apiClient.downloadExcel(evfId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `EVF_${companyName || evfId}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading Excel:', error);
    }
  };

  const handleViewDetails = (evfId: string) => {
    router.push(`/evf/${evfId}`);
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-gray-200 rounded" />
          ))}
        </div>
      </Card>
    );
  }

  const evfs = data?.items || [];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center space-x-4 mb-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">
            Estado:
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">Todos</option>
            <option value="draft">Rascunho</option>
            <option value="processing">Em Processamento</option>
            <option value="completed">Concluído</option>
            <option value="failed">Falhado</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">
            Tipo de Fundo:
          </label>
          <select
            value={fundTypeFilter}
            onChange={(e) => setFundTypeFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">Todos</option>
            <option value="PT2030">Portugal 2030</option>
            <option value="PRR">PRR</option>
            <option value="SITCE">SITCE</option>
          </select>
        </div>

        <div className="flex-1" />

        <Button onClick={() => refetch()} variant="outline" size="sm">
          Atualizar
        </Button>
      </div>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Empresa</TableHead>
              <TableHead>Tipo de Fundo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>VALF</TableHead>
              <TableHead>TRF</TableHead>
              <TableHead>Criado</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {evfs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                  Nenhum EVF encontrado
                </TableCell>
              </TableRow>
            ) : (
              evfs.map((evf: EVFProject) => (
                <TableRow
                  key={evf.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleViewDetails(evf.id)}
                >
                  <TableCell className="font-medium">
                    <div className="flex items-center">
                      <FileText className="h-4 w-4 mr-2 text-gray-400" />
                      {evf.company_name || 'Sem nome'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {getFundTypeLabel(evf.fund_type)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(evf.status)}>
                      {evf.status === 'draft' && 'Rascunho'}
                      {evf.status === 'processing' && 'A Processar'}
                      {evf.status === 'completed' && 'Concluído'}
                      {evf.status === 'failed' && 'Falhado'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {evf.valf !== null && evf.valf !== undefined ? (
                      <span
                        className={
                          evf.valf < 0 ? 'text-green-600' : 'text-red-600'
                        }
                      >
                        {formatCurrency(evf.valf)}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {evf.trf !== null && evf.trf !== undefined ? (
                      <span
                        className={evf.trf < 4 ? 'text-green-600' : 'text-red-600'}
                      >
                        {formatPercent(evf.trf)}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-gray-500 text-sm">
                    {formatDate(evf.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewDetails(evf.id);
                        }}
                        title="Ver detalhes"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      {evf.status === 'completed' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadExcel(evf.id, evf.company_name);
                          }}
                          title="Descarregar Excel"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Pagination - Future enhancement */}
      {data && data.total > 10 && (
        <div className="flex items-center justify-between px-2">
          <p className="text-sm text-gray-700">
            Mostrando {evfs.length} de {data.total} EVFs
          </p>
        </div>
      )}
    </div>
  );
}
