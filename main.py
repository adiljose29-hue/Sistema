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
from typing import Dict, List, Optional, Tuple, Any
import json
import tkinter.simpledialog

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

# =============================================================================
# 1. CONFIG MANAGER - DEVE VIR PRIMEIRO
# =============================================================================

class ConfigManager:
    """Gerenciador avançado de configurações do sistema"""
    
    def __init__(self, config_file: str = 'config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
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
        
        # Nova seção PONTOS_VENDA
        self.config['PONTOS_VENDA'] = {
            'pdv_principal': 'PDV Principal|USB001|Loja Central',
            'pdv_secundario': 'PDV Secundário|USB002|Piso 1',
            'pdv_restauracao': 'PDV Restauração|USB003|Piso 2'
        }
    
    def salvar_configuracao(self):
        """Salva a configuração atual no ficheiro"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
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

# =============================================================================
# 2. DATABASE MANAGER - DEPENDE DO CONFIG MANAGER
# =============================================================================

class DatabaseManager:
    """Gerenciador otimizado de conexões MySQL com suporte a múltiplos PDVs"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.connection_pool = self._criar_pool()
        self.ponto_venda_id = self._obter_id_ponto_venda()
    
    def _criar_pool(self) -> pooling.MySQLConnectionPool:
        """Cria pool de conexões com tratamento de erro melhorado"""
        try:
            db_config = {
                'host': self.config_manager.get('DATABASE', 'host', 'localhost'),
                'user': self.config_manager.get('DATABASE', 'user', 'root'),
                'password': self.config_manager.get('DATABASE', 'password', ''),
                'database': self.config_manager.get('DATABASE', 'database', 'bd_stop'),
                'charset': self.config_manager.get('DATABASE', 'charset', 'utf8mb4'),
                'pool_size': self.config_manager.getint('DATABASE', 'pool_size', 5),
                'pool_reset_session': self.config_manager.getboolean('DATABASE', 'pool_reset_session', True)
            }
            
            logger.info(f"Tentando conectar à base de dados: {db_config['host']}/{db_config['database']}")
            
            return mysql.connector.pooling.MySQLConnectionPool(
                pool_name="vendas_pool",
                **db_config
            )
        except Exception as e:
            logger.error(f"Erro ao criar pool de conexões: {e}")
            # Criar pool dummy para evitar crash
            return self._criar_pool_dummy()
    
    def _criar_pool_dummy(self):
        """Cria um pool dummy quando a base de dados não está disponível"""
        class DummyConnection:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def cursor(self, *args, **kwargs):
                return self
            def execute(self, *args, **kwargs):
                pass
            def fetchone(self):
                return None
            def fetchall(self):
                return []
            def close(self):
                pass
        
        class DummyPool:
            def get_connection(self):
                return DummyConnection()
        
        return DummyPool()
    
    def _obter_id_ponto_venda(self) -> int:
        """Obtém o ID do ponto de venda atual da base de dados"""
        try:
            pdv_config = self.config_manager.obter_ponto_venda_atual()
            nome_pdv = pdv_config['nome']
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar se a tabela existe
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = DATABASE() AND table_name = 'pontos_venda'
                """)
                tabela_existe = cursor.fetchone()[0] > 0
                
                if not tabela_existe:
                    logger.warning("Tabela pontos_venda não existe. Usando ID padrão 1.")
                    return 1
                
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
    
    def _carregar_config(self) -> configparser.ConfigParser:
        return self.config_manager.config
    
        
    def get_connection(self):
        """Obtém conexão do pool"""
        return self.connection_pool.get_connection()
            
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

# =============================================================================
# 3. OUTRAS CLASSES (CONTINUAÇÃO...)
# =============================================================================


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

class ScannerManager:
    """Gerenciador de scanner USB e Serial"""
    
    def __init__(self, config_manager: ConfigManager, callback_leitura):
        self.config_manager = config_manager
        self.callback_leitura = callback_leitura
        self.scanner_ativa = False
        self.thread_scanner = None
        
    def iniciar_scanner(self):
        """Inicia o serviço de scanner"""
        try:
            if not self.config_manager.getboolean('SCANNER', 'enabled', True):
                logger.info("Scanner desativado na configuração")
                return
                
            scanner_type = self.config_manager.get('SCANNER', 'type', 'usb')
            
            if scanner_type == 'usb':
                self._iniciar_scanner_usb()
            elif scanner_type == 'serial':
                self._iniciar_scanner_serial()
            else:
                logger.warning(f"Tipo de scanner não suportado: {scanner_type}")
                
        except Exception as e:
            logger.error(f"Erro ao iniciar scanner: {e}")
    
    def _iniciar_scanner_usb(self):
        """Inicia scanner USB (simulação por enquanto)"""
        if self.config_manager.getboolean('SCANNER', 'simulate_scanner', False):
            logger.info("Scanner USB em modo simulação")
            # Em desenvolvimento - simular scanner
            return
        
        try:
            # Implementação real do scanner USB viria aqui
            # Usando pyusb ou outra biblioteca
            logger.info("Scanner USB configurado - aguardando leituras")
        except Exception as e:
            logger.error(f"Erro no scanner USB: {e}")
    
    def _iniciar_scanner_serial(self):
        """Inicia scanner Serial"""
        try:
            import serial
            
            port = self.config_manager.get('SERIAL_SCANNER', 'port', 'COM3')
            baudrate = self.config_manager.getint('SERIAL_SCANNER', 'baudrate', 9600)
            
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            self.scanner_ativa = True
            self.thread_scanner = threading.Thread(target=self._ler_scanner_serial)
            self.thread_scanner.daemon = True
            self.thread_scanner.start()
            
            logger.info(f"Scanner serial iniciado na porta {port}")
            
        except ImportError:
            logger.error("Biblioteca pyserial não disponível. Instale pyserial.")
        except Exception as e:
            logger.error(f"Erro ao iniciar scanner serial: {e}")
    
    def _ler_scanner_serial(self):
        """Lê dados do scanner serial em thread separada"""
        while self.scanner_ativa:
            try:
                if self.serial_conn.in_waiting > 0:
                    dados = self.serial_conn.readline().decode('utf-8').strip()
                    
                    # Processar código de barras
                    if dados:
                        prefix = self.config_manager.get('SCANNER', 'barcode_prefix', '')
                        suffix = self.config_manager.get('SCANNER', 'barcode_suffix', '\r\n')
                        
                        # Remover prefixo e sufixo se existirem
                        if prefix and dados.startswith(prefix):
                            dados = dados[len(prefix):]
                        if suffix and dados.endswith(suffix):
                            dados = dados[:-len(suffix)]
                        
                        # Chamar callback na thread principal
                        if self.callback_leitura:
                            self.callback_leitura(dados)
                    
            except Exception as e:
                logger.error(f"Erro na leitura do scanner: {e}")
            
            time.sleep(0.1)
    
    def parar_scanner(self):
        """Para o serviço de scanner"""
        self.scanner_ativa = False
        if hasattr(self, 'serial_conn'):
            self.serial_conn.close()

class ImpressoraManager:
    """Gerenciador de impressão corrigido"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def _formatar_moeda(self, valor: float) -> str:
        """Formata valor em moeda Kz"""
        return f"{valor:,.2f} {self.config_manager.get('RECEIPT', 'currency', 'Kz')}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def _imprimir_windows(self, texto: str):
        """Imprime no Windows usando o nome exato da impressora"""
        try:
            import win32print
            
            printer_name = self.config_manager.get('PRINTER', 'port', 'Microsoft Print to PDF')
            
            # Obter handle da impressora
            hprinter = win32print.OpenPrinter(printer_name)
            
            try:
                # Iniciar documento
                job_info = ("Recibo Venda", None, "RAW")
                job_id = win32print.StartDocPrinter(hprinter, 1, job_info)
                win32print.StartPagePrinter(hprinter)
                
                # Converter texto para bytes
                texto_bytes = texto.encode('utf-8')
                
                # Escrever na impressora
                win32print.WritePrinter(hprinter, texto_bytes)
                
                # Finalizar
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                
                logger.info(f"Recibo enviado para impressora: {printer_name}")
                
            except Exception as e:
                logger.error(f"Erro durante impressão: {e}")
                win32print.AbortPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
                
        except ImportError:
            logger.error("Biblioteca win32print não disponível. Instale pywin32.")
            self._imprimir_arquivo(texto)
        except Exception as e:
            logger.error(f"Erro ao imprimir no Windows: {e}")
            self._imprimir_arquivo(texto)
    
    def imprimir_recibo(self, dados_venda: Dict):
        """Imprime recibo da venda"""
        try:
            recibo = self._formatar_recibo(dados_venda)
            
            printer_type = self.config_manager.get('PRINTER', 'type', 'windows')
            
            if printer_type == 'windows':
                self._imprimir_windows(recibo)
            elif printer_type == 'file':
                self._imprimir_arquivo(recibo)
            else:
                logger.warning(f"Tipo de impressora não suportado: {printer_type}")
                self._imprimir_arquivo(recibo)  # Fallback para arquivo
            
            logger.info("Recibo impresso com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao imprimir recibo: {e}")
            # Salvar em arquivo como fallback
            try:
                self._imprimir_arquivo(recibo)
            except Exception as e2:
                logger.error(f"Erro ao salvar recibo em arquivo: {e2}")
            
    def _imprimir_windows_alternativo(self, texto: str):
        """Método alternativo para impressão Windows"""
        try:
            import os
            # Usar comando de impressão do Windows
            printer_name = self.config_manager.get('PRINTER', 'port', 'Microsoft Print to PDF')
            
            # Salvar em arquivo temporário
            temp_file = "recibo_temp.txt"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(texto)
            
            # Imprimir usando comando do Windows
            os.system(f'print /D:"{printer_name}" "{temp_file}"')
            
            # Limpar arquivo temporário
            os.remove(temp_file)
            
            logger.info(f"Recibo enviado para impressora (método alternativo): {printer_name}")
            
        except Exception as e:
            logger.error(f"Erro no método alternativo de impressão: {e}")
            self._imprimir_arquivo(texto)
    
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
    
    def _imprimir_arquivo(self, texto: str):
        """Imprime em arquivo"""
        with open("recibo.txt", "w", encoding="utf-8") as f:
            f.write(texto)

import configparser
import os
from typing import Any, Dict, Optional



# Exemplo de uso no sistema principal
class SistemaVendasProfissional:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Vendas Professional - STOP")
        self.root.geometry("1300x900")
        self.root.configure(bg='#2c3e50')
        
        # Inicializar componentes
        self.config_manager = ConfigManager()
        
        # Verificar se a configuração é válida
        if not self.config_manager.validate_config():
            messagebox.showwarning("Configuração", "Configuração inválida! Usando configuração padrão.")
            self.config_manager._criar_configuracao_padrao()
            self.config_manager.salvar_configuracao()
        
        try:
            self.db_manager = DatabaseManager(self.config_manager)
            self.cache_produtos = CacheProdutos(self.db_manager)
        except Exception as e:
            logger.error(f"Erro ao inicializar base de dados: {e}")
            messagebox.showerror("Erro", f"Erro na base de dados: {e}\nO sistema funcionará em modo offline.")
            # Criar managers dummy para permitir funcionamento básico
            self.db_manager = None
            self.cache_produtos = None
        
        self.processador_teclas = ProcessadorTeclas()
        self.impressora = ImpressoraManager(self.config_manager)
        
        # Estado do sistema
        self.usuario_logado = None
        self.token_sessao = None
        self.venda_atual = []
        self.modo_operacao = "normal"
        self.ponto_venda_atual = self.config_manager.obter_ponto_venda_atual()
        
        # Estado do sistema para pagamentos múltiplos
        self.pagamentos_venda = []  # Lista de pagamentos
        self.valor_restante = 0.0   # Valor ainda não pago
        
        # Inicializar scanner
        self.scanner_manager = ScannerManager(self.config_manager, self._processar_leitura_scanner)
        self.scanner_manager.iniciar_scanner()
        
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
        
        # Limpar sessões expiradas ao iniciar (se db disponível)
        if self.db_manager:
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
    
    def fazer_login(self, credencial: str = None):
        """Realiza login do usuário com senha"""
        try:
            if credencial is None:
                credencial = self.processador_teclas.buffer
            
            # Verificar se é modo cartão supervisor
            if self.modo_operacao == 'supervisor_login':
                if self._validar_cartao_supervisor(credencial):
                    self.display_text.set("Cartão válido. Digite número:")
                    self.display_secundario.set("")
                    self.modo_operacao = 'supervisor_numero'
                    self.processador_teclas.limpar_buffer()
                    return
                else:
                    messagebox.showerror("Erro", "Cartão supervisor inválido!")
                    self.modo_operacao = 'normal'
                    self.processador_teclas.set_modo('normal')
                    return
            
            # Modo número de trabalhador
            elif self.modo_operacao == 'supervisor_numero':
                if len(credencial) < 4:
                    messagebox.showerror("Erro", "Número de trabalhador inválido!")
                    return
                
                self.numero_supervisor = credencial
                self.display_text.set(f"Usuário: {credencial}")
                self.display_secundario.set("Digite senha:")
                self.modo_operacao = 'supervisor_senha'
                self.processador_teclas.limpar_buffer()
                return
            
            # Modo senha supervisor
            elif self.modo_operacao == 'supervisor_senha':
                senha = credencial
                if self._validar_supervisor(self.numero_supervisor, senha):
                    self._concluir_login_supervisor()
                else:
                    messagebox.showerror("Erro", "Senha incorreta!")
                    self.modo_operacao = 'normal'
                    self.processador_teclas.set_modo('normal')
                return
            
            # Login normal
            else:
                if len(credencial) < 4:
                    messagebox.showerror("Erro", "Número de trabalhador inválido!")
                    return
                
                # Primeiro pede número
                if not hasattr(self, 'numero_trabalhador_temp'):
                    self.numero_trabalhador_temp = credencial
                    self.display_text.set(f"Usuário: {credencial}")
                    self.display_secundario.set("Digite senha:")
                    self.processador_teclas.limpar_buffer()
                    return
                
                # Depois pede senha
                senha = credencial
                self._validar_login_normal(self.numero_trabalhador_temp, senha)
                    
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            messagebox.showerror("Erro", "Falha no sistema de login!")
    
    def _validar_login_normal(self, numero_trabalhador: str, senha: str):
        """Valida login normal com senha"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, nome, nivel FROM usuarios 
                    WHERE numero_trabalhador = %s AND senha = MD5(%s) AND ativo = TRUE
                """, (numero_trabalhador, senha))
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
                    self.display_secundario.set("")
                    
                    # Limpar temporário
                    if hasattr(self, 'numero_trabalhador_temp'):
                        del self.numero_trabalhador_temp
                    
                    logger.info(f"Usuário {usuario['nome']} fez login com sucesso no PDV {self.ponto_venda_atual['nome']}")
                else:
                    messagebox.showerror("Erro", "Falha ao criar sessão!")
            else:
                messagebox.showerror("Erro", "Usuário ou senha incorretos!")
                # Resetar login
                if hasattr(self, 'numero_trabalhador_temp'):
                    del self.numero_trabalhador_temp
                self.display_text.set("Digite número de trabalhador")
                self.display_secundario.set("")
                
        except Exception as e:
            logger.error(f"Erro na validação de login: {e}")
            messagebox.showerror("Erro", "Falha na validação de login!")
    
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
        
        # Display principal - AGORA COM 2 LINHAS
        display_frame = tk.Frame(parent, bg='#2c3e50')
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Linha 1 - Display principal
        self.display_text = tk.StringVar(value="Sistema de Vendas STOP - Faça login")
        display_label = tk.Label(display_frame, textvariable=self.display_text,
                                font=('Arial', 14), bg='#1a252f', fg='#2ecc71',
                                height=1, anchor=tk.W, padx=10)
        display_label.pack(fill=tk.X, pady=(0, 2))
        
        # Linha 2 - Display secundário
        self.display_secundario = tk.StringVar(value="")
        display_sec_label = tk.Label(display_frame, textvariable=self.display_secundario,
                                    font=('Arial', 12), bg='#1a252f', fg='#3498db',
                                    height=1, anchor=tk.W, padx=10)
        display_sec_label.pack(fill=tk.X)
        
        # Resto do código permanece igual...
        # Treeview dos itens
        tree_frame = tk.Frame(parent, bg='#34495e')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ... resto do código do método
        
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
        """Cria teclado numérico melhorado"""
        teclado_frame = tk.Frame(parent, bg='#34495e')
        teclado_frame.pack(fill=tk.X, pady=5)
        
        # Botões organizados em 5x4
        botoes = [
            ('7', '#2c3e50'), ('8', '#2c3e50'), ('9', '#2c3e50'), ('C', '#e74c3c'),
            ('4', '#2c3e50'), ('5', '#2c3e50'), ('6', '#2c3e50'), ('⌫', '#e67e22'),
            ('1', '#2c3e50'), ('2', '#2c3e50'), ('3', '#2c3e50'), ('Total', '#f39c12'),
            ('0', '#2c3e50', 2), (',', '#2c3e50'), ('Enter', '#27ae60')
        ]
        
        for i, btn_info in enumerate(botoes):
            row, col = i // 4, i % 4
            
            if len(btn_info) == 3:
                texto, cor, colspan = btn_info
            else:
                texto, cor = btn_info
                colspan = 1
            
            btn = tk.Button(teclado_frame, text=texto, font=('Arial', 12, 'bold'),
                           bg=cor, fg='white', height=2, width=6,
                           command=lambda t=texto: self._processar_tecla_melhorada(t))
            btn.grid(row=row, column=col, columnspan=colspan, 
                    padx=2, pady=2, sticky='nsew')
        
        # Configurar grid
        for i in range(4):
            teclado_frame.rowconfigure(i, weight=1)
        for i in range(4):
            teclado_frame.columnconfigure(i, weight=1)
    
    def _processar_tecla_melhorada(self, tecla: str):
        """Processa teclas do teclado melhorado"""
        if tecla == 'C':  # Clear
            self.processador_teclas.limpar_buffer()
            self.display_text.set("")
            self.display_secundario.set("")
        elif tecla == 'Total':
            self._mostrar_formas_pagamento()
        else:
            self.processador_teclas.processar_tecla(tecla)
    
        
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
    
   

    def _configurar_processador_teclas(self):
        """Configura callbacks do processador de teclas"""
        self.processador_teclas.registrar_callback('normal', self._processar_tecla_normal)
        self.processador_teclas.registrar_callback('quantidade', self._processar_tecla_quantidade)
        self.processador_teclas.registrar_callback('pagamento', self._processar_tecla_pagamento)
        self.processador_teclas.registrar_callback('login', self._processar_tecla_login)
        self.processador_teclas.registrar_callback('consulta', self._processar_tecla_consulta)
        self.processador_teclas.registrar_callback('supervisor', self._processar_tecla_supervisor)

    def modo_login(self):
        """Ativa modo de login"""
        self.processador_teclas.set_modo('login')
        self.operacao_var.set("Digite número de trabalhador + Enter")
        self.display_text.set("Modo Login - Digite número")

    def modo_balanca(self):
        """Ativa modo balança"""
        if not self.usuario_logado:
            messagebox.showwarning("Aviso", "Faça login primeiro!")
            return
        
        self.processador_teclas.set_modo('normal')
        self.operacao_var.set("Modo Balança - Use X para quantidade")
        self.display_text.set("Modo Balança - Digite X + Peso + Código")
        messagebox.showinfo("Modo Balança", 
                          "Formato: X[Peso][Código]\nExemplo: X0.250001 para 250g do produto 001")

    def consultar_preco(self):
        """Consulta preço de produto"""
        self.processador_teclas.set_modo('consulta')
        self.operacao_var.set("Digite código do produto para consulta")
        self.display_text.set("Modo consulta - Digite código")

    # =============================================================================
    # MÉTODOS DE PROCESSAMENTO DE TECLAS
    # =============================================================================

    def _processar_tecla_normal(self, tecla: str) -> bool:
        """Processa teclas no modo normal"""
        try:
            if tecla == 'X':
                self.processador_teclas.set_modo('quantidade')
                self.operacao_var.set("Digite quantidade + código (ex: X2CODIGO)")
                self.display_text.set("X")
                return True
            elif tecla == '⌫':
                if self.processador_teclas.buffer:
                    self.processador_teclas.buffer = self.processador_teclas.buffer[:-1]
                    self.display_text.set(self.processador_teclas.buffer)
                return True
            elif tecla == 'Enter':
                # Processar código do produto
                codigo = self.processador_teclas.buffer
                if codigo:
                    self.adicionar_produto(codigo)
                    self.processador_teclas.limpar_buffer()
                return True
            elif tecla.isdigit():
                self.processador_teclas.buffer += tecla
                self.display_text.set(self.processador_teclas.buffer)
                return True
            elif tecla == ',':
                self.processador_teclas.buffer += '.'  # Internamente usa ponto, exibe como vírgula
                self.display_text.set(self.processador_teclas.buffer.replace('.', ','))
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

    def _processar_tecla_quantidade(self, tecla: str) -> bool:
        """Processa teclas no modo quantidade"""
        try:
            if tecla == 'Enter':
                self._processar_entrada_quantidade()
                return True
            elif tecla == '⌫':
                if len(self.processador_teclas.buffer) > 1:
                    self.processador_teclas.buffer = self.processador_teclas.buffer[:-1]
                    self.display_text.set(self.processador_teclas.buffer)
                else:
                    self.processador_teclas.set_modo('normal')
                    self.operacao_var.set("Operação: Aguardando...")
                    self.display_text.set("")
                return True
            elif tecla.isdigit() or tecla == '.':
                self.processador_teclas.buffer += tecla
                self.display_text.set(self.processador_teclas.buffer)
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao processar tecla quantidade: {e}")
            return False
    
    def _processar_tecla_consulta(self, tecla: str) -> bool:
        """Processa teclas no modo consulta"""
        try:
            if tecla == 'Enter':
                self._executar_consulta_preco()
                return True
            elif tecla == '⌫':
                if self.processador_teclas.buffer:
                    self.processador_teclas.buffer = self.processador_teclas.buffer[:-1]
                    self.display_text.set(self.processador_teclas.buffer)
                else:
                    self.processador_teclas.set_modo('normal')
                    self.operacao_var.set("Operação: Aguardando...")
                return True
            elif tecla.isdigit() or tecla.isalpha():
                self.processador_teclas.buffer += tecla
                self.display_text.set(self.processador_teclas.buffer)
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao processar tecla consulta: {e}")
            return False

    def _processar_tecla_supervisor(self, tecla: str) -> bool:
        """Processa teclas no modo supervisor"""
        try:
            if tecla == 'Enter':
                # Implementar atalhos do supervisor
                pass
            elif tecla == '1':
                self.aplicar_desconto()
            elif tecla == '2':
                self.movimento_caixa()
            elif tecla == '3':
                self.fechar_caixa()
            elif tecla == '4':
                self.cancelar_venda()
            elif tecla == '5':
                self.mostrar_relatorios()
            return True
        except Exception as e:
            logger.error(f"Erro ao processar tecla supervisor: {e}")
            return False

    def _processar_entrada_quantidade(self):
        """Processa entrada no modo quantidade"""
        try:
            buffer = self.processador_teclas.buffer
            if buffer.startswith('X') and len(buffer) > 1:
                # Encontrar onde termina a quantidade
                i = 1
                while i < len(buffer) and (buffer[i].isdigit() or buffer[i] == '.'):
                    i += 1
                
                quantidade_str = buffer[1:i]
                codigo = buffer[i:]
                
                if quantidade_str and codigo:
                    quantidade = float(quantidade_str)
                    if self.adicionar_produto(codigo, quantidade):
                        self.display_text.set(f"{quantidade}X{codigo} ✓")
                        self.operacao_var.set("Produto adicionado com sucesso!")
                    else:
                        self.display_text.set("Erro ao adicionar produto!")
                else:
                    messagebox.showerror("Erro", "Formato inválido! Use: XQuantidadeCódigo")
            
            self.processador_teclas.set_modo('normal')
            
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida!")
            self.processador_teclas.set_modo('normal')
        except Exception as e:
            logger.error(f"Erro ao processar entrada quantidade: {e}")
            messagebox.showerror("Erro", "Erro ao processar quantidade!")

    def _executar_consulta_preco(self):
        """Executa consulta de preço"""
        try:
            codigo = self.processador_teclas.buffer
            if not codigo:
                return
            
            if self.cache_produtos:
                produto = self.cache_produtos.obter_produto_por_codigo(codigo)
            else:
                # Fallback: consulta direta na base de dados
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT nome, preco, estoque FROM produtos 
                        WHERE codigo = %s AND ativo = TRUE
                    """, (codigo,))
                    produto = cursor.fetchone()
            
            if produto:
                mensagem = f"{produto['nome']}\nPreço: Kz {produto['preco']:.2f}\nEstoque: {produto['estoque']}"
                self.display_text.set(f"Consulta: {codigo}")
                messagebox.showinfo("Consulta de Preço", mensagem)
            else:
                messagebox.showerror("Erro", f"Produto {codigo} não encontrado!")
            
            self.processador_teclas.set_modo('normal')
            self.operacao_var.set("Consulta concluída")
            
        except Exception as e:
            logger.error(f"Erro na consulta de preço: {e}")
            messagebox.showerror("Erro", "Falha na consulta!")

    # =============================================================================
    # MÉTODOS DO SUPERVISOR
    # =============================================================================

    def aplicar_desconto(self):
        """Aplica desconto na venda atual"""
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhuma venda em andamento!")
            return
        
        # Implementar lógica de desconto
        desconto = tk.simpledialog.askfloat("Desconto", "Digite o valor do desconto (Kz):", minvalue=0)
        if desconto is not None:
            total_atual = sum(item['subtotal'] for item in self.venda_atual)
            if desconto <= total_atual:
                # Aplicar desconto proporcional nos itens
                for item in self.venda_atual:
                    proporcao = item['subtotal'] / total_atual
                    item['desconto'] = desconto * proporcao
                    item['subtotal'] -= item['desconto']
                
                self.atualizar_display_venda()
                self.display_text.set(f"Desconto de Kz {desconto:.2f} aplicado")
            else:
                messagebox.showerror("Erro", "Desconto maior que o total da venda!")

    def movimento_caixa(self):
        """Mostra movimento do caixa"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT 
                        DATE(data_hora) as data,
                        COUNT(*) as total_vendas,
                        SUM(total) as total_valor,
                        AVG(total) as media_venda
                    FROM vendas 
                    WHERE DATE(data_hora) = CURDATE() AND estado = 'finalizada'
                    GROUP BY DATE(data_hora)
                """)
                movimento = cursor.fetchone()
            
            if movimento:
                relatorio = f"MOVIMENTO DO CAIXA - {movimento['data']}\n"
                relatorio += f"Total de Vendas: {movimento['total_vendas']}\n"
                relatorio += f"Valor Total: Kz {movimento['total_valor']:.2f}\n"
                relatorio += f"Média por Venda: Kz {movimento['media_venda']:.2f}"
            else:
                relatorio = "Nenhuma venda hoje."
            
            messagebox.showinfo("Movimento do Caixa", relatorio)
            
        except Exception as e:
            logger.error(f"Erro ao obter movimento do caixa: {e}")
            messagebox.showerror("Erro", "Falha ao obter movimento do caixa!")

    def fechar_caixa(self):
        """Fecha caixa e gera relatório"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT 
                        fp.nome as forma_pagamento,
                        COUNT(*) as quantidade,
                        SUM(v.total) as total
                    FROM vendas v
                    JOIN formas_pagamento fp ON v.forma_pagamento_id = fp.id
                    WHERE DATE(v.data_hora) = CURDATE() AND v.estado = 'finalizada'
                    GROUP BY fp.nome
                """)
                totais = cursor.fetchall()
            
            # Gerar relatório
            relatorio = "FECHAMENTO DE CAIXA\n" + "="*40 + "\n"
            relatorio += f"Data: {datetime.now().strftime('%d/%m/%Y')}\n"
            relatorio += f"PDV: {self.ponto_venda_atual['nome']}\n"
            relatorio += "="*40 + "\n"
            
            total_geral = 0
            for total in totais:
                relatorio += f"{total['forma_pagamento']}: {total['quantidade']} vendas - Kz {total['total']:.2f}\n"
                total_geral += total['total']
            
            relatorio += "="*40 + "\n"
            relatorio += f"TOTAL GERAL: Kz {total_geral:.2f}\n"
            relatorio += "="*40 + "\n"
            
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
        relatorio_window = tk.Toplevel(self.root)
        relatorio_window.title("Relatórios")
        relatorio_window.geometry("300x400")
        relatorio_window.configure(bg='#34495e')
        
        opcoes = [
            ("Vendas por Período", self.relatorio_vendas_periodo),
            ("Produtos Mais Vendidos", self.relatorio_produtos_vendidos),
            ("Formas de Pagamento", self.relatorio_formas_pagamento),
            ("Estoque Baixo", self.relatorio_estoque_baixo)
        ]
        
        for texto, comando in opcoes:
            btn = tk.Button(relatorio_window, text=texto, font=('Arial', 12, 'bold'),
                           bg='#3498db', fg='white', height=2, width=25,
                           command=comando)
            btn.pack(fill=tk.X, padx=20, pady=5)

    def relatorio_vendas_periodo(self):
        """Gera relatório de vendas por período"""
        # Implementar relatório de vendas
        messagebox.showinfo("Relatório", "Relatório de Vendas por Período")

    def relatorio_produtos_vendidos(self):
        """Gera relatório de produtos mais vendidos"""
        # Implementar relatório de produtos
        messagebox.showinfo("Relatório", "Relatório de Produtos Mais Vendidos")

    def relatorio_formas_pagamento(self):
        """Gera relatório de formas de pagamento"""
        # Implementar relatório de formas de pagamento
        messagebox.showinfo("Relatório", "Relatório de Formas de Pagamento")

    def relatorio_estoque_baixo(self):
        """Gera relatório de estoque baixo"""
        # Implementar relatório de estoque
        messagebox.showinfo("Relatório", "Relatório de Estoque Baixo") 
    
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
            
            # Converter preço para float para evitar erro de Decimal
            preco = float(produto['preco'])
            iva_taxa = float(produto.get('iva_taxa', 14))
            
            # Calcular valores com IVA
            iva_valor = (preco * iva_taxa / 100) * quantidade
            subtotal = preco * quantidade
            
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
                    'preco': preco,
                    'quantidade': quantidade,
                    'subtotal': subtotal,
                    'iva_taxa': iva_taxa,
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
        """Ativa modo supervisor com cartão"""
        if self.usuario_logado and self.usuario_logado['nivel'] in ['admin', 'gerente', 'supervisor']:
            # Se já é supervisor, mostra menu direto
            self.mostrar_menu_supervisor()
        else:
            # Pedir cartão supervisor
            self.modo_operacao = 'supervisor_login'
            self.processador_teclas.set_modo('login')
            self.operacao_var.set("Passe o cartão supervisor")
            self.display_text.set("Modo Supervisor")
            self.display_secundario.set("Use o scanner para ler o cartão")
    
    def _validar_cartao_supervisor(self, codigo_barras: str) -> bool:
        """Valida cartão supervisor pelo código de barras"""
        try:
            cartoes_validos = self.config_manager.get('SUPERVISOR', 'cartoes', '999888777,999888666').split(',')
            return codigo_barras.strip() in cartoes_validos
        except:
            # Cartões padrão se não configurado
            cartoes_padrao = ['999888777', '999888666', '999888555']
            return codigo_barras.strip() in cartoes_padrao
    
    def _validar_supervisor(self, numero_trabalhador: str, senha: str) -> bool:
        """Valida credenciais do supervisor"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, nome, nivel FROM usuarios 
                    WHERE numero_trabalhador = %s AND senha = MD5(%s) 
                    AND nivel IN ('admin', 'gerente', 'supervisor') AND ativo = TRUE
                """, (numero_trabalhador, senha))
                usuario = cursor.fetchone()
            
            if usuario:
                self.usuario_supervisor = usuario
                return True
            return False
            
        except Exception as e:
            logger.error(f"Erro ao validar supervisor: {e}")
            return False
    
    def _concluir_login_supervisor(self):
        """Conclui login do supervisor"""
        self.usuario_logado = self.usuario_supervisor
        self.usuario_label.config(text=f"Supervisor: {self.usuario_logado['nome']}")
        self.processador_teclas.set_modo('normal')
        self.operacao_var.set("Modo Supervisor Ativo")
        self.display_text.set(f"Supervisor: {self.usuario_logado['nome']}")
        self.display_secundario.set("")
        
        # Mostrar menu supervisor
        self.mostrar_menu_supervisor()
        
        logger.info(f"Supervisor {self.usuario_logado['nome']} fez login")
    
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
       
    def finalizar_venda(self):
        """Finaliza venda atual com pagamentos múltiplos"""
        try:
            if not self.venda_atual:
                return
            
            total_venda = sum(item['subtotal'] for item in self.venda_atual)
            total_pago = sum(pagamento['valor'] for pagamento in self.pagamentos_venda)
            
            if total_pago < total_venda:
                messagebox.showerror("Erro", 
                                   f"Pagamento insuficiente! Total: Kz {total_venda:.2f} | Pago: Kz {total_pago:.2f}")
                return
            
            # Registrar venda no banco
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Inserir venda
                data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO vendas (usuario_id, data_hora, total, total_iva, ponto_venda_id, estado)
                    VALUES (%s, %s, %s, %s, %s, 'finalizada')
                """, (self.usuario_logado['id'], data_hora, total_venda, 
                      sum(item['iva_valor'] for item in self.venda_atual), 
                      self.db_manager.ponto_venda_id))
                
                venda_id = cursor.lastrowid
                
                # Registrar itens e atualizar estoque
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
                
                # Registrar pagamentos múltiplos
                for pagamento in self.pagamentos_venda:
                    cursor.execute("""
                        INSERT INTO pagamentos_venda (venda_id, forma_pagamento, valor, valor_pago, troco)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (venda_id, pagamento['forma'], pagamento['valor'], 
                          pagamento['valor_pago'], pagamento['troco']))
                
                conn.commit()
            
            # Preparar dados para impressão
            dados_venda = {
                'numero_venda': venda_id,
                'data_hora': data_hora,
                'itens': self.venda_atual,
                'pagamentos': self.pagamentos_venda,
                'total': total_venda,
                'total_iva': sum(item['iva_valor'] for item in self.venda_atual),
                'total_pago': total_pago,
                'troco_total': sum(pagamento['troco'] for pagamento in self.pagamentos_venda)
            }
            
            # Imprimir recibo
            self.impressora.imprimir_recibo(dados_venda)
            
            # Mostrar confirmação
            mensagem = f"Venda #{venda_id:06d} finalizada com sucesso!\n\n"
            mensagem += f"Total: Kz {total_venda:.2f}\n"
            for pagamento in self.pagamentos_venda:
                mensagem += f"{pagamento['forma']}: Kz {pagamento['valor']:.2f}\n"
                if pagamento['troco'] > 0:
                    mensagem += f"Troco: Kz {pagamento['troco']:.2f}\n"
            
            messagebox.showinfo("Venda Finalizada", mensagem)
            
            # Limpar venda
            self._limpar_venda()
            
            logger.info(f"Venda {venda_id} finalizada com {len(self.pagamentos_venda)} pagamentos")
            
        except Exception as e:
            logger.error(f"Erro ao finalizar venda: {e}")
            messagebox.showerror("Erro", "Falha ao finalizar venda!")
    
    def _limpar_venda(self):
        """Limpa todos os dados da venda atual"""
        self.venda_atual.clear()
        self.pagamentos_venda.clear()
        self.valor_restante = 0.0
        self.valor_pago_temp = 0
        self.forma_pagamento_temp = ""
        
        self.processador_teclas.set_modo('normal')
        self.atualizar_display_venda()
        self.atualizar_display_pagamento()
        self.display_text.set("Venda finalizada! Próxima venda...")
        self.display_secundario.set("")
        self.operacao_var.set("Operação: Aguardando...")
    
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
        
    def atualizar_relogio(self):
        """Atualiza relógio do sistema"""
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.config(text=agora)
        self.root.after(1000, self.atualizar_relogio)
    
    def filtrar_produtos(self, categoria: str):
        """Filtra produtos por categoria"""
        # Implementar filtro de produtos
        logger.info(f"Filtrando produtos por categoria: {categoria}")
     
    def _processar_leitura_scanner(self, codigo: str):
        """Processa leitura do scanner"""
        try:
            # Processar na thread principal
            self.root.after(0, lambda: self._processar_codigo_barras(codigo))
        except Exception as e:
            logger.error(f"Erro ao processar leitura do scanner: {e}")
    
    def _processar_codigo_barras(self, codigo: str):
        """Processa código de barras lido"""
        if not codigo:
            return
            
        # Verificar se é modo supervisor
        if self.modo_operacao == 'supervisor_login':
            if self._validar_cartao_supervisor(codigo):
                self.display_text.set("Cartão válido. Digite número:")
                self.display_secundario.set("")
                self.modo_operacao = 'supervisor_numero'
                self.processador_teclas.limpar_buffer()
            else:
                messagebox.showerror("Erro", "Cartão supervisor inválido!")
            return
        
        # Verificar se é produto
        if self.usuario_logado:
            # Tentar adicionar como produto
            produto = self.cache_produtos.obter_produto_por_codigo(codigo)
            if produto:
                self.adicionar_produto(codigo)
            else:
                # Pode ser um código interno ou desconhecido
                logger.info(f"Código de barras não reconhecido: {codigo}")
    
    def _mostrar_formas_pagamento(self):
        """Mostra formas de pagamento após apertar Total"""
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        total_venda = sum(item['subtotal'] for item in self.venda_atual)
        total_pago = sum(pagamento['valor'] for pagamento in self.pagamentos_venda)
        self.valor_restante = total_venda - total_pago
        
        if self.valor_restante <= 0:
            # Venda já totalmente paga
            self.finalizar_venda()
            return
        
        self.display_text.set(f"Total: Kz {total_venda:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        self.display_secundario.set(f"Falta: Kz {self.valor_restante:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        self.operacao_var.set("Selecione forma de pagamento")
    
    def selecionar_forma_pagamento(self, forma: str):
        """Seleciona forma de pagamento para pagamento múltiplo"""
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        total_venda = sum(item['subtotal'] for item in self.venda_atual)
        total_pago = sum(pagamento['valor'] for pagamento in self.pagamentos_venda)
        valor_restante = total_venda - total_pago
        
        if valor_restante <= 0:
            self.finalizar_venda()
            return
        
        if forma == 'DINHEIRO':
            self.processador_teclas.set_modo('pagamento')
            self.operacao_var.set(f"Digite valor pago em dinheiro (Falta: Kz {valor_restante:.2f})")
            self.valor_pago_temp = 0
            self.forma_pagamento_temp = forma
            self.atualizar_display_pagamento()
        else:
            # Para outras formas, usar o valor restante
            self._adicionar_pagamento(forma, valor_restante)
    
    def _adicionar_pagamento(self, forma: str, valor: float):
        """Adiciona um pagamento à venda"""
        try:
            # Verificar se a forma de pagamento aceita troco
            aceita_troco = self._forma_aceita_troco(forma)
            troco = 0.0
            
            if forma == 'DINHEIRO' and self.valor_pago_temp > valor:
                if aceita_troco:
                    troco = self.valor_pago_temp - valor
                else:
                    messagebox.showwarning("Aviso", 
                                         f"{forma} não aceita troco. Valor exato necessário.")
                    return
            
            pagamento = {
                'forma': forma,
                'valor': min(self.valor_pago_temp if forma == 'DINHEIRO' else valor, valor),
                'valor_pago': self.valor_pago_temp if forma == 'DINHEIRO' else valor,
                'troco': troco,
                'data_hora': datetime.now().strftime("%H:%M:%S")
            }
            
            self.pagamentos_venda.append(pagamento)
            
            # Atualizar display
            total_pago = sum(p['valor'] for p in self.pagamentos_venda)
            total_venda = sum(item['subtotal'] for item in self.venda_atual)
            valor_restante = total_venda - total_pago
            
            self.display_text.set(f"Pago: {forma} - Kz {pagamento['valor']:.2f}")
            
            if valor_restante > 0:
                self.display_secundario.set(f"Falta: Kz {valor_restante:.2f}")
                self.operacao_var.set("Selecione próxima forma de pagamento")
            else:
                self.display_secundario.set(f"Troco: Kz {troco:.2f}" if troco > 0 else "Pagamento concluído")
                self.finalizar_venda()
            
            # Resetar temporários
            self.valor_pago_temp = 0
            self.forma_pagamento_temp = ""
            
        except Exception as e:
            logger.error(f"Erro ao adicionar pagamento: {e}")
            messagebox.showerror("Erro", "Falha ao processar pagamento!")
    
    def _forma_aceita_troco(self, forma: str) -> bool:
        """Verifica se a forma de pagamento aceita troco"""
        try:
            formas_troco = self.config_manager.get('PAYMENT', 'formas_com_troco', 'DINHEIRO').split(',')
            return forma.strip().upper() in [f.strip().upper() for f in formas_troco]
        except:
            # Por padrão, apenas dinheiro aceita troco
            return forma.upper() == 'DINHEIRO'
    
    def _processar_tecla_pagamento(self, tecla: str) -> bool:
        """Processa teclas no modo pagamento"""
        try:
            if tecla == 'Enter':
                total_venda = sum(item['subtotal'] for item in self.venda_atual)
                total_pago = sum(pagamento['valor'] for pagamento in self.pagamentos_venda)
                valor_restante = total_venda - total_pago
                
                if self.valor_pago_temp > 0:
                    self._adicionar_pagamento(self.forma_pagamento_temp, valor_restante)
                return True
            elif tecla == '⌫':
                if self.valor_pago_temp > 0:
                    self.valor_pago_temp = int(self.valor_pago_temp / 10)
                    self.atualizar_display_pagamento()
                return True
            elif tecla.isdigit():
                self.valor_pago_temp = self.valor_pago_temp * 10 + int(tecla)
                self.atualizar_display_pagamento()
                return True
            elif tecla == ',':
                # Para valores decimais (em desenvolvimento)
                pass
            return False
        except Exception as e:
            logger.error(f"Erro ao processar tecla pagamento: {e}")
            return False
    
    def atualizar_display_pagamento(self):
        """Atualiza display de pagamento"""
        total_venda = sum(item['subtotal'] for item in self.venda_atual)
        total_pago = sum(pagamento['valor'] for pagamento in self.pagamentos_venda)
        valor_restante = total_venda - total_pago
        
        self.valor_pago_var.set(f"Kz {self.valor_pago_temp:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        if self.forma_pagamento_temp == 'DINHEIRO' and self.valor_pago_temp > valor_restante:
            troco = self.valor_pago_temp - valor_restante
            self.troco_var.set(f"Kz {troco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        else:
            self.troco_var.set("Kz 0,00")
    
    

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SistemaVendasProfissional(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Erro crítico no sistema: {e}")
        messagebox.showerror("Erro Fatal", f"O sistema encontrou um erro crítico:\n{e}")
