/**
 * EVF Detail Page
 * Complete view of a single EVF project with tabs
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Download, Trash2, FileText, Activity } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FinancialMetrics } from '@/components/financial-metrics';
import { ComplianceViewer } from '@/components/compliance-viewer';
import { ProcessingStatus } from '@/components/processing-status';
import { cn, formatDate, getStatusColor, getFundTypeLabel, downloadBlob } from '@/lib/utils';
import apiClient from '@/lib/api-client';

type Tab = 'overview' | 'metrics' | 'compliance' | 'processing';

export default function EVFDetailPage() {
  const params = useParams();
  const router = useRouter();
  const evfId = params.id as string;
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: evf, isLoading } = useQuery({
    queryKey: ['evf', evfId],
    queryFn: () => apiClient.getEVFById(evfId),
  });

  const handleDownloadExcel = async () => {
    try {
      const blob = await apiClient.downloadExcel(evfId);
      downloadBlob(
        blob,
        `EVF_${evf?.company_name || evfId}_${new Date().toISOString().split('T')[0]}.xlsx`
      );
    } catch (error) {
      console.error('Error downloading Excel:', error);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const blob = await apiClient.downloadPDF(evfId);
      downloadBlob(
        blob,
        `EVF_${evf?.company_name || evfId}_${new Date().toISOString().split('T')[0]}.pdf`
      );
    } catch (error) {
      console.error('Error downloading PDF:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Tem certeza que deseja eliminar este EVF?')) return;

    try {
      await apiClient.deleteEVF(evfId);
      router.push('/dashboard/evfs');
    } catch (error) {
      console.error('Error deleting EVF:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-12 w-64 bg-gray-200 rounded animate-pulse" />
        <div className="h-96 bg-gray-200 rounded animate-pulse" />
      </div>
    );
  }

  if (!evf) {
    return (
      <Card className="p-6">
        <p className="text-center text-gray-500">EVF não encontrado</p>
      </Card>
    );
  }

  const tabs: Array<{ id: Tab; label: string; icon: any }> = [
    { id: 'overview', label: 'Visão Geral', icon: FileText },
    { id: 'metrics', label: 'Métricas Financeiras', icon: Activity },
    { id: 'compliance', label: 'Compliance', icon: FileText },
    { id: 'processing', label: 'Estado', icon: Activity },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <Link href="/dashboard/evfs">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar aos Projetos
          </Button>
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">
              {evf.company_name || 'EVF sem nome'}
            </h1>
            <div className="flex items-center space-x-4 mt-2">
              <Badge className={getStatusColor(evf.status)}>
                {evf.status === 'draft' && 'Rascunho'}
                {evf.status === 'processing' && 'A Processar'}
                {evf.status === 'completed' && 'Concluído'}
                {evf.status === 'failed' && 'Falhado'}
              </Badge>
              <Badge variant="outline">
                {getFundTypeLabel(evf.fund_type)}
              </Badge>
              <span className="text-sm text-gray-500">
                Criado em {formatDate(evf.created_at, true)}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-2">
            {evf.status === 'completed' && (
              <>
                <Button variant="outline" onClick={handleDownloadExcel}>
                  <Download className="h-4 w-4 mr-2" />
                  Excel
                </Button>
                <Button variant="outline" onClick={handleDownloadPDF}>
                  <Download className="h-4 w-4 mr-2" />
                  PDF
                </Button>
              </>
            )}
            <Button variant="outline" onClick={handleDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Eliminar
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors',
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                )}
              >
                <Icon className="h-5 w-5 mr-2" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && (
          <div className="grid gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Informação do Projeto</CardTitle>
              </CardHeader>
              <CardContent className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">ID do Projeto</p>
                  <p className="text-sm text-gray-900 mt-1">{evf.id}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Empresa</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {evf.company_name || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Tipo de Fundo</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {getFundTypeLabel(evf.fund_type)}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Estado</p>
                  <p className="text-sm text-gray-900 mt-1">{evf.status}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Criado</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {formatDate(evf.created_at, true)}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Atualizado</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {formatDate(evf.updated_at, true)}
                  </p>
                </div>
              </CardContent>
            </Card>

            {evf.status === 'completed' && (
              <Card>
                <CardHeader>
                  <CardTitle>Resultados Financeiros</CardTitle>
                </CardHeader>
                <CardContent className="grid md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-500">VALF (NPV)</p>
                    <p className={cn(
                      'text-2xl font-bold mt-1',
                      (evf.valf ?? 0) < 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {evf.valf?.toLocaleString('pt-PT', {
                        style: 'currency',
                        currency: 'EUR',
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">TRF (IRR)</p>
                    <p className={cn(
                      'text-2xl font-bold mt-1',
                      (evf.trf ?? 0) < 4 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {evf.trf?.toFixed(2)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Payback</p>
                    <p className="text-2xl font-bold mt-1 text-gray-900">
                      {evf.payback?.toFixed(1)} anos
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'metrics' && <FinancialMetrics evfId={evfId} />}

        {activeTab === 'compliance' && <ComplianceViewer evfId={evfId} />}

        {activeTab === 'processing' && (
          <ProcessingStatus
            evfId={evfId}
            onComplete={() => {
              // Refetch EVF data
              router.refresh();
            }}
          />
        )}
      </div>
    </div>
  );
}
