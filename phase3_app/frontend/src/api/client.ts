const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export type ModelSettingsPayload = {
  provider: string;
  model_name: string;
  base_url: string;
  api_key?: string;
};

export type TaskStatus = {
  task_id: string;
  status: string;
  customer_count: number;
  metrics?: {
    total_count: number;
    auto_code_count: number;
    returned_to_nature_count: number;
    hard_case_count: number;
  };
};

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

export async function importCompanyCatalog(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson("/catalog/company/import", {
    method: "POST",
    body: formData,
  });
}

export async function createTask(file: File): Promise<TaskStatus> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson("/tasks", {
    method: "POST",
    body: formData,
  }) as Promise<TaskStatus>;
}

export async function startTask(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/start`, { method: "POST" }) as Promise<TaskStatus>;
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  return requestJson(`/tasks/${taskId}/status`) as Promise<TaskStatus>;
}

export function exportTaskUrl(taskId: string): string {
  return `${API_BASE}/tasks/${taskId}/export`;
}

async function requestJson(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json();
}

