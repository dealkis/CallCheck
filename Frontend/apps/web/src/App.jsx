import React, { useCallback, useEffect, useState } from "react";
import CallCheckPage from "./CallCheckPage";
import Login from "./Login";
import AdminPanel from "./AdminPanel";

const API_URL = (import.meta.env.VITE_API_URL || "https://callcheck.onrender.com").replace(/\/$/, "");

export default function App() {
  const [usuario, setUsuario] = useState(() => {
    try { return JSON.parse(localStorage.getItem("callcheck_usuario") || "null"); }
    catch { return null; }
  });
  const [mostrarLogin, setMostrarLogin] = useState(false);
  const [pagina, setPagina] = useState("inicio");

  const sair = useCallback(async () => {
    const token = localStorage.getItem("callcheck_token");
    try {
      if (token) await fetch(`${API_URL}/api/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    } catch { /* a limpeza local continua mesmo se o servidor estiver indisponível */ }
    localStorage.removeItem("callcheck_token");
    localStorage.removeItem("callcheck_usuario");
    setUsuario(null);
    setPagina("inicio");
    setMostrarLogin(false);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("callcheck_token");
    if (!token) return;
    fetch(`${API_URL}/api/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async r => { if (!r.ok) throw new Error("Sessão expirada"); return r.json(); })
      .then(d => setUsuario(d.usuario))
      .catch(() => { localStorage.removeItem("callcheck_token"); localStorage.removeItem("callcheck_usuario"); setUsuario(null); });
  }, []);

  if (pagina === "admin") {
    if (usuario?.nivel !== "admin") return <div className="min-h-screen bg-[#080d18] p-8 text-white"><p>Acesso restrito a administradores.</p><button className="mt-4 rounded bg-green-600 px-4 py-2" onClick={() => setPagina("inicio")}>Voltar</button></div>;
    return <AdminPanel usuario={usuario} onLogout={sair} onVoltar={() => setPagina("inicio")} />;
  }

  return <>
    <div className="fixed right-4 top-4 z-50 flex items-center gap-2">
      {usuario ? <>
        <span className="hidden rounded-lg bg-black/50 px-3 py-2 text-sm text-white sm:inline">Olá, {usuario.nome}</span>
        {usuario.nivel === "admin" && <button onClick={() => setPagina("admin")} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow">Painel admin</button>}
        <button onClick={sair} className="rounded-lg border border-white/20 bg-black/50 px-4 py-2 text-sm text-white">Sair</button>
      </> : <button onClick={() => setMostrarLogin(true)} className="rounded-lg bg-green-500 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-green-600">Entrar</button>}
    </div>
    <CallCheckPage />
    {mostrarLogin && <Login onLogin={u => { setUsuario(u); setMostrarLogin(false); }} onClose={() => setMostrarLogin(false)} />}
  </>;
}
