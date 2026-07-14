import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Download, FileUp, RefreshCw, Search } from "lucide-react";
import { Catalogs, Filters, Purchase, PurchaseResponse, fetchCatalogs, fetchPurchases, importFile, syncOfficialPurchases } from "../lib/api";

const emptyResponse: PurchaseResponse = {
  items: [],
  total: 0,
  active: 0,
  previous: 0,
  awarded_total_uyu: "0",
  awarded_average_uyu: "0"
};

const defaultFilters: Filters = {
  query: "",
  status: "all",
  agency: "all",
  procedure_type: "all"
};

function money(value: string | number, currency = "UYU") {
  return new Intl.NumberFormat("es-UY", {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "UYU" ? 0 : 2
  }).format(Number(value) || 0);
}

function dateLabel(value: string | null) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-UY", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

function errorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Ocurrio un error inesperado.";
}

export function App() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [data, setData] = useState<PurchaseResponse>(emptyResponse);
  const [catalogs, setCatalogs] = useState<Catalogs>({ agencies: [], agency_options: [], procedure_types: [], statuses: [] });
  const [selected, setSelected] = useState<Purchase | null>(null);
  const [status, setStatus] = useState("Listo para importar XML, RSS o CSV de ARCE.");
  const [loading, setLoading] = useState(false);
  const didInitialLoad = useRef(false);

  async function reload(nextFilters = filters) {
    setLoading(true);
    try {
      const [purchases, nextCatalogs] = await Promise.all([fetchPurchases(nextFilters), fetchCatalogs()]);
      setData(purchases);
      setCatalogs(nextCatalogs);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload(defaultFilters);
  }, []);

  useEffect(() => {
    if (!didInitialLoad.current) {
      didInitialLoad.current = true;
      return;
    }
    const timeout = window.setTimeout(() => reload(filters), 250);
    return () => window.clearTimeout(timeout);
  }, [filters]);

  const rows = useMemo(() => data.items, [data.items]);

  function updateFilter(key: keyof Filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setStatus(`Importando ${file.name}...`);
    try {
      await importFile(file);
      setStatus(`${file.name} importado.`);
      event.target.value = "";
      await reload();
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function handleSyncAgency() {
    if (filters.agency === "all") {
      setStatus("Seleccione un organismo para sincronizar sus llamados.");
      return;
    }
    const agencyOption = catalogs.agency_options.find((option) => option.label === filters.agency);
    if (!agencyOption) {
      setStatus("No se encontro el codigo ARCE del organismo seleccionado.");
      return;
    }
    setStatus(`Sincronizando vigentes y adjudicadas de ${filters.agency}...`);
    try {
      const result = await syncOfficialPurchases({ inciso: agencyOption.code, tipo_pub: "ALL", agency: filters.agency });
      const nextFilters = { ...filters, status: "all" };
      setFilters(nextFilters);
      setStatus(`Organismo sincronizado: ${result.imported} nuevos, ${result.updated} actualizados.`);
      await reload(nextFilters);
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  function exportCsv() {
    const headers = ["expediente", "estado", "procedimiento", "organismo", "objeto", "proveedor", "fecha_adjudicacion", "moneda", "precio_adjudicado"];
    const body = rows.map((row) => [
      row.external_id,
      row.status,
      row.procedure_type,
      row.agency,
      row.object,
      row.supplier,
      row.award_date ?? "",
      row.currency,
      row.awarded_amount
    ]);
    const csv = [headers, ...body].map((line) => line.map((cell) => `"${String(cell).replaceAll("\"", "\"\"")}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "compras-estatales.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen bg-[#f6f8f5] text-ink">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-6 md:flex-row md:items-end md:justify-between lg:px-10">
          <div>
            <p className="text-sm font-extrabold text-accent">VeriqraHQ</p>
            <h1 className="text-4xl font-black tracking-normal md:text-5xl">Compras estatales</h1>
            <p className="mt-1 text-sm text-muted" role="status" aria-live="polite">{status}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-accent bg-accent px-4 py-2 font-bold text-white">
              <FileUp size={18} /> Importar archivo
              <input className="sr-only" type="file" accept=".xml,.rss,.csv,text/csv,application/xml,text/xml" onChange={handleFile} />
            </label>
            <button className="inline-flex min-h-11 items-center gap-2 rounded-md border border-accent bg-white px-4 py-2 font-bold text-accent" type="button" onClick={handleSyncAgency} disabled={loading}>
              <RefreshCw size={18} /> Sincronizar organismo
            </button>
            <button className="inline-flex min-h-11 items-center gap-2 rounded-md border border-accent bg-white px-4 py-2 font-bold text-accent" type="button" onClick={exportCsv}>
              <Download size={18} /> Exportar
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 lg:px-10">
        <section className="grid gap-3 md:grid-cols-4" aria-label="Resumen">
          <Metric label="Vigentes" value={data.active} />
          <Metric label="Anteriores" value={data.previous} />
          <Metric label="Total UYU adjudicado" value={money(data.awarded_total_uyu)} />
          <Metric label="Promedio UYU" value={money(data.awarded_average_uyu)} />
        </section>

        <section className="rounded-lg border border-line bg-white p-4 shadow-sm">
          <div className="grid gap-3 lg:grid-cols-[1.4fr_repeat(3,1fr)_auto]">
            <label className="grid gap-1 text-sm font-bold text-muted">
              Buscar
              <span className="relative">
                <Search className="pointer-events-none absolute left-3 top-3 text-muted" size={18} />
                <input className="min-h-11 w-full rounded-md border border-line pl-10 pr-3 text-ink" type="search" value={filters.query} onChange={(event) => updateFilter("query", event.target.value)} placeholder="Objeto, proveedor, expediente" />
              </span>
            </label>
            <Select label="Estado" value={filters.status} onChange={(value) => updateFilter("status", value)} options={["all", ...catalogs.statuses]} />
            <Select label="Organismo" value={filters.agency} onChange={(value) => updateFilter("agency", value)} options={["all", ...catalogs.agencies]} />
            <Select label="Procedimiento" value={filters.procedure_type} onChange={(value) => updateFilter("procedure_type", value)} options={["all", ...catalogs.procedure_types]} />
            <button className="mt-auto inline-flex min-h-11 items-center justify-center gap-2 rounded-md border border-accent bg-white px-4 py-2 font-bold text-accent disabled:cursor-not-allowed disabled:opacity-60" type="button" onClick={handleSyncAgency} disabled={loading || filters.agency === "all"}>
              <RefreshCw size={18} /> Sincronizar
            </button>
          </div>
        </section>

        <section className="overflow-hidden rounded-lg border border-line bg-white shadow-sm">
          <div className="flex flex-col gap-1 border-b border-line p-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-black">Resultados</h2>
              <p className="text-sm text-muted" aria-live="polite">{loading ? "Cargando..." : `${data.total} compras encontradas`}</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[1100px] w-full border-collapse text-left">
              <thead className="bg-[#eef3ef] text-sm">
                <tr>
                  <th className="border-b border-line p-3">Estado</th>
                  <th className="border-b border-line p-3">Expediente</th>
                  <th className="border-b border-line p-3">Objeto</th>
                  <th className="border-b border-line p-3">Organismo</th>
                  <th className="border-b border-line p-3">Proveedor</th>
                  <th className="border-b border-line p-3">Fecha</th>
                  <th className="border-b border-line p-3">Adjudicación</th>
                  <th className="border-b border-line p-3">Acción</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((purchase) => (
                  <tr className="hover:bg-[#f8faf8]" key={purchase.id}>
                    <td className="border-b border-line p-3"><Badge status={purchase.status} /></td>
                    <td className="border-b border-line p-3 font-bold">{purchase.external_id}<span className="block text-sm font-medium text-muted">{purchase.procedure_type}</span></td>
                    <td className="max-w-xl border-b border-line p-3 font-bold">{purchase.object}</td>
                    <td className="border-b border-line p-3">{purchase.agency}</td>
                    <td className="border-b border-line p-3">{purchase.supplier}</td>
                    <td className="border-b border-line p-3">{dateLabel(purchase.award_date)}<span className="block text-sm text-muted">Cierre: {dateLabel(purchase.closing_date)}</span></td>
                    <td className="border-b border-line p-3 font-black">{money(purchase.awarded_amount, purchase.currency)}<span className="block text-sm font-medium text-muted">Unitario: {money(purchase.unit_price, purchase.currency)}</span></td>
                    <td className="border-b border-line p-3"><button className="rounded-md border border-accent px-3 py-2 font-bold text-accent" type="button" onClick={() => setSelected(purchase)}>Ver</button></td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td className="h-32 border-b border-line p-3 text-center text-muted" colSpan={8}>No hay compras para los filtros seleccionados.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {selected && <Detail purchase={selected} onClose={() => setSelected(null)} />}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="rounded-lg border border-line bg-white p-4 shadow-sm">
      <span className="text-sm font-bold text-muted">{label}</span>
      <strong className="mt-2 block text-3xl font-black">{value}</strong>
    </article>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-sm font-bold text-muted">
      {label}
      <select className="min-h-11 rounded-md border border-line bg-white px-3 text-ink" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>{option === "all" ? "Todos" : option}</option>
        ))}
      </select>
    </label>
  );
}

function Badge({ status }: { status: string }) {
  const active = status === "vigente";
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-black ${active ? "bg-teal-100 text-teal-800" : "bg-slate-200 text-slate-700"}`}>{status}</span>;
}

function Detail({ purchase, onClose }: { purchase: Purchase; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-10 grid place-items-center bg-black/45 p-4" role="dialog" aria-modal="true" aria-labelledby="detail-title">
      <section className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="detail-title" className="text-2xl font-black">{purchase.object}</h2>
            <p className="text-muted">{purchase.external_id} · {purchase.procedure_type}</p>
          </div>
          <button className="rounded-md border border-line px-3 py-2 font-bold" type="button" onClick={onClose}>Cerrar</button>
        </div>
        <dl className="mt-4 grid gap-3 md:grid-cols-2">
          <DetailItem label="Estado" value={purchase.status} />
          <DetailItem label="Organismo" value={purchase.agency} />
          <DetailItem label="Proveedor" value={purchase.supplier} />
          <DetailItem label="Fecha adjudicación" value={dateLabel(purchase.award_date)} />
          <DetailItem label="Cierre" value={dateLabel(purchase.closing_date)} />
          <DetailItem label="Cantidad" value={purchase.quantity} />
          <DetailItem label="Precio unitario" value={money(purchase.unit_price, purchase.currency)} />
          <DetailItem label="Total adjudicado" value={money(purchase.awarded_amount, purchase.currency)} />
          <DetailItem label="Fuente" value={purchase.source} />
          <DetailItem label="Notas" value={purchase.notes || "Sin observaciones"} />
        </dl>
      </section>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line p-3">
      <dt className="text-xs font-black text-muted">{label}</dt>
      <dd className="mt-1 font-bold">{value}</dd>
    </div>
  );
}
