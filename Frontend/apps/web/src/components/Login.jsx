import React, { useState } from "react";

const API_URL = (import.meta.env.VITE_API_URL || "https://callcheck.onrender.com").replace(/\/$/, "");

export default function Login({ onLogin, onClose }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.mensagem || "Não foi possível entrar.");
      // O backend retorna apenas o token em texto claro; o banco guarda seu hash.
      localStorage.setItem("callcheck_token", data.token);
      localStorage.setItem("callcheck_usuario", JSON.stringify(data.usuario));
      onLogin(data.usuario);
    } catch (err) {
      setErro(err.message || "Erro de conexão com o servidor.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal="true" aria-labelledby="login-title">
      <form onSubmit={enviar} className="w-full max-w-md rounded-2xl border border-white/10 bg-[#111827] p-7 text-white shadow-2xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 id="login-title" className="text-2xl font-bold">Entrar no CallCheck</h2>
            <p className="mt-1 text-sm text-gray-400">Acesse sua área de usuário.</p>
          </div>
          {onClose && <button type="button" onClick={onClose} className="text-gray-400 hover:text-white" aria-label="Fechar">✕</button>}
        </div>
        <label className="mb-1 block text-sm text-gray-300" htmlFor="login-email">E-mail</label>
        <input id="login-email" type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} className="mb-4 w-full rounded-lg border border-white/10 bg-black/30 p-3 outline-none focus:border-green-500" />
        <label className="mb-1 block text-sm text-gray-300" htmlFor="login-senha">Senha</label>
        <input id="login-senha" type="password" autoComplete="current-password" required value={senha} onChange={e => setSenha(e.target.value)} className="mb-4 w-full rounded-lg border border-white/10 bg-black/30 p-3 outline-none focus:border-green-500" />
        {erro && <p role="alert" className="mb-4 rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
        <button disabled={carregando} className="w-full rounded-lg bg-green-500 px-4 py-3 font-semibold text-white hover:bg-green-600 disabled:opacity-60">{carregando ? "Entrando..." : "Entrar"}</button>
        <p className="mt-4 text-xs text-gray-500">A senha é validada no servidor; nunca envie nem armazene a senha no navegador.</p>
      </form>
    </div>
  );
}
