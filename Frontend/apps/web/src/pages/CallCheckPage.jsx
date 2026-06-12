import React, { useState, useRef } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, Phone, TrendingDown, Shield, Zap, DollarSign, Users, Clock, AlertTriangle, Building2, MessageSquareWarning } from 'lucide-react';
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
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [mensagemBackend, setMensagemBackend] = useState(''); 
  const [dadosCompletos, setDadosCompletos] = useState(null); // <-- Novo estado para guardar o objeto completo do Python (empresa, telefone, denuncias, etc.)

  const handleValidation = async () => {
    if (!phoneInput) return;
    
    setIsValidating(true);
    setValidationResult(null);
    setMensagemBackend(''); 
    setDadosCompletos(null); // Limpa os dados anteriores

    try {
      // Chama a sua API Flask hospedada no Render
      const response = await fetch('https://callcheck.onrender.com/api/validar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        // Envia o telefone para o Python
        body: JSON.stringify({ telefone: phoneInput }) 
      });

      const dados = await response.json();
      
      // Guarda o objeto de dados que veio de dentro da resposta do Python
      // Se o seu python retorna tudo no objeto principal ou dentro de dados.dados, pegamos aqui:
      const dadosDoObjeto = dados.dados || dados;
      setDadosCompletos(dadosDoObjeto);

      const mensagemRetornada = dados.mensagem || dadosDoObjeto.mensagem || '';
      setMensagemBackend(mensagemRetornada);

      // Define a cor/ícone baseado no status que o seu Python retornou
      const statusRetornado = dados.status || dadosDoObjeto.status;

      if (statusRetornado === 'OFICIAL' || statusRetornado === 'ENCONTRADO' || statusRetornado === 'valid') {
        setValidationResult('valid');
      } else if (statusRetornado === 'RISCO' || statusRetornado === 'DENUNCIADO') {
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

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleValidation();
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value.replace(/[^\d\s()-]/g, '');
    setPhoneInput(value);
  };

  // Framer Motion Variants
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
        <title>CallCheck - Validação de números telefônicos</title>
        <meta name="description" content="Valide números telefônicos com precisão e elimine contatos inválidos da sua base de dados" />
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
              Valide números telefônicos com precisão e elimine contatos inválidos da sua base.
            </motion.p>

            <motion.div 
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
              variants={itemVariants}
            >
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
            </motion.div>
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
              <motion.h2 variants={itemVariants} className="text-3xl md:text-4xl font-bold mb-4">
                O Custo dos Dados Ruins
              </motion.h2>
              <motion.p variants={itemVariants} className="text-gray-400 text-lg max-w-2xl mx-auto">
                Manter números inválidos na sua base drena recursos e diminui a eficiência da sua equipe de vendas.
              </motion.p>
            </div>
            
            <div className="flex flex-wrap justify-center gap-[20px]">
              {[
                { icon: AlertTriangle, title: 'Números inválidos', desc: 'Contatos que nunca existiram ou foram digitados incorretamente.' },
                { icon: TrendingDown, title: 'Leads falsos', desc: 'Desperdício de recursos em contatos que não convertem.' },
                { icon: Clock, title: 'Tempo perdido', desc: 'Horas gastas tentando contatar números inexistentes.' }
              ].map((item, i) => (
                <motion.div 
                  key={i}
                  variants={itemVariants}
                  className="bg-[#111827] p-[20px] rounded-[12px] w-[250px] border border-white/5 transition-all duration-300 ease-in-out hover:scale-105 hover:-translate-y-[5px] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-[#EF4444]/30"
                >
                  <item.icon className="w-8 h-8 text-[#EF4444] mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{item.desc}</p>
                </motion.div>
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
              <motion.h2 variants={itemVariants} className="text-3xl md:text-4xl font-bold mb-4">
                Nossa Solução
              </motion.h2>
              <motion.p variants={itemVariants} className="text-gray-400 text-lg max-w-2xl mx-auto">
                Tecnologia avançada para garantir que cada número na sua lista seja uma oportunidade real.
              </motion.p>
            </div>
            
            <div className="flex flex-wrap justify-center gap-[20px]">
              {[
                { icon: Zap, title: 'Validação em tempo real', desc: 'Verifique instantaneamente se o número está no formato correto.' },
                { icon: CheckCircle2, title: 'Identificação ativa', desc: 'Confirme que o telefone possui a quantidade correta de dígitos.' },
                { icon: Shield, title: 'Detecção de spam', desc: 'Identifique números com formato suspeito ou incompleto.' }
              ].map((item, i) => (
                <motion.div 
                  key={i}
                  variants={itemVariants}
                  className="bg-[#111827] p-[20px] rounded-[12px] w-[250px] border border-white/5 transition-all duration-300 ease-in-out hover:scale-105 hover:-translate-y-[5px] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-[#22C55E]/30"
                >
                  <item.icon className="w-8 h-8 text-[#22C55E] mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{item.desc}</p>
                </motion.div>
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
              <motion.h2 variants={itemVariants} className="text-3xl md:text-4xl font-bold mb-4">
                Teste a Validação
              </motion.h2>
              <motion.p variants={itemVariants} className="text-gray-400 text-lg">
                Digite um número de telefone abaixo para ver o sistema em ação.
              </motion.p>
            </div>

            <motion.div variants={itemVariants}>
              <Card className="p-8 bg-[#111827] border-white/10 shadow-2xl">
                <div className="flex flex-col sm:flex-row gap-4 mb-8">
                  <div className="flex-1">
                    <Input
                      type="tel"
                      placeholder="Ex: 11987654321"
                      value={phoneInput}
                      onChange={handleInputChange}
                      onKeyPress={handleKeyPress}
                      disabled={isValidating}
                      className="h-14 text-lg bg-black/40 border-white/10 text-white placeholder:text-gray-500 transition-all duration-300 ease-in-out focus:scale-[1.02] focus:ring-2 focus:ring-[#22C55E]/50 focus:border-[#22C55E] focus:shadow-[0_0_15px_rgba(34,197,94,0.3)] rounded-xl"
                    />
                  </div>
                  <RippleButton 
                    onClick={handleValidation}
                    disabled={isValidating || !phoneInput}
                    className="bg-[#22C55E] hover:bg-[#22C55E] text-white font-semibold h-14 px-8 rounded-xl hover:shadow-[0_0_20px_rgba(34,197,94,0.4)] disabled:opacity-50 disabled:hover:scale-100 disabled:hover:shadow-none"
                  >
                    <Phone className="w-5 h-5 mr-2" />
                    Validar
                  </RippleButton>
                </div>

                <div className="min-h-[80px] flex items-center justify-center rounded-xl bg-black/20 border border-white/5 p-4 overflow-hidden">
                  {isValidating ? (
                    <div className="flex items-center gap-3 text-[#2563EB] animate-custom-pulse">
                      <div className="w-5 h-5 rounded-full border-2 border-current border-t-transparent animate-spin" />
                      <span className="text-lg font-medium">⏳ Validando...</span>
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
                        <span className="text-lg font-bold">{mensagemBackend || "✅ Número Oficial Encontrado"}</span>
                      </div>
                      {/* Exibe os dados extras retornados pelo Python se existirem */}
                      {dadosCompletos && (dadosCompletos.empresa || dadosCompletos.nome_empresa) && (
                        <div className="mt-2 pl-9 text-gray-300 space-y-1 text-base bg-white/5 p-3 rounded-lg w-full border border-[#22C55E]/20">
                          <div className="flex items-center gap-2 text-white font-medium">
                            <Building2 className="w-4 h-4 text-[#22C55E]" />
                            <span>Empresa: {dadosCompletos.empresa || dadosCompletos.nome_empresa}</span>
                          </div>
                          <div className="text-sm text-gray-400">
                            Telefone Oficial: {dadosCompletos.telefone || phoneInput}
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
                        <span className="text-lg font-bold">{mensagemBackend || "⚠️ Atenção: Número com Alertas"}</span>
                      </div>
                      {dadosCompletos && (
                        <div className="mt-2 pl-9 text-gray-300 space-y-1 text-base bg-white/5 p-3 rounded-lg w-full border border-[#F59E0B]/20">
                          {dadosCompletos.empresa && (
                            <div className="flex items-center gap-2 text-white font-medium">
                              <Building2 className="w-4 h-4 text-[#F59E0B]" />
                              <span>Suposta Empresa: {dadosCompletos.empresa}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-2 text-sm text-red-400 font-semibold bg-red-500/10 p-2 rounded border border-red-500/20 mt-1">
                            <MessageSquareWarning className="w-4 h-4" />
                            <span>Status: {dadosCompletos.denuncias || "Este número possui registros de atividade suspeita ou denúncias."}</span>
                          </div>
                        </div>
                      )}
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
                        <span className="text-lg font-bold">{mensagemBackend || "❌ Número Não Oficial / Inválido"}</span>
                      </div>
                      <div className="mt-1 pl-9 text-sm text-gray-400">
                        Este número não está cadastrado em canais oficiais conhecidos ou falhou nos critérios de validação.
                      </div>
                    </motion.div>
                  ) : (
                    <span className="text-gray-500 text-sm transition-opacity duration-300">O resultado da validação aparecerá aqui</span>
                  )}
                </div>
              </Card>
            </motion.div>
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
              <motion.h2 variants={itemVariants} className="text-3xl md:text-4xl font-bold mb-4">
                Benefícios Imediatos
              </motion.h2>
              <motion.p variants={itemVariants} className="text-gray-400 text-lg max-w-2xl mx-auto">
                Transforme sua operação de vendas com dados limpos e precisos.
              </motion.p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { icon: DollarSign, title: 'Redução de custos', desc: 'Economize resources eliminando contatos inválidos antes de investir tempo neles.' },
                { icon: Users, title: 'Mais contatos reais', desc: 'Foque apenas em números válidos e aumente sua taxa de conversão significativamente.' },
                { icon: Zap, title: 'Resultado instantâneo', desc: 'Validação em tempo real sem espera ou processamento demorado em lote.' }
              ].map((item, i) => (
                <motion.div 
                  key={i}
                  variants={itemVariants}
                  className="text-center p-8 bg-[#111827] rounded-2xl border border-white/5 transition-all duration-300 ease-in-out hover:scale-105 hover:-translate-y-[5px] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-white/20"
                >
                  <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center bg-[#2563EB]/10 rounded-2xl text-[#2563EB]">
                    <item.icon className="w-8 h-8" />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
                  <p className="text-gray-400 leading-relaxed">{item.desc}</p>
                </motion.div>
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
            <motion.h2 variants={itemVariants} className="text-4xl md:text-5xl font-bold mb-6" style={{ letterSpacing: '-0.02em' }}>
              Pronto para validar seus contatos?
            </motion.h2>
            
            <motion.p variants={itemVariants} className="text-xl text-gray-300 mb-10 leading-relaxed">
              Comece agora e elimine números inválidos da sua base de forma definitiva.
            </motion.p>

            <motion.div variants={itemVariants}>
              <RippleButton 
                size="lg" 
                className="bg-[#22C55E] hover:bg-[#22C55E] text-white font-semibold px-12 py-7 text-lg rounded-xl hover:shadow-[0_0_25px_rgba(34,197,94,0.5)]"
                onClick={() => document.getElementById('test-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Comece agora
              </RippleButton>
            </motion.div>
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
// DEALKIS
