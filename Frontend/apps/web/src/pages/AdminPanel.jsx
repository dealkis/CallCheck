import React, { useCallback, useEffect, useState } from "react";

const API_URL = (import.meta.env.VITE_API_URL || "https://callcheck.onrender.com").replace(/\/$/, "");
const tabs = [
  { id: "denuncias", label: "Gerenciar denúncias" },
  { id: "banco", label: "Status do banco" },
  { id: "usuarios", label: "Permissões de usuários" },
];

export default function AdminPanel({ usuario, onLogout, onVoltar }) {
  const [aba, setAba] = useState("denuncias");
  const [telefone, setTelefone] = useState("");
  const [denuncias, setDenuncias] = useState([]);
  const [statusDb, setStatusDb] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");
  const [busy, setBusy] = useState(false);

  const token = localStorage.getItem("callcheck_token");
  const request = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401 || response.status === 403) {
      if (response.status === 401) onLogout();
      throw new Error(data.mensagem || "Você não tem permissão para executar esta ação.");
    }
    if (!response.ok) throw new Error(data.mensagem || "Falha na requisição.");
    return data;
  }, [token, onLogout]);

  const carregarDenuncias = useCallback(async (tel = "") => {
    setErro(""); setMensagem(""); setBusy(true);
    try {
      const query = tel ? `?telefone=${encodeURIComponent(tel)}` : "";
      const data = await request(`/api/admin/denuncias${query}`);
      setDenuncias(data.denuncias || []);
      if (!(data.denuncias || []).length) setMensagem("Nenhuma denúncia encontrada.");
    } catch (e) { setErro(e.message); setDenuncias([]); }
    finally { setBusy(false); }
  }, [request]);

  const carregarStatus = useCallback(async () => {
    setErro(""); setBusy(true);
    try { setStatusDb(await request("/api/admin/status-db")); }
    catch (e) { setStatusDb({ conectado: false, mensagem: e.message }); }
    finally { setBusy(false); }
  }, [request]);

  const carregarUsuarios = useCallback(async () => {
    setErro(""); setBusy(true);
    try { const data = await request("/api/admin/usuarios"); setUsuarios(data.usuarios || []); }
    catch (e) { setErro(e.message); }
    finally { setBusy(false); }
  }, [request]);

  useEffect(() => {
    if (aba === "denuncias") carregarDenuncias();
    if (aba === "banco") carregarStatus();
    if (aba === "usuarios") carregarUsuarios();
  }, [aba, carregarDenuncias, carregarStatus, carregarUsuarios]);

  async function apagarPorTelefone() {
    if (!telefone.trim()) { setErro("Digite um número de telefone."); return; }
    if (!window.confirm(`Confirma apagar TODAS as denúncias vinculadas ao número ${telefone}? Esta ação não pode ser desfeita.`)) return;
    setErro(""); setMensagem(""); setBusy(true);
    try {
      const data = await request(`/api/admin/denuncias?telefone=${encodeURIComponent(telefone)}`, { method: "DELETE" });
      setMensagem(data.mensagem || "Denúncias removidas.");
      setDenuncias(prev => prev.filter(d => String(d.telefone).replace(/\D/g, "") !== telefone.replace(/\D/g, "")));
      await carregarDenuncias(telefone);
    } catch (e) { setErro(e.message); }
    finally { setBusy(false); }
  }

  async function apagarUma(id) {
    if (!window.confirm(`Confirma remover a denúncia #${id}?`)) return;
    setErro(""); setMensagem(""); setBusy(true);
    try {
      const data = await request(`/api/admin/denuncias/${id}`, { method: "DELETE" });
      setMensagem(data.mensagem || "Denúncia removida.");
      await carregarDenuncias(telefone);
    } catch (e) { setErro(e.message); }
    finally { setBusy(false); }
  }

  async function mudarPermissao(u) {
    const admin = u.nivel !== "admin";
    if (!window.confirm(`Confirma ${admin ? "promover" : "remover os privilégios de administrador de"} ${u.nome}?`)) return;
    setErro(""); setMensagem(""); setBusy(true);
    try {
      const data = await request("/api/admin/usuarios/permissoes", {
        method: "PUT", body: JSON.stringify({ usuario_id: u.id, admin }),
      });
      setMensagem(data.mensagem || "Permissão atualizada.");
      await carregarUsuarios();
    } catch (e) { setErro(e.message); }
    finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen bg-[#080d18] px-4 py-8 text-white sm:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm font-semibold uppercase tracking-widest text-green-400">CallCheck</p><h1 className="mt-1 text-3xl font-bold">Painel administrativo</h1><p className="mt-2 text-sm text-gray-400">Olá, {usuario?.nome || "administrador"}.</p></div>
          <div className="flex gap-2"><button onClick={onVoltar} className="rounded-lg border border-white/15 px-4 py-2 hover:bg-white/5">Página inicial</button><button onClick={onLogout} className="rounded-lg bg-red-600 px-4 py-2 hover:bg-red-700">Sair</button></div>
        </header>
        <nav className="mb-6 flex flex-wrap gap-2" aria-label="Seções administrativas">
          {tabs.map(t => <button key={t.id} onClick={() => { setAba(t.id); setErro(""); setMensagem(""); }} className={`rounded-lg px-4 py-3 text-sm font-medium ${aba === t.id ? "bg-green-500 text-white" : "border border-white/10 bg-white/5 text-gray-300 hover:bg-white/10"}`}>{t.label}</button>)}
        </nav>
        {erro && <div role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-red-200">{erro}</div>}
        {mensagem && <div role="status" className="mb-4 rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-green-200">{mensagem}</div>}

        {aba === "denuncias" && <section className="rounded-2xl border border-white/10 bg-[#111827] p-5 sm:p-7">
          <h2 className="mb-2 text-xl font-semibold">Gerenciar denúncias</h2><p className="mb-5 text-sm text-gray-400">Busque por telefone para revisar registros ou remover denúncias incorretas.</p>
          <form className="mb-6 flex flex-col gap-3 sm:flex-row" onSubmit={e => { e.preventDefault(); carregarDenuncias(telefone); }}>
            <input value={telefone} onChange={e => setTelefone(e.target.value)} placeholder="Telefone (ex.: 11 4979-3300)" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 p-3" />
            <button disabled={busy} className="rounded-lg bg-blue-600 px-5 py-3 font-semibold hover:bg-blue-700 disabled:opacity-50">Buscar</button>
            <button type="button" disabled={busy || !telefone.trim()} onClick={apagarPorTelefone} className="rounded-lg bg-red-600 px-5 py-3 font-semibold hover:bg-red-700 disabled:opacity-50">Apagar todas do número</button>
          </form>
          <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="text-gray-400"><tr><th className="p-3">ID</th><th className="p-3">Telefone</th><th className="p-3">Tipo / motivo</th><th className="p-3">Empresa</th><th className="p-3">Ação</th></tr></thead>
          <tbody>{denuncias.map(d => <tr key={d.id} className="border-t border-white/10"><td className="p-3">#{d.id}</td><td className="p-3">{d.telefone}</td><td className="p-3">{d.tipo}{d.descricao ? ` — ${d.descricao}` : ""}</td><td className="p-3">{d.empresa || "—"}</td><td className="p-3"><button disabled={busy} onClick={() => apagarUma(d.id)} className="rounded-md border border-red-500/40 px-3 py-1.5 text-red-300 hover:bg-red-500/10">Remover</button></td></tr>)}</tbody></table></div>
          {!denuncias.length && <p className="py-8 text-center text-gray-500">{busy ? "Carregando..." : "Nenhuma denúncia para exibir."}</p>}
        </section>}

        {aba === "banco" && <section className="rounded-2xl border border-white/10 bg-[#111827] p-6 sm:p-8">
          <h2 className="mb-4 text-xl font-semibold">Status do banco de dados</h2>
          <div className="mb-5 flex items-center gap-3"><span className={`h-3 w-3 rounded-full ${statusDb?.conectado ? "bg-green-400" : "bg-red-400"}`} /><span className="font-medium">{statusDb?.conectado ? "Conectado" : statusDb ? "Indisponível" : "Aguardando teste"}</span></div>
          <p className="mb-5 text-gray-300">{busy ? "Testando conexão..." : statusDb?.mensagem || "Execute o teste para consultar o NeonDB."}</p>
          <button onClick={carregarStatus} disabled={busy} className="rounded-lg bg-blue-600 px-5 py-3 font-semibold hover:bg-blue-700 disabled:opacity-50">Testar novamente</button>
        </section>}

        {aba === "usuarios" && <section className="rounded-2xl border border-white/10 bg-[#111827] p-5 sm:p-7">
          <h2 className="mb-2 text-xl font-semibold">Permissões de usuários</h2><p className="mb-5 text-sm text-gray-400">Promova usuários a administrador ou remova seus privilégios. O servidor valida as permissões em cada requisição.</p>
          <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="text-gray-400"><tr><th className="p-3">Nome</th><th className="p-3">E-mail</th><th className="p-3">Nível</th><th className="p-3">Status</th><th className="p-3">Ação</th></tr></thead><tbody>
          {usuarios.map(u => <tr key={u.id} className="border-t border-white/10"><td className="p-3">{u.nome}</td><td className="p-3">{u.email}</td><td className="p-3"><span className={`rounded-full px-2 py-1 ${u.nivel === "admin" ? "bg-green-500/15 text-green-300" : "bg-white/10 text-gray-300"}`}>{u.nivel}</span></td><td className="p-3">{u.status}</td><td className="p-3"><button disabled={busy || (u.id === usuario?.id && u.nivel === "admin")} onClick={() => mudarPermissao(u)} className="rounded-md border border-white/15 px-3 py-1.5 hover:bg-white/10 disabled:opacity-40">{u.nivel === "admin" ? "Remover admin" : "Promover a admin"}</button></td></tr>)}
          </tbody></table></div>{!usuarios.length && <p className="py-8 text-center text-gray-500">{busy ? "Carregando..." : "Nenhum usuário encontrado."}</p>}
        </section>}
      </div>
    </main>
  );
}
