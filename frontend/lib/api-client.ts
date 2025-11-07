/**
 * API Client for EVF Portugal 2030
 * Handles all backend communication with tenant context and JWT auth
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface EVFProject {
  id: string;
  tenant_id: string;
  company_id?: string;
  company_name?: string;
  fund_type: 'PT2030' | 'PRR' | 'SITCE';
  status: 'draft' | 'processing' | 'completed' | 'failed';
  valf?: number;
  trf?: number;
  payback?: number;
  input_file_path?: string;
  excel_output_path?: string;
  created_at: string;
  updated_at: string;
}

export interface ComplianceResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
  score: number;
}

export interface FinancialMetrics {
  valf: number;
  trf: number;
  payback: number;
  cash_flows: number[];
  ratios: Record<string, number>;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  agent: string;
  user_id: string;
  tokens_used: number;
  cost_euros: number;
  processing_time_ms: number;
}

export interface ProcessingStatus {
  evf_id: string;
  status: string;
  progress: number;
  current_agent?: string;
  message?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

class APIClient {
  private client: AxiosInstance;
  private tenantId: string | null = null;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor - add auth and tenant headers
    this.client.interceptors.request.use(
      (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        if (this.tenantId) {
          config.headers['X-Tenant-ID'] = this.tenantId;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Token expired, try to refresh
          try {
            await this.refreshToken();
            // Retry the original request
            return this.client.request(error.config);
          } catch (refreshError) {
            // Redirect to login
            if (typeof window !== 'undefined') {
              window.location.href = '/auth/login';
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth methods
  setTenant(tenantId: string) {
    this.tenantId = tenantId;
    if (typeof window !== 'undefined') {
      localStorage.setItem('tenant_id', tenantId);
    }
  }

  setAccessToken(token: string) {
    this.accessToken = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  async login(email: string, password: string) {
    const response = await this.client.post('/api/v1/auth/login', {
      email,
      password,
    });
    this.setAccessToken(response.data.access_token);
    this.setTenant(response.data.tenant_id);
    return response.data;
  }

  async refreshToken() {
    const refreshToken = typeof window !== 'undefined'
      ? localStorage.getItem('refresh_token')
      : null;

    if (!refreshToken) throw new Error('No refresh token');

    const response = await this.client.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    this.setAccessToken(response.data.access_token);
    return response.data;
  }

  logout() {
    this.accessToken = null;
    this.tenantId = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('tenant_id');
      window.location.href = '/auth/login';
    }
  }

  // EVF endpoints
  async uploadSAFT(
    file: File,
    fundType: string,
    onProgress?: (progress: number) => void
  ): Promise<{ evf_id: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('fund_type', fundType);

    const response = await this.client.post('/api/v1/evf/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress?.(percent);
        }
      },
    });

    return response.data;
  }

  async getEVFList(params?: {
    status?: string;
    fund_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: EVFProject[]; total: number }> {
    const response = await this.client.get('/api/v1/evf', { params });
    return response.data;
  }

  async getEVFById(evfId: string): Promise<EVFProject> {
    const response = await this.client.get(`/api/v1/evf/${evfId}`);
    return response.data;
  }

  async getEVFStatus(evfId: string): Promise<ProcessingStatus> {
    const response = await this.client.get(`/api/v1/evf/${evfId}/status`);
    return response.data;
  }

  async getFinancialMetrics(evfId: string): Promise<FinancialMetrics> {
    const response = await this.client.get(`/api/v1/evf/${evfId}/metrics`);
    return response.data;
  }

  async getComplianceResults(evfId: string): Promise<ComplianceResult> {
    const response = await this.client.get(`/api/v1/evf/${evfId}/compliance`);
    return response.data;
  }

  async getAuditLogs(evfId: string): Promise<AuditLog[]> {
    const response = await this.client.get(`/api/v1/evf/${evfId}/audit`);
    return response.data;
  }

  async downloadExcel(evfId: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/evf/${evfId}/excel`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async downloadPDF(evfId: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/evf/${evfId}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async updateEVF(evfId: string, data: Partial<EVFProject>): Promise<EVFProject> {
    const response = await this.client.patch(`/api/v1/evf/${evfId}`, data);
    return response.data;
  }

  async deleteEVF(evfId: string): Promise<void> {
    await this.client.delete(`/api/v1/evf/${evfId}`);
  }

  // Dashboard stats
  async getDashboardStats(): Promise<{
    total_evfs: number;
    completed_evfs: number;
    processing_evfs: number;
    total_cost_euros: number;
    avg_processing_time_hours: number;
  }> {
    const response = await this.client.get('/api/v1/dashboard/stats');
    return response.data;
  }

  // Tenant management
  async getTenantUsage(): Promise<{
    evfs_processed: number;
    tokens_consumed: number;
    cost_euros: number;
    storage_mb: number;
  }> {
    const response = await this.client.get('/api/v1/tenant/usage');
    return response.data;
  }
}

// Singleton instance
const apiClient = new APIClient();

// Initialize from localStorage on client side
if (typeof window !== 'undefined') {
  const token = localStorage.getItem('access_token');
  const tenantId = localStorage.getItem('tenant_id');
  if (token) apiClient.setAccessToken(token);
  if (tenantId) apiClient.setTenant(tenantId);
}

export default apiClient;
