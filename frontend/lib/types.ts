/**
 * TypeScript types for API responses
 * Centralized type definitions for the EVF Portugal 2030 platform
 */

// Auth Types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
  name: string;
  role: 'admin' | 'member' | 'viewer';
  tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  plan: 'starter' | 'professional' | 'enterprise';
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// EVF Types
export type FundType = 'PT2030' | 'PRR' | 'SITCE';
export type EVFStatus = 'draft' | 'processing' | 'completed' | 'failed';
export type UserRole = 'admin' | 'member' | 'viewer';
export type PlanType = 'starter' | 'professional' | 'enterprise';

export interface EVFProject {
  id: string;
  tenant_id: string;
  company_id?: string;
  company_name?: string;
  fund_type: FundType;
  status: EVFStatus;
  valf?: number;
  trf?: number;
  payback?: number;
  input_file_path?: string;
  excel_output_path?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateEVFRequest {
  company_name: string;
  fund_type: FundType;
  company_id?: string;
}

export interface UploadSAFTRequest {
  file: File;
  fund_type: FundType;
}

export interface UploadSAFTResponse {
  evf_id: string;
  status: string;
  message: string;
}

// Compliance Types
export interface ComplianceResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
  score: number;
  checked_at: string;
}

export interface ComplianceRule {
  rule_id: string;
  rule_name: string;
  description: string;
  category: string;
  severity: 'error' | 'warning' | 'info';
  passed: boolean;
  details?: string;
}

// Financial Types
export interface FinancialMetrics {
  valf: number;
  trf: number;
  payback: number;
  cash_flows: number[];
  ratios: Record<string, number>;
  calculated_at: string;
}

export interface CashFlow {
  year: number;
  revenue: number;
  costs: number;
  net_cash_flow: number;
  cumulative_cash_flow: number;
}

// Audit Types
export interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  agent: string;
  user_id: string;
  evf_id?: string;
  tokens_used: number;
  cost_euros: number;
  processing_time_ms: number;
  details?: Record<string, any>;
}

export interface AuditSummary {
  total_actions: number;
  total_tokens: number;
  total_cost_euros: number;
  avg_processing_time_ms: number;
  actions_by_agent: Record<string, number>;
}

// Processing Types
export interface ProcessingStatus {
  evf_id: string;
  status: EVFStatus;
  progress: number;
  current_agent?: string;
  message?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  stages: ProcessingStage[];
}

export interface ProcessingStage {
  stage_name: string;
  agent: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

// Dashboard Types
export interface DashboardStats {
  total_evfs: number;
  completed_evfs: number;
  processing_evfs: number;
  failed_evfs: number;
  total_cost_euros: number;
  avg_processing_time_hours: number;
  success_rate: number;
}

export interface TenantUsage {
  evfs_processed: number;
  tokens_consumed: number;
  cost_euros: number;
  storage_mb: number;
  api_calls: number;
  last_updated: string;
}

// List Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ListParams {
  page?: number;
  page_size?: number;
  status?: EVFStatus;
  fund_type?: FundType;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Error Types
export interface APIError {
  detail: string;
  code?: string;
  field?: string;
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// User & Tenant Types
export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  plan: PlanType;
  is_active: boolean;
  created_at: string;
  settings?: TenantSettings;
}

export interface TenantSettings {
  max_evfs_per_month: number;
  max_storage_gb: number;
  features: string[];
  branding?: {
    logo_url?: string;
    primary_color?: string;
  };
}

// Upload Progress Types
export interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  evfId?: string;
  error?: string;
  uploadedBytes?: number;
  totalBytes?: number;
}

// Notification Types
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: number;
  read?: boolean;
  action?: {
    label: string;
    href: string;
  };
}

// Export Types
export interface ExportOptions {
  format: 'excel' | 'pdf';
  include_charts: boolean;
  include_audit: boolean;
  language: 'pt' | 'en';
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'status_update' | 'progress_update' | 'error' | 'completed';
  evf_id: string;
  data: any;
  timestamp: string;
}
