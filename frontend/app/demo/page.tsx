/**
 * Demo Page - Complete EVF Workflow Demonstration
 *
 * This page demonstrates:
 * 1. Login/Authentication
 * 2. EVF Project List
 * 3. File Upload (SAF-T)
 * 4. Processing Status with Progress
 * 5. Results Display
 * 6. Excel Download
 *
 * Usage: Navigate to /demo to test the full workflow
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { FileText, Upload, Download, Play, RefreshCw, CheckCircle, XCircle, AlertCircle, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api-client';
import { useStore } from '@/lib/store';
import type { EVFProject, ProcessingStatus, FinancialMetrics, ComplianceResult } from '@/lib/types';

export default function DemoPage() {
  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [email, setEmail] = useState('demo@evfportugal.pt');
  const [password, setPassword] = useState('demo123');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // EVF List State
  const [evfProjects, setEvfProjects] = useState<EVFProject[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [selectedEVF, setSelectedEVF] = useState<string | null>(null);

  // Upload State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [fundType, setFundType] = useState<'PT2030' | 'PRR' | 'SITCE'>('PT2030');

  // Processing State
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null);
  const [processingLoading, setProcessingLoading] = useState(false);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Results State
  const [financialMetrics, setFinancialMetrics] = useState<FinancialMetrics | null>(null);
  const [complianceResults, setComplianceResults] = useState<ComplianceResult | null>(null);
  const [downloadLoading, setDownloadLoading] = useState(false);

  const { setUser, setTenant } = useStore();

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // Authentication Handler
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');

    try {
      const response = await apiClient.login(email, password);

      setUser({
        id: response.user_id,
        email: response.email,
        name: response.name,
        role: response.role,
        tenant_id: response.tenant_id,
      });

      setTenant({
        id: response.tenant_id,
        slug: response.tenant_slug,
        name: response.tenant_name,
        plan: response.plan,
      });

      setIsAuthenticated(true);
      loadEVFProjects();
    } catch (err: any) {
      setLoginError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoginLoading(false);
    }
  };

  // Logout Handler
  const handleLogout = () => {
    apiClient.logout();
    setIsAuthenticated(false);
    setEvfProjects([]);
    setSelectedEVF(null);
    setProcessingStatus(null);
    setFinancialMetrics(null);
    setComplianceResults(null);
  };

  // Load EVF Projects
  const loadEVFProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const response = await apiClient.getEVFList({ limit: 10, offset: 0 });
      setEvfProjects(response.items);
    } catch (err: any) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  // File Upload Handler
  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setUploadLoading(true);
    setUploadError('');
    setUploadProgress(0);

    try {
      const response = await apiClient.uploadSAFT(
        uploadFile,
        fundType,
        (progress) => setUploadProgress(progress)
      );

      setSelectedEVF(response.evf_id);
      setUploadFile(null);
      await loadEVFProjects();

      // Auto-start processing
      setTimeout(() => handleStartProcessing(response.evf_id), 1000);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploadLoading(false);
    }
  };

  // Start Processing
  const handleStartProcessing = async (evfId: string) => {
    setProcessingLoading(true);
    try {
      await apiClient.startProcessing(evfId);
      startPollingStatus(evfId);
    } catch (err: any) {
      console.error('Failed to start processing:', err);
    } finally {
      setProcessingLoading(false);
    }
  };

  // Poll Processing Status
  const startPollingStatus = (evfId: string) => {
    // Clear existing interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    // Poll every 2 seconds
    const interval = setInterval(async () => {
      try {
        const status = await apiClient.getEVFStatus(evfId);
        setProcessingStatus(status);

        // Stop polling when completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          setPollingInterval(null);

          if (status.status === 'completed') {
            loadResults(evfId);
          }
        }
      } catch (err) {
        console.error('Failed to get status:', err);
      }
    }, 2000);

    setPollingInterval(interval);
  };

  // Load Results
  const loadResults = async (evfId: string) => {
    try {
      const [metrics, compliance] = await Promise.all([
        apiClient.getFinancialMetrics(evfId),
        apiClient.getComplianceResults(evfId),
      ]);
      setFinancialMetrics(metrics);
      setComplianceResults(compliance);
    } catch (err) {
      console.error('Failed to load results:', err);
    }
  };

  // Download Excel Report
  const handleDownloadExcel = async (evfId: string) => {
    setDownloadLoading(true);
    try {
      const blob = await apiClient.downloadExcel(evfId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `EVF_${evfId}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('Download failed:', err);
    } finally {
      setDownloadLoading(false);
    }
  };

  // Render Login Form
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="h-10 w-10 bg-primary rounded-lg flex items-center justify-center">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <div>
                <CardTitle>EVF Portugal 2030 - Demo</CardTitle>
                <CardDescription>Complete workflow demonstration</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              {loginError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{loginError}</p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="demo@evfportugal.pt"
                  disabled={loginLoading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="demo123"
                  disabled={loginLoading}
                />
              </div>

              <Button type="submit" className="w-full" disabled={loginLoading}>
                {loginLoading ? 'Logging in...' : 'Login'}
              </Button>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-800">
                  <strong>Demo Credentials:</strong><br />
                  Email: demo@evfportugal.pt<br />
                  Password: demo123
                </p>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render Main Demo Interface
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-primary rounded-lg flex items-center justify-center">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">EVF Portugal 2030 - Demo</h1>
              <p className="text-sm text-gray-600">Complete workflow demonstration</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Upload & Project List */}
          <div className="space-y-6">
            {/* Upload Form */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Upload SAF-T File
                </CardTitle>
                <CardDescription>
                  Upload a SAF-T file to create a new EVF project
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleFileUpload} className="space-y-4">
                  {uploadError && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-800">{uploadError}</p>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Fund Type
                    </label>
                    <select
                      value={fundType}
                      onChange={(e) => setFundType(e.target.value as any)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      disabled={uploadLoading}
                    >
                      <option value="PT2030">PT2030</option>
                      <option value="PRR">PRR</option>
                      <option value="SITCE">SITCE</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SAF-T File
                    </label>
                    <input
                      type="file"
                      accept=".xml,.zip"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      disabled={uploadLoading}
                    />
                  </div>

                  {uploadLoading && (
                    <div className="space-y-2">
                      <Progress value={uploadProgress} />
                      <p className="text-sm text-gray-600 text-center">
                        Uploading... {uploadProgress}%
                      </p>
                    </div>
                  )}

                  <Button
                    type="submit"
                    className="w-full"
                    disabled={!uploadFile || uploadLoading}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {uploadLoading ? 'Uploading...' : 'Upload & Process'}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Project List */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>EVF Projects</CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadEVFProjects}
                    disabled={loadingProjects}
                  >
                    <RefreshCw className={`h-4 w-4 ${loadingProjects ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {loadingProjects ? (
                  <div className="text-center py-8 text-gray-500">
                    <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                    Loading projects...
                  </div>
                ) : evfProjects.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No projects yet. Upload a file to get started.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {evfProjects.map((project) => (
                      <div
                        key={project.id}
                        className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                          selectedEVF === project.id
                            ? 'border-primary bg-primary/5'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => {
                          setSelectedEVF(project.id);
                          if (project.status === 'processing') {
                            startPollingStatus(project.id);
                          } else if (project.status === 'completed') {
                            loadResults(project.id);
                          }
                        }}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="font-medium text-gray-900">
                              {project.company_name || 'Unnamed Project'}
                            </p>
                            <p className="text-sm text-gray-600">
                              {project.fund_type} • {new Date(project.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <Badge variant={
                            project.status === 'completed' ? 'default' :
                            project.status === 'processing' ? 'secondary' :
                            project.status === 'failed' ? 'destructive' : 'outline'
                          }>
                            {project.status}
                          </Badge>
                        </div>
                        {project.status === 'completed' && project.valf !== undefined && (
                          <div className="flex gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">VALF:</span>
                              <span className={`ml-1 font-medium ${project.valf < 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {project.valf.toFixed(2)}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-600">TRF:</span>
                              <span className={`ml-1 font-medium ${project.trf && project.trf < 4 ? 'text-green-600' : 'text-red-600'}`}>
                                {project.trf?.toFixed(2)}%
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Status & Results */}
          <div className="space-y-6">
            {/* Processing Status */}
            {processingStatus && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Play className="h-5 w-5" />
                    Processing Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Progress</span>
                      <span className="font-medium">{processingStatus.progress}%</span>
                    </div>
                    <Progress value={processingStatus.progress} />
                  </div>

                  {processingStatus.current_agent && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <p className="text-sm text-blue-900">
                        <strong>Current Agent:</strong> {processingStatus.current_agent}
                      </p>
                      {processingStatus.message && (
                        <p className="text-sm text-blue-800 mt-1">
                          {processingStatus.message}
                        </p>
                      )}
                    </div>
                  )}

                  {processingStatus.error && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-800">{processingStatus.error}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Financial Results */}
            {financialMetrics && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    Financial Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">VALF</p>
                      <p className={`text-2xl font-bold ${financialMetrics.valf < 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {financialMetrics.valf.toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {financialMetrics.valf < 0 ? 'Approved' : 'Not Approved'}
                      </p>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">TRF</p>
                      <p className={`text-2xl font-bold ${financialMetrics.trf < 4 ? 'text-green-600' : 'text-red-600'}`}>
                        {financialMetrics.trf.toFixed(2)}%
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {financialMetrics.trf < 4 ? 'Approved' : 'Not Approved'}
                      </p>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">Payback</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {financialMetrics.payback.toFixed(1)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">years</p>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">Cash Flows</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {financialMetrics.cash_flows.length}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">periods</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Compliance Results */}
            {complianceResults && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {complianceResults.valid ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    Compliance Check
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Score</span>
                    <span className="text-2xl font-bold">{complianceResults.score}/100</span>
                  </div>

                  {complianceResults.errors.length > 0 && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm font-medium text-red-900 mb-1">Errors</p>
                      <ul className="text-sm text-red-800 space-y-1">
                        {complianceResults.errors.map((error, idx) => (
                          <li key={idx}>• {error}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {complianceResults.warnings.length > 0 && (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-sm font-medium text-yellow-900 mb-1">Warnings</p>
                      <ul className="text-sm text-yellow-800 space-y-1">
                        {complianceResults.warnings.map((warning, idx) => (
                          <li key={idx}>• {warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Download Section */}
            {selectedEVF && financialMetrics && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Download className="h-5 w-5" />
                    Export Results
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Button
                    className="w-full"
                    onClick={() => handleDownloadExcel(selectedEVF)}
                    disabled={downloadLoading}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    {downloadLoading ? 'Downloading...' : 'Download Excel Report'}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
