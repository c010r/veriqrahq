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

export async function fetchOfficialCatalog(): Promise<OfficialCatalogResponse> {
  const response = await fetch(`${API_BASE}/api/catalogs/official`);
  if (!response.ok) throw new Error("No se pudo cargar el catalogo oficial.");
  return response.json();
}

export async function importFile(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source", "ARCE");
  const response = await fetch(`${API_BASE}/api/purchases/import`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) throw new Error("No se pudo importar el archivo.");
  return response.json();
}

export async function syncUrl(url: string): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("url", url);
  const response = await fetch(`${API_BASE}/api/purchases/sync-url`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) throw new Error("No se pudo sincronizar la URL.");
  return response.json();
}


export async function syncOfficialPurchases(options: { inciso?: string; tipo_pub?: string; agency?: string } = {}): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("inciso", options.inciso ?? "29");
  formData.append("tipo_pub", options.tipo_pub ?? "ALL");
  if (options.agency) formData.append("agency", options.agency);
  const response = await fetch(`${API_BASE}/api/purchases/sync-official`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) throw new Error("No se pudo sincronizar el RSS oficial de ARCE.");
  return response.json();
}
