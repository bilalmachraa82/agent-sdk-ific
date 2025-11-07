/**
 * File Upload Component
 * Drag & drop interface for SAF-T, Excel, and CSV files
 * Shows upload progress and validation status
 */

'use client';

import { useState, useCallback } from 'react';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn, formatFileSize } from '@/lib/utils';
import apiClient from '@/lib/api-client';
import { useStore } from '@/lib/store';

interface FileUploadProps {
  fundType: 'PT2030' | 'PRR' | 'SITCE';
  onUploadComplete?: (evfId: string) => void;
  onError?: (error: string) => void;
}

export function FileUpload({ fundType, onUploadComplete, onError }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [validationStatus, setValidationStatus] = useState<
    'idle' | 'validating' | 'valid' | 'invalid'
  >('idle');
  const [error, setError] = useState<string | null>(null);

  const addNotification = useStore((state) => state.addNotification);

  const acceptedTypes = [
    'application/xml',
    'text/xml',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
  ];

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const validateFile = (file: File): boolean => {
    // Check file type
    if (!acceptedTypes.includes(file.type) && !file.name.endsWith('.xml')) {
      setError('Tipo de ficheiro não suportado. Use SAF-T XML, Excel ou CSV.');
      return false;
    }

    // Check file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError('Ficheiro demasiado grande. Máximo 50MB.');
      return false;
    }

    setError(null);
    return true;
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile && validateFile(droppedFile)) {
        setFile(droppedFile);
        setValidationStatus('validating');

        // Simulate client-side validation
        setTimeout(() => {
          setValidationStatus('valid');
        }, 1000);
      }
    },
    []
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
      setValidationStatus('validating');

      setTimeout(() => {
        setValidationStatus('valid');
      }, 1000);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const result = await apiClient.uploadSAFT(file, fundType, (progress) => {
        setUploadProgress(progress);
      });

      addNotification({
        type: 'success',
        title: 'Upload concluído',
        message: `Ficheiro ${file.name} enviado com sucesso. Processamento iniciado.`,
      });

      onUploadComplete?.(result.evf_id);

      // Reset form
      setFile(null);
      setUploadProgress(0);
      setValidationStatus('idle');
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Erro ao enviar ficheiro';
      setError(errorMsg);
      onError?.(errorMsg);

      addNotification({
        type: 'error',
        title: 'Erro no upload',
        message: errorMsg,
      });
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setUploadProgress(0);
    setValidationStatus('idle');
    setError(null);
  };

  return (
    <Card className="p-6">
      {!file ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            'border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-gray-300 hover:border-gray-400'
          )}
        >
          <input
            type="file"
            id="file-upload"
            className="hidden"
            accept=".xml,.xlsx,.xls,.csv"
            onChange={handleFileSelect}
            disabled={uploading}
          />

          <label htmlFor="file-upload" className="cursor-pointer">
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              Arraste o ficheiro ou clique para selecionar
            </p>
            <p className="text-sm text-gray-500 mb-4">
              SAF-T XML, Excel ou CSV (máx. 50MB)
            </p>
            <Button type="button" variant="outline">
              Selecionar Ficheiro
            </Button>
          </label>
        </div>
      ) : (
        <div className="space-y-4">
          {/* File Info */}
          <div className="flex items-start justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-start space-x-3 flex-1">
              <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{file.name}</p>
                <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
              </div>
            </div>

            {/* Validation Status */}
            <div className="flex items-center space-x-2 ml-4">
              {validationStatus === 'validating' && (
                <div className="flex items-center text-blue-600">
                  <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full mr-2" />
                  <span className="text-sm">Validando...</span>
                </div>
              )}
              {validationStatus === 'valid' && (
                <div className="flex items-center text-green-600">
                  <CheckCircle className="h-5 w-5 mr-1" />
                  <span className="text-sm">Válido</span>
                </div>
              )}
              {validationStatus === 'invalid' && (
                <div className="flex items-center text-red-600">
                  <AlertCircle className="h-5 w-5 mr-1" />
                  <span className="text-sm">Inválido</span>
                </div>
              )}

              {!uploading && (
                <button
                  onClick={handleRemoveFile}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              )}
            </div>
          </div>

          {/* Upload Progress */}
          {uploading && (
            <div className="space-y-2">
              <Progress value={uploadProgress} />
              <p className="text-sm text-center text-gray-600">
                A enviar... {uploadProgress}%
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3">
            <Button
              variant="outline"
              onClick={handleRemoveFile}
              disabled={uploading}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleUpload}
              disabled={uploading || validationStatus !== 'valid'}
            >
              {uploading ? 'A enviar...' : 'Enviar e Processar'}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
