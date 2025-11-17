CREATE DATABASE sistema_vendas7 ;
USE sistema_vendas7;

CREATE TABLE IF NOT EXISTS `auditoria` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_hora` datetime NOT NULL,
  `usuario_id` int NOT NULL,
  `acao` varchar(100) NOT NULL,
  `descricao` text,
  `tabela_afetada` varchar(50) DEFAULT NULL,
  `registro_id` int DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`)
) ENGINE=MyISAM AUTO_INCREMENT=431 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `auditoria` (`id`, `data_hora`, `usuario_id`, `acao`, `descricao`, `tabela_afetada`, `registro_id`, `ip_address`) VALUES
(1, '2025-11-03 21:40:14', 1, 'LOGIN', 'Login no sistema', '', NULL, NULL),
(430, '2025-11-14 23:49:19', 4, 'LOGIN', 'Login no PDV 1', '', NULL, NULL);


CREATE TABLE IF NOT EXISTS `caixa` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ponto_venda_id` int NOT NULL,
  `data_abertura` datetime NOT NULL,
  `data_fecho` datetime DEFAULT NULL,
  `operador_id` int NOT NULL,
  `supervisor_abertura_id` int DEFAULT NULL,
  `supervisor_fecho_id` int DEFAULT NULL,
  `saldo_inicial` decimal(10,2) NOT NULL,
  `saldo_final` decimal(10,2) DEFAULT NULL,
  `total_vendas` decimal(10,2) DEFAULT '0.00',
  `total_entradas` decimal(10,2) DEFAULT '0.00',
  `total_saidas` decimal(10,2) DEFAULT '0.00',
  `status` enum('ABERTO','FECHADO') DEFAULT 'ABERTO',
  `observacoes` text,
  PRIMARY KEY (`id`),
  KEY `operador_id` (`operador_id`),
  KEY `supervisor_abertura_id` (`supervisor_abertura_id`),
  KEY `supervisor_fecho_id` (`supervisor_fecho_id`),
  KEY `ponto_venda_id` (`ponto_venda_id`)
) ENGINE=MyISAM AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `caixa` (`id`, `ponto_venda_id`, `data_abertura`, `data_fecho`, `operador_id`, `supervisor_abertura_id`, `supervisor_fecho_id`, `saldo_inicial`, `saldo_final`, `total_vendas`, `total_entradas`, `total_saidas`, `status`, `observacoes`) VALUES
(1, 0, '2025-11-03 21:40:24', '2025-11-11 22:11:35', 1, 1, NULL, 10000.00, 10000.00, 228.08, 0.00, 0.00, 'FECHADO', NULL),
(9, 0, '2025-11-14 20:28:42', NULL, 3, 5, NULL, 0.00, NULL, 0.00, 0.00, 0.00, 'ABERTO', NULL);


CREATE TABLE IF NOT EXISTS `cartoes_cliente` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_cartao` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cliente_id` int NOT NULL,
  `senha_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `saldo` decimal(10,2) DEFAULT '0.00',
  `data_emissao` datetime DEFAULT CURRENT_TIMESTAMP,
  `data_validade` date DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_cartao` (`numero_cartao`),
  KEY `cliente_id` (`cliente_id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `cartoes_cliente` (`id`, `numero_cartao`, `cliente_id`, `senha_hash`, `saldo`, `data_emissao`, `data_validade`, `ativo`) VALUES
(1, '0654251128461173', 4, '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 199511.50, '2025-11-10 20:59:49', '2027-11-10', 1);

CREATE TABLE IF NOT EXISTS `categorias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `descricao` text,
  `ativo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `categorias` (`id`, `nome`, `descricao`, `ativo`) VALUES
(1, 'Alimentos', NULL, 1),
(2, 'Bebidas', NULL, 1),
(3, 'Limpeza', NULL, 1),
(4, 'Higiene', NULL, 1),
(5, 'Outros', NULL, 1),
(6, 'Alimentos', 'Produtos alimentícios em geral', 1),
(7, 'Bebidas', 'Bebidas diversas', 1),
(8, 'Limpeza', 'Produtos de limpeza', 1),
(9, 'Higiene', 'Produtos de higiene pessoal', 1),
(10, 'Padaria', 'Pães, bolos e salgados', 1),
(11, 'Frios', 'Queijos, presuntos e frios', 1),
(12, 'Hortifruti', 'Frutas, verduras e legumes', 1),
(13, 'Bazar', 'Produtos diversos para casa', 1),
(14, 'Carnes', 'Carnes bovinas, suínas e aves', 1),
(15, 'Laticínios', 'Leite, iogurte e derivados', 1);

CREATE TABLE IF NOT EXISTS `clientes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `telefone` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `endereco` text,
  `data_cadastro` datetime DEFAULT CURRENT_TIMESTAMP,
  `cadastrado_por` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cadastrado_por` (`cadastrado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


INSERT INTO `clientes` (`id`, `nome`, `telefone`, `email`, `endereco`, `data_cadastro`, `cadastrado_por`) VALUES
(1, 'João da Silva', '(11) 99999-1111', 'joao.silva@email.com', 'Rua A, 123 - Centro', '2025-11-03 23:36:56', 1),
(2, 'Maria Oliveira', '(11) 99999-2222', 'maria.oliveira@email.com', 'Av. B, 456 - Jardim', '2025-11-03 23:36:56', 1),
(3, 'Pedro Santos', '(11) 99999-3333', 'pedro.santos@email.com', 'Rua C, 789 - Vila Nova', '2025-11-03 23:36:56', 1),
(4, 'Ana Costa', '(11) 99999-4444', 'ana.costa@email.com', 'Alameda D, 321 - Centro', '2025-11-03 23:36:56', 1);

CREATE TABLE IF NOT EXISTS `fornecedores` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `telefone` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `endereco` text,
  `ativo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `fornecedores` (`id`, `nome`, `telefone`, `email`, `endereco`, `ativo`) VALUES
(1, 'Distribuidora Alimentícia Ltda', '(11) 3333-4444', 'vendas@distralim.com.br', 'Rua das Indústrias, 100 - SP', 1),
(2, 'Bebidas do Brasil S.A.', '(11) 5555-6666', 'contato@bebidasbrasil.com', 'Av. das Nações, 500 - SP', 1),
(3, 'Limpeza Total Indústria', '(11) 7777-8888', 'vendas@limpezatotal.com', 'Rua da Limpeza, 250 - SP', 1),
(4, 'Higiene Pura Ltda', '(11) 9999-0000', 'contato@higienepura.com', 'Alameda da Saúde, 75 - SP', 1),
(5, 'Padaria Pão Quente', '(11) 2222-3333', 'paoquente@padaria.com', 'Rua dos Padeiros, 33 - SP', 1);

CREATE TABLE IF NOT EXISTS `itens_venda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `venda_id` int NOT NULL,
  `produto_id` int NOT NULL,
  `quantidade` int NOT NULL,
  `preco_unitario` decimal(10,2) NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  `cancelado` tinyint(1) DEFAULT '0',
  `motivo_cancelamento` text,
  `cancelado_por` int DEFAULT NULL,
  `data_cancelamento` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `venda_id` (`venda_id`),
  KEY `produto_id` (`produto_id`),
  KEY `cancelado_por` (`cancelado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=282 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `itens_venda` (`id`, `venda_id`, `produto_id`, `quantidade`, `preco_unitario`, `subtotal`, `cancelado`, `motivo_cancelamento`, `cancelado_por`, `data_cancelamento`) VALUES
(1, 1, 31, 1, 5.90, 5.90, 0, NULL, NULL, NULL),
(2, 1, 3, 1, 4.20, 4.20, 0, NULL, NULL, NULL),
(281, 69, 33, 1, 4.90, 4.90, 0, NULL, NULL, NULL);

CREATE TABLE IF NOT EXISTS `movimentos_caixa` (
  `id` int NOT NULL AUTO_INCREMENT,
  `caixa_id` int NOT NULL,
  `data_hora` datetime NOT NULL,
  `tipo` enum('ENTRADA','SAIDA','OBSERVACAO') NOT NULL,
  `descricao` varchar(200) DEFAULT NULL,
  `valor` decimal(10,2) NOT NULL,
  `forma_pagamento` varchar(50) DEFAULT NULL,
  `autorizado_por` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `caixa_id` (`caixa_id`),
  KEY `autorizado_por` (`autorizado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=88 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `movimentos_caixa` (`id`, `caixa_id`, `data_hora`, `tipo`, `descricao`, `valor`, `forma_pagamento`, `autorizado_por`) VALUES
(1, 3, '2025-11-04 14:55:48', 'ENTRADA', 'VENDA #000001', 11.00, 'DINHEIRO', NULL),
(2, 3, '2025-11-04 14:56:06', 'ENTRADA', 'VENDA #000002', 10.10, 'CARTÃO DÉBITO', NULL),
(87, 9, '2025-11-14 20:38:10', 'SAIDA', 'SANGRIA - DINHEIRO', 50.00, 'DINHEIRO', NULL);

CREATE TABLE IF NOT EXISTS `movimentos_cartao` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cartao_id` int NOT NULL,
  `data_hora` datetime NOT NULL,
  `tipo` enum('CARREGAMENTO','PAGAMENTO','CONSULTA') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valor` decimal(10,2) NOT NULL,
  `saldo_anterior` decimal(10,2) DEFAULT NULL,
  `saldo_posterior` decimal(10,2) DEFAULT NULL,
  `operador_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cartao_id` (`cartao_id`),
  KEY `operador_id` (`operador_id`)
) ENGINE=MyISAM AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `movimentos_cartao` (`id`, `cartao_id`, `data_hora`, `tipo`, `descricao`, `valor`, `saldo_anterior`, `saldo_posterior`, `operador_id`) VALUES
(1, 1, '2025-11-10 21:01:25', 'CARREGAMENTO', 'Carregamento via caixa', 200000.00, 0.00, 200000.00, 1),
(2, 1, '2025-11-10 21:02:42', 'CONSULTA', 'Consulta de saldo', 0.00, 200000.00, 200000.00, NULL),
(3, 1, '2025-11-10 21:04:21', 'PAGAMENTO', 'Pagamento de compra', 89.40, 200000.00, 199910.60, 1),
(9, 1, '2025-11-10 22:48:55', 'CONSULTA', 'Consulta de saldo', 0.00, 199816.30, 199816.30, NULL),
(15, 1, '2025-11-13 22:02:28', 'PAGAMENTO', 'Pagamento de compra', 109.70, 199621.20, 199511.50, 4);

CREATE TABLE IF NOT EXISTS `pontos_venda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_caixa` int NOT NULL,
  `descricao_caixa` varchar(100) NOT NULL,
  `localizacao` varchar(200) DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `data_cadastro` datetime DEFAULT CURRENT_TIMESTAMP,
  `cadastrado_por` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_caixa` (`numero_caixa`),
  KEY `cadastrado_por` (`cadastrado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `pontos_venda` (`id`, `numero_caixa`, `descricao_caixa`, `localizacao`, `ativo`, `data_cadastro`, `cadastrado_por`) VALUES
(1, 1, 'Caixa Principal', 'Loja Centro', 1, '2025-11-14 20:19:39', NULL);

CREATE TABLE IF NOT EXISTS `produtos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(50) NOT NULL,
  `nome` varchar(200) NOT NULL,
  `descricao` text,
  `preco` decimal(10,2) NOT NULL,
  `preco_custo` decimal(10,2) DEFAULT NULL,
  `estoque` int DEFAULT '0',
  `estoque_minimo` int DEFAULT '5',
  `categoria_id` int DEFAULT NULL,
  `fornecedor_id` int DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `data_cadastro` datetime DEFAULT CURRENT_TIMESTAMP,
  `cadastrado_por` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `categoria_id` (`categoria_id`),
  KEY `fornecedor_id` (`fornecedor_id`),
  KEY `cadastrado_por` (`cadastrado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `produtos` (`id`, `codigo`, `nome`, `descricao`, `preco`, `preco_custo`, `estoque`, `estoque_minimo`, `categoria_id`, `fornecedor_id`, `ativo`, `data_cadastro`, `cadastrado_por`) VALUES
(1, 'ARROZ001', 'Arroz Branco 5kg', 'Arroz tipo 1, pacote 5kg', 22.90, 15.50, 61, 10, 1, 1, 1, '2025-11-03 23:36:56', 1),
(2, 'FEIJAO001', 'Feijão Carioca 1kg', 'Feijão carioca tipo 1', 8.50, 5.20, 131, 20, 1, 1, 1, '2025-11-03 23:36:56', 1),
(3, 'ACUCAR001', 'Açúcar Refinado 1kg', 'Açúcar cristal refinado', 4.20, 2.50, 184, 30, 1, 1, 1, '2025-11-03 23:36:56', 1),
(4, 'CAFE001', 'Café em Pó 500g', 'Café torrado e moído', 18.90, 12.00, 70, 15, 1, 1, 1, '2025-11-03 23:36:56', 1),
(5, 'OLEO001', 'Óleo de Soja 900ml', 'Óleo de soja refinado', 7.80, 4.50, 120, 25, 1, 1, 1, '2025-11-03 23:36:56', 1),
(6, 'FARINHA001', 'Farinha de Trigo 1kg', 'Farinha de trigo especial', 5.90, 3.20, 88, 20, 1, 1, 1, '2025-11-03 23:36:56', 1),
(7, 'SAL001', 'Sal Refinado 1kg', 'Sal refinado iodado', 3.50, 1.80, 179, 40, 1, 1, 1, '2025-11-03 23:36:56', 1),
(8, 'REFRIG001', 'Refrigerante Cola 2L', 'Refrigerante sabor cola', 8.90, 5.00, 59, 15, 2, 2, 1, '2025-11-03 23:36:56', 1),
(9, 'SUCO001', 'Suco de Laranja 1L', 'Suco integral de laranja', 9.50, 6.00, 44, 10, 2, 2, 1, '2025-11-03 23:36:56', 1),
(10, '4897057900065', 'Água Mineral 500ml', 'Água mineral sem gás', 40.50, 1.20, 194, 50, 2, 2, 1, '2025-11-03 23:36:56', 1),
(48, 'CERVEJA002', 'Cerveja IPA 350ml', 'Cerveja artesanal IPA', 12.90, 8.00, 8, 8, 2, 2, 1, '2025-11-03 23:36:56', 1);

CREATE TABLE IF NOT EXISTS `promocoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `tipo` enum('PERCENTUAL','VALOR_FIXO','COMPRE_X_LEVE_Y','DESCONTO_POR_QUANTIDADE') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `valor` decimal(10,2) DEFAULT NULL,
  `produto_alvo_id` int DEFAULT NULL,
  `categoria_alvo_id` int DEFAULT NULL,
  `produtos_aplicaveis` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `data_inicio` date NOT NULL,
  `data_fim` date NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `quantidade_x` int DEFAULT '1',
  `quantidade_y` int DEFAULT '1',
  `quantidade_minima` int DEFAULT '1',
  `criado_por` int DEFAULT NULL,
  `data_criacao` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `produto_alvo_id` (`produto_alvo_id`),
  KEY `categoria_alvo_id` (`categoria_alvo_id`),
  KEY `criado_por` (`criado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `promocoes` (`id`, `nome`, `descricao`, `tipo`, `valor`, `produto_alvo_id`, `categoria_alvo_id`, `produtos_aplicaveis`, `data_inicio`, `data_fim`, `ativo`, `quantidade_x`, `quantidade_y`, `quantidade_minima`, `criado_por`, `data_criacao`) VALUES
(1, 'test', 'test', 'PERCENTUAL', 10.00, 2, 2, NULL, '0000-00-00', '0000-00-00', 0, 1, 1, 1, NULL, '2025-11-10 23:03:30'),
(2, 'Promoção Geral 10% OFF', 'Desconto de 10% em todos os produtos da loja', 'PERCENTUAL', 10.00, NULL, NULL, NULL, '2025-11-10', '2025-12-10', 0, 1, 1, 1, 1, '2025-11-10 23:04:37'),
(11, 'Desconto Produto B', 'Promoção especial', 'VALOR_FIXO', 2.00, 2, NULL, NULL, '2025-11-10', '2025-12-10', 1, 1, 1, 1, 1, '2025-11-10 23:12:39'),
(12, 'Promoção Categoria X', 'Desconto na categoria', 'PERCENTUAL', 15.00, NULL, 1, NULL, '2025-11-10', '2025-12-10', 0, 1, 1, 1, 1, '2025-11-10 23:12:39'),
(13, 'Leve 2 Pague 1', 'Promoção compre 2 leve 1', 'COMPRE_X_LEVE_Y', NULL, 3, NULL, NULL, '2025-11-10', '2025-12-10', 0, 2, 1, 1, 1, '2025-11-10 23:12:40'),
(14, 'Leve 3 Pague 2', 'Promoção compre 3 leve 2', 'COMPRE_X_LEVE_Y', NULL, 4, NULL, NULL, '2025-11-10', '2025-12-10', 0, 3, 2, 1, 1, '2025-11-10 23:12:40');

CREATE TABLE IF NOT EXISTS `promocoes_aplicadas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `venda_id` int NOT NULL,
  `promocao_id` int NOT NULL,
  `produto_id` int NOT NULL,
  `valor_desconto` decimal(10,2) NOT NULL,
  `quantidade` int NOT NULL,
  `data_aplicacao` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `venda_id` (`venda_id`),
  KEY `promocao_id` (`promocao_id`),
  KEY `produto_id` (`produto_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_trabalhador` varchar(20) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `nivel_acesso` enum('OPERADOR','SUPERVISOR','ADMIN') DEFAULT 'OPERADOR',
  `ativo` tinyint(1) DEFAULT '1',
  `data_cadastro` datetime DEFAULT CURRENT_TIMESTAMP,
  `ultimo_login` datetime DEFAULT NULL,
  `criado_por` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_trabalhador` (`numero_trabalhador`),
  KEY `criado_por` (`criado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `usuarios` (`id`, `numero_trabalhador`, `nome`, `senha_hash`, `nivel_acesso`, `ativo`, `data_cadastro`, `ultimo_login`, `criado_por`) VALUES
(1, '00001', 'Administrador', '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5', 'ADMIN', 1, '2025-11-03 21:12:19', '2025-11-14 20:05:38', NULL),
(2, '00002', 'Supervisor João Silva', '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5', 'SUPERVISOR', 1, '2025-11-03 23:36:56', NULL, NULL),
(3, '00003', 'Operadora Maria Santos', '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5', 'OPERADOR', 1, '2025-11-03 23:36:56', '2025-11-14 21:13:54', NULL),
(4, '00004', 'Operador Pedro Oliveira', '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5', 'OPERADOR', 1, '2025-11-03 23:36:56', '2025-11-14 23:49:19', NULL),
(5, '00005', 'Supervisora Ana Costa', '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5', 'SUPERVISOR', 1, '2025-11-03 23:36:56', NULL, NULL),
(6, '00007', 'Paulo', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'OPERADOR', 1, '2025-11-12 00:35:11', NULL, 1),
(7, '00006', 'Miguel ant', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'SUPERVISOR', 1, '2025-11-12 00:35:41', NULL, 1),
(8, '00009', 'santos', '12345', 'SUPERVISOR', 1, '2025-11-13 19:52:18', NULL, NULL);


CREATE TABLE IF NOT EXISTS `vendas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_hora` datetime NOT NULL,
  `total` decimal(10,2) NOT NULL,
  `forma_pagamento` text,
  `valor_pago` decimal(10,2) DEFAULT NULL,
  `troco` decimal(10,2) DEFAULT NULL,
  `operador_id` int NOT NULL,
  `supervisor_id` int DEFAULT NULL,
  `cliente_id` int DEFAULT NULL,
  `desconto` decimal(10,2) DEFAULT '0.00',
  `status` enum('FINALIZADA','CANCELADA','PENDENTE') DEFAULT 'FINALIZADA',
  `motivo_cancelamento` text,
  `cancelado_por` int DEFAULT NULL,
  `data_cancelamento` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `operador_id` (`operador_id`),
  KEY `supervisor_id` (`supervisor_id`),
  KEY `cliente_id` (`cliente_id`),
  KEY `cancelado_por` (`cancelado_por`)
) ENGINE=MyISAM AUTO_INCREMENT=70 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `vendas` (`id`, `data_hora`, `total`, `forma_pagamento`, `valor_pago`, `troco`, `operador_id`, `supervisor_id`, `cliente_id`, `desconto`, `status`, `motivo_cancelamento`, `cancelado_por`, `data_cancelamento`) VALUES
(1, '2025-11-04 14:55:48', 10.10, 'DINHEIRO: R$ 11.00', 11.00, 0.90, 1, NULL, NULL, 0.00, 'CANCELADA', 'erro', 1, '2025-11-04 14:58:36'),
(2, '2025-11-04 14:56:06', 10.10, 'CARTÃO DÉBITO: R$ 10.10', 10.10, 0.00, 1, NULL, NULL, 0.00, 'FINALIZADA', NULL, NULL, NULL),
(69, '2025-11-14 20:30:05', 30.70, 'DINHEIRO: R$ 31.00', 31.00, 0.30, 3, NULL, NULL, 0.00, 'FINALIZADA', NULL, NULL, NULL);

