export type Purchase = {
  id: string;
  external_id: string;
  status: "vigente" | "anterior" | string;
  procedure_type: string;
  agency: string;
  object: string;
  supplier: string;
  award_date: string | null;
  closing_date: string | null;
  currency: string;
  awarded_amount: string;
  quantity: string;
  unit_price: string;
  source: string;
  source_url: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type PurchaseResponse = {
  items: Purchase[];
  total: number;
  active: number;
  previous: number;
  awarded_total_uyu: string;
  awarded_average_uyu: string;
};

export type CatalogOption = {
  code: string;
  label: string;
};

export type Catalogs = {
  agencies: string[];
  agency_options: CatalogOption[];
  procedure_types: string[];
  procedure_type_options: CatalogOption[];
  currency_options: CatalogOption[];
  unit_options: CatalogOption[];
  statuses: string[];
};

export type OfficialCatalogResource = {
  slug: string;
  name: string;
  description: string;
  source_url: string;
  item_count: number;
  synced_at: string | null;
};

export type OfficialCatalogResponse = {
  resources: OfficialCatalogResource[];
};

export type ImportResult = {
  imported: number;
  updated: number;
  skipped?: number;
  message?: string;
};

export type Filters = {
  query: string;
  status: string;
  agency: string;
  procedure_type: string;
  agency_code: string;
  procedure_type_code: string;
  currency_code: string;
  unit_code: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function fetchPurchases(filters: Filters): Promise<PurchaseResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const response = await fetch(`${API_BASE}/api/purchases?${params.toString()}`);
  if (!response.ok) throw new Error("No se pudieron cargar las compras.");
  return response.json();
}

export async function fetchCatalogs(): Promise<Catalogs> {
  const response = await fetch(`${API_BASE}/api/purchases/catalogs`);
  if (!response.ok) throw new Error("No se pudieron cargar los catalogos.");
  return response.json();
}
