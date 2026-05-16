import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export interface LPOLineItem {
  id: number;
  document_id: number;
  item_name: string;
  quantity: number;
  unit: string;
  date_extracted: string;
}

export interface LPODocument {
  id: number;
  filename: string;
  customer_name: string | null;
  upload_timestamp: string;
  status: string;
}

export interface MasterProcurementItem {
  item_name: string;
  total_quantity: number;
  unit: string;
  item_ids: number[];
  item_statuses: string[];
}

export interface DistributionItemDetail {
  item_name: string;
  quantity: number;
  unit: string;
}

export interface DistributionEntry {
  customer_name: string;
  items: DistributionItemDetail[];
}

export interface DashboardData {
  date: string;
  master_procurement: MasterProcurementItem[];
  distribution: DistributionEntry[];
}

export interface RawDataItem {
  id: number;
  document_id: number;
  item_name: string;
  quantity: number;
  unit: string;
  date_extracted: string;
}

export interface UploadResponse {
  documents: LPODocument[];
  message: string;
}

export async function uploadPDFs(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });
  const response = await api.post<UploadResponse>('/lpo/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getRawData(date?: string): Promise<RawDataItem[]> {
  const params = date ? { date_filter: date } : {};
  const response = await api.get<RawDataItem[]>('/lpo/raw-data', { params });
  return response.data;
}

export async function getDashboard(date?: string): Promise<DashboardData> {
  const params = date ? { date_filter: date } : {};
  const response = await api.get<DashboardData>('/lpo/dashboard', { params });
  return response.data;
}

export async function toggleItemStatus(itemId: number, status: string): Promise<void> {
  await api.patch(`/lpo/items/${itemId}/status`, { status });
}

export default api;
