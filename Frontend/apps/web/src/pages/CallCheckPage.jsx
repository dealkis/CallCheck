import React, { useState, useRef } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  XCircle, 
  Phone, 
  TrendingDown, 
  Shield, 
  Zap, 
  DollarSign, 
  Users, 
  Clock, 
  AlertTriangle, 
  Building2, 
  MessageSquareWarning, 
  Search,
  ShieldAlert // Ícone adicionado para o formulário de denúncia
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';

// Custom Ripple Button Component
const RippleButton = ({ children, className, onClick, ...props }) => {
  const [ripples, setRipples] = useState([]);
  const buttonRef = useRef(null);

  const handleClick = (e) => {
    const button = buttonRef.current;
    if (button) {
      const rect = button.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      const newRipple = { x, y, size, id: Date.now() };
      setRipples((prev) => [...prev, newRipple]);

      setTimeout(() => {
        setRipples((prev) => prev.filter((r) => r.id !== newRipple.id));
      }, 600);
    }
    if (onClick) onClick(e);
  };

  return (
    <Button
      ref={buttonRef}
      onClick={handleClick}
      className={`ripple-container relative overflow-hidden transition-all duration-300 ease-in-out hover:scale-105 active:scale-98 ${className}`}
      {...props}
    >
      {children}
      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          className="ripple-span"
          style={{
            left: ripple.x,
            top: ripple.y,
            width: ripple.size,
            height: ripple.size,
          }}
        />
      ))}
    </Button>
  );
};

function CallCheckPage() {
  const [phoneInput, setPhoneInput] = useState('');
  const [companyInput, setCompanyInput] = useState(''); 
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [mensagemBackend, setMensagemBackend] = useState(''); 
  const [dadosCompletos, setDadosCompletos] = useState(null); 
  
  const [currentPage, setCurrentPage] = useState(1);
  const [temProxima, setTemProxima] = useState(false);

  // === NOVOS ESTADOS: SISTEMA DE DENÚNCIA ===
  const [showDenunciaForm, setShowDenunciaForm] = useState(false);
  const [tipoDenuncia, setTipoDenuncia] = useState('');
  const [descricaoDenuncia, setDescricaoDenuncia] = useState('');
  const [isSubmittingDenuncia, setIsSubmittingDenuncia] = useState(false);
  const [denunciaSucesso, setDenunciaSucesso] = useState(false);

  const handleValidation = async (pageToFetch = 1) => {
    if (!phoneInput && !companyInput) return;
    
    setIsValidating(true);
    setValidationResult(null);
    setMensagemBackend(''); 
    setDadosCompletos(null); 

    // Limpa o formulário de denúncia a cada nova busca
    setShowDenunciaForm(false);
    setDenunciaSucesso(false);
    setTipoDenuncia('');
    setDescricaoDenuncia('');

    let telefoneLimpo = '';
    if (phoneInput) {
      telefoneLimpo = phoneInput.replace(/\D/g, '');

      if (telefoneLimpo.length === 8 || telefoneLimpo.length === 9) {
        telefoneLimpo = '5511' + telefoneLimpo; 
      } 
      else if (telefoneLimpo.length === 10 || telefoneLimpo.length === 11) {
        telefoneLimpo = '55' + telefoneLimpo; 
      }
    }

    try {
      const response = await fetch('https://callcheck.onrender.com/api/validar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          telefone: telefoneLimpo || null, 
          empresa: companyInput.trim() || null,
          pagina: pageToFetch
        }) 
      });

      const dados = await response.json();
      
      const dadosDoObjeto = dados.dados || dados;
      setDadosCompletos(dadosDoObjeto);

      const mensagemRetornada = dados.mensagem || dadosDoObjeto.mensagem || '';
      setMensagemBackend(mensagemRetornada);

      const statusRetornado = dados.status || dadosDoObjeto.status;

      setCurrentPage(dados.pagina_atual || dadosDoObjeto.pagina_atual || pageToFetch);
      setTemProxima(dados.tem_proxima || dadosDoObjeto.tem_proxima || false);

      if (statusRetornado === 'OFICIAL' || statusRetornado === 'ENCONTRADO' || statusRetornado === 'valid') {
        setValidationResult('valid');
      } else if (statusRetornado === 'RISCO' || statusRetornado === 'DENUNCIADO' || statusRetornado === 'risco') {
        setValidationResult('risco'); 
      } else {
        setValidationResult('invalid'); 
      }

    } catch (error) {
      console.error("Erro na comunicação com o backend:", error);
      setValidationResult('invalid');
      setMensagemBackend('Erro de conexão com o servidor. Verifique se o backend está rodando.');
    } finally {
      setIsValidating(false);
    }
  };

 // === FUNÇÃO CORRIGIDA NO JSX ===
const handleEnviarDenuncia = async () => {
  if (!tipoDenuncia) return;
  setIsSubmittingDenuncia(true);

  try {
    let telefoneLimpo = phoneInput ? phoneInput.replace(/\D/g, '') : '';
    
    const response = await fetch('https://callcheck.onrender.com/api/denuncias', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        telefone: telefoneLimpo, 
        empresa: companyInput,
        tipo: tipoDenuncia, // Envia GOLPE, SPAM, FALSO_ATENDIMENTO
        descricao: descricaoDenuncia
      })
    });

    // Buscamos a resposta do servidor (sucesso ou erro)
    const dadosResposta = await response.json();

    if (response.ok) {
      setDenunciaSucesso(true);
    } else {
      // AGORA SIM: Exibe a mensagem real que veio do Python/Postgres
      alert(dadosResposta.mensagem || "Não foi possível registrar a denúncia.");
    }
  } catch (error) {
    console.error("Erro ao enviar denúncia:", error);
    alert("Erro de conexão ao enviar a denúncia.");
  } finally {
    setIsSubmittingDenuncia(false);
  }
};
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleValidation(1);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value.replace(/[^\d\s()+-]/g, '');
    setPhoneInput(value);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.15 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    show: { 
      opacity: 1, 
      y: 0, 
      transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } 
    }
  };

  const resultVariants = {
    hidden: { scale: 0, rotate: -2, opacity: 0 },
    show: { 
      scale: 1, 
      rotate: 0, 
      opacity: 1,
      transition: { type: "spring", bounce: 0.5, duration: 0.4 }
    }
  };

  return (
    <>
      <Helmet>
        <title>CallCheck - Validação de canais corporativos</title>
        <meta name="description" content="Valide números telefônicos e empresas com precisão e elimine fraudes da sua base." />
      </Helmet>

      <div className="min-h-screen text-white selection:bg-[#22C55E]/30">
        {/* Hero Section */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 flex flex-col items-center justify-center min-h-[80vh]">
          <motion.div 
            className="max-w-4xl mx-auto text-center"
            variants={containerVariants}
            initial="hidden"
            animate="show"
          >
            <motion.h1 
              className="text-5xl md:text-6xl lg:text-7xl font-extrabold mb-6 text-[#22C55E]"
              style={{ letterSpacing: '-0.02em' }}
              variants={itemVariants}
            >
              CallCheck
            </motion.h1>
            
            <motion.p 
              className="text-xl md:text-2xl mb-10 text-gray-300 leading-relaxed max-w-2xl mx-auto font-medium"
              variants={itemVariants}
            >
              Valide números telefônicos ou empresas com precisão e elimine contatos falsos da sua base.
            </motion.p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <RippleButton 
                size="lg" 
                className="bg-[#22C55E] hover:bg-[#22C55E] text-white font-semibold px-8 py-6 text-lg rounded-xl hover:shadow-[0_0_20px_rgba(34,197,94,0.4)] border border-transparent"
                onClick={() => document.getElementById('test-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Testar agora
              </RippleButton>
              <RippleButton 
                size="lg" 
                className="bg-[#2563EB] hover:bg-[#2563EB] text-white font-semibold px-8 py-6 text-lg rounded-xl hover:shadow-[0_0_20px_rgba(37,99,235,0.4)] border border-transparent"
                onClick={() => document.getElementById('solution-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Ver demonstração
              </RippleButton>
            </div>
          </motion.div>
        </section>

        {/* Problems Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-white/5 bg-black/10">
          <motion.div 
            className="max-w-6xl mx-auto"
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                O Custo dos Dados Ruins
              </h2>
              <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                Manter números inválidos na sua base drena recursos e diminui a eficiência da sua equipe de vendas.
              </p>
            </div>
            
            <div className="flex flex-wrap justify-center gap-[20px]">
              {[
                { icon: AlertTriangle, title: 'Números inválidos', desc: 'Contatos que nunca existiram ou foram digitados incorretamente.' },
                { icon: TrendingDown, title: 'Leads falsos', desc: 'Desperdício de recursos em contatos que não convertem.' },
                { icon: Clock, title: 'Tempo perdido', desc: 'Horas gastas tentando contatar números inexistentes.' }
              ].map((item, i) => (
                <div 
                  key={i}
                  className="bg-[#111827] p-[20px] rounded-[12px] w-[250px] border border-white/5 transition-all duration-300 ease-in-out hover:scale-105 hover:-translate-y-[5px] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-[#EF4444]/30"
                >
                  <item.icon className="w-8 h-8 text-[#EF4444] mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Solution Section */}
        <section id="solution-section" className="py-20 px-4 sm:px-6 lg:px-8 border-t border-white/5">
          <motion.div 
            className="max-w-6xl mx-auto"
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Nossa Solução
              </h2>
              <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                Tecnologia avançada para garantir que cada número na sua lista seja uma oportunidade real.
              </p>
            </div>
            
            <div className="flex flex-wrap justify-center gap-[20px]">
              {[
                { icon: Zap, title: 'Validação em tempo real', desc: 'Verifique instantaneamente se o número está no formato correto.' },
                { icon: CheckCircle2, title: 'Identificação activa', desc: 'Confirme que o telefone possui a quantidade correta de dígitos.' },
                { icon: Shield, title: 'Detecção de spam', desc: 'Identifique números com formato suspeito ou incompleto.' }
              ].map((item, i) => (
                <div 
                  key={i}
                  className="bg-[#111827] p-[20px] rounded-[12px] w-[250px] border border-white/5 transition-all duration-300 ease-in-out hover:scale-105 hover:-translate-y-[5px] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-[#22C55E]/30"
                >
                  <item.icon className="w-8 h-8 text-[#22C55E] mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Test Section */}
        <section id="test-section" className="py-24 px-4 sm:px-6 lg:px-8 border-t border-white/5 bg-black/20">
          <motion.div 
            className="max-w-2xl mx-auto"
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <div className="text-center mb-10">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Painel de Consulta
              </h2>
              <p className="text-gray-400 text-lg">
                Pesquise por Telefone, Nome da Empresa ou use ambos os filtros.
              </p>
            </div>

            <div>
              <Card className="p-8 bg-[#111827] border-white/10 shadow-2xl">
                {/* Inputs empilhados verticalmente */}
                <div className="flex flex-col gap-4 mb-8">
                  <div className="relative">
                    <Input
                      type="tel"
                      placeholder="Pesquisar por Telefone (Ex: 11 4979-3300)"
                      value={phoneInput}
                      onChange={handleInputChange}
                      onKeyPress={handleKeyPress}
                      disabled={isValidating}
                      className="h-14 text-lg bg-black/40 border-white/10 text-white placeholder:text-gray-500 transition-all duration-300 ease-in-out focus:scale-[1.01] focus:ring-2 focus:ring-[#22C55E]/50 focus:border-[#22C55E] focus:shadow-[0_0_15px_rgba(34,197,94,0.3)] rounded-xl pl-12"
                    />
                    <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  </div>

                  <div className="relative">
                    <Input
                      type="text"
                      placeholder="Pesquisar por Nome da Empresa (Ex: Google Brasil)"
                      value={companyInput}
                      onChange={(e) => setCompanyInput(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={isValidating}
                      className="h-14 text-lg bg-black/40 border-white/10 text-white placeholder:text-gray-500 transition-all duration-300 ease-in-out focus:scale-[1.01] focus:ring-2 focus:ring-[#22C55E]/50 focus:border-[#22C55E] focus:shadow-[0_0_15px_rgba(34,197,94,0.3)] rounded-xl pl-12"
                    />
                    <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  </div>

                  <RippleButton 
                    onClick={() => handleValidation(1)}
                    disabled={isValidating || (!phoneInput && !companyInput)}
                    className="bg-[#22C55E] hover:bg-[#22C55E] text-white font-semibold h-14 rounded-xl hover:shadow-[0_0_20px_rgba(34,197,94,0.4)] disabled:opacity-50 disabled:hover:scale-100 disabled:hover:shadow-none mt-2 flex items-center justify-center text-lg w-full"
                  >
                    <Search className="w-5 h-5 mr-2" />
                    Pesquisar Registro
                  </RippleButton>
                </div>

                {/* Bloco de Resposta dos Resultados */}
                <div className="min-h-[80px] flex items-center justify-center rounded-xl bg-black/20 border border-white/5 p-4 overflow-hidden">
                  {isValidating ? (
                    <div className="flex items-center gap-3 text-[#2563EB] animate-custom-pulse">
                      <div className="w-5 h-5 rounded-full border-2 border-current border-t-transparent animate-spin" />
                      <span className="text-lg font-medium">⏳ Consultando base de dados...</span>
                    </div>
                  ) : validationResult === 'valid' ? (
                    <motion.div 
                      variants={resultVariants}
                      initial="hidden"
                      animate="show"
                      className="flex flex-col items-start gap-2 text-[#22C55E] w-full text-left p-2"
                    >
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-6 h-6 flex-shrink-0" />
                        <span className="text-lg font-bold">{mensagemBackend || "✅ Canal Oficial Identificado"}</span>
                      </div>
                      {dadosCompletos && (
                        <div className="mt-2 pl-9 w-full flex flex-col gap-3">
                          {(Array.isArray(dadosCompletos) ? dadosCompletos : [dadosCompletos]).map((item, index) => (
                            <div key={index} className="text-gray-300 space-y-1 text-base bg-white/5 p-3 rounded-lg w-full border border-[#22C55E]/20">
                              <div className="flex items-center gap-2 text-white font-medium">
                                <Building2 className="w-4 h-4 text-[#22C55E]" />
                                <span>Empresa: {item.empresa || item.nome_empresa || "Nome indisponível"}</span>
                              </div>
                              <div className="text-sm text-gray-400 flex items-center gap-1.5">
                                <Phone className="w-3.5 h-3.5 text-gray-500" />
                                <span>Telefone Vinculado: {item.telefone || phoneInput || "Não informado"}</span>
                              </div>
                            </div>
                          ))}

                          {/* Controles de Paginação Sempre Visíveis */}
                          <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-white/10 w-full">
                            <Button
                              onClick={() => handleValidation(currentPage - 1)}
                              disabled={isValidating || currentPage <= 1}
                              className="bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm py-1 px-4 h-9 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                              ⬅️ Anterior
                            </Button>
                            
                            <span className="text-gray-400 text-sm font-medium">
                              Página {currentPage}
                            </span>

                            <Button
                              onClick={() => handleValidation(currentPage + 1)}
                              disabled={isValidating || !temProxima}
                              className="bg-[#22C55E] hover:bg-[#1fba58] text-white text-sm py-1 px-4 h-9 rounded-lg shadow-md transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                              Próxima ➡️
                            </Button>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ) : validationResult === 'risco' ? (
                    <motion.div 
                      variants={resultVariants}
                      initial="hidden"
                      animate="show"
                      className="flex flex-col items-start gap-2 text-[#F59E0B] w-full text-left p-2"
                    >
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="w-6 h-6 flex-shrink-0" />
                        <span className="text-lg font-bold">{mensagemBackend || "⚠️ Atenção: Registros com Alertas"}</span>
                      </div>
                      {dadosCompletos && (
                        <div className="mt-2 pl-9 w-full flex flex-col gap-3">
                          {(Array.isArray(dadosCompletos) ? dadosCompletos : [dadosCompletos]).map((item, index) => (
                            <div key={index} className={`text-gray-300 space-y-1 text-base bg-white/5 p-3 rounded-lg w-full border ${item.denuncias ? 'border-[#F59E0B]/50' : 'border-[#22C55E]/20'}`}>
                              {(item.empresa || item.nome_empresa) && (
                                <div className="flex items-center gap-2 text-white font-medium">
                                  <Building2 className={`w-4 h-4 ${item.denuncias ? 'text-[#F59E0B]' : 'text-[#22C55E]'}`} />
                                  <span>Suposta Empresa: {item.empresa || item.nome_empresa}</span>
                                </div>
                              )}
                              <div className="text-sm text-gray-400 flex items-center gap-1.5 mt-1">
                                <Phone className="w-3.5 h-3.5 text-gray-500" />
                                <span>Telefone Vinculado: {item.telefone || phoneInput || "Não informado"}</span>
                              </div>
                              
                              {item.denuncias ? (
                                <div className="flex items-center gap-2 text-sm text-red-400 font-semibold bg-red-500/10 p-2 rounded border border-red-500/20 mt-2">
                                  <MessageSquareWarning className="w-4 h-4 flex-shrink-0" />
                                  <span>Status: {item.denuncias}</span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2 text-sm text-[#22C55E] font-medium mt-2">
                                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                  <span>Canal sem alertas</span>
                                </div>
                              )}
                            </div>
                          ))}

                          {/* Controles de Paginação (importante para buscas longas por nome que resultam em RISCO) */}
                          <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-white/10 w-full">
                            <Button
                              onClick={() => handleValidation(currentPage - 1)}
                              disabled={isValidating || currentPage <= 1}
                              className="bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm py-1 px-4 h-9 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                              ⬅️ Anterior
                            </Button>
                            
                            <span className="text-gray-400 text-sm font-medium">
                              Página {currentPage}
                            </span>

                            <Button
                              onClick={() => handleValidation(currentPage + 1)}
                              disabled={isValidating || !temProxima}
                              className="bg-[#22C55E] hover:bg-[#1fba58] text-white text-sm py-1 px-4 h-9 rounded-lg shadow-md transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                              Próxima ➡️
                            </Button>
                          </div>
                        </div>
                      )}
                      
                      {/* BLOCO DE DENÚNCIA PARA STATUS RISCO */}
                      <div className="mt-4 pl-9 w-full">
                        {!showDenunciaForm ? (
                          <Button 
                            onClick={() => setShowDenunciaForm(true)}
                            variant="outline"
                            className="bg-transparent hover:bg-white/5 text-gray-300 border-white/20 w-full md:w-auto h-10"
                          >
                            <ShieldAlert className="w-4 h-4 mr-2" /> Adicionar nova denúncia
                          </Button>
                        ) : denunciaSucesso ? (
                          <div className="bg-[#22C55E]/10 text-[#22C55E] border border-[#22C55E]/20 p-4 rounded-lg text-sm flex items-center gap-2">
                            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                            Denúncia registrada no banco com sucesso!
                          </div>
                        ) : (
                          <div className="bg-black/40 border border-white/10 p-5 rounded-xl flex flex-col gap-4">
                            <div className="flex items-center gap-2 text-white font-medium">
                              <ShieldAlert className="w-5 h-5 text-red-400" />
                              <span>Registrar Denúncia</span>
                            </div>
                            <select 
                              value={tipoDenuncia}
                              onChange={(e) => setTipoDenuncia(e.target.value)}
                              className="h-12 bg-[#111827] border border-white/10 text-white rounded-xl px-4 text-sm focus:ring-2 focus:ring-red-500/50 outline-none w-full appearance-none"
                            >
                              <option value="">Selecione o tipo...</option>
                              <option value="GOLPE">Golpe / Fraude</option>
                              <option value="SPAM">Spam / Assédio Comercial</option>
                              <option value="FALSO_ATENDIMENTO">Falso Atendimento</option>
                            </select>
                            <textarea 
                              value={descricaoDenuncia}
                              onChange={(e) => setDescricaoDenuncia(e.target.value)}
                              placeholder="Detalhes (opcional)..."
                              className="min-h-[100px] bg-[#111827] border border-white/10 text-white rounded-xl p-4 text-sm focus:ring-2 focus:ring-red-500/50 outline-none resize-y w-full"
                            />
                            <div className="flex gap-3 justify-end">
                              <Button variant="ghost" onClick={() => setShowDenunciaForm(false)} className="text-gray-400 hover:text-white">Cancelar</Button>
                              <RippleButton onClick={handleEnviarDenuncia} disabled={!tipoDenuncia || isSubmittingDenuncia} className="bg-red-600 hover:bg-red-700 text-white">
                                {isSubmittingDenuncia ? "Enviando..." : "Confirmar"}
                              </RippleButton>
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ) : validationResult === 'invalid' ? (
                    <motion.div 
                      variants={resultVariants}
                      initial="hidden"
                      animate="show"
                      className="flex flex-col items-start gap-2 text-[#EF4444] w-full text-left p-2"
                    >
                      <div className="flex items-center gap-3">
                        <XCircle className="w-6 h-6 flex-shrink-0" />
                        <span className="text-lg font-bold">{mensagemBackend || "❌ Não Encontrado / Fora dos Padrões"}</span>
                      </div>
                      <div className="mt-1 pl-9 text-sm text-gray-400">
                        O termo ou telefone pesquisado não consta nos registros oficiais cadastrados ou falhou na checagem.
                      </div>

                      {/* BLOCO DE DENÚNCIA PARA STATUS INVALID */}
                      <div className="mt-4 pl-9 w-full">
                        {!showDenunciaForm ? (
                          <Button 
                            onClick={() => setShowDenunciaForm(true)}
                            variant="outline"
                            className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border-red-500/20 w-full md:w-auto h-10"
                          >
                            <ShieldAlert className="w-4 h-4 mr-2" /> Relatar este número
                          </Button>
                        ) : denunciaSucesso ? (
                          <div className="bg-[#22C55E]/10 text-[#22C55E] border border-[#22C55E]/20 p-4 rounded-lg text-sm flex items-center gap-2">
                            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                            Denúncia registrada no banco com sucesso!
                          </div>
                        ) : (
                          <div className="bg-black/40 border border-white/10 p-5 rounded-xl flex flex-col gap-4">
                            <div className="flex items-center gap-2 text-white font-medium">
                              <ShieldAlert className="w-5 h-5 text-red-400" />
                              <span>Registrar Denúncia</span>
                            </div>
                            <select 
                              value={tipoDenuncia}
                              onChange={(e) => setTipoDenuncia(e.target.value)}
                              className="h-12 bg-[#111827] border border-white/10 text-white rounded-xl px-4 text-sm focus:ring-2 focus:ring-red-500/50 outline-none w-full appearance-none"
                            >
                              <option value="">Selecione o tipo de ocorrência...</option>
                              <option value="GOLPE">Golpe / Fraude</option>
                              <option value="SPAM">Spam / Assédio Comercial</option>
                              <option value="FALSO_ATENDIMENTO">Falso Atendimento</option>
                            </select>
                            <textarea 
                              value={descricaoDenuncia}
                              onChange={(e) => setDescricaoDenuncia(e.target.value)}
                              placeholder="Descreva brevemente o que aconteceu..."
                              className="min-h-[100px] bg-[#111827] border border-white/10 text-white rounded-xl p-4 text-sm focus:ring-2 focus:ring-red-500/50 outline-none resize-y w-full placeholder:text-gray-500"
                            />
                            <div className="flex gap-3 justify-end">
                              <Button variant="ghost" onClick={() => setShowDenunciaForm(false)} className="text-gray-400 hover:text-white hover:bg-white/5">Cancelar</Button>
                              <RippleButton onClick={handleEnviarDenuncia} disabled={!tipoDenuncia || isSubmittingDenuncia} className="bg-red-600 hover:bg-red-700 text-white font-semibold">
                                {isSubmittingDenuncia ? "Enviando..." : "Confirmar Denúncia"}
                              </RippleButton>
                            </div>
                          </div>
                        )}
                      </div>

                    </motion.div>
                  ) : (
                    <span className="text-gray-500 text-sm transition-opacity duration-300">O resultado da busca detalhada aparecerá aqui</span>
                  )}
                </div>
              </Card>
            </div>
          </motion.div>
        </section>

        {/* Benefits Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-white/5">
          <motion.div 
            className="max-w-6xl mx-auto"
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Benefícios Imediatos
              </h2>
              <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                Transforme sua operação de vendas com dados limpos e precisos.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { icon: DollarSign, title: 'Redução de custos', desc: 'Economize recursos eliminando contatos inválidos antes de investir tempo neles.' },
                { icon: Users, title: 'Mais contatos reais', desc: 'Foque apenas em números válidos e aumente sua taxa de conversão significativamente.' },
                { icon: Zap, title: 'Resultado instantâneo', desc: 'Validação em tempo real sem espera ou processamento demorado em lote.' }
              ].map((item, i) => (
                <div 
                  key={i}
                  className="text-center p-8 bg-[#111827] rounded-2xl border border-white/5 transition-all duration-300 ease-in-out hover:scale-105 hover:-translate-y-[5px] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-white/20"
                >
                  <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center bg-[#2563EB]/10 rounded-2xl text-[#2563EB]">
                    <item.icon className="w-8 h-8" />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
                  <p className="text-gray-400 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Final CTA Section */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 border-t border-white/5 bg-black/30">
          <motion.div 
            className="max-w-3xl mx-auto text-center"
            variants={containerVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-6" style={{ letterSpacing: '-0.02em' }}>
              Pronto para validar seus contatos?
            </h2>
            
            <p className="text-xl text-gray-300 mb-10 leading-relaxed">
              Comece agora e elimine números inválidos da sua base de forma definitiva.
            </p>

            <div>
              <RippleButton 
                size="lg" 
                className="bg-[#22C55E] hover:bg-[#22C55E] text-white font-semibold px-12 py-7 text-lg rounded-xl hover:shadow-[0_0_25px_rgba(34,197,94,0.5)]"
                onClick={() => document.getElementById('test-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Comece agora
              </RippleButton>
            </div>
          </motion.div>
        </section>

        {/* Footer */}
        <footer className="py-8 px-4 sm:px-6 lg:px-8 border-t border-white/10 bg-black/40">
          <div className="max-w-7xl mx-auto text-center">
            <p className="text-gray-500 text-sm">
              © 2026 CallCheck. Todos os direitos reservados.
            </p>
            <div className="mt-4 flex justify-center gap-6 text-sm">
              <span className="text-gray-500 cursor-pointer hover:text-gray-300 transition-colors duration-200">Política de Privacidade</span>
              <span className="text-gray-500 cursor-pointer hover:text-gray-300 transition-colors duration-200">Termos de Serviço</span>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

export default CallCheckPage;
