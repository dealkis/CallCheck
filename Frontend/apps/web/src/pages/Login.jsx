
import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function Login() {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');

  async function fazerLogin(e) {
    e.preventDefault();

    try {
      const resposta = await fetch(
        `${import.meta.env.VITE_API_URL}/api/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            senha,
          }),
        }
      );

      const dados = await resposta.json();

      if (!resposta.ok) {
        alert(dados.erro || dados.message || 'Não foi possível entrar.');
        return;
      }

      if (dados.token) {
        localStorage.setItem('callcheck_token', dados.token);
      }

      if (dados.usuario) {
        localStorage.setItem(
          'callcheck_usuario',
          JSON.stringify(dados.usuario)
        );
      }

      alert('Login realizado com sucesso!');
      window.location.href = '/';
    } catch (erro) {
      console.error(erro);
      alert('Erro ao conectar com o servidor.');
    }
  }

  return (
    <main className="login-container">
      <h1>Entrar no CallCheck</h1>
      <p>Acesse sua conta para continuar.</p>

      <form onSubmit={fazerLogin}>
        <label htmlFor="email">E-mail</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label htmlFor="senha">Senha</label>
        <input
          id="senha"
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
        />

        <button type="submit">Entrar</button>
      </form>

      <Link to="/">Voltar para a página inicial</Link>
    </main>
  );
}

export default Login;
