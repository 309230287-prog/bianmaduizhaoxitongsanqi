const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

// ─── Types ───

export type ModelSettingsPayload = {
  provider: string;
  model_name: string;
  base_url: string;
  api_key?: string;
};

export type TaskStatus = {
  task_id: string;
  task_status: string;
  run_status: string;
  can_export: boolean;
  customer_count: number;
  fields_confirmed?: boolean;
  metrics?: {
    total_count: number;
    auto_code_count: number;
    auto_code_with_diff_count: number;
    suggested_review_count: number;
    manual_review_count: number;
    no_reliable_match_count: number;
    returned_to_nature_count: number;
    hard_case_count: number;
    total_rounds: number;
  };
};

export type ConfigStatus = {
  model_configured: boolean;
  model_name: string;
  has_company_catalog: boolean;
  company_product_count: number;
  tasks?: Array<{ task_id: string; task_status: string; can_export: boolean; customer_count: number }>;
};

export type SelfCheckResult = {
  ok: boolean;
  issues: string[];
  model_ready: boolean;
  data_dir_writable: boolean;
};

// ─── Config ───

export async function getConfigStatus(): Promise<ConfigStatus> {
  return requestJson("/config/status");
}

export async function selfCheck(): Promise<SelfCheckResult> {
  return requestJson("/config/self-check");
}

// ─── Model Settings ───

export async function getModelSettings() {
  return requestJson("/settings/model");
}

export async function saveModelSettings(payload: ModelSettingsPayload) {
  return requestJson("/settings/model", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function testModelSettings() {
  return requestJson("/settings/model/test", { method: "POST" });
}

// ─── Company Catalog ───

export async function importCompanyCatalog(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson("/catalog/company/import", { method: "POST", body: formData });
}

export async function getCurrentCatalog(): Promise<{
  product_count: number;
  sample_products: Array<{ code: string; name: string; brand: string; spec: string; unit: string }>;
}> {
  return requestJson("/catalog/company/current");
}

// ─── Tasks ───

export async function createTask(file: File): Promise<{ task_id: string; status: string; customer_count: number }> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson("/tasks", { method: "POST", body: formData });
}

export async function createManualTask(fields: Record<string, string>): Promise<{ task_id: string; status: string; customer_count: number }> {
  return requestJson("/tasks/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/status`);
}

export function exportTaskUrl(taskId: string): string {
  return `${API_BASE}/tasks/${taskId}/export`;
}

export async function startTask(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/start`, { method: "POST" });
}

export async function pauseTask(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/pause`, { method: "POST" });
}

export async function resumeTask(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/resume`, { method: "POST" });
}

export async function stopTask(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/stop`, { method: "POST" });
}

// ─── Field Confirmation ───

export async function confirmFields(
  taskId: string,
  customerMappings: Array<Record<string, unknown>>,
  companyMappings: Array<Record<string, unknown>>,
) {
  return requestJson(`/tasks/${taskId}/fields/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customer_mappings: customerMappings, company_mappings: companyMappings }),
  });
}

export type FieldMapping = {
  business_field: string;
  column_name: string;
  column_index: number;
  importance_level: string;
  confirmed_by_user?: boolean;
};

export type FieldSuggestions = {
  task_id: string;
  customer_mappings: FieldMapping[];
  company_mappings: FieldMapping[];
  missing_required: string[];
  fields_confirmed: boolean;
  can_start: boolean;
};

export async function getFieldSuggestions(taskId: string): Promise<FieldSuggestions> {
  return requestJson(`/tasks/${taskId}/fields/suggestions`);
}

export async function getFieldMappings(taskId: string) {
  return requestJson(`/tasks/${taskId}/fields`);
}

// ─── Manual Input ───

export async function addManualRow(taskId: string, fields: Record<string, string>) {
  return requestJson(`/tasks/${taskId}/manual-row`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
}

// ─── Next Round ───

export async function previewNextRound(
  taskId: string,
  file: File,
): Promise<{ valid: boolean; errors: string[]; warnings: string[]; confirmed_count: number; modified_count: number; no_match_count: number }> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson(`/tasks/${taskId}/next-round/preview`, { method: "POST", body: formData });
}

export async function startNextRound(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/next-round/start`, { method: "POST" });
}

// ─── Helpers ───

async function requestJson(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `请求失败：${response.status}`);
  }
  return response.json();
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "操作失败，请检查本地服务。";
}
