CREATE DATABASE IF NOT EXISTS bd_stop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bd_stop;
--
--
-- Banco de dados: `bd_stop`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `categorias`
--

DROP TABLE IF EXISTS `categorias`;
CREATE TABLE IF NOT EXISTS `categorias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ativo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `categorias`
--

INSERT INTO `categorias` (`id`, `nome`, `descricao`, `ativo`) VALUES
(1, 'Alimentos', NULL, 1),
(2, 'Laticínios', NULL, 1),
(3, 'Limpeza', NULL, 1),
(4, 'Higiene', NULL, 1),
(5, 'Bebidas', NULL, 1),
(6, 'Padaria', NULL, 1);

-- --------------------------------------------------------

--
-- Estrutura da tabela `formas_pagamento`
--

DROP TABLE IF EXISTS `formas_pagamento`;
CREATE TABLE IF NOT EXISTS `formas_pagamento` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `requer_troco` tinyint(1) DEFAULT '0',
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `formas_pagamento`
--

INSERT INTO `formas_pagamento` (`id`, `nome`, `ativo`, `requer_troco`, `data_criacao`) VALUES
(1, 'DINHEIRO', 1, 1, '2025-11-16 16:31:23'),
(2, 'CARTÃO DÉBITO', 1, 0, '2025-11-16 16:31:23'),
(3, 'CARTÃO CRÉDITO', 1, 0, '2025-11-16 16:31:23'),
(4, 'PIX', 1, 0, '2025-11-16 16:31:23'),
(5, 'TRANSFERÊNCIA', 1, 0, '2025-11-16 16:31:23');

-- --------------------------------------------------------

--
-- Estrutura da tabela `itens_venda`
--

DROP TABLE IF EXISTS `itens_venda`;
CREATE TABLE IF NOT EXISTS `itens_venda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `venda_id` int DEFAULT NULL,
  `produto_id` int DEFAULT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `preco_unitario` decimal(10,2) NOT NULL,
  `iva_taxa` decimal(5,2) NOT NULL,
  `iva_valor` decimal(10,2) NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `venda_id` (`venda_id`),
  KEY `produto_id` (`produto_id`)
) ENGINE=MyISAM AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `itens_venda`
--

INSERT INTO `itens_venda` (`id`, `venda_id`, `produto_id`, `quantidade`, `preco_unitario`, `iva_taxa`, `iva_valor`, `subtotal`) VALUES
(1, 1, 1, 1.000, 2890.00, 7.00, 202.30, 2890.00),
(2, 1, 2, 1.000, 950.00, 7.00, 66.50, 950.00),
(3, 2, 1, 1.000, 2890.00, 7.00, 202.30, 2890.00),
(4, 2, 2, 2.000, 950.00, 7.00, 133.00, 1900.00),
(5, 2, 3, 2.000, 2580.00, 7.00, 361.20, 5160.00),
(6, 2, 5, 1.000, 520.00, 7.00, 36.40, 520.00),
(7, 2, 8, 1.000, 1230.00, 7.00, 86.10, 1230.00),
(8, 2, 9, 1.000, 350.00, 7.00, 24.50, 350.00),
(9, 3, 1, 1.000, 2890.00, 7.00, 202.30, 2890.00),
(10, 3, 2, 2.000, 950.00, 7.00, 133.00, 1900.00),
(11, 3, 8, 2.000, 1230.00, 14.00, 344.40, 2460.00),
(12, 4, 1, 1.000, 2890.00, 7.00, 202.30, 2890.00),
(13, 4, 2, 2.000, 950.00, 7.00, 133.00, 1900.00),
(14, 4, 8, 2.000, 1230.00, 14.00, 344.40, 2460.00);

-- --------------------------------------------------------

--
-- Estrutura da tabela `iva`
--

DROP TABLE IF EXISTS `iva`;
CREATE TABLE IF NOT EXISTS `iva` (
  `id` int NOT NULL AUTO_INCREMENT,
  `taxa` decimal(5,2) NOT NULL,
  `descricao` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `iva`
--

INSERT INTO `iva` (`id`, `taxa`, `descricao`, `ativo`, `data_criacao`) VALUES
(1, 0.00, 'Isento', 1, '2025-11-16 16:31:23'),
(2, 1.00, 'IVA 1%', 1, '2025-11-16 16:31:23'),
(3, 7.00, 'IVA 7%', 1, '2025-11-16 16:31:23'),
(4, 14.00, 'IVA 14%', 1, '2025-11-16 16:31:23');

-- --------------------------------------------------------

--
-- Estrutura da tabela `logs_sistema`
--

DROP TABLE IF EXISTS `logs_sistema`;
CREATE TABLE IF NOT EXISTS `logs_sistema` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int DEFAULT NULL,
  `acao` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_hora` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `movimentos_caixa`
--

DROP TABLE IF EXISTS `movimentos_caixa`;
CREATE TABLE IF NOT EXISTS `movimentos_caixa` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int DEFAULT NULL,
  `tipo` enum('abertura','fechamento','suprimento','sangria') COLLATE utf8mb4_unicode_ci NOT NULL,
  `valor` decimal(10,2) NOT NULL,
  `observacoes` text COLLATE utf8mb4_unicode_ci,
  `data_hora` datetime NOT NULL,
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `pagamentos_venda`
--

DROP TABLE IF EXISTS `pagamentos_venda`;
CREATE TABLE IF NOT EXISTS `pagamentos_venda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `venda_id` int NOT NULL,
  `forma_pagamento` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `valor` decimal(10,2) NOT NULL,
  `valor_pago` decimal(10,2) NOT NULL,
  `troco` decimal(10,2) DEFAULT '0.00',
  `data_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `venda_id` (`venda_id`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `pagamentos_venda`
--

INSERT INTO `pagamentos_venda` (`id`, `venda_id`, `forma_pagamento`, `valor`, `valor_pago`, `troco`, `data_registro`) VALUES
(1, 3, 'DINHEIRO', 7250.00, 8000.00, 750.00, '2025-11-16 23:21:04'),
(2, 4, 'DINHEIRO', 7250.00, 8000.00, 750.00, '2025-11-16 23:21:36');

-- --------------------------------------------------------

--
-- Estrutura da tabela `pontos_venda`
--

DROP TABLE IF EXISTS `pontos_venda`;
CREATE TABLE IF NOT EXISTS `pontos_venda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `localizacao` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impressora` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `data_atualizacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome` (`nome`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `pontos_venda`
--

INSERT INTO `pontos_venda` (`id`, `nome`, `localizacao`, `impressora`, `ativo`, `data_criacao`, `data_atualizacao`) VALUES
(1, 'PDV Principal', 'Loja Central', 'USB001', 1, '2025-11-16 21:52:09', '2025-11-16 21:52:09'),
(2, 'PDV Secundário', 'Piso 1 - Secção Eletrónica', 'USB002', 1, '2025-11-16 21:52:09', '2025-11-16 21:52:09'),
(3, 'PDV Restauração', 'Piso 2 - Área de Restauração', 'USB003', 1, '2025-11-16 21:52:09', '2025-11-16 21:52:09');

-- --------------------------------------------------------

--
-- Estrutura da tabela `produtos`
--

DROP TABLE IF EXISTS `produtos`;
CREATE TABLE IF NOT EXISTS `produtos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nome` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `preco` decimal(10,2) NOT NULL,
  `preco_custo` decimal(10,2) DEFAULT NULL,
  `estoque` int DEFAULT '0',
  `estoque_minimo` int DEFAULT '0',
  `categoria_id` int DEFAULT NULL,
  `iva_id` int DEFAULT NULL,
  `peso_bruto` decimal(10,3) DEFAULT NULL,
  `unidade_medida` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `data_atualizacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `categoria_id` (`categoria_id`),
  KEY `iva_id` (`iva_id`)
) ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `produtos`
--

INSERT INTO `produtos` (`id`, `codigo`, `nome`, `preco`, `preco_custo`, `estoque`, `estoque_minimo`, `categoria_id`, `iva_id`, `peso_bruto`, `unidade_medida`, `ativo`, `data_criacao`, `data_atualizacao`) VALUES
(1, '001', 'Arroz Integral 5kg', 2890.00, 2200.00, 46, 0, 1, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 23:21:36'),
(2, '002', 'Feijão Carioca 1kg', 950.00, 700.00, 93, 0, 1, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 23:21:36'),
(3, '003', 'Azeite Extra Virgem 500ml', 2580.00, 1900.00, 28, 0, 1, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 22:49:54'),
(4, '4897057900065', 'Café Gourmet 500g', 2250.00, 1600.00, 40, 0, 1, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 22:12:30'),
(5, '005', 'Leite Integral 1L', 520.00, 380.00, 119, 0, 2, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 22:49:54'),
(6, '006', 'Queijo Mussarela 1kg', 1890.00, 1400.00, 25, 0, 2, 3, NULL, 'kg', 1, '2025-11-16 16:31:23', '2025-11-16 16:31:23'),
(7, '007', 'Iogurte Natural 200g', 850.00, 600.00, 60, 0, 2, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 16:31:23'),
(8, '008', 'Sabonete Líquido 500ml', 1230.00, 900.00, 40, 0, 4, 4, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 23:21:36'),
(9, '009', 'Detergente 500ml', 350.00, 250.00, 79, 0, 3, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 22:49:54'),
(10, '010', 'Shampoo Antiqueda 400ml', 3290.00, 2400.00, 35, 0, 4, 3, NULL, 'un', 1, '2025-11-16 16:31:23', '2025-11-16 16:31:23');

-- --------------------------------------------------------

--
-- Estrutura da tabela `sessoes_usuarios`
--

DROP TABLE IF EXISTS `sessoes_usuarios`;
CREATE TABLE IF NOT EXISTS `sessoes_usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int NOT NULL,
  `ponto_venda_id` int NOT NULL,
  `data_login` datetime NOT NULL,
  `data_ultima_acao` datetime NOT NULL,
  `endereco_ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `token_sessao` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ativa` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_sessao` (`token_sessao`),
  KEY `ponto_venda_id` (`ponto_venda_id`),
  KEY `idx_sessoes_usuario` (`usuario_id`,`ativa`),
  KEY `idx_sessoes_token` (`token_sessao`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `sessoes_usuarios`
--

INSERT INTO `sessoes_usuarios` (`id`, `usuario_id`, `ponto_venda_id`, `data_login`, `data_ultima_acao`, `endereco_ip`, `token_sessao`, `ativa`) VALUES
(1, 4, 1, '2025-11-16 23:10:59', '2025-11-16 23:13:53', NULL, 'SESSION_4_1763331059', 0),
(2, 1, 1, '2025-11-16 23:14:31', '2025-11-16 23:14:31', NULL, 'SESSION_1_1763331271', 0),
(3, 4, 1, '2025-11-16 23:15:47', '2025-11-16 23:43:45', NULL, 'SESSION_4_1763331347', 0),
(4, 4, 1, '2025-11-16 23:46:23', '2025-11-16 23:49:44', NULL, 'SESSION_4_1763333183', 1);

-- --------------------------------------------------------

--
-- Estrutura da tabela `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_trabalhador` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nome` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `senha` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nivel` enum('admin','gerente','supervisor','operador') COLLATE utf8mb4_unicode_ci NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_trabalhador` (`numero_trabalhador`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `usuarios`
--

INSERT INTO `usuarios` (`id`, `numero_trabalhador`, `nome`, `senha`, `nivel`, `ativo`, `data_criacao`) VALUES
(1, '0001', 'Administrador', '827ccb0eea8a706c4c34a16891f84e7b', 'admin', 1, '2025-11-16 16:31:23'),
(2, '0002', 'Gerente Geral', '827ccb0eea8a706c4c34a16891f84e7b', 'gerente', 1, '2025-11-16 16:31:23'),
(3, '0003', 'Supervisor', '827ccb0eea8a706c4c34a16891f84e7b', 'supervisor', 1, '2025-11-16 16:31:23'),
(4, '0004', 'Operador Caixa', '827ccb0eea8a706c4c34a16891f84e7b', 'operador', 1, '2025-11-16 16:31:23');

-- --------------------------------------------------------

--
-- Estrutura da tabela `vendas`
--

DROP TABLE IF EXISTS `vendas`;
CREATE TABLE IF NOT EXISTS `vendas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_venda` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usuario_id` int DEFAULT NULL,
  `data_hora` datetime NOT NULL,
  `total` decimal(10,2) NOT NULL,
  `total_iva` decimal(10,2) NOT NULL,
  `desconto` decimal(10,2) DEFAULT '0.00',
  `estado` enum('pendente','finalizada','cancelada') COLLATE utf8mb4_unicode_ci DEFAULT 'finalizada',
  `observacoes` text COLLATE utf8mb4_unicode_ci,
  `ponto_venda_id` int DEFAULT '1',
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_venda` (`numero_venda`),
  KEY `usuario_id` (`usuario_id`),
  KEY `fk_vendas_ponto_venda` (`ponto_venda_id`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Extraindo dados da tabela `vendas`
--

INSERT INTO `vendas` (`id`, `numero_venda`, `usuario_id`, `data_hora`, `total`, `total_iva`, `desconto`, `estado`, `observacoes`, `ponto_venda_id`, `data_criacao`) VALUES
(1, NULL, 4, '2025-11-16 23:47:13', 3840.00, 268.80, 0.00, 'finalizada', NULL, 1, '2025-11-16 22:47:13'),
(2, NULL, 4, '2025-11-16 23:49:54', 12050.00, 843.50, 0.00, 'finalizada', NULL, 1, '2025-11-16 22:49:54'),
(3, NULL, 3, '2025-11-17 00:21:04', 7250.00, 679.70, 0.00, 'finalizada', NULL, 1, '2025-11-16 23:21:04'),
(4, NULL, 3, '2025-11-17 00:21:36', 7250.00, 679.70, 0.00, 'finalizada', NULL, 1, '2025-11-16 23:21:36');
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
