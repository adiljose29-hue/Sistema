import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import mysql.connector
from mysql.connector import pooling
from datetime import datetime
import logging
import configparser
import os
import threading
import queue
import time
from typing import Dict, List, Optional, Tuple
import json

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_vendas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = self.config_manager._carregar_config()
        self.connection_pool = self._criar_pool()
        self.ponto_venda_id = self._obter_id_ponto_venda()
    
    def _obter_id_ponto_venda(self) -> int:
        """Obtém o ID do ponto de venda atual da base de dados"""
        try:
            pdv_config = self.config_manager.obter_ponto_venda_atual()
            nome_pdv = pdv_config['nome']
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM pontos_venda WHERE nome = %s", (nome_pdv,))
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    # Criar ponto de venda se não existir
                    cursor.execute("""
                        INSERT INTO pontos_venda (nome, localizacao, impressora) 
                        VALUES (%s, %s, %s)
                    """, (nome_pdv, pdv_config['localizacao'], pdv_config['impressora']))
                    conn.commit()
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Erro ao obter ID do ponto de venda: {e}")
            return 1  # ID padrão
    
    def verificar_login_multiplo(self, usuario_id: int) -> Tuple[bool, Optional[str]]:
        """Verifica se o usuário já está logado em outro PDV"""
        try:
            bloquear_multiplo = self.config_manager.getboolean('SYSTEM', 'bloquear_login_multiplo', True)
            
            if not bloquear_multiplo:
                return False, None
            
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT pv.nome, su.data_login 
                    FROM sessoes_usuarios su
                    JOIN pontos_venda pv ON su.ponto_venda_id = pv.id
                    WHERE su.usuario_id = %s AND su.ativa = TRUE AND su.ponto_venda_id != %s
                    ORDER BY su.data_ultima_acao DESC 
                    LIMIT 1
                """, (usuario_id, self.ponto_venda_id))
                
                sessao_ativa = cursor.fetchone()
                
                if sessao_ativa:
                    mensagem = f"Usuário já está logado no {sessao_ativa['nome']} desde {sessao_ativa['data_login']}"
                    return True, mensagem
            
            return False, None
            
        except Exception as e:
            logger.error(f"Erro ao verificar login múltiplo: {e}")
            return False, None
    
    def registrar_sessao(self, usuario_id: int, endereco_ip: str = None) -> str:
        """Registra nova sessão de usuário"""
        try:
            token_sessao = f"SESSION_{usuario_id}_{int(time.time())}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Desativar sessões antigas do mesmo usuário no mesmo PDV
                cursor.execute("""
                    UPDATE sessoes_usuarios 
                    SET ativa = FALSE 
                    WHERE usuario_id = %s AND ponto_venda_id = %s
                """, (usuario_id, self.ponto_venda_id))
                
                # Inserir nova sessão
                cursor.execute("""
                    INSERT INTO sessoes_usuarios 
                    (usuario_id, ponto_venda_id, data_login, data_ultima_acao, endereco_ip, token_sessao)
                    VALUES (%s, %s, NOW(), NOW(), %s, %s)
                """, (usuario_id, self.ponto_venda_id, endereco_ip, token_sessao))
                
                conn.commit()
            
            logger.info(f"Sessão registrada para usuário {usuario_id} no PDV {self.ponto_venda_id}")
            return token_sessao
            
        except Exception as e:
            logger.error(f"Erro ao registrar sessão: {e}")
            return ""
    
    def atualizar_ultima_acao(self, token_sessao: str):
        """Atualiza data da última ação da sessão"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessoes_usuarios 
                    SET data_ultima_acao = NOW() 
                    WHERE token_sessao = %s AND ativa = TRUE
                """, (token_sessao,))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Erro ao atualizar última ação: {e}")
    
    def encerrar_sessao(self, token_sessao: str):
        """Encerra sessão do usuário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessoes_usuarios 
                    SET ativa = FALSE, data_ultima_acao = NOW() 
                    WHERE token_sessao = %s
                """, (token_sessao,))
                conn.commit()
            
            logger.info(f"Sessão {token_sessao} encerrada")
                
        except Exception as e:
            logger.error(f"Erro ao encerrar sessão: {e}")
    
    def limpar_sessoes_expiradas(self, tempo_expiracao_minutos: int = 60):
        """Limpa sessões expiradas"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessoes_usuarios 
                    SET ativa = FALSE 
                    WHERE ativa = TRUE AND 
                    TIMESTAMPDIFF(MINUTE, data_ultima_acao, NOW()) > %s
                """, (tempo_expiracao_minutos,))
                
                sessoes_afetadas = cursor.rowcount
                conn.commit()
                
                if sessoes_afetadas > 0:
                    logger.info(f"{sessoes_afetadas} sessões expiradas limpas")
                    
        except Exception as e:
            logger.error(f"Erro ao limpar sessões expiradas: {e}")
    
    def _obter_id_ponto_venda(self) -> int:
        """Obtém o ID do ponto de venda atual"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pontos_venda (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        nome VARCHAR(100) NOT NULL,
                        localizacao VARCHAR(200),
                        impressora VARCHAR(100),
                        ativo BOOLEAN DEFAULT TRUE,
                        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Inserir ponto de venda padrão se não existir
                cursor.execute("SELECT COUNT(*) FROM pontos_venda")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT INTO pontos_venda (nome, localizacao, impressora) 
                        VALUES (%s, %s, %s)
                    """, ('PDV Principal', 'Loja Central', 'USB001'))
                    conn.commit()
                
                # Obter ID do ponto de venda atual
                nome_pdv = self.config_manager.get('SYSTEM', 'ponto_venda', 'PDV Principal')
                cursor.execute("SELECT id FROM pontos_venda WHERE nome = %s", (nome_pdv,))
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    # Criar novo ponto de venda
                    cursor.execute("""
                        INSERT INTO pontos_venda (nome, localizacao, impressora) 
                        VALUES (%s, %s, %s)
                    """, (nome_pdv, 'Localização não definida', 'USB001'))
                    conn.commit()
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Erro ao obter ID do ponto de venda: {e}")
            return 1  # ID padrão
    
    def _carregar_config(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        if os.path.exists('config.ini'):
            config.read('config.ini')
        else:
            self._criar_config_padrao(config)
        return config
           
    def _criar_pool(self) -> pooling.MySQLConnectionPool:
        try:
            return mysql.connector.pooling.MySQLConnectionPool(
                pool_name="vendas_pool",
                pool_size=int(self.config['DATABASE']['pool_size']),
                **dict(self.config['DATABASE'])
            )
        except Exception as e:
            logger.error(f"Erro ao criar pool de conexões: {e}")
            raise
    
    def get_connection(self):
        """Obtém conexão do pool"""
        return self.connection_pool.get_connection()

class CacheProdutos:
    """Cache inteligente para produtos"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.produtos_cache = {}
        self.categorias_cache = {}
        self.ultima_atualizacao = 0
        self.tempo_cache = 300  # 5 minutos
        
    def obter_produto_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Obtém produto do cache ou banco de dados"""
        agora = time.time()
        
        # Verificar se precisa atualizar cache
        if agora - self.ultima_atualizacao > self.tempo_cache:
            self._atualizar_cache()
        
        # Buscar no cache
        produto = self.produtos_cache.get(codigo)
        if produto:
            logger.debug(f"Produto {codigo} encontrado no cache")
            return produto
        
        # Buscar no banco
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT p.*, c.nome as categoria, i.taxa as iva_taxa
                    FROM produtos p 
                    LEFT JOIN categorias c ON p.categoria_id = c.id
                    LEFT JOIN iva i ON p.iva_id = i.id
                    WHERE p.codigo = %s AND p.ativo = TRUE
                """, (codigo,))
                produto = cursor.fetchone()
                
                if produto:
                    self.produtos_cache[codigo] = produto
                    logger.info(f"Produto {codigo} carregado do banco")
                
                return produto
        except Exception as e:
            logger.error(f"Erro ao buscar produto {codigo}: {e}")
            return None
    
    def _atualizar_cache(self):
        """Atualiza o cache completo"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT p.*, c.nome as categoria, i.taxa as iva_taxa
                    FROM produtos p 
                    LEFT JOIN categorias c ON p.categoria_id = c.id
                    LEFT JOIN iva i ON p.iva_id = i.id
                    WHERE p.ativo = TRUE
                """)
                produtos = cursor.fetchall()
                
                self.produtos_cache.clear()
                for produto in produtos:
                    self.produtos_cache[produto['codigo']] = produto
                
                self.ultima_atualizacao = time.time()
                logger.info("Cache de produtos atualizado")
                
        except Exception as e:
            logger.error(f"Erro ao atualizar cache: {e}")

class ProcessadorTeclas:
    """Processador otimizado de teclas"""
    
    def __init__(self):
        self.buffer = ""
        self.modo = "normal"  # normal, quantidade, pagamento, login, consulta, supervisor
        self.callbacks = {}
    
    def registrar_callback(self, modo: str, callback):
        """Registra callback para modo específico"""
        self.callbacks[modo] = callback
    
    def processar_tecla(self, tecla: str):
        """Processa tecla pressionada"""
        if self.modo in self.callbacks:
            return self.callbacks[self.modo](tecla)
        return False
    
    def limpar_buffer(self):
        """Limpa buffer de entrada"""
        self.buffer = ""
    
    def set_modo(self, modo: str):
        """Altera modo de operação"""
        self.modo = modo
        self.limpar_buffer()

class ImpressoraManager:
    """Gerenciador de impressão"""
    
    def __init__(self, config: configparser.ConfigParser):
        self.config = config
        self.printer_type = config['PRINTER']['type']
    
    def imprimir_recibo(self, dados_venda: Dict):
        """Imprime recibo da venda"""
        try:
            recibo = self._formatar_recibo(dados_venda)
            
            if self.printer_type == 'windows':
                self._imprimir_windows(recibo)
            elif self.printer_type == 'file':
                self._imprimir_arquivo(recibo)
            
            logger.info("Recibo impresso com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao imprimir recibo: {e}")
            raise
    
    def _formatar_recibo(self, dados_venda: Dict) -> str:
        """Formata recibo conforme configuração"""
        recibo = []
        
        # Cabeçalho
        if self.config.getboolean('RECEIPT', 'logo_enabled', fallback=False):
            recibo.append("[LOGO]")
        
        recibo.append(self.config['RECEIPT']['header'])
        recibo.append("=" * 40)
        
        # Itens
        for item in dados_venda['itens']:
            recibo.append(f"{item['nome'][:30]}")
            recibo.append(f"{item['quantidade']} x {self._formatar_moeda(item['preco'])}")
            recibo.append(f"Subtotal: {self._formatar_moeda(item['subtotal'])}")
            recibo.append("-" * 20)
        
        # Totais
        recibo.append(f"TOTAL: {self._formatar_moeda(dados_venda['total'])}")
        recibo.append(f"IVA: {self._formatar_moeda(dados_venda['total_iva'])}")
        
        if dados_venda['forma_pagamento']:
            recibo.append(f"Pagamento: {dados_venda['forma_pagamento']}")
            if dados_venda['valor_pago']:
                recibo.append(f"Valor Pago: {self._formatar_moeda(dados_venda['valor_pago'])}")
            if dados_venda['troco']:
                recibo.append(f"Troco: {self._formatar_moeda(dados_venda['troco'])}")
        
        # Rodapé
        recibo.append("=" * 40)
        recibo.append(self.config['RECEIPT']['footer'])
        recibo.append(dados_venda['data_hora'])
        
        # Comandos de impressora
        if self.config.getboolean('PRINTER', 'cutter_enabled', fallback=True):
            recibo.append("\n" * 5)  # Avançar papel para corte
            recibo.append("\x1B\x69")  # Comando corte (ESC i)
        
        if self.config.getboolean('PRINTER', 'drawer_enabled', fallback=True):
            recibo.append("\x1B\x70\x00\x19\xFA")  # Abrir gaveta
        
        return "\n".join(recibo)
    
    def _formatar_moeda(self, valor: float) -> str:
        """Formata valor em moeda Kz"""
        return f"{valor:,.2f} {self.config['RECEIPT']['currency']}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def _imprimir_windows(self, texto: str):
        """Imprime no Windows"""
        import win32print
        import win32api
        
        printer_name = self.config['PRINTER']['port']
        hprinter = win32print.OpenPrinter(printer_name)
        
        try:
            win32print.StartDocPrinter(hprinter, 1, ("Recibo Venda", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, texto.encode('utf-8'))
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
    
    def _imprimir_arquivo(self, texto: str):
        """Imprime em arquivo"""
        with open("recibo.txt", "w", encoding="utf-8") as f:
            f.write(texto)

import configparser
import os
from typing import Any, Dict, Optional

class ConfigManager:
    """Gerenciador avançado de configurações do sistema"""
    
    def __init__(self, config_file: str = 'config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._carregar_configuracao()
    
    def _carregar_configuracao(self):
        """Carrega a configuração do ficheiro ou cria padrão"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self._criar_configuracao_padrao()
            self.salvar_configuracao()
    
    def _criar_configuracao_padrao(self):
        """Cria configuração padrão para Angola"""
        # Seção DATABASE
        self.config['DATABASE'] = {
            'host': 'localhost',
            'user': 'root', 
            'password': '',
            'database': 'bd_stop',
            'pool_size': '5',
            'pool_reset_session': 'True',
            'charset': 'utf8mb4'
        }
        
        # Seção PRINTER
        self.config['PRINTER'] = {
            'type': 'windows',
            'port': 'USB001',
            'cutter_enabled': 'True',
            'drawer_enabled': 'True',
            'open_drawer_command': r'\x1B\x70\x00\x19\xFA',
            'cut_command': r'\x1B\x69',
            'line_feed': '5',
            'characters_per_line': '42',
            'encoding': 'utf-8'
        }
        
        # Seção RECEIPT
        self.config['RECEIPT'] = {
            'header': 'LOJA STOP - ANGOLA',
            'subheader': 'Sistema de Vendas Professional',
            'footer': 'Obrigado pela preferência!',
            'currency': 'Kz',
            'logo_enabled': 'False',
            'logo_path': 'logo.bmp',
            'center_content': 'True',
            'bold_headers': 'True',
            'print_date': 'True',
            'print_vat': 'True',
            'print_barcode': 'False'
        }
        
        # Seção SYSTEM
        self.config['SYSTEM'] = {
            'language': 'pt',
            'country': 'AO', 
            'currency_symbol': 'Kz',
            'decimal_separator': ',',
            'thousands_separator': '.',
            'enable_scanner': 'True',
            'scanner_delay': '0.5',
            'auto_login': 'False',
            'session_timeout': '3600',
            'backup_interval': '24',
            'log_level': 'INFO',
            'ponto_venda': 'PDV Principal',
            'bloquear_login_multiplo': 'True'
        }
        
        # Seção COMPANY
        self.config['COMPANY'] = {
            'name': 'Loja STOP Comércio Geral Lda',
            'address': 'Rua Comandante Gika, Nº 123, Luanda',
            'phone': '+244 923 456 789',
            'email': 'info@stopangola.com',
            'tax_id': '54123456789',
            'website': 'www.stopangola.com'
        }
        # Nova seção PONTOS_VENDA
        self.config['PONTOS_VENDA'] = {
            'pdv_principal': 'PDV Principal|USB001|Loja Central',
            'pdv_secundario': 'PDV Secundário|USB002|Piso 1',
            'pdv_restauracao': 'PDV Restauração|USB003|Piso 2'
        }
        # Seção TAX
        self.config['TAX'] = {
            'vat_enabled': 'True',
            'default_vat_rate': '14',
            'vat_inclusive': 'True',
            'round_tax': 'True',
            'tax_rounding': 'commercial'
        }
        
        # Seção SECURITY
        self.config['SECURITY'] = {
            'admin_password': 'admin123',
            'supervisor_password': 'supervisor123',
            'max_login_attempts': '3',
            'lockout_time': '900',
            'password_expiry': '90',
            'session_timeout': '1800',
            'log_sensitive_operations': 'True'
        }
    
    def salvar_configuracao(self):
        """Salva a configuração atual no ficheiro"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def obter_pontos_venda(self) -> List[Dict[str, str]]:
        """Obtém lista de pontos de venda da configuração"""
        pontos_venda = []
        try:
            for key, value in self.config['PONTOS_VENDA'].items():
                partes = value.split('|')
                if len(partes) >= 3:
                    pontos_venda.append({
                        'id': key,
                        'nome': partes[0],
                        'impressora': partes[1],
                        'localizacao': partes[2]
                    })
        except (KeyError, configparser.NoSectionError):
            # Retornar pontos padrão se a secção não existir
            pontos_venda = [
                {'id': 'pdv_principal', 'nome': 'PDV Principal', 'impressora': 'USB001', 'localizacao': 'Loja Central'},
                {'id': 'pdv_secundario', 'nome': 'PDV Secundário', 'impressora': 'USB002', 'localizacao': 'Piso 1'}
            ]
        
        return pontos_venda
    
    def obter_ponto_venda_atual(self) -> Dict[str, str]:
        """Obtém configuração do ponto de venda atual"""
        nome_pdv = self.get('SYSTEM', 'ponto_venda', 'PDV Principal')
        pontos = self.obter_pontos_venda()
        
        for pdv in pontos:
            if pdv['nome'] == nome_pdv:
                return pdv
        
        # Retornar o primeiro se não encontrar
        return pontos[0] if pontos else {'nome': 'PDV Principal', 'impressora': 'USB001', 'localizacao': 'Loja Central'}
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Obtém um valor de configuração"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def getboolean(self, section: str, key: str, default: bool = False) -> bool:
        """Obtém um valor booleano"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def getint(self, section: str, key: str, default: int = 0) -> int:
        """Obtém um valor inteiro"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def getfloat(self, section: str, key: str, default: float = 0.0) -> float:
        """Obtém um valor float"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Define um valor de configuração"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = str(value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Obtém uma secção completa como dicionário"""
        try:
            return dict(self.config[section])
        except KeyError:
            return {}
    
    def update_section(self, section: str, values: Dict[str, Any]):
        """Atualiza uma secção completa"""
        if section not in self.config:
            self.config[section] = {}
        
        for key, value in values.items():
            self.config[section][key] = str(value)
    
    def validate_config(self) -> bool:
        """Valida a configuração atual"""
        required_sections = ['DATABASE', 'PRINTER', 'RECEIPT', 'SYSTEM']
        
        for section in required_sections:
            if section not in self.config:
                return False
        
        # Validar configurações essenciais
        essential_settings = [
            ('DATABASE', 'host'),
            ('DATABASE', 'database'),
            ('PRINTER', 'type'),
            ('RECEIPT', 'currency'),
            ('SYSTEM', 'language')
        ]
        
        for section, key in essential_settings:
            if not self.get(section, key):
                return False
        
        return True
    
    def backup_config(self, backup_path: str = None):
        """Cria backup da configuração"""
        if backup_path is None:
            backup_path = f"{self.config_file}.backup"
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def restore_config(self, backup_path: str):
        """Restaura configuração de backup"""
        if os.path.exists(backup_path):
            self.config.read(backup_path, encoding='utf-8')
            self.salvar_configuracao()
            return True
        return False
class ConfigManager:
    """Gerenciador avançado de configurações do sistema"""
    
    def __init__(self, config_file: str = 'config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        # Corrigir problema de encoding
        self._carregar_configuracao()
    
    def _carregar_configuracao(self):
        """Carrega a configuração do ficheiro ou cria padrão"""
        try:
            if os.path.exists(self.config_file):
                # Tentar diferentes encodings
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        with open(self.config_file, 'r', encoding=encoding) as f:
                            content = f.read()
                        self.config.read_string(content)
                        logger.info(f"Configuração carregada com encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Se nenhum encoding funcionar, criar novo
                    logger.warning("Não foi possível ler o ficheiro de configuração. Criando novo.")
                    self._criar_configuracao_padrao()
            else:
                self._criar_configuracao_padrao()
                self.salvar_configuracao()
                
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            self._criar_configuracao_padrao()

# Exemplo de uso no sistema principal
class SistemaVendasProfissional:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Vendas Professional - STOP")
        self.root.geometry("1300x900")
        self.root.configure(bg='#2c3e50')
        
        # Inicializar componentes
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager(self.config_manager)
        self.cache_produtos = CacheProdutos(self.db_manager)
        self.processador_teclas = ProcessadorTeclas()
        self.impressora = ImpressoraManager(self.config_manager)
        
        # Estado do sistema
        self.usuario_logado = None
        self.token_sessao = None
        self.venda_atual = []
        self.modo_operacao = "normal"
        self.ponto_venda_atual = self.config_manager.obter_ponto_venda_atual()
        self.config = self.config_manager
        
        # Variáveis de interface
        self.display_text = tk.StringVar(value="Sistema de Vendas STOP - Faça login")
        self.total_var = tk.StringVar(value="Kz 0,00")
        self.operacao_var = tk.StringVar(value="Aguardando login...")
        self.valor_pago_var = tk.StringVar(value="Kz 0,00")
        self.troco_var = tk.StringVar(value="Kz 0,00")
        self.ponto_venda_var = tk.StringVar(value=f"PDV: {self.ponto_venda_atual['nome']}")
        
        # Configurar processador de teclas
        self._configurar_processador_teclas()
        
        # Criar interface
        self.criar_interface()
        
        # Limpar sessões expiradas ao iniciar
        self.db_manager.limpar_sessoes_expiradas()
        
        # Bloquear sistema até login
        self.bloquear_sistema()
        
        # Agendar atualização periódica da sessão
        self._agendar_atualizacao_sessao()
        
        logger.info(f"Sistema de vendas inicializado - Ponto de Venda: {self.ponto_venda_atual['nome']}")
    
    def _agendar_atualizacao_sessao(self):
        """Agenda atualização periódica da sessão"""
        if self.token_sessao:
            self.db_manager.atualizar_ultima_acao(self.token_sessao)
        
        # Agendar próxima atualização em 1 minuto
        self.root.after(60000, self._agendar_atualizacao_sessao)
    
    def fazer_login(self, credencial: str):
        """Realiza login do usuário com verificação de múltiplos logins"""
        try:
            if len(credencial) < 4:
                messagebox.showerror("Erro", "Número de trabalhador inválido!")
                return
            
            numero_trabalhador = credencial
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, nome, nivel FROM usuarios 
                    WHERE numero_trabalhador = %s AND ativo = TRUE
                """, (numero_trabalhador,))
                usuario = cursor.fetchone()
            
            if usuario:
                # Verificar se já está logado em outro PDV
                bloqueado, mensagem = self.db_manager.verificar_login_multiplo(usuario['id'])
                
                if bloqueado:
                    messagebox.showerror("Login Bloqueado", 
                                       f"{mensagem}\n\nNão é possível fazer login em múltiplos pontos de venda simultaneamente.")
                    logger.warning(f"Tentativa de login múltiplo para usuário {usuario['nome']}")
                    return
                
                # Registrar nova sessão
                self.token_sessao = self.db_manager.registrar_sessao(usuario['id'])
                
                if self.token_sessao:
                    self.usuario_logado = usuario
                    self.usuario_label.config(text=f"Usuário: {usuario['nome']} ({usuario['nivel']})")
                    self.processador_teclas.set_modo('normal')
                    self.operacao_var.set("Sistema liberado - Pronto para vender")
                    self.display_text.set(f"Bem-vindo, {usuario['nome']}!")
                    
                    logger.info(f"Usuário {usuario['nome']} fez login com sucesso no PDV {self.ponto_venda_atual['nome']}")
                else:
                    messagebox.showerror("Erro", "Falha ao criar sessão!")
                    
            else:
                messagebox.showerror("Erro", "Usuário não encontrado!")
                logger.warning(f"Tentativa de login com número inválido: {numero_trabalhador}")
                
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            messagebox.showerror("Erro", "Falha no sistema de login!")
    
    def fazer_logout(self):
        """Realiza logout do usuário"""
        try:
            if self.token_sessao:
                self.db_manager.encerrar_sessao(self.token_sessao)
                self.token_sessao = None
            
            self.usuario_logado = None
            self.usuario_label.config(text="Não logado")
            self.venda_atual.clear()
            self.atualizar_display_venda()
            
            self.processador_teclas.set_modo('login')
            self.operacao_var.set("Digite número de trabalhador + Enter")
            self.display_text.set("Sessão encerrada - Faça login")
            
            logger.info("Logout realizado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao fazer logout: {e}")
    
    def trocar_ponto_venda(self):
        """Permite trocar o ponto de venda atual"""
        if not self.usuario_logado or self.usuario_logado['nivel'] not in ['admin', 'gerente']:
            messagebox.showerror("Acesso Negado", 
                               "Apenas administradores e gerentes podem trocar PDV!")
            return
        
        # Verificar se há venda em andamento
        if self.venda_atual:
            resposta = messagebox.askyesno(
                "Venda em Andamento", 
                "Existe uma venda em andamento. Deseja cancelá-la antes de trocar de PDV?"
            )
            if resposta:
                self.venda_atual.clear()
                self.atualizar_display_venda()
            else:
                return
        
        # Janela de seleção de PDV
        pdv_window = tk.Toplevel(self.root)
        pdv_window.title("Selecionar Ponto de Venda")
        pdv_window.geometry("400x300")
        pdv_window.configure(bg='#34495e')
        pdv_window.transient(self.root)
        pdv_window.grab_set()
        
        tk.Label(pdv_window, text="SELECIONAR PONTO DE VENDA", 
                font=('Arial', 14, 'bold'), bg='#34495e', fg='#ecf0f1').pack(pady=10)
        
        # Obter pontos de venda da configuração
        pontos_venda = self.config_manager.obter_pontos_venda()
        
        # Lista de PDVs
        pdv_frame = tk.Frame(pdv_window, bg='#34495e')
        pdv_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        for pdv in pontos_venda:
            btn_text = f"{pdv['nome']}\n{pdv['localizacao']} - {pdv['impressora']}"
            btn = tk.Button(pdv_frame, text=btn_text, font=('Arial', 10),
                           bg='#3498db', fg='white', height=2, width=30,
                           command=lambda p=pdv: self._selecionar_pdv(p, pdv_window))
            btn.pack(pady=2)
    
    def _selecionar_pdv(self, pdv: dict, window: tk.Toplevel):
        """Seleciona um ponto de venda específico"""
        try:
            # Fazer logout se estiver logado
            if self.usuario_logado:
                self.fazer_logout()
            
            # Atualizar configuração
            self.config_manager.set('SYSTEM', 'ponto_venda', pdv['nome'])
            self.config_manager.salvar_configuracao()
            
            # Reinicializar database manager para atualizar PDV
            self.db_manager = DatabaseManager(self.config_manager)
            
            # Atualizar estado do sistema
            self.ponto_venda_atual = pdv
            self.ponto_venda_var.set(f"PDV: {pdv['nome']}")
            
            # Fechar janela
            window.destroy()
            
            # Mostrar confirmação
            self.display_text.set(f"PDV alterado para: {pdv['nome']}")
            self.operacao_var.set("Faça login no novo ponto de venda")
            
            logger.info(f"Ponto de venda alterado para: {pdv['nome']}")
            
        except Exception as e:
            logger.error(f"Erro ao selecionar PDV: {e}")
            messagebox.showerror("Erro", "Falha ao alterar ponto de venda!")
    
    def __del__(self):
        """Destrutor - garante que a sessão seja encerrada"""
        if hasattr(self, 'token_sessao') and self.token_sessao:
            self.db_manager.encerrar_sessao(self.token_sessao)
    
    def _configurar_processador_teclas(self):
        """Configura callbacks do processador de teclas"""
        self.processador_teclas.registrar_callback('normal', self._processar_tecla_normal)
        self.processador_teclas.registrar_callback('quantidade', self._processar_tecla_quantidade)
        self.processador_teclas.registrar_callback('pagamento', self._processar_tecla_pagamento)
        self.processador_teclas.registrar_callback('login', self._processar_tecla_login)
        self.processador_teclas.registrar_callback('consulta', self._processar_tecla_consulta)
        self.processador_teclas.registrar_callback('supervisor', self._processar_tecla_supervisor)
    
    def criar_interface(self):
        """Cria interface completa do sistema"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header
        self.criar_header(main_frame)
        
        # Corpo principal
        body_frame = tk.Frame(main_frame, bg='#2c3e50')
        body_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Painel esquerdo - Produtos
        left_panel = tk.Frame(body_frame, bg='#34495e', relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Painel direito - Teclado e controles
        right_panel = tk.Frame(body_frame, bg='#34495e', relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.criar_painel_produtos(left_panel)
        self.criar_painel_direito(right_panel)
    
    def _obter_ponto_venda(self) -> str:
        """Obtém o ponto de venda atual da configuração"""
        return self.config_manager.get('SYSTEM', 'ponto_venda', 'PDV Principal')
    
    def criar_header(self, parent):
        """Cria cabeçalho com informações do sistema e PDV"""
        header_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Título e informações
        title_frame = tk.Frame(header_frame, bg='#34495e')
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Lado esquerdo - Título
        left_frame = tk.Frame(title_frame, bg='#34495e')
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(left_frame, text="SISTEMA DE VENDAS PROFISSIONAL - STOP", 
                font=('Arial', 16, 'bold'), bg='#34495e', fg='#ecf0f1').pack(anchor=tk.W)
        
        tk.Label(left_frame, textvariable=self.ponto_venda_var,
                font=('Arial', 12, 'bold'), bg='#34495e', fg='#3498db').pack(anchor=tk.W)
        
        # Lado direito - Informações do usuário e data
        right_frame = tk.Frame(title_frame, bg='#34495e')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.usuario_label = tk.Label(right_frame, text="Não logado", 
                                     font=('Arial', 10), bg='#34495e', fg='#bdc3c7')
        self.usuario_label.pack(anchor=tk.E)
        
        self.time_label = tk.Label(right_frame, font=('Arial', 10), 
                                  bg='#34495e', fg='#bdc3c7')
        self.time_label.pack(anchor=tk.E)
        self.atualizar_relogio()
          
    
    
    def gerenciar_pontos_venda(self):
        """Interface para gerenciar pontos de venda (apenas admin)"""
        if not self.usuario_logado or self.usuario_logado['nivel'] != 'admin':
            messagebox.showerror("Acesso Negado", 
                               "Apenas administradores podem gerir pontos de venda!")
            return
        
        gerenciar_window = tk.Toplevel(self.root)
        gerenciar_window.title("Gerir Pontos de Venda")
        gerenciar_window.geometry("600x500")
        gerenciar_window.configure(bg='#34495e')
        gerenciar_window.transient(self.root)
        gerenciar_window.grab_set()
        
        # Frame principal com scroll
        main_frame = tk.Frame(gerenciar_window, bg='#34495e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        tk.Label(main_frame, text="GERIR PONTOS DE VENDA", 
                font=('Arial', 16, 'bold'), bg='#34495e', fg='#ecf0f1').pack(pady=10)
        
        # Botão para adicionar novo PDV
        btn_adicionar = tk.Button(main_frame, text="+ Adicionar Novo PDV", 
                                 font=('Arial', 12, 'bold'), bg='#27ae60', fg='white',
                                 command=self._adicionar_ponto_venda)
        btn_adicionar.pack(fill=tk.X, pady=5)
        
        # Lista de PDVs existentes
        self._carregar_lista_pontos_venda(main_frame)
    
    def _carregar_lista_pontos_venda(self, parent):
        """Carrega lista de pontos de venda para gestão"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, nome, localizacao, impressora, ativo 
                    FROM pontos_venda 
                    ORDER BY nome
                """)
                pontos_venda = cursor.fetchall()
        except Exception as e:
            logger.error(f"Erro ao carregar pontos de venda: {e}")
            pontos_venda = []
        
        # Frame para lista com scroll
        lista_frame = tk.Frame(parent, bg='#2c3e50')
        lista_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        canvas = tk.Canvas(lista_frame, bg='#2c3e50', highlightthickness=0)
        scrollbar = ttk.Scrollbar(lista_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2c3e50')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Adicionar PDVs à lista
        for pdv in pontos_venda:
            self._criar_item_ponto_venda(scrollable_frame, pdv)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _criar_item_ponto_venda(self, parent, pdv: dict):
        """Cria item da lista para um ponto de venda"""
        item_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=1)
        item_frame.pack(fill=tk.X, pady=2, padx=5)
        
        # Informações do PDV
        info_frame = tk.Frame(item_frame, bg='#34495e')
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
        
        nome_label = tk.Label(info_frame, text=pdv['nome'], 
                             font=('Arial', 11, 'bold'), bg='#34495e', fg='#ecf0f1')
        nome_label.pack(anchor=tk.W)
        
        local_label = tk.Label(info_frame, text=pdv['localizacao'], 
                              font=('Arial', 9), bg='#34495e', fg='#bdc3c7')
        local_label.pack(anchor=tk.W)
        
        impressora_label = tk.Label(info_frame, text=f"Impressora: {pdv['impressora']}", 
                                   font=('Arial', 8), bg='#34495e', fg='#95a5a6')
        impressora_label.pack(anchor=tk.W)
        
        # Botões de ação
        botoes_frame = tk.Frame(item_frame, bg='#34495e')
        botoes_frame.pack(side=tk.RIGHT, padx=5)
        
        if pdv['ativo']:
            estado_btn = tk.Button(botoes_frame, text="Desativar", 
                                  font=('Arial', 8), bg='#e74c3c', fg='white',
                                  command=lambda: self._alterar_estado_pdv(pdv['id'], False))
        else:
            estado_btn = tk.Button(botoes_frame, text="Ativar", 
                                  font=('Arial', 8), bg='#27ae60', fg='white',
                                  command=lambda: self._alterar_estado_pdv(pdv['id'], True))
        
        estado_btn.pack(side=tk.LEFT, padx=2)
        
        editar_btn = tk.Button(botoes_frame, text="Editar", 
                              font=('Arial', 8), bg='#3498db', fg='white',
                              command=lambda: self._editar_ponto_venda(pdv))
        editar_btn.pack(side=tk.LEFT, padx=2)
    
    def _adicionar_ponto_venda(self):
        """Adiciona novo ponto de venda"""
        # Implementar interface para adicionar novo PDV
        pass
    
    def _editar_ponto_venda(self, pdv: dict):
        """Edita ponto de venda existente"""
        # Implementar interface para editar PDV
        pass
    
    def _alterar_estado_pdv(self, pdv_id: int, ativo: bool):
        """Ativa/desativa ponto de venda"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE pontos_venda SET ativo = %s WHERE id = %s", 
                             (ativo, pdv_id))
                conn.commit()
            
            # Recarregar lista
            messagebox.showinfo("Sucesso", "Estado do ponto de venda alterado!")
            logger.info(f"PDV {pdv_id} {'ativado' if ativo else 'desativado'}")
            
        except Exception as e:
            logger.error(f"Erro ao alterar estado do PDV: {e}")
            messagebox.showerror("Erro", "Falha ao alterar estado do ponto de venda!")
    
    def criar_painel_produtos(self, parent):
        """Cria painel de produtos com categorias"""
        # Frame de categorias
        cat_frame = tk.Frame(parent, bg='#34495e')
        cat_frame.pack(fill=tk.X, padx=10, pady=5)
        
        categorias = ["Todos", "Alimentos", "Laticínios", "Limpeza", "Higiene", "Bebidas", "Padaria"]
        for cat in categorias:
            btn = tk.Button(cat_frame, text=cat, font=('Arial', 9, 'bold'),
                           bg='#3498db', fg='white', height=1, width=10,
                           command=lambda c=cat: self.filtrar_produtos(c))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Display principal
        display_frame = tk.Frame(parent, bg='#2c3e50')
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        
        display_label = tk.Label(display_frame, textvariable=self.display_text,
                                font=('Arial', 14), bg='#1a252f', fg='#2ecc71',
                                height=2, anchor=tk.W, padx=10)
        display_label.pack(fill=tk.X)
        
        # Treeview dos itens
        tree_frame = tk.Frame(parent, bg='#34495e')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('produto', 'qtd', 'preco', 'subtotal', 'iva')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)
        
        # Configurar colunas
        col_configs = [
            ('PRODUTO', 300),
            ('QTD', 80),
            ('PREÇO UNIT.', 120),
            ('SUBTOTAL', 120),
            ('IVA', 80)
        ]
        
        for col, (heading, width) in zip(columns, col_configs):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Frame de totais
        totais_frame = tk.Frame(parent, bg='#34495e')
        totais_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(totais_frame, text="TOTAL:", font=('Arial', 14, 'bold'),
                bg='#34495e', fg='#ecf0f1').pack(side=tk.LEFT)
        
        tk.Label(totais_frame, textvariable=self.total_var, font=('Arial', 16, 'bold'),
                bg='#34495e', fg='#2ecc71').pack(side=tk.RIGHT)
        
        # Botões de produtos
        self.criar_botoes_produtos(parent)
    
    def criar_botoes_produtos(self, parent):
        """Cria grid de botões de produtos"""
        produtos_frame = tk.Frame(parent, bg='#34495e')
        produtos_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Buscar produtos do cache
        produtos = list(self.cache_produtos.produtos_cache.values())[:12]  # Limitar a 12 produtos
        
        # Criar botões em grid 4x3
        for i, produto in enumerate(produtos):
            row, col = i // 3, i % 3
            btn_text = f"{produto['nome'][:20]}\nKz {produto['preco']:.2f}"
            btn = tk.Button(produtos_frame, text=btn_text, font=('Arial', 8),
                           bg='#3498db', fg='white', height=3, width=18,
                           command=lambda p=produto: self.adicionar_produto(p['codigo']))
            btn.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
        
        # Configurar grid
        for i in range(4):
            produtos_frame.rowconfigure(i, weight=1)
        for i in range(3):
            produtos_frame.columnconfigure(i, weight=1)
    
    def criar_painel_direito(self, parent):
        """Cria painel direito com teclado e controles"""
        # Display de operação
        op_frame = tk.Frame(parent, bg='#2c3e50')
        op_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(op_frame, textvariable=self.operacao_var, font=('Arial', 11),
                bg='#2c3e50', fg='#ecf0f1').pack()
        
        # Teclado numérico com scrollbar
        teclado_container = tk.Frame(parent, bg='#34495e')
        teclado_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(teclado_container, bg='#34495e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(teclado_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#34495e')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self.criar_teclado_numerico(scrollable_frame)
        self.criar_botoes_controle(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Informações de pagamento
        self.criar_info_pagamento(parent)
    
    def criar_teclado_numerico(self, parent):
        """Cria teclado numérico otimizado"""
        teclado_frame = tk.Frame(parent, bg='#34495e')
        teclado_frame.pack(fill=tk.X, pady=5)
        
        botoes = [
            ('7', '#2c3e50'), ('8', '#2c3e50'), ('9', '#2c3e50'),
            ('4', '#2c3e50'), ('5', '#2c3e50'), ('6', '#2c3e50'),
            ('1', '#2c3e50'), ('2', '#2c3e50'), ('3', '#2c3e50'),
            ('0', '#2c3e50', 2), ('.', '#2c3e50'),
            ('X', '#e67e22'), ('⌫', '#e74c3c'), ('Enter', '#27ae60')
        ]
        
        for i, btn_info in enumerate(botoes):
            row, col = i // 3, i % 3
            
            if len(btn_info) == 3:
                texto, cor, colspan = btn_info
            else:
                texto, cor = btn_info
                colspan = 1
            
            btn = tk.Button(teclado_frame, text=texto, font=('Arial', 12, 'bold'),
                           bg=cor, fg='white', height=2, width=6,
                           command=lambda t=texto: self.processador_teclas.processar_tecla(t))
            btn.grid(row=row, column=col, columnspan=colspan, 
                    padx=2, pady=2, sticky='nsew')
        
        # Configurar grid
        for i in range(4):
            teclado_frame.rowconfigure(i, weight=1)
        for i in range(3):
            teclado_frame.columnconfigure(i, weight=1)
    
    def criar_botoes_controle(self, parent):
        """Cria botões de controle adicionais incluindo gestão de PDVs"""
        controles_frame = tk.Frame(parent, bg='#34495e')
        controles_frame.pack(fill=tk.X, pady=5)
        
        botoes_controle = [
            ('Consultar Preço', '#2980b9', self.consultar_preco),
            ('Eliminar Item', '#c0392b', self.eliminar_item),
            ('Trocar PDV', '#8e44ad', self.trocar_ponto_venda),
            ('Logout', '#e74c3c', self.fazer_logout),
            ('Supervisor', '#f39c12', self.modo_supervisor),
            ('Balança', '#7f8c8d', self.modo_balanca),
            ('Login', '#27ae60', self.modo_login)
        ]
        
        for texto, cor, comando in botoes_controle:
            btn = tk.Button(controles_frame, text=texto, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=2,
                           command=comando)
            btn.pack(fill=tk.X, pady=2)
    
    def criar_info_pagamento(self, parent):
        """Cria informações de pagamento"""
        info_frame = tk.Frame(parent, bg='#34495e')
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(info_frame, text="FORMA DE PAGAMENTO", font=('Arial', 12, 'bold'),
                bg='#34495e', fg='#ecf0f1').pack()
        
        formas_frame = tk.Frame(info_frame, bg='#34495e')
        formas_frame.pack(fill=tk.X, pady=5)
        
        formas = [
            ('DINHEIRO', '#27ae60'),
            ('CARTÃO DÉBITO', '#2980b9'),
            ('CARTÃO CRÉDITO', '#8e44ad'),
            ('PIX', '#3498db')
        ]
        
        for forma, cor in formas:
            btn = tk.Button(formas_frame, text=forma, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=2,
                           command=lambda f=forma: self.selecionar_forma_pagamento(f))
            btn.pack(fill=tk.X, pady=1)
        
        # Valores de pagamento
        valores_frame = tk.Frame(info_frame, bg='#34495e')
        valores_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(valores_frame, text="Valor Pago:", font=('Arial', 10),
                bg='#34495e', fg='#ecf0f1').grid(row=0, column=0, sticky=tk.W)
        tk.Label(valores_frame, textvariable=self.valor_pago_var, font=('Arial', 11, 'bold'),
                bg='#34495e', fg='#2ecc71').grid(row=0, column=1, sticky=tk.E)
        
        tk.Label(valores_frame, text="Troco:", font=('Arial', 10),
                bg='#34495e', fg='#ecf0f1').grid(row=1, column=0, sticky=tk.W)
        tk.Label(valores_frame, textvariable=self.troco_var, font=('Arial', 11, 'bold'),
                bg='#34495e', fg='#e74c3c').grid(row=1, column=1, sticky=tk.E)
        
        valores_frame.columnconfigure(1, weight=1)
    
    # Métodos de processamento de teclas
    def _processar_tecla_normal(self, tecla: str) -> bool:
        """Processa teclas no modo normal"""
        try:
            if tecla == 'X':
                self.processador_teclas.set_modo('quantidade')
                self.operacao_var.set("Digite quantidade + código (ex: X2CODIGO)")
                return True
            elif tecla == '⌫':
                self.display_text.set("")
                return True
            elif tecla == 'Enter':
                # Processar código do produto
                codigo = self.processador_teclas.buffer
                if codigo:
                    self.adicionar_produto(codigo)
                    self.processador_teclas.limpar_buffer()
                return True
            elif tecla.isdigit() or tecla == '.':
                self.processador_teclas.buffer += tecla
                self.display_text.set(self.processador_teclas.buffer)
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao processar tecla normal: {e}")
            return False
    
    def _processar_tecla_login(self, tecla: str) -> bool:
        """Processa teclas no modo login"""
        try:
            if tecla == 'Enter':
                self.fazer_login(self.processador_teclas.buffer)
                return True
            elif tecla == '⌫':
                if self.processador_teclas.buffer:
                    self.processador_teclas.buffer = self.processador_teclas.buffer[:-1]
                    self.display_text.set("*" * len(self.processador_teclas.buffer))
                return True
            elif tecla.isdigit() and len(self.processador_teclas.buffer) < 10:
                self.processador_teclas.buffer += tecla
                self.display_text.set("*" * len(self.processador_teclas.buffer))
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao processar tecla login: {e}")
            return False
    
    # Métodos principais do sistema
    def bloquear_sistema(self):
        """Bloqueia sistema até fazer login"""
        self.modo_operacao = "bloqueado"
        self.processador_teclas.set_modo('login')
        self.operacao_var.set("Digite número de trabalhador + Enter")
        self.display_text.set("Sistema bloqueado - Faça login")
    
    
    
    def adicionar_produto(self, codigo: str, quantidade: float = 1.0):
        """Adiciona produto à venda atual"""
        try:
            produto = self.cache_produtos.obter_produto_por_codigo(codigo)
            if not produto:
                messagebox.showerror("Erro", f"Produto {codigo} não encontrado!")
                return False
            
            # Verificar estoque
            if produto['estoque'] < quantidade:
                messagebox.showerror("Erro", 
                    f"Estoque insuficiente! Disponível: {produto['estoque']}")
                return False
            
            # Calcular valores com IVA
            iva_valor = (produto['preco'] * produto['iva_taxa'] / 100) * quantidade
            subtotal = produto['preco'] * quantidade
            
            # Verificar se produto já está na venda
            for item in self.venda_atual:
                if item['produto_id'] == produto['id']:
                    item['quantidade'] += quantidade
                    item['subtotal'] += subtotal
                    item['iva_valor'] += iva_valor
                    break
            else:
                # Adicionar novo item
                self.venda_atual.append({
                    'produto_id': produto['id'],
                    'codigo': produto['codigo'],
                    'nome': produto['nome'],
                    'preco': produto['preco'],
                    'quantidade': quantidade,
                    'subtotal': subtotal,
                    'iva_taxa': produto['iva_taxa'],
                    'iva_valor': iva_valor
                })
            
            self.atualizar_display_venda()
            self.display_text.set(f"✓ {produto['nome']} adicionado")
            logger.info(f"Produto {codigo} adicionado à venda")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar produto {codigo}: {e}")
            messagebox.showerror("Erro", "Falha ao adicionar produto!")
            return False
    
    def consultar_preco(self):
        """Consulta preço de produto"""
        self.processador_teclas.set_modo('consulta')
        self.operacao_var.set("Digite código do produto para consulta")
        self.display_text.set("Modo consulta - Digite código")
    
    def eliminar_item(self):
        """Elimina item da venda atual"""
        selecionado = self.tree.selection()
        if selecionado:
            item = self.tree.item(selecionado[0])
            valores = item['values']
            
            # Encontrar e remover item da venda
            for i, venda_item in enumerate(self.venda_atual):
                if venda_item['nome'] == valores[0]:
                    self.venda_atual.pop(i)
                    break
            
            self.atualizar_display_venda()
            self.display_text.set(f"Item {valores[0]} removido")
            logger.info(f"Item {valores[0]} removido da venda")
        else:
            messagebox.showwarning("Aviso", "Selecione um item para remover!")
    
    def modo_supervisor(self):
        """Ativa modo supervisor"""
        if self.usuario_logado and self.usuario_logado['nivel'] in ['admin', 'gerente', 'supervisor']:
            self.processador_teclas.set_modo('supervisor')
            self.operacao_var.set("Modo Supervisor - Escolha opção")
            self.mostrar_menu_supervisor()
        else:
            messagebox.showerror("Acesso Negado", "Permissão de supervisor necessária!")
    
    def mostrar_menu_supervisor(self):
        """Mostra menu de opções do supervisor"""
        menu_window = tk.Toplevel(self.root)
        menu_window.title("Menu Supervisor")
        menu_window.geometry("300x400")
        menu_window.configure(bg='#34495e')
        
        opcoes = [
            ("Desconto", self.aplicar_desconto),
            ("Movimento Caixa", self.movimento_caixa),
            ("Fechar Caixa", self.fechar_caixa),
            ("Cancelar Venda", self.cancelar_venda),
            ("Relatórios", self.mostrar_relatorios),
            ("Sair", menu_window.destroy)
        ]
        
        for texto, comando in opcoes:
            btn = tk.Button(menu_window, text=texto, font=('Arial', 12, 'bold'),
                           bg='#3498db', fg='white', height=2, width=20,
                           command=comando)
            btn.pack(fill=tk.X, padx=20, pady=5)
    
    def aplicar_desconto(self):
        """Aplica desconto na venda atual"""
        if self.venda_atual:
            # Implementar lógica de desconto
            pass
    
    def movimento_caixa(self):
        """Mostra movimento do caixa"""
        # Implementar relatório de movimento
        pass
    
    def fechar_caixa(self):
        """Fecha caixa e gera relatório"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT forma_pagamento_id, SUM(total) as total
                    FROM vendas 
                    WHERE DATE(data_hora) = CURDATE() AND estado = 'finalizada'
                    GROUP BY forma_pagamento_id
                """)
                totais = cursor.fetchall()
            
            # Gerar relatório
            relatorio = "FECHAMENTO DE CAIXA\n" + "="*30 + "\n"
            for total in totais:
                relatorio += f"{total['forma_pagamento_id']}: Kz {total['total']:.2f}\n"
            
            messagebox.showinfo("Fechamento de Caixa", relatorio)
            logger.info("Caixa fechado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao fechar caixa: {e}")
            messagebox.showerror("Erro", "Falha ao fechar caixa!")
    
    def cancelar_venda(self):
        """Cancela venda atual"""
        if self.venda_atual:
            if messagebox.askyesno("Confirmar", "Cancelar venda atual?"):
                self.venda_atual.clear()
                self.atualizar_display_venda()
                self.display_text.set("Venda cancelada")
                logger.info("Venda cancelada pelo supervisor")
    
    def mostrar_relatorios(self):
        """Mostra menu de relatórios"""
        # Implementar diversos relatórios
        pass
    
    def selecionar_forma_pagamento(self, forma: str):
        """Seleciona forma de pagamento"""
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        self.forma_pagamento = forma
        total = sum(item['subtotal'] for item in self.venda_atual)
        
        if forma == 'DINHEIRO':
            self.processador_teclas.set_modo('pagamento')
            self.operacao_var.set("Digite valor pago em dinheiro")
            self.valor_pago = 0
            self.atualizar_display_pagamento()
        else:
            self.valor_pago = total
            self.finalizar_venda()
    
    def finalizar_venda(self):
        """Finaliza venda atual"""
        try:
            if not self.venda_atual:
                return
            
            total = sum(item['subtotal'] for item in self.venda_atual)
            total_iva = sum(item['iva_valor'] for item in self.venda_atual)
            
            # Verificar pagamento em dinheiro
            if self.forma_pagamento == 'DINHEIRO' and self.valor_pago < total:
                messagebox.showerror("Erro", 
                    f"Valor pago insuficiente! Total: Kz {total:.2f}")
                return
            
            # Calcular troco
            troco = self.valor_pago - total if self.forma_pagamento == 'DINHEIRO' else 0
            
            # Registrar venda no banco
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Inserir venda
                data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO vendas (usuario_id, data_hora, total, total_iva, 
                                      forma_pagamento_id, valor_pago, troco, estado)
                    VALUES (%s, %s, %s, %s, 
                           (SELECT id FROM formas_pagamento WHERE nome = %s), 
                           %s, %s, 'finalizada')
                """, (self.usuario_logado['id'], data_hora, total, total_iva,
                     self.forma_pagamento, self.valor_pago, troco))
                
                venda_id = cursor.lastrowid
                
                # Inserir itens e atualizar estoque
                for item in self.venda_atual:
                    cursor.execute("""
                        INSERT INTO itens_venda (venda_id, produto_id, quantidade, 
                                               preco_unitario, iva_taxa, iva_valor, subtotal)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (venda_id, item['produto_id'], item['quantidade'],
                         item['preco'], item['iva_taxa'], item['iva_valor'], item['subtotal']))
                    
                    cursor.execute("""
                        UPDATE produtos SET estoque = estoque - %s 
                        WHERE id = %s
                    """, (item['quantidade'], item['produto_id']))
                
                conn.commit()
            
            # Preparar dados para impressão
            dados_venda = {
                'numero_venda': venda_id,
                'data_hora': data_hora,
                'itens': self.venda_atual,
                'total': total,
                'total_iva': total_iva,
                'forma_pagamento': self.forma_pagamento,
                'valor_pago': self.valor_pago,
                'troco': troco
            }
            
            # Imprimir recibo
            self.impressora.imprimir_recibo(dados_venda)
            
            # Mostrar confirmação
            messagebox.showinfo("Sucesso", f"Venda #{venda_id:06d} finalizada com sucesso!")
            
            # Limpar venda
            self.venda_atual.clear()
            self.processador_teclas.set_modo('normal')
            self.forma_pagamento = ""
            self.valor_pago = 0
            self.atualizar_display_venda()
            self.atualizar_display_pagamento()
            self.display_text.set("Venda finalizada! Próxima venda...")
            self.operacao_var.set("Operação: Aguardando...")
            
            logger.info(f"Venda {venda_id} finalizada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao finalizar venda: {e}")
            messagebox.showerror("Erro", "Falha ao finalizar venda!")
    
    def atualizar_display_venda(self):
        """Atualiza display da venda atual"""
        # Limpar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Adicionar itens
        total_venda = 0
        for item in self.venda_atual:
            self.tree.insert('', tk.END, values=(
                item['nome'],
                f"{item['quantidade']:.3f}",
                f"Kz {item['preco']:.2f}",
                f"Kz {item['subtotal']:.2f}",
                f"{item['iva_taxa']:.1f}%"
            ))
            total_venda += item['subtotal']
        
        # Atualizar total
        self.total_var.set(f"Kz {total_venda:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    def atualizar_display_pagamento(self):
        """Atualiza display de pagamento"""
        self.valor_pago_var.set(f"Kz {self.valor_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        total = sum(item['subtotal'] for item in self.venda_atual)
        troco = self.valor_pago - total if self.valor_pago > total else 0
        self.troco_var.set(f"Kz {troco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    def atualizar_relogio(self):
        """Atualiza relógio do sistema"""
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.config(text=agora)
        self.root.after(1000, self.atualizar_relogio)
    
    def filtrar_produtos(self, categoria: str):
        """Filtra produtos por categoria"""
        # Implementar filtro de produtos
        logger.info(f"Filtrando produtos por categoria: {categoria}")

    # Implementar outros métodos de processamento de teclas
    def _processar_tecla_quantidade(self, tecla: str) -> bool:
        """Processa teclas no modo quantidade"""
        # Implementar similar ao normal mas com formatação XQTDCODIGO
        pass
    
    def _processar_tecla_pagamento(self, tecla: str) -> bool:
        """Processa teclas no modo pagamento"""
        # Implementar entrada de valor pago
        pass
    
    def _processar_tecla_consulta(self, tecla: str) -> bool:
        """Processa teclas no modo consulta"""
        # Implementar consulta de preços
        pass
    
    def _processar_tecla_supervisor(self, tecla: str) -> bool:
        """Processa teclas no modo supervisor"""
        # Implementar atalhos do supervisor
        pass
    
    def modo_balanca(self):
        """Ativa modo balança"""
        # Implementar integração com balança
        pass

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SistemaVendasProfissional(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Erro crítico no sistema: {e}")
        messagebox.showerror("Erro Fatal", f"O sistema encontrou um erro crítico:\n{e}")
