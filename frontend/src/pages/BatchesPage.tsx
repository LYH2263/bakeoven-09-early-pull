import { useEffect, useState } from "react";
import { api } from "../api/client";
type P = { id: number; name: string }; type O = { id: number; label: string };
type B = { id: number; code: string; product_name?: string; oven_label?: string; start_min: number; ferment_end?: number; bake_end?: number; actual_bake_end_min?: number | null; status: string };
function fmt(m: number) { const h = Math.floor(m/60), mm = m%60; return `${String(h).padStart(2,"0")}:${String(mm).padStart(2,"0")}`; }
export default function BatchesPage() {
  const [products, setProducts] = useState<P[]>([]);
  const [ovens, setOvens] = useState<O[]>([]);
  const [rows, setRows] = useState<B[]>([]);
  const [pid, setPid] = useState<number | "">(""); const [oid, setOid] = useState<number | "">("");
  const [start, setStart] = useState(11 * 60); const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const [outMin, setOutMin] = useState<Record<number, number | undefined>>({});
  const reload = () => api<B[]>("/batches").then(setRows);
  useEffect(() => {
    api<P[]>("/products").then(p => { setProducts(p); if (p[0]) setPid(p[0].id); });
    api<O[]>("/ovens").then(o => { setOvens(o); if (o[0]) setOid(o[0].id); });
    reload();
  }, []);
  async function create() {
    setMsg(""); setErr("");
    try {
      const b = await api<B>("/batches", { method: "POST", body: JSON.stringify({ product_id: pid, oven_id: oid, start_min: start }) });
      setMsg(`已排产 ${b.code}`);
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  async function registerOut(b: B) {
    setMsg(""); setErr("");
    const m = outMin[b.id];
    if (m === undefined || Number.isNaN(m)) { setErr("请先填写实际出炉分钟"); return; }
    try {
      const r = await api<B>(`/batches/${b.id}/actual-bake-end`, { method: "POST", body: JSON.stringify({ actual_bake_end_min: m }) });
      setMsg(`已登记 ${r.code} 实际出炉 ${fmt(r.actual_bake_end_min ?? m)}`);
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>批次</h2>
    <div className="toolbar">
      <select value={pid} onChange={e => setPid(Number(e.target.value))}>{products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
      <select value={oid} onChange={e => setOid(Number(e.target.value))}>{ovens.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}</select>
      <label>开工分钟 <input type="number" value={start} onChange={e => setStart(Number(e.target.value))} style={{ width: 90 }} /></label>
      <button onClick={create}>创建生产批次</button>
    </div>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>批次</th><th>产品</th><th>炉位</th><th>发酵</th><th>烘烤结束</th><th>实际出炉</th><th>状态</th><th>登记出炉</th></tr></thead>
    <tbody>{rows.map(b => <tr key={b.id}><td className="mono">{b.code}</td><td>{b.product_name}</td><td>{b.oven_label}</td>
      <td className="mono">{fmt(b.start_min)}–{fmt(b.ferment_end ?? b.start_min)}</td>
      <td className="mono">{fmt(b.bake_end ?? b.start_min)}</td>
      <td className="mono">{b.actual_bake_end_min != null ? fmt(b.actual_bake_end_min) : "—"}</td><td>{b.status}</td>
      <td><input type="number" style={{ width: 90 }} placeholder={`${b.ferment_end ?? 0}–${b.bake_end ?? 0}`}
        value={outMin[b.id] ?? ""} onChange={e => setOutMin({ ...outMin, [b.id]: e.target.value === "" ? undefined : Number(e.target.value) })} />
        <button onClick={() => registerOut(b)}>登记</button></td></tr>)}</tbody></table>
  </>);
}
