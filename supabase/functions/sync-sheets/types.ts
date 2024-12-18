export interface Product {
  id?: string;
  name: string;
  quantity: number;
  price: number;
  description?: string;
  category?: string;
  last_synced_at?: string;
}

export interface GoogleSheetsProduct {
  name: string;
  quantity: string | number;
  price: string | number;
  description?: string;
  category?: string;
}

export interface SyncStats {
  added: number;
  updated: number;
  deleted: number;
  errors: string[];
}
