-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 30/03/2026 às 16:13
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `callcheck`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `denuncia`
--

CREATE TABLE `denuncia` (
  `id` int(11) NOT NULL,
  `telefone_id` int(11) NOT NULL,
  `tipo` enum('fraude','golpe','spam','telemarketing abusivo') NOT NULL,
  `descricao` text DEFAULT NULL,
  `data` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `denuncia`
--

INSERT INTO `denuncia` (`id`, `telefone_id`, `tipo`, `descricao`, `data`) VALUES
(1, 1, 'golpe', 'Ligação pedindo dados bancários', '2026-03-26 17:40:02'),
(2, 4, 'golpe', 'Ligação dizendo ser do banco pedindo senha e código do app', '2026-03-30 10:23:36'),
(3, 5, 'fraude', 'Mensagem falando de entrega bloqueada e pedindo pagamento', '2026-03-30 10:24:07'),
(4, 6, 'spam', 'Ligação oferecendo promoção falsa de internet', '2026-03-30 10:24:38'),
(5, 4, 'golpe', 'Se passou por banco pedindo senha', '2026-03-30 10:37:35'),
(6, 4, 'fraude', 'Solicitou código do aplicativo', '2026-03-30 10:37:35'),
(7, 4, 'golpe', 'Tentativa de acesso à conta bancária', '2026-03-30 10:37:35'),
(8, 5, 'fraude', 'Cobrança de dívida inexistente', '2026-03-30 10:37:35'),
(9, 5, 'spam', 'Ligação insistente várias vezes', '2026-03-30 10:37:35'),
(10, 6, 'spam', 'Ligação automática', '2026-03-30 10:37:35'),
(11, 6, 'spam', 'Telemarketing genérico', '2026-03-30 10:37:35'),
(12, 5, 'spam', 'Ligação autommática', '2026-03-30 10:39:23'),
(13, 4, 'golpe', 'Solicitou informações pessoasi se passando pelo banco', '2026-03-30 10:40:52'),
(14, 1, 'fraude', 'Se passando por outras pessoas', '2026-03-30 10:45:14'),
(15, 4, 'golpe', 'Se passou por gerente do banco pedindo senha', '2026-03-30 11:09:52'),
(16, 4, 'golpe', 'Tentativa de acesso à conta bancária', '2026-03-30 11:09:52'),
(17, 4, 'golpe', 'Solicitou código do aplicativo', '2026-03-30 11:09:52'),
(18, 4, 'golpe', 'Ligação urgente sobre transação suspeita', '2026-03-30 11:09:52'),
(19, 4, 'golpe', 'Falsa central de segurança do banco', '2026-03-30 11:09:52'),
(20, 4, 'golpe', 'Tentou induzir transferência via PIX', '2026-03-30 11:09:52'),
(21, 4, 'fraude', 'Pediu confirmação de dados pessoais', '2026-03-30 11:09:52'),
(22, 4, 'fraude', 'Informou compra não reconhecida falsa', '2026-03-30 11:09:52'),
(23, 4, 'fraude', 'Tentativa de phishing bancário', '2026-03-30 11:09:52'),
(24, 4, 'spam', 'Ligação repetitiva insistente', '2026-03-30 11:09:52'),
(25, 5, 'fraude', 'Cobrança de dívida inexistente', '2026-03-30 11:09:52'),
(26, 5, 'fraude', 'Envio de link falso para pagamento', '2026-03-30 11:09:52'),
(27, 5, 'fraude', 'Ameaça de negativação indevida', '2026-03-30 11:09:52'),
(28, 5, 'golpe', 'Promessa de empréstimo fácil', '2026-03-30 11:09:52'),
(29, 5, 'golpe', 'Solicitou pagamento antecipado', '2026-03-30 11:09:52'),
(30, 5, 'golpe', 'Oferta de crédito falso', '2026-03-30 11:09:52'),
(31, 5, 'spam', 'Telemarketing abusivo', '2026-03-30 11:09:52'),
(32, 5, 'spam', 'Liga várias vezes ao dia', '2026-03-30 11:09:52'),
(33, 5, 'spam', 'Ofertas insistentes de serviços', '2026-03-30 11:09:52'),
(34, 6, 'spam', 'Ligação automática de operadora', '2026-03-30 11:09:52'),
(35, 6, 'spam', 'Chamada repetitiva sem resposta', '2026-03-30 11:09:52'),
(36, 6, 'spam', 'Oferta de plano de internet', '2026-03-30 11:09:52'),
(37, 6, 'spam', 'Ligação em horários inconvenientes', '2026-03-30 11:09:52'),
(38, 6, 'spam', 'Contato frequente sem autorização', '2026-03-30 11:09:52'),
(39, 6, 'fraude', 'Solicitação de CPF para cadastro suspeito', '2026-03-30 11:09:52'),
(40, 6, 'golpe', 'Falsa promoção de pacote de celular', '2026-03-30 11:09:52');

-- --------------------------------------------------------

--
-- Estrutura para tabela `empresa`
--

CREATE TABLE `empresa` (
  `id` int(11) NOT NULL,
  `nome` varchar(150) DEFAULT NULL,
  `cnpj` varchar(18) DEFAULT NULL,
  `verificada` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `empresa`
--

INSERT INTO `empresa` (`id`, `nome`, `cnpj`, `verificada`) VALUES
(1, 'Fundação Santo André', '57.538.696/0001-21', 1),
(3, 'TechNova Soluções', '11.111.111/0001-01', 1),
(4, 'Brasil Digital Serviços', '11.111.111/0001-02', 1),
(5, 'Central Financeira Alpha', '11.111.111/0001-03', 0),
(6, 'Rede Suporte Online', '11.111.111/0001-04', 1),
(7, 'Cobrança Express', '11.111.111/0001-05', 0),
(8, 'InfoTech Brasil', '11.111.111/0001-06', 1),
(9, 'Atendimento Rápido', '11.111.111/0001-07', 0),
(10, 'Global Serviços LTDA', '11.111.111/0001-08', 1),
(11, 'Max Crédito Fácil', '11.111.111/0001-09', 0),
(12, 'Conecta Telecom', '11.111.111/0001-10', 1),
(13, 'Segurança Digital Pro', '11.111.111/0001-11', 1),
(14, 'Help Desk Brasil', '11.111.111/0001-12', 1),
(15, 'Ativa Cobranças', '11.111.111/0001-13', 0),
(16, 'Central Vendas Online', '11.111.111/0001-14', 1),
(17, 'Prime Serviços Digitais', '11.111.111/0001-15', 1),
(18, 'NetCall Atendimento', '11.111.111/0001-16', 0),
(19, 'Ultra Tech Solutions', '11.111.111/0001-17', 1),
(20, 'Brasil Connect', '11.111.111/0001-18', 1),
(21, 'Fácil Crédito Brasil', '11.111.111/0001-19', 0),
(22, 'Central de Ofertas', '11.111.111/0001-20', 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `telefone`
--

CREATE TABLE `telefone` (
  `id` int(11) NOT NULL,
  `numero` varchar(20) DEFAULT NULL,
  `empresa_id` int(11) DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `suspeito` tinyint(1) DEFAULT 0,
  `principal` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `telefone`
--

INSERT INTO `telefone` (`id`, `numero`, `empresa_id`, `tipo`, `suspeito`, `principal`) VALUES
(1, '11963279440', NULL, 'desconhecido', 1, 0),
(2, '1149793312', 1, 'arrecadação', 0, 1),
(3, '1149793331', 1, 'arrecadação', 0, 0),
(4, '11999998888', NULL, 'desconhecido', 1, 0),
(5, '11988887777', NULL, 'desconhecido', 1, 0),
(6, '11977776666', NULL, 'desconhecido', 1, 0),
(9, '11940000003', 3, 'oficial', 0, 1),
(10, '11940000103', 3, 'secundario', 0, 0),
(11, '11940000004', 4, 'oficial', 0, 1),
(12, '11940000104', 4, 'secundario', 0, 0),
(13, '11940000005', 5, 'oficial', 0, 1),
(14, '11940000105', 5, 'secundario', 0, 0),
(15, '11940000006', 6, 'oficial', 0, 1),
(16, '11940000106', 6, 'secundario', 0, 0),
(17, '11940000007', 7, 'oficial', 0, 1),
(18, '11940000107', 7, 'secundario', 0, 0),
(19, '11940000008', 8, 'oficial', 0, 1),
(20, '11940000108', 8, 'secundario', 0, 0),
(21, '11940000009', 9, 'oficial', 0, 1),
(22, '11940000109', 9, 'secundario', 0, 0),
(23, '11940000010', 10, 'oficial', 0, 1),
(24, '11940000110', 10, 'secundario', 0, 0),
(25, '11940000011', 11, 'oficial', 0, 1),
(26, '11940000111', 11, 'secundario', 0, 0),
(27, '11940000012', 12, 'oficial', 0, 1),
(28, '11940000112', 12, 'secundario', 0, 0),
(29, '11940000013', 13, 'oficial', 0, 1),
(30, '11940000113', 13, 'secundario', 0, 0),
(31, '11940000014', 14, 'oficial', 0, 1),
(32, '11940000114', 14, 'secundario', 0, 0),
(33, '11940000015', 15, 'oficial', 0, 1),
(34, '11940000115', 15, 'secundario', 0, 0),
(35, '11940000016', 16, 'oficial', 0, 1),
(36, '11940000116', 16, 'secundario', 0, 0),
(37, '11940000017', 17, 'oficial', 0, 1),
(38, '11940000117', 17, 'secundario', 0, 0),
(39, '11940000018', 18, 'oficial', 0, 1),
(40, '11940000118', 18, 'secundario', 0, 0),
(41, '11940000019', 19, 'oficial', 0, 1),
(42, '11940000119', 19, 'secundario', 0, 0),
(43, '11940000020', 20, 'oficial', 0, 1),
(44, '11940000120', 20, 'secundario', 0, 0),
(45, '11940000021', 21, 'oficial', 0, 1),
(46, '11940000121', 21, 'secundario', 0, 0),
(47, '11940000022', 22, 'oficial', 0, 1),
(48, '11940000122', 22, 'secundario', 0, 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `usuario`
--

CREATE TABLE `usuario` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `senha` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `usuario`
--

INSERT INTO `usuario` (`id`, `nome`, `email`, `senha`) VALUES
(1, 'Pedro', 'pedro@email.com', '12345');

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `denuncia`
--
ALTER TABLE `denuncia`
  ADD PRIMARY KEY (`id`),
  ADD KEY `telefone_id` (`telefone_id`);

--
-- Índices de tabela `empresa`
--
ALTER TABLE `empresa`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `telefone`
--
ALTER TABLE `telefone`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `numero` (`numero`);

--
-- Índices de tabela `usuario`
--
ALTER TABLE `usuario`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `denuncia`
--
ALTER TABLE `denuncia`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=41;

--
-- AUTO_INCREMENT de tabela `empresa`
--
ALTER TABLE `empresa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;

--
-- AUTO_INCREMENT de tabela `telefone`
--
ALTER TABLE `telefone`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=49;

--
-- AUTO_INCREMENT de tabela `usuario`
--
ALTER TABLE `usuario`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `denuncia`
--
ALTER TABLE `denuncia`
  ADD CONSTRAINT `denuncia_ibfk_1` FOREIGN KEY (`telefone_id`) REFERENCES `telefone` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
