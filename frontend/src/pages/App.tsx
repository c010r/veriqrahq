import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Activity, Building2, CheckCircle2, Clock3, Database, Download, Search, SlidersHorizontal, WalletCards, X } from "lucide-react";
import { Catalogs, Filters, Purchase, PurchaseResponse, fetchCatalogs, fetchPurchases } from "../lib/api";

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
  const [status, setStatus] = useState("Consulta de compras estatales por organismo.");
  const [loading, setLoading] = useState(false);
  const didInitialLoad = useRef(false);
  const selectedAgency = filters.agency === "all" ? "Todos los organismos" : filters.agency;

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
    <main id="content" className="workspace-shell min-h-screen text-ink" tabIndex={-1}>
      <header className="border-b border-[#d9e1dc] bg-white/90 backdrop-blur">
        <div className="mx-auto grid max-w-[1500px] gap-5 px-4 py-5 lg:grid-cols-[1fr_auto] lg:items-end lg:px-10">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-sm font-black text-[#0f766e]">
              <Database size={17} /> VeriqraHQ
              <span className="rounded-full bg-[#eef3ef] px-2 py-1 text-xs text-[#5b6b61]">ARCE en tiempo operativo</span>
            </div>
            <h1 className="mt-2 max-w-4xl text-3xl font-black tracking-normal text-[#111827] md:text-5xl">Compras estatales por organismo</h1>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-muted" role="status" aria-live="polite">{status}</p>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <button className="inline-flex min-h-11 items-center gap-2 rounded-md border border-[#c8d3cc] bg-white px-4 py-2 font-black text-[#334155] transition hover:bg-[#f8faf8]" type="button" onClick={exportCsv}>
              <Download size={18} /> Exportar
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 lg:px-10">
        <section className="grid gap-3 lg:grid-cols-[1.2fr_repeat(4,1fr)]" aria-label="Resumen">
          <AgencyPanel agency={selectedAgency} total={data.total} />
          <Metric label="Vigentes" value={data.active} icon={<Activity size={19} />} tone="teal" />
          <Metric label="Pasadas" value={data.previous} icon={<Clock3 size={19} />} tone="slate" />
          <Metric label="Adjudicado UYU" value={money(data.awarded_total_uyu)} icon={<WalletCards size={19} />} tone="amber" />
          <Metric label="Promedio UYU" value={money(data.awarded_average_uyu)} icon={<CheckCircle2 size={19} />} tone="indigo" />
        </section>

        <section className="sticky top-0 z-[3] rounded-lg border border-[#d6dfd9] bg-white/95 p-4 shadow-sm backdrop-blur" aria-labelledby="filters-title">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="inline-flex items-center gap-2 text-sm font-black text-[#0f766e]"><SlidersHorizontal size={17} /> Panel de consulta</p>
              <h2 id="filters-title" className="text-xl font-black text-[#111827]">Filtrar y comparar</h2>
            </div>
            <button className="hidden rounded-md border border-[#c8d3cc] px-3 py-2 text-sm font-black text-muted transition hover:bg-[#f8faf8] md:inline-flex" type="button" onClick={() => setFilters(defaultFilters)}>
              <X size={16} /> Limpiar
            </button>
          </div>
          <div className="grid gap-3 lg:grid-cols-[1.35fr_repeat(3,1fr)]">
            <label className="grid gap-1 text-sm font-black text-muted" htmlFor="query">
              Buscar
              <span className="relative">
                <Search className="pointer-events-none absolute left-3 top-3 text-muted" size={18} />
                <input id="query" name="query" className="min-h-11 w-full rounded-md border border-[#c8d3cc] bg-white pl-10 pr-3 text-ink shadow-inner shadow-black/[0.02]" type="search" value={filters.query} onChange={(event) => updateFilter("query", event.target.value)} placeholder="Objeto, proveedor, expediente" />
              </span>
            </label>
            <Select label="Estado" value={filters.status} onChange={(value) => updateFilter("status", value)} options={["all", ...catalogs.statuses]} />
            <Select label="Organismo" value={filters.agency} onChange={(value) => updateFilter("agency", value)} options={["all", ...catalogs.agencies]} />
            <Select label="Procedimiento" value={filters.procedure_type} onChange={(value) => updateFilter("procedure_type", value)} options={["all", ...catalogs.procedure_types]} />
          </div>
        </section>

        <section className="overflow-hidden rounded-lg border border-[#d6dfd9] bg-white shadow-sm" aria-labelledby="results-title">
          <div className="flex flex-col gap-2 border-b border-[#d6dfd9] bg-[#fbfcfb] p-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 id="results-title" className="text-xl font-black text-[#111827]">Resultados</h2>
              <p className="text-sm font-medium text-muted" aria-live="polite">{loading ? "Cargando..." : `${data.total} compras encontradas${filters.agency === "all" ? "" : ` para ${filters.agency}`}`}</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-black text-muted">
              <span className="rounded-full border border-[#d6dfd9] bg-white px-3 py-1">Estado: {filters.status === "all" ? "Todos" : filters.status}</span>
              <span className="rounded-full border border-[#d6dfd9] bg-white px-3 py-1">Procedimiento: {filters.procedure_type === "all" ? "Todos" : filters.procedure_type}</span>
            </div>
          </div>
          <div className="max-h-[68dvh] overflow-auto">
            <table className="min-w-[1160px] w-full border-collapse text-left">
              <caption className="sr-only">Compras estatales filtradas por organismo, estado y procedimiento</caption>
              <thead className="sticky top-0 z-[2] bg-[#eef3ef] text-sm shadow-[0_1px_0_#cbd8ce]">
                <tr>
                  <th scope="col" className="p-3">Estado</th>
                  <th scope="col" className="p-3">Expediente</th>
                  <th scope="col" className="p-3">Objeto</th>
                  <th scope="col" className="p-3">Organismo</th>
                  <th scope="col" className="p-3">Proveedor</th>
                  <th scope="col" className="p-3">Fechas</th>
                  <th scope="col" className="p-3 text-right">Adjudicación</th>
                  <th scope="col" className="p-3">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e3eae5]">
                {rows.map((purchase) => (
                  <tr className="align-top transition hover:bg-[#f8faf8]" key={purchase.id}>
                    <td className="p-3"><Badge status={purchase.status} /></td>
                    <th scope="row" className="p-3 font-black text-[#111827]">{purchase.external_id}<span className="block text-sm font-semibold text-muted">{purchase.procedure_type}</span></th>
                    <td className="max-w-xl p-3 font-bold leading-6 text-[#1f2937]">{purchase.object}</td>
                    <td className="p-3 text-sm font-semibold text-[#334155]">{purchase.agency}</td>
                    <td className="p-3 text-sm text-[#334155]">{purchase.supplier}</td>
                    <td className="p-3 text-sm font-semibold text-[#334155]">{dateLabel(purchase.award_date)}<span className="block text-muted">Cierre: {dateLabel(purchase.closing_date)}</span></td>
                    <td className="p-3 text-right font-black text-[#111827]">{money(purchase.awarded_amount, purchase.currency)}<span className="block text-sm font-semibold text-muted">Unitario: {money(purchase.unit_price, purchase.currency)}</span></td>
                    <td className="p-3"><button className="rounded-md border border-[#0f766e] px-3 py-2 font-black text-[#0f766e] transition hover:bg-[#f1faf8]" type="button" onClick={() => setSelected(purchase)}>Ver</button></td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td className="h-40 p-3 text-center text-muted" colSpan={8}>No hay compras para los filtros seleccionados.</td>
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

function AgencyPanel({ agency, total }: { agency: string; total: number }) {
  return (
    <article className="rounded-lg border border-[#17211b] bg-[#17211b] p-4 text-white shadow-sm">
      <span className="inline-flex items-center gap-2 text-sm font-black text-[#a7f3d0]"><Building2 size={18} /> Organismo activo</span>
      <strong className="mt-2 block line-clamp-2 text-xl font-black leading-tight">{agency}</strong>
      <div className="mt-4 text-sm">
        <span className="font-bold text-[#dbe7df]">{total} registros visibles</span>
      </div>
    </article>
  );
}

function Metric({ label, value, icon, tone }: { label: string; value: string | number; icon: ReactNode; tone: "teal" | "slate" | "amber" | "indigo" }) {
  const tones = {
    teal: "bg-[#e7f7f4] text-[#0f766e]",
    slate: "bg-[#eef2f7] text-[#475569]",
    amber: "bg-[#fff7e6] text-[#b45309]",
    indigo: "bg-[#eef2ff] text-[#4f46e5]"
  };
  return (
    <article className="rounded-lg border border-[#d6dfd9] bg-white p-4 shadow-sm">
      <span className={`inline-flex rounded-md p-2 ${tones[tone]}`}>{icon}</span>
      <span className="mt-3 block text-sm font-black text-muted">{label}</span>
      <strong className="mt-1 block text-2xl font-black text-[#111827]">{value}</strong>
    </article>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-sm font-black text-muted">
      {label}
      <select className="min-h-11 rounded-md border border-[#c8d3cc] bg-white px-3 text-ink shadow-inner shadow-black/[0.02]" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>{option === "all" ? "Todos" : option}</option>
        ))}
      </select>
    </label>
  );
}

function Badge({ status }: { status: string }) {
  const active = status === "vigente";
  return <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-black ring-1 ${active ? "bg-[#e6fffb] text-[#0f766e] ring-[#99f6e4]" : "bg-[#f1f5f9] text-[#475569] ring-[#cbd5e1]"}`}>{active ? <Activity size={12} /> : <Clock3 size={12} />}{status}</span>;
}

function Detail({ purchase, onClose }: { purchase: Purchase; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-10 grid place-items-center bg-[#0f1712]/60 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="detail-title">
      <section className="max-h-[90dvh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#d6dfd9] pb-4">
          <div>
            <Badge status={purchase.status} />
            <h2 id="detail-title" className="mt-3 text-2xl font-black text-[#111827]">{purchase.object}</h2>
            <p className="mt-1 text-sm font-semibold text-muted">{purchase.external_id} · {purchase.procedure_type}</p>
          </div>
          <button className="rounded-md border border-[#c8d3cc] px-3 py-2 font-black text-[#334155] transition hover:bg-[#f8faf8]" type="button" onClick={onClose}>Cerrar</button>
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
    <div className="rounded-md border border-[#d6dfd9] bg-[#fbfcfb] p-3">
      <dt className="text-xs font-black uppercase text-muted">{label}</dt>
      <dd className="mt-1 [overflow-wrap:anywhere] font-bold text-[#1f2937]">{value}</dd>
    </div>
  );
}
