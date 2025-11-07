/**
 * Upload Page
 * File upload interface for new EVF creation
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { FileUpload } from '@/components/file-upload';

export default function UploadPage() {
  const router = useRouter();
  const [fundType, setFundType] = useState<'PT2030' | 'PRR' | 'SITCE'>('PT2030');

  const handleUploadComplete = (evfId: string) => {
    // Redirect to EVF detail page
    router.push(`/dashboard/evf/${evfId}`);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar ao Dashboard
          </Button>
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Criar Novo EVF</h1>
        <p className="text-gray-600 mt-1">
          Carregue o ficheiro SAF-T, Excel ou CSV para começar
        </p>
      </div>

      {/* Fund Type Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Tipo de Fundo</CardTitle>
          <CardDescription>
            Selecione o programa de financiamento para este projeto
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setFundType('PT2030')}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                fundType === 'PT2030'
                  ? 'border-primary bg-primary/5'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <h3 className="font-semibold text-gray-900 mb-1">
                Portugal 2030
              </h3>
              <p className="text-sm text-gray-600">
                Fundo principal para investimento produtivo
              </p>
            </button>

            <button
              onClick={() => setFundType('PRR')}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                fundType === 'PRR'
                  ? 'border-primary bg-primary/5'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <h3 className="font-semibold text-gray-900 mb-1">PRR</h3>
              <p className="text-sm text-gray-600">
                Plano de Recuperação e Resiliência
              </p>
            </button>

            <button
              onClick={() => setFundType('SITCE')}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                fundType === 'SITCE'
                  ? 'border-primary bg-primary/5'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <h3 className="font-semibold text-gray-900 mb-1">SITCE</h3>
              <p className="text-sm text-gray-600">
                Sistema de Incentivos à Transformação
              </p>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* File Upload */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Carregar Ficheiro
        </h2>
        <FileUpload fundType={fundType} onUploadComplete={handleUploadComplete} />
      </div>

      {/* Info Cards */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Formatos Suportados</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-600 space-y-2">
            <p>• SAF-T XML (recomendado)</p>
            <p>• Excel (.xlsx, .xls)</p>
            <p>• CSV com estrutura contabilística</p>
            <p className="text-xs text-gray-500 mt-4">
              Máximo 50MB por ficheiro
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Processamento</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-600 space-y-2">
            <p>• Validação automática de dados</p>
            <p>• Cálculos financeiros (VALF, TRF)</p>
            <p>• Verificação de compliance PT2030</p>
            <p className="text-xs text-gray-500 mt-4">
              Tempo estimado: 3-5 minutos
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
