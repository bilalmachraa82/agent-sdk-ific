/**
 * Compliance Results Viewer
 * Displays PT2030/PRR compliance validation results
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { CheckCircle, XCircle, AlertTriangle, Lightbulb } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import apiClient from '@/lib/api-client';

interface ComplianceViewerProps {
  evfId: string;
}

export function ComplianceViewer({ evfId }: ComplianceViewerProps) {
  const { data: compliance, isLoading } = useQuery({
    queryKey: ['compliance', evfId],
    queryFn: () => apiClient.getComplianceResults(evfId),
  });

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-6 w-48 bg-gray-200 rounded" />
          <div className="h-4 w-64 bg-gray-200 rounded mt-2" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="h-20 bg-gray-200 rounded" />
            <div className="h-20 bg-gray-200 rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!compliance) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-gray-500">
            Dados de compliance não disponíveis
          </p>
        </CardContent>
      </Card>
    );
  }

  const scoreColor =
    compliance.score >= 80
      ? 'text-green-600'
      : compliance.score >= 60
      ? 'text-orange-600'
      : 'text-red-600';

  const scoreLabel =
    compliance.score >= 80
      ? 'Excelente'
      : compliance.score >= 60
      ? 'Aceitável'
      : 'Insuficiente';

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Compliance PT2030</CardTitle>
              <CardDescription>
                Resultado da validação de requisitos
              </CardDescription>
            </div>
            {compliance.valid ? (
              <Badge className="bg-green-100 text-green-800">
                <CheckCircle className="h-4 w-4 mr-1" />
                Válido
              </Badge>
            ) : (
              <Badge className="bg-red-100 text-red-800">
                <XCircle className="h-4 w-4 mr-1" />
                Inválido
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Pontuação de Compliance
                </span>
                <span className={`text-2xl font-bold ${scoreColor}`}>
                  {compliance.score}/100
                </span>
              </div>
              <Progress value={compliance.score} />
              <p className="text-sm text-gray-600 mt-2">{scoreLabel}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Errors */}
      {compliance.errors.length > 0 && (
        <Card className="border-red-200">
          <CardHeader className="bg-red-50">
            <CardTitle className="text-red-800 flex items-center">
              <XCircle className="h-5 w-5 mr-2" />
              Erros ({compliance.errors.length})
            </CardTitle>
            <CardDescription className="text-red-600">
              Requisitos obrigatórios não cumpridos
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <ul className="space-y-3">
              {compliance.errors.map((error, index) => (
                <li
                  key={index}
                  className="flex items-start p-3 bg-red-50 rounded-lg"
                >
                  <XCircle className="h-5 w-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-red-900">{error}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Warnings */}
      {compliance.warnings.length > 0 && (
        <Card className="border-orange-200">
          <CardHeader className="bg-orange-50">
            <CardTitle className="text-orange-800 flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Avisos ({compliance.warnings.length})
            </CardTitle>
            <CardDescription className="text-orange-600">
              Recomendações para melhorar a candidatura
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <ul className="space-y-3">
              {compliance.warnings.map((warning, index) => (
                <li
                  key={index}
                  className="flex items-start p-3 bg-orange-50 rounded-lg"
                >
                  <AlertTriangle className="h-5 w-5 text-orange-600 mr-3 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-orange-900">{warning}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Suggestions */}
      {compliance.suggestions.length > 0 && (
        <Card className="border-blue-200">
          <CardHeader className="bg-blue-50">
            <CardTitle className="text-blue-800 flex items-center">
              <Lightbulb className="h-5 w-5 mr-2" />
              Sugestões ({compliance.suggestions.length})
            </CardTitle>
            <CardDescription className="text-blue-600">
              Ações recomendadas para corrigir problemas
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <ul className="space-y-3">
              {compliance.suggestions.map((suggestion, index) => (
                <li
                  key={index}
                  className="flex items-start p-3 bg-blue-50 rounded-lg"
                >
                  <Lightbulb className="h-5 w-5 text-blue-600 mr-3 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-blue-900">{suggestion}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* All Clear */}
      {compliance.valid &&
        compliance.errors.length === 0 &&
        compliance.warnings.length === 0 && (
          <Card className="border-green-200">
            <CardContent className="p-6 bg-green-50">
              <div className="flex items-center">
                <CheckCircle className="h-8 w-8 text-green-600 mr-4" />
                <div>
                  <p className="font-medium text-green-900">
                    Todos os requisitos cumpridos
                  </p>
                  <p className="text-sm text-green-700">
                    O EVF está pronto para submissão ao PT2030
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
    </div>
  );
}
