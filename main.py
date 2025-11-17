import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
from datetime import datetime, timedelta
import json
import os
import threading
import time
import hashlib
import random
import math

# Para impressão Windows
try:
    import win32print
    import win32ui
except ImportError:
    print("⚠️  pywin32 não instalado. Recursos de impressão limitados.")

# Para impressão serial
try:
    import serial
except ImportError:
    print("⚠️  pyserial não instalado. Impressão COM não disponível.")

# Para manipulação de imagem (PIL)
try:
    from PIL import Image, ImageWin
except ImportError:
    print("⚠️  Pillow não instalado. Alguns recursos de impressão não disponíveis.")

class SistemaVendasProfissional:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Vendas Touch - Professional Plus")
        self.root.geometry("1300x900")
        self.root.configure(bg='#2c3e50')
        
        # Sistema de configurações .INI - CORREÇÃO
        self.config_manager = GerenciadorConfig('config.ini')
        self.config = self.config_manager  # Para compatibilidade
        
        # SISTEMA DE MÚLTIPLOS PDVs - CONFIGURAÇÃO
        self._configurar_pdv()
        #self.inserir_dados_iniciais()
        # Verificar e criar config.ini se necessário
        #self.verificar_config_ini()
        
        # Conectar ao MySQL usando configurações
        self.conectar_mysql()
        self.criar_tabelas()
        
        # Inicializar variáveis
        # Inicializar variáveis
        
        self._inicializar_variaveis()
        
        # Sistema de impressão
        self.impressao = SistemaImpressao(self)
        
        # Vincular eventos do teclado
        self.root.bind('<Key>', self.ler_scanner)
        
        # Criar interface
        self.criar_interface()
        
        # Iniciar relógio
        self.iniciar_relogio()
        
        # NÃO verificar status do caixa aqui - será feito após login        
    def _configurar_pdv(self):
        """Configura o ponto de venda a partir do arquivo de configuração"""
        try:
            # Obter configurações do PDV
            self.numero_caixa = self.config_manager.get('PONTO_VENDA', 'numero_caixa', 1)
            self.descricao_caixa = self.config_manager.get('PONTO_VENDA', 'descricao_caixa', f'Caixa {self.numero_caixa}')
            self.localizacao_caixa = self.config_manager.get('PONTO_VENDA', 'localizacao', 'Loja Principal')
            self.pdv_ativo = self.config_manager.get('PONTO_VENDA', 'ativo', True)
            
            print(f"🖥️  Configurando PDV: {self.descricao_caixa}")
            print(f"📍 Localização: {self.localizacao_caixa}")
            print(f"🔢 Número do Caixa: {self.numero_caixa}")
            print(f"✅ Status: {'ATIVO' if self.pdv_ativo else 'INATIVO'}")
            
        except Exception as e:
            print(f"❌ Erro ao configurar PDV: {e}")
            # Valores padrão
            self.numero_caixa = 1
            self.descricao_caixa = 'Caixa 1'
            self.localizacao_caixa = 'Loja Principal'
            self.pdv_ativo = True
    
        
        
    def _inicializar_variaveis(self):
        """Inicializa variáveis do sistema"""
        # Variáveis de venda        
        self.venda_atual = []
        self.display_text = ""
        self.modo_quantidade = False
        self.modo_pagamento = False
        self.modo_multiplos_pagamentos = False
        self.modo_digitar_valor = False
        self.pagamentos = []
        self.valor_pago_str = ""
        self.forma_pagamento = ""
        self.operador_atual = None
        self.supervisor_atual = None
        self.cliente_atual = None
        self.desconto_aplicado = 0
        
        # Variáveis de caixa
        self.caixa_aberto = False
        self.saldo_inicial = 0
        self.id_abertura = None
        
        # Variáveis para scanner
        self.codigo_scanner = ""
        self.scanner_ativo = self.config_manager.get('SISTEMA', 'usar_scanner', bool)
        

    #multiplas caixa
    def obter_info_pdv(self):
        """Obtém informações do ponto de venda atual - CORRIGIDO"""
        try:
            return {
                'numero_caixa': getattr(self, 'numero_caixa', 1),
                'descricao_caixa': getattr(self, 'descricao_caixa', 'Caixa 1'),
                'localizacao': getattr(self, 'localizacao_caixa', 'Não especificado'),
                'operador': self.operador_atual['nome'] if hasattr(self, 'operador_atual') and self.operador_atual else 'Não logado'
            }
        except Exception as e:
            print(f"❌ Erro ao obter info PDV: {e}")
            return {
                'numero_caixa': 1,
                'descricao_caixa': 'Caixa 1',
                'localizacao': 'Não especificado',
                'operador': 'Não logado'
            }
    
    def atualizar_titulo_pdv(self):
        """Atualiza o título da janela com informações do PDV"""
        info_pdv = self.obter_info_pdv()
        titulo = f"Sistema de Vendas - {info_pdv['descricao_caixa']} - {info_pdv['localizacao']}"
        
        if hasattr(self, 'operador_atual') and self.operador_atual:
            titulo += f" - Operador: {self.operador_atual['nome']}"
        
        self.root.title(titulo)
    
    def mostrar_info_pdv(self):
        """Mostra informações do ponto de venda"""
        info_pdv = self.obter_info_pdv()
        
        info_window = tk.Toplevel(self.root)
        info_window.title("Informações do Ponto de Venda")
        info_window.geometry("400x300")
        info_window.transient(self.root)
        
        main_frame = tk.Frame(info_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="🖥️ INFORMAÇÕES DO PDV", 
                font=('Arial', 16, 'bold')).pack(pady=20)
        
        info_text = f"""
    Número do Caixa: {info_pdv['numero_caixa']}
    Descrição: {info_pdv['descricao_caixa']}
    Localização: {info_pdv['localizacao']}
    Operador: {info_pdv['operador']}
    
    Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    Status Caixa: {'ABERTO' if self.caixa_aberto else 'FECHADO'}
    """
        
        tk.Label(main_frame, text=info_text, font=('Arial', 12),
                justify=tk.LEFT).pack(pady=10)
        
        tk.Button(main_frame, text="✅ FECHAR", command=info_window.destroy,
                 bg='#3498db', fg='white').pack(pady=10)
                 
                 
    #multiplas caixa fim
    def conectar_mysql(self):
        """Conecta ao MySQL usando configurações do .INI"""
        try:
            # Obter configurações do .INI
            host = self.config_manager.get('BANCO_DADOS', 'host')
            user = self.config_manager.get('BANCO_DADOS', 'usuario')
            password = self.config_manager.get('BANCO_DADOS', 'senha')
            database = self.config_manager.get('BANCO_DADOS', 'database')
            
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                autocommit=True
            )
            self.cursor = self.conn.cursor(dictionary=True)
            print("✅ Conexão com MySQL estabelecida com sucesso!")
            
        except mysql.connector.Error as e:
            print(f"❌ Erro ao conectar com MySQL: {e}")
            
            # Tentar criar database se não existir
            if "Unknown database" in str(e):
                self._criar_database_se_necessario(host, user, password, database)
            else:
                messagebox.showerror(
                    "Erro de Banco de Dados", 
                    f"Não foi possível conectar ao MySQL:\n{str(e)}\n\n"
                    "Verifique as configurações em config.ini"
                )
                self.root.quit()
    
    def _criar_database_se_necessario(self, host, user, password, database):
        """Cria o database se não existir"""
        try:
            # Conectar sem database especificado
            temp_conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password
            )
            temp_cursor = temp_conn.cursor()
            
            # Criar database
            temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            print(f"✅ Database '{database}' criado com sucesso!")
            
            temp_cursor.close()
            temp_conn.close()
            
            # Tentar conectar novamente
            self.conectar_mysql()
            
        except Exception as e:
            print(f"❌ Erro ao criar database: {e}")
            messagebox.showerror(
                "Erro de Banco de Dados", 
                f"Não foi possível criar o database '{database}':\n{str(e)}"
            )
            self.root.quit()

    def criar_tabelas(self):
        """Cria todas as tabelas necessárias incluindo PDVs"""""
        tables = {
            'usuarios': '''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_trabalhador VARCHAR(20) UNIQUE NOT NULL,
                    nome VARCHAR(100) NOT NULL,
                    senha_hash VARCHAR(255) NOT NULL,
                    nivel_acesso ENUM('OPERADOR', 'SUPERVISOR', 'ADMIN') DEFAULT 'OPERADOR',
                    ativo BOOLEAN DEFAULT TRUE,
                    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ultimo_login DATETIME,
                    criado_por INT,
                    FOREIGN KEY (criado_por) REFERENCES usuarios(id)
                )
            ''',
            'pontos_venda': '''
                CREATE TABLE IF NOT EXISTS pontos_venda (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_caixa INT UNIQUE NOT NULL,
                    descricao_caixa VARCHAR(100) NOT NULL,
                    localizacao VARCHAR(200),
                    ativo BOOLEAN DEFAULT TRUE,
                    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cadastrado_por INT,
                    FOREIGN KEY (cadastrado_por) REFERENCES usuarios(id)
                )
            ''',
            'produtos': '''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    codigo VARCHAR(50) UNIQUE NOT NULL,
                    nome VARCHAR(200) NOT NULL,
                    descricao TEXT,
                    preco DECIMAL(10,2) NOT NULL,
                    preco_custo DECIMAL(10,2),
                    estoque INT DEFAULT 0,
                    estoque_minimo INT DEFAULT 5,
                    categoria_id INT,
                    fornecedor_id INT,
                    ativo BOOLEAN DEFAULT TRUE,
                    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cadastrado_por INT,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                    FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
                    FOREIGN KEY (cadastrado_por) REFERENCES usuarios(id)
                )
            ''',
            'auditoria': '''
                CREATE TABLE IF NOT EXISTS auditoria (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    data_hora DATETIME NOT NULL,
                    usuario_id INT NOT NULL,
                    acao VARCHAR(100) NOT NULL,
                    descricao TEXT,
                    tabela_afetada VARCHAR(50),
                    registro_id INT,
                    ip_address VARCHAR(45),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )
            '''
        }

        for table_name, table_query in tables.items():
            try:
                self.cursor.execute(table_query)
                print(f"✅ Tabela {table_name} criada/verificada")
            except mysql.connector.Error as e:
                print(f"❌ Erro ao criar tabela {table_name}: {e}")

        # Inserir dados iniciais
        self.inserir_dados_iniciais()

    def inserir_dados_iniciais(self):
        """Insere dados iniciais no sistema incluindo PDV"""
        # Verificar se já existe admin
        self.cursor.execute("SELECT COUNT(*) as count FROM usuarios")
        if self.cursor.fetchone()['count'] == 0:
            # Criar usuário admin padrão
            senha_hash = self.hash_senha('12345')
            self.cursor.execute('''
                INSERT INTO usuarios (numero_trabalhador, nome, senha_hash, nivel_acesso)
                VALUES (%s, %s, %s, %s)
            ''', ('00001', 'Administrador', senha_hash, 'ADMIN'))
            # Criar PDV padrão
            self.cursor.execute('''
                INSERT INTO pontos_venda (numero_caixa, descricao_caixa, localizacao)
                VALUES (%s, %s, %s)
            ''', (self.numero_caixa, self.descricao_caixa, self.localizacao_caixa))
            # Criar categorias padrão
            categorias = ['Alimentos', 'Bebidas', 'Limpeza', 'Higiene', 'Outros']
            for categoria in categorias:
                self.cursor.execute('''
                    INSERT INTO categorias (nome) VALUES (%s)
                ''', (categoria,))
            
            print("✅ Dados iniciais inseridos com sucesso!")

    def hash_senha(self, senha):
        """Gera hash da senha"""
        return hashlib.sha256(senha.encode()).hexdigest()

    def verificar_senha(self, senha, senha_hash):
        """Verifica se a senha corresponde ao hash - VERSÃO CORRIGIDA"""
        try:
            # Gerar hash da senha digitada
            senha_hash_digitada = self.hash_senha(senha)
            
            print(f"🔐 Comparando hashes:")  # DEBUG
            print(f"🔐 Hash digitado: {senha_hash_digitada}")  # DEBUG
            print(f"🔐 Hash no banco: {senha_hash}")  # DEBUG
            print(f"🔐 São iguais? {senha_hash_digitada == senha_hash}")  # DEBUG
            
            return senha_hash_digitada == senha_hash
        except Exception as e:
            print(f"❌ Erro ao verificar senha: {e}")  # DEBUG
            return False

    def registrar_auditoria(self, acao, descricao="", tabela_afetada="", registro_id=None):
        """Registra ação na tabela de auditoria"""
        if not self.operador_atual:
            return
            
        try:
            self.cursor.execute('''
                INSERT INTO auditoria (data_hora, usuario_id, acao, descricao, tabela_afetada, registro_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (datetime.now(), self.operador_atual['id'], acao, descricao, tabela_afetada, registro_id))
        except Exception as e:
            print(f"Erro ao registrar auditoria: {e}")

# =============================================================================
# MÓDULO DE ADMINISTRAÇÃO
# =============================================================================

    def mostrar_modulo_administracao(self):
        """Mostra o módulo de administração com aba de Promoções"""
        if not self.verificar_acesso_supervisor():
            return
    
        admin_window = tk.Toplevel(self.root)
        admin_window.title("Módulo de Administração")
        admin_window.geometry("1100x750")
        admin_window.transient(self.root)
        admin_window.grab_set()
    
        # Centralizar
        admin_window.update_idletasks()
        width = 1100
        height = 750
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        admin_window.geometry(f'{width}x{height}+{x}+{y}')
    
        # Notebook para abas
        notebook = ttk.Notebook(admin_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        # Aba Usuários
        frame_usuarios = ttk.Frame(notebook)
        notebook.add(frame_usuarios, text="👥 Gestão de Usuários")
        self.criar_aba_usuarios(frame_usuarios)
    
        # Aba Produtos
        frame_produtos = ttk.Frame(notebook)
        notebook.add(frame_produtos, text="📦 Gestão de Produtos")
        self.criar_aba_produtos(frame_produtos)
    
        # NOVA ABA: Promoções
        frame_promocoes = ttk.Frame(notebook)
        notebook.add(frame_promocoes, text="🎯 Gestão de Promoções")
        self.criar_aba_promocoes(frame_promocoes)
    
        # Aba Relatórios
        frame_relatorios = ttk.Frame(notebook)
        notebook.add(frame_relatorios, text="📊 Dashboard e Relatórios")
        self.criar_aba_relatorios(frame_relatorios)
    
        # Aba Vendas
        frame_vendas = ttk.Frame(notebook)
        notebook.add(frame_vendas, text="💰 Gestão de Vendas")
        self.criar_aba_vendas(frame_vendas)
    
        # Aba Auditoria
        frame_auditoria = ttk.Frame(notebook)
        notebook.add(frame_auditoria, text="🔍 Auditoria")
        self.criar_aba_auditoria(frame_auditoria)

    def criar_aba_usuarios(self, parent):
        """Cria aba de gestão de usuários"""
        # Frame de controles
        controles_frame = tk.Frame(parent)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(controles_frame, text="➕ Novo Usuário", 
                 command=self.cadastrar_usuario, bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="✏️ Editar", 
                 command=self.editar_usuario, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="🚫 Ativar/Desativar", 
                 command=self.alterar_status_usuario, bg='#e67e22', fg='white').pack(side=tk.LEFT, padx=5)

        # Treeview de usuários
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('id', 'numero', 'nome', 'nivel', 'status', 'ultimo_login')
        self.tree_usuarios = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        self.tree_usuarios.heading('id', text='ID')
        self.tree_usuarios.heading('numero', text='Nº Trabalhador')
        self.tree_usuarios.heading('nome', text='Nome')
        self.tree_usuarios.heading('nivel', text='Nível Acesso')
        self.tree_usuarios.heading('status', text='Status')
        self.tree_usuarios.heading('ultimo_login', text='Último Login')

        for col in columns:
            self.tree_usuarios.column(col, width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_usuarios.yview)
        self.tree_usuarios.configure(yscrollcommand=scrollbar.set)

        self.tree_usuarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Carregar dados
        self.carregar_usuarios()

    def carregar_usuarios(self):
        """Carrega usuários na treeview"""
        for item in self.tree_usuarios.get_children():
            self.tree_usuarios.delete(item)

        self.cursor.execute('''
            SELECT id, numero_trabalhador, nome, nivel_acesso, ativo, ultimo_login
            FROM usuarios ORDER BY nome
        ''')
        
        for usuario in self.cursor.fetchall():
            status = "Ativo" if usuario['ativo'] else "Inativo"
            ultimo_login = usuario['ultimo_login'].strftime('%d/%m/%Y %H:%M') if usuario['ultimo_login'] else "Nunca"
            
            self.tree_usuarios.insert('', tk.END, values=(
                usuario['id'],
                usuario['numero_trabalhador'],
                usuario['nome'],
                usuario['nivel_acesso'],
                status,
                ultimo_login
            ))

    def cadastrar_usuario(self):
        """Cadastra novo usuário"""
        if not self.verificar_acesso_supervisor():
            return

        cadastro_window = tk.Toplevel(self.root)
        cadastro_window.title("Cadastrar Novo Usuário")
        cadastro_window.geometry("400x400")
        cadastro_window.transient(self.root)
        cadastro_window.grab_set()

        tk.Label(cadastro_window, text="Nº Trabalhador:").pack(pady=5)
        numero_var = tk.StringVar()
        tk.Entry(cadastro_window, textvariable=numero_var, width=20).pack(pady=5)

        tk.Label(cadastro_window, text="Nome Completo:").pack(pady=5)
        nome_var = tk.StringVar()
        tk.Entry(cadastro_window, textvariable=nome_var, width=30).pack(pady=5)

        tk.Label(cadastro_window, text="Senha (5+ dígitos):").pack(pady=5)
        senha_var = tk.StringVar()
        tk.Entry(cadastro_window, textvariable=senha_var, show='*', width=20).pack(pady=5)

        tk.Label(cadastro_window, text="Confirmar Senha:").pack(pady=5)
        confirmar_var = tk.StringVar()
        tk.Entry(cadastro_window, textvariable=confirmar_var, show='*', width=20).pack(pady=5)

        tk.Label(cadastro_window, text="Nível de Acesso:").pack(pady=5)
        nivel_var = tk.StringVar(value="OPERADOR")
        nivel_combo = ttk.Combobox(cadastro_window, textvariable=nivel_var, 
                                  values=['OPERADOR', 'SUPERVISOR', 'ADMIN'], state='readonly')
        nivel_combo.pack(pady=5)

        def salvar_usuario():
            if not all([numero_var.get(), nome_var.get(), senha_var.get()]):
                messagebox.showerror("Erro", "Preencha todos os campos!")
                return

            if len(senha_var.get()) < 5:
                messagebox.showerror("Erro", "Senha deve ter pelo menos 5 dígitos!")
                return

            if senha_var.get() != confirmar_var.get():
                messagebox.showerror("Erro", "Senhas não coincidem!")
                return

            try:
                senha_hash = self.hash_senha(senha_var.get())
                
                self.cursor.execute('''
                    INSERT INTO usuarios (numero_trabalhador, nome, senha_hash, nivel_acesso, criado_por)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (numero_var.get(), nome_var.get(), senha_hash, nivel_var.get(), self.operador_atual['id']))
                
                self.registrar_auditoria('CADASTRO_USUARIO', 
                                       f'Novo usuário: {nome_var.get()} ({numero_var.get()})',
                                       'usuarios', self.cursor.lastrowid)
                
                messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
                cadastro_window.destroy()
                self.carregar_usuarios()

            except mysql.connector.Error as e:
                messagebox.showerror("Erro", f"Erro ao cadastrar usuário: {e}")

        tk.Button(cadastro_window, text="Salvar", command=salvar_usuario,
                 bg='#27ae60', fg='white').pack(pady=20)

    def editar_usuario(self):
        """Edita usuário selecionado"""
        selecao = self.tree_usuarios.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um usuário!")
            return

        if not self.verificar_acesso_supervisor():
            return

        item = self.tree_usuarios.item(selecao[0])
        usuario_id = item['values'][0]

        self.cursor.execute('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
        usuario = self.cursor.fetchone()

        editar_window = tk.Toplevel(self.root)
        editar_window.title("Editar Usuário")
        editar_window.geometry("400x300")
        editar_window.transient(self.root)
        editar_window.grab_set()

        tk.Label(editar_window, text="Nº Trabalhador:").pack(pady=5)
        numero_var = tk.StringVar(value=usuario['numero_trabalhador'])
        tk.Entry(editar_window, textvariable=numero_var, width=20, state='readonly').pack(pady=5)

        tk.Label(editar_window, text="Nome Completo:").pack(pady=5)
        nome_var = tk.StringVar(value=usuario['nome'])
        tk.Entry(editar_window, textvariable=nome_var, width=30).pack(pady=5)

        tk.Label(editar_window, text="Nível de Acesso:").pack(pady=5)
        nivel_var = tk.StringVar(value=usuario['nivel_acesso'])
        nivel_combo = ttk.Combobox(editar_window, textvariable=nivel_var,
                                  values=['OPERADOR', 'SUPERVISOR', 'ADMIN'], state='readonly')
        nivel_combo.pack(pady=5)

        def salvar_edicao():
            self.cursor.execute('''
                UPDATE usuarios SET nome = %s, nivel_acesso = %s
                WHERE id = %s
            ''', (nome_var.get(), nivel_var.get(), usuario_id))
            
            self.registrar_auditoria('EDICAO_USUARIO', 
                                   f'Usuário editado: {usuario["nome"]}',
                                   'usuarios', usuario_id)
            
            messagebox.showinfo("Sucesso", "Usuário atualizado!")
            editar_window.destroy()
            self.carregar_usuarios()

        tk.Button(editar_window, text="Salvar", command=salvar_edicao,
                 bg='#3498db', fg='white').pack(pady=20)

    def alterar_status_usuario(self):
        """Ativa/desativa usuário"""
        selecao = self.tree_usuarios.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um usuário!")
            return

        if not self.verificar_acesso_supervisor():
            return

        item = self.tree_usuarios.item(selecao[0])
        usuario_id = item['values'][0]
        usuario_nome = item['values'][2]
        status_atual = item['values'][4]

        novo_status = not (status_atual == "Ativo")
        status_text = "ativar" if novo_status else "desativar"

        if messagebox.askyesno("Confirmar", f"Deseja {status_text} o usuário {usuario_nome}?"):
            self.cursor.execute('UPDATE usuarios SET ativo = %s WHERE id = %s', 
                              (novo_status, usuario_id))
            
            self.registrar_auditoria('ALTERACAO_STATUS_USUARIO',
                                   f'Status alterado para: {status_text} - Usuário: {usuario_nome}',
                                   'usuarios', usuario_id)
            
            messagebox.showinfo("Sucesso", f"Usuário {status_text}do com sucesso!")
            self.carregar_usuarios()

    def criar_aba_produtos(self, parent):
        """Cria aba de gestão de produtos"""
        # Frame de controles
        controles_frame = tk.Frame(parent)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(controles_frame, text="➕ Novo Produto", 
                 command=self.cadastrar_produto, bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="✏️ Editar", 
                 command=self.editar_produto, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="📊 Estoque", 
                 command=self.gerenciar_estoque, bg='#e67e22', fg='white').pack(side=tk.LEFT, padx=5)

        # Treeview de produtos
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('id', 'codigo', 'nome', 'categoria', 'preco', 'estoque', 'status')
        self.tree_produtos = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col, text in zip(columns, ['ID', 'Código', 'Nome', 'Categoria', 'Preço', 'Estoque', 'Status']):
            self.tree_produtos.heading(col, text=text)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_produtos.yview)
        self.tree_produtos.configure(yscrollcommand=scrollbar.set)

        self.tree_produtos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Carregar dados
        self.carregar_produtos()

    def carregar_produtos(self):
        """Carrega produtos na treeview"""
        for item in self.tree_produtos.get_children():
            self.tree_produtos.delete(item)

        self.cursor.execute('''
            SELECT p.id, p.codigo, p.nome, c.nome as categoria, p.preco, p.estoque, p.ativo
            FROM produtos p LEFT JOIN categorias c ON p.categoria_id = c.id
            ORDER BY p.nome
        ''')
        
        for produto in self.cursor.fetchall():
            status = "Ativo" if produto['ativo'] else "Inativo"
            self.tree_produtos.insert('', tk.END, values=(
                produto['id'],
                produto['codigo'],
                produto['nome'],
                produto['categoria'],
                f"R$ {produto['preco']:.2f}",
                produto['estoque'],
                status
            ))

    def cadastrar_produto(self):
        """Cadastra novo produto"""
        if not self.verificar_acesso_supervisor():
            return

        cadastro_window = tk.Toplevel(self.root)
        cadastro_window.title("Cadastrar Novo Produto")
        cadastro_window.geometry("500x500")
        cadastro_window.transient(self.root)
        cadastro_window.grab_set()

        # Campos do formulário
        campos = [
            ("Código:", "codigo"),
            ("Nome:", "nome"),
            ("Descrição:", "descricao"),
            ("Preço:", "preco"),
            ("Preço de Custo:", "preco_custo"),
            ("Estoque:", "estoque"),
            ("Estoque Mínimo:", "estoque_minimo")
        ]

        variaveis = {}
        for i, (label, nome) in enumerate(campos):
            tk.Label(cadastro_window, text=label).pack(pady=5)
            var = tk.StringVar()
            if "preco" in label.lower():
                tk.Entry(cadastro_window, textvariable=var, width=30).pack(pady=5)
            else:
                tk.Entry(cadastro_window, textvariable=var, width=30).pack(pady=5)
            variaveis[nome] = var

        # Categoria
        tk.Label(cadastro_window, text="Categoria:").pack(pady=5)
        categoria_var = tk.StringVar()
        self.cursor.execute("SELECT id, nome FROM categorias WHERE ativo = TRUE")
        categorias = [cat['nome'] for cat in self.cursor.fetchall()]
        categoria_combo = ttk.Combobox(cadastro_window, textvariable=categoria_var, values=categorias)
        categoria_combo.pack(pady=5)

        def salvar_produto():
            try:
                # Buscar ID da categoria
                self.cursor.execute("SELECT id FROM categorias WHERE nome = %s", (categoria_var.get(),))
                categoria_id = self.cursor.fetchone()['id'] if self.cursor.fetchone() else None

                self.cursor.execute('''
                    INSERT INTO produtos (codigo, nome, descricao, preco, preco_custo, estoque, 
                                        estoque_minimo, categoria_id, cadastrado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    variaveis['codigo'].get(),
                    variaveis['nome'].get(),
                    variaveis['descricao'].get(),
                    float(variaveis['preco'].get().replace(',', '.')),
                    float(variaveis['preco_custo'].get().replace(',', '.')) if variaveis['preco_custo'].get() else None,
                    int(variaveis['estoque'].get()),
                    int(variaveis['estoque_minimo'].get()),
                    categoria_id,
                    self.operador_atual['id']
                ))

                produto_id = self.cursor.lastrowid
                self.registrar_auditoria('CADASTRO_PRODUTO',
                                       f'Novo produto: {variaveis["nome"].get()}',
                                       'produtos', produto_id)

                messagebox.showinfo("Sucesso", "Produto cadastrado com sucesso!")
                cadastro_window.destroy()
                self.carregar_produtos()

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao cadastrar produto: {e}")

        tk.Button(cadastro_window, text="Salvar", command=salvar_produto,
                 bg='#27ae60', fg='white').pack(pady=20)

    def criar_aba_relatorios(self, parent):
        """Cria aba de relatórios e dashboard"""
        # Frame principal com notebook
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Aba Dashboard
        frame_dashboard = ttk.Frame(notebook)
        notebook.add(frame_dashboard, text="📈 Dashboard")

        # Aba Relatórios
        frame_relatorios = ttk.Frame(notebook)
        notebook.add(frame_relatorios, text="📋 Relatórios")

        self.criar_dashboard(frame_dashboard)
        self.criar_relatorios_detalhados(frame_relatorios)

    def criar_dashboard(self, parent):
        """Cria dashboard com métricas"""
        # Frame de métricas
        metricas_frame = tk.Frame(parent)
        metricas_frame.pack(fill=tk.X, padx=10, pady=10)
    
        # Métricas rápidas
        metricas = [
            ("💰 Vendas Hoje", "SELECT COALESCE(SUM(total), 0) as total FROM vendas WHERE DATE(data_hora) = CURDATE() AND status = 'FINALIZADA'"),
            ("📦 Produtos Vendidos", "SELECT COALESCE(SUM(quantidade), 0) as total FROM itens_venda iv JOIN vendas v ON iv.venda_id = v.id WHERE DATE(v.data_hora) = CURDATE() AND v.status = 'FINALIZADA'"),
            ("👥 Clientes Atendidos", "SELECT COUNT(DISTINCT cliente_id) as total FROM vendas WHERE DATE(data_hora) = CURDATE() AND status = 'FINALIZADA' AND cliente_id IS NOT NULL"),
            ("⚠️ Produtos em Falta", "SELECT COUNT(*) as total FROM produtos WHERE estoque <= estoque_minimo AND ativo = TRUE")
        ]
    
        for i, (titulo, query) in enumerate(metricas):
            frame_metrica = tk.Frame(metricas_frame, relief=tk.RAISED, bd=1)
            frame_metrica.grid(row=0, column=i, padx=5, pady=5, sticky='nsew')
            
            try:
                self.cursor.execute(query)
                resultado = self.cursor.fetchone()
                # CORREÇÃO: Acessar pelo nome da coluna diretamente
                valor = resultado['total'] if resultado else 0
            except Exception as e:
                print(f"Erro ao executar query {titulo}: {e}")
                valor = 0
            
            tk.Label(frame_metrica, text=titulo, font=('Arial', 10, 'bold')).pack(pady=5)
            tk.Label(frame_metrica, text=str(valor), font=('Arial', 14, 'bold'), fg='#2c3e50').pack(pady=5)
    
        for i in range(len(metricas)):
            metricas_frame.columnconfigure(i, weight=1)

    def criar_relatorios_detalhados(self, parent):
        """Cria relatórios detalhados"""
        controles_frame = tk.Frame(parent)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(controles_frame, text="Período:").pack(side=tk.LEFT, padx=5)
        
        data_inicio_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        data_fim_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        
        tk.Entry(controles_frame, textvariable=data_inicio_var, width=12).pack(side=tk.LEFT, padx=5)
        tk.Label(controles_frame, text="até").pack(side=tk.LEFT, padx=5)
        tk.Entry(controles_frame, textvariable=data_fim_var, width=12).pack(side=tk.LEFT, padx=5)

        tipos_relatorio = ['Vendas por Dia', 'Produtos Mais Vendidos', 'Formas de Pagamento', 'Desempenho Operadores']
        tipo_var = tk.StringVar(value=tipos_relatorio[0])
        tipo_combo = ttk.Combobox(controles_frame, textvariable=tipo_var, values=tipos_relatorio, state='readonly')
        tipo_combo.pack(side=tk.LEFT, padx=10)

        def gerar_relatorio():
            try:
                data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')
                
                if tipo_var.get() == 'Vendas por Dia':
                    self.relatorio_vendas_dia(data_inicio, data_fim)
                elif tipo_var.get() == 'Produtos Mais Vendidos':
                    self.relatorio_produtos_mais_vendidos(data_inicio, data_fim)
                    
            except ValueError:
                messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")

        tk.Button(controles_frame, text="Gerar Relatório", command=gerar_relatorio,
                 bg='#3498db', fg='white').pack(side=tk.LEFT, padx=10)

    def relatorio_vendas_dia(self, data_inicio, data_fim):
        """Gera relatório de vendas por dia"""
        relatorio_window = tk.Toplevel(self.root)
        relatorio_window.title(f"Relatório de Vendas - {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
        relatorio_window.geometry("800x600")

        self.cursor.execute('''
            SELECT DATE(data_hora) as data, 
                   COUNT(*) as num_vendas,
                   SUM(total) as total_vendas
            FROM vendas 
            WHERE DATE(data_hora) BETWEEN %s AND %s 
            AND status = 'FINALIZADA'
            GROUP BY DATE(data_hora)
            ORDER BY data
        ''', (data_inicio, data_fim))

        dados = self.cursor.fetchall()

        tree_frame = tk.Frame(relatorio_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tree = ttk.Treeview(tree_frame, columns=('data', 'vendas', 'total'), show='headings')
        tree.heading('data', text='Data')
        tree.heading('vendas', text='Nº Vendas')
        tree.heading('total', text='Total Vendas')

        for row in dados:
            tree.insert('', tk.END, values=(
                row['data'].strftime('%d/%m/%Y'),
                row['num_vendas'],
                f"R$ {row['total_vendas']:.2f}"
            ))

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def criar_aba_vendas(self, parent):
        """Cria aba de gestão de vendas"""
        controles_frame = tk.Frame(parent)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(controles_frame, text="📋 Consultar Vendas", 
                 command=self.consultar_vendas, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="❌ Cancelar Venda", 
                 command=self.cancelar_venda, bg='#e74c3c', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="🔄 Devolução", 
                 command=self.processar_devolucao, bg='#9b59b6', fg='white').pack(side=tk.LEFT, padx=5)

    def consultar_vendas(self):
        """Consulta vendas realizadas"""
        if not self.verificar_acesso_supervisor():
            return

        consulta_window = tk.Toplevel(self.root)
        consulta_window.title("Consulta de Vendas")
        consulta_window.geometry("1000x600")

        # Filtros
        filtros_frame = tk.Frame(consulta_window)
        filtros_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(filtros_frame, text="Data Início:").grid(row=0, column=0, padx=5)
        data_inicio_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        tk.Entry(filtros_frame, textvariable=data_inicio_var, width=12).grid(row=0, column=1, padx=5)

        tk.Label(filtros_frame, text="Data Fim:").grid(row=0, column=2, padx=5)
        data_fim_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        tk.Entry(filtros_frame, textvariable=data_fim_var, width=12).grid(row=0, column=3, padx=5)

        def carregar_vendas():
            try:
                data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')

                self.cursor.execute('''
                    SELECT v.id, v.data_hora, v.total, v.forma_pagamento, 
                           u.nome as operador, v.status
                    FROM vendas v 
                    JOIN usuarios u ON v.operador_id = u.id
                    WHERE DATE(v.data_hora) BETWEEN %s AND %s
                    ORDER BY v.data_hora DESC
                ''', (data_inicio, data_fim))

                for item in tree.get_children():
                    tree.delete(item)

                for venda in self.cursor.fetchall():
                    tree.insert('', tk.END, values=(
                        venda['id'],
                        venda['data_hora'].strftime('%d/%m/%Y %H:%M'),
                        f"R$ {venda['total']:.2f}",
                        venda['forma_pagamento'],
                        venda['operador'],
                        venda['status']
                    ))

            except ValueError:
                messagebox.showerror("Erro", "Data inválida!")

        tk.Button(filtros_frame, text="Buscar", command=carregar_vendas,
                 bg='#3498db', fg='white').grid(row=0, column=4, padx=10)

        # Treeview de vendas
        tree_frame = tk.Frame(consulta_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('id', 'data', 'total', 'pagamento', 'operador', 'status')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col, text in zip(columns, ['ID', 'Data/Hora', 'Total', 'Pagamento', 'Operador', 'Status']):
            tree.heading(col, text=text)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        carregar_vendas()

    def cancelar_venda(self):
        """Cancela uma venda com autorização do supervisor"""
        if not self.verificar_acesso_supervisor():
            return

        venda_id = simpledialog.askinteger("Cancelar Venda", "Número da venda a cancelar:")
        if not venda_id:
            return

        self.cursor.execute('''
            SELECT v.*, u.nome as operador_nome 
            FROM vendas v 
            JOIN usuarios u ON v.operador_id = u.id 
            WHERE v.id = %s
        ''', (venda_id,))
        
        venda = self.cursor.fetchone()
        
        if not venda:
            messagebox.showerror("Erro", "Venda não encontrada!")
            return

        if venda['status'] == 'CANCELADA':
            messagebox.showwarning("Aviso", "Esta venda já está cancelada!")
            return

        motivo = simpledialog.askstring("Cancelar Venda", "Motivo do cancelamento:")
        if not motivo:
            return

        # Confirmar cancelamento
        if messagebox.askyesno("Confirmar", f"Cancelar venda {venda_id}?\nTotal: R$ {venda['total']:.2f}\nMotivo: {motivo}"):
            try:
                # Atualizar status da venda
                self.cursor.execute('''
                    UPDATE vendas 
                    SET status = 'CANCELADA', 
                        motivo_cancelamento = %s,
                        cancelado_por = %s,
                        data_cancelamento = %s
                    WHERE id = %s
                ''', (motivo, self.operador_atual['id'], datetime.now(), venda_id))

                # Restaurar estoque
                self.cursor.execute('''
                    UPDATE produtos p
                    JOIN itens_venda iv ON p.id = iv.produto_id
                    SET p.estoque = p.estoque + iv.quantidade
                    WHERE iv.venda_id = %s AND iv.cancelado = FALSE
                ''', (venda_id,))

                self.registrar_auditoria('CANCELAMENTO_VENDA',
                                       f'Venda {venda_id} cancelada. Motivo: {motivo}',
                                       'vendas', venda_id)

                messagebox.showinfo("Sucesso", "Venda cancelada com sucesso!")

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao cancelar venda: {e}")

    def processar_devolucao(self):
        """Processa devolução de itens"""
        if not self.verificar_acesso_supervisor():
            return

        venda_id = simpledialog.askinteger("Devolução", "Número da venda:")
        if not venda_id:
            return

        # Buscar itens da venda
        self.cursor.execute('''
            SELECT iv.id, p.nome, iv.quantidade, iv.preco_unitario, iv.subtotal
            FROM itens_venda iv
            JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = %s AND iv.cancelado = FALSE
        ''', (venda_id,))
        
        itens = self.cursor.fetchall()
        
        if not itens:
            messagebox.showerror("Erro", "Nenhum item encontrado para esta venda!")
            return

        devolucao_window = tk.Toplevel(self.root)
        devolucao_window.title(f"Devolução - Venda {venda_id}")
        devolucao_window.geometry("600x400")

        tk.Label(devolucao_window, text="Selecione os itens para devolver:", 
                font=('Arial', 12, 'bold')).pack(pady=10)

        # Lista de itens com checkboxes
        var_itens = {}
        for item in itens:
            frame_item = tk.Frame(devolucao_window)
            frame_item.pack(fill=tk.X, padx=20, pady=2)
            
            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame_item, variable=var)
            chk.pack(side=tk.LEFT)
            
            tk.Label(frame_item, 
                    text=f"{item['nome']} - Qtd: {item['quantidade']} - R$ {item['subtotal']:.2f}").pack(side=tk.LEFT)
            
            var_itens[item['id']] = var

        def confirmar_devolucao():
            itens_selecionados = [item_id for item_id, var in var_itens.items() if var.get()]
            
            if not itens_selecionados:
                messagebox.showwarning("Aviso", "Selecione pelo menos um item!")
                return

            motivo = simpledialog.askstring("Devolução", "Motivo da devolução:")
            if not motivo:
                return

            try:
                for item_id in itens_selecionados:
                    # Marcar item como cancelado
                    self.cursor.execute('''
                        UPDATE itens_venda 
                        SET cancelado = TRUE,
                            motivo_cancelamento = %s,
                            cancelado_por = %s,
                            data_cancelamento = %s
                        WHERE id = %s
                    ''', (motivo, self.operador_atual['id'], datetime.now(), item_id))

                    # Restaurar estoque
                    self.cursor.execute('''
                        UPDATE produtos p
                        JOIN itens_venda iv ON p.id = iv.produto_id
                        SET p.estoque = p.estoque + iv.quantidade
                        WHERE iv.id = %s
                    ''', (item_id,))

                self.registrar_auditoria('DEVOLUCAO_ITENS',
                                       f'Devolução de {len(itens_selecionados)} itens da venda {venda_id}',
                                       'itens_venda', venda_id)

                messagebox.showinfo("Sucesso", "Devolução processada com sucesso!")
                devolucao_window.destroy()

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao processar devolução: {e}")

        tk.Button(devolucao_window, text="Confirmar Devolução", 
                 command=confirmar_devolucao, bg='#9b59b6', fg='white').pack(pady=20)

    def criar_aba_auditoria(self, parent):
        """Cria aba de auditoria do sistema"""
        # Filtros
        filtros_frame = tk.Frame(parent)
        filtros_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(filtros_frame, text="Data Início:").grid(row=0, column=0, padx=5)
        data_inicio_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime('%d/%m/%Y'))
        tk.Entry(filtros_frame, textvariable=data_inicio_var, width=12).grid(row=0, column=1, padx=5)

        tk.Label(filtros_frame, text="Data Fim:").grid(row=0, column=2, padx=5)
        data_fim_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        tk.Entry(filtros_frame, textvariable=data_fim_var, width=12).grid(row=0, column=3, padx=5)

        def carregar_auditoria():
            try:
                data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')

                self.cursor.execute('''
                    SELECT a.data_hora, u.nome as usuario, a.acao, a.descricao, a.tabela_afetada
                    FROM auditoria a
                    JOIN usuarios u ON a.usuario_id = u.id
                    WHERE DATE(a.data_hora) BETWEEN %s AND %s
                    ORDER BY a.data_hora DESC
                ''', (data_inicio, data_fim))

                for item in tree.get_children():
                    tree.delete(item)

                for registro in self.cursor.fetchall():
                    tree.insert('', tk.END, values=(
                        registro['data_hora'].strftime('%d/%m/%Y %H:%M:%S'),
                        registro['usuario'],
                        registro['acao'],
                        registro['descricao'],
                        registro['tabela_afetada']
                    ))

            except ValueError:
                messagebox.showerror("Erro", "Data inválida!")

        tk.Button(filtros_frame, text="Carregar", command=carregar_auditoria,
                 bg='#3498db', fg='white').grid(row=0, column=4, padx=10)

        # Treeview de auditoria
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('data', 'usuario', 'acao', 'descricao', 'tabela')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col, text in zip(columns, ['Data/Hora', 'Usuário', 'Ação', 'Descrição', 'Tabela']):
            tree.heading(col, text=text)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        carregar_auditoria()

# =============================================================================
# SUPERVISOR
# =============================================================================
   # Adicione estas funções na classe SistemaVendasProfissional:

    def criar_botoes_supervisor_especiais(self, parent):
        """Cria botões especiais para supervisor"""
        especiais_frame = tk.Frame(parent, bg='#34495e')
        especiais_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(especiais_frame, text="FUNÇÕES ESPECIAIS:", 
                font=('Arial', 10, 'bold'), bg='#34495e', fg='#ecf0f1').pack(pady=5)
        
        # Frame para os botões em grid
        botoes_frame = tk.Frame(especiais_frame, bg='#34495e')
        botoes_frame.pack(fill=tk.X, pady=5)
        
        # Botão Supervisor (expandível)
        self.btn_supervisor = tk.Button(botoes_frame, text="👨‍💼 SUPERVISOR", 
                                       font=('Arial', 9, 'bold'),
                                       bg='#e67e22', fg='white', height=2,
                                       command=self.mostrar_menu_supervisor)
        self.btn_supervisor.grid(row=0, column=0, padx=2, pady=2, sticky='ew')
        
        # Botão Balança
        btn_balanca = tk.Button(botoes_frame, text="⚖️ BALANÇA", 
                               font=('Arial', 9, 'bold'),
                               bg='#9b59b6', fg='white', height=2,
                               command=self.funcao_balanca)
        btn_balanca.grid(row=0, column=1, padx=2, pady=2, sticky='ew')
        
        # Botão Consultar Preço
        btn_consultar_preco = tk.Button(botoes_frame, text="💰 CONSULTAR PREÇO", 
                                       font=('Arial', 9, 'bold'),
                                       bg='#3498db', fg='white', height=2,
                                       command=self.consultar_preco)
        btn_consultar_preco.grid(row=1, column=0, padx=2, pady=2, sticky='ew')
        
        # Botão Eliminar Item
        btn_eliminar_item = tk.Button(botoes_frame, text="❌ ELIMINAR ITEM", 
                                     font=('Arial', 9, 'bold'),
                                     bg='#e74c3c', fg='white', height=2,
                                     command=self.eliminar_item_venda)
        btn_eliminar_item.grid(row=1, column=1, padx=2, pady=2, sticky='ew')
        
        # Configurar grid para expandir
        botoes_frame.columnconfigure(0, weight=1)
        botoes_frame.columnconfigure(1, weight=1)
    
    def mostrar_menu_supervisor(self):
        """Mostra menu expandido do supervisor"""
        # Verificar acesso com cartão + credenciais
        if not self.verificar_acesso_supervisor_com_cartao():
            return
        
        # Criar janela de menu do supervisor
        menu_window = tk.Toplevel(self.root)
        menu_window.title("Menu Supervisor")
        menu_window.geometry("300x400")
        menu_window.transient(self.root)
        menu_window.grab_set()
        
        # Centralizar
        menu_window.update_idletasks()
        width = 350
        height = 700
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        menu_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Título
        tk.Label(menu_window, text="👨‍💼 MENU SUPERVISOR", 
                font=('Arial', 16, 'bold'), fg='#2c3e50').pack(pady=20)
        
        # Frame dos botões
        botoes_frame = tk.Frame(menu_window)
        botoes_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Botões do menu supervisor
        botoes_supervisor = [
            ("🖥️ INFO PDV", self.mostrar_info_pdv, '#3498db'),
            ("🎯 DESCONTO", self.aplicar_desconto_supervisor, '#9b59b6'),
            ("💰 MOVIMENTO CAIXA", self.movimento_caixa, '#3498db'),
            ("💸 SANGRIA", self.sangria_caixa, '#e74c3c'),
            ("📊 FECHAR CAIXA", self.fechar_caixa, '#e74c3c'),
            ("🚪 SAÍDA", self.saida_operador, '#7f8c8d'),
            ("❌ CANCELAR VENDA", self.cancelar_venda_supervisor, '#c0392b'),
            ("📈 RELATÓRIOS", self.mostrar_relatorios_supervisor, '#27ae60'),
            ("⚙️ ADMINISTRAÇÃO", self.mostrar_modulo_administracao, '#34495e'),
            ("👥 GERENCIAR CLIENTES", self.gerenciar_clientes_completo, '#16a085'),
            ("📦 GERENCIAR ESTOQUE", self.gerenciar_estoque, '#f39c12')
        ]
        
        for texto, comando, cor in botoes_supervisor:
            btn = tk.Button(botoes_frame, text=texto, font=('Arial', 11, 'bold'),
                           bg=cor, fg='white', height=2, width=20,
                           command=comando, wraplength=250)
            btn.pack(fill=tk.X, pady=3)
        
        # Botão fechar
        tk.Button(menu_window, text="❌ FECHAR", command=menu_window.destroy,
                 bg='#7f8c8d', fg='white', font=('Arial', 10, 'bold')).pack(pady=10)
    
    def aplicar_desconto_supervisor(self):
        """Aplica desconto com autorização de supervisor"""
        if not self.verificar_acesso_supervisor():
            return
        
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        total = sum(item['subtotal'] for item in self.venda_atual)
        
        desconto = simpledialog.askfloat("Desconto Supervisor", 
                                       f"Digite o valor do desconto:\n\nTotal: R$ {total:.2f}",
                                       minvalue=0, maxvalue=total)
        
        if desconto is not None:
            self.desconto_aplicado = desconto
            self.atualizar_display()
            messagebox.showinfo("Desconto", f"Desconto de R$ {desconto:.2f} aplicado com sucesso!")
            
            # Registrar auditoria
            self.registrar_auditoria('DESCONTO_SUPERVISOR', 
                                   f'Desconto aplicado: R$ {desconto:.2f}')
    
    def cancelar_venda_supervisor(self):
        """Cancela venda atual com autorização de supervisor"""
        if not self.verificar_acesso_supervisor():
            return
        
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhuma venda em andamento!")
            return
        
        total = self.calcular_total()
        
        resposta = messagebox.askyesno("Cancelar Venda", 
                                     f"Deseja cancelar a venda atual?\n\n"
                                     f"Total: R$ {total:.2f}\n"
                                     f"Itens: {len(self.venda_atual)}")
        
        if resposta:
            motivo = simpledialog.askstring("Motivo do Cancelamento", 
                                          "Informe o motivo do cancelamento:")
            if motivo is None:
                return
            
            # Registrar auditoria antes de limpar
            self.registrar_auditoria('CANCELAMENTO_VENDA_SUPERVISOR', 
                                   f'Venda cancelada. Motivo: {motivo}\n'
                                   f'Total: R$ {total:.2f}')
            
            self.limpar_venda()
            messagebox.showinfo("Sucesso", "Venda cancelada com sucesso!")
    
    def mostrar_relatorios_supervisor(self):
        """Mostra relatórios para supervisor"""
        if not self.verificar_acesso_supervisor():
            return
        
        relatorios_window = tk.Toplevel(self.root)
        relatorios_window.title("Relatórios Supervisor")
        relatorios_window.geometry("400x500")
        relatorios_window.transient(self.root)
        
        # Centralizar
        relatorios_window.update_idletasks()
        width = 400
        height = 500
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        relatorios_window.geometry(f'{width}x{height}+{x}+{y}')
        
        tk.Label(relatorios_window, text="📈 RELATÓRIOS", 
                font=('Arial', 16, 'bold')).pack(pady=20)
        
        # Frame dos botões
        botoes_frame = tk.Frame(relatorios_window)
        botoes_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        relatorios = [
            ("💰 VENDAS DO DIA", self.relatorio_vendas_dia_supervisor, '#27ae60'),
            ("📊 VENDAS POR PERÍODO", self.relatorio_vendas_periodo, '#3498db'),
            ("📦 ESTOQUE ATUAL", self.gerenciar_estoque, '#e67e22'),
            ("👥 CLIENTES", self.gerenciar_clientes_completo, '#9b59b6'),
            ("💳 MOVIMENTOS CAIXA", self.consulta_caixa, '#34495e'),
            ("🔍 AUDITORIA", self.criar_aba_auditoria, '#7f8c8d')
        ]
        
        for texto, comando, cor in relatorios:
            btn = tk.Button(botoes_frame, text=texto, font=('Arial', 11, 'bold'),
                           bg=cor, fg='white', height=2,
                           command=comando, wraplength=300)
            btn.pack(fill=tk.X, pady=3)
        
        tk.Button(relatorios_window, text="❌ FECHAR", command=relatorios_window.destroy,
                 bg='#e74c3c', fg='white').pack(pady=10)
    
    def relatorio_vendas_dia_supervisor(self):
        """Relatório de vendas do dia para supervisor"""
        if not self.verificar_acesso_supervisor():
            return
        
        data_hoje = datetime.now().strftime('%d/%m/%Y')
        
        try:
            self.cursor.execute('''
                SELECT COUNT(*) as total_vendas, 
                       COALESCE(SUM(total), 0) as total_valor,
                       COALESCE(SUM(troco), 0) as total_troco
                FROM vendas 
                WHERE DATE(data_hora) = CURDATE()
                AND status = 'FINALIZADA'
            ''')
            
            resultado = self.cursor.fetchone()
            total_vendas = resultado['total_vendas']
            total_valor = float(resultado['total_valor'])
            total_troco = float(resultado['total_troco'])
            
            # Vendas por forma de pagamento
            self.cursor.execute('''
                SELECT forma_pagamento, COUNT(*) as count, COALESCE(SUM(total), 0) as valor
                FROM vendas 
                WHERE DATE(data_hora) = CURDATE()
                AND status = 'FINALIZADA'
                GROUP BY forma_pagamento
            ''')
            
            formas = self.cursor.fetchall()
            
            relatorio = f"RELATÓRIO DO DIA - {data_hoje}\n"
            relatorio += "=" * 40 + "\n\n"
            relatorio += f"Total de Vendas: {total_vendas}\n"
            relatorio += f"Valor Total: R$ {total_valor:.2f}\n"
            relatorio += f"Total em Troco: R$ {total_troco:.2f}\n\n"
            relatorio += "Formas de Pagamento:\n"
            
            for forma in formas:
                relatorio += f"- {forma['forma_pagamento']}: {forma['count']} vendas (R$ {float(forma['valor']):.2f})\n"
            
            # Mostrar relatório
            self.mostrar_relatorio_detalhado(relatorio, self.root)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    
    def funcao_balanca(self):
        """Função para integração com balança (placeholder)"""
        messagebox.showinfo("Balança", "Funcionalidade de integração com balança.\n\n"
                                      "Em desenvolvimento...")
    
    # ADICIONE estes métodos para processar as entradas especiais:
# =============================================================================
# FUNÇÕES DE LOGIN NOVO INICI
# =============================================================================

    def fazer_login_display(self):
        """Realiza login usando display e teclado numérico"""
        self.modo_login = True
        self.etapa_login = 'NUMERO_TRABALHADOR'
        self.numero_trabalhador_login = ""
        self.senha_login = ""
        
        self.display_text = ""
        self.display_var.set("Digite nº trabalhador...")
        self.op_var.set("Sistema de Vendas - Login")
        self.op_secundario_var.set("Etapa 1/2: Nº Trabalhador")
        self.entrada_especial = 'LOGIN_SISTEMA'
        
        # Criar variável para resultado
        self.resultado_login = {'sucesso': False}
        
        # Esperar pelo login
        self.root.wait_variable(self._get_var_login())
        
        return self.resultado_login['sucesso']
    
    def _verificar_login_para_venda(self):
        """Verifica se há operador logado para operações de venda"""
        if not hasattr(self, 'operador_atual') or not self.operador_atual:
            self.display_var.set("🔒 Efetue login para esta operação")
            self.display_secundario_var.set("Façaa login")
            return False
        return True
    
    def _get_var_login(self):
        """Cria variável para monitorar resultado do login"""
        if not hasattr(self, '_var_login'):
            self._var_login = tk.BooleanVar()
        return self._var_login
    
    def _processar_login(self, tecla):
        """Processa teclas no modo login"""
        if tecla == '⌫':
            if self.etapa_login == 'NUMERO_TRABALHADOR':
                if self.numero_trabalhador_login:
                    self.numero_trabalhador_login = self.numero_trabalhador_login[:-1]
                    self.display_var.set(f"Nº: {self.numero_trabalhador_login}")
            elif self.etapa_login == 'SENHA':
                if self.senha_login:
                    self.senha_login = self.senha_login[:-1]
                    senha_oculta = '•' * len(self.senha_login)
                    self.display_var.set(f"Senha: {senha_oculta}")
        
        elif tecla == 'Enter ↵':
            if self.etapa_login == 'NUMERO_TRABALHADOR':
                if self.numero_trabalhador_login:
                    # Avançar para senha
                    self.etapa_login = 'SENHA'
                    self.display_text = ""
                    self.senha_login = ""
                    self.display_var.set("Digite senha...")
                    self.op_secundario_var.set("Etapa 2/2: Senha (5+ dígitos)")
                else:
                    self.display_var.set("Digite nº trabalhador!")
            
            elif self.etapa_login == 'SENHA':
                if len(self.senha_login) >= 5:
                    # Verificar login
                    self._validar_login()
                else:
                    self.display_var.set("Senha deve ter 5+ dígitos!")
        
        elif tecla == 'CANCELAR':
            self._cancelar_login()
        
        elif tecla.isdigit():
            if self.etapa_login == 'NUMERO_TRABALHADOR':
                if len(self.numero_trabalhador_login) < 10:
                    self.numero_trabalhador_login += tecla
                    self.display_var.set(f"Nº: {self.numero_trabalhador_login}")
            
            elif self.etapa_login == 'SENHA':
                if len(self.senha_login) < 15:
                    self.senha_login += tecla
                    senha_oculta = '•' * len(self.senha_login)
                    self.display_var.set(f"Senha: {senha_oculta}")
    
    def _verificar_operador_em_outro_pdv(self, operador_id):
        """Verifica se o operador já está logado em outro PDV"""
        try:
            # Buscar se há caixa aberto com este operador em outro PDV
            self.cursor.execute('''
                SELECT c.*, p.numero_caixa, p.descricao_caixa 
                FROM caixa c
                JOIN pontos_venda p ON c.ponto_venda_id = p.id
                WHERE c.operador_id = %s 
                AND c.status = 'ABERTO'
                AND p.numero_caixa != %s
            ''', (operador_id, self.numero_caixa))
            
            caixa_aberto = self.cursor.fetchone()
            
            if caixa_aberto:
                return {
                    'logado_em_outro_pdv': True,
                    'numero_caixa': caixa_aberto['numero_caixa'],
                    'descricao_caixa': caixa_aberto['descricao_caixa'],
                    'data_abertura': caixa_aberto['data_abertura']
                }
            else:
                return {'logado_em_outro_pdv': False}
                
        except Exception as e:
            print(f"❌ Erro ao verificar operador em outro PDV: {e}")
            return {'logado_em_outro_pdv': False}
    
    def _validar_login(self):
        """Valida as credenciais de login - COM VERIFICAÇÃO DE PDV"""
        try:
            numero = self.numero_trabalhador_login.strip()
            senha = self.senha_login.strip()
            
            print(f"🔐 Validando login - Nº: {numero}")
            
            if not numero or not senha:
                self.display_var.set("❌ Preencha todos os campos!")
                self.display_secundario_var.set("Tente novamente")
                self.root.after(3000, self._recomecar_login)
                return
            
            # Buscar usuário no banco
            self.cursor.execute('''
                SELECT * FROM usuarios 
                WHERE numero_trabalhador = %s AND ativo = TRUE
            ''', (numero,))
            
            usuario = self.cursor.fetchone()
            
            if usuario and self.verificar_senha(senha, usuario['senha_hash']):
                # VERIFICAR SE OPERADOR JÁ ESTÁ LOGADO EM OUTRO PDV
                verificacao_pdv = self._verificar_operador_em_outro_pdv(usuario['id'])
                
                if verificacao_pdv['logado_em_outro_pdv']:
                    self.display_var.set("❌ Operador em outro PDV!")
                    self.display_secundario_var.set(
                        f"Já logado no PDV {verificacao_pdv['numero_caixa']}"
                    )
                    self.root.after(4000, self._recomecar_login)
                    return
                
                # Login válido
                self.operador_atual = usuario
                
                # Atualizar último login
                self.cursor.execute('''
                    UPDATE usuarios SET ultimo_login = %s WHERE id = %s
                ''', (datetime.now(), usuario['id']))
                
                self.registrar_auditoria('LOGIN', f'Login no PDV {self.numero_caixa}')
                
                self.display_var.set("✅ Login realizado!")
                self.display_secundario_var.set(f"Bem-vindo, {usuario['nome']}!")
                
                # Atualizar interface
                self.atualizar_info_operador()
                self.verificar_status_caixa()
                
                # Aguardar 2 segundos e prosseguir
                self.root.after(2000, self._prosseguir_apos_login)
                
            else:
                self.display_var.set("❌ Credenciais inválidas!")
                self.display_secundario_var.set("Verifique nº e senha")
                self.root.after(3000, self._recomecar_login)
                
        except Exception as e:
            print(f"❌ Erro no login: {e}")
            self.display_var.set("❌ Erro no sistema!")
            self.display_secundario_var.set("Tente novamente")
            self.root.after(3000, self._recomecar_login)
    
    def _cancelar_login(self):
        """Cancela o processo de login"""
        self.resultado_login['sucesso'] = False
        self._limpar_modo_especial()
        self._var_login.set(False)
    
    def _prosseguir_apos_login(self):
        """Prossegue após login válido"""
        self._limpar_modo_especial()
        self._var_login.set(True)
    
    def _recomecar_login(self):
        """Recomeça o processo de login"""
        self.etapa_login = 'NUMERO_TRABALHADOR'
        self.numero_trabalhador_login = ""
        self.senha_login = ""
        self.display_text = ""
        self.display_var.set("Digite nº trabalhador...")
        self.op_secundario_var.set("Etapa 1/2: Nº Trabalhador")
        
    def atualizar_interface_sem_login(self):
        """Atualiza interface quando não há operador logado - CORRIGIDO"""
        # Lista de botões que devem estar ATIVOS sem login
        botoes_ativos_sem_login = ['CONSULTAR PREÇO', 'SUPERVISOR', 'CANCELAR']
        
        # Lista de botões que devem estar DESATIVADOS sem login
        botoes_desativados_sem_login = ['TOTAL', 'DESCONTO', 'CLIENTE', 'NOVA VENDA']
        
        # Percorrer todos os widgets para encontrar botões
        for widget in self.scrollable_frame_direito.winfo_children():
            if isinstance(widget, tk.Button):
                texto = widget.cget('text')
                if texto in botoes_desativados_sem_login:
                    widget.config(state=tk.DISABLED, bg='#95a5a6')
                elif texto in botoes_ativos_sem_login:
                    widget.config(state=tk.NORMAL)
        
        # Atualizar display
        self.display_var.set("Sistema pronto - Efetue login para vender")
        self.display_secundario_var.set("Use SUPERVISOR para login")
    
    def atualizar_interface_com_login(self):
        """Atualiza interface quando há operador logado - CORRIGIDO"""
        # Reativar todos os botões
        for widget in self.scrollable_frame_direito.winfo_children():  # CORRIGIDO: direito
            if isinstance(widget, tk.Button):
                widget.config(state=tk.NORMAL)
        
        # Restaurar cores originais dos botões de função
        botoes_cores = {
            'TOTAL': '#f39c12',
            'DESCONTO': '#9b59b6', 
            'CLIENTE': '#3498db',
            'NOVA VENDA': '#27ae60',
            'CANCELAR': '#e67e22',
            'CONSULTAR PREÇO': '#3498db',
            'SUPERVISOR': '#e67e22'
        }
        
        for widget in self.scrollable_frame_direito.winfo_children():
            if isinstance(widget, tk.Button):
                texto = widget.cget('text')
                if texto in botoes_cores:
                    widget.config(bg=botoes_cores[texto])
        
        # Atualizar display
        self.display_var.set(f"Bem-vindo, {self.operador_atual['nome']}!")
        self.display_secundario_var.set("Pronto para vender...")

    def _garantir_botao_login_visivel(self):
        """Garante que o botão de login está sempre visível quando não há operador logado"""
        if not hasattr(self, 'operador_atual') or not self.operador_atual:
            # Se não há operador logado, mostrar opção de login
            self.display_var.set("Sistema pronto - Pressione SUPERVISOR para login")
            self.op_var.set("Aguardando autenticação...")
            
            # Ativar botão supervisor para login
            if hasattr(self, 'btn_supervisor'):
                self.btn_supervisor.config(state=tk.NORMAL, bg='#e67e22')                
# =============================================================================
# FUNÇÕES DE LOGIN NOVO FIM
# =============================================================================
# =============================================================================
# FUNÇÕES DE OPERADOR NOVO INICIO
# =============================================================================
    
    def saida_operador(self):
        """Realiza saída do operador com relatório - ATUALIZADO"""
        if not self.verificar_acesso_supervisor_com_cartao():
            return
        
        if not self.operador_atual:
            messagebox.showwarning("Aviso", "Nenhum operador logado!")
            return
        
        # Confirmar saída
        resposta = messagebox.askyesno(
            "Confirmar Saída",
            f"Deseja realizar a saída do operador?\n\n"
            f"Operador: {self.operador_atual['nome']}\n"
            f"Esta ação irá gerar e imprimir o relatório de fechamento."
        )
        
        if not resposta:
            return
        
        # Gerar relatório de saída
        relatorio = self._gerar_relatorio_saida()
        
        # SALVAR AUTOMATICAMENTE o comprovativo
        nome_arquivo = self._salvar_comprovativo_saida(relatorio)
        
        # IMPRIMIR AUTOMATICAMENTE
        self._imprimir_comprovativo_saida(relatorio, nome_arquivo)
        
        # Mostrar relatório na tela
        self._mostrar_relatorio_saida(relatorio, nome_arquivo)
        
        # Fazer logout
        self._fazer_logout_operador()
    
    def _salvar_comprovativo_saida(self, relatorio):
        """Salva o comprovativo de saída em arquivo - NOVO"""
        try:
            # Criar pasta de comprovativos se não existir
            pasta_comprovativos = "comprovativos_saida"
            if not os.path.exists(pasta_comprovativos):
                os.makedirs(pasta_comprovativos)
            
            # Nome do arquivo com data, hora e operador
            data_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_operador = self.operador_atual['nome'].replace(' ', '_')
            nome_arquivo = f"{pasta_comprovativos}/saida_{nome_operador}_{data_hora}.txt"
            
            # Salvar arquivo
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                f.write(relatorio)
            
            print(f"✅ Comprovativo salvo: {nome_arquivo}")
            return nome_arquivo
            
        except Exception as e:
            print(f"❌ Erro ao salvar comprovativo: {e}")
            return None
    
    def _imprimir_comprovativo_saida(self, relatorio, nome_arquivo):
        """Imprime automaticamente o comprovativo de saída - NOVO"""
        try:
            # Tentar impressão automática
            sucesso = self.impressao.imprimir_recibo(relatorio, "SAIDA_OPERADOR")
            
            if sucesso:
                print("✅ Comprovativo impresso automaticamente")
            else:
                print("⚠️ Comprovativo salvo mas não foi possível imprimir")
                
            # Registrar auditoria
            self.registrar_auditoria('COMPROVATIVO_SAIDA_GERADO',
                                   f'Comprovativo salvo: {nome_arquivo}')
                                   
        except Exception as e:
            print(f"❌ Erro na impressão automática: {e}")
    
    def _mostrar_relatorio_saida(self, relatorio, nome_arquivo):
        """Mostra o relatório de saída - ATUALIZADO"""
        relatorio_window = tk.Toplevel(self.root)
        relatorio_window.title("Relatório de Saída - COMPROVATIVO GERADO")
        relatorio_window.geometry("700x800")
        
        # Adicionar informações do arquivo
        info_arquivo = f"\n💾 Comprovativo salvo em: {nome_arquivo}\n" if nome_arquivo else ""
        relatorio_completo = relatorio + info_arquivo
        
        text_frame = tk.Frame(relatorio_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=('Courier', 10), wrap=tk.WORD)
        text_widget.insert(tk.END, relatorio_completo)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões
        btn_frame = tk.Frame(relatorio_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="🖨️ IMPRIMIR NOVAMENTE", 
                 command=lambda: self.imprimir_relatorio(relatorio),
                 bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="💾 SALVAR CÓPIA", 
                 command=lambda: self._salvar_copia_comprovativo(relatorio),
                 bg='#9b59b6', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="✅ CONFIRMAR SAÍDA", 
                 command=relatorio_window.destroy,
                 bg='#27ae60', fg='white').pack(side=tk.RIGHT, padx=5)
    
    def _salvar_copia_comprovativo(self, relatorio):
        """Salva uma cópia adicional do comprovativo"""
        try:
            from tkinter import filedialog
            
            arquivo = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
                title="Salvar comprovativo como..."
            )
            
            if arquivo:
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write(relatorio)
                messagebox.showinfo("Sucesso", f"Comprovativo salvo em:\n{arquivo}")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar cópia: {e}")
    
    def _gerar_relatorio_saida(self):
        """Gera relatório completo da saída do operador - CORRIGIDO"""
        try:
            data_hoje = datetime.now().strftime('%d/%m/%Y')
            hora_saida = datetime.now().strftime('%H:%M:%S')
            
            # Buscar vendas POR FORMA DE PAGAMENTO do operador
            self.cursor.execute('''
                SELECT 
                    CASE 
                        WHEN forma_pagamento LIKE '%DINHEIRO%' THEN 'DINHEIRO'
                        WHEN forma_pagamento LIKE '%DÉBITO%' THEN 'CARTÃO DÉBITO'
                        WHEN forma_pagamento LIKE '%CRÉDITO%' THEN 'CARTÃO CRÉDITO' 
                        WHEN forma_pagamento LIKE '%PIX%' THEN 'PIX'
                        WHEN forma_pagamento LIKE '%CLIENTE%' THEN 'CARTÃO CLIENTE'
                        ELSE 'OUTROS'
                    END as forma,
                    COUNT(*) as num_vendas,
                    SUM(total) as total_vendas,
                    SUM(valor_pago) as total_pago,
                    SUM(troco) as total_troco
                FROM vendas 
                WHERE DATE(data_hora) = CURDATE() 
                AND operador_id = %s
                AND status = 'FINALIZADA'
                GROUP BY forma
                ORDER BY total_vendas DESC
            ''', (self.operador_atual['id'],))
            
            vendas_por_forma = self.cursor.fetchall()
            
            # Buscar sangrias POR FORMA DE PAGAMENTO
            self.cursor.execute('''
                SELECT 
                    forma_pagamento as forma,
                    SUM(valor) as total_sangria
                FROM movimentos_caixa 
                WHERE caixa_id = %s
                AND tipo = 'SAIDA'
                GROUP BY forma_pagamento
            ''', (self.id_abertura,))
            
            sangrias_por_forma = self.cursor.fetchall()
            
            # Converter sangrias para dicionário para fácil acesso
            sangrias_dict = {}
            for s in sangrias_por_forma:
                # CORREÇÃO: Converter decimal.Decimal para float
                sangrias_dict[s['forma']] = float(s['total_sangria']) if s['total_sangria'] else 0.0
            
            # Calcular totais gerais - CORREÇÃO: Converter todos para float
            total_vendas_geral = 0.0
            for v in vendas_por_forma:
                total_vendas_geral += float(v['total_vendas']) if v['total_vendas'] else 0.0
            
            total_sangria_geral = sum(sangrias_dict.values())
            
            # CORREÇÃO: Converter saldo_inicial para float
            saldo_inicial_float = float(self.saldo_inicial) if self.saldo_inicial else 0.0
            
            # Gerar relatório com tabela formatada
            relatorio = f"""
    {'='*60}
    {'RELATÓRIO DE SAÍDA - OPERADOR'.center(60)}
    {'='*60}
    
    OPERADOR: {self.operador_atual['nome']}
    DATA: {data_hoje}
    HORA SAÍDA: {hora_saida}
    Nº TRABALHADOR: {self.operador_atual['numero_trabalhador']}
    
    {'RESUMO POR FORMA DE PAGAMENTO'.center(60)}
    {'-'*60}
    | {'FORMA PAGAMENTO':<20} | {'VENDAS':>10} | {'SANGRIA':>10} | {'DIFERENÇA':>12} |
    {'-'*60}"""
            
            # Adicionar cada forma de pagamento - CORREÇÃO: Converter para float
            for venda in vendas_por_forma:
                forma = venda['forma']
                total_venda = float(venda['total_vendas']) if venda['total_vendas'] else 0.0
                total_sangria = sangrias_dict.get(forma, 0.0)
                diferenca = total_venda - total_sangria
                
                relatorio += f"\n| {forma:<20} | R$ {total_venda:>8.2f} | R$ {total_sangria:>8.2f} | R$ {diferenca:>10.2f} |"
            
            relatorio += f"\n{'-'*60}"
            relatorio += f"\n| {'TOTAIS':<20} | R$ {total_vendas_geral:>8.2f} | R$ {total_sangria_geral:>8.2f} | R$ {total_vendas_geral - total_sangria_geral:>10.2f} |"
            relatorio += f"\n{'-'*60}"
            
            # Adicionar informações adicionais
            relatorio += f"\n\n{'INFORMAÇÕES ADICIONAIS':<60}"
            relatorio += f"\n{'-'*60}"
            relatorio += f"\n{'Total de Vendas:':<30} {len(vendas_por_forma)} formas de pagamento"
            relatorio += f"\n{'Saldo Inicial:':<30} R$ {saldo_inicial_float:>10.2f}"
            relatorio += f"\n{'Saldo Líquido:':<30} R$ {total_vendas_geral - total_sangria_geral:>10.2f}"
            
            relatorio += f"\n\n{'='*60}"
            relatorio += f"\n{'*** SAÍDA REGISTRADA COM SUCESSO ***'.center(60)}"
            relatorio += f"\n{'='*60}"
            
            return relatorio
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Erro detalhado no relatório: {error_details}")
            return f"Erro ao gerar relatório: {str(e)}"
    
    def _fazer_logout_operador(self):
        """Faz logout do operador atual"""
        # Registrar auditoria
        self.registrar_auditoria('SAIDA_OPERADOR', 
                               f'Saída do operador: {self.operador_atual["nome"]}')
        
        # Limpar dados do operador
        self.operador_atual = None
        self.operador_var.set("Operador: Não logado")
        self.cliente_atual = None
        self.cliente_var.set("Cliente: Não informado")
        
        # Limpar venda atual
        self.limpar_venda()
        
        # Mostrar mensagem
        messagebox.showinfo("Saída Realizada", 
                           "Saída do operador realizada com sucesso!\n"
                           "Relatório gerado e impresso.")
        
        # Voltar para tela de login
        self.root.after(1000, self.fazer_login)

    def sangria_caixa(self):
        """Realiza sangria do caixa usando display e teclado"""
        if not self.verificar_acesso_supervisor_com_cartao():
            return
        
        if not self.caixa_aberto:
            messagebox.showwarning("Aviso", "Caixa não está aberto!")
            return
        
        self.modo_sangria = True
        self.etapa_sangria = 'SELECIONAR_FORMA'
        self.forma_sangria = ""
        self.valor_sangria = ""
        self.motivo_sangria = ""
        
        self.display_text = ""
        self.display_var.set("Selecione forma de pagamento...")
        self.op_var.set("Sangria de Caixa")
        self.op_secundario_var.set("Use botões abaixo")
        self.entrada_especial = 'SANGRIA_CAIXA'
        
        # Mostrar botões de formas de pagamento
        self._mostrar_botoes_sangria()
    
    def _mostrar_botoes_sangria(self):
        """Mostra botões para seleção da forma de pagamento - ATUALIZADO"""
        # Limpar frame de informações
        self.info_frame.pack_forget()
        
        # Criar frame para botões de sangria
        if hasattr(self, 'sangria_frame'):
            self.sangria_frame.destroy()
        
        self.sangria_frame = tk.Frame(self.scrollable_frame_direito, bg='#34495e')
        self.sangria_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(self.sangria_frame, text="FORMA DE PAGAMENTO:", 
                font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1').pack(pady=5)
        
        formas_frame = tk.Frame(self.sangria_frame, bg='#34495e')
        formas_frame.pack(fill=tk.X, pady=5)
        
        formas = [
            ('💵 DINHEIRO', '#27ae60'),
            ('💳 CARTÃO DÉBITO', '#2980b9'), 
            ('💳 CARTÃO CRÉDITO', '#8e44ad'),
            ('📱 PIX', '#3498db'),
            ('👤 CARTÃO CLIENTE', '#16a085')
        ]
        
        for forma, cor in formas:
            btn = tk.Button(formas_frame, text=forma, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=2,
                           command=lambda f=forma: self._selecionar_forma_sangria(f))
            btn.pack(fill=tk.X, pady=2)
        
        # BOTÃO PARA TERMINAR SANGRIA - NOVO
        botoes_acao_frame = tk.Frame(self.sangria_frame, bg='#34495e')
        botoes_acao_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(botoes_acao_frame, text="✅ TERMINAR SANGRIA", 
                 command=self._terminar_sangria,
                 bg='#27ae60', fg='white', font=('Arial', 11, 'bold')).pack(fill=tk.X, pady=2)
        
        tk.Button(botoes_acao_frame, text="🔴 CANCELAR TUDO", 
                 command=self._cancelar_sangria,
                 bg='#e74c3c', fg='white').pack(fill=tk.X, pady=2)
    
    def _atualizar_botoes_sangria(self):
        """Atualiza botões durante a sangria - ATUALIZADO"""
        if hasattr(self, 'sangria_frame'):
            self.sangria_frame.destroy()
        
        self.sangria_frame = tk.Frame(self.scrollable_frame_direito, bg='#34495e')
        self.sangria_frame.pack(fill=tk.X, padx=10, pady=10)
        
        if self.etapa_sangria == 'SELECIONAR_FORMA':
            self._mostrar_botoes_sangria()
        elif self.etapa_sangria == 'DIGITAR_VALOR':
            tk.Label(self.sangria_frame, text=f"VALOR PARA: {self.forma_sangria}", 
                    font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1').pack(pady=5)
            
            # Mostrar saldo atual desta forma
            saldo_atual = self._obter_saldo_por_forma(self.forma_sangria)
            tk.Label(self.sangria_frame, text=f"Saldo disponível: R$ {saldo_atual:.2f}", 
                    font=('Arial', 10), bg='#34495e', fg='#bdc3c7').pack(pady=2)
            
            # Botões de ação
            botoes_frame = tk.Frame(self.sangria_frame, bg='#34495e')
            botoes_frame.pack(fill=tk.X, pady=5)
            
            tk.Button(botoes_frame, text="✅ CONFIRMAR VALOR", 
                     command=self._confirmar_valor_sangria,
                     bg='#27ae60', fg='white', font=('Arial', 10, 'bold')).pack(fill=tk.X, pady=2)
            
            tk.Button(botoes_frame, text="🔄 TROCAR FORMA", 
                     command=lambda: self._mudar_etapa_sangria('SELECIONAR_FORMA'),
                     bg='#3498db', fg='white').pack(fill=tk.X, pady=2)
            
            tk.Button(botoes_frame, text="✅ TERMINAR SANGRIA", 
                     command=self._terminar_sangria,
                     bg='#f39c12', fg='white').pack(fill=tk.X, pady=2)
            
            tk.Button(botoes_frame, text="🔴 CANCELAR TUDO", 
                     command=self._cancelar_sangria,
                     bg='#e74c3c', fg='white').pack(fill=tk.X, pady=2)
    
    def _terminar_sangria(self):
        """Termina o processo de sangria e mostra resumo"""
        try:
            # Buscar sangrias realizadas nesta sessão
            self.cursor.execute('''
                SELECT forma_pagamento, SUM(valor) as total 
                FROM movimentos_caixa 
                WHERE caixa_id = %s 
                AND tipo = 'SAIDA'
                AND descricao LIKE 'SANGRIA%'
                GROUP BY forma_pagamento
            ''', (self.id_abertura,))
            
            sangrias_realizadas = self.cursor.fetchall()
            
            if not sangrias_realizadas:
                messagebox.showinfo("Sangria", "Nenhuma sangria foi realizada!")
                self._cancelar_sangria()
                return
            
            # Gerar resumo das sangrias
            resumo = "📋 RESUMO DAS SANGRIAS REALIZADAS:\n\n"
            total_geral = 0.0
            
            for sangria in sangrias_realizadas:
                forma = sangria['forma_pagamento']
                valor = float(sangria['total']) if sangria['total'] else 0.0
                total_geral += valor
                resumo += f"  {forma}: R$ {valor:.2f}\n"
            
            resumo += f"\n💰 TOTAL GERAL: R$ {total_geral:.2f}"
            
            # Mostrar resumo
            messagebox.showinfo("Sangria Concluída", resumo)
            
            # Registrar auditoria
            self.registrar_auditoria('SANGRIA_CONCLUIDA',
                                   f'Sangria concluída - Total: R$ {total_geral:.2f}')
            
            # Limpar modo sangria
            self._limpar_modo_especial()
            
            self.display_var.set("✅ Sangria concluída!")
            self.display_secundario_var.set(f"Total: R$ {total_geral:.2f}")
            
        except Exception as e:
            print(f"❌ Erro ao terminar sangria: {e}")
            messagebox.showerror("Erro", f"Erro ao terminar sangria: {e}")
            self._cancelar_sangria()
    
    def _selecionar_forma_sangria(self, forma):
        """Seleciona forma de pagamento para sangria"""
        if forma == '🔴 CANCELAR':
            self._cancelar_sangria()
            return
        
        # Extrair nome da forma sem emoji
        if ' ' in forma:
            self.forma_sangria = forma.split(' ', 1)[1]  # Remove o emoji
        else:
            self.forma_sangria = forma
        
        self.etapa_sangria = 'DIGITAR_VALOR'
        self.valor_sangria = ""
        
        self.display_var.set("Digite valor da sangria...")
        self.op_secundario_var.set(f"Forma: {self.forma_sangria}")
        
        # Atualizar botões
        self._atualizar_botoes_sangria()
  
    def _processar_sangria(self, tecla):
        """Processa teclas no modo sangria"""
        if self.etapa_sangria == 'DIGITAR_VALOR':
            if tecla == '⌫':
                if self.valor_sangria:
                    self.valor_sangria = self.valor_sangria[:-1]
                    if self.valor_sangria:
                        self.display_var.set(f"Valor: R$ {self.valor_sangria}")
                    else:
                        self.display_var.set("Digite valor da sangria...")
            
            elif tecla == 'Enter ↵':
                if self.valor_sangria:
                    self._confirmar_valor_sangria()
                else:
                    self.display_var.set("Digite um valor!")
            
            elif tecla == 'CANCELAR':
                self._cancelar_sangria()
            
            elif tecla.isdigit() or tecla == ',':
                if tecla == ',' and ',' in self.valor_sangria:
                    return
                self.valor_sangria += tecla
                self.display_var.set(f"Valor: R$ {self.valor_sangria}")
    
    def _confirmar_valor_sangria(self):
        """Confirma o valor da sangria"""
        try:
            if not self.valor_sangria:
                self.display_var.set("Digite um valor!")
                return
            
            valor = float(self.valor_sangria.replace(',', '.'))
            
            if valor <= 0:
                self.display_var.set("Valor deve ser > 0!")
                return
            
            # Buscar saldo atual da forma de pagamento
            saldo_forma = self._obter_saldo_por_forma(self.forma_sangria)
            
            if valor > saldo_forma:
                self.display_var.set("Valor maior que saldo!")
                self.display_secundario_var.set(f"Saldo {self.forma_sangria}: R$ {saldo_forma:.2f}")
                return
            
            # Registrar sangria
            motivo = f"SANGRIA - {self.forma_sangria}"
            if self.registrar_movimento_caixa('SAIDA', motivo, valor, self.forma_sangria):
                self.registrar_auditoria('SANGRIA_CAIXA',
                                       f'Sangria: {self.forma_sangria} - R$ {valor:.2f}')
                
                self.display_var.set(f"✅ Sangria: R$ {valor:.2f}")
                self.display_secundario_var.set(f"Forma: {self.forma_sangria}")
                
                # Aguardar e voltar para seleção de forma
                self.root.after(2000, self._voltar_selecao_forma)
            else:
                self.display_var.set("❌ Erro ao registrar!")
                
        except ValueError:
            self.display_var.set("Valor inválido!")
    
    def _obter_saldo_por_forma(self, forma):
        """Obtém o saldo atual por forma de pagamento - CORRIGIDO PARA DECIMAL"""
        try:
            # Buscar TOTAL DE VENDAS por forma
            self.cursor.execute('''
                SELECT COALESCE(SUM(total), 0) as total_vendas
                FROM vendas 
                WHERE DATE(data_hora) = CURDATE() 
                AND forma_pagamento LIKE %s
                AND status = 'FINALIZADA'
            ''', (f'%{forma}%',))
            
            resultado = self.cursor.fetchone()
            # CORREÇÃO: Lidar com decimal.Decimal
            total_vendas = float(resultado['total_vendas']) if resultado and resultado['total_vendas'] else 0.0
            
            # Buscar SANGRIA já realizada para esta forma
            self.cursor.execute('''
                SELECT COALESCE(SUM(valor), 0) as total_sangria
                FROM movimentos_caixa 
                WHERE caixa_id = %s 
                AND tipo = 'SAIDA'
                AND forma_pagamento = %s
            ''', (self.id_abertura, forma))
            
            resultado_sangria = self.cursor.fetchone()
            # CORREÇÃO: Lidar com decimal.Decimal
            total_sangria = float(resultado_sangria['total_sangria']) if resultado_sangria and resultado_sangria['total_sangria'] else 0.0
            
            # Saldo = Vendas - Sangrias
            saldo = total_vendas - total_sangria
            
            print(f"💰 Saldo {forma}: Vendas R$ {total_vendas:.2f} - Sangrias R$ {total_sangria:.2f} = R$ {saldo:.2f}")
            
            return max(0, saldo)  # Não permitir saldo negativo
            
        except Exception as e:
            print(f"Erro ao obter saldo por forma: {e}")
            return 0.0
    
    def _voltar_selecao_forma(self):
        """Volta para seleção de forma após sangria"""
        self.etapa_sangria = 'SELECIONAR_FORMA'
        self.forma_sangria = ""
        self.valor_sangria = ""
        
        self.display_var.set("Selecione forma de pagamento...")
        self.op_secundario_var.set("Sangria realizada - Continue ou CANCELAR")
        
        self._mostrar_botoes_sangria()
    
    def _mudar_etapa_sangria(self, etapa):
        """Muda a etapa da sangria"""
        self.etapa_sangria = etapa
        if etapa == 'SELECIONAR_FORMA':
            self._voltar_selecao_forma()
    
    def _cancelar_sangria(self):
        """Cancela o processo de sangria"""
        self._limpar_modo_especial()
        self.display_var.set("Sangria cancelada")
        self.display_secundario_var.set("Pronto para novas operações")
        
    def _converter_decimal_para_float(self, valor_decimal):
        """Converte decimal.Decimal para float de forma segura"""
        try:
            if valor_decimal is None:
                return 0.0
            elif hasattr(valor_decimal, '__float__'):
                return float(valor_decimal)
            else:
                return float(str(valor_decimal))
        except (TypeError, ValueError):
            return 0.0    
    
    def iniciar_relogio(self):
        """Inicia o relógio de forma segura"""
        try:
            # Inicializar variáveis do relógio se não existirem
            if not hasattr(self, 'data_var'):
                self.data_var = tk.StringVar()
            if not hasattr(self, 'hora_var'):
                self.hora_var = tk.StringVar()
            
            self.atualizar_relogio()
        except Exception as e:
            print(f"Erro ao iniciar relógio: {e}")
    # No __init__, substitua:
    # self.atualizar_relogio()
    # por:
    # self.iniciar_relogio()
    
    def _atualizar_relogio(self):
        """Atualiza o relógio na interface"""
        try:
            agora = datetime.now()
            data_str = agora.strftime("%d/%m/%Y")
            hora_str = agora.strftime("%H:%M:%S")
            
            if hasattr(self, 'data_var'):
                self.data_var.set(f"Data: {data_str}")
            if hasattr(self, 'hora_var'):
                self.hora_var.set(f"Hora: {hora_str}")
            
            # Agendar próxima atualização em 1 segundo
            self.root.after(1000, self.atualizar_relogio)
        except Exception as e:
            print(f"Erro no relógio: {e}")
# =============================================================================
# FUNÇÕES DE OPERADOR NOVO FIM
# =============================================================================

# =============================================================================
# cartao SUPERVISOR
# =============================================================================

    def verificar_acesso_supervisor_com_cartao(self):
        """Verifica acesso de supervisor usando cartão + credenciais no display"""
        # Primeira fase: Verificação com cartão supervisor
        resultado_cartao = self._verificar_cartao_supervisor()
        
        if not resultado_cartao:
            return False
        
        # Segunda fase: Verificação com credenciais no display
        return self._verificar_credenciais_supervisor_display()
    
    def _verificar_cartao_supervisor(self):
        """Verifica cartão supervisor usando display e teclado"""
        self.modo_cartao_supervisor = True
        self.display_text = ""
        self.display_var.set("Passe o cartão supervisor...")
        self.op_var.set("Modo Cartão Supervisor")
        self.op_secundario_var.set("Use leitor ou digite código")
        self.entrada_especial = 'CARTAO_SUPERVISOR'
        
        # Criar uma variável para armazenar o resultado
        self.resultado_cartao_supervisor = {'autorizado': False}
        
        # Esperar pela verificação do cartão
        self.root.wait_variable(self._get_var_cartao_supervisor())
        
        return self.resultado_cartao_supervisor['autorizado']
    
    def _get_var_cartao_supervisor(self):
        """Cria variável para monitorar resultado do cartão"""
        if not hasattr(self, '_var_cartao_supervisor'):
            self._var_cartao_supervisor = tk.BooleanVar()
        return self._var_cartao_supervisor
    
    def _processar_cartao_supervisor(self, codigo_cartao):
        """Processa a leitura do cartão supervisor"""
        try:
            # Obter cartões supervisor do config
            cartao_principal = self.config_manager.get('SEGURANCA', 'cartao_supervisor')
            cartao_backup = self.config_manager.get('SEGURANCA', 'cartao_supervisor_backup', cartao_principal)
            
            # Verificar se o cartão é válido
            if codigo_cartao == cartao_principal or codigo_cartao == cartao_backup:
                self.display_var.set("✓ Cartão supervisor válido")
                self.display_secundario_var.set("Aguarde...")
                self.resultado_cartao_supervisor['autorizado'] = True
                
                # Registrar auditoria
                self.registrar_auditoria('CARTAO_SUPERVISOR_VALIDADO', 
                                       'Cartão supervisor validado com sucesso')
                
                # Aguardar 1 segundo e prosseguir para credenciais
                self.root.after(1000, self._prosseguir_para_credenciais)
            else:
                self.display_var.set("❌ Cartão supervisor inválido!")
                self.display_secundario_var.set("Tente novamente")
                self.resultado_cartao_supervisor['autorizado'] = False
                
                # Registrar tentativa falha
                self.registrar_auditoria('CARTAO_SUPERVISOR_INVALIDO', 
                                       f'Tentativa com cartão inválido: {codigo_cartao}')
                
                # Aguardar 2 segundos e recomeçar
                self.root.after(2000, self._recomecar_verificacao_cartao)
                
        except Exception as e:
            self.display_var.set("❌ Erro na verificação!")
            self.resultado_cartao_supervisor['autorizado'] = False
            self.root.after(2000, self._limpar_modo_especial)
    
    def _prosseguir_para_credenciais(self):
        """Prossegue para verificação de credenciais após cartão válido"""
        self._limpar_modo_especial()
        self._var_cartao_supervisor.set(True)
    
    def _recomecar_verificacao_cartao(self):
        """Recomeça a verificação do cartão"""
        self._limpar_modo_especial()
        self._var_cartao_supervisor.set(False)
    
    def _verificar_credenciais_supervisor(self):
        """Verifica credenciais do supervisor após cartão válido"""
        credenciais_window = tk.Toplevel(self.root)
        credenciais_window.title("Autorização de Supervisor")
        credenciais_window.geometry("400x450")
        credenciais_window.transient(self.root)
        credenciais_window.grab_set()
        
        # Centralizar
        credenciais_window.update_idletasks()
        width = 400
        height = 450
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        credenciais_window.geometry(f'{width}x{height}+{x}+{y}')
        
        resultado = {'autorizado': False, 'supervisor': None}
        
        # Interface moderna
        main_frame = tk.Frame(credenciais_window, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="👨‍💼 AUTORIZAÇÃO SUPERVISOR", 
                font=('Arial', 16, 'bold'), bg='#2c3e50', fg='#ecf0f1').pack(pady=20)
        
        # Frame de credenciais
        cred_frame = tk.Frame(main_frame, bg='#2c3e50')
        cred_frame.pack(fill=tk.X, pady=10)
        
        # Nº Trabalhador
        tk.Label(cred_frame, text="Nº Trabalhador:", font=('Arial', 12),
                bg='#2c3e50', fg='#ecf0f1').pack(anchor='w', pady=5)
        
        numero_var = tk.StringVar()
        numero_entry = tk.Entry(cred_frame, textvariable=numero_var, 
                               font=('Arial', 14), width=15, justify='center')
        numero_entry.pack(fill=tk.X, pady=5)
        
        # Senha
        tk.Label(cred_frame, text="Senha:", font=('Arial', 12),
                bg='#2c3e50', fg='#ecf0f1').pack(anchor='w', pady=5)
        
        senha_var = tk.StringVar()
        senha_entry = tk.Entry(cred_frame, textvariable=senha_var, show='•',
                              font=('Arial', 14), width=15, justify='center')
        senha_entry.pack(fill=tk.X, pady=5)
        
        # Status
        status_var = tk.StringVar(value="Digite credenciais...")
        status_label = tk.Label(cred_frame, textvariable=status_var,
                               font=('Arial', 10), bg='#2c3e50', fg='#bdc3c7')
        status_label.pack(pady=10)
        
        def verificar_credenciais():
            numero = numero_var.get().strip()
            senha = senha_var.get().strip()
            
            if not numero or not senha:
                status_var.set("❌ Preencha todos os campos!")
                status_label.config(fg='#e74c3c')
                return
            
            # Buscar supervisor no banco
            self.cursor.execute('''
                SELECT * FROM usuarios 
                WHERE numero_trabalhador = %s 
                AND nivel_acesso IN ('SUPERVISOR', 'ADMIN')
                AND ativo = TRUE
            ''', (numero,))
            
            supervisor = self.cursor.fetchone()
            
            if supervisor and self.verificar_senha(senha, supervisor['senha_hash']):
                resultado['autorizado'] = True
                resultado['supervisor'] = supervisor
                
                # Registrar auditoria
                self.registrar_auditoria('AUTORIZACAO_SUPERVISOR_CONCEDIDA',
                                       f'Autorização concedida para: {self.operador_atual["nome"]} '
                                       f'por: {supervisor["nome"]}')
                
                status_var.set("✅ Autorização concedida!")
                status_label.config(fg='#27ae60')
                
                # Fechar após 1 segundo
                credenciais_window.after(1000, credenciais_window.destroy)
            else:
                status_var.set("❌ Credenciais inválidas!")
                status_label.config(fg='#e74c3c')
                
                # Registrar tentativa falha
                self.registrar_auditoria('TENTATIVA_AUTORIZACAO_INVALIDA',
                                       f'Tentativa inválida - Nº: {numero}')
        
        def fazer_logout_supervisor():
            resultado['autorizado'] = False
            credenciais_window.destroy()
        
        # Botões
        botoes_frame = tk.Frame(main_frame, bg='#2c3e50')
        botoes_frame.pack(fill=tk.X, pady=20)
        
        tk.Button(botoes_frame, text="✅ AUTORIZAR", command=verificar_credenciais,
                 bg='#27ae60', fg='white', font=('Arial', 12, 'bold'),
                 height=2).pack(fill=tk.X, pady=5)
        
        tk.Button(botoes_frame, text="❌ CANCELAR", command=fazer_logout_supervisor,
                 bg='#e74c3c', fg='white', font=('Arial', 10),
                 height=1).pack(fill=tk.X, pady=5)
        
        # Bind Enter para facilitar
        senha_entry.bind('<Return>', lambda e: verificar_credenciais())
        
        # Focar no campo número
        numero_entry.focus()
        
        credenciais_window.wait_window()
        
        if resultado['autorizado']:
            self.supervisor_atual = resultado['supervisor']
            # Iniciar timer de sessão
            self._iniciar_sessao_supervisor()
        
        return resultado['autorizado']
    
    def _verificar_credenciais_supervisor_display(self):
        """Verifica credenciais do supervisor usando display e teclado - CORRIGIDO"""
        # DEBUG: Listar supervisores disponíveis
        self._debug_listar_supervisores()
        
        self.modo_credenciais_supervisor = True
        self.etapa_credenciais = 'NUMERO_TRABALHADOR'
        self.numero_trabalhador_supervisor = ""
        self.senha_supervisor = ""
        
        self.display_text = ""
        self.display_var.set("Digite nº trabalhador...")
        self.op_var.set("Autorização Supervisor")
        self.op_secundario_var.set("Etapa 1/2: Nº Trabalhador")
        self.entrada_especial = 'CREDENCIAIS_SUPERVISOR'
        
        # Criar variável para resultado
        self.resultado_credenciais_supervisor = {'autorizado': False}
        
        # Esperar pela verificação
        self.root.wait_variable(self._get_var_credenciais_supervisor())
        
        return self.resultado_credenciais_supervisor['autorizado']
    
    def _get_var_credenciais_supervisor(self):
        """Cria variável para monitorar resultado das credenciais"""
        if not hasattr(self, '_var_credenciais_supervisor'):
            self._var_credenciais_supervisor = tk.BooleanVar()
        return self._var_credenciais_supervisor
    
    def _processar_credenciais_supervisor(self, tecla):
        """Processa teclas no modo credenciais supervisor"""
        if tecla == '⌫':
            if self.etapa_credenciais == 'NUMERO_TRABALHADOR':
                if self.numero_trabalhador_supervisor:
                    self.numero_trabalhador_supervisor = self.numero_trabalhador_supervisor[:-1]
                    self.display_var.set(f"Nº: {self.numero_trabalhador_supervisor}")
            elif self.etapa_credenciais == 'SENHA':
                if self.senha_supervisor:
                    self.senha_supervisor = self.senha_supervisor[:-1]
                    senha_oculta = '•' * len(self.senha_supervisor)
                    self.display_var.set(f"Senha: {senha_oculta}")
        
        elif tecla == 'Enter ↵':
            if self.etapa_credenciais == 'NUMERO_TRABALHADOR':
                if self.numero_trabalhador_supervisor:
                    # Avançar para senha
                    self.etapa_credenciais = 'SENHA'
                    self.display_text = ""
                    self.senha_supervisor = ""
                    self.display_var.set("Digite senha...")
                    self.op_secundario_var.set("Etapa 2/2: Senha (4+ dígitos)")
                else:
                    self.display_var.set("Digite nº trabalhador!")
            
            elif self.etapa_credenciais == 'SENHA':
                if len(self.senha_supervisor) >= 4:
                    # Verificar credenciais
                    self._validar_credenciais_supervisor()
                else:
                    self.display_var.set("Senha deve ter 4+ dígitos!")
        
        elif tecla == 'CANCELAR':
            self._cancelar_verificacao_credenciais()
        
        elif tecla.isdigit():
            if self.etapa_credenciais == 'NUMERO_TRABALHADOR':
                if len(self.numero_trabalhador_supervisor) < 10:  # Limite razoável
                    self.numero_trabalhador_supervisor += tecla
                    self.display_var.set(f"Nº: {self.numero_trabalhador_supervisor}")
            
            elif self.etapa_credenciais == 'SENHA':
                if len(self.senha_supervisor) < 10:  # Limite para senha
                    self.senha_supervisor += tecla
                    senha_oculta = '•' * len(self.senha_supervisor)
                    self.display_var.set(f"Senha: {senha_oculta}")
    
    def _validar_credenciais_supervisor(self):
        """Valida as credenciais do supervisor - VERSÃO COMPLETAMENTE CORRIGIDA"""
        try:
            numero = self.numero_trabalhador_supervisor.strip()
            senha = self.senha_supervisor.strip()
            
            print(f"🔍 Validando credenciais - Nº: {numero}, Senha: {senha}")
            
            if not numero or not senha:
                self.display_var.set("❌ Preencha todos os campos!")
                self.display_secundario_var.set("Tente novamente")
                self.root.after(3000, self._recomecar_credenciais)
                return
            
            # Buscar supervisor no banco
            self.cursor.execute('''
                SELECT * FROM usuarios 
                WHERE numero_trabalhador = %s 
                AND nivel_acesso IN ('SUPERVISOR', 'ADMIN')
                AND ativo = TRUE
            ''', (numero,))
            
            supervisor = self.cursor.fetchone()
            
            print(f"🔍 Supervisor encontrado: {supervisor is not None}")
            
            if supervisor:
                print(f"🔍 Hash no banco: {supervisor['senha_hash']}")
                print(f"🔍 Senha digitada: {senha}")
                
                # Verificar senha
                senha_correta = self.verificar_senha(senha, supervisor['senha_hash'])
                print(f"🔍 Senha correta: {senha_correta}")
                
                if senha_correta:
                    # Credenciais válidas
                    self.resultado_credenciais_supervisor['autorizado'] = True
                    self.supervisor_atual = supervisor
                    
                    # Registrar auditoria
                    self.registrar_auditoria('AUTORIZACAO_SUPERVISOR_CONCEDIDA',
                                           f'Autorização concedida para: {self.operador_atual["nome"] if self.operador_atual else "N/A"} '
                                           f'por: {supervisor["nome"]}')
                    
                    self.display_var.set("✅ Autorização concedida!")
                    self.display_secundario_var.set(f"Supervisor: {supervisor['nome']}")
                    
                    # CORREÇÃO: Iniciar sessão com tratamento de erro
                    try:
                        self._iniciar_sessao_supervisor()
                    except Exception as sessao_error:
                        print(f"⚠️ Erro na sessão (continuando): {sessao_error}")
                    
                    # Aguardar 2 segundos e prosseguir
                    self.root.after(2000, self._prosseguir_apos_credenciais_validas)
                    return
            
            # Se chegou aqui, credenciais são inválidas
            self.display_var.set("❌ Credenciais inválidas!")
            self.display_secundario_var.set("Verifique nº e senha")
            
            # Registrar tentativa falha
            self.registrar_auditoria('TENTATIVA_AUTORIZACAO_INVALIDA',
                                   f'Tentativa inválida - Nº: {numero}')
            
            # Aguardar 3 segundos e recomeçar
            self.root.after(3000, self._recomecar_credenciais)
            
        except Exception as e:
            print(f"❌ Erro crítico na validação: {e}")
            import traceback
            traceback.print_exc()  # Mostrar stack trace completo
            
            self.display_var.set("❌ Erro no sistema!")
            self.display_secundario_var.set("Contate o administrador")
            self.root.after(3000, self._recomecar_credenciais)
    
    def _cancelar_verificacao_credenciais(self):
        """Cancela a verificação de credenciais"""
        self.resultado_credenciais_supervisor['autorizado'] = False
        self._limpar_modo_especial()
        self._var_credenciais_supervisor.set(False)
    
    def _prosseguir_apos_credenciais_validas(self):
        """Prossegue após credenciais válidas"""
        self._limpar_modo_especial()
        self._var_credenciais_supervisor.set(True)
    
    def _recomecar_credenciais(self):
        """Recomeça a verificação de credenciais"""
        self.etapa_credenciais = 'NUMERO_TRABALHADOR'
        self.numero_trabalhador_supervisor = ""
        self.senha_supervisor = ""
        self.display_text = ""
        self.display_var.set("Digite nº trabalhador...")
        self.op_secundario_var.set("Etapa 1/2: Nº Trabalhador")
    
    def _iniciar_sessao_supervisor(self):
        """Inicia sessão temporária do supervisor - CORRIGIDO"""
        try:
            # CORREÇÃO: Converter para int e usar valor padrão se necessário
            tempo_sessao_str = self.config_manager.get('SEGURANCA', 'tempo_sessao_supervisor', '300')
            tempo_sessao = int(tempo_sessao_str)  # Converter para int
            
            self.sessao_supervisor_expira = datetime.now() + timedelta(seconds=tempo_sessao)
            
            print(f"✅ Sessão supervisor iniciada - Expira em: {self.sessao_supervisor_expira}")  # DEBUG
            
            # Atualizar interface
            self._atualizar_status_sessao_supervisor()
            
            # Agendar verificação de expiração
            self._verificar_expiracao_sessao()
            
        except Exception as e:
            print(f"❌ Erro ao iniciar sessão supervisor: {e}")
            # Usar valor padrão em caso de erro
            self.sessao_supervisor_expira = datetime.now() + timedelta(seconds=300)
            self._atualizar_status_sessao_supervisor()
            self._verificar_expiracao_sessao()
    
    def _verificar_expiracao_sessao(self):
        """Verifica se a sessão do supervisor expirou - CORRIGIDO"""
        if hasattr(self, 'sessao_supervisor_expira'):
            if datetime.now() > self.sessao_supervisor_expira:
                # Sessão expirada
                print("⏰ Sessão supervisor expirada")  # DEBUG
                self.supervisor_atual = None
                if hasattr(self, 'sessao_supervisor_expira'):
                    del self.sessao_supervisor_expira
                
                self._atualizar_status_sessao_supervisor()
                messagebox.showinfo("Sessão Expirada", 
                                  "Sessão do supervisor expirou.\n"
                                  "É necessário reautenticar.")
            else:
                # Agendar próxima verificação em 30 segundos
                self.root.after(30000, self._verificar_expiracao_sessao)
    
    def _atualizar_status_sessao_supervisor(self):
        """Atualiza status da sessão supervisor na interface - CORRIGIDO"""
        try:
            if hasattr(self, 'supervisor_atual') and self.supervisor_atual and hasattr(self, 'sessao_supervisor_expira'):
                tempo_restante = self.sessao_supervisor_expira - datetime.now()
                minutos = max(0, int(tempo_restante.total_seconds() // 60))
                segundos = max(0, int(tempo_restante.total_seconds() % 60))
                
                status_text = f"Supervisor: {self.supervisor_atual['nome']} ({minutos:02d}:{segundos:02d})"
                
                # Atualizar botão supervisor
                if hasattr(self, 'btn_supervisor'):
                    self.btn_supervisor.config(
                        text=f"👨‍💼 SUPERVISOR\n({minutos:02d}:{segundos:02d})",
                        bg='#27ae60',
                        state=tk.NORMAL
                    )
            else:
                # Resetar botão supervisor
                if hasattr(self, 'btn_supervisor'):
                    self.btn_supervisor.config(
                        text="👨‍💼 SUPERVISOR",
                        bg='#e67e22',
                        state=tk.NORMAL
                    )
        except Exception as e:
            print(f"❌ Erro ao atualizar status sessão: {e}")
                
    def _processar_tecla_cartao_supervisor(self, tecla):
        """Processa teclas no modo cartão supervisor"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                self.display_var.set(f"Cartão: {self.display_text}")
        elif tecla == 'Enter ↵':
            if self.display_text:
                codigo_cartao = self.display_text.strip()
                self.display_text = ""
                self._processar_cartao_supervisor(codigo_cartao)
            else:
                self._recomecar_verificacao_cartao()
        elif tecla == 'CANCELAR':
            self._recomecar_verificacao_cartao()
        elif tecla.isdigit():
            if len(self.display_text) < 20:  # Limite razoável para código
                self.display_text += tecla
                self.display_var.set(f"Cartão: {self.display_text}")
        else:
            return  # Ignorar outras teclas            
                
    def _mostrar_contador_senha(self):
        """Mostra contador de caracteres da senha"""
        if hasattr(self, 'senha_supervisor'):
            contador = len(self.senha_supervisor)
            if contector >= 4:
                self.op_secundario_var.set(f"Senha: {contador}/10 dígitos ✓")
            else:
                self.op_secundario_var.set(f"Senha: {contador}/10 dígitos (mín: 4)")
                
    def _debug_listar_supervisores(self):
        """Método de debug para listar supervisores no banco"""
        try:
            self.cursor.execute('''
                SELECT numero_trabalhador, nome, nivel_acesso, ativo 
                FROM usuarios 
                WHERE nivel_acesso IN ('SUPERVISOR', 'ADMIN')
            ''')
            
            supervisores = self.cursor.fetchall()
            print("👨‍💼 SUPERVISORES NO BANCO:")
            for supervisor in supervisores:
                print(f"  Nº: {supervisor['numero_trabalhador']}, Nome: {supervisor['nome']}, "
                      f"Nível: {supervisor['nivel_acesso']}, Ativo: {supervisor['ativo']}")
        except Exception as e:
            print(f"❌ Erro ao listar supervisores: {e}")            
    
    def _verificar_config_seguranca(self):
        """Verifica e corrige configurações de segurança"""
        try:
            # Verificar se a seção SEGURANCA existe
            if not self.config_manager.has_section('SEGURANCA'):
                self.config_manager.add_section('SEGURANCA')
            
            # Verificar e definir valores padrão
            configs_padrao = {
                'cartao_supervisor': '9999888777',
                'cartao_supervisor_backup': '9999888777', 
                'tempo_sessao_supervisor': '300'
            }
            
            for chave, valor_padrao in configs_padrao.items():
                if not self.config_manager.has_option('SEGURANCA', chave):
                    self.config_manager.set('SEGURANCA', chave, valor_padrao)
                    print(f"✅ Config {chave} definida para: {valor_padrao}")
            
            # Salvar configurações
            self.config_manager.salvar_configuracoes()
            
        except Exception as e:
            print(f"❌ Erro ao verificar config segurança: {e}")
    
    # Chame este método no __init__ após inicializar config_manager
    # self._verificar_config_seguranca()
    
# cartao SUPERVISOR fim
# =============================================================================
    def _processar_consulta_preco(self, codigo):
        """Processa consulta de preço - FUNCIONA SEM LOGIN"""
        try:
            # Buscar produto no banco
            self.cursor.execute('''
                SELECT codigo, nome, preco, estoque, descricao 
                FROM produtos 
                WHERE (codigo = %s OR nome LIKE %s) AND ativo = TRUE
                LIMIT 1
            ''', (codigo, f'%{codigo}%'))
            
            produto = self.cursor.fetchone()
            
            if produto:
                info_produto = (f"✓ {produto['nome']}\n"
                              f"Código: {produto['codigo']}\n"
                              f"Preço: R$ {float(produto['preco']):.2f}\n"
                              f"Estoque: {produto['estoque']} uni.")
                
                self.display_var.set(f"Preço: R$ {float(produto['preco']):.2f}")
                self.display_secundario_var.set(f"{produto['nome'][:20]}...")
                self.op_var.set("Consulta Preço - Produto Encontrado")
                
                # Mostrar popup com informações completas
                messagebox.showinfo("Consulta de Preço", 
                                  f"PRODUTO: {produto['nome']}\n"
                                  f"CÓDIGO: {produto['codigo']}\n"
                                  f"PREÇO: R$ {float(produto['preco']):.2f}\n"
                                  f"ESTOQUE: {produto['estoque']} unidades\n"
                                  f"DESCRIÇÃO: {produto['descricao'] or 'N/A'}")
            else:
                self.display_var.set("Produto não encontrado!")
                self.display_secundario_var.set(f"Código: {codigo}")
                self.op_var.set("Consulta Preço - Não Encontrado")
                messagebox.showerror("Erro", f"Produto não encontrado!\nCódigo: {codigo}")
        
        except Exception as e:
            self.display_var.set("Erro na consulta!")
            self.op_var.set("Erro")
            messagebox.showerror("Erro", f"Erro na consulta: {e}")
        
        finally:
            # Limpar modo especial
            self._limpar_modo_especial()
    
    def eliminar_produto_especifico(self, produto_id, quantidade=1):
        """Elimina quantidade específica de um produto da venda"""
        for i, item in enumerate(self.venda_atual):
            if item['produto_id'] == produto_id:
                if quantidade >= item['quantidade']:
                    # Remove completamente o item
                    self.venda_atual.pop(i)
                else:
                    # Reduz a quantidade
                    item['quantidade'] -= quantidade
                    item['subtotal'] = item['quantidade'] * item['preco']
                break
        
        self.atualizar_display()
    
    # ATUALIZE o método _processar_eliminar_item para melhor feedback:
    
    def _processar_eliminar_item(self, numero_str):
        """Processa eliminação de item com melhor feedback"""
        try:
            numero = int(numero_str)
            if 1 <= numero <= len(self.venda_atual):
                item = self.venda_atual[numero-1]
                
                # Se o item tem quantidade > 1, perguntar se quer eliminar tudo ou reduzir
                if item['quantidade'] > 1:
                    resposta = self._perguntar_quantidade_eliminar(item, numero)
                    if resposta == 'cancelar':
                        return
                else:
                    # Eliminar item completo
                    resposta = messagebox.askyesno(
                        "Confirmar Eliminação",
                        f"Eliminar item {numero}?\n\n"
                        f"Produto: {item['nome']}\n"
                        f"Quantidade: {item['quantidade']}\n"
                        f"Subtotal: R$ {item['subtotal']:.2f}"
                    )
                    
                    if resposta:
                        item_eliminado = self.venda_atual.pop(numero-1)
                        self.display_var.set(f"Item {numero} eliminado!")
                        self.display_secundario_var.set(f"-R$ {item_eliminado['subtotal']:.2f}")
                        self.atualizar_display()
                        
                        # Manter por 2 segundos antes de limpar
                        self.root.after(2000, self._limpar_display_apos_operacao)
                    else:
                        self._limpar_modo_especial()
            
            else:
                self.display_var.set("Número inválido!")
                self.display_secundario_var.set(f"Digite 1 a {len(self.venda_atual)}")
                self.root.after(2000, self._limpar_modo_especial)
        
        except ValueError:
            self.display_var.set("Número inválido!")
            self.display_secundario_var.set("Digite apenas números")
            self.root.after(2000, self._limpar_modo_especial)
    
    def _perguntar_quantidade_eliminar(self, item, numero):
        """Pergunta se quer eliminar tudo ou reduzir quantidade"""
        escolha_window = tk.Toplevel(self.root)
        escolha_window.title("Eliminar Item")
        escolha_window.geometry("400x200")
        escolha_window.transient(self.root)
        escolha_window.grab_set()
        
        resultado = {'acao': 'cancelar'}
        
        tk.Label(escolha_window, text=f"Eliminar: {item['nome']}", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        tk.Label(escolha_window, text=f"Quantidade atual: {item['quantidade']}",
                 font=('Arial', 10)).pack(pady=5)
        
        def eliminar_tudo():
            resultado['acao'] = 'tudo'
            escolha_window.destroy()
            
            item_eliminado = self.venda_atual.pop(numero-1)
            self.display_var.set(f"Item {numero} eliminado!")
            self.display_secundario_var.set(f"-R$ {item_eliminado['subtotal']:.2f}")
            self.atualizar_display()
            self.root.after(2000, self._limpar_display_apos_operacao)
        
        def reduzir_quantidade():
            resultado['acao'] = 'reduzir'
            escolha_window.destroy()
            self._reduzir_quantidade_item(item, numero)
        
        def cancelar():
            resultado['acao'] = 'cancelar'
            escolha_window.destroy()
            self._limpar_modo_especial()
        
        botoes_frame = tk.Frame(escolha_window)
        botoes_frame.pack(pady=20)
        
        tk.Button(botoes_frame, text="❌ ELIMINAR TUDO", command=eliminar_tudo,
                 bg='#e74c3c', fg='white', font=('Arial', 10, 'bold')).pack(fill=tk.X, pady=2)
        
        tk.Button(botoes_frame, text="📉 REDUZIR QUANTIDADE", command=reduzir_quantidade,
                 bg='#e67e22', fg='white', font=('Arial', 10)).pack(fill=tk.X, pady=2)
        
        tk.Button(botoes_frame, text="❌ CANCELAR", command=cancelar,
                 bg='#95a5a6', fg='white').pack(fill=tk.X, pady=2)
        
        escolha_window.wait_window()
        return resultado['acao']
    
    def _reduzir_quantidade_item(self, item, numero):
        """Reduz quantidade de um item específico"""
        self.modo_reduzir_item = True
        self.item_reduzir = item
        self.numero_item = numero
        self.display_text = ""
        self.display_var.set(f"Reduzir {item['nome'][:15]}...")
        self.display_secundario_var.set(f"Digite quantidade a remover (1-{item['quantidade']})")
        self.entrada_especial = 'REDUZIR_ITEM'
    
    def _processar_desconto(self, valor_str):
        """Processa aplicação de desconto"""
        try:
            total = self.calcular_total()
            valor_desconto = float(valor_str.replace(',', '.'))
            
            if valor_desconto < 0:
                self.display_var.set("Desconto negativo!")
                self.display_secundario_var.set("Digite valor positivo")
                self.root.after(2000, self._limpar_modo_especial)
                return
            
            if valor_desconto > total:
                self.display_var.set("Desconto maior que total!")
                self.display_secundario_var.set(f"Máx: R$ {total:.2f}")
                self.root.after(2000, self._limpar_modo_especial)
                return
            
            # Aplicar desconto
            self.desconto_aplicado = valor_desconto
            self.atualizar_display()
            
            self.display_var.set(f"Desconto: R$ {valor_desconto:.2f}")
            self.display_secundario_var.set(f"Novo Total: R$ {total - valor_desconto:.2f}")
            self.op_var.set("Desconto Aplicado!")
            
            # Registrar auditoria se for supervisor
            if hasattr(self, 'operador_atual') and self.operador_atual:
                self.registrar_auditoria('DESCONTO_APLICADO', 
                                       f'Desconto: R$ {valor_desconto:.2f}')
            
            # Manter por 2 segundos antes de limpar
            self.root.after(2000, self._limpar_display_apos_operacao)
            
        except ValueError:
            self.display_var.set("Valor inválido!")
            self.display_secundario_var.set("Digite valor numérico")
            self.root.after(2000, self._limpar_modo_especial)
    
    # ADICIONE estes métodos auxiliares:
    
    def _limpar_modo_especial(self):
        """Limpa modo especial e retorna ao normal - CORRIGIDO"""
        # Limpar modos de sangria
        if hasattr(self, 'modo_sangria'):
            del self.modo_sangria
        if hasattr(self, 'etapa_sangria'):
            del self.etapa_sangria
        if hasattr(self, 'forma_sangria'):
            del self.forma_sangria
        if hasattr(self, 'valor_sangria'):
            del self.valor_sangria
        
        # Limpar modos de login
        if hasattr(self, 'modo_login'):
            del self.modo_login
        if hasattr(self, 'etapa_login'):
            del self.etapa_login
        if hasattr(self, 'numero_trabalhador_login'):
            del self.numero_trabalhador_login
        if hasattr(self, 'senha_login'):
            del self.senha_login
        
        # Limpar modos de supervisor
        if hasattr(self, 'modo_credenciais_supervisor'):
            del self.modo_credenciais_supervisor
        if hasattr(self, 'etapa_credenciais'):
            del self.etapa_credenciais
        if hasattr(self, 'numero_trabalhador_supervisor'):
            del self.numero_trabalhador_supervisor
        if hasattr(self, 'senha_supervisor'):
            del self.senha_supervisor
        
        # Limpar frame de sangria se existir
        if hasattr(self, 'sangria_frame'):
            self.sangria_frame.destroy()
            del self.sangria_frame
        
        # Limpar outros modos especiais
        modos_para_limpar = [
            'entrada_especial', 'modo_consulta_preco', 'modo_eliminar_item',
            'modo_desconto', 'modo_cartao_supervisor', 'modo_quantidade',
            'modo_pagamento', 'cartao_consulta', 'modo_consulta_saldo'
        ]
        
        for modo in modos_para_limpar:
            if hasattr(self, modo):
                delattr(self, modo)
        
        self.display_text = ""
        self.display_var.set("Pronto para nova operação...")
        self.display_secundario_var.set("Use teclado ou scanner")
        self.op_var.set("Operação: Aguardando...")
        self.op_secundario_var.set("")
        
        # SEMPRE garantir que o botão de login está disponível
        self._garantir_botao_login_visivel()
    
    def _limpar_display_apos_operacao(self):
        """Limpa display após operação bem-sucedida"""
        self._limpar_modo_especial()
        self.atualizar_display()
    
    
    # MODIFIQUE estas funções na classe SistemaVendasProfissional:

    def consultar_preco(self):
        """Consulta preço de produto - AGORA FUNCIONA SEM LOGIN"""
        self.modo_consulta_preco = True
        self.display_text = ""
        self.display_var.set("Digite o código do produto...")
        self.op_var.set("Modo Consulta Preço")
        self.op_secundario_var.set("Digite código ou use scanner")
        self.entrada_especial = 'CONSULTA_PRECO'
    
    def eliminar_item_venda(self):
        """Elimina item da venda usando display para seleção"""
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum item na venda!")
            return
        
        self.modo_eliminar_item = True
        self.display_text = ""
        self.display_var.set("Digite número do item a eliminar:")
        self.op_var.set("Modo Eliminar Item")
        self.op_secundario_var.set("Itens: " + ", ".join([str(i+1) for i in range(len(self.venda_atual))]))
        
        # Mostrar lista de itens no display secundário
        itens_lista = ""
        for i, item in enumerate(self.venda_atual):
            itens_lista += f"{i+1}. {item['nome'][:15]}... R$ {item['subtotal']:.2f}\n"
        
        self.display_secundario_var.set(itens_lista)
        self.entrada_especial = 'ELIMINAR_ITEM'


    def atualizar_botao_supervisor(self):
        """Atualiza visibilidade do botão supervisor baseado no nível de acesso"""
        if hasattr(self, 'btn_supervisor'):
            if self.operador_atual and self.operador_atual['nivel_acesso'] in ['SUPERVISOR', 'ADMIN']:
                self.btn_supervisor.config(state=tk.NORMAL, bg='#e67e22')
            else:
                self.btn_supervisor.config(state=tk.DISABLED, bg='#95a5a6')
                
    def _processar_tecla_consulta_preco(self, tecla):
        """Processa teclas no modo consulta preço"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                self.display_var.set(f"Consulta: {self.display_text}")
        elif tecla == 'Enter ↵':
            if self.display_text:
                codigo = self.display_text.strip()
                self.display_text = ""
                self._processar_consulta_preco(codigo)
            else:
                self._limpar_modo_especial()
        elif tecla == 'CANCELAR':
            self._limpar_modo_especial()
        elif tecla.isdigit() or tecla.isalpha() or tecla in ['-', '_', '.']:
            # Aceitar números, letras e alguns caracteres especiais para códigos
            self.display_text += tecla
            self.display_var.set(f"Consulta: {self.display_text}")
        else:
            return  # Ignorar outras teclas
    
    def _processar_tecla_eliminar_item(self, tecla):
        """Processa teclas no modo eliminar item"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                self.display_var.set(f"Eliminar item: {self.display_text}")
        elif tecla == 'Enter ↵':
            if self.display_text:
                numero = self.display_text
                self.display_text = ""
                self._processar_eliminar_item(numero)
            else:
                self._limpar_modo_especial()
        elif tecla == 'CANCELAR':
            self._limpar_modo_especial()
        elif tecla.isdigit():
            self.display_text += tecla
            self.display_var.set(f"Eliminar item: {self.display_text}")
        else:
            return  # Ignorar teclas não numéricas
    
    def _processar_tecla_desconto(self, tecla):
        """Processa teclas no modo desconto"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                self.display_var.set(f"Desconto: R$ {self.display_text}")
        elif tecla == 'Enter ↵':
            if self.display_text:
                valor = self.display_text
                self.display_text = ""
                self._processar_desconto(valor)
            else:
                self._limpar_modo_especial()
        elif tecla == 'CANCELAR':
            self._limpar_modo_especial()
        elif tecla.isdigit() or tecla == ',':
            # Verificar se já tem vírgula
            if tecla == ',' and ',' in self.display_text:
                return
            self.display_text += tecla
            self.display_var.set(f"Desconto: R$ {self.display_text}")
        else:
            return  # Ignorar outras teclas            
                
# =============================================================================
# FUNÇÕES DE SEGURANÇA E SUPERVISOR
# =============================================================================

    def verificar_acesso_supervisor(self):
        """Verifica se o usuário atual tem acesso de supervisor"""
        if not self.operador_atual:
            messagebox.showerror("Acesso Negado", "Nenhum usuário logado!")
            return False

        if self.operador_atual['nivel_acesso'] in ['SUPERVISOR', 'ADMIN']:
            return True

        # Solicitar credenciais de supervisor
        return self.solicitar_credenciais_supervisor()

    def solicitar_credenciais_supervisor(self):
        """Solicita credenciais de supervisor para operações sensíveis"""
        credenciais_window = tk.Toplevel(self.root)
        credenciais_window.title("Autorização de Supervisor")
        credenciais_window.geometry("300x300")
        credenciais_window.transient(self.root)
        credenciais_window.grab_set()

        tk.Label(credenciais_window, text="Autorização de Supervisor Requerida", 
                font=('Arial', 12, 'bold')).pack(pady=10)

        tk.Label(credenciais_window, text="Nº Trabalhador:").pack(pady=5)
        numero_var = tk.StringVar()
        tk.Entry(credenciais_window, textvariable=numero_var, width=15).pack(pady=5)

        tk.Label(credenciais_window, text="Senha:").pack(pady=5)
        senha_var = tk.StringVar()
        tk.Entry(credenciais_window, textvariable=senha_var, show='*', width=15).pack(pady=5)

        resultado = {'autorizado': False}

        def verificar_credenciais():
            numero = numero_var.get().strip()
            senha = senha_var.get().strip()

            if not numero or not senha:
                messagebox.showerror("Erro", "Preencha todos os campos!")
                return

            self.cursor.execute('''
                SELECT * FROM usuarios 
                WHERE numero_trabalhador = %s 
                AND nivel_acesso IN ('SUPERVISOR', 'ADMIN')
                AND ativo = TRUE
            ''', (numero,))
            
            supervisor = self.cursor.fetchone()

            if supervisor and self.verificar_senha(senha, supervisor['senha_hash']):
                resultado['autorizado'] = True
                self.supervisor_atual = supervisor
                self.registrar_auditoria('AUTORIZACAO_SUPERVISOR',
                                       f'Autorização concedida para operação por {self.operador_atual["nome"]}')
                credenciais_window.destroy()
            else:
                messagebox.showerror("Erro", "Credenciais inválidas ou sem permissão!")
                resultado['autorizado'] = False

        tk.Button(credenciais_window, text="Autorizar", command=verificar_credenciais,
                 bg='#e74c3c', fg='white').pack(pady=20)

        credenciais_window.wait_window()
        return resultado['autorizado']

# =============================================================================
# FUNÇÕES DE LOGIN E CONFIGURAÇÃO
# =============================================================================

    def carregar_configuracoes(self):
        """Método de compatibilidade - usa o novo sistema .INI"""
        # Este método existe para compatibilidade com código antigo
        # Agora usamos self.config_manager diretamente
        pass

    def salvar_configuracoes(self):
        """Método de compatibilidade - usa o novo sistema .INI"""
        self.config_manager.salvar_configuracoes()

    def fazer_login(self):
        """Realiza login no sistema - AGORA COM DISPLAY/TECLADO"""
        # Usar o novo sistema de login com display
        sucesso = self.fazer_login_display()
        
        if sucesso:
            self.atualizar_interface_com_login()
            if not self.caixa_aberto:
                self.abrir_caixa()
        else:
            self.atualizar_interface_sem_login()

    def abrir_caixa(self):
        """Abre o caixa com autorização se necessário"""
        if self.operador_atual['nivel_acesso'] == 'OPERADOR':
            if not self.solicitar_credenciais_supervisor():
                messagebox.showerror("Erro", "Abertura de caixa requer autorização de supervisor!")
                return

        saldo_inicial = simpledialog.askfloat("Abertura de Caixa", 
                                            "Saldo inicial em caixa:",
                                            minvalue=0.0)
        
        if saldo_inicial is None:
            return

        try:
            self.cursor.execute('''
                INSERT INTO caixa (data_abertura, operador_id, supervisor_abertura_id, saldo_inicial, status)
                VALUES (%s, %s, %s, %s, 'ABERTO')
            ''', (datetime.now(), self.operador_atual['id'], 
                  self.supervisor_atual['id'] if self.supervisor_atual else self.operador_atual['id'],
                  saldo_inicial))
            
            self.id_abertura = self.cursor.lastrowid
            self.saldo_inicial = saldo_inicial
            self.caixa_aberto = True
            
            self.registrar_auditoria('ABERTURA_CAIXA',
                                   f'Caixa aberto com saldo inicial: R$ {saldo_inicial:.2f}',
                                   'caixa', self.id_abertura)
            
            messagebox.showinfo("Sucesso", f"Caixa aberto com R$ {saldo_inicial:.2f}")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir caixa: {e}")

    def verificar_status_caixa(self):
        """Verifica se há caixa aberto"""
        if not self.operador_atual:
            return  # Não verificar se não há operador logado
        
        try:
            self.cursor.execute('''
                SELECT * FROM caixa 
                WHERE status = 'ABERTO' 
                ORDER BY data_abertura DESC 
                LIMIT 1
            ''')
            
            caixa = self.cursor.fetchone()
            
            if caixa:
                self.caixa_aberto = True
                self.id_abertura = caixa['id']
                self.saldo_inicial = caixa['saldo_inicial']
                
                # Verificar se o operador atual é o mesmo que abriu o caixa
                if caixa['operador_id'] != self.operador_atual['id']:
                    messagebox.showwarning("Aviso", 
                                        f"Caixa foi aberto por outro operador. "
                                        f"Entre em contato com o supervisor.")
                    
        except Exception as e:
            print(f"Erro ao verificar status do caixa: {e}")

    # ... (mantenha as funções existentes de venda, interface, etc.)
    #antigo iniciais
    def mostrar_login_centralizado(self):
        """Mostra tela de login centralizada na tela"""
        # Primeiro, centralizar a janela principal
        self.root.update_idletasks()
        width = 1300
        height = 900
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Agora criar a janela de login
        login_window = tk.Toplevel(self.root)
        login_window.title("Login - Sistema de Vendas")
        login_window.geometry("300x250")
        login_window.resizable(False, False)
        login_window.transient(self.root)
        login_window.grab_set()
        
        # Centralizar a janela de login
        login_window.update_idletasks()
        login_width = 300
        login_height = 250
        login_x = (self.root.winfo_screenwidth() // 2) - (login_width // 2)
        login_y = (self.root.winfo_screenheight() // 2) - (login_height // 2)
        login_window.geometry('{}x{}+{}+{}'.format(login_width, login_height, login_x, login_y))
        
        # Forçar o foco
        login_window.focus_force()
        login_window.lift()
        
        # Conteúdo do login
        tk.Label(login_window, text="SISTEMA DE VENDAS", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        tk.Label(login_window, text="Usuário:").pack()
        usuario_var = tk.StringVar()
        usuario_entry = tk.Entry(login_window, textvariable=usuario_var, width=20)
        usuario_entry.pack(pady=5)
        
        tk.Label(login_window, text="Senha:").pack()
        senha_var = tk.StringVar()
        senha_entry = tk.Entry(login_window, textvariable=senha_var, show='*', width=20)
        senha_entry.pack(pady=5)    
     #caixa

    # MÉTODOS DO CAIXA - COMPLETOS E FUNCIONAIS

    def movimento_caixa(self):
        """Janela para registrar movimentos de caixa - ENTRADAS/SAÍDAS MANUAIS"""
        if not self.caixa_aberto:
            messagebox.showwarning("Aviso", "Caixa não está aberto!")
            return
        
        movimento_window = tk.Toplevel(self.root)
        movimento_window.title("Movimento de Caixa - Entradas/Saídas")
        movimento_window.geometry("400x350")
        movimento_window.transient(self.root)
        
        # Centralizar
        movimento_window.update_idletasks()
        width = 400
        height = 350
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        movimento_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        tk.Label(movimento_window, text="REGISTRAR MOVIMENTO DE CAIXA", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        # Tipo de movimento
        tk.Label(movimento_window, text="Tipo de Movimento:").pack(pady=5)
        tipo_var = tk.StringVar(value="ENTRADA")
        tipo_frame = tk.Frame(movimento_window)
        tipo_frame.pack(pady=5)
        
        tk.Radiobutton(tipo_frame, text="🎉 Entrada (Suprimento)", variable=tipo_var, 
                      value="ENTRADA", font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(tipo_frame, text="💸 Saída (Sangria)", variable=tipo_var, 
                      value="SAIDA", font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        
        # Descrição
        tk.Label(movimento_window, text="Descrição/Motivo:").pack(pady=5)
        descricao_var = tk.StringVar()
        descricao_entry = tk.Entry(movimento_window, textvariable=descricao_var, width=40, font=('Arial', 10))
        descricao_entry.pack(pady=5)
        
        # Valor
        tk.Label(movimento_window, text="Valor (R$):").pack(pady=5)
        valor_var = tk.StringVar()
        valor_entry = tk.Entry(movimento_window, textvariable=valor_var, width=40, font=('Arial', 10))
        valor_entry.pack(pady=5)
        
        # Forma de pagamento (para entradas)
        tk.Label(movimento_window, text="Forma (para entradas):").pack(pady=5)
        forma_var = tk.StringVar(value="CAIXA")
        forma_combo = ttk.Combobox(movimento_window, textvariable=forma_var, 
                                  values=["CAIXA", "DINHEIRO", "TRANSFERÊNCIA", "OUTRO"],
                                  state="readonly", width=37)
        forma_combo.pack(pady=5)
        
        def registrar_movimento():
            tipo = tipo_var.get()
            descricao = descricao_var.get().strip()
            forma = forma_var.get()
            
            try:
                valor = float(valor_var.get().replace(',', '.'))
                if valor <= 0:
                    messagebox.showerror("Erro", "Valor deve ser maior que zero!")
                    return
            except ValueError:
                messagebox.showerror("Erro", "Valor inválido!")
                return
            
            if not descricao:
                messagebox.showerror("Erro", "Informe a descrição/motivo!")
                return
            
            # Confirmar operação
            confirmacao = messagebox.askyesno(
                "Confirmar Movimento",
                f"Tipo: {tipo}\n"
                f"Descrição: {descricao}\n"
                f"Valor: R$ {valor:.2f}\n"
                f"Forma: {forma}\n\n"
                f"Confirmar operação?"
            )
            
            if not confirmacao:
                return
            
            if self.registrar_movimento_caixa(tipo, descricao, valor, forma):
                movimento_window.destroy()
                messagebox.showinfo("Sucesso", f"Movimento de {tipo} registrado com sucesso!")
                self.atualizar_status_caixa()
        
        # Frame de botões
        botoes_frame = tk.Frame(movimento_window)
        botoes_frame.pack(pady=20)
        
        tk.Button(botoes_frame, text="📝 Registrar Movimento", command=registrar_movimento,
                 bg='#27ae60', fg='white', width=20, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)
        
        tk.Button(botoes_frame, text="❌ Cancelar", command=movimento_window.destroy,
                 bg='#e74c3c', fg='white', width=15).pack(side=tk.LEFT, padx=10)
        
        # Focar na descrição
        descricao_entry.focus_set()

    def consulta_caixa(self):
        """Consulta de movimentos do caixa atual - DIFERENÇA APURADA"""
        if not self.caixa_aberto:
            messagebox.showwarning("Aviso", "Não há caixa aberto!")
            return
        
        consulta_window = tk.Toplevel(self.root)
        consulta_window.title("Consulta de Caixa - Movimentos e Saldo")
        consulta_window.geometry("900x600")
        consulta_window.transient(self.root)
        
        # Centralizar
        consulta_window.update_idletasks()
        width = 900
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        consulta_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Frame principal
        main_frame = tk.Frame(consulta_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(main_frame, text="CONSULTA DE CAIXA - MOVIMENTOS", 
                font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Frame de totais
        totais_frame = tk.LabelFrame(main_frame, text="TOTAIS DO DIA", font=('Arial', 12, 'bold'))
        totais_frame.pack(fill=tk.X, pady=10)
        
        # Calcular totais
        totais = self.calcular_totais_caixa()
        
        # CORREÇÃO: Converter decimal para float e calcular saldo_atual
        saldo_inicial_float = float(self.saldo_inicial)
        total_entradas_float = float(totais['total_entradas'])
        total_saidas_float = float(totais['total_saidas'])
        
        saldo_atual = saldo_inicial_float + total_entradas_float - total_saidas_float  # LINHA ADICIONADA
        
        # Exibir totais
        totais_grid = tk.Frame(totais_frame)
        totais_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Coluna 1
        tk.Label(totais_grid, text=f"Saldo Inicial: R$ {saldo_inicial_float:.2f}",
                font=('Arial', 10)).grid(row=0, column=0, sticky='w', padx=10, pady=2)
        
        tk.Label(totais_grid, text=f"Total Entradas: R$ {total_entradas_float:.2f}",
                font=('Arial', 10), fg='#27ae60').grid(row=1, column=0, sticky='w', padx=10, pady=2)
        
        # Coluna 2
        tk.Label(totais_grid, text=f"Total Saídas: R$ {total_saidas_float:.2f}",
                font=('Arial', 10), fg='#e74c3c').grid(row=0, column=1, sticky='w', padx=10, pady=2)
        
        tk.Label(totais_grid, text=f"Total Vendas: R$ {totais['total_vendas']:.2f}",
                font=('Arial', 10), fg='#3498db').grid(row=1, column=1, sticky='w', padx=10, pady=2)
        
        # Coluna 3 - DIFERENÇA APURADA
        tk.Label(totais_grid, text=f"Saldo Atual: R$ {saldo_atual:.2f}",  # VARIÁVEL DEFINIDA
                font=('Arial', 12, 'bold'), fg='#2c3e50').grid(row=0, column=2, sticky='w', padx=10, pady=2)
        
        # Ajustar colunas
        totais_grid.columnconfigure(0, weight=1)
        totais_grid.columnconfigure(1, weight=1)
        totais_grid.columnconfigure(2, weight=1)
        
        # Resto do método permanece igual...
        
        # Treeview de movimentos
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('data', 'tipo', 'descricao', 'valor', 'forma')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        tree.heading('data', text='Data/Hora')
        tree.heading('tipo', text='Tipo')
        tree.heading('descricao', text='Descrição')
        tree.heading('valor', text='Valor (R$)')
        tree.heading('forma', text='Forma')
        
        tree.column('data', width=150)
        tree.column('tipo', width=100)
        tree.column('descricao', width=350)
        tree.column('valor', width=120)
        tree.column('forma', width=100)
        
        # Carregar movimentos
        self.carregar_movimentos_caixa(tree)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões
        botoes_frame = tk.Frame(main_frame)
        botoes_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(botoes_frame, text="🔄 Atualizar", 
                 command=lambda: self.carregar_movimentos_caixa(tree),
                 bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="📊 Fecho Completo", 
                 command=self.fechar_caixa,
                 bg='#e74c3c', fg='white').pack(side=tk.RIGHT, padx=5)
        
        tk.Button(botoes_frame, text="➕ Novo Movimento", 
                 command=self.movimento_caixa,
                 bg='#27ae60', fg='white').pack(side=tk.RIGHT, padx=5)

    def fechar_caixa(self):
        """FECHO DE CAIXA - APURAÇÃO + RELATÓRIO COMPLETO"""
        if self.operador_atual['nivel_acesso'] == 'OPERADOR':
            if not self.solicitar_credenciais_supervisor():
                messagebox.showerror("Erro", "Abertura de caixa requer autorização de supervisor!")
                return        
        if not self.caixa_aberto:
            messagebox.showwarning("Aviso", "Não há caixa aberto!")
            return
        
        # Calcular totais
        totais = self.calcular_totais_caixa()
        
        # CORREÇÃO: Converter valores para float
        saldo_inicial_float = float(self.saldo_inicial)
        total_entradas_float = float(totais['total_entradas'])
        total_saidas_float = float(totais['total_saidas'])
        
        saldo_teorico = saldo_inicial_float + total_entradas_float - total_saidas_float
        
        # Janela de fecho de caixa
        fecho_window = tk.Toplevel(self.root)
        fecho_window.title("Fecho de Caixa - Apuração Completa")
        fecho_window.geometry("600x700")
        fecho_window.transient(self.root)
        fecho_window.grab_set()
        
        # Centralizar
        fecho_window.update_idletasks()
        width = 600
        height = 700
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        fecho_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Frame principal com scroll
        main_frame = tk.Frame(fecho_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Conteúdo do fecho
        tk.Label(scrollable_frame, text="FECHO DE CAIXA - RELATÓRIO FINAL", 
                font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Informações do caixa
        info_frame = tk.LabelFrame(scrollable_frame, text="🔍 APURAÇÃO COMPLETA", font=('Arial', 12, 'bold'))
        info_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Saldo inicial
        tk.Label(info_frame, text=f"💰 Saldo Inicial: R$ {saldo_inicial_float:.2f}",
                font=('Arial', 11)).pack(anchor='w', pady=8, padx=10)
        
        # Vendas por forma de pagamento
        tk.Label(info_frame, text="💳 VENDAS POR FORMA DE PAGAMENTO:",
                font=('Arial', 11, 'bold')).pack(anchor='w', pady=(15, 5), padx=10)
        
        for forma, total in totais['vendas_por_forma'].items():
            tk.Label(info_frame, text=f"  📊 {forma}: R$ {total:.2f}",
                    font=('Arial', 10)).pack(anchor='w', pady=2, padx=20)
        
        # Separador
        tk.Frame(info_frame, height=2, bg='#bdc3c7').pack(fill=tk.X, pady=10, padx=10)
        
        # Totais gerais
        tk.Label(info_frame, text=f"📈 TOTAL EM VENDAS: R$ {totais['total_vendas']:.2f}",
                font=('Arial', 11, 'bold')).pack(anchor='w', pady=5, padx=10)
        
        tk.Label(info_frame, text=f"⬆️ TOTAL DE ENTRADAS: R$ {totais['total_entradas']:.2f}",
                font=('Arial', 11), fg='#27ae60').pack(anchor='w', pady=3, padx=10)
        
        tk.Label(info_frame, text=f"⬇️ TOTAL DE SAÍDAS: R$ {totais['total_saidas']:.2f}",
                font=('Arial', 11), fg='#e74c3c').pack(anchor='w', pady=3, padx=10)
        
        # Separador
        tk.Frame(info_frame, height=2, bg='#bdc3c7').pack(fill=tk.X, pady=10, padx=10)
        
        # Saldo teórico
        saldo_teorico = saldo_inicial_float + totais['total_entradas'] - totais['total_saidas']
        tk.Label(info_frame, text=f"🧮 SALDO TEÓRICO: R$ {float(saldo_teorico):.2f}",  # Converter para float
                font=('Arial', 12, 'bold'), fg='#2c3e50').pack(anchor='w', pady=8, padx=10)
        
        # DIFERENÇA APURADA - CAMPO PRINCIPAL
        tk.Label(scrollable_frame, text="💰 SALDO REAL EM CAIXA:",
                font=('Arial', 12, 'bold')).pack(anchor='w', pady=(20, 5))
        
        saldo_real_var = tk.StringVar(value=f"{float(saldo_teorico):.2f}")  # Converter para float
        saldo_entry = tk.Entry(scrollable_frame, textvariable=saldo_real_var, 
                              font=('Arial', 14, 'bold'), width=15, justify='center')
        saldo_entry.pack(pady=10)
        
        # DIFERENÇA CALCULADA
        diferenca_var = tk.StringVar()
        diferenca_label = tk.Label(scrollable_frame, textvariable=diferenca_var, 
                                  font=('Arial', 12, 'bold'))
        diferenca_label.pack(pady=10)
        
        # CORREÇÃO: Função calcular_diferenca sem parâmetros extras
        def calcular_diferenca(*args):
            try:
                saldo_real = float(saldo_real_var.get().replace(',', '.'))
                saldo_teorico_float = float(saldo_teorico)  # Converter decimal para float
                diferenca = saldo_real - saldo_teorico_float
                
                if diferenca < 0:
                    cor = '#e74c3c'
                    icone = "🔴"
                    texto = f"{icone} FALTANDO: R$ {abs(diferenca):.2f}"
                elif diferenca > 0:
                    cor = '#27ae60'
                    icone = "🟢"
                    texto = f"{icone} SOBRANDO: R$ {diferenca:.2f}"
                else:
                    cor = '#3498db'
                    icone = "🔵"
                    texto = f"{icone} VALOR CORRETO - SEM DIFERENÇA"
                
                diferenca_var.set(texto)
                diferenca_label.config(fg=cor)
            except ValueError:
                diferenca_var.set("❌ Saldo inválido")
                diferenca_label.config(fg='#e74c3c')
        
        saldo_real_var.trace('w', calcular_diferenca)
        calcular_diferenca()  # Calcular inicial
        
        # Observações
        tk.Label(scrollable_frame, text="📝 OBSERVAÇÕES:",
                font=('Arial', 11, 'bold')).pack(anchor='w', pady=(20, 5))
        
        observacoes_text = tk.Text(scrollable_frame, height=4, width=50, font=('Arial', 10))
        observacoes_text.pack(pady=5, fill=tk.X)
        
        def confirmar_fecho():
            try:
                saldo_real = float(saldo_real_var.get().replace(',', '.'))
                observacoes = observacoes_text.get("1.0", tk.END).strip()
            except ValueError:
                messagebox.showerror("Erro", "Saldo real inválido!")
                return
            
            # Confirmar fecho
            confirmacao = messagebox.askyesno(
                "Confirmar Fecho",
                f"Saldo Teórico: R$ {float(saldo_teorico):.2f}\n"
                f"Saldo Real: R$ {saldo_real:.2f}\n"
                f"DIFERENÇA: R$ {saldo_real - float(saldo_teorico):+.2f}\n\n"
                f"Confirmar fecho do caixa?"
            )
            
            if not confirmacao:
                return
            
            data_fecho = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Atualizar registro do caixa
            self.cursor.execute('''
                UPDATE caixa 
                SET data_fecho = %s, saldo_final = %s, total_vendas = %s,
                    total_entradas = %s, total_saidas = %s, status = 'FECHADO'
                WHERE id = %s
            ''', (data_fecho, saldo_real, totais['total_vendas'], 
                  totais['total_entradas'], totais['total_saidas'], self.id_abertura))
            
            # Registrar observações se houver
            if observacoes:
                self.registrar_movimento_caixa('OBSERVACAO', observacoes, 0, 'SISTEMA')
            
            self.conn.commit()
            
            # Gerar relatório
            self.gerar_relatorio_fecho(saldo_real, float(saldo_teorico), observacoes)
            
            self.caixa_aberto = False
            self.id_abertura = None
            self.saldo_inicial = 0
            
            fecho_window.destroy()
            self.atualizar_status_caixa()
            
            messagebox.showinfo("Sucesso", "✅ Caixa fechado com sucesso!\n\nRelatório gerado e salvo.")
            self.abrir_caixa()  # Oferecer nova abertura
        
        def cancelar_fecho():
            if messagebox.askyesno("Cancelar", "Deseja cancelar o fecho do caixa?"):
                fecho_window.destroy()
        
        # Botões
        botoes_frame = tk.Frame(scrollable_frame)
        botoes_frame.pack(pady=20)
        
        tk.Button(botoes_frame, text="✅ CONFIRMAR FECHO", command=confirmar_fecho,
                 bg='#27ae60', fg='white', width=20, font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=10)
        
        tk.Button(botoes_frame, text="❌ CANCELAR", command=cancelar_fecho,
                 bg='#e74c3c', fg='white', width=15).pack(side=tk.LEFT, padx=10)
        
        # Focar no campo saldo real
        saldo_entry.focus_set()
        saldo_entry.select_range(0, tk.END)

    def mostrar_abertura_caixa(self):
        """Janela para abertura de caixa"""
        abertura_window = tk.Toplevel(self.root)
        abertura_window.title("Abertura de Caixa")
        abertura_window.geometry("400x300")
        abertura_window.transient(self.root)
        abertura_window.grab_set()
        abertura_window.resizable(False, False)
        
        # Centralizar
        abertura_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + self.root.winfo_width() // 2 - 200,
            self.root.winfo_rooty() + self.root.winfo_height() // 2 - 150
        ))
        
        tk.Label(abertura_window, text="ABERTURA DE CAIXA", 
                font=('Arial', 16, 'bold')).pack(pady=20)
        
        # Operador
        tk.Label(abertura_window, text="Operador:").pack(pady=5)
        operador_var = tk.StringVar(value=self.operador_atual)
        tk.Entry(abertura_window, textvariable=operador_var, width=30).pack(pady=5)
        
        # Saldo inicial
        tk.Label(abertura_window, text="Saldo Inicial em Caixa:").pack(pady=5)
        saldo_var = tk.StringVar(value="0.00")
        tk.Entry(abertura_window, textvariable=saldo_var, width=30).pack(pady=5)
        
        def abrir_caixa():
            operador = operador_var.get().strip()
            try:
                saldo_inicial = float(saldo_var.get().replace(',', '.'))
            except ValueError:
                messagebox.showerror("Erro", "Saldo inicial inválido!")
                return
            
            if not operador:
                messagebox.showerror("Erro", "Informe o operador!")
                return
            
            data_abertura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.cursor.execute('''
                INSERT INTO caixa (data_abertura, operador, saldo_inicial, status)
                VALUES (?, ?, ?, 'ABERTO')
            ''', (data_abertura, operador, saldo_inicial))
            
            self.id_abertura = self.cursor.lastrowid
            self.conn.commit()
            
            self.caixa_aberto = True
            self.saldo_inicial = saldo_inicial
            self.operador_atual = operador
            self.operador_var.set(f"Operador: {operador}")
            
            # Registrar movimento de abertura
            self.registrar_movimento_caixa('ENTRADA', 'SALDO INICIAL', saldo_inicial, 'CAIXA')
            
            abertura_window.destroy()
            self.atualizar_status_caixa()
            messagebox.showinfo("Sucesso", "Caixa aberto com sucesso!")
        
        tk.Button(abertura_window, text="Abrir Caixa", command=abrir_caixa,
                 bg='#27ae60', fg='white', width=20).pack(pady=20)
        
        # Focar no campo operador
        abertura_window.after(100, lambda: operador_var.set(self.operador_atual) or abertura_window.focus_force())
        
    def calcular_totais_caixa(self):
        """Calcula totais do caixa atual - SEMPRE RETORNA FLOATS"""
        totais = {
            'total_vendas': 0.0,
            'total_entradas': 0.0,
            'total_saidas': 0.0,
            'vendas_por_forma': {}
        }
        
        if not self.caixa_aberto or not self.id_abertura:
            return totais
        
        try:
            # Total de vendas - CORREÇÃO: garantir float
            self.cursor.execute('''
                SELECT SUM(total) as total FROM vendas 
                WHERE DATE(data_hora) = CURDATE() AND status = 'FINALIZADA'
            ''')
            resultado = self.cursor.fetchone()
            totais['total_vendas'] = float(resultado['total']) if resultado['total'] is not None else 0.0
            
            # Vendas por forma de pagamento
            self.cursor.execute('''
                SELECT forma_pagamento, SUM(total) as total FROM vendas 
                WHERE DATE(data_hora) = CURDATE() AND status = 'FINALIZADA'
                GROUP BY forma_pagamento
            ''')
            for row in self.cursor.fetchall():
                totais['vendas_por_forma'][row['forma_pagamento']] = float(row['total'])
            
            # Movimentos de caixa - CORREÇÃO: garantir float
            self.cursor.execute('''
                SELECT tipo, SUM(valor) as total FROM movimentos_caixa 
                WHERE caixa_id = %s AND tipo IN ('ENTRADA', 'SAIDA')
                GROUP BY tipo
            ''', (self.id_abertura,))
            
            for row in self.cursor.fetchall():
                valor = float(row['total']) if row['total'] is not None else 0.0
                if row['tipo'] == 'ENTRADA':
                    totais['total_entradas'] = valor
                elif row['tipo'] == 'SAIDA':
                    totais['total_saidas'] = valor
            
            return totais
            
        except Exception as e:
            print(f"Erro ao calcular totais do caixa: {e}")
            return totais
    
    def registrar_movimento_caixa(self, tipo, descricao, valor, forma_pagamento='CAIXA'):
        """Registra movimento no caixa"""
        if not self.caixa_aberto:
            messagebox.showwarning("Aviso", "Caixa não está aberto!")
            return False
        
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            self.cursor.execute('''
                INSERT INTO movimentos_caixa (caixa_id, data_hora, tipo, descricao, valor, forma_pagamento)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (self.id_abertura, data_hora, tipo, descricao, valor, forma_pagamento))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao registrar movimento: {e}")
            return False
    
    def gerar_relatorio_fecho(self, saldo_real, saldo_teorico, observacoes):
        """Gera relatório do fecho de caixa - CORREÇÃO"""
        totais = self.calcular_totais_caixa()
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        
        # CORREÇÃO: Usar config_manager em vez de config
        relatorio = f"""
    {self.config_manager.get('SISTEMA', 'empresa_nome')}
    {self.config_manager.get('SISTEMA', 'empresa_endereco')}
    {self.config_manager.get('SISTEMA', 'empresa_telefone')}
    
    {'='*50}
    RELATÓRIO DE FECHO DE CAIXA
    Data: {data_hoje}
    Operador: {self.operador_atual['nome'] if self.operador_atual else 'N/A'}
    {'='*50}
    
    SALDO INICIAL: R$ {float(self.saldo_inicial):>10.2f}

VENDAS DO DIA:
"""
        
        # Vendas por forma de pagamento
        for forma, total in totais['vendas_por_forma'].items():
            relatorio += f"  {forma:.<30} R$ {total:>10.2f}\n"
        
        relatorio += f"{'-'*50}\n"
        relatorio += f"TOTAL VENDAS: R$ {totais['total_vendas']:>10.2f}\n"
        relatorio += f"TOTAL ENTRADAS: R$ {totais['total_entradas']:>10.2f}\n"
        relatorio += f"TOTAL SAÍDAS: R$ {totais['total_saidas']:>10.2f}\n"
        relatorio += f"{'-'*50}\n"
        relatorio += f"SALDO TEÓRICO: R$ {saldo_teorico:>10.2f}\n"
        relatorio += f"SALDO REAL: R$ {saldo_real:>10.2f}\n"
        
        diferenca = saldo_real - saldo_teorico
        relatorio += f"DIFERENÇA: R$ {diferenca:>10.2f}\n"
        
        if observacoes:
            relatorio += f"\nOBSERVAÇÕES:\n{observacoes}\n"
        
        relatorio += f"\n{'='*50}\n"
        relatorio += "ASSINATURA: _________________________\n"
        
        # Mostrar relatório
        self.mostrar_relatorio_fecho(relatorio)
        
        # Salvar arquivo
        try:
            filename = f"fecho_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(relatorio)
        except Exception as e:
            print(f"Erro ao salvar relatório: {e}")
    
    def mostrar_relatorio_fecho(self, relatorio):
        """Mostra relatório de fecho"""
        relatorio_window = tk.Toplevel(self.root)
        relatorio_window.title("Relatório de Fecho de Caixa")
        relatorio_window.geometry("600x700")
        
        # Centralizar
        relatorio_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + self.root.winfo_width() // 2 - 300,
            self.root.winfo_rooty() + self.root.winfo_height() // 2 - 350
        ))
        
        text_frame = tk.Frame(relatorio_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=('Courier', 10), wrap=tk.WORD)
        text_widget.insert(tk.END, relatorio)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = tk.Frame(relatorio_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="Imprimir", 
                 command=lambda: self.imprimir_relatorio(relatorio),
                 bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Fechar", command=relatorio_window.destroy,
                 bg='#e74c3c', fg='white').pack(side=tk.RIGHT, padx=5)

    def criar_painel_direito(self, parent):
        # Display de operação
        op_frame = tk.Frame(parent, bg='#2c3e50')
        op_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.op_var = tk.StringVar(value="Operação: Aguardando...")
        op_label = tk.Label(op_frame, textvariable=self.op_var, font=('Arial', 12),
                           bg='#2c3e50', fg='#ecf0f1')
        op_label.pack()
        
        # Teclado numérico
        teclado_frame = tk.Frame(parent, bg='#34495e')
        teclado_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.criar_teclado_numerico(teclado_frame)
        
        # Botões de função
        funcoes_frame = tk.Frame(parent, bg='#34495e')
        funcoes_frame.pack(fill=tk.X, padx=10, pady=5)
        
        botoes_funcao = [
            ("TOTAL", self.mostrar_formas_pagamento, '#f39c12'),
            ("DESCONTO", self.aplicar_desconto, '#9b59b6'),
            ("CLIENTE", self.selecionar_cliente, '#3498db'),
            ("CANCELAR VENDA", self.cancelar_venda, '#e74c3c'),
            ("CANCELAR", self.cancelar_entrada, '#e67e22')
        ]
        
        for texto, comando, cor in botoes_funcao:
            btn = tk.Button(funcoes_frame, text=texto, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=1 if texto == "CANCELAR" else 2,
                           command=comando)
            btn.pack(fill=tk.X, pady=2)
        
        # Frame de formas de pagamento (inicialmente escondido)
        self.pagamento_frame = tk.Frame(parent, bg='#34495e')
        
        # Informações de pagamento
        self.info_frame = tk.Frame(parent, bg='#34495e')
 
    # MÉTODOS DE PROCESSAMENTO DE TECLAS E VENDAS
    def pressionar_tecla(self, tecla):
        """Processa tecla pressionada no teclado numérico"""
        # Verificar modos especiais primeiro
        if hasattr(self, 'entrada_especial'):
            if self.entrada_especial == 'CARTAO_SUPERVISOR':
                self._processar_tecla_cartao_supervisor(tecla)
                return
            elif self.entrada_especial == 'CREDENCIAIS_SUPERVISOR':
                self._processar_credenciais_supervisor(tecla)
                return
            elif self.entrada_especial == 'LOGIN_SISTEMA':  # NOVO
                self._processar_login(tecla)
                return
            elif self.entrada_especial == 'SANGRIA_CAIXA':  # NOVO
                self._processar_sangria(tecla)
                return    
        # Verificar modos especiais primeiro
        if hasattr(self, 'entrada_especial'):
            if self.entrada_especial == 'CONSULTA_PRECO':
                self._processar_tecla_consulta_preco(tecla)
                return
            elif self.entrada_especial == 'ELIMINAR_ITEM':
                self._processar_tecla_eliminar_item(tecla)
                return
            elif self.entrada_especial == 'DESCONTO':
                self._processar_tecla_desconto(tecla)
                return
            # ... outros modos especiais existentes ...
            
            if self.entrada_especial == 'CARTAO_CONSULTA':
                self._processar_tecla_cartao_consulta(tecla)
                return
            elif self.entrada_especial == 'SENHA_CONSULTA':
                self._processar_tecla_senha_consulta(tecla)
                return
        
        # Modos normais (original)
        if self.modo_pagamento:
            self.processar_tecla_pagamento(tecla)
        elif self.modo_quantidade:
            self.processar_tecla_quantidade(tecla)
        else:
            self.processar_tecla_normal(tecla)
    
    def _processar_tecla_cartao_consulta(self, tecla):
        """Processa tecla para entrada de cartão na consulta"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                self.display_var.set(f"Cartão: {self.display_text}")
        elif tecla == 'Enter ↵':
            if self.display_text:
                numero_cartao = self.display_text
                self.display_text = ""
                del self.entrada_especial
                self._processar_consulta_saldo(numero_cartao)
            else:
                self._limpar_display_consulta()
        elif tecla.isdigit() and len(self.display_text) < 16:
            self.display_text += tecla
            self.display_var.set(f"Cartão: {self.display_text}")
        elif tecla == 'CANCELAR':
            self._limpar_display_consulta()
    
    def _processar_tecla_senha_consulta(self, tecla):
        """Processa tecla para entrada de senha na consulta"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                display_senha = '*' * len(self.display_text) + '_' * (4 - len(self.display_text))
                self.display_var.set(f"Senha: {display_senha}")
        elif tecla == 'Enter ↵':
            if len(self.display_text) == 4:
                senha = self.display_text
                cartao = self.cartao_consulta
                
                if self._verificar_senha_consulta(senha):
                    self.display_text = ""
                    del self.entrada_especial
                    self._finalizar_consulta_saldo(cartao)
            else:
                self.display_secundario_var.set("Senha deve ter 4 dígitos!")
        elif tecla.isdigit() and len(self.display_text) < 4:
            self.display_text += tecla
            display_senha = '*' * len(self.display_text) + '_' * (4 - len(self.display_text))
            self.display_var.set(f"Senha: {display_senha}")
        elif tecla == 'CANCELAR':
            self._limpar_display_consulta()
    
    def processar_tecla_senha(self, tecla):
        """Processa tecla no modo senha"""
        if tecla == '⌫':
            if self.senha_digitada:
                self.senha_digitada = self.senha_digitada[:-1]
                self.display_var.set(f"Senha: {'*' * len(self.senha_digitada)}{'_' * (4 - len(self.senha_digitada))}")
        elif tecla == 'Enter ↵':
            if len(self.senha_digitada) == 4:
                if hasattr(self, 'finalizar_senha_callback'):
                    self.finalizar_senha_callback()
        elif tecla.isdigit() and len(self.senha_digitada) < 4:
            self.senha_digitada += tecla
            self.display_var.set(f"Senha: {'*' * len(self.senha_digitada)}{'_' * (4 - len(self.senha_digitada))}")
    
    def processar_tecla_entrada_cartao(self, tecla):
        """Processa tecla no modo entrada de cartão"""
        if tecla == '⌫':
            if self.entrada_cartao:
                self.entrada_cartao = self.entrada_cartao[:-1]
                self.display_var.set(f"Cartão: {self.entrada_cartao}")
        elif tecla == 'Enter ↵':
            if self.entrada_cartao:
                if hasattr(self, 'finalizar_entrada_callback'):
                    self.finalizar_entrada_callback()
        elif tecla.isdigit():
            self.entrada_cartao += tecla
            self.display_var.set(f"Cartão: {self.entrada_cartao}")
    
    def processar_tecla_normal(self, tecla):
        """Processa tecla no modo normal"""
        if tecla == '✕ Qtd':
            self.modo_quantidade = True
            self.display_text = ""
            self.display_var.set("Digite quantidade + produto")
            self.op_var.set("Modo Quantidade: Digite QtdXCódigo")
        elif tecla == '⌫':
            self.cancelar_entrada()
        elif tecla == 'Enter ↵':
            self.processar_entrada()
        elif tecla.isdigit() or tecla == ',':
            self.display_text += tecla
            self.display_var.set(self.display_text)
        else:
            return
    
    def processar_tecla_quantidade(self, tecla):
        """Processa tecla no modo quantidade"""
        if tecla == '⌫':
            if self.display_text:
                self.display_text = self.display_text[:-1]
                self.display_var.set(self.display_text)
        elif tecla == 'Enter ↵':
            self.processar_entrada_quantidade()
        elif tecla.isdigit() or tecla == ',':
            self.display_text += tecla
            self.display_var.set(self.display_text)
        else:
            return
    
    def processar_entrada_quantidade(self):
        """Processa entrada no modo quantidade"""
        if not self.display_text:
            return
            
        # Formato: QuantidadeXCódigo
        if 'X' in self.display_text or 'x' in self.display_text:
            try:
                # Substituir x minúsculo por X maiúsculo
                entrada = self.display_text.upper().replace('X', 'X')
                partes = entrada.split('X')
                
                if len(partes) != 2:
                    raise ValueError("Formato inválido")
                
                quantidade_str, codigo = partes
                quantidade = int(quantidade_str)
                
                if quantidade > 0 and codigo:
                    if self.adicionar_produto(codigo, "", quantidade):
                        self.display_text = ""
                        self.display_var.set(f"{quantidade}X{codigo} ✓")
                        self.modo_quantidade = False
                        self.op_var.set("Produto adicionado com sucesso!")
                    else:
                        self.display_text = ""
                        self.display_var.set("Erro ao adicionar produto")
                else:
                    raise ValueError("Quantidade ou código inválido")
                    
            except Exception as e:
                messagebox.showerror("Erro", f"Formato inválido! Use: QuantidadeXCódigo\nExemplo: 2X001\n\nErro: {str(e)}")
                self.display_text = ""
                self.display_var.set("Erro - tente novamente")
        else:
            messagebox.showerror("Erro", "Formato inválido! Use: QuantidadeXCódigo\nExemplo: 2X001")
    
    def processar_tecla_pagamento(self, tecla):
        """Processa tecla no modo pagamento"""
        if tecla == '⌫':
            if self.valor_pago_str:
                self.valor_pago_str = self.valor_pago_str[:-1]
                self.atualizar_display_pagamento()
        elif tecla == 'Enter ↵':
            self.processar_pagamento()
        elif tecla.isdigit() or tecla == ',':
            # Verificar se já tem vírgula
            if tecla == ',' and ',' in self.valor_pago_str:
                return
            self.valor_pago_str += tecla
            self.atualizar_display_pagamento()
        else:
            return

    def mostrar_pagamentos_multiplos(self):
        self.pagamento_frame.pack_forget()
        self.mostrar_info_pagamento_multiplos()
    
    def mostrar_info_pagamento_multiplos(self):
        # Mostrar informações de pagamento múltiplo
        self.info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Limpar frame anterior
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        
        total = self.calcular_total()
        total_pago = sum(p['valor'] for p in self.pagamentos)
        restante = total - total_pago
        
        tk.Label(self.info_frame, text=f"Total: R$ {total:.2f}", 
                font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1').pack()
        tk.Label(self.info_frame, text=f"Total Pago: R$ {total_pago:.2f}",
                font=('Arial', 10), bg='#34495e', fg='#2ecc71').pack()
        tk.Label(self.info_frame, text=f"Restante: R$ {restante:.2f}",
                font=('Arial', 10), bg='#34495e', fg='#e74c3c').pack()
        
        # Lista de pagamentos
        for i, pagamento in enumerate(self.pagamentos):
            tk.Label(self.info_frame, 
                    text=f"{pagamento['forma']}: R$ {pagamento['valor']:.2f}",
                    font=('Arial', 9), bg='#34495e', fg='#bdc3c7').pack()
        
        if restante > 0:
            # Botões para adicionar pagamentos
            formas_frame = tk.Frame(self.info_frame, bg='#34495e')
            formas_frame.pack(pady=5)
            
            formas = [
                ('DINHEIRO', '#27ae60'),
                ('CARTÃO DÉBITO', '#2980b9'),
                ('CARTÃO CRÉDITO', '#8e44ad'),
                ('PIX', '#3498db')
            ]
            
            for forma, cor in formas:
                btn = tk.Button(formas_frame, text=f"+ {forma}", font=('Arial', 8, 'bold'),
                               bg=cor, fg='white', height=1,
                               command=lambda f=forma: self.adicionar_pagamento_multiplo(f))
                btn.pack(side=tk.LEFT, padx=2)
            
            tk.Button(self.info_frame, text="FINALIZAR", font=('Arial', 10, 'bold'),
                     bg='#27ae60', fg='white', command=self.finalizar_venda).pack(pady=5)
        else:
            tk.Button(self.info_frame, text="FINALIZAR VENDA", font=('Arial', 12, 'bold'),
                     bg='#27ae60', fg='white', command=self.finalizar_venda).pack(pady=10)
    
    def adicionar_pagamento_multiplo(self, forma):
        if forma == 'DINHEIRO':
            valor = simpledialog.askfloat("Pagamento em Dinheiro", 
                                        f"Digite o valor em dinheiro:")
        else:
            total = self.calcular_total()
            total_pago = sum(p['valor'] for p in self.pagamentos)
            restante = total - total_pago
            valor = restante  # Para outras formas, usa o valor restante
        
        if valor and valor > 0:
            self.pagamentos.append({'forma': forma, 'valor': valor})
            self.mostrar_info_pagamento_multiplos()
    
    def mostrar_info_pagamento(self):
        # Mostrar informações de pagamento
        self.info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Limpar frame anterior
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        
        self.valor_pago_var = tk.StringVar(value="R$ 0,00")
        self.troco_var = tk.StringVar(value="R$ 0,00")
        
        tk.Label(self.info_frame, text="Valor Pago:", font=('Arial', 10),
                bg='#34495e', fg='#ecf0f1').grid(row=0, column=0, sticky=tk.W)
        tk.Label(self.info_frame, textvariable=self.valor_pago_var, font=('Arial', 12, 'bold'),
                bg='#34495e', fg='#2ecc71').grid(row=0, column=1, sticky=tk.E)
        
        tk.Label(self.info_frame, text="Troco:", font=('Arial', 10),
                bg='#34495e', fg='#ecf0f1').grid(row=1, column=0, sticky=tk.W)
        tk.Label(self.info_frame, textvariable=self.troco_var, font=('Arial', 12, 'bold'),
                bg='#34495e', fg='#e74c3c').grid(row=1, column=1, sticky=tk.E)
        
        self.info_frame.columnconfigure(1, weight=1)
        
    def calcular_total(self):
        subtotal = sum(item['subtotal'] for item in self.venda_atual)
        return subtotal - self.desconto_aplicado
    
    def atualizar_display_pagamento(self):
        # Formatar valor pago
        if self.valor_pago_str:
            try:
                # Substituir vírgula por ponto para cálculo
                valor_float = float(self.valor_pago_str.replace(',', '.'))
                self.valor_pago_var.set(f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                
                # Calcular troco apenas para dinheiro
                if self.forma_pagamento == 'DINHEIRO':
                    total = self.calcular_total()
                    troco = valor_float - total
                    if troco < 0:
                        troco = 0
                    self.troco_var.set(f"R$ {troco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                else:
                    self.troco_var.set("R$ 0,00")
            except ValueError:
                self.valor_pago_var.set("R$ 0,00")
                self.troco_var.set("R$ 0,00")
        else:
            self.valor_pago_var.set("R$ 0,00")
            self.troco_var.set("R$ 0,00")
   
    def processar_entrada(self):
        if not self.display_text:
            return
            
        if self.modo_quantidade:
            # Formato: QuantidadeXCódigo
            if 'X' in self.display_text and len(self.display_text) > 1:
                try:
                    # Extrair quantidade e código
                    partes = self.display_text.split('X')
                    if len(partes) != 2:
                        raise ValueError
                    
                    quantidade_str, codigo = partes
                    quantidade = int(quantidade_str)
                    
                    if quantidade > 0 and codigo:
                        if self.adicionar_produto(codigo, "", quantidade):
                            self.display_text = ""
                            self.display_var.set(f"{quantidade}X{codigo} ✓")
                            self.modo_quantidade = False
                            self.op_var.set("Produto adicionado com sucesso!")
                        else:
                            self.display_text = ""
                            self.display_var.set("Erro ao adicionar produto")
                    else:
                        raise ValueError
                        
                except:
                    messagebox.showerror("Erro", "Formato inválido! Use: QuantidadeXCódigo\nExemplo: 2X001")
            else:
                messagebox.showerror("Erro", "Formato inválido! Use: QuantidadeXCódigo\nExemplo: 2X001")
        else:
            # Apenas código do produto
            if self.adicionar_produto(self.display_text, ""):
                self.display_text = ""
                self.display_var.set(f"Produto adicionado ✓")
                self.op_var.set("Produto adicionado com sucesso!")

    def mostrar_formas_pagamento(self):
        """Mostra formas de pagamento - VERIFICA LOGIN"""
        if not self._verificar_login_para_venda():
            return
        
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        # Mostrar frame de formas de pagamento
        self.pagamento_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Limpar frame anterior
        for widget in self.pagamento_frame.winfo_children():
            widget.destroy()
        
        pagamento_label = tk.Label(self.pagamento_frame, text="FORMA DE PAGAMENTO",
                                  font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1')
        pagamento_label.pack()
        
        formas_frame = tk.Frame(self.pagamento_frame, bg='#34495e')
        formas_frame.pack(fill=tk.X, pady=5)
        
        formas = [
            ('DINHEIRO', '#27ae60'),
            ('CARTÃO DÉBITO', '#2980b9'),
            ('CARTÃO CRÉDITO', '#8e44ad'),
            ('CARTÃO CLIENTE', '#16a085'),  # NOVA OPÇÃO
            ('PIX', '#3498db'),
            ('MÚLTIPLOS PAGAMENTOS', '#f39c12'),
            ('DIGITAR VALOR', '#9b59b6')
        ]
        
        for forma, cor in formas:
            btn = tk.Button(formas_frame, text=forma, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=2,
                           command=lambda f=forma: self.selecionar_forma_pagamento(f))
            btn.pack(fill=tk.X, pady=2)
    
    def selecionar_forma_pagamento(self, forma):
        self.forma_pagamento = forma
        self.pagamento_frame.pack_forget()
        
        if forma == 'MÚLTIPLOS PAGAMENTOS':
            self.modo_multiplos_pagamentos = True
            self.pagamentos = []
            self.mostrar_pagamentos_multiplos()
        elif forma == 'DIGITAR VALOR':
            self.modo_digitar_valor = True
            self.mostrar_selecao_forma_com_valor()
        elif forma == 'DINHEIRO':
            self.modo_pagamento = True
            self.valor_pago_str = ""
            self.op_var.set("Digite o valor pago em dinheiro")
            self.mostrar_info_pagamento()
        elif forma == 'CARTÃO CLIENTE':  # NOVA FORMA DE PAGAMENTO
            self.processar_pagamento_cartao_cliente()
        else:
            # Para outras formas, perguntar se quer digitar valor ou usar total
            self.perguntar_valor_pagamento(forma)
 
    def mostrar_formas_pagamento(self):
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        # Mostrar frame de formas de pagamento
        self.pagamento_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Limpar frame anterior
        for widget in self.pagamento_frame.winfo_children():
            widget.destroy()
        
        pagamento_label = tk.Label(self.pagamento_frame, text="FORMA DE PAGAMENTO",
                                  font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1')
        pagamento_label.pack()
        
        formas_frame = tk.Frame(self.pagamento_frame, bg='#34495e')
        formas_frame.pack(fill=tk.X, pady=5)
        
        formas = [
            ('DINHEIRO', '#27ae60'),
            ('CARTÃO DÉBITO', '#2980b9'),
            ('CARTÃO CRÉDITO', '#8e44ad'),
            ('CARTÃO CLIENTE', '#16a085'),  # NOVA OPÇÃO
            ('PIX', '#3498db'),
            ('MÚLTIPLOS PAGAMENTOS', '#f39c12'),
            ('DIGITAR VALOR', '#9b59b6')
        ]
        
        for forma, cor in formas:
            btn = tk.Button(formas_frame, text=forma, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=2,
                           command=lambda f=forma: self.selecionar_forma_pagamento(f))
            btn.pack(fill=tk.X, pady=2)
    
    def perguntar_valor_pagamento(self, forma):
        """Pergunta se quer digitar valor ou usar total"""
        total = self.calcular_total()
        
        resposta = messagebox.askyesno("Valor do Pagamento", 
                                     f"Total: R$ {total:.2f}\n\nDeseja digitar o valor do pagamento?\n\nSim - Digitar valor específico\nNão - Usar valor total")
        
        if resposta:
            # Modo digitar valor
            self.forma_pagamento = forma
            self.modo_pagamento = True
            self.valor_pago_str = ""
            self.op_var.set(f"Digite o valor para {forma}")
            self.mostrar_info_pagamento()
        else:
            # Usar valor total
            self.pagamentos = [{'forma': forma, 'valor': total}]
            self.finalizar_venda()
    
    def mostrar_selecao_forma_com_valor(self):
        """Mostra seleção de forma de pagamento para digitar valor"""
        self.pagamento_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Limpar frame anterior
        for widget in self.pagamento_frame.winfo_children():
            widget.destroy()
        
        pagamento_label = tk.Label(self.pagamento_frame, text="SELECIONE A FORMA DE PAGAMENTO",
                                  font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1')
        pagamento_label.pack()
        
        formas_frame = tk.Frame(self.pagamento_frame, bg='#34495e')
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
                           command=lambda f=forma: self.iniciar_digitacao_valor(f))
            btn.pack(fill=tk.X, pady=2)
    
    def iniciar_digitacao_valor(self, forma):
        """Inicia a digitação do valor para forma específica"""
        self.forma_pagamento = forma
        self.modo_pagamento = True
        self.valor_pago_str = ""
        self.op_var.set(f"Digite o valor para {forma}")
        self.pagamento_frame.pack_forget()
        self.mostrar_info_pagamento()
    
    def processar_pagamento(self):
        """Processa o pagamento digitado"""
        if not self.valor_pago_str:
            messagebox.showerror("Erro", "Digite o valor pago!")
            return
        
        try:
            valor_pago = float(self.valor_pago_str.replace(',', '.'))
        except ValueError:
            messagebox.showerror("Erro", "Valor pago inválido!")
            return
        
        total = self.calcular_total()
        
        if self.forma_pagamento == 'DINHEIRO':
            if valor_pago < total:
                messagebox.showerror("Erro", f"Valor pago insuficiente! Total: R$ {total:.2f}")
                return
            self.pagamentos = [{'forma': 'DINHEIRO', 'valor': valor_pago}]
        else:
            # Para outras formas, validar valor
            if valor_pago < total:
                messagebox.showerror("Erro", f"Valor pago insuficiente! Total: R$ {total:.2f}")
                return
            elif valor_pago > total:
                resposta = messagebox.askyesno("Atenção", 
                                            f"Para {self.forma_pagamento} não é possível dar troco.\n"
                                            f"Valor pago: R$ {valor_pago:.2f}\n"
                                            f"Total: R$ {total:.2f}\n\n"
                                            f"Deseja continuar mesmo assim?")
                if not resposta:
                    return
            
            self.pagamentos = [{'forma': self.forma_pagamento, 'valor': valor_pago}]
        
        # FECHAR A CONTA
        self.finalizar_venda()
    
    # NOVAS FUNCIONALIDADES

    def gerenciar_estoque(self):
        """Interface para gerenciamento de estoque"""
        estoque_window = tk.Toplevel(self.root)
        estoque_window.title("Gerenciamento de Estoque")
        estoque_window.geometry("800x600")
        estoque_window.transient(self.root)
        
        # Frame de controles
        controles_frame = tk.Frame(estoque_window)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(controles_frame, text="Atualizar Estoque", 
                 command=self.atualizar_estoque_lote).pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="Exportar Relatório", 
                 command=self.exportar_relatorio_estoque).pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="Importar CSV", 
                 command=self.importar_estoque_csv).pack(side=tk.LEFT, padx=5)
        
        # Treeview de estoque
        tree_frame = tk.Frame(estoque_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('codigo', 'nome', 'categoria', 'estoque', 'minimo', 'status')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree.heading('codigo', text='Código')
        tree.heading('nome', text='Produto')
        tree.heading('categoria', text='Categoria')
        tree.heading('estoque', text='Estoque')
        tree.heading('minimo', text='Mínimo')
        tree.heading('status', text='Status')
        
        tree.column('codigo', width=80)
        tree.column('nome', width=200)
        tree.column('categoria', width=100)
        tree.column('estoque', width=80)
        tree.column('minimo', width=80)
        tree.column('status', width=100)
        
        # Carregar dados
        self.carregar_dados_estoque(tree)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botão duplo-clique para editar
        tree.bind('<Double-1>', lambda e: self.editar_produto_estoque(tree))
    
    def carregar_dados_estoque(self, tree):
        """Carrega dados do estoque na treeview - CORREÇÃO MYSQL"""
        for item in tree.get_children():
            tree.delete(item)
            
        try:
            # CORREÇÃO: Remover qualquer ? e usar sintaxe MySQL correta
            self.cursor.execute('''
                SELECT p.codigo, p.nome, c.nome as categoria, p.estoque, p.estoque_minimo 
                FROM produtos p 
                LEFT JOIN categorias c ON p.categoria_id = c.id 
                WHERE p.ativo = 1 
                ORDER BY p.nome
            ''')
            
            for produto in self.cursor.fetchall():
                codigo, nome, categoria, estoque, minimo = produto.values()
                status = "CRÍTICO" if estoque == 0 else "BAIXO" if estoque <= minimo else "OK"
                tree.insert('', tk.END, values=(codigo, nome, categoria, estoque, minimo, status))
        except Exception as e:
            print(f"Erro ao carregar estoque: {e}")
    
    def editar_produto(self):
        """Edita produto selecionado"""
        selecao = self.tree_produtos.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um produto!")
            return
        
        if not self.verificar_acesso_supervisor():
            return
        
        item = self.tree_produtos.item(selecao[0])
        produto_id = item['values'][0]
        
        # Buscar dados completos do produto
        self.cursor.execute('''
            SELECT p.*, c.nome as categoria_nome 
            FROM produtos p 
            LEFT JOIN categorias c ON p.categoria_id = c.id 
            WHERE p.id = %s
        ''', (produto_id,))
        
        produto = self.cursor.fetchone()
        if not produto:
            return
            
        # Janela de edição
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Editar {produto['nome']}")
        edit_window.geometry("400x400")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        tk.Label(edit_window, text="Nome:").pack(pady=5)
        nome_var = tk.StringVar(value=produto['nome'])
        tk.Entry(edit_window, textvariable=nome_var, width=30).pack(pady=5)
        
        tk.Label(edit_window, text="Preço:").pack(pady=5)
        preco_var = tk.StringVar(value=str(produto['preco']))
        tk.Entry(edit_window, textvariable=preco_var, width=15).pack(pady=5)
        
        tk.Label(edit_window, text="Estoque:").pack(pady=5)
        estoque_var = tk.StringVar(value=str(produto['estoque']))
        tk.Entry(edit_window, textvariable=estoque_var, width=10).pack(pady=5)
        
        tk.Label(edit_window, text="Estoque Mínimo:").pack(pady=5)
        minimo_var = tk.StringVar(value=str(produto['estoque_minimo']))
        tk.Entry(edit_window, textvariable=minimo_var, width=10).pack(pady=5)
        
        def salvar_alteracoes():
            try:
                novo_preco = float(preco_var.get().replace(',', '.'))
                novo_estoque = int(estoque_var.get())
                novo_minimo = int(minimo_var.get())
                
                self.cursor.execute('''
                    UPDATE produtos 
                    SET nome = %s, preco = %s, estoque = %s, estoque_minimo = %s
                    WHERE id = %s
                ''', (nome_var.get(), novo_preco, novo_estoque, novo_minimo, produto_id))
                
                self.conn.commit()
                self.carregar_produtos()
                edit_window.destroy()
                messagebox.showinfo("Sucesso", "Produto atualizado!")
                
            except ValueError:
                messagebox.showerror("Erro", "Valores inválidos!")
        
        tk.Button(edit_window, text="Salvar", command=salvar_alteracoes,
                 bg='#27ae60', fg='white').pack(pady=20)
    
    def editar_produto_estoque(self, tree):
        """Edita produto selecionado no estoque - CORREÇÃO MYSQL"""
        selecao = tree.selection()
        if not selecao:
            return
            
        item = tree.item(selecao[0])
        codigo = item['values'][0]
        
        # Buscar dados completos do produto - CORREÇÃO: usar %s em vez de ?
        self.cursor.execute('''
            SELECT p.id, p.nome, p.estoque, p.estoque_minimo, p.preco, c.nome as categoria
            FROM produtos p 
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.codigo = %s
        ''', (codigo,))
        
        produto = self.cursor.fetchone()
        if not produto:
            messagebox.showerror("Erro", "Produto não encontrado!")
            return
            
        nome, estoque, minimo, preco, categoria = produto['nome'], produto['estoque'], produto['estoque_minimo'], produto['preco'], produto['categoria']
        
        # Janela de edição
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Editar {nome}")
        edit_window.geometry("300x300")
        edit_window.transient(self.root)
        
        tk.Label(edit_window, text="Estoque Atual:").pack(pady=5)
        estoque_var = tk.StringVar(value=str(estoque))
        tk.Entry(edit_window, textvariable=estoque_var).pack(pady=5)
        
        tk.Label(edit_window, text="Estoque Mínimo:").pack(pady=5)
        minimo_var = tk.StringVar(value=str(minimo))
        tk.Entry(edit_window, textvariable=minimo_var).pack(pady=5)
        
        tk.Label(edit_window, text="Preço:").pack(pady=5)
        preco_var = tk.StringVar(value=str(float(preco)))  # Converter decimal para float
        tk.Entry(edit_window, textvariable=preco_var).pack(pady=5)
        
        def salvar_alteracoes():
            try:
                novo_estoque = int(estoque_var.get())
                novo_minimo = int(minimo_var.get())
                novo_preco = float(preco_var.get().replace(',', '.'))
                
                # CORREÇÃO: usar %s em vez de ?
                self.cursor.execute('''
                    UPDATE produtos SET estoque = %s, estoque_minimo = %s, preco = %s
                    WHERE codigo = %s
                ''', (novo_estoque, novo_minimo, novo_preco, codigo))
                
                self.conn.commit()
                self.carregar_dados_estoque(tree)
                edit_window.destroy()
                messagebox.showinfo("Sucesso", "Produto atualizado!")
                
            except ValueError:
                messagebox.showerror("Erro", "Valores inválidos!")
        
        tk.Button(edit_window, text="Salvar", command=salvar_alteracoes,
                 bg='#27ae60', fg='white').pack(pady=10)
    
    def atualizar_estoque_lote(self):
        """Atualização de estoque em lote - CORREÇÃO MYSQL"""
        lote_window = tk.Toplevel(self.root)
        lote_window.title("Atualização em Lote")
        lote_window.geometry("400x200")
        lote_window.transient(self.root)
        
        tk.Label(lote_window, text="Código do Produto:").pack(pady=5)
        codigo_var = tk.StringVar()
        tk.Entry(lote_window, textvariable=codigo_var).pack(pady=5)
        
        tk.Label(lote_window, text="Quantidade a Adicionar/Remover:").pack(pady=5)
        quantidade_var = tk.StringVar()
        tk.Entry(lote_window, textvariable=quantidade_var).pack(pady=5)
        
        def processar_lote():
            try:
                codigo = codigo_var.get()
                quantidade = int(quantidade_var.get())
                
                # CORREÇÃO: usar %s em vez de ?
                self.cursor.execute('''
                    UPDATE produtos SET estoque = estoque + %s 
                    WHERE codigo = %s
                ''', (quantidade, codigo))
                
                if self.cursor.rowcount > 0:
                    self.conn.commit()
                    messagebox.showinfo("Sucesso", f"Estoque atualizado! {quantidade} unidades")
                    lote_window.destroy()
                else:
                    messagebox.showerror("Erro", "Produto não encontrado!")
                    
            except ValueError:
                messagebox.showerror("Erro", "Quantidade inválida!")
        
        tk.Button(lote_window, text="Atualizar", command=processar_lote,
                 bg='#3498db', fg='white').pack(pady=10)
    
    def exportar_relatorio_estoque(self):
        """Exporta relatório de estoque para CSV - CORREÇÃO MYSQL"""
        try:
            filename = f"estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Código;Produto;Categoria;Estoque;Mínimo;Status;Preço\n")
                
                # CORREÇÃO: Remover ? se houver
                self.cursor.execute('''
                    SELECT p.codigo, p.nome, c.nome as categoria, p.estoque, p.estoque_minimo, p.preco
                    FROM produtos p 
                    LEFT JOIN categorias c ON p.categoria_id = c.id 
                    WHERE p.ativo = 1 
                    ORDER BY c.nome, p.nome
                ''')
                
                for produto in self.cursor.fetchall():
                    codigo, nome, categoria, estoque, minimo, preco = produto.values()
                    status = "CRÍTICO" if estoque == 0 else "BAIXO" if estoque <= minimo else "OK"
                    f.write(f"{codigo};{nome};{categoria};{estoque};{minimo};{status};{float(preco):.2f}\n")
            
            messagebox.showinfo("Exportado", f"Relatório salvo como: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar: {e}")
    
    def importar_estoque_csv(self):
        """Importa estoque de arquivo CSV"""
        messagebox.showinfo("Importar", "Funcionalidade de importação em desenvolvimento")
    
    def relatorio_vendas_periodo(self):
        """Relatório de vendas por período - CORREÇÃO MYSQL"""
        periodo_window = tk.Toplevel(self.root)
        periodo_window.title("Relatório por Período")
        periodo_window.geometry("400x300")
        periodo_window.transient(self.root)
        
        tk.Label(periodo_window, text="Data Inicial (DD/MM/AAAA):").pack(pady=5)
        data_inicio_var = tk.StringVar()
        tk.Entry(periodo_window, textvariable=data_inicio_var).pack(pady=5)
        
        tk.Label(periodo_window, text="Data Final (DD/MM/AAAA):").pack(pady=5)
        data_fim_var = tk.StringVar()
        tk.Entry(periodo_window, textvariable=data_fim_var).pack(pady=5)
        
        def gerar_relatorio():
            try:
                data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')
                
                # CORREÇÃO: usar %s em vez de ?
                self.cursor.execute('''
                    SELECT COUNT(*) as total_vendas, 
                           COALESCE(SUM(total), 0) as total_valor, 
                           COALESCE(SUM(troco), 0) as total_troco
                    FROM vendas 
                    WHERE DATE(data_hora) BETWEEN %s AND %s
                    AND status = 'FINALIZADA'
                ''', (data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d')))
                
                resultado = self.cursor.fetchone()
                total_vendas = resultado['total_vendas'] or 0
                total_valor = float(resultado['total_valor']) or 0
                total_troco = float(resultado['total_troco']) or 0
                
                # Detalhes por forma de pagamento - CORREÇÃO: usar %s
                self.cursor.execute('''
                    SELECT forma_pagamento, COUNT(*) as count, COALESCE(SUM(total), 0) as valor
                    FROM vendas 
                    WHERE DATE(data_hora) BETWEEN %s AND %s
                    AND status = 'FINALIZADA'
                    GROUP BY forma_pagamento
                ''', (data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d')))
                
                formas = self.cursor.fetchall()
                
                relatorio = f"Relatório: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}\n"
                relatorio += f"Total de Vendas: {total_vendas}\n"
                relatorio += f"Valor Total: R$ {total_valor:.2f}\n"
                relatorio += f"Total em Troco: R$ {total_troco:.2f}\n\n"
                relatorio += "Formas de Pagamento:\n"
                
                for forma in formas:
                    relatorio += f"- {forma['forma_pagamento']}: {forma['count']} vendas (R$ {float(forma['valor']):.2f})\n"
                
                # Mostrar relatório
                self.mostrar_relatorio_detalhado(relatorio, periodo_window)
                
            except ValueError:
                messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")
        
        tk.Button(periodo_window, text="Gerar Relatório", command=gerar_relatorio,
                 bg='#3498db', fg='white').pack(pady=10)
    
    def mostrar_relatorio_detalhado(self, relatorio, parent):
        """Mostra relatório em nova janela"""
        relatorio_window = tk.Toplevel(parent)
        relatorio_window.title("Relatório Detalhado")
        relatorio_window.geometry("500x400")
        
        text_frame = tk.Frame(relatorio_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=('Arial', 10), wrap=tk.WORD)
        text_widget.insert(tk.END, relatorio)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Button(relatorio_window, text="Fechar", command=relatorio_window.destroy,
                 bg='#e74c3c', fg='white').pack(pady=10)
    
    def backup_dados(self):
        """Realiza backup dos dados - VERSÃO MYSQL"""
        try:
            # Para MySQL, vamos exportar dados importantes
            data_backup = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"backup_mysql_{data_backup}.sql"
            
            # Criar pasta de backup se não existir
            os.makedirs('backup', exist_ok=True)
            
            # Exportar estrutura e dados principais
            with open(f"backup/{backup_file}", 'w', encoding='utf-8') as f:
                f.write(f"-- Backup MySQL - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                #f.write(f-- Sistema: {self.config_manager.get('SISTEMA', 'empresa_nome')}\n\n")
                
                # Tabelas para backup
                tabelas = ['usuarios', 'produtos', 'clientes', 'vendas', 'itens_venda', 'caixa', 'movimentos_caixa']
                
                for tabela in tabelas:
                    f.write(f"\n-- Dados da tabela {tabela}\n")
                    
                    # Exportar dados
                    self.cursor.execute(f"SELECT * FROM {tabela}")
                    dados = self.cursor.fetchall()
                    
                    for linha in dados:
                        colunas = []
                        valores = []
                        
                        for coluna, valor in linha.items():
                            colunas.append(coluna)
                            if valor is None:
                                valores.append("NULL")
                            elif isinstance(valor, (int, float)):
                                valores.append(str(valor))
                            else:
                                valores.append(f"'{str(valor).replace("'", "''")}'")
                        
                        insert_sql = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join(valores)});\n"
                        f.write(insert_sql)
            
            messagebox.showinfo("Backup", f"Backup realizado: backup/{backup_file}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no backup: {e}")
    
    def mostrar_configuracoes(self):
        """Mostra configurações do sistema - redireciona para o novo sistema"""
        self.mostrar_configuracoes_avancadas()
            
    def ler_scanner(self, event):
        """Captura entrada do scanner de código de barras"""
        # Ignorar teclas de controle
        if event.keysym in ['Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock']:
            return
            
        if event.char and event.char.isprintable():
            # Modo cartão supervisor - capturar tudo
            if hasattr(self, 'entrada_especial') and self.entrada_especial == 'CARTAO_SUPERVISOR':
                self.codigo_scanner += event.char
                self.display_secundario_var.set(f"Scanner: {self.codigo_scanner}")
                return
                
            # Modo credenciais supervisor - NÃO usar scanner (apenas teclado)
            if hasattr(self, 'entrada_especial') and self.entrada_especial == 'CREDENCIAIS_SUPERVISOR':
                # Para credenciais, usar apenas teclado numérico, não scanner
                return
                
            # Outros modos especiais...
            if hasattr(self, 'entrada_especial'):
                self.codigo_scanner += event.char
                self.display_secundario_var.set(f"Scanner: {self.codigo_scanner}")
                return
                
            # Scanner normal de produtos
            self.codigo_scanner += event.char
            
        # Processar quando pressionar Enter
        if event.keysym == 'Return':
            # Modo cartão supervisor
            if hasattr(self, 'entrada_especial') and self.entrada_especial == 'CARTAO_SUPERVISOR':
                if self.codigo_scanner:
                    codigo_cartao = self.codigo_scanner.strip()
                    self._processar_cartao_supervisor(codigo_cartao)
                self.codigo_scanner = ""
                return
             # Modo credenciais supervisor - NÃO processar scanner
            if hasattr(self, 'entrada_especial') and self.entrada_especial == 'CREDENCIAIS_SUPERVISOR':
                self.codigo_scanner = ""  # Limpar mas não processar
                return

            if hasattr(self, 'entrada_especial'):
                if self.entrada_especial == 'CONSULTA_PRECO' and self.codigo_scanner:
                    codigo = self.codigo_scanner.strip()
                    self._limpar_modo_especial()
                    self._processar_consulta_preco(codigo)
                elif self.entrada_especial == 'ELIMINAR_ITEM' and self.codigo_scanner:
                    numero = self.codigo_scanner.strip()
                    self._limpar_modo_especial()
                    self._processar_eliminar_item(numero)
                # Nota: Desconto geralmente não usa scanner
                self.codigo_scanner = ""
                return
            
            # Outros modos especiais...
            if hasattr(self, 'entrada_especial'):
                # ... código existente para outros modos
                pass
                
            # Scanner normal
            if len(self.codigo_scanner) >= 3 and not hasattr(self, 'entrada_especial'):
                self.processar_codigo_scanner(self.codigo_scanner)
            self.codigo_scanner = ""
            
    def processar_codigo_scanner(self, codigo):
        """Processa o código do scanner - CORREÇÃO MYSQL"""
        # Remover possíveis caracteres extras do scanner
        codigo = codigo.strip()
        
        # Verificar se é um código de produto válido
        # CORREÇÃO: Usar %s em vez de ? para MySQL
        self.cursor.execute("SELECT codigo, nome, preco, estoque FROM produtos WHERE codigo = %s", (codigo,))
        produto = self.cursor.fetchone()
        
        if produto:
            codigo_prod, nome, preco, estoque = produto.values()
            if self.adicionar_produto(codigo_prod, nome):
                self.display_text = ""
                self.display_var.set(f"Scanner: {nome} ✓")
                self.display_secundario_var.set(f"Preço: R$ {float(preco):.2f} | Estoque: {estoque}")
                self.op_var.set("Produto adicionado via scanner!")
                self.op_secundario_var.set("Continue adicionando produtos")
        else:
            # Tentar buscar por parte do nome - CORREÇÃO: usar %s
            self.cursor.execute("SELECT codigo, nome, preco, estoque FROM produtos WHERE nome LIKE %s LIMIT 1", 
                              (f'%{codigo}%',))
            produto = self.cursor.fetchone()
            if produto:
                codigo_prod, nome, preco, estoque = produto.values()
                if self.adicionar_produto(codigo_prod, nome):
                    self.display_text = ""
                    self.display_var.set(f"Scanner: {nome} ✓")
                    self.display_secundario_var.set(f"Encontrado por nome")
                    self.op_var.set("Produto encontrado por nome!")
                    self.op_secundario_var.set("Continue adicionando produtos")
            else:
                self.display_var.set(f"Código não encontrado: {codigo}")
                self.display_secundario_var.set("Tente novamente")
                self.op_var.set("Erro no scanner")
                self.op_secundario_var.set("Produto não cadastrado")
                messagebox.showerror("Scanner", f"Código não encontrado: {codigo}")
    
    def carregar_configuracoes(self):
        configuracoes_padrao = {
            'empresa_nome': 'Minha Empresa',
            'empresa_endereco': 'Rua Exemplo, 123',
            'empresa_telefone': '(11) 9999-9999',
            'taxa_juros_cartao': 0.02,
            'cor_primaria': '#2c3e50',
            'cor_secundaria': '#34495e',
            'imprimir_recibo': True,
            'usar_scanner': True,
            'alertar_estoque_baixo': True
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = configuracoes_padrao
        else:
            self.config = configuracoes_padrao
            self.salvar_configuracoes()
    
    def salvar_configuracoes(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
            
    def carregar_movimentos_caixa(self, tree):
        """Carrega movimentos do caixa na treeview"""
        for item in tree.get_children():
            tree.delete(item)
            
        try:
            self.cursor.execute('''
                SELECT data_hora, tipo, descricao, valor, forma_pagamento
                FROM movimentos_caixa 
                WHERE caixa_id = %s
                ORDER BY data_hora DESC
            ''', (self.id_abertura,))
            
            for movimento in self.cursor.fetchall():
                data, tipo, descricao, valor, forma = movimento.values()
                
                # CORREÇÃO: Lidar com diferentes formatos de data
                try:
                    if isinstance(data, str):
                        data_formatada = datetime.strptime(data, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
                    else:
                        # Se já for datetime object
                        data_formatada = data.strftime('%d/%m/%Y %H:%M')
                except:
                    data_formatada = str(data)  # Fallback
                    
                tree.insert('', tk.END, values=(
                    data_formatada, 
                    tipo, 
                    descricao, 
                    f"R$ {float(valor):.2f}", 
                    forma
                ))
        except Exception as e:
            print(f"Erro ao carregar movimentos: {e}")

    def finalizar_venda(self):
        """Finaliza venda e registra no caixa"""
        if not self.venda_atual or not self.pagamentos:
            messagebox.showwarning("Aviso", "Nenhum produto ou pagamento na venda!")
            return
        
        if not self.caixa_aberto:
            messagebox.showerror("Erro", "Caixa não está aberto! Abra o caixa primeiro.")
            return
        
        try:
            total = self.calcular_total()
            total_pagos = sum(p['valor'] for p in self.pagamentos)
            
            # Verificar se o total pago é suficiente
            if total_pagos < total - 0.01:
                messagebox.showerror("Erro", f"Pagamento insuficiente! Total: R$ {total:.2f} | Pago: R$ {total_pagos:.2f}")
                return
            
            # Calcular troco apenas para pagamentos em dinheiro
            troco = 0
            for pagamento in self.pagamentos:
                if pagamento['forma'] == 'DINHEIRO':
                    troco += pagamento['valor'] - (total * (pagamento['valor'] / total_pagos))
            
            # Registrar venda
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formas_str = ", ".join([f"{p['forma']}: R$ {p['valor']:.2f}" for p in self.pagamentos])
            
            # Usar IDs em vez de objetos completos
            operador_id = self.operador_atual['id'] if self.operador_atual else None
            cliente_id = self.cliente_atual  # Se for ID, não dict
            
            self.cursor.execute(
                """INSERT INTO vendas (data_hora, total, forma_pagamento, valor_pago, troco, operador_id, cliente_id, desconto) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (data_hora, total, formas_str, total_pagos, troco, operador_id, cliente_id, self.desconto_aplicado)
            )
            venda_id = self.cursor.lastrowid
            
            # Registrar movimentos no caixa para cada forma de pagamento
            for pagamento in self.pagamentos:
                self.registrar_movimento_caixa(
                    'ENTRADA', 
                    f"VENDA #{venda_id:06d}", 
                    pagamento['valor'], 
                    pagamento['forma']
                )
            
            # Registrar itens e atualizar estoque
            for item in self.venda_atual:
                self.cursor.execute(
                    """INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (venda_id, item['produto_id'], item['quantidade'], item['preco'], item['subtotal'])
                )
                
                # Atualizar estoque
                self.cursor.execute(
                    """UPDATE produtos SET estoque = estoque - %s WHERE id = %s""",
                    (item['quantidade'], item['produto_id'])
                )
            
            self.conn.commit()
            
            # Gerar e mostrar recibo
            self.gerar_recibo(venda_id, data_hora, total, troco)
            
            # Limpar venda
            self.limpar_venda()
            
            # Atualizar status do caixa
            self.atualizar_status_caixa()
            
            messagebox.showinfo("Sucesso", f"Venda finalizada com sucesso! #{venda_id:06d}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao finalizar venda: {e}")
            print(f"Erro detalhado ao finalizar venda: {e}")
            # Fazer rollback em caso de erro
            try:
                self.conn.rollback()
            except:
                pass
    
    def imprimir_relatorio(self, relatorio):
        """Simula impressão do relatório"""
        try:
            filename = f"impressao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(relatorio)
            messagebox.showinfo("Impressão", f"Relatório salvo para impressão: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")

    def gerar_recibo(self, venda_id, data_hora, total, troco):
        """Gera recibo com configurações do .ini e informações do cartão"""
        try:
            # Informações da empresa do .ini
            empresa_nome = self.config_manager.get('SISTEMA', 'empresa_nome')
            empresa_endereco = self.config_manager.get('SISTEMA', 'empresa_endereco')
            empresa_telefone = self.config_manager.get('SISTEMA', 'empresa_telefone')
            
             # Informações do PDV
            info_pdv = self.obter_info_pdv()
            
            data_formatada = datetime.now().strftime('%d/%m/%Y %H:%M')
            
            # Verificar se foi pagamento com cartão cliente
            info_cartao = ""
            if any(p['forma'] == 'CARTÃO CLIENTE' for p in self.pagamentos):
                # Buscar informações do cartão usado
                cartao_pagamento = next(p for p in self.pagamentos if p['forma'] == 'CARTÃO CLIENTE')
                numero_cartao = cartao_pagamento.get('numero_cartao', '')
                
                if numero_cartao:
                    # Buscar informações completas do cartão
                    self.cursor.execute('''
                        SELECT cc.numero_cartao, c.nome as cliente_nome, 
                               mc.saldo_anterior, mc.saldo_posterior
                        FROM movimentos_cartao mc
                        JOIN cartoes_cliente cc ON mc.cartao_id = cc.id
                        JOIN clientes c ON cc.cliente_id = c.id
                        WHERE mc.tipo = 'PAGAMENTO' 
                        AND cc.numero_cartao = %s
                        ORDER BY mc.data_hora DESC 
                        LIMIT 1
                    ''', (numero_cartao,))
                    
                    movimento_cartao = self.cursor.fetchone()
                    
                    if movimento_cartao:
                        info_cartao = f"""
    PAGAMENTO COM CARTÃO CLIENTE:
    Cliente: {movimento_cartao['cliente_nome']}
    Nº Cartão: {movimento_cartao['numero_cartao']}
    Saldo Inicial: R$ {float(movimento_cartao['saldo_anterior']):.2f}
    Valor Pago: R$ {total:.2f}
    Saldo Final: R$ {float(movimento_cartao['saldo_posterior']):.2f}
    {'='*42}
    """
            
            # Mostrar CNPJ se configurado
            cnpj_texto = ""
            if self.config_manager.get('RECIBO', 'mostrar_cnpj', bool):
                cnpj = self.config_manager.get('SISTEMA', 'empresa_cnpj')
                if cnpj:
                    cnpj_texto = f"CNPJ: {cnpj}\n"
            
             # Adicionar seção de promoções se houver
            info_promocoes = ""
            if hasattr(self, 'promocoes_aplicadas_venda') and self.promocoes_aplicadas_venda:
                info_promocoes = "\nPROMOÇÕES APLICADAS:\n"
                for promocao in self.promocoes_aplicadas_venda:
                    info_promocoes += f"  {promocao['promocao_nome']}: -R$ {promocao['valor_desconto']:.2f}\n"
                info_promocoes += f"{'-'*42}\n"
            
            recibo = f"""
    {empresa_nome}
    {empresa_endereco}
    {empresa_telefone}
    {cnpj_texto}
    {'='*42}
    {'RECIBO'.center(42)}
    {'='*42}
    
    Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    Nº Venda: #{venda_id:06d}
    PDV: {info_pdv['numero_caixa']} - {info_pdv['localizacao']}
    Operador: {self.operador_atual['nome'] if self.operador_atual else 'N/A'}
    {self.cliente_var.get()}
    
    {info_cartao}
    {info_promocoes}
    {'ITENS:'.ljust(42)}
    """
            
            for item in self.venda_atual:
                linha = f"{item['nome'][:25]:25} {item['quantidade']:2} x {item['preco']:6.2f} = {item['subtotal']:7.2f}"
                recibo += linha + "\n"
            
            recibo += f"{'-'*42}\n"
            subtotal = sum(item['subtotal'] for item in self.venda_atual)
            recibo += f"SUBTOTAL: R$ {subtotal:>8.2f}\n"
            
            if self.desconto_aplicado > 0:
                recibo += f"DESCONTO: R$ {self.desconto_aplicado:>8.2f}\n"
            
            recibo += f"TOTAL: R$ {total:>10.2f}\n"
            recibo += f"{'-'*42}\n"
            
            recibo += "FORMA PAGAMENTO:\n"
            for pagamento in self.pagamentos:
                if pagamento['forma'] == 'CARTÃO CLIENTE':
                    recibo += f"CARTÃO CLIENTE: R$ {pagamento['valor']:>8.2f}\n"
                else:
                    recibo += f"{pagamento['forma']}: R$ {pagamento['valor']:>8.2f}\n"
            
            if troco > 0:
                recibo += f"TROCO: R$ {troco:>10.2f}\n"
            
            recibo += f"{'='*42}\n"
            recibo += f"{self.config_manager.get('RECIBO', 'mensagem_rodape').center(42)}\n"
            
            # Imprimir múltiplas cópias
            copias = self.config_manager.get('RECIBO', 'numero_copias', int)
            for i in range(copias):
                if i > 0:
                    recibo += f"\n{'** VIA CLIENTE **'.center(42)}\n"
                
                # Mostrar recibo
                self.mostrar_recibo_tela(recibo, venda_id)
                
                # IMPRIMIR AUTOMATICAMENTE se configurado
                if self.config_manager.get('RECIBO', 'imprimir_automaticamente', bool):
                    try:
                        sucesso = self.impressao.imprimir_recibo(recibo, venda_id)
                        if not sucesso:
                            messagebox.showwarning("Impressão", 
                                                "Recibo salvo, mas impressão falhou.\n"
                                                "Verifique configurações da impressora.")
                    except Exception as e:
                        print(f"Erro na impressão automática: {e}")
                        # Não mostrar erro ao usuário para não interromper o fluxo
                
        except Exception as e:
                print(f"Erro ao gerar recibo: {e}")
                # Fallback simples
                recibo_basico = f"RECIBO #{venda_id:06d}\nTotal: R$ {total:.2f}"
                self.mostrar_recibo_tela(recibo_basico, venda_id)
    
    def mostrar_recibo_tela(self, recibo, venda_id):
        """Mostra o recibo em uma janela"""
        recibo_window = tk.Toplevel(self.root)
        recibo_window.title(f"Recibo da Venda #{venda_id:06d}")
        recibo_window.geometry("500x600")
        recibo_window.transient(self.root)
        
        # Centralizar a janela
        recibo_window.update_idletasks()
        width = 500
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        recibo_window.geometry(f'{width}x{height}+{x}+{y}')
        
        text_frame = tk.Frame(recibo_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=('Courier', 10), wrap=tk.WORD)
        text_widget.insert(tk.END, recibo)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botão para imprimir/fechar
        btn_frame = tk.Frame(recibo_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="Fechar", command=recibo_window.destroy,
                 bg='#3498db', fg='white').pack(side=tk.RIGHT, padx=5)
        
        if self.config_manager.get('imprimir_recibo', True):
            tk.Button(btn_frame, text="Imprimir", command=lambda: self.imprimir_recibo(recibo),
                     bg='#27ae60', fg='white').pack(side=tk.RIGHT, padx=5)
    
    def verificar_configuracoes_empresa(self):
        """Verifica configurações essenciais - agora feito automaticamente pelo GerenciadorConfig"""
        # Este método não é mais necessário pois o GerenciadorConfig já cria configurações padrão
        pass
    
    def aplicar_desconto(self):
        """Aplica desconto - VERIFICA LOGIN"""
        if not self._verificar_login_para_venda():
            return
        
        """Aplica desconto usando teclado para entrada do valor"""
        if not self.venda_atual:
            messagebox.showwarning("Aviso", "Nenhum produto na venda!")
            return
        
        self.modo_desconto = True
        self.display_text = ""
        total = self.calcular_total()
        self.display_var.set("Digite valor do desconto...")
        self.op_var.set("Modo Desconto")
        self.op_secundario_var.set(f"Total: R$ {total:.2f} - Máx: R$ {total:.2f}")
        self.entrada_especial = 'DESCONTO'
    
    def selecionar_cliente(self):
        """Seleciona cliente - VERIFICA LOGIN"""
        if not self._verificar_login_para_venda():
            return
        """Seleciona cliente para a venda - VERSÃO COMPLETA E CORRIGIDA"""
        cliente_window = tk.Toplevel(self.root)
        cliente_window.title("Selecionar Cliente")
        cliente_window.geometry("600x500")
        cliente_window.transient(self.root)
        cliente_window.grab_set()
        
        # Centralizar
        cliente_window.update_idletasks()
        width = 600
        height = 500
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        cliente_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Frame de busca
        busca_frame = tk.Frame(cliente_window, bg='#f8f9fa')
        busca_frame.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(busca_frame, text="🔍 Buscar:", font=('Arial', 10, 'bold'), 
                 bg='#f8f9fa').pack(side=tk.LEFT, padx=(0, 10))
        
        busca_cliente_var = tk.StringVar()
        busca_entry = tk.Entry(busca_frame, textvariable=busca_cliente_var, 
                              width=30, font=('Arial', 10))
        busca_entry.pack(side=tk.LEFT, padx=5)
        
        # Atualizar lista enquanto digita
        def atualizar_busca(event=None):
            self.atualizar_lista_clientes(cliente_listbox, busca_cliente_var.get())
        
        busca_entry.bind('<KeyRelease>', atualizar_busca)
        
        # Botão limpar busca
        tk.Button(busca_frame, text="🗑️", font=('Arial', 8),
                  command=lambda: [busca_cliente_var.set(""), atualizar_busca()],
                  bg='#e74c3c', fg='white', width=3).pack(side=tk.LEFT, padx=5)
        
        # Lista de clientes
        lista_frame = tk.Frame(cliente_window)
        lista_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Cabeçalho da lista
        header_frame = tk.Frame(lista_frame, bg='#34495e')
        header_frame.pack(fill=tk.X)
        
        tk.Label(header_frame, text="Nome", width=30, anchor='w', 
                 bg='#34495e', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text="Telefone", width=15, anchor='w',
                 bg='#34495e', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Listbox com scroll
        listbox_frame = tk.Frame(lista_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        cliente_listbox = tk.Listbox(listbox_frame, font=('Arial', 10), 
                                    height=12, selectmode=tk.SINGLE)
        cliente_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=cliente_listbox.yview)
        cliente_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind duplo clique para seleção rápida
        cliente_listbox.bind('<Double-Button-1>', lambda e: selecionar())
        
        # Informações do cliente selecionado
        info_frame = tk.LabelFrame(cliente_window, text="Informações do Cliente", font=('Arial', 10))
        info_frame.pack(fill=tk.X, padx=15, pady=10)
        
        info_text = tk.Text(info_frame, height=3, font=('Arial', 9), wrap=tk.WORD)
        info_text.pack(fill=tk.X, padx=5, pady=5)
        info_text.config(state=tk.DISABLED)
        
        def atualizar_info_cliente(event=None):
            """Atualiza informações do cliente selecionado"""
            selecao = cliente_listbox.curselection()
            if selecao:
                cliente_texto = cliente_listbox.get(selecao[0])
                # Buscar informações completas do cliente
                nome = cliente_texto.split(' - ')[0]
                try:
                    self.cursor.execute('''
                        SELECT nome, telefone, email, endereco 
                        FROM clientes WHERE nome = %s
                    ''', (nome,))
                    cliente = self.cursor.fetchone()
                    if cliente:
                        info_text.config(state=tk.NORMAL)
                        info_text.delete(1.0, tk.END)
                        info = f"📞 {cliente['telefone'] or 'Sem telefone'}"
                        if cliente['email']:
                            info += f" | 📧 {cliente['email']}"
                        if cliente['endereco']:
                            info += f" | 📍 {cliente['endereco'][:50]}..."
                        info_text.insert(1.0, info)
                        info_text.config(state=tk.DISABLED)
                except Exception as e:
                    print(f"Erro ao buscar info cliente: {e}")
        
        cliente_listbox.bind('<<ListboxSelect>>', atualizar_info_cliente)
        
        # Botões
        botoes_frame = tk.Frame(cliente_window, bg='#f8f9fa')
        botoes_frame.pack(fill=tk.X, padx=15, pady=15)
        
        def selecionar():
            selecao = cliente_listbox.curselection()
            if selecao:
                cliente_texto = cliente_listbox.get(selecao[0])
                nome_cliente = cliente_texto.split(' - ')[0]
                
                # Buscar ID do cliente
                self.cursor.execute("SELECT id FROM clientes WHERE nome = %s", (nome_cliente,))
                resultado = self.cursor.fetchone()
                
                if resultado:
                    self.cliente_atual = resultado['id']  # Guardar o ID, não o nome
                    self.cliente_var.set(f"Cliente: {nome_cliente}")
                    cliente_window.destroy()
                    messagebox.showinfo("Sucesso", f"Cliente selecionado: {nome_cliente}")
                else:
                    messagebox.showerror("Erro", "Cliente não encontrado no banco de dados!")
            else:
                messagebox.showwarning("Aviso", "Selecione um cliente!")
        
        def novo_cliente():
            nome = simpledialog.askstring("Novo Cliente", "Nome do cliente:")
            if not nome:
                return
            
            telefone = simpledialog.askstring("Novo Cliente", "Telefone:")
            email = simpledialog.askstring("Novo Cliente", "Email (opcional):")
            endereco = simpledialog.askstring("Novo Cliente", "Endereço (opcional):")
            
            try:
                self.cursor.execute('''
                    INSERT INTO clientes (nome, telefone, email, endereco, data_cadastro, cadastrado_por)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (nome, telefone, email, endereco, datetime.now(), self.operador_atual['id']))
                
                self.conn.commit()
                cliente_id = self.cursor.lastrowid
                
                self.cliente_atual = cliente_id
                self.cliente_var.set(f"Cliente: {nome}")
                cliente_window.destroy()
                
                self.registrar_auditoria('CADASTRO_CLIENTE', f'Novo cliente: {nome}', 'clientes', cliente_id)
                messagebox.showinfo("Sucesso", "Cliente cadastrado com sucesso!")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao cadastrar cliente: {e}")
        
        def cliente_anonimo():
            self.cliente_atual = None
            self.cliente_var.set("Cliente: Não informado")
            cliente_window.destroy()
            messagebox.showinfo("Info", "Venda para cliente anônimo")
        
        def gerenciar_clientes():
            cliente_window.destroy()
            self.gerenciar_clientes_completo()
        
        # Layout dos botões
        tk.Button(botoes_frame, text="✅ Selecionar", command=selecionar, 
                 bg='#27ae60', fg='white', font=('Arial', 10, 'bold'), width=12).pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="➕ Novo", command=novo_cliente,
                 bg='#3498db', fg='white', font=('Arial', 10), width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="👤 Anônimo", command=cliente_anonimo,
                 bg='#95a5a6', fg='white', font=('Arial', 10), width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="📋 Gerenciar", command=gerenciar_clientes,
                 bg='#9b59b6', fg='white', font=('Arial', 10), width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="❌ Cancelar", command=cliente_window.destroy,
                 bg='#e74c3c', fg='white', font=('Arial', 10), width=10).pack(side=tk.RIGHT, padx=5)
        
        # Carregar clientes inicialmente
        self.atualizar_lista_clientes(cliente_listbox)
        
        # Focar na busca
        busca_entry.focus_set()
        
        # Atualizar a cada 2 segundos (para caso outros usuários adicionem clientes)
        def atualizar_periodicamente():
            if cliente_window.winfo_exists():
                self.atualizar_lista_clientes(cliente_listbox, busca_cliente_var.get())
                cliente_window.after(2000, atualizar_periodicamente)
        
        cliente_window.after(2000, atualizar_periodicamente)
    
    def atualizar_lista_clientes(self, listbox, busca=""):
        """Carrega clientes na listbox - VERSÃO MELHORADA"""
        # Salvar seleção atual
        selecao_atual = listbox.curselection()
        texto_selecionado = listbox.get(selecao_atual) if selecao_atual else ""
        
        listbox.delete(0, tk.END)
        
        try:
            query = """
                SELECT id, nome, telefone, email 
                FROM clientes 
                WHERE 1=1
            """
            params = []
            
            if busca and busca.strip():
                query += " AND (nome LIKE %s OR telefone LIKE %s OR email LIKE %s)"
                params.extend([f'%{busca}%', f'%{busca}%', f'%{busca}%'])
            
            query += " ORDER BY nome"
            
            self.cursor.execute(query, params)
            clientes = self.cursor.fetchall()
            
            if not clientes:
                if busca:
                    listbox.insert(tk.END, f"❌ Nenhum cliente encontrado para: '{busca}'")
                else:
                    listbox.insert(tk.END, "📝 Nenhum cliente cadastrado. Clique em 'Novo' para adicionar.")
                return
            
            for cliente in clientes:
                nome = cliente['nome']
                telefone = cliente['telefone'] or "Sem telefone"
                email = cliente['email'] or ""
                
                # Formatar exibição
                if email:
                    texto = f"{nome} - {telefone} - {email}"
                else:
                    texto = f"{nome} - {telefone}"
                
                listbox.insert(tk.END, texto)
                
                # Restaurar seleção anterior se possível
                if texto == texto_selecionado:
                    listbox.selection_set(tk.END)
            
            # Selecionar o primeiro item se houver clientes
            if clientes and not selecao_atual:
                listbox.selection_set(0)
                listbox.see(0)
                
        except Exception as e:
            print(f"Erro ao carregar clientes: {e}")
            listbox.insert(tk.END, f"❌ Erro ao carregar clientes: {str(e)}")
    
    def gerenciar_clientes_completo(self):
        """Interface completa de gerenciamento de clientes - VERSÃO CORRIGIDA"""
        if not self.verificar_acesso_supervisor():
            return
        
        gerenciar_window = tk.Toplevel(self.root)
        gerenciar_window.title("Gerenciamento de Clientes")
        gerenciar_window.geometry("900x600")
        gerenciar_window.transient(self.root)
        
        # Notebook para abas
        notebook = ttk.Notebook(gerenciar_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba Lista de Clientes
        frame_lista = ttk.Frame(notebook)
        notebook.add(frame_lista, text="📋 Lista de Clientes")
        
        # Controles
        controles_frame = tk.Frame(frame_lista)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(controles_frame, text="➕ Novo Cliente", 
                 command=self.novo_cliente_avancado, bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(controles_frame, text="✏️ Editar", 
                 command=lambda: self.editar_cliente_selecionado(tree), bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(controles_frame, text="🔄 Atualizar", 
                 command=lambda: self.carregar_clientes_arvore(tree), bg='#f39c12', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(controles_frame, text="📊 Exportar", 
                 command=self.exportar_clientes, bg='#9b59b6', fg='white').pack(side=tk.LEFT, padx=5)
        
        # Frame de busca
        busca_frame = tk.Frame(frame_lista)
        busca_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(busca_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busca_var = tk.StringVar()
        busca_entry = tk.Entry(busca_frame, textvariable=busca_var, width=30)
        busca_entry.pack(side=tk.LEFT, padx=5)
        
        def buscar_clientes():
            texto_busca = busca_var.get().strip()
            if texto_busca:
                try:
                    for item in tree.get_children():
                        tree.delete(item)
                    
                    self.cursor.execute('''
                        SELECT id, nome, telefone, email, data_cadastro 
                        FROM clientes 
                        WHERE nome LIKE %s OR telefone LIKE %s OR email LIKE %s
                        ORDER BY nome
                    ''', (f'%{texto_busca}%', f'%{texto_busca}%', f'%{texto_busca}%'))
                    
                    for cliente in self.cursor.fetchall():
                        data_formatada = cliente['data_cadastro'].strftime('%d/%m/%Y') if cliente['data_cadastro'] else 'N/A'
                        tree.insert('', tk.END, values=(
                            cliente['id'],
                            cliente['nome'],
                            cliente['telefone'] or 'N/A',
                            cliente['email'] or 'N/A',
                            data_formatada
                        ))
                except Exception as e:
                    print(f"Erro na busca: {e}")
            else:
                self.carregar_clientes_arvore(tree)
        
        tk.Button(busca_frame, text="🔍 Buscar", command=buscar_clientes,
                 bg='#2c3e50', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(busca_frame, text="🗑️ Limpar", command=lambda: [busca_var.set(""), self.carregar_clientes_arvore(tree)],
                 bg='#e74c3c', fg='white').pack(side=tk.LEFT, padx=5)
        
        # Treeview de clientes
        tree_frame = tk.Frame(frame_lista)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('id', 'nome', 'telefone', 'email', 'data_cadastro')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree.heading('id', text='ID')
        tree.heading('nome', text='Nome')
        tree.heading('telefone', text='Telefone')
        tree.heading('email', text='Email')
        tree.heading('data_cadastro', text='Data Cadastro')
        
        tree.column('id', width=50)
        tree.column('nome', width=200)
        tree.column('telefone', width=120)
        tree.column('email', width=200)
        tree.column('data_cadastro', width=120)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind duplo clique para editar
        tree.bind('<Double-1>', lambda e: self.editar_cliente_selecionado(tree))
        
        # Carregar dados
        self.carregar_clientes_arvore(tree)
        
        # Aba Estatísticas
        frame_stats = ttk.Frame(notebook)
        notebook.add(frame_stats, text="📊 Estatísticas")
        
        self.criar_estatisticas_clientes(frame_stats)
    
    def editar_cliente_selecionado(self, tree):
        """Edita cliente selecionado na treeview"""
        selecao = tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um cliente para editar!")
            return
        
        item = tree.item(selecao[0])
        cliente_id = item['values'][0]
        
        # Buscar dados completos do cliente
        self.cursor.execute('''
            SELECT * FROM clientes WHERE id = %s
        ''', (cliente_id,))
        
        cliente = self.cursor.fetchone()
        if not cliente:
            messagebox.showerror("Erro", "Cliente não encontrado!")
            return
        
        # Janela de edição (similar ao novo_cliente_avancado)
        editar_window = tk.Toplevel(self.root)
        editar_window.title(f"Editar Cliente: {cliente['nome']}")
        editar_window.geometry("500x400")
        editar_window.transient(self.root)
        editar_window.grab_set()
        
        main_frame = tk.Frame(editar_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text=f"EDITAR CLIENTE: {cliente['nome']}", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Campos do formulário (preenchidos com dados atuais)
        campos_frame = tk.Frame(main_frame)
        campos_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Nome
        tk.Label(campos_frame, text="Nome *:", font=('Arial', 10)).grid(row=0, column=0, sticky='w', pady=5)
        nome_var = tk.StringVar(value=cliente['nome'])
        nome_entry = tk.Entry(campos_frame, textvariable=nome_var, width=40, font=('Arial', 10))
        nome_entry.grid(row=0, column=1, sticky='w', pady=5, padx=10)
        
        # Telefone
        tk.Label(campos_frame, text="Telefone:", font=('Arial', 10)).grid(row=1, column=0, sticky='w', pady=5)
        telefone_var = tk.StringVar(value=cliente['telefone'] or '')
        telefone_entry = tk.Entry(campos_frame, textvariable=telefone_var, width=40, font=('Arial', 10))
        telefone_entry.grid(row=1, column=1, sticky='w', pady=5, padx=10)
        
        # Email
        tk.Label(campos_frame, text="Email:", font=('Arial', 10)).grid(row=2, column=0, sticky='w', pady=5)
        email_var = tk.StringVar(value=cliente['email'] or '')
        email_entry = tk.Entry(campos_frame, textvariable=email_var, width=40, font=('Arial', 10))
        email_entry.grid(row=2, column=1, sticky='w', pady=5, padx=10)
        
        # Endereço
        tk.Label(campos_frame, text="Endereço:", font=('Arial', 10)).grid(row=3, column=0, sticky='w', pady=5)
        endereco_text = tk.Text(campos_frame, width=40, height=4, font=('Arial', 10))
        endereco_text.grid(row=3, column=1, sticky='w', pady=5, padx=10)
        endereco_text.insert(1.0, cliente['endereco'] or '')
        
        def salvar_edicao():
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O nome é obrigatório!")
                nome_entry.focus()
                return
            
            telefone = telefone_var.get().strip()
            email = email_var.get().strip()
            endereco = endereco_text.get(1.0, tk.END).strip()
            
            try:
                self.cursor.execute('''
                    UPDATE clientes 
                    SET nome = %s, telefone = %s, email = %s, endereco = %s
                    WHERE id = %s
                ''', (nome, telefone, email, endereco, cliente_id))
                
                self.conn.commit()
                
                self.registrar_auditoria('EDICAO_CLIENTE', f'Cliente editado: {cliente["nome"]} -> {nome}', 'clientes', cliente_id)
                messagebox.showinfo("Sucesso", f"Cliente '{nome}' atualizado com sucesso!")
                editar_window.destroy()
                self.carregar_clientes_arvore(tree)
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao atualizar cliente: {e}")
        
        # Botões
        botoes_frame = tk.Frame(main_frame)
        botoes_frame.pack(fill=tk.X, pady=20)
        
        tk.Button(botoes_frame, text="💾 Salvar", command=salvar_edicao,
                 bg='#27ae60', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="❌ Cancelar", command=editar_window.destroy,
                 bg='#e74c3c', fg='white', font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)
        
        # Focar no campo nome
        nome_entry.focus()
        nome_entry.select_range(0, tk.END)
    
    def criar_estatisticas_clientes(self, parent):
        """Cria estatísticas de clientes"""
        try:
            # Total de clientes
            self.cursor.execute("SELECT COUNT(*) as total FROM clientes")
            total_clientes = self.cursor.fetchone()['total']
            
            # Clientes cadastrados este mês
            self.cursor.execute('''
                SELECT COUNT(*) as total 
                FROM clientes 
                WHERE MONTH(data_cadastro) = MONTH(CURDATE()) 
                AND YEAR(data_cadastro) = YEAR(CURDATE())
            ''')
            clientes_mes = self.cursor.fetchone()['total']
            
            # Clientes com telefone
            self.cursor.execute("SELECT COUNT(*) as total FROM clientes WHERE telefone IS NOT NULL AND telefone != ''")
            com_telefone = self.cursor.fetchone()['total']
            
            # Clientes com email
            self.cursor.execute("SELECT COUNT(*) as total FROM clientes WHERE email IS NOT NULL AND email != ''")
            com_email = self.cursor.fetchone()['total']
            
            # Exibir estatísticas
            stats_frame = tk.Frame(parent)
            stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            tk.Label(stats_frame, text="📊 ESTATÍSTICAS DE CLIENTES", 
                    font=('Arial', 16, 'bold')).pack(pady=20)
            
            # Grid de estatísticas
            estatisticas = [
                ("👥 Total de Clientes", f"{total_clientes} clientes"),
                ("📅 Cadastrados Este Mês", f"{clientes_mes} clientes"),
                ("📞 Com Telefone", f"{com_telefone} clientes ({com_telefone/total_clientes*100:.1f}%)"),
                ("📧 Com Email", f"{com_email} clientes ({com_email/total_clientes*100:.1f}%)"),
            ]
            
            for i, (titulo, valor) in enumerate(estatisticas):
                frame = tk.Frame(stats_frame, relief=tk.RAISED, bd=1)
                frame.pack(fill=tk.X, pady=5)
                
                tk.Label(frame, text=titulo, font=('Arial', 12), 
                        anchor='w').pack(side=tk.LEFT, padx=10, pady=10)
                tk.Label(frame, text=valor, font=('Arial', 12, 'bold'), 
                        fg='#2c3e50').pack(side=tk.RIGHT, padx=10, pady=10)
            
        except Exception as e:
            print(f"Erro ao carregar estatísticas: {e}")
    
    def carregar_clientes_arvore(self, tree):
        """Carrega clientes na treeview - VERSÃO CORRIGIDA"""
        for item in tree.get_children():
            tree.delete(item)
        
        try:
            self.cursor.execute('''
                SELECT id, nome, telefone, email, data_cadastro 
                FROM clientes 
                ORDER BY nome
            ''')
            
            for cliente in self.cursor.fetchall():
                data_formatada = cliente['data_cadastro'].strftime('%d/%m/%Y') if cliente['data_cadastro'] else 'N/A'
                tree.insert('', tk.END, values=(
                    cliente['id'],
                    cliente['nome'],
                    cliente['telefone'] or 'N/A',
                    cliente['email'] or 'N/A',
                    data_formatada
                ))
        except Exception as e:
            print(f"Erro ao carregar clientes na treeview: {e}")
    
    def novo_cliente_avancado(self):
        """Cadastro avançado de cliente com formulário completo"""
        if not self.verificar_acesso_supervisor():
            return
        
        cliente_window = tk.Toplevel(self.root)
        cliente_window.title("Cadastro de Cliente")
        cliente_window.geometry("500x400")
        cliente_window.transient(self.root)
        cliente_window.grab_set()
        
        main_frame = tk.Frame(cliente_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="CADASTRO DE CLIENTE", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Campos do formulário
        campos_frame = tk.Frame(main_frame)
        campos_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Nome
        tk.Label(campos_frame, text="Nome *:", font=('Arial', 10)).grid(row=0, column=0, sticky='w', pady=5)
        nome_var = tk.StringVar()
        nome_entry = tk.Entry(campos_frame, textvariable=nome_var, width=40, font=('Arial', 10))
        nome_entry.grid(row=0, column=1, sticky='w', pady=5, padx=10)
        
        # Telefone
        tk.Label(campos_frame, text="Telefone:", font=('Arial', 10)).grid(row=1, column=0, sticky='w', pady=5)
        telefone_var = tk.StringVar()
        telefone_entry = tk.Entry(campos_frame, textvariable=telefone_var, width=40, font=('Arial', 10))
        telefone_entry.grid(row=1, column=1, sticky='w', pady=5, padx=10)
        
        # Email
        tk.Label(campos_frame, text="Email:", font=('Arial', 10)).grid(row=2, column=0, sticky='w', pady=5)
        email_var = tk.StringVar()
        email_entry = tk.Entry(campos_frame, textvariable=email_var, width=40, font=('Arial', 10))
        email_entry.grid(row=2, column=1, sticky='w', pady=5, padx=10)
        
        # Endereço
        tk.Label(campos_frame, text="Endereço:", font=('Arial', 10)).grid(row=3, column=0, sticky='w', pady=5)
        endereco_text = tk.Text(campos_frame, width=40, height=4, font=('Arial', 10))
        endereco_text.grid(row=3, column=1, sticky='w', pady=5, padx=10)
        
        # Observações
        tk.Label(campos_frame, text="Observações:", font=('Arial', 10)).grid(row=4, column=0, sticky='w', pady=5)
        observacoes_text = tk.Text(campos_frame, width=40, height=3, font=('Arial', 10))
        observacoes_text.grid(row=4, column=1, sticky='w', pady=5, padx=10)
        
        def salvar_cliente():
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O nome é obrigatório!")
                nome_entry.focus()
                return
            
            telefone = telefone_var.get().strip()
            email = email_var.get().strip()
            endereco = endereco_text.get(1.0, tk.END).strip()
            observacoes = observacoes_text.get(1.0, tk.END).strip()
            
            try:
                self.cursor.execute('''
                    INSERT INTO clientes (nome, telefone, email, endereco, observacoes, data_cadastro, cadastrado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (nome, telefone, email, endereco, observacoes, datetime.now(), self.operador_atual['id']))
                
                self.conn.commit()
                cliente_id = self.cursor.lastrowid
                
                self.registrar_auditoria('CADASTRO_CLIENTE_AVANCADO', f'Cliente: {nome}', 'clientes', cliente_id)
                messagebox.showinfo("Sucesso", f"Cliente '{nome}' cadastrado com sucesso!")
                cliente_window.destroy()
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao cadastrar cliente: {e}")
        
        # Botões
        botoes_frame = tk.Frame(main_frame)
        botoes_frame.pack(fill=tk.X, pady=20)
        
        tk.Button(botoes_frame, text="💾 Salvar", command=salvar_cliente,
                 bg='#27ae60', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(botoes_frame, text="❌ Cancelar", command=cliente_window.destroy,
                 bg='#e74c3c', fg='white', font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)
        
        # Focar no campo nome
        nome_entry.focus()
    
    def exportar_clientes(self):
        """Exporta lista de clientes para CSV"""
        try:
            filename = f"clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ID;Nome;Telefone;Email;Endereço;Data Cadastro\n")
                
                self.cursor.execute('''
                    SELECT id, nome, telefone, email, endereco, data_cadastro 
                    FROM clientes 
                    ORDER BY nome
                ''')
                
                for cliente in self.cursor.fetchall():
                    data_formatada = cliente['data_cadastro'].strftime('%d/%m/%Y %H:%M') if cliente['data_cadastro'] else 'N/A'
                    f.write(f"{cliente['id']};{cliente['nome']};{cliente['telefone'] or ''};{cliente['email'] or ''};{cliente['endereco'] or ''};{data_formatada}\n")
            
            messagebox.showinfo("Exportado", f"Lista de clientes exportada para:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar clientes: {e}")
    
    def adicionar_cliente_rapido(self, parent):
        nome = simpledialog.askstring("Novo Cliente", "Nome do cliente:")
        if nome:
            telefone = simpledialog.askstring("Novo Cliente", "Telefone:")
            data_cadastro = datetime.now().strftime("%Y-%m-%d")
            
            self.cursor.execute(
                "INSERT INTO clientes (nome, telefone, data_cadastro) VALUES (%s, %s, %s)",
                (nome, telefone, data_cadastro)
            )
            self.conn.commit()
            
            self.cliente_atual = nome
            self.cliente_var.set(f"Cliente: {nome}")
            parent.destroy()
            messagebox.showinfo("Sucesso", "Cliente cadastrado com sucesso!")
    
    def cancelar_entrada(self):
        self._limpar_modo_especial()
        """Cancela a entrada atual - VERIFICA LOGIN"""
        if not hasattr(self, 'operador_atual') or not self.operador_atual:
          self.display_var.set("🔒 Efetue login para esta operação")
          self.display_secundario_var.set("Faça login Op")
          self.fazer_login_display()
          return False
         
        # Sempre permite cancelar, mesmo sem login
        
        self.display_var.set("Operação cancelada")
        self.display_secundario_var.set("Pronto para nova operação")
        
    def mostrar_login(self):
        login_window = tk.Toplevel(self.root)
        login_window.title("Login - Sistema de Vendas")
        login_window.geometry("300x300")
        login_window.transient(self.root)
        login_window.grab_set()
        login_window.resizable(False, False)
        
        # Centralizar a janela
        login_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + self.root.winfo_width() // 2 - 150,
            self.root.winfo_rooty() + self.root.winfo_height() // 2 - 100
        ))
        
        # Forçar o foco
        login_window.focus_force()
        login_window.lift()
        
        tk.Label(login_window, text="SISTEMA DE VENDAS", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        tk.Label(login_window, text="Usuário:").pack()
        usuario_var = tk.StringVar()
        usuario_entry = tk.Entry(login_window, textvariable=usuario_var, width=20)
        usuario_entry.pack(pady=5)
        
        tk.Label(login_window, text="Senha:").pack()
        senha_var = tk.StringVar()
        senha_entry = tk.Entry(login_window, textvariable=senha_var, show='*', width=20)
        senha_entry.pack(pady=5)

    def nova_venda(self):
        self.limpar_venda()
    
    def limpar_venda(self):
        self.venda_atual = []
        self.modo_pagamento = False
        self.modo_quantidade = False
        self.modo_multiplos_pagamentos = False
        self.pagamentos = []
        self.forma_pagamento = ""
        self.valor_pago_str = ""
        self.display_text = ""
        self.desconto_aplicado = 0
        self.cliente_atual = None
        self.cliente_var.set("Cliente: Não informado")
        self.display_var.set("Nova venda iniciada...")
        self.op_var.set("Operação: Aguardando...")
        self.atualizar_display()
        
        # Esconder frames de pagamento
        self.pagamento_frame.pack_forget()
        self.info_frame.pack_forget()

    def vendas_do_dia(self):
        messagebox.showinfo("Vendas do Dia", "Funcionalidade em desenvolvimento")
  
    def imprimir_recibo(self, recibo):
        # Simulação de impressão - salvar em arquivo
        try:
            with open(f"recibo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w', encoding='utf-8') as f:
                f.write(recibo)
            messagebox.showinfo("Impressão", "Recibo salvo para impressão!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar recibo: {e}")        
                     
    # antigo fim

    def criar_interface(self):
        """Cria a interface principal do sistema"""
        # Inicializar variáveis de interface PRIMEIRO
        self.inicializar_variaveis_interface()
        
        # Menu principal
        self.criar_menu()
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header
        self.criar_header(main_frame)
        
        # NÃO criar botão de administração aqui - será criado após login se necessário
        # O botão será criado dinamicamente no método atualizar_botao_administracao()
        
        # Corpo principal
        body_frame = tk.Frame(main_frame, bg='#2c3e50')
        body_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Painel esquerdo - Produtos
        left_panel = tk.Frame(body_frame, bg='#34495e', relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Painel direito - Teclado e informações (COM SCROLL)
        right_panel = tk.Frame(body_frame, bg='#34495e', relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        # Criar componentes
        self.criar_painel_produtos(left_panel)
        self.criar_painel_direito_com_scroll(right_panel)
        
        # Mostrar tela de login automaticamente
        self.root.after(500, self.fazer_login)
        
    def inicializar_variaveis_interface(self):
        """Inicializa variáveis da interface"""
        # Variáveis para display
        self.display_var = tk.StringVar(value="Pronto para vender...")
        self.op_var = tk.StringVar(value="Operação: Aguardando...")
        self.operador_var = tk.StringVar(value="Operador: Não logado")
        self.cliente_var = tk.StringVar(value="Cliente: Não informado")
        self.subtotal_var = tk.StringVar(value="Subtotal: R$ 0,00")
        self.desconto_var = tk.StringVar(value="Desconto: R$ 0,00")
        self.total_var = tk.StringVar(value="R$ 0,00")
        
        # Variáveis para busca/filtro
        self.busca_var = tk.StringVar()
        self.categoria_var = tk.StringVar(value="Todos")
        
        # Variáveis de pagamento
        self.valor_pago_var = tk.StringVar(value="R$ 0,00")
        self.troco_var = tk.StringVar(value="R$ 0,00")
        
        # Atualizar informações do operador se já estiver logado
        if hasattr(self, 'operador_atual') and self.operador_atual:
            self.operador_var.set(f"Operador: {self.operador_atual['nome']}")
    
    def criar_header(self, parent):
        """Cria o cabeçalho da interface"""
        header_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo e título
        title_frame = tk.Frame(header_frame, bg='#34495e')
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        title_label = tk.Label(title_frame, text=f"{self.config_manager.get('empresa_nome', 'Sistema de Vendas')} - PROFESSIONAL PLUS", 
                              font=('Arial', 18, 'bold'), bg='#34495e', fg='#ecf0f1')
        title_label.pack(side=tk.LEFT)
        
        # Informações do operador e cliente
        info_frame = tk.Frame(title_frame, bg='#34495e')
        info_frame.pack(side=tk.RIGHT)
        
        operador_label = tk.Label(info_frame, textvariable=self.operador_var,
                                 font=('Arial', 10), bg='#34495e', fg='#bdc3c7')
        operador_label.pack(anchor=tk.E)
        
        cliente_label = tk.Label(info_frame, textvariable=self.cliente_var,
                               font=('Arial', 10), bg='#34495e', fg='#bdc3c7')
        cliente_label.pack(anchor=tk.E)
        
        # Status do caixa
        self.status_caixa_label = tk.Label(info_frame, font=('Arial', 10, 'bold'), 
                                          bg='#e74c3c', fg='white', padx=10, pady=2)
        self.status_caixa_label.pack(anchor=tk.E, pady=2)
        self.atualizar_status_caixa()
        
        # Data e hora
        self.time_label = tk.Label(info_frame, font=('Arial', 10), bg='#34495e', fg='#bdc3c7')
        self.time_label.pack(anchor=tk.E)
        self.atualizar_relogio()
    
    def criar_painel_produtos(self, parent):
        """Cria o painel de produtos"""
        # Filtros e busca
        filtros_frame = tk.Frame(parent, bg='#34495e')
        filtros_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Busca
        tk.Label(filtros_frame, text="Buscar:", font=('Arial', 10), 
                bg='#34495e', fg='#ecf0f1').pack(side=tk.LEFT, padx=(0, 5))
        
        busca_entry = tk.Entry(filtros_frame, textvariable=self.busca_var, font=('Arial', 10), width=20)
        busca_entry.pack(side=tk.LEFT, padx=(0, 10))
        busca_entry.bind('<KeyRelease>', self.filtrar_produtos)
        
        # Categorias
        tk.Label(filtros_frame, text="Categoria:", font=('Arial', 10),
                bg='#34495e', fg='#ecf0f1').pack(side=tk.LEFT, padx=(0, 5))
        
        # Carregar categorias do banco
        categorias = ["Todos"]
        try:
            self.cursor.execute("SELECT nome FROM categorias WHERE ativo = TRUE ORDER BY nome")
            categorias_db = [cat['nome'] for cat in self.cursor.fetchall()]
            categorias.extend(categorias_db)
        except Exception as e:
            print(f"Erro ao carregar categorias: {e}")
        
        self.categoria_combo = ttk.Combobox(filtros_frame, textvariable=self.categoria_var, 
                                          values=categorias, state="readonly", width=15)
        self.categoria_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.categoria_combo.bind('<<ComboboxSelected>>', self.filtrar_produtos)
        
        # Botão atualizar
        atualizar_btn = tk.Button(filtros_frame, text="Atualizar", font=('Arial', 9),
                                 bg='#3498db', fg='white', command=self.carregar_botoes_produtos)
        atualizar_btn.pack(side=tk.LEFT)
        
        # ... resto do método permanece igual ...
        
        # Display de entrada MELHORADO com 2 linhas
        display_frame = tk.Frame(parent, bg='#2c3e50')
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Primeira linha - informação principal
        self.display_var = tk.StringVar(value="Pronto para vender...")
        display_label = tk.Label(display_frame, textvariable=self.display_var,
                                font=('Arial', 14), bg='#1a252f', fg='#2ecc71',
                                height=1, anchor=tk.W, padx=10)
        display_label.pack(fill=tk.X, pady=(5, 0))
        
        # Segunda linha - informação secundária
        self.display_secundario_var = tk.StringVar(value="Aguardando operação...")
        display_secundario_label = tk.Label(display_frame, textvariable=self.display_secundario_var,
                                           font=('Arial', 12), bg='#1a252f', fg='#3498db',
                                           height=1, anchor=tk.W, padx=10)
        display_secundario_label.pack(fill=tk.X, pady=(0, 5))
        
        # Treeview dos itens da venda
        tree_frame = tk.Frame(parent, bg='#34495e')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('produto', 'qtd', 'preco', 'subtotal')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)
        
        # Definir cabeçalhos
        self.tree.heading('produto', text='PRODUTO')
        self.tree.heading('qtd', text='QTD')
        self.tree.heading('preco', text='PREÇO UNIT.')
        self.tree.heading('subtotal', text='SUBTOTAL')
        
        # Definir largura das colunas
        self.tree.column('produto', width=400)
        self.tree.column('qtd', width=80)
        self.tree.column('preco', width=120)
        self.tree.column('subtotal', width=120)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame de totais
        totais_frame = tk.Frame(parent, bg='#34495e')
        totais_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Subtotal e desconto
        info_totais_frame = tk.Frame(totais_frame, bg='#34495e')
        info_totais_frame.pack(fill=tk.X)
        
        subtotal_label = tk.Label(info_totais_frame, textvariable=self.subtotal_var,
                                font=('Arial', 10), bg='#34495e', fg='#bdc3c7')
        subtotal_label.pack(side=tk.LEFT)
        
        desconto_label = tk.Label(info_totais_frame, textvariable=self.desconto_var,
                                font=('Arial', 10), bg='#34495e', fg='#e74c3c')
        desconto_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Total
        total_label = tk.Label(totais_frame, text="TOTAL:", font=('Arial', 16, 'bold'),
                              bg='#34495e', fg='#ecf0f1')
        total_label.pack(side=tk.LEFT)
        
        total_valor = tk.Label(totais_frame, textvariable=self.total_var,
                              font=('Arial', 20, 'bold'), bg='#34495e', fg='#2ecc71')
        total_valor.pack(side=tk.RIGHT)
        
        # Container com scroll para produtos
        self.produtos_main_frame = tk.Frame(parent, bg='#34495e')
        self.produtos_main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas e Scrollbar para produtos
        self.canvas = tk.Canvas(self.produtos_main_frame, bg='#34495e', highlightthickness=0)
        scrollbar_produtos = ttk.Scrollbar(self.produtos_main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#34495e')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar_produtos.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar_produtos.pack(side="right", fill="y")
        
        # Botões de navegação
        nav_frame = tk.Frame(parent, bg='#34495e')
        nav_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(nav_frame, text="▲", font=('Arial', 12), 
                 command=self.scroll_up, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="▼", font=('Arial', 12),
                 command=self.scroll_down, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        
        # Carregar produtos
        self.carregar_botoes_produtos()
    
    def criar_painel_direito_com_scroll(self, parent):
        """Cria o painel direito com scrollbar"""
        # Frame principal com scroll
        main_frame = tk.Frame(parent, bg='#34495e')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas e Scrollbar
        canvas = tk.Canvas(main_frame, bg='#34495e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        # Frame scrollável
        self.scrollable_frame_direito = tk.Frame(canvas, bg='#34495e')
        
        self.scrollable_frame_direito.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame_direito, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empacotar canvas e scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configurar scroll com mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Adicionar conteúdo ao frame scrollável
        self.adicionar_conteudo_painel_direito()
    
    def adicionar_conteudo_painel_direito(self):
        """Adiciona todo o conteúdo ao painel direito com scroll"""
        # Display de operação MELHORADO
        op_frame = tk.Frame(self.scrollable_frame_direito, bg='#2c3e50')
        op_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Primeira linha do display
        self.op_var = tk.StringVar(value="Operação: Aguardando...")
        op_label = tk.Label(op_frame, textvariable=self.op_var, font=('Arial', 12),
                           bg='#2c3e50', fg='#ecf0f1')
        op_label.pack()
        
        # Segunda linha do display
        self.op_secundario_var = tk.StringVar(value="Use o teclado para entrada")
        op_secundario_label = tk.Label(op_frame, textvariable=self.op_secundario_var, 
                                      font=('Arial', 10), bg='#2c3e50', fg='#bdc3c7')
        op_secundario_label.pack()
        
        # === NOVO: BOTÕES ESPECIAIS ===
        self.criar_botoes_supervisor_especiais(self.scrollable_frame_direito)
        
        # Teclado numérico
        teclado_frame = tk.Frame(self.scrollable_frame_direito, bg='#34495e')
        teclado_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.criar_teclado_numerico(teclado_frame)
        
        # Botões de função principais
        funcoes_frame = tk.Frame(self.scrollable_frame_direito, bg='#34495e')
        funcoes_frame.pack(fill=tk.X, padx=10, pady=5)
        
        botoes_funcao = [
            ("💳 TOTAL", self.mostrar_formas_pagamento, '#f39c12'),
            ("🎯 DESCONTO", self.aplicar_desconto, '#9b59b6'),
            ("💰 CONSULTAR SALDO", self.consultar_saldo_cartao_display, '#16a085'),  # NOVO BOTÃO
            ("👨‍💼 SUPERVISOR", self.mostrar_menu_supervisor, '#e67e22'),
            ("👥 CLIENTE", self.selecionar_cliente, '#3498db'),
            ("🔄 NOVA VENDA", self.nova_venda, '#27ae60'),
            ("❌ CANCELAR", self.cancelar_entrada, '#e67e22')
        ]
        
        for texto, comando, cor in botoes_funcao:
            btn = tk.Button(funcoes_frame, text=texto, font=('Arial', 10, 'bold'),
                           bg=cor, fg='white', height=1 if texto == "❌ CANCELAR" else 2,
                           command=comando)
            btn.pack(fill=tk.X, pady=2)
        
        # Frame de formas de pagamento (inicialmente escondido)
        self.pagamento_frame = tk.Frame(self.scrollable_frame_direito, bg='#34495e')
        
        # Informações de pagamento
        self.info_frame = tk.Frame(self.scrollable_frame_direito, bg='#34495e')
    
    def criar_teclado_numerico(self, parent):
        """Cria o teclado numérico"""
        teclado_grid = tk.Frame(parent, bg='#34495e')
        teclado_grid.pack(fill=tk.BOTH, expand=True)
        
        botoes = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0, 2), (',', 3, 2),
            ('✕ Qtd', 4, 0, 1, '#e67e22'),
            ('⌫', 4, 1, 1, '#e74c3c'),
            ('Enter ↵', 4, 2, 1, '#27ae60')
        ]
        
        for btn_info in botoes:
            if len(btn_info) == 3:
                texto, linha, coluna = btn_info
                colspan, cor = 1, '#2c3e50'
            elif len(btn_info) == 4:
                texto, linha, coluna, colspan = btn_info
                cor = '#2c3e50'
            else:
                texto, linha, coluna, colspan, cor = btn_info
                
            btn = tk.Button(teclado_grid, text=texto, font=('Arial', 12, 'bold'),
                           bg=cor, fg='white', height=2, width=6,
                           command=lambda t=texto: self.pressionar_tecla(t))
            btn.grid(row=linha, column=coluna, columnspan=colspan, 
                    padx=2, pady=2, sticky='nsew')
        
        for i in range(5):
            teclado_grid.rowconfigure(i, weight=1)
        for i in range(3):
            teclado_grid.columnconfigure(i, weight=1)
    
    # nova class impr print fim
        # =============================================================================
    # SISTEMA DE CARTÃO CLIENTE - ADICIONE ESTES MÉTODOS ANTES DO criar_menu()
    # =============================================================================
    
    def gerenciar_cartoes_cliente(self):
        """Interface para gerenciamento de cartões cliente"""
        if not self.verificar_acesso_supervisor():
            return
    
        cartoes_window = tk.Toplevel(self.root)
        cartoes_window.title("Gestão de Cartões Cliente")
        cartoes_window.geometry("1000x600")
        cartoes_window.transient(self.root)
    
        # Frame de controles
        controles_frame = tk.Frame(cartoes_window)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)
    
        tk.Button(controles_frame, text="➕ Novo Cartão", 
                 command=self.emitir_novo_cartao, bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="💰 Carregar Saldo", 
                 command=self.carregar_saldo_cartao, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="📊 Consultar Saldo", 
                 command=self.consultar_saldo_cartao, bg='#9b59b6', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="🔄 Ativar/Desativar", 
                 command=self.alterar_status_cartao, bg='#e67e22', fg='white').pack(side=tk.LEFT, padx=5)
    
        # Treeview de cartões
        tree_frame = tk.Frame(cartoes_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        columns = ('id', 'numero', 'cliente', 'saldo', 'validade', 'status')
        tree_cartoes = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree_cartoes.heading('id', text='ID')
        tree_cartoes.heading('numero', text='Nº Cartão')
        tree_cartoes.heading('cliente', text='Cliente')
        tree_cartoes.heading('saldo', text='Saldo')
        tree_cartoes.heading('validade', text='Validade')
        tree_cartoes.heading('status', text='Status')
    
        for col in columns:
            tree_cartoes.column(col, width=120)
    
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree_cartoes.yview)
        tree_cartoes.configure(yscrollcommand=scrollbar.set)
    
        tree_cartoes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Carregar dados
        self.carregar_cartoes(tree_cartoes)
    
    def carregar_cartoes(self, tree):
        """Carrega cartões na treeview"""
        for item in tree.get_children():
            tree.delete(item)
    
        self.cursor.execute('''
            SELECT cc.id, cc.numero_cartao, c.nome as cliente_nome, 
                   cc.saldo, cc.data_validade, cc.ativo
            FROM cartoes_cliente cc
            JOIN clientes c ON cc.cliente_id = c.id
            ORDER BY cc.data_emissao DESC
        ''')
        
        for cartao in self.cursor.fetchall():
            status = "Ativo" if cartao['ativo'] else "Inativo"
            validade = cartao['data_validade'].strftime('%d/%m/%Y') if cartao['data_validade'] else "Indeterminada"
            
            tree.insert('', tk.END, values=(
                cartao['id'],
                cartao['numero_cartao'],
                cartao['cliente_nome'],
                f"R$ {float(cartao['saldo']):.2f}",
                validade,
                status
            ))
    
    def emitir_novo_cartao(self):
        """Emite novo cartão para cliente"""
        if not self.verificar_acesso_supervisor():
            return
    
        # Janela para selecionar cliente
        cliente_window = tk.Toplevel(self.root)
        cliente_window.title("Selecionar Cliente para Cartão")
        cliente_window.geometry("500x400")
        cliente_window.transient(self.root)
    
        tk.Label(cliente_window, text="Selecione o Cliente:", 
                font=('Arial', 12, 'bold')).pack(pady=10)
    
        # Lista de clientes
        lista_frame = tk.Frame(cliente_window)
        lista_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
        cliente_listbox = tk.Listbox(lista_frame, font=('Arial', 11))
        cliente_listbox.pack(fill=tk.BOTH, expand=True)
    
        # Carregar clientes
        self.cursor.execute('''
            SELECT c.id, c.nome, c.telefone 
            FROM clientes c 
            ORDER BY c.nome
        ''')
        
        clientes = self.cursor.fetchall()
        for cliente in clientes:
            cliente_listbox.insert(tk.END, f"{cliente['id']} - {cliente['nome']} - {cliente['telefone']}")
    
        def emitir_cartao():
            selecao = cliente_listbox.curselection()
            if not selecao:
                messagebox.showwarning("Aviso", "Selecione um cliente!")
                return
    
            cliente_info = cliente_listbox.get(selecao[0])
            cliente_id = int(cliente_info.split(' - ')[0])
    
            cliente_window.destroy()
            self._criar_cartao_cliente(cliente_id)
    
        tk.Button(cliente_window, text="Emitir Cartão", command=emitir_cartao,
                 bg='#27ae60', fg='white').pack(pady=10)
    
    def _criar_cartao_cliente(self, cliente_id):
        """Cria novo cartão para cliente específico"""
        # Buscar dados do cliente
        self.cursor.execute("SELECT nome FROM clientes WHERE id = %s", (cliente_id,))
        cliente = self.cursor.fetchone()
    
        cartao_window = tk.Toplevel(self.root)
        cartao_window.title(f"Emitir Cartão - {cliente['nome']}")
        cartao_window.geometry("400x300")
        cartao_window.transient(self.root)
    
        tk.Label(cartao_window, text=f"Cliente: {cliente['nome']}", 
                font=('Arial', 12, 'bold')).pack(pady=10)
    
        # Gerar número do cartão (código de barras)
        numero_cartao = self._gerar_numero_cartao()
        
        tk.Label(cartao_window, text="Número do Cartão:").pack(pady=5)
        numero_var = tk.StringVar(value=numero_cartao)
        tk.Entry(cartao_window, textvariable=numero_var, width=20, font=('Arial', 12), 
                 state='readonly', justify='center').pack(pady=5)
    
        tk.Label(cartao_window, text="Senha (4 dígitos):").pack(pady=5)
        senha_var = tk.StringVar()
        tk.Entry(cartao_window, textvariable=senha_var, show='*', width=10, 
                 justify='center').pack(pady=5)
    
        tk.Label(cartao_window, text="Confirmar Senha:").pack(pady=5)
        confirmar_var = tk.StringVar()
        tk.Entry(cartao_window, textvariable=confirmar_var, show='*', width=10,
                 justify='center').pack(pady=5)
    
        tk.Label(cartao_window, text="Data de Validade:").pack(pady=5)
        validade_var = tk.StringVar(value=(datetime.now() + timedelta(days=365*2)).strftime('%d/%m/%Y'))
        tk.Entry(cartao_window, textvariable=validade_var, width=12).pack(pady=5)
    
        def salvar_cartao():
            if len(senha_var.get()) != 4 or not senha_var.get().isdigit():
                messagebox.showerror("Erro", "Senha deve ter 4 dígitos!")
                return
    
            if senha_var.get() != confirmar_var.get():
                messagebox.showerror("Erro", "Senhas não coincidem!")
                return
    
            try:
                data_validade = datetime.strptime(validade_var.get(), '%d/%m/%Y')
            except ValueError:
                messagebox.showerror("Erro", "Data de validade inválida!")
                return
    
            senha_hash = self.hash_senha(senha_var.get())
            
            try:
                self.cursor.execute('''
                    INSERT INTO cartoes_cliente (numero_cartao, cliente_id, senha_hash, data_validade)
                    VALUES (%s, %s, %s, %s)
                ''', (numero_cartao, cliente_id, senha_hash, data_validade))
                
                cartao_id = self.cursor.lastrowid
                
                self.registrar_auditoria('EMISSAO_CARTAO',
                                       f'Cartão emitido para {cliente["nome"]} - Nº: {numero_cartao}',
                                       'cartoes_cliente', cartao_id)
                
                messagebox.showinfo("Sucesso", 
                                  f"Cartão emitido com sucesso!\n\n"
                                  f"Número: {numero_cartao}\n"
                                  f"Senha: {senha_var.get()}\n\n"
                                  f"Guarde estas informações com segurança!")
                cartao_window.destroy()
    
            except mysql.connector.Error as e:
                messagebox.showerror("Erro", f"Erro ao emitir cartão: {e}")
    
        tk.Button(cartao_window, text="Emitir Cartão", command=salvar_cartao,
                 bg='#27ae60', fg='white').pack(pady=20)
    
    def _gerar_numero_cartao(self):
        """Gera número único para cartão cliente"""
        import random
        while True:
            # Gerar número no formato 1234567890123456
            numero = ''.join([str(random.randint(0, 9)) for _ in range(16)])
            
            # Verificar se já existe
            self.cursor.execute("SELECT COUNT(*) as count FROM cartoes_cliente WHERE numero_cartao = %s", (numero,))
            if self.cursor.fetchone()['count'] == 0:
                return numero
    
    def carregar_saldo_cartao(self):
        """Carrega saldo no cartão cliente usando display"""
        if not self.caixa_aberto:
            messagebox.showwarning("Aviso", "Caixa não está aberto!")
            return
    
        # Atualizar display
        self.display_var.set("Aguardando cartão...")
        self.op_var.set("Passe o cartão no scanner")
        self.root.update()
        
        numero_cartao = simpledialog.askstring("Carregar Saldo", "Número do cartão (scanner ou digitar):")
        if not numero_cartao:
            self.display_var.set("Operação cancelada")
            return
    
        # Atualizar display
        self.display_var.set(f"Cartão: {numero_cartao}")
        self.op_var.set("Verificando...")
        self.root.update()
    
        # Buscar cartão
        self.cursor.execute('''
            SELECT cc.id, cc.numero_cartao, c.nome as cliente_nome, cc.saldo, cc.ativo
            FROM cartoes_cliente cc
            JOIN clientes c ON cc.cliente_id = c.id
            WHERE cc.numero_cartao = %s
        ''', (numero_cartao,))
        
        cartao = self.cursor.fetchone()
        
        if not cartao:
            self.display_var.set("Cartão não encontrado!")
            self.op_var.set("Verifique o número")
            messagebox.showerror("Erro", "Cartão não encontrado!")
            return
    
        if not cartao['ativo']:
            self.display_var.set("Cartão inativo!")
            self.op_var.set("Contate o administrador")
            messagebox.showerror("Erro", "Cartão inativo!")
            return
    
        # Atualizar display com informações
        self.display_var.set(f"Cliente: {cartao['cliente_nome']}")
        self.op_var.set(f"Saldo atual: R$ {float(cartao['saldo']):.2f}")
        self.root.update()
        
        valor = simpledialog.askfloat("Carregar Saldo", 
                                     f"Cliente: {cartao['cliente_nome']}\n"
                                     f"Saldo Atual: R$ {float(cartao['saldo']):.2f}\n\n"
                                     f"Valor a carregar:",
                                     minvalue=0.01)
        
        if not valor:
            self.display_var.set("Carregamento cancelado")
            return
    
        # Verificar senha para segurança
        self.display_var.set("Verificando senha...")
        self.op_var.set("Aguardando autenticação")
        self.root.update()
        
        senha = simpledialog.askstring("Verificação", "Senha do cartão (4 dígitos):", show='*')
        if not senha:
            self.display_var.set("Autenticação cancelada")
            return
    
        if not self.verificar_senha_cartao(cartao['id'], senha):
            self.display_var.set("Senha incorreta!")
            self.op_var.set("Tente novamente")
            messagebox.showerror("Erro", "Senha incorreta!")
            return
    
        # Processar carregamento
        try:
            saldo_anterior = float(cartao['saldo'])
            saldo_posterior = saldo_anterior + valor
            
            # Atualizar display
            self.display_var.set("Processando...")
            self.op_var.set("Registrando transação")
            self.root.update()
            
            # Atualizar saldo
            self.cursor.execute('''
                UPDATE cartoes_cliente SET saldo = %s WHERE id = %s
            ''', (saldo_posterior, cartao['id']))
            
            # Registrar movimento
            self.cursor.execute('''
                INSERT INTO movimentos_cartao 
                (cartao_id, data_hora, tipo, descricao, valor, saldo_anterior, saldo_posterior, operador_id)
                VALUES (%s, %s, 'CARREGAMENTO', 'Carregamento via caixa', %s, %s, %s, %s)
            ''', (cartao['id'], datetime.now(), valor, saldo_anterior, saldo_posterior, self.operador_atual['id']))
            
            # Registrar movimento no caixa
            self.registrar_movimento_caixa('ENTRADA', f'CARREGAMENTO CARTÃO {numero_cartao}', valor, 'CARTAO_CLIENTE')
            
            self.conn.commit()
            
            # Atualizar display com sucesso
            self.display_var.set(f"Carregado: R$ {valor:.2f}")
            self.op_var.set(f"Novo saldo: R$ {saldo_posterior:.2f}")
            
            messagebox.showinfo("Sucesso", 
                              f"Carregamento realizado!\n\n"
                              f"Saldo Anterior: R$ {saldo_anterior:.2f}\n"
                              f"Valor Carregado: R$ {valor:.2f}\n"
                              f"Novo Saldo: R$ {saldo_posterior:.2f}")
            
            self.registrar_auditoria('CARREGAMENTO_CARTAO',
                                   f'Cartão {numero_cartao} - R$ {valor:.2f}',
                                   'cartoes_cliente', cartao['id'])
            
        except Exception as e:
            self.display_var.set("Erro no carregamento!")
            self.op_var.set("Tente novamente")
            messagebox.showerror("Erro", f"Erro ao carregar saldo: {e}")
    
    def verificar_senha_cartao(self, cartao_id, senha):
        """Verifica senha do cartão"""
        self.cursor.execute("SELECT senha_hash FROM cartoes_cliente WHERE id = %s", (cartao_id,))
        cartao = self.cursor.fetchone()
        
        if not cartao:
            return False
        
        return self.hash_senha(senha) == cartao['senha_hash']
    
    def consultar_saldo_cartao(self):
        """Consulta saldo do cartão cliente usando display"""
        # Atualizar display
        self.display_var.set("Aguardando cartão...")
        self.op_var.set("Passe o cartão no scanner")
        self.root.update()
        
        numero_cartao = simpledialog.askstring("Consultar Saldo", "Número do cartão:")
        if not numero_cartao:
            self.display_var.set("Consulta cancelada")
            return
    
        # Atualizar display
        self.display_var.set(f"Cartão: {numero_cartao}")
        self.op_var.set("Verificando...")
        self.root.update()
    
        # Buscar cartão
        self.cursor.execute('''
            SELECT cc.id, cc.numero_cartao, c.nome as cliente_nome, cc.saldo, cc.data_validade
            FROM cartoes_cliente cc
            JOIN clientes c ON cc.cliente_id = c.id
            WHERE cc.numero_cartao = %s AND cc.ativo = TRUE
        ''', (numero_cartao,))
        
        cartao = self.cursor.fetchone()
        
        if not cartao:
            self.display_var.set("Cartão não encontrado!")
            self.op_var.set("Verifique o número")
            messagebox.showerror("Erro", "Cartão não encontrado ou inativo!")
            return
    
        # Verificar senha
        self.display_var.set("Verificando senha...")
        self.op_var.set("Aguardando autenticação")
        self.root.update()
        
        senha = simpledialog.askstring("Verificação", "Senha do cartão (4 dígitos):", show='*')
        if not senha:
            self.display_var.set("Autenticação cancelada")
            return
    
        if not self.verificar_senha_cartao(cartao['id'], senha):
            self.display_var.set("Senha incorreta!")
            self.op_var.set("Tente novamente")
            messagebox.showerror("Erro", "Senha incorreta!")
            return
    
        # Registrar consulta
        self.cursor.execute('''
            INSERT INTO movimentos_cartao 
            (cartao_id, data_hora, tipo, descricao, valor, saldo_anterior, saldo_posterior)
            VALUES (%s, %s, 'CONSULTA', 'Consulta de saldo', 0, %s, %s)
        ''', (cartao['id'], datetime.now(), cartao['saldo'], cartao['saldo']))
        
        self.conn.commit()
    
        # Atualizar display com resultado
        self.display_var.set(f"Saldo: R$ {float(cartao['saldo']):.2f}")
        self.op_var.set(f"Cliente: {cartao['cliente_nome']}")
        
        messagebox.showinfo("Saldo do Cartão",
                           f"Cliente: {cartao['cliente_nome']}\n"
                           f"Número: {cartao['numero_cartao']}\n"
                           f"Saldo Disponível: R$ {float(cartao['saldo']):.2f}\n"
                           f"Validade: {cartao['data_validade'].strftime('%d/%m/%Y') if cartao['data_validade'] else 'Indeterminada'}")
    
    def processar_pagamento_cartao(self, numero_cartao, valor):
        """Processa pagamento com cartão cliente usando display"""
        if not numero_cartao:
            return False
    
        # Atualizar display
        self.display_var.set(f"Cartão: {numero_cartao}")
        self.op_var.set("Verificando cartão...")
        self.root.update()
    
        # Buscar cartão
        self.cursor.execute('''
            SELECT cc.id, cc.numero_cartao, c.nome as cliente_nome, cc.saldo, cc.ativo
            FROM cartoes_cliente cc
            JOIN clientes c ON cc.cliente_id = c.id
            WHERE cc.numero_cartao = %s
        ''', (numero_cartao,))
        
        cartao = self.cursor.fetchone()
        
        if not cartao:
            self.display_var.set("Cartão não encontrado!")
            self.op_var.set("Erro - cartão inválido")
            messagebox.showerror("Erro", "Cartão não encontrado!")
            return False
    
        if not cartao['ativo']:
            self.display_var.set("Cartão inativo!")
            self.op_var.set("Erro - cartão inativo")
            messagebox.showerror("Erro", "Cartão inativo!")
            return False
    
        saldo_atual = float(cartao['saldo'])
        
        # Atualizar display com informações do cartão
        self.display_var.set(f"Cliente: {cartao['cliente_nome']}")
        self.op_var.set(f"Saldo: R$ {saldo_atual:.2f} | Valor: R$ {valor:.2f}")
        self.root.update()
        
        if saldo_atual < valor:
            self.display_var.set("Saldo insuficiente!")
            self.op_var.set(f"Faltam: R$ {valor - saldo_atual:.2f}")
            messagebox.showerror("Erro", 
                               f"Saldo insuficiente!\n\n"
                               f"Saldo Disponível: R$ {saldo_atual:.2f}\n"
                               f"Valor da Compra: R$ {valor:.2f}\n"
                               f"Faltam: R$ {valor - saldo_atual:.2f}")
            return False
    
        # Verificar senha
        self.display_var.set("Aguardando senha...")
        self.op_var.set("Digite a senha do cartão")
        self.root.update()
        
        senha = simpledialog.askstring("Pagamento com Cartão", 
                                     f"Cliente: {cartao['cliente_nome']}\n"
                                     f"Valor: R$ {valor:.2f}\n\n"
                                     f"Digite a senha do cartão:",
                                     show='*')
        if not senha:
            self.display_var.set("Pagamento cancelado")
            self.op_var.set("Senha não fornecida")
            return False
    
        if not self.verificar_senha_cartao(cartao['id'], senha):
            self.display_var.set("Senha incorreta!")
            self.op_var.set("Pagamento recusado")
            messagebox.showerror("Erro", "Senha incorreta!")
            return False
    
        # Processar pagamento
        try:
            saldo_posterior = saldo_atual - valor
            
            # Atualizar display
            self.display_var.set("Processando pagamento...")
            self.op_var.set("Atualizando saldo...")
            self.root.update()
            
            # Atualizar saldo
            self.cursor.execute('''
                UPDATE cartoes_cliente SET saldo = %s WHERE id = %s
            ''', (saldo_posterior, cartao['id']))
            
            # Registrar movimento
            self.cursor.execute('''
                INSERT INTO movimentos_cartao 
                (cartao_id, data_hora, tipo, descricao, valor, saldo_anterior, saldo_posterior, operador_id)
                VALUES (%s, %s, 'PAGAMENTO', 'Pagamento de compra', %s, %s, %s, %s)
            ''', (cartao['id'], datetime.now(), valor, saldo_atual, saldo_posterior, self.operador_atual['id']))
            
            self.conn.commit()
            
            # Atualizar display com sucesso
            self.display_var.set(f"Pagamento realizado!")
            self.op_var.set(f"Saldo final: R$ {saldo_posterior:.2f}")
            
            messagebox.showinfo("Pagamento Realizado",
                              f"Pagamento com cartão realizado!\n\n"
                              f"Valor: R$ {valor:.2f}\n"
                              f"Saldo Anterior: R$ {saldo_atual:.2f}\n"
                              f"Saldo Posterior: R$ {saldo_posterior:.2f}")
            
            self.registrar_auditoria('PAGAMENTO_CARTAO',
                                   f'Cartão {numero_cartao} - R$ {valor:.2f}',
                                   'cartoes_cliente', cartao['id'])
            
            return True
            
        except Exception as e:
            self.display_var.set("Erro no pagamento!")
            self.op_var.set("Tente novamente")
            messagebox.showerror("Erro", f"Erro ao processar pagamento: {e}")
            return False
    
    def alterar_status_cartao(self):
        """Ativa/desativa cartão cliente"""
        numero_cartao = simpledialog.askstring("Alterar Status", "Número do cartão:")
        if not numero_cartao:
            return
    
        # Buscar cartão
        self.cursor.execute('''
            SELECT cc.id, cc.numero_cartao, c.nome as cliente_nome, cc.ativo
            FROM cartoes_cliente cc
            JOIN clientes c ON cc.cliente_id = c.id
            WHERE cc.numero_cartao = %s
        ''', (numero_cartao,))
        
        cartao = self.cursor.fetchone()
        
        if not cartao:
            messagebox.showerror("Erro", "Cartão não encontrado!")
            return
    
        novo_status = not cartao['ativo']
        status_text = "ativar" if novo_status else "desativar"
    
        if messagebox.askyesno("Confirmar", f"Deseja {status_text} o cartão de {cartao['cliente_nome']}?"):
            self.cursor.execute('UPDATE cartoes_cliente SET ativo = %s WHERE id = %s', 
                              (novo_status, cartao['id']))
            
            self.registrar_auditoria('ALTERACAO_STATUS_CARTAO',
                                   f'Status alterado para: {status_text} - Cartão: {numero_cartao}',
                                   'cartoes_cliente', cartao['id'])
            
            messagebox.showinfo("Sucesso", f"Cartão {status_text}do com sucesso!")
    
    def processar_pagamento_cartao_cliente(self):
        """Processa pagamento com cartão cliente"""
        total = self.calcular_total()
        
        # Atualizar display
        self.display_var.set("Aguardando cartão...")
        self.op_var.set("Passe o cartão no scanner")
        self.root.update()
        
        # Ler número do cartão via scanner ou entrada manual
        numero_cartao = simpledialog.askstring("Cartão Cliente", 
                                             f"Total: R$ {total:.2f}\n\n"
                                             f"Passe o cartão no scanner ou digite o número:")
        if not numero_cartao:
            self.display_var.set("Pagamento cancelado")
            return
    
        if self.processar_pagamento_cartao(numero_cartao, total):
            # Pagamento bem-sucedido - passar número do cartão para o recibo
            self.pagamentos = [{'forma': 'CARTÃO CLIENTE', 'valor': total, 'numero_cartao': numero_cartao}]
            self.finalizar_venda()
 
    def consultar_saldo_cartao_display(self):
        """Consulta saldo do cartão cliente usando display e scanner"""
        # Limpar display
        self.display_var.set("CONSULTA DE SALDO")
        self.display_secundario_var.set("Passe o cartão no scanner...")
        self.op_var.set("Aguardando leitura do cartão")
        self.op_secundario_var.set("Aguarde a leitura automática")
        self.root.update()
        
        # Configurar modo de consulta
        self.modo_consulta_saldo = True
        self.codigo_scanner = ""
        
        def verificar_scanner():
            # Verificar a cada 100ms se houve leitura do scanner
            if hasattr(self, 'codigo_scanner') and self.codigo_scanner and len(self.codigo_scanner) >= 3:
                numero_cartao = self.codigo_scanner.strip()
                self._limpar_modo_consulta()
                self._processar_consulta_saldo(numero_cartao)
            elif hasattr(self, 'modo_consulta_saldo') and self.modo_consulta_saldo:
                # Continuar verificando por até 10 segundos
                self.root.after(100, verificar_scanner)
        
        # Iniciar verificação
        verificar_scanner()
        
        # Timeout após 10 segundos
        def timeout_consulta():
            if hasattr(self, 'modo_consulta_saldo') and self.modo_consulta_saldo:
                self._limpar_modo_consulta()
                self.display_var.set("Tempo esgotado")
                self.display_secundario_var.set("Nenhum cartão detectado")
                self.root.after(2000, self._limpar_display_consulta)
        
        self.root.after(10000, timeout_consulta)
    
    def _processar_consulta_saldo(self, numero_cartao):
        """Processa a consulta de saldo após leitura do cartão"""
        if not numero_cartao or len(numero_cartao) < 3:
            self._limpar_display_consulta()
            return
            
        # Atualizar display
        self.display_var.set(f"Cartão: {numero_cartao}")
        self.display_secundario_var.set("Verificando...")
        self.op_var.set("Consultando saldo")
        self.op_secundario_var.set("Aguarde...")
        self.root.update()
    
        # Buscar cartão
        self.cursor.execute('''
            SELECT cc.id, cc.numero_cartao, c.nome as cliente_nome, cc.saldo, cc.data_validade
            FROM cartoes_cliente cc
            JOIN clientes c ON cc.cliente_id = c.id
            WHERE cc.numero_cartao = %s AND cc.ativo = TRUE
        ''', (numero_cartao,))
        
        cartao = self.cursor.fetchone()
        
        if not cartao:
            self.display_var.set("Cartão não encontrado!")
            self.display_secundario_var.set("Verifique o número")
            self.op_var.set("Consulta cancelada")
            self.op_secundario_var.set("Cartão inválido ou inativo")
            messagebox.showerror("Erro", "Cartão não encontrado ou inativo!")
            self.root.after(3000, self._limpar_display_consulta)
            return
    
        # Pedir senha - usar teclado externo
        self._solicitar_senha_externa(cartao)
    
    def _solicitar_senha_externa(self, cartao):
        """Solicita senha usando teclado externo"""
        self.display_var.set("Digite a senha")
        self.display_secundario_var.set("Use o teclado externo")
        self.op_var.set("Aguardando senha...")
        self.op_secundario_var.set("Digite 4 dígitos e pressione Enter")
        self.root.update()
        
        # Usar simpledialog para entrada externa
        senha = simpledialog.askstring("Senha do Cartão", 
                                     f"Cliente: {cartao['cliente_nome']}\n"
                                     f"Cartão: {cartao['numero_cartao']}\n\n"
                                     f"Digite a senha (4 dígitos):", 
                                     show='*')
        
        if not senha:
            self.display_var.set("Consulta cancelada")
            self.display_secundario_var.set("Senha não fornecida")
            self.root.after(2000, self._limpar_display_consulta)
            return
            
        if len(senha) != 4 or not senha.isdigit():
            self.display_var.set("Senha inválida!")
            self.display_secundario_var.set("Deve ter 4 dígitos")
            messagebox.showerror("Erro", "Senha deve ter exatamente 4 dígitos!")
            self.root.after(2000, self._limpar_display_consulta)
            return
            
        if not self.verificar_senha_cartao(cartao['id'], senha):
            self.display_var.set("Senha incorreta!")
            self.display_secundario_var.set("Tente novamente")
            messagebox.showerror("Erro", "Senha incorreta!")
            self.root.after(2000, self._limpar_display_consulta)
            return
            
        # Senha correta - finalizar consulta
        self._finalizar_consulta_saldo(cartao)
    
    def _limpar_modo_consulta(self):
        """Limpa o modo de consulta"""
        if hasattr(self, 'modo_consulta_saldo'):
            self.modo_consulta_saldo = False
        if hasattr(self, 'codigo_scanner'):
            self.codigo_scanner = ""
    
    def _iniciar_entrada_manual_cartao(self):
        """Inicia entrada manual do número do cartão"""
        self.display_var.set("Digite o número do cartão")
        self.display_secundario_var.set("Use o teclado numérico")
        self.op_var.set("Entrada manual do cartão")
        self.op_secundario_var.set("Digite os 16 dígitos e pressione Enter")
        self.root.update()
        
        # Usar o modo normal de entrada com uma flag especial
        self.entrada_especial = 'CARTAO_CONSULTA'
        self.display_text = ""

    def _solicitar_senha_consulta(self, cartao):
        """Solicita senha para consulta"""
        self.display_var.set("Digite a senha (4 dígitos)")
        self.display_secundario_var.set("Use o teclado numérico")
        self.op_var.set("Aguardando senha...")
        self.op_secundario_var.set("Digite 4 dígitos e pressione Enter")
        self.root.update()
        
        # Usar modo normal com flag de senha
        self.entrada_especial = 'SENHA_CONSULTA'
        self.cartao_consulta = cartao
        self.display_text = ""
        self.display_var.set("Senha: ____")
        self.display_secundario_var.set("Digite 4 dígitos")
    
    def _verificar_senha_consulta(self, senha):
        """Verifica senha da consulta"""
        if not hasattr(self, 'cartao_consulta'):
            return False
            
        if len(senha) != 4 or not senha.isdigit():
            self.display_var.set("Senha inválida!")
            self.display_secundario_var.set("Deve ter 4 dígitos")
            self.root.after(2000, self._limpar_display_consulta)
            return False
            
        cartao = self.cartao_consulta
        
        if not self.verificar_senha_cartao(cartao['id'], senha):
            self.display_var.set("Senha incorreta!")
            self.display_secundario_var.set("Tente novamente")
            self.op_var.set("Consulta recusada")
            self.op_secundario_var.set("Autenticação falhou")
            messagebox.showerror("Erro", "Senha incorreta!")
            self.root.after(3000, self._limpar_display_consulta)
            return False
            
        return True
    
    def _finalizar_consulta_saldo(self, cartao):
        """Finaliza a consulta de saldo com sucesso"""
        # Registrar consulta
        self.cursor.execute('''
            INSERT INTO movimentos_cartao 
            (cartao_id, data_hora, tipo, descricao, valor, saldo_anterior, saldo_posterior)
            VALUES (%s, %s, 'CONSULTA', 'Consulta de saldo', 0, %s, %s)
        ''', (cartao['id'], datetime.now(), cartao['saldo'], cartao['saldo']))
        
        self.conn.commit()
    
        # Mostrar resultado no display
        saldo_formatado = f"R$ {float(cartao['saldo']):.2f}"
        self.display_var.set(f"Saldo: {saldo_formatado}")
        self.display_secundario_var.set(f"Cliente: {cartao['cliente_nome']}")
        self.op_var.set("Consulta realizada")
        self.op_secundario_var.set("Imprimindo recibo...")
        self.root.update()
    
        # CORREÇÃO: Chamar sem parâmetro senha
        self._gerar_recibo_consulta_saldo(cartao)
        
        messagebox.showinfo("Saldo do Cartão",
                           f"Cliente: {cartao['cliente_nome']}\n"
                           f"Número: {cartao['numero_cartao']}\n"
                           f"Saldo Disponível: {saldo_formatado}\n"
                           f"Validade: {cartao['data_validade'].strftime('%d/%m/%Y') if cartao['data_validade'] else 'Indeterminada'}")
        
        # Limpar após sucesso
        self.root.after(5000, self._limpar_display_consulta)
    
    def _gerar_recibo_consulta_saldo(self, cartao):  # REMOVIDO parâmetro senha
        """Gera recibo de consulta de saldo do cartão"""
        try:
            empresa_nome = self.config_manager.get('SISTEMA', 'empresa_nome')
            empresa_endereco = self.config_manager.get('SISTEMA', 'empresa_endereco')
            empresa_telefone = self.config_manager.get('SISTEMA', 'empresa_telefone')
            
            recibo = f"""
    {empresa_nome}
    {empresa_endereco}
    {empresa_telefone}
    {'='*42}
    {'CONSULTA DE SALDO - CARTÃO CLIENTE'.center(42)}
    {'='*42}
    
    Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    Operador: {self.operador_atual['nome'] if self.operador_atual else 'N/A'}
    
    CLIENTE: {cartao['cliente_nome']}
    CARTÃO: {cartao['numero_cartao']}
    VALIDADE: {cartao['data_validade'].strftime('%d/%m/%Y') if cartao['data_validade'] else 'INDETERMINADA'}
    
    {'='*42}
    SALDO DISPONÍVEL: R$ {float(cartao['saldo']):>10.2f}
    {'='*42}
    
    Este comprovante não tem valor fiscal
    Consulta realizada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    
    {self.config_manager.get('RECIBO', 'mensagem_rodape').center(42)}
    """
            
            # Mostrar recibo
            self.mostrar_recibo_consulta_saldo(recibo, cartao['numero_cartao'])
            
            # Imprimir automaticamente
            if self.config_manager.get('RECIBO', 'imprimir_automaticamente', bool):
                try:
                    self.impressao.imprimir_recibo(recibo, f"CONSULTA_{cartao['numero_cartao']}")
                except Exception as e:
                    print(f"Erro na impressão: {e}")
                    
        except Exception as e:
            print(f"Erro ao gerar recibo de consulta: {e}")
    
    def _limpar_display_consulta(self):
        """Limpa o display após consulta"""
        self.display_var.set("Pronto para vender...")
        self.display_secundario_var.set("Aguardando operação...")
        self.op_var.set("Operação: Aguardando...")
        self.op_secundario_var.set("Use o teclado para entrada")
        
        # Limpar variáveis de modo especial
        if hasattr(self, 'entrada_especial'):
            del self.entrada_especial
        if hasattr(self, 'cartao_consulta'):
            del self.cartao_consulta
        if hasattr(self, 'modo_consulta_saldo'):
            del self.modo_consulta_saldo
            
        self.display_text = ""
    
    def _solicitar_senha_teclado(self):
        """Solicita senha usando o teclado numérico"""
        self.modo_senha = True
        self.senha_digitada = ""
        
        def finalizar_senha():
            senha = self.senha_digitada
            self.modo_senha = False
            self.senha_digitada = ""
            return senha
        
        # Configurar display para entrada de senha
        self.display_var.set("Senha: ____")
        self.display_secundario_var.set("Digite 4 dígitos")
        self.op_var.set("Entrada de senha")
        self.op_secundario_var.set("Teclado ativo para senha")
        self.root.update()
        
        # Aguardar entrada da senha
        self.finalizar_senha_callback = finalizar_senha
        self.root.wait_variable(self.senha_digitada)  # Você precisará implementar essa lógica
        
        return finalizar_senha()
   
    
    def mostrar_recibo_consulta_saldo(self, recibo, numero_cartao):
        """Mostra o recibo de consulta de saldo"""
        recibo_window = tk.Toplevel(self.root)
        recibo_window.title(f"Comprovante - Cartão {numero_cartao}")
        recibo_window.geometry("500x400")
        recibo_window.transient(self.root)
        
        # Centralizar
        recibo_window.update_idletasks()
        width = 500
        height = 400
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        recibo_window.geometry(f'{width}x{height}+{x}+{y}')
        
        text_frame = tk.Frame(recibo_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, font=('Courier', 10), wrap=tk.WORD)
        text_widget.insert(tk.END, recibo)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = tk.Frame(recibo_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="Fechar", command=recibo_window.destroy,
                 bg='#3498db', fg='white').pack(side=tk.RIGHT, padx=5)
        
        if self.config_manager.get('RECIBO', 'imprimir_automaticamente', bool):
            tk.Button(btn_frame, text="Reimprimir", command=lambda: self.impressao.imprimir_recibo(recibo, f"CONSULTA_{numero_cartao}"),
                     bg='#27ae60', fg='white').pack(side=tk.RIGHT, padx=5)
        
    # nova class configuconf ini    
    
    def criar_menu(self):
        """Cria o menu principal"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu Arquivo
        menu_arquivo = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arquivo", menu=menu_arquivo)
        menu_arquivo.add_command(label="Nova Venda", command=self.nova_venda)
        menu_arquivo.add_separator()
        
        # Submenu Caixa
        submenu_caixa = tk.Menu(menu_arquivo, tearoff=0)
        submenu_caixa.add_command(label="Abrir Caixa", command=self.abrir_caixa)
        submenu_caixa.add_command(label="Fechar Caixa", command=self.fechar_caixa)
        submenu_caixa.add_separator()
        submenu_caixa.add_command(label="Movimento de Caixa", command=self.movimento_caixa)
        submenu_caixa.add_command(label="Consulta Caixa", command=self.consulta_caixa)
        menu_arquivo.add_cascade(label="Caixa", menu=submenu_caixa)
        
        # Menu Configurações
        menu_config = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configurações", menu=menu_config)
        menu_config.add_command(label="Configurações Avançadas", 
                              command=self.mostrar_configuracoes_avancadas)
        menu_config.add_command(label="Backup de Dados", 
                              command=self.backup_dados)
        menu_config.add_separator()
        menu_config.add_command(label="Sair", command=self.root.quit)
        
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Backup", command=self.backup_dados)
        menu_arquivo.add_command(label="Configurações", command=self.mostrar_configuracoes)
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Sair", command=self.root.quit)
        
        # Menu Vendas
        menu_vendas = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Vendas", menu=menu_vendas)
        menu_vendas.add_command(label="Nova Venda", command=self.nova_venda)
        menu_vendas.add_command(label="Cancelar Venda", command=self.cancelar_venda)
        menu_vendas.add_separator()
        menu_vendas.add_command(label="Consultar Vendas", command=self.consultar_vendas)
        menu_vendas.add_command(label="Histórico de Vendas", command=self.historico_vendas)
        
        # Menu Produtos
        menu_produtos = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Produtos", menu=menu_produtos)
        menu_produtos.add_command(label="Gerenciar Produtos", command=self.gerenciar_produtos)
        menu_produtos.add_command(label="Consultar Estoque", command=self.consultar_estoque)
        menu_produtos.add_command(label="Produtos em Falta", command=self.produtos_em_falta)
        menu_produtos.add_separator()
        menu_produtos.add_command(label="Categorias", command=self.relatorio_promocoes)
        
         # Menu Pomocao
        menu_promo = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Promoçao", menu=menu_promo)
        menu_promo.add_command(label="Gerenciar promo", command=self.gerenciar_produtos)
            # Menu Impressão
        menu_impressao = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Impressão", menu=menu_impressao)
        menu_impressao.add_command(label="Configurar Impressora", 
                                  command=self.impressao.mostrar_config_impressao)
        menu_impressao.add_command(label="Testar Impressão", 
                                  command=lambda: self.impressao.imprimir_texto("*** TESTE ***\nSistema OK!\n\n"))
        menu_impressao.add_separator()
        menu_impressao.add_command(label="Listar Impressoras", 
                              command=self.listar_impressoras)
                              
         # Menu Cartões Cliente
        menu_cartoes = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Cartões Cliente", menu=menu_cartoes)
        menu_cartoes.add_command(label="Gestão de Cartões", command=self.gerenciar_cartoes_cliente)
        menu_cartoes.add_command(label="Carregar Saldo", command=self.carregar_saldo_cartao)
        menu_cartoes.add_command(label="Consultar Saldo", command=self.consultar_saldo_cartao)
        
        # Menu Clientes
        menu_clientes = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Clientes", menu=menu_clientes)
        menu_clientes.add_command(label="Gerenciar Clientes", command=self.gerenciar_clientes)
        menu_clientes.add_command(label="Gerenciar Clientes_Comp", command=self.gerenciar_clientes_completo)
        menu_clientes.add_command(label="Adicionar Cliente", command=self.adicionar_cliente)
        
        # Menu Relatórios
        menu_relatorios = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Relatórios", menu=menu_relatorios)
        menu_relatorios.add_command(label="Dashboard", command=self.mostrar_dashboard)
        menu_relatorios.add_command(label="Vendas por Período", command=self.relatorio_vendas_periodo)
        menu_relatorios.add_command(label="Produtos Mais Vendidos", command=self.relatorio_produtos_mais_vendidos)
        menu_relatorios.add_command(label="Desempenho Operadores", command=self.relatorio_desempenho_operadores)
        
        # Menu Administração (apenas para supervisores/admins)
        if hasattr(self, 'operador_atual') and self.operador_atual and self.operador_atual['nivel_acesso'] in ['SUPERVISOR', 'ADMIN']:
            menu_admin = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Administração", menu=menu_admin)
            menu_admin.add_command(label="Módulo Administrativo", command=self.mostrar_modulo_administracao)
            menu_admin.add_separator()
            menu_admin.add_command(label="Gestão de Usuários", command=self.mostrar_gestao_usuarios)
            menu_admin.add_command(label="Auditoria do Sistema", command=self.mostrar_auditoria)
            menu_admin.add_command(label="Configurações do Sistema", command=self.mostrar_configuracoes_sistema)
        
        # Menu Ajuda
        menu_ajuda = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ajuda", menu=menu_ajuda)
        menu_ajuda.add_command(label="Sobre", command=self.mostrar_sobre)
        menu_ajuda.add_command(label="Manual do Usuário", command=self.mostrar_manual)
        menu_ajuda.add_separator()
        menu_ajuda.add_command(label="Verificar Atualizações", command=self.verificar_atualizacoes)
    
    def listar_impressoras(self):
        """Lista impressoras disponíveis"""
        impressoras = self.impressao.detectar_impressoras()
        if impressoras:
            lista = "Impressoras disponíveis:\n\n" + "\n".join(impressoras)
            messagebox.showinfo("Impressoras", lista)
        else:
            messagebox.showinfo("Impressoras", "Nenhuma impressora local encontrada.")
    
    def atualizar_relogio(self):
        """Atualiza o relógio na interface - CORRIGIDO"""
        try:
            if hasattr(self, 'time_label') and self.time_label.winfo_exists():
                agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                self.time_label.config(text=agora)
                
                # Agendar próxima atualização apenas se a janela ainda existir
                if self.root.winfo_exists():
                    self.root.after(1000, self.atualizar_relogio)
        except tk.TclError:
            # A janela foi fechada, não fazer nada
            pass
        except Exception as e:
            print(f"Erro no relógio: {e}")
    
    def __del__(self):
        """Destrutor para limpar callbacks do relógio"""
        try:
            # Cancelar qualquer callback pendente do relógio
            if hasattr(self, '_relogio_id'):
                self.root.after_cancel(self._relogio_id)
        except:
            pass
    
    def atualizar_status_caixa(self):
        """Atualiza a barra de status do caixa"""
        if hasattr(self, 'status_caixa_label'):
            if self.caixa_aberto:
                status_text = "CAIXA ABERTO"
                cor = '#27ae60'
                
                # Calcular saldo atual
                try:
                    totais = self.calcular_totais_caixa()
                    saldo_atual = self.saldo_inicial + totais['total_entradas'] - totais['total_saidas']
                    status_text = f"{status_text} | Saldo: R$ {saldo_atual:.2f}"
                except:
                    status_text = f"{status_text} | Saldo: R$ {self.saldo_inicial:.2f}"
                
                self.status_caixa_label.config(text=status_text, bg=cor, fg='white')
            else:
                status_text = "CAIXA FECHADO"
                cor = '#e74c3c'
                self.status_caixa_label.config(text=status_text, bg=cor, fg='white')
    
    def scroll_up(self):
        """Rola para cima na lista de produtos"""
        if hasattr(self, 'canvas'):
            self.canvas.yview_scroll(-1, "units")
    
    def scroll_down(self):
        """Rola para baixo na lista de produtos"""
        if hasattr(self, 'canvas'):
            self.canvas.yview_scroll(1, "units")
 
    def relatorio_produtos_mais_vendidos(self, data_inicio=None, data_fim=None):
        """Gera relatório de produtos mais vendidos"""
        if not data_inicio or not data_fim:
            # Se não foram fornecidas datas, pedir ao usuário
            periodo_window = tk.Toplevel(self.root)
            periodo_window.title("Produtos Mais Vendidos - Período")
            periodo_window.geometry("400x200")
            periodo_window.transient(self.root)
            
            tk.Label(periodo_window, text="Data Inicial (DD/MM/AAAA):").pack(pady=5)
            data_inicio_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y'))
            tk.Entry(periodo_window, textvariable=data_inicio_var, width=15).pack(pady=5)
            
            tk.Label(periodo_window, text="Data Final (DD/MM/AAAA):").pack(pady=5)
            data_fim_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
            tk.Entry(periodo_window, textvariable=data_fim_var, width=15).pack(pady=5)
            
            def gerar_com_datas():
                try:
                    data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                    data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')
                    periodo_window.destroy()
                    self.relatorio_produtos_mais_vendidos(data_inicio, data_fim)
                except ValueError:
                    messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")
            
            tk.Button(periodo_window, text="Gerar Relatório", command=gerar_com_datas,
                     bg='#3498db', fg='white').pack(pady=20)
            return
        
        # Gerar relatório
        try:
            self.cursor.execute('''
                SELECT p.nome, p.codigo, SUM(iv.quantidade) as total_vendido,
                       SUM(iv.subtotal) as total_receita
                FROM itens_venda iv
                JOIN produtos p ON iv.produto_id = p.id
                JOIN vendas v ON iv.venda_id = v.id
                WHERE v.data_hora BETWEEN %s AND %s 
                AND v.status = 'FINALIZADA'
                AND iv.cancelado = FALSE
                GROUP BY p.id, p.nome, p.codigo
                ORDER BY total_vendido DESC
                LIMIT 50
            ''', (data_inicio, data_fim))
            
            produtos = self.cursor.fetchall()
            
            relatorio_window = tk.Toplevel(self.root)
            relatorio_window.title(f"Produtos Mais Vendidos - {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
            relatorio_window.geometry("800x600")
            
            # Frame principal
            main_frame = tk.Frame(relatorio_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tk.Label(main_frame, text=f"PRODUTOS MAIS VENDIDOS\n{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", 
                    font=('Arial', 14, 'bold')).pack(pady=10)
            
            # Treeview
            tree_frame = tk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            columns = ('posicao', 'produto', 'codigo', 'quantidade', 'receita')
            tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
            
            tree.heading('posicao', text='#')
            tree.heading('produto', text='Produto')
            tree.heading('codigo', text='Código')
            tree.heading('quantidade', text='Qtd Vendida')
            tree.heading('receita', text='Total Receita')
            
            tree.column('posicao', width=50)
            tree.column('produto', width=300)
            tree.column('codigo', width=100)
            tree.column('quantidade', width=100)
            tree.column('receita', width=120)
            
            # Adicionar dados
            for i, produto in enumerate(produtos, 1):
                tree.insert('', tk.END, values=(
                    i,
                    produto['nome'],
                    produto['codigo'],
                    produto['total_vendido'],
                    f"R$ {produto['total_receita']:.2f}"
                ))
            
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Botões
            botoes_frame = tk.Frame(main_frame)
            botoes_frame.pack(fill=tk.X, pady=10)
            
            tk.Button(botoes_frame, text="Exportar CSV", 
                     command=lambda: self.exportar_relatorio_csv(produtos, 'produtos_mais_vendidos'),
                     bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
            
            tk.Button(botoes_frame, text="Fechar", command=relatorio_window.destroy,
                     bg='#e74c3c', fg='white').pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    
    def relatorio_desempenho_operadores(self, data_inicio=None, data_fim=None):
        """Gera relatório de desempenho dos operadores"""
        if not data_inicio or not data_fim:
            # Se não foram fornecidas datas, pedir ao usuário
            periodo_window = tk.Toplevel(self.root)
            periodo_window.title("Desempenho Operadores - Período")
            periodo_window.geometry("400x200")
            periodo_window.transient(self.root)
            
            tk.Label(periodo_window, text="Data Inicial (DD/MM/AAAA):").pack(pady=5)
            data_inicio_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y'))
            tk.Entry(periodo_window, textvariable=data_inicio_var, width=15).pack(pady=5)
            
            tk.Label(periodo_window, text="Data Final (DD/MM/AAAA):").pack(pady=5)
            data_fim_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
            tk.Entry(periodo_window, textvariable=data_fim_var, width=15).pack(pady=5)
            
            def gerar_com_datas():
                try:
                    data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                    data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')
                    periodo_window.destroy()
                    self.relatorio_desempenho_operadores(data_inicio, data_fim)
                except ValueError:
                    messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")
            
            tk.Button(periodo_window, text="Gerar Relatório", command=gerar_com_datas,
                     bg='#3498db', fg='white').pack(pady=20)
            return
        
        # Gerar relatório
        try:
            self.cursor.execute('''
                SELECT u.nome, u.numero_trabalhador,
                       COUNT(v.id) as total_vendas,
                       SUM(v.total) as total_valor,
                       AVG(v.total) as media_venda,
                       MIN(v.data_hora) as primeira_venda,
                       MAX(v.data_hora) as ultima_venda
                FROM vendas v
                JOIN usuarios u ON v.operador_id = u.id
                WHERE v.data_hora BETWEEN %s AND %s 
                AND v.status = 'FINALIZADA'
                GROUP BY u.id, u.nome, u.numero_trabalhador
                ORDER BY total_valor DESC
            ''', (data_inicio, data_fim))
            
            operadores = self.cursor.fetchall()
            
            relatorio_window = tk.Toplevel(self.root)
            relatorio_window.title(f"Desempenho Operadores - {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
            relatorio_window.geometry("900x600")
            
            # Frame principal
            main_frame = tk.Frame(relatorio_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tk.Label(main_frame, text=f"DESEMPENHO DOS OPERADORES\n{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", 
                    font=('Arial', 14, 'bold')).pack(pady=10)
            
            # Treeview
            tree_frame = tk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            columns = ('operador', 'numero', 'vendas', 'total', 'media', 'primeira', 'ultima')
            tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
            
            tree.heading('operador', text='Operador')
            tree.heading('numero', text='Nº Trab.')
            tree.heading('vendas', text='Nº Vendas')
            tree.heading('total', text='Total Vendido')
            tree.heading('media', text='Média/Venda')
            tree.heading('primeira', text='Primeira Venda')
            tree.heading('ultima', text='Última Venda')
            
            # Adicionar dados
            for operador in operadores:
                tree.insert('', tk.END, values=(
                    operador['nome'],
                    operador['numero_trabalhador'],
                    operador['total_vendas'],
                    f"R$ {operador['total_valor']:.2f}",
                    f"R$ {operador['media_venda']:.2f}",
                    operador['primeira_venda'].strftime('%d/%m/%Y') if operador['primeira_venda'] else '-',
                    operador['ultima_venda'].strftime('%d/%m/%Y') if operador['ultima_venda'] else '-'
                ))
            
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Botões
            botoes_frame = tk.Frame(main_frame)
            botoes_frame.pack(fill=tk.X, pady=10)
            
            tk.Button(botoes_frame, text="Exportar CSV", 
                     command=lambda: self.exportar_relatorio_csv(operadores, 'desempenho_operadores'),
                     bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
            
            tk.Button(botoes_frame, text="Fechar", command=relatorio_window.destroy,
                     bg='#e74c3c', fg='white').pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    
    def exportar_relatorio_csv(self, dados, nome_arquivo):
        """Exporta relatório para CSV"""
        try:
            filename = f"{nome_arquivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', encoding='utf-8') as f:
                if dados:
                    # Escrever cabeçalho
                    headers = list(dados[0].keys())
                    f.write(';'.join(headers) + '\n')
                    
                    # Escrever dados
                    for linha in dados:
                        valores = [str(linha[header]) for header in headers]
                        f.write(';'.join(valores) + '\n')
            
            messagebox.showinfo("Exportado", f"Relatório exportado como: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {e}")
    
    def gerenciar_produtos(self):
        """Interface para gerenciamento de produtos"""
        if not self.verificar_acesso_supervisor():
            return
        
        self.mostrar_modulo_administracao()
    
    def consultar_estoque(self):
        """Consulta de estoque"""
        estoque_window = tk.Toplevel(self.root)
        estoque_window.title("Consulta de Estoque")
        estoque_window.geometry("800x600")
        
        # Filtros
        filtros_frame = tk.Frame(estoque_window)
        filtros_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(filtros_frame, text="Buscar:").pack(side=tk.LEFT)
        busca_var = tk.StringVar()
        busca_entry = tk.Entry(filtros_frame, textvariable=busca_var, width=20)
        busca_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(filtros_frame, text="Status:").pack(side=tk.LEFT, padx=(20,5))
        status_var = tk.StringVar(value="Todos")
        status_combo = ttk.Combobox(filtros_frame, textvariable=status_var, 
                                   values=["Todos", "Normal", "Baixo", "Crítico"], 
                                   state="readonly", width=10)
        status_combo.pack(side=tk.LEFT, padx=5)
        
        def carregar_estoque():
            query = '''
                SELECT p.codigo, p.nome, c.nome as categoria, p.estoque, p.estoque_minimo, p.preco
                FROM produtos p 
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.ativo = TRUE
            '''
            params = []
            
            if busca_var.get():
                query += " AND (p.nome LIKE %s OR p.codigo LIKE %s)"
                params.extend([f'%{busca_var.get()}%', f'%{busca_var.get()}%'])
            
            query += " ORDER BY p.estoque ASC, p.nome"
            
            self.cursor.execute(query, params)
            produtos = self.cursor.fetchall()
            
            for item in tree.get_children():
                tree.delete(item)
            
            for produto in produtos:
                estoque = produto['estoque']
                minimo = produto['estoque_minimo']
                
                if estoque == 0:
                    status = "CRÍTICO"
                    cor = '#e74c3c'
                elif estoque <= minimo:
                    status = "BAIXO"
                    cor = '#f39c12'
                else:
                    status = "NORMAL"
                    cor = '#27ae60'
                
                # Aplicar filtro de status
                if status_var.get() != "Todos" and status_var.get() != status:
                    continue
                
                tree.insert('', tk.END, values=(
                    produto['codigo'],
                    produto['nome'],
                    produto['categoria'] or '-',
                    produto['estoque'],
                    produto['estoque_minimo'],
                    f"R$ {produto['preco']:.2f}",
                    status
                ), tags=(status,))
            
            # Configurar cores
            tree.tag_configure('CRÍTICO', background='#ffebee')
            tree.tag_configure('BAIXO', background='#fff3e0')
            tree.tag_configure('NORMAL', background='#e8f5e8')
        
        tk.Button(filtros_frame, text="Buscar", command=carregar_estoque,
                 bg='#3498db', fg='white').pack(side=tk.LEFT, padx=10)
        
        # Treeview
        tree_frame = tk.Frame(estoque_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('codigo', 'nome', 'categoria', 'estoque', 'minimo', 'preco', 'status')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree.heading('codigo', text='Código')
        tree.heading('nome', text='Produto')
        tree.heading('categoria', text='Categoria')
        tree.heading('estoque', text='Estoque')
        tree.heading('minimo', text='Mínimo')
        tree.heading('preco', text='Preço')
        tree.heading('status', text='Status')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        carregar_estoque()
    
    def produtos_em_falta(self):
        """Mostra produtos em falta ou com estoque baixo"""
        try:
            self.cursor.execute('''
                SELECT p.codigo, p.nome, c.nome as categoria, p.estoque, p.estoque_minimo
                FROM produtos p 
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.estoque <= p.estoque_minimo 
                AND p.ativo = TRUE
                ORDER BY p.estoque ASC, p.nome
            ''')
            
            produtos = self.cursor.fetchall()
            
            if not produtos:
                messagebox.showinfo("Estoque", "Nenhum produto em falta ou com estoque baixo!")
                return
            
            falta_window = tk.Toplevel(self.root)
            falta_window.title("Produtos com Estoque Baixo")
            falta_window.geometry("700x500")
            
            tk.Label(falta_window, text="PRODUTOS COM ESTOQUE BAIXO OU EM FALTA", 
                    font=('Arial', 14, 'bold')).pack(pady=10)
            
            tree_frame = tk.Frame(falta_window)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            columns = ('codigo', 'nome', 'categoria', 'estoque', 'minimo', 'status')
            tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
            
            tree.heading('codigo', text='Código')
            tree.heading('nome', text='Produto')
            tree.heading('categoria', text='Categoria')
            tree.heading('estoque', text='Estoque Atual')
            tree.heading('minimo', text='Estoque Mínimo')
            tree.heading('status', text='Status')
            
            for produto in produtos:
                estoque = produto['estoque']
                minimo = produto['estoque_minimo']
                
                if estoque == 0:
                    status = "EM FALTA"
                    cor = '#e74c3c'
                else:
                    status = "ESTOQUE BAIXO"
                    cor = '#f39c12'
                
                tree.insert('', tk.END, values=(
                    produto['codigo'],
                    produto['nome'],
                    produto['categoria'] or '-',
                    produto['estoque'],
                    produto['estoque_minimo'],
                    status
                ), tags=(status,))
            
            tree.tag_configure('EM FALTA', background='#ffebee')
            tree.tag_configure('ESTOQUE BAIXO', background='#fff3e0')
            
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Botão para imprimir lista de compras
            def imprimir_lista_compras():
                produtos_falta = [p for p in produtos if p['estoque'] == 0]
                if produtos_falta:
                    lista = "LISTA DE COMPRAS - PRODUTOS EM FALTA\n\n"
                    for produto in produtos_falta:
                        lista += f"□ {produto['nome']} (Cód: {produto['codigo']})\n"
                    
                    messagebox.showinfo("Lista de Compras", lista)
                else:
                    messagebox.showinfo("Lista de Compras", "Nenhum produto completamente em falta.")
            
            botoes_frame = tk.Frame(falta_window)
            botoes_frame.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Button(botoes_frame, text="📋 Lista de Compras", command=imprimir_lista_compras,
                     bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
            
            tk.Button(botoes_frame, text="Fechar", command=falta_window.destroy,
                     bg='#e74c3c', fg='white').pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar produtos: {e}")
    
    def gerenciar_clientes(self):
        """Interface para gerenciamento de clientes"""
        clientes_window = tk.Toplevel(self.root)
        clientes_window.title("Gestão de Clientes")
        clientes_window.geometry("800x600")
        
        # Controles
        controles_frame = tk.Frame(clientes_window)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(controles_frame, text="➕ Novo Cliente", 
                 command=self.adicionar_cliente, bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Label(controles_frame, text="Buscar:").pack(side=tk.LEFT, padx=(20,5))
        busca_var = tk.StringVar()
        busca_entry = tk.Entry(controles_frame, textvariable=busca_var, width=20)
        busca_entry.pack(side=tk.LEFT, padx=5)
        busca_entry.bind('<KeyRelease>', lambda e: self.carregar_clientes(tree, busca_var.get()))
        
        # Treeview
        tree_frame = tk.Frame(clientes_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('id', 'nome', 'telefone', 'email', 'data_cadastro')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree.heading('id', text='ID')
        tree.heading('nome', text='Nome')
        tree.heading('telefone', text='Telefone')
        tree.heading('email', text='Email')
        tree.heading('data_cadastro', text='Data Cadastro')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Carregar clientes
        self.carregar_clientes(tree)
        
        # Botão duplo-clique para editar
        def editar_cliente(event):
            selecao = tree.selection()
            if selecao:
                item = tree.item(selecao[0])
                cliente_id = item['values'][0]
                self.editar_cliente_detalhes(cliente_id, tree)
        
        tree.bind('<Double-1>', editar_cliente)
    
    def carregar_clientes(self, tree, busca=""):
        """Carrega clientes na treeview"""
        for item in tree.get_children():
            tree.delete(item)
        
        query = "SELECT * FROM clientes WHERE 1=1"
        params = []
        
        if busca:
            query += " AND (nome LIKE %s OR telefone LIKE %s OR email LIKE %s)"
            params.extend([f'%{busca}%', f'%{busca}%', f'%{busca}%'])
        
        query += " ORDER BY nome"
        
        self.cursor.execute(query, params)
        clientes = self.cursor.fetchall()
        
        for cliente in clientes:
            tree.insert('', tk.END, values=(
                cliente['id'],
                cliente['nome'],
                cliente['telefone'] or '-',
                cliente['email'] or '-',
                cliente['data_cadastro'].strftime('%d/%m/%Y') if cliente['data_cadastro'] else '-'
            ))
    
    def adicionar_cliente(self):
        """Adiciona novo cliente"""
        cliente_window = tk.Toplevel(self.root)
        cliente_window.title("Novo Cliente")
        cliente_window.geometry("400x300")
        cliente_window.transient(self.root)
        
        tk.Label(cliente_window, text="Nome:*").pack(pady=5)
        nome_var = tk.StringVar()
        tk.Entry(cliente_window, textvariable=nome_var, width=30).pack(pady=5)
        
        tk.Label(cliente_window, text="Telefone:").pack(pady=5)
        telefone_var = tk.StringVar()
        tk.Entry(cliente_window, textvariable=telefone_var, width=20).pack(pady=5)
        
        tk.Label(cliente_window, text="Email:").pack(pady=5)
        email_var = tk.StringVar()
        tk.Entry(cliente_window, textvariable=email_var, width=30).pack(pady=5)
        
        tk.Label(cliente_window, text="Endereço:").pack(pady=5)
        endereco_var = tk.StringVar()
        tk.Entry(cliente_window, textvariable=endereco_var, width=30).pack(pady=5)
        
        def salvar_cliente():
            if not nome_var.get().strip():
                messagebox.showerror("Erro", "Nome é obrigatório!")
                return
            
            try:
                self.cursor.execute('''
                    INSERT INTO clientes (nome, telefone, email, endereco, cadastrado_por)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (nome_var.get().strip(), telefone_var.get().strip(), 
                      email_var.get().strip(), endereco_var.get().strip(),
                      self.operador_atual['id']))
                
                self.registrar_auditoria('CADASTRO_CLIENTE',
                                       f'Novo cliente: {nome_var.get()}',
                                       'clientes', self.cursor.lastrowid)
                
                messagebox.showinfo("Sucesso", "Cliente cadastrado com sucesso!")
                cliente_window.destroy()
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao cadastrar cliente: {e}")
        
        tk.Button(cliente_window, text="Salvar", command=salvar_cliente,
                 bg='#27ae60', fg='white').pack(pady=20)
    
    def editar_cliente_detalhes(self, cliente_id, tree):
        """Edita detalhes do cliente"""
        self.cursor.execute("SELECT * FROM clientes WHERE id = %s", (cliente_id,))
        cliente = self.cursor.fetchone()
        
        if not cliente:
            return
        
        editar_window = tk.Toplevel(self.root)
        editar_window.title(f"Editar Cliente - {cliente['nome']}")
        editar_window.geometry("400x300")
        editar_window.transient(self.root)
        
        tk.Label(editar_window, text="Nome:*").pack(pady=5)
        nome_var = tk.StringVar(value=cliente['nome'])
        tk.Entry(editar_window, textvariable=nome_var, width=30).pack(pady=5)
        
        tk.Label(editar_window, text="Telefone:").pack(pady=5)
        telefone_var = tk.StringVar(value=cliente['telefone'] or '')
        tk.Entry(editar_window, textvariable=telefone_var, width=20).pack(pady=5)
        
        tk.Label(editar_window, text="Email:").pack(pady=5)
        email_var = tk.StringVar(value=cliente['email'] or '')
        tk.Entry(editar_window, textvariable=email_var, width=30).pack(pady=5)
        
        tk.Label(editar_window, text="Endereço:").pack(pady=5)
        endereco_var = tk.StringVar(value=cliente['endereco'] or '')
        tk.Entry(editar_window, textvariable=endereco_var, width=30).pack(pady=5)
        
        def salvar_edicao():
            if not nome_var.get().strip():
                messagebox.showerror("Erro", "Nome é obrigatório!")
                return
            
            try:
                self.cursor.execute('''
                    UPDATE clientes 
                    SET nome = %s, telefone = %s, email = %s, endereco = %s
                    WHERE id = %s
                ''', (nome_var.get().strip(), telefone_var.get().strip(), 
                      email_var.get().strip(), endereco_var.get().strip(),
                      cliente_id))
                
                self.registrar_auditoria('EDICAO_CLIENTE',
                                       f'Cliente editado: {cliente["nome"]}',
                                       'clientes', cliente_id)
                
                messagebox.showinfo("Sucesso", "Cliente atualizado com sucesso!")
                editar_window.destroy()
                self.carregar_clientes(tree)
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao atualizar cliente: {e}")
        
        tk.Button(editar_window, text="Salvar", command=salvar_edicao,
                 bg='#3498db', fg='white').pack(pady=20)
    
    def historico_vendas(self):
        """Mostra histórico completo de vendas"""
        self.consultar_vendas()
    
    def atualizar_info_operador(self):
        """Atualiza informações do operador na interface - ATUALIZADO"""
        if hasattr(self, 'operador_atual') and self.operador_atual:
            self.operador_var.set(f"Operador: {self.operador_atual['nome']}")
            self.atualizar_titulo_pdv()  # Atualizar título com PDV
            self.atualizar_interface_com_login()
        else:
            self.operador_var.set("Operador: Não logado")
            self.atualizar_interface_sem_login()
            self._garantir_botao_login_visivel()
    
    def atualizar_botao_administracao(self):
        """Atualiza a visibilidade do botão de administração"""
        # Esta função será chamada após o login para mostrar/ocultar o botão de admin
        if hasattr(self, 'admin_btn_frame'):
            # Se já existe um frame de admin, destruir e recriar se necessário
            self.admin_btn_frame.destroy()
        
        if self.operador_atual and self.operador_atual['nivel_acesso'] in ['SUPERVISOR', 'ADMIN']:
            # Criar frame para botão de administração
            self.admin_btn_frame = tk.Frame(self.root, bg='#2c3e50')
            self.admin_btn_frame.pack(fill=tk.X, pady=(0, 10))
            
            admin_btn = tk.Button(self.admin_btn_frame, text="⚙️ MÓDULO DE ADMINISTRAÇÃO", 
                                command=self.mostrar_modulo_administracao,
                                bg='#8e44ad', fg='white', font=('Arial', 12, 'bold'),
                                height=2, width=25)
            admin_btn.pack(pady=5)
        
    # Métodos auxiliares para o menu (a serem implementados)
    def mostrar_dashboard(self):
        """Mostra o dashboard do sistema"""
        self.mostrar_modulo_administracao()
    
    def mostrar_gestao_usuarios(self):
        """Mostra gestão de usuários"""
        if hasattr(self, 'mostrar_modulo_administracao'):
            self.mostrar_modulo_administracao()
    
    def mostrar_auditoria(self):
        """Mostra auditoria do sistema"""
        if hasattr(self, 'mostrar_modulo_administracao'):
            self.mostrar_modulo_administracao()
    
    def mostrar_configuracoes_sistema(self):
        """Mostra configurações do sistema"""
        self.mostrar_configuracoes()
    
    def mostrar_sobre(self):
        """Mostra informações sobre o sistema"""
        messagebox.showinfo("Sobre", "Sistema de Vendas Professional Plus\n\nVersão 2.0\nDesenvolvido com Python e MySQL\n\n© 2024 - Todos os direitos reservados")
    
    def mostrar_manual(self):
        """Mostra manual do usuário"""
        messagebox.showinfo("Manual", "Manual do usuário em desenvolvimento...")
    
    def verificar_atualizacoes(self):
        """Verifica atualizações do sistema"""
        messagebox.showinfo("Atualizações", "Sistema está atualizado!")
    
    def gerenciar_categorias(self):
        """Gerencia categorias de produtos"""
        messagebox.showinfo("Categorias", "Funcionalidade em desenvolvimento...")
    
    def carregar_botoes_produtos(self):
        """Carrega os botões de produtos no painel"""
        # Limpar container anterior
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Buscar produtos com filtros
        categoria = self.categoria_var.get()
        busca = self.busca_var.get()
        
        query = """
            SELECT p.codigo, p.nome, p.preco, p.estoque, c.nome as categoria_nome 
            FROM produtos p 
            LEFT JOIN categorias c ON p.categoria_id = c.id 
            WHERE p.ativo = TRUE
        """
        params = []
        
        if categoria != "Todos":
            query += " AND c.nome = %s"
            params.append(categoria)
        
        if busca:
            query += " AND (p.nome LIKE %s OR p.codigo LIKE %s)"
            params.extend([f'%{busca}%', f'%{busca}%'])
        
        query += " ORDER BY p.nome"
        
        try:
            self.cursor.execute(query, params)
            produtos = self.cursor.fetchall()
            
            # Criar botões em grid 4x4
            row, col = 0, 0
            for produto in produtos:
                codigo = produto['codigo']
                nome = produto['nome']
                preco = float(produto['preco'])  # Converter para float
                estoque = int(produto['estoque'])  # Converter para int
                categoria_nome = produto['categoria_nome'] or 'Sem Categoria'
                
                # Definir cor baseada no estoque
                if estoque > 10:
                    cor_estoque = '#27ae60'  # Verde - estoque bom
                    estoque_text = "✓"
                elif estoque > 0:
                    cor_estoque = '#f39c12'  # Laranja - estoque baixo
                    estoque_text = str(estoque)
                else:
                    cor_estoque = '#e74c3c'  # Vermelho - sem estoque
                    estoque_text = "X"
                
                btn_text = f"{nome}\nR$ {preco:.2f} [{estoque_text}]"
                btn = tk.Button(self.scrollable_frame, text=btn_text, font=('Arial', 8),
                               bg='#3498db', fg='white', height=3, width=18,
                               command=lambda c=codigo, n=nome: self.adicionar_produto(c, n))
                btn.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
                
                # Colorir borda baseada no estoque
                btn.configure(highlightbackground=cor_estoque, highlightthickness=2)
                
                col += 1
                if col >= 4:
                    col = 0
                    row += 1
            
            # Configurar grid
            for i in range(row + 1):
                self.scrollable_frame.rowconfigure(i, weight=1)
            for i in range(4):
                self.scrollable_frame.columnconfigure(i, weight=1)
                
            # Se não há produtos, mostrar mensagem
            if not produtos:
                label_vazio = tk.Label(self.scrollable_frame, text="Nenhum produto encontrado",
                                      font=('Arial', 12), bg='#34495e', fg='#bdc3c7')
                label_vazio.grid(row=0, column=0, columnspan=4, pady=20)
                
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            label_erro = tk.Label(self.scrollable_frame, text="Erro ao carregar produtos",
                                 font=('Arial', 12), bg='#34495e', fg='#e74c3c')
            label_erro.grid(row=0, column=0, columnspan=4, pady=20)
    
    def adicionar_produto(self, codigo, nome="", quantidade=1):
        """Adiciona produto à venda atual com agrupamento e promoções"""
        try:
            # Buscar produto no banco
            self.cursor.execute('''
                SELECT id, codigo, nome, preco, estoque 
                FROM produtos 
                WHERE (codigo = %s OR nome LIKE %s) AND ativo = TRUE
            ''', (codigo, f'%{codigo}%'))
            
            produto = self.cursor.fetchone()
            
            if not produto:
                self.display_var.set("Produto não encontrado!")
                return False
    
            # CORREÇÃO: Converter decimal.Decimal para float
            preco = float(produto['preco'])
            
            # Verificar estoque
            if produto['estoque'] < quantidade:
                self.display_var.set("Estoque insuficiente!")
                messagebox.showerror("Erro", f"Estoque insuficiente! Disponível: {produto['estoque']}")
                return False
    
            # VERIFICAR SE PRODUTO JÁ EXISTE NA VENDA PARA AGRUPAR
            produto_existente = None
            for item in self.venda_atual:
                if item['produto_id'] == produto['id']:
                    produto_existente = item
                    break
    
            if produto_existente:
                # ATUALIZAR QUANTIDADE DO PRODUTO EXISTENTE
                nova_quantidade = produto_existente['quantidade'] + quantidade
                produto_existente['quantidade'] = nova_quantidade
                produto_existente['subtotal'] = nova_quantidade * preco
                
                self.display_var.set(f"{produto['nome']} - Qtd: {nova_quantidade}")
                self.display_secundario_var.set(f"Atualizado: +{quantidade} uni")
            else:
                # ADICIONAR NOVO PRODUTO
                subtotal = preco * quantidade
                novo_item = {
                    'produto_id': produto['id'],
                    'codigo': produto['codigo'],
                    'nome': produto['nome'],
                    'preco': preco,
                    'quantidade': quantidade,
                    'subtotal': subtotal
                }
                self.venda_atual.append(novo_item)
                
                self.display_var.set(f"{produto['nome']} - Adicionado")
                self.display_secundario_var.set(f"Qtd: {quantidade} x R$ {preco:.2f}")
    
            # APLICAR PROMOÇÕES AUTOMATICAMENTE
            self.aplicar_promocoes_venda()
    
            self.atualizar_display()
            self.op_var.set("Produto adicionado com sucesso!")
            return True
    
        except Exception as e:
            print(f"Erro detalhado ao adicionar produto: {e}")
            messagebox.showerror("Erro", f"Erro ao adicionar produto: {e}")
            return False

    def filtrar_produtos(self, event=None):
        """Filtra produtos baseado nos critérios de busca"""
        self.carregar_botoes_produtos()
    
    def atualizar_display(self):
        """Atualiza o display da venda atual"""
        # Limpar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Adicionar itens agrupados
        for item in self.venda_atual:
            self.tree.insert('', tk.END, values=(
                f"{item['nome']}",
                f"{item['quantidade']}",
                f"R$ {item['preco']:.2f}",
                f"R$ {item['subtotal']:.2f}"
            ))
        
        # Calcular totais
        subtotal = sum(item['subtotal'] for item in self.venda_atual)
        total = subtotal - self.desconto_aplicado
        
        # Atualizar variáveis
        self.subtotal_var.set(f"Subtotal: R$ {subtotal:.2f}")
        self.desconto_var.set(f"Desconto: R$ {self.desconto_aplicado:.2f}")
        self.total_var.set(f"R$ {total:.2f}")
    
    def carregar_categorias_combo(self):
        """Carrega categorias no combobox"""
        try:
            self.cursor.execute("SELECT nome FROM categorias WHERE ativo = TRUE ORDER BY nome")
            categorias = [cat['nome'] for cat in self.cursor.fetchall()]
            
            # Atualizar combobox de categorias se existir
            if hasattr(self, 'categoria_combo'):
                self.categoria_combo['values'] = ["Todos"] + categorias
        except Exception as e:
            print(f"Erro ao carregar categorias: {e}")
        
# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================
   
    def mostrar_relatorios(self):
        """Mostra menu de relatórios"""
        relatorios_window = tk.Toplevel(self.root)
        relatorios_window.title("Relatórios do Sistema")
        relatorios_window.geometry("400x500")
        relatorios_window.transient(self.root)
        
        tk.Label(relatorios_window, text="RELATÓRIOS DISPONÍVEIS", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        relatorios = [
            ("📊 Dashboard Geral", self.mostrar_dashboard),
            ("💰 Vendas por Período", self.relatorio_vendas_periodo),
            ("📦 Produtos Mais Vendidos", self.relatorio_produtos_mais_vendidos),
            ("👥 Desempenho Operadores", self.relatorio_desempenho_operadores),
            ("📈 Vendas por Dia", lambda: self.relatorio_vendas_dia(datetime.now() - timedelta(days=30), datetime.now())),
            ("⚠️ Produtos em Falta", self.produtos_em_falta),
            ("📋 Estoque Completo", self.consultar_estoque)
        ]
        
        for texto, comando in relatorios:
            btn = tk.Button(relatorios_window, text=texto, font=('Arial', 10, 'bold'),
                           bg='#3498db', fg='white', height=2, width=25,
                           command=comando)
            btn.pack(pady=5)

    #novos metos avança inicio
    def mostrar_configuracoes_avancadas(self):
        """Mostra configurações avançadas do sistema"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configurações Avançadas")
        config_window.geometry("600x700")
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Centralizar
        config_window.update_idletasks()
        width = 600
        height = 700
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        config_window.geometry(f'{width}x{height}+{x}+{y}')
        
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba Empresa
        frame_empresa = self._criar_aba_empresa(notebook)
        notebook.add(frame_empresa, text="🏢 Empresa")
        
        # Aba Recibo
        frame_recibo = self._criar_aba_recibo(notebook)
        notebook.add(frame_recibo, text="🧾 Recibo")
        
        # Aba Impressão
        frame_impressao = self._criar_aba_impressao(notebook)
        notebook.add(frame_impressao, text="🖨️ Impressão")
        
        # Aba Banco de Dados
        frame_banco = self._criar_aba_banco(notebook)
        notebook.add(frame_banco, text="🗄️ Banco")
        
        # Aba Segurança
        frame_seguranca = self._criar_aba_seguranca(notebook)
        notebook.add(frame_seguranca, text="🔒 Segurança")
        
        def salvar_todas_configuracoes():
            self.config_manager.salvar_configuracoes()
            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
            config_window.destroy()
        
        tk.Button(config_window, text="💾 Salvar Todas as Configurações", 
                 command=salvar_todas_configuracoes, bg='#27ae60', fg='white',
                 font=('Arial', 12, 'bold')).pack(pady=10)
 
    def _criar_aba_empresa(self, notebook):
        """Cria aba de configurações da empresa"""
        frame = ttk.Frame(notebook)
        
        campos = [
            ("Nome da Empresa:", "SISTEMA", "empresa_nome"),
            ("Endereço:", "SISTEMA", "empresa_endereco"),
            ("Telefone:", "SISTEMA", "empresa_telefone"),
            ("CNPJ:", "SISTEMA", "empresa_cnpj"),
        ]
        
        for i, (label, secao, chave) in enumerate(campos):
            tk.Label(frame, text=label, font=('Arial', 10)).grid(row=i, column=0, sticky='w', pady=5, padx=5)
            var = tk.StringVar(value=self.config_manager.get(secao, chave))
            entry = tk.Entry(frame, textvariable=var, width=40)
            entry.grid(row=i, column=1, sticky='ew', pady=5, padx=5)
            # Salvar quando mudar
            var.trace('w', lambda *args, s=secao, c=chave, v=var: self.config_manager.set(s, c, v.get()))
        
        frame.columnconfigure(1, weight=1)
        return frame
    
    def _criar_aba_recibo(self, notebook):
        """Cria aba de configurações de recibo"""
        frame = ttk.Frame(notebook)
        
        opcoes = [
            ("Imprimir automaticamente", "RECIBO", "imprimir_automaticamente"),
            ("Cortar papel após impressão", "RECIBO", "cortar_papel"),
            ("Abrir gaveta de dinheiro", "RECIBO", "abrir_gaveta"),
            ("Mostrar CNPJ no recibo", "RECIBO", "mostrar_cnpj"),
        ]
        
        for i, (label, secao, chave) in enumerate(opcoes):
            var = tk.BooleanVar(value=self.config_manager.get(secao, chave, bool))
            cb = tk.Checkbutton(frame, text=label, variable=var, font=('Arial', 10))
            cb.grid(row=i, column=0, sticky='w', pady=5, padx=5)
            # Salvar quando mudar
            var.trace('w', lambda *args, s=secao, c=chave, v=var: self.config_manager.set(s, c, v.get()))
        
        # Número de cópias
        tk.Label(frame, text="Número de cópias:", font=('Arial', 10)).grid(row=len(opcoes), column=0, sticky='w', pady=5, padx=5)
        copias_var = tk.StringVar(value=str(self.config_manager.get("RECIBO", "numero_copias", int)))
        spin = tk.Spinbox(frame, from_=1, to=3, textvariable=copias_var, width=5)
        spin.grid(row=len(opcoes), column=1, sticky='w', pady=5, padx=5)
        copias_var.trace('w', lambda *args: self.config_manager.set("RECIBO", "numero_copias", copias_var.get()))
        
        return frame
    
    def _criar_aba_impressao(self, notebook):
        """Cria aba de configurações de impressão"""
        frame = ttk.Frame(notebook)
        
        # Esta aba será preenchida pelo sistema de impressão
        label = tk.Label(frame, text="Configurações de impressão disponíveis no menu Impressão", 
                        font=('Arial', 10), pady=20)
        label.pack()
        
        btn_config = tk.Button(frame, text="🖨️ Abrir Configurações de Impressão",
                              command=self.impressao.mostrar_config_impressao,
                              bg='#3498db', fg='white')
        btn_config.pack(pady=10)
        
        return frame

    def _criar_aba_banco(self, notebook):
        """Cria aba de configurações do banco de dados"""
        frame = ttk.Frame(notebook)
        
        campos = [
            ("Host:", "BANCO_DADOS", "host"),
            ("Usuário:", "BANCO_DADOS", "usuario"),
            ("Senha:", "BANCO_DADOS", "senha"),
            ("Database:", "BANCO_DADOS", "database"),
        ]
        
        for i, (label, secao, chave) in enumerate(campos):
            tk.Label(frame, text=label, font=('Arial', 10)).grid(row=i, column=0, sticky='w', pady=5, padx=5)
            var = tk.StringVar(value=self.config_manager.get(secao, chave))
            entry = tk.Entry(frame, textvariable=var, width=30, show='*' if 'senha' in chave else None)
            entry.grid(row=i, column=1, sticky='ew', pady=5, padx=5)
            var.trace('w', lambda *args, s=secao, c=chave, v=var: self.config_manager.set(s, c, v.get()))
        
        # Botão testar conexão
        def testar_conexao():
            try:
                # Testar conexão com novas configurações
                host = self.config_manager.get('BANCO_DADOS', 'host')
                user = self.config_manager.get('BANCO_DADOS', 'usuario')
                password = self.config_manager.get('BANCO_DADOS', 'senha')
                database = self.config_manager.get('BANCO_DADOS', 'database')
                
                temp_conn = mysql.connector.connect(
                    host=host, user=user, password=password, database=database
                )
                temp_conn.close()
                messagebox.showinfo("Conexão", "Conexão com MySQL bem-sucedida!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha na conexão: {e}")
        
        tk.Button(frame, text="🔗 Testar Conexão", command=testar_conexao,
                 bg='#27ae60', fg='white').grid(row=len(campos), column=0, columnspan=2, pady=10)
        
        frame.columnconfigure(1, weight=1)
        return frame
    
    def _criar_aba_seguranca(self, notebook):
        """Cria aba de configurações de segurança"""
        frame = ttk.Frame(notebook)
        
        opcoes = [
            ("Backup automático", "SEGURANCA", "backup_automatico"),
            ("Log de auditoria", "SEGURANCA", "log_auditoria"),
        ]
        
        for i, (label, secao, chave) in enumerate(opcoes):
            var = tk.BooleanVar(value=self.config_manager.get(secao, chave, bool))
            cb = tk.Checkbutton(frame, text=label, variable=var, font=('Arial', 10))
            cb.grid(row=i, column=0, sticky='w', pady=5, padx=5)
            var.trace('w', lambda *args, s=secao, c=chave, v=var: self.config_manager.set(s, c, v.get()))
        
        # Tamanho mínimo senha
        tk.Label(frame, text="Tamanho mínimo da senha:", font=('Arial', 10)).grid(row=len(opcoes), column=0, sticky='w', pady=5, padx=5)
        senha_var = tk.StringVar(value=str(self.config_manager.get("SEGURANCA", "tamanho_minimo_senha", int)))
        spin = tk.Spinbox(frame, from_=4, to=12, textvariable=senha_var, width=5)
        spin.grid(row=len(opcoes), column=1, sticky='w', pady=5, padx=5)
        senha_var.trace('w', lambda *args: self.config_manager.set("SEGURANCA", "tamanho_minimo_senha", senha_var.get()))
        
        return frame

    # 1. BACKUP AUTOMÁTICO
    def backup_automatico(self):
        """Faz backup automático dos dados"""
        try:
            backup_dir = "backup_automatico"
            os.makedirs(backup_dir, exist_ok=True)
            
            data = datetime.now().strftime('%Y%m%d_%H%M')
            backup_file = f"{backup_dir}/backup_{data}.sql"
            
            # Exportar dados importantes
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(f"-- Backup Automático - {datetime.now()}\n")
                
                tabelas = ['produtos', 'vendas', 'clientes', 'usuarios', 'caixa']
                for tabela in tabelas:
                    self.cursor.execute(f"SELECT * FROM {tabela}")
                    for linha in self.cursor.fetchall():
                        # Gerar INSERT statements
                        colunas = ', '.join(linha.keys())
                        valores = ', '.join([f"'{str(v).replace("'", "''")}'" if v is not None else 'NULL' 
                                           for v in linha.values()])
                        f.write(f"INSERT INTO {tabela} ({colunas}) VALUES ({valores});\n")
            
            # Manter apenas últimos 7 backups
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('backup_')])
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    os.remove(f"{backup_dir}/{old_backup}")
                    
            print(f"✅ Backup automático realizado: {backup_file}")
            
        except Exception as e:
            print(f"❌ Erro no backup automático: {e}")
            
    def criar_dashboard_tempo_real(self, parent):
        """Cria dashboard com atualização automática"""
        dashboard_frame = tk.Frame(parent, bg='#2c3e50')
        dashboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # Métricas em tempo real
        metricas_frame = tk.Frame(dashboard_frame, bg='#34495e')
        metricas_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.vendas_hoje_var = tk.StringVar(value="Carregando...")
        self.produtos_vendidos_var = tk.StringVar(value="Carregando...")
        self.valor_medio_var = tk.StringVar(value="Carregando...")
        
        tk.Label(metricas_frame, text="💰 Vendas Hoje:", 
                font=('Arial', 12), bg='#34495e', fg='white').grid(row=0, column=0, sticky='w')
        tk.Label(metricas_frame, textvariable=self.vendas_hoje_var,
                font=('Arial', 14, 'bold'), bg='#34495e', fg='#2ecc71').grid(row=0, column=1, sticky='w')
        
        tk.Label(metricas_frame, text="📦 Produtos Vendidos:", 
                font=('Arial', 12), bg='#34495e', fg='white').grid(row=1, column=0, sticky='w')
        tk.Label(metricas_frame, textvariable=self.produtos_vendidos_var,
                font=('Arial', 14, 'bold'), bg='#34495e', fg='#3498db').grid(row=1, column=1, sticky='w')
        
        # Atualizar métricas
        self.atualizar_metricas_tempo_real()
        
        # Programar atualização automática a cada 30 segundos
        def atualizar_periodicamente():
            self.atualizar_metricas_tempo_real()
            parent.after(30000, atualizar_periodicamente)  # 30 segundos
        
        atualizar_periodicamente()
    
    def atualizar_metricas_tempo_real(self):
        """Atualiza métricas do dashboard"""
        try:
            # Vendas hoje
            self.cursor.execute('''
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total 
                FROM vendas 
                WHERE DATE(data_hora) = CURDATE() 
                AND status = 'FINALIZADA'
            ''')
            vendas = self.cursor.fetchone()
            self.vendas_hoje_var.set(f"R$ {float(vendas['total']):.2f} ({vendas['count']} vendas)")
            
            # Produtos vendidos
            self.cursor.execute('''
                SELECT COALESCE(SUM(quantidade), 0) as total
                FROM itens_venda iv
                JOIN vendas v ON iv.venda_id = v.id
                WHERE DATE(v.data_hora) = CURDATE()
                AND v.status = 'FINALIZADA'
            ''')
            produtos = self.cursor.fetchone()
            self.produtos_vendidos_var.set(f"{produtos['total']} unidades")
            
        except Exception as e:
            print(f"Erro ao atualizar métricas: {e}")
    
    def verificar_notificacoes(self):
        """Verifica e mostra notificações importantes"""
        try:
            # Produtos com estoque baixo
            self.cursor.execute('''
                SELECT nome, estoque, estoque_minimo 
                FROM produtos 
                WHERE estoque <= estoque_minimo 
                AND ativo = TRUE
            ''')
            produtos_baixo = self.cursor.fetchall()
            
            if produtos_baixo:
                mensagem = "⚠️ Produtos com estoque baixo:\n"
                for produto in produtos_baixo:
                    mensagem += f"• {produto['nome']} ({produto['estoque']} unidades)\n"
                
                # Mostrar notificação
                self.mostrar_notificacao("Estoque Baixo", mensagem)
            
            # Promoções próximas do vencimento
            self.cursor.execute('''
                SELECT nome, data_fim 
                FROM promocoes 
                WHERE ativo = TRUE 
                AND data_fim BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 DAY)
            ''')
            promocoes = self.cursor.fetchall()
            
            if promocoes:
                mensagem = "🎯 Promoções terminando em breve:\n"
                for promocao in promocoes:
                    dias = (promocao['data_fim'] - datetime.now().date()).days
                    mensagem += f"• {promocao['nome']} ({dias} dias)\n"
                
                self.mostrar_notificacao("Promoções", mensagem)
                
        except Exception as e:
            print(f"Erro nas notificações: {e}")
    
    def mostrar_notificacao(self, titulo, mensagem):
        """Mostra notificação na interface"""
        # Implementar sistema de notificações toast
        pass
    
    def otimizar_consultas(self):
        """Otimiza consultas frequentes com cache"""
        self.cache_produtos = {}
        self.cache_ultima_atualizacao = None
        
    def buscar_produto_cache(self, codigo):
        """Busca produto com cache para melhor performance"""
        if codigo in self.cache_produtos:
            return self.cache_produtos[codigo]
        
        self.cursor.execute('SELECT * FROM produtos WHERE codigo = %s', (codigo,))
        produto = self.cursor.fetchone()
        
        if produto:
            self.cache_produtos[codigo] = produto
            return produto
        
        return None
    
    # 2. CONTROLE DE VALIDADE DE PRODUTOS
    def verificar_produtos_vencidos(self):
        """Verifica produtos próximos da validade"""
        try:
            self.cursor.execute('''
                SELECT nome, data_validade FROM produtos 
                WHERE data_validade IS NOT NULL 
                AND data_validade <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                AND ativo = TRUE
            ''')
            produtos = self.cursor.fetchall()
            
            if produtos:
                mensagem = "⚠️ PRODUTOS PRÓXIMOS DA VALIDADE:\n\n"
                for produto in produtos:
                    mensagem += f"• {produto['nome']} - Vence: {produto['data_validade']}\n"
                
                # Mostrar alerta apenas uma vez por dia
                ultimo_alerta = self.config_manager.get('ESTOQUE', 'ultimo_alerta_validade', str)
                hoje = datetime.now().strftime('%Y-%m-%d')
                
                if ultimo_alerta != hoje:
                    messagebox.showwarning("Alerta de Validade", mensagem)
                    self.config_manager.set('ESTOQUE', 'ultimo_alerta_validade', hoje)
                    
        except Exception as e:
            print(f"Erro ao verificar validade: {e}")
    
    # 3. RELATÓRIOS AVANÇADOS
    def relatorio_analise_vendas(self):
        """Relatório analítico de vendas"""
        try:
            self.cursor.execute('''
                SELECT 
                    DATE(data_hora) as data,
                    COUNT(*) as total_vendas,
                    SUM(total) as valor_total,
                    AVG(total) as ticket_medio,
                    HOUR(data_hora) as hora,
                    COUNT(DISTINCT operador_id) as operadores_ativos
                FROM vendas 
                WHERE status = 'FINALIZADA'
                AND data_hora >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(data_hora), HOUR(data_hora)
                ORDER BY data DESC, hora DESC
            ''')
            
            dados = self.cursor.fetchall()
            # Gerar relatório gráfico/analítico
            self._gerar_relatorio_analitico(dados)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    
    # 4. INTEGRAÇÃO COM BALANÇA
    class IntegracaoBalança:
        def __init__(self, sistema):
            self.sistema = sistema
            self.config = sistema.config_manager
        
        def ler_peso_balanca(self):
            """Lê peso da balança integrada"""
            try:
                tipo = self.config_manager.get('BALANCA', 'tipo', str)
                
                if tipo == 'serial':
                    return self._ler_balanca_serial()
                elif tipo == 'usb':
                    return self._ler_balanca_usb()
                else:
                    return None
                    
            except Exception as e:
                print(f"Erro ao ler balança: {e}")
                return None
        
        def _ler_balanca_serial(self):
            """Lê balança serial"""
            try:
                import serial
                porta = self.config_manager.get('BALANCA', 'porta', str)
                baudrate = self.config_manager.get('BALANCA', 'baudrate', int)
                
                with serial.Serial(porta, baudrate, timeout=2) as ser:
                    dados = ser.readline().decode().strip()
                    return float(dados) if dados else None
                    
            except:
                return None
    
    # 5. SISTEMA DE PROMOÇÕES
    def aplicar_promocao(self, produto_id, quantidade):
        """Aplica promoções automáticas"""
        try:
            self.cursor.execute('''
                SELECT * FROM promocoes 
                WHERE produto_id = %s 
                AND data_inicio <= NOW() 
                AND data_fim >= NOW()
                AND ativa = TRUE
            ''', (produto_id,))
            
            promocao = self.cursor.fetchone()
            
            if promocao:
                if promocao['tipo'] == 'DESCONTO_PERCENTUAL':
                    desconto = promocao['valor'] / 100
                    return desconto
                elif promocao['tipo'] == 'LEVE_MAIS_PAGUE_MENOS':
                    if quantidade >= promocao['quantidade_trigger']:
                        return promocao['valor_desconto']
            
            return 0
            
        except Exception as e:
            print(f"Erro ao aplicar promoção: {e}")
            return 0 
    #nome metodo promo ini
    def criar_aba_promocoes(self, parent):
        """Cria aba de gestão de promoções"""
        # Frame de controles
        controles_frame = tk.Frame(parent)
        controles_frame.pack(fill=tk.X, padx=10, pady=10)
    
        tk.Button(controles_frame, text="➕ Nova Promoção", 
                 command=self.criar_promocao, bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="✏️ Editar", 
                 command=self.editar_promocao, bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="🚫 Ativar/Desativar", 
                 command=self.alterar_status_promocao, bg='#e67e22', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(controles_frame, text="📊 Relatório", 
                 command=self.relatorio_promocoes, bg='#9b59b6', fg='white').pack(side=tk.LEFT, padx=5)
    
        # Treeview de promoções
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        columns = ('id', 'nome', 'tipo', 'valor', 'data_inicio', 'data_fim', 'produto', 'categoria', 'status')
        self.tree_promocoes = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        self.tree_promocoes.heading('id', text='ID')
        self.tree_promocoes.heading('nome', text='Nome')
        self.tree_promocoes.heading('tipo', text='Tipo')
        self.tree_promocoes.heading('valor', text='Valor')
        self.tree_promocoes.heading('data_inicio', text='Início')
        self.tree_promocoes.heading('data_fim', text='Fim')
        self.tree_promocoes.heading('produto', text='Produto')
        self.tree_promocoes.heading('categoria', text='Categoria')
        self.tree_promocoes.heading('status', text='Status')
    
        for col in columns:
            self.tree_promocoes.column(col, width=100)
    
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_promocoes.yview)
        self.tree_promocoes.configure(yscrollcommand=scrollbar.set)
    
        self.tree_promocoes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Carregar dados
        self.carregar_promocoes()
    
    def carregar_promocoes(self):
        """Carrega promoções na treeview"""
        for item in self.tree_promocoes.get_children():
            self.tree_promocoes.delete(item)
    
        try:
            self.cursor.execute('''
                SELECT p.id, p.nome, p.tipo, p.valor, p.data_inicio, p.data_fim, 
                       pr.nome as produto_nome, c.nome as categoria_nome, p.ativo
                FROM promocoes p
                LEFT JOIN produtos pr ON p.produto_alvo_id = pr.id
                LEFT JOIN categorias c ON p.categoria_alvo_id = c.id
                ORDER BY p.data_inicio DESC
            ''')
            
            for promocao in self.cursor.fetchall():
                # CORREÇÃO: Verificar se as datas não são None
                data_inicio = promocao['data_inicio'].strftime('%d/%m/%Y') if promocao['data_inicio'] else "N/A"
                data_fim = promocao['data_fim'].strftime('%d/%m/%Y') if promocao['data_fim'] else "N/A"
                status = "Ativa" if promocao['ativo'] else "Inativa"
                
                self.tree_promocoes.insert('', tk.END, values=(
                    promocao['id'],
                    promocao['nome'],
                    promocao['tipo'],
                    f"R$ {float(promocao['valor']):.2f}" if promocao['valor'] else "N/A",
                    data_inicio,
                    data_fim,
                    promocao['produto_nome'] or "N/A",
                    promocao['categoria_nome'] or "N/A",
                    status
                ))
        except Exception as e:
            print(f"Erro ao carregar promoções: {e}")
    
    def criar_promocao(self):
        """Cria nova promoção"""
        if not self.verificar_acesso_supervisor():
            return
    
        promocao_window = tk.Toplevel(self.root)
        promocao_window.title("Nova Promoção")
        promocao_window.geometry("500x600")
        promocao_window.transient(self.root)
        promocao_window.grab_set()
    
        tk.Label(promocao_window, text="Nome da Promoção:").pack(pady=5)
        nome_var = tk.StringVar()
        tk.Entry(promocao_window, textvariable=nome_var, width=40).pack(pady=5)
    
        tk.Label(promocao_window, text="Descrição:").pack(pady=5)
        descricao_var = tk.StringVar()
        tk.Entry(promocao_window, textvariable=descricao_var, width=40).pack(pady=5)
    
        tk.Label(promocao_window, text="Tipo de Promoção:").pack(pady=5)
        tipo_var = tk.StringVar(value="PERCENTUAL")
        tipo_combo = ttk.Combobox(promocao_window, textvariable=tipo_var,
                                 values=['PERCENTUAL', 'VALOR_FIXO', 'COMPRE_X_LEVE_Y', 'DESCONTO_POR_QUANTIDADE'],
                                 state='readonly')
        tipo_combo.pack(pady=5)
    
        tk.Label(promocao_window, text="Valor/Percentual:").pack(pady=5)
        valor_var = tk.StringVar()
        tk.Entry(promocao_window, textvariable=valor_var, width=20).pack(pady=5)
    
        # Campos específicos para cada tipo
        tk.Label(promocao_window, text="Quantidade X (Compre X Leve Y):").pack(pady=5)
        quantidade_x_var = tk.StringVar(value="1")
        tk.Entry(promocao_window, textvariable=quantidade_x_var, width=10).pack(pady=5)
    
        tk.Label(promocao_window, text="Quantidade Y (Compre X Leve Y):").pack(pady=5)
        quantidade_y_var = tk.StringVar(value="1")
        tk.Entry(promocao_window, textvariable=quantidade_y_var, width=10).pack(pady=5)
    
        tk.Label(promocao_window, text="Quantidade Mínima (Desconto por Qtde):").pack(pady=5)
        quantidade_minima_var = tk.StringVar(value="1")
        tk.Entry(promocao_window, textvariable=quantidade_minima_var, width=10).pack(pady=5)
    
        # Produto alvo
        tk.Label(promocao_window, text="Produto Alvo (opcional):").pack(pady=5)
        produto_var = tk.StringVar()
        
        self.cursor.execute("SELECT id, nome FROM produtos WHERE ativo = TRUE ORDER BY nome")
        produtos = [f"{p['id']} - {p['nome']}" for p in self.cursor.fetchall()]
        produto_combo = ttk.Combobox(promocao_window, textvariable=produto_var, values=produtos)
        produto_combo.pack(pady=5)
    
        # Categoria alvo
        tk.Label(promocao_window, text="Categoria Alvo (opcional):").pack(pady=5)
        categoria_var = tk.StringVar()
        
        self.cursor.execute("SELECT id, nome FROM categorias WHERE ativo = TRUE ORDER BY nome")
        categorias = [f"{c['id']} - {c['nome']}" for c in self.cursor.fetchall()]
        categoria_combo = ttk.Combobox(promocao_window, textvariable=categoria_var, values=categorias)
        categoria_combo.pack(pady=5)
    
        # Datas
        tk.Label(promocao_window, text="Data Início (DD/MM/AAAA):").pack(pady=5)
        data_inicio_var = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        tk.Entry(promocao_window, textvariable=data_inicio_var, width=12).pack(pady=5)
    
        tk.Label(promocao_window, text="Data Fim (DD/MM/AAAA):").pack(pady=5)
        data_fim_var = tk.StringVar(value=(datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y'))
        tk.Entry(promocao_window, textvariable=data_fim_var, width=12).pack(pady=5)
    
        def salvar_promocao():
            try:
                # Extrair IDs dos combos
                produto_id = produto_var.get().split(' - ')[0] if produto_var.get() and ' - ' in produto_var.get() else None
                categoria_id = categoria_var.get().split(' - ')[0] if categoria_var.get() and ' - ' in categoria_var.get() else None
    
                # Converter datas
                data_inicio = datetime.strptime(data_inicio_var.get(), '%d/%m/%Y')
                data_fim = datetime.strptime(data_fim_var.get(), '%d/%m/%Y')
    
                self.cursor.execute('''
                    INSERT INTO promocoes (nome, descricao, tipo, valor, produto_alvo_id, 
                                         categoria_alvo_id, data_inicio, data_fim, 
                                         quantidade_x, quantidade_y, quantidade_minima, criado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (nome_var.get(), descricao_var.get(), tipo_var.get(),
                      float(valor_var.get()) if valor_var.get() else None,
                      produto_id, categoria_id, data_inicio, data_fim,
                      int(quantidade_x_var.get()), int(quantidade_y_var.get()),
                      int(quantidade_minima_var.get()), self.operador_atual['id']))
    
                promocao_id = self.cursor.lastrowid
                self.registrar_auditoria('CRIACAO_PROMOCAO',
                                       f'Nova promoção: {nome_var.get()}',
                                       'promocoes', promocao_id)
    
                messagebox.showinfo("Sucesso", "Promoção criada com sucesso!")
                promocao_window.destroy()
                self.carregar_promocoes()
    
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar promoção: {e}")
    
        tk.Button(promocao_window, text="Salvar Promoção", command=salvar_promocao,
                 bg='#27ae60', fg='white').pack(pady=20)
    
    def aplicar_promocoes_venda(self):
        """Aplica promoções automaticamente na venda atual - VERSÃO CORRIGIDA"""
        if not self.venda_atual:
            return
    
        # Resetar descontos antes de aplicar novas promoções
        for item in self.venda_atual:
            # Restaurar preço original
            item['subtotal'] = item['preco'] * item['quantidade']
    
        self.desconto_aplicado = 0
        self.promocoes_aplicadas_venda = []
    
        # Buscar promoções ativas
        self.cursor.execute('''
            SELECT * FROM promocoes 
            WHERE ativo = TRUE 
            AND data_inicio <= CURDATE() 
            AND data_fim >= CURDATE()
            ORDER BY valor DESC  # Aplica promoções com maior valor primeiro
        ''')
        
        promocoes = self.cursor.fetchall()
        total_desconto = 0
    
        for promocao in promocoes:
            desconto_promocao = self._aplicar_promocao_individual(promocao)
            total_desconto += desconto_promocao
    
        if total_desconto > 0:
            self.desconto_aplicado = total_desconto
            self.atualizar_display()
            print(f"Promoções aplicadas: R$ {total_desconto:.2f}")
    
    def _aplicar_promocao_individual(self, promocao):
        """Aplica uma promoção individual à venda - VERSÃO CORRIGIDA"""
        desconto_total = 0
        
        try:
            if promocao['tipo'] == 'PERCENTUAL':
                desconto_total = self._aplicar_desconto_percentual(promocao)
            elif promocao['tipo'] == 'VALOR_FIXO':
                desconto_total = self._aplicar_desconto_valor_fixo(promocao)
            elif promocao['tipo'] == 'COMPRE_X_LEVE_Y':
                desconto_total = self._aplicar_compre_x_leve_y(promocao)
            elif promocao['tipo'] == 'DESCONTO_POR_QUANTIDADE':
                desconto_total = self._aplicar_desconto_quantidade(promocao)
        except Exception as e:
            print(f"Erro ao aplicar promoção {promocao['nome']}: {e}")
        
        return desconto_total
    
    def _aplicar_desconto_valor_fixo(self, promocao):
        """Aplica desconto de valor fixo"""
        desconto_total = 0
        valor_fixo = float(promocao['valor'])
        
        for item in self.venda_atual:
            if self._produto_se_aplica_promocao(item['produto_id'], promocao):
                # Aplica o desconto fixo por item
                desconto_item = min(valor_fixo * item['quantidade'], item['subtotal'])
                item['subtotal'] -= desconto_item
                desconto_total += desconto_item
                
                # Registrar promoção aplicada
                self._registrar_promocao_aplicada(promocao['id'], item['produto_id'], 
                                                item['quantidade'], desconto_item)
        
        return desconto_total
    
    def _aplicar_compre_x_leve_y(self, promocao):
        """Aplica promoção Compre X Leve Y"""
        desconto_total = 0
        quantidade_x = promocao['quantidade_x']
        quantidade_y = promocao['quantidade_y']
        
        for item in self.venda_atual:
            if self._produto_se_aplica_promocao(item['produto_id'], promocao):
                if item['quantidade'] >= quantidade_x:
                    # Calcula quantos conjuntos X+Y o cliente comprou
                    conjuntos = item['quantidade'] // (quantidade_x + quantidade_y)
                    # Cada conjunto Y é gratuito
                    itens_gratis = conjuntos * quantidade_y
                    desconto_item = itens_gratis * item['preco']
                    
                    if desconto_item > 0:
                        item['subtotal'] -= desconto_item
                        desconto_total += desconto_item
                        
                        # Registrar promoção aplicada
                        self._registrar_promocao_aplicada(promocao['id'], item['produto_id'], 
                                                        item['quantidade'], desconto_item)
        
        return desconto_total
    
    def _aplicar_desconto_quantidade(self, promocao):
        """Aplica desconto por quantidade"""
        desconto_total = 0
        quantidade_minima = promocao['quantidade_minima']
        percentual_desconto = float(promocao['valor']) / 100
        
        for item in self.venda_atual:
            if self._produto_se_aplica_promocao(item['produto_id'], promocao):
                if item['quantidade'] >= quantidade_minima:
                    desconto_item = item['subtotal'] * percentual_desconto
                    item['subtotal'] -= desconto_item
                    desconto_total += desconto_item
                    
                    # Registrar promoção aplicada
                    self._registrar_promocao_aplicada(promocao['id'], item['produto_id'], 
                                                    item['quantidade'], desconto_item)
        
        return desconto_total
    
    def _aplicar_desconto_percentual(self, promocao):
        """Aplica desconto percentual"""
        desconto_total = 0
        percentual = float(promocao['valor']) / 100
        
        for item in self.venda_atual:
            if self._produto_se_aplica_promocao(item['produto_id'], promocao):
                desconto_item = item['subtotal'] * percentual
                item['subtotal'] -= desconto_item
                desconto_total += desconto_item
                
                # Registrar promoção aplicada
                self._registrar_promocao_aplicada(promocao['id'], item['produto_id'], 
                                                item['quantidade'], desconto_item)
        
        return desconto_total
    
    def _produto_se_aplica_promocao(self, produto_id, promocao):
        """Verifica se o produto se aplica à promoção - VERSÃO MELHORADA"""
        # Se a promoção tem produto alvo específico
        if promocao['produto_alvo_id'] and produto_id == promocao['produto_alvo_id']:
            return True
        
        # Se a promoção tem categoria alvo
        if promocao['categoria_alvo_id']:
            self.cursor.execute('SELECT categoria_id FROM produtos WHERE id = %s', (produto_id,))
            produto = self.cursor.fetchone()
            if produto and produto['categoria_id'] == promocao['categoria_alvo_id']:
                return True
        
        # Se a promoção não tem alvo específico, aplica a todos os produtos
        if not promocao['produto_alvo_id'] and not promocao['categoria_alvo_id']:
            return True
        
        return False
    
    def _registrar_promocao_aplicada(self, promocao_id, produto_id, quantidade, valor_desconto):
        """Registra promoção aplicada (para relatórios) - VERSÃO CORRIGIDA"""
        if not hasattr(self, 'promocoes_aplicadas_venda'):
            self.promocoes_aplicadas_venda = []
        
        # Buscar nome da promoção para exibir no recibo
        self.cursor.execute('SELECT nome FROM promocoes WHERE id = %s', (promocao_id,))
        promocao = self.cursor.fetchone()
        promocao_nome = promocao['nome'] if promocao else f"Promoção #{promocao_id}"
        
        self.promocoes_aplicadas_venda.append({
            'promocao_id': promocao_id,
            'promocao_nome': promocao_nome,
            'produto_id': produto_id,
            'quantidade': quantidade,
            'valor_desconto': valor_desconto
        })
     
    def _atualizar_campos_promocao(self, tipo, parent_frame):
        """Atualiza campos dinâmicos conforme tipo de promoção"""
        # Limpar campos anteriores
        for widget in parent_frame.winfo_children():
            widget.pack_forget()
    
        if tipo == "PERCENTUAL":
            self.valor_label.config(text="Valor do Desconto (%):")
            self.valor_label.pack(anchor='w', pady=5)
            self.valor_entry.pack(anchor='w', pady=5)
            
        elif tipo == "VALOR_FIXO":
            self.valor_label.config(text="Valor do Desconto (R$):")
            self.valor_label.pack(anchor='w', pady=5)
            self.valor_entry.pack(anchor='w', pady=5)
            
        elif tipo == "COMPRE_X_LEVE_Y":
            self.quantidade_x_label.pack(anchor='w', pady=5)
            self.quantidade_x_entry.pack(anchor='w', pady=5)
            self.quantidade_y_label.pack(anchor='w', pady=5)
            self.quantidade_y_entry.pack(anchor='w', pady=5)
            
        elif tipo == "DESCONTO_POR_QUANTIDADE":
            self.valor_label.config(text="Valor do Desconto (%):")
            self.valor_label.pack(anchor='w', pady=5)
            self.valor_entry.pack(anchor='w', pady=5)
            self.quantidade_minima_label.pack(anchor='w', pady=5)
            self.quantidade_minima_entry.pack(anchor='w', pady=5)

    def aplicar_promocoes(self, produto_id, quantidade, preco_original):
        """Aplica promoções automaticamente no produto"""
        hoje = datetime.now().date()
        
        self.cursor.execute('''
            SELECT p.* 
            FROM promocoes p
            WHERE p.ativo = TRUE 
            AND p.data_inicio <= %s 
            AND p.data_fim >= %s
            AND (p.produto_alvo_id = %s 
                 OR p.categoria_alvo_id IN (SELECT categoria_id FROM produtos WHERE id = %s)
                 OR (p.produto_alvo_id IS NULL AND p.categoria_alvo_id IS NULL))
            ORDER BY p.valor DESC
        ''', (hoje, hoje, produto_id, produto_id))
        
        promocoes = self.cursor.fetchall()
        
        desconto_total = 0
        promocoes_aplicadas = []
        
        for promocao in promocoes:
            desconto = self._calcular_desconto_promocao(promocao, produto_id, quantidade, preco_original)
            if desconto > 0:
                desconto_total += desconto
                promocoes_aplicadas.append({
                    'promocao': promocao,
                    'desconto': desconto
                })
        
        return desconto_total, promocoes_aplicadas
    
    def _calcular_desconto_promocao(self, promocao, produto_id, quantidade, preco_original):
        """Calcula desconto baseado no tipo de promoção"""
        if promocao['tipo'] == 'PERCENTUAL':
            return preco_original * (promocao['valor'] / 100) * quantidade
            
        elif promocao['tipo'] == 'VALOR_FIXO':
            return promocao['valor'] * quantidade
            
        elif promocao['tipo'] == 'COMPRE_X_LEVE_Y':
            x = promocao['quantidade_x']
            y = promocao['quantidade_y']
            if quantidade >= x:
                # Calcular quantos conjuntos "compre X leve Y" cabem
                conjuntos = quantidade // x
                produtos_pagos = conjuntos * y
                produtos_gratis = (quantidade // x) * (x - y)
                return produtos_gratis * preco_original
                
        elif promocao['tipo'] == 'DESCONTO_POR_QUANTIDADE':
            if quantidade >= promocao['quantidade_minima']:
                return preco_original * (promocao['valor'] / 100) * quantidade
                
        return 0
            
    def adicionar_promocao_rapida(self):
        """Método rápido para adicionar promoções de teste"""
        # Exemplo de promoção percentual
        promocao_data = {
            'nome': 'Promoção Teste 15% OFF',
            'descricao': 'Desconto de teste de 15% em todos os produtos',
            'tipo': 'PERCENTUAL',
            'valor': 15.00,
            'produto_alvo_id': None,  # Aplicar a todos
            'categoria_alvo_id': None,  # Aplicar a todas
            'data_inicio': datetime.now().date(),
            'data_fim': (datetime.now() + timedelta(days=30)).date(),
            'ativo': True
        }
        
        try:
            self.cursor.execute('''
                INSERT INTO promocoes 
                (nome, descricao, tipo, valor, produto_alvo_id, categoria_alvo_id, 
                 data_inicio, data_fim, ativo, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                promocao_data['nome'],
                promocao_data['descricao'],
                promocao_data['tipo'],
                promocao_data['valor'],
                promocao_data['produto_alvo_id'],
                promocao_data['categoria_alvo_id'],
                promocao_data['data_inicio'],
                promocao_data['data_fim'],
                promocao_data['ativo'],
                self.operador_atual['id'] if self.operador_atual else 1
            ))
            
            self.conn.commit()
            messagebox.showinfo("Sucesso", "Promoção adicionada com sucesso!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar promoção: {e}")
           
        
    def _mostrar_formulario_promocao(self, promocao=None):
        """Mostra formulário para criar/editar promoção"""
        formulario_window = tk.Toplevel(self.root)
        formulario_window.title("Nova Promoção" if not promocao else "Editar Promoção")
        formulario_window.geometry("600x700")
        formulario_window.transient(self.root)
        formulario_window.grab_set()
    
        # Frame principal com scroll
        main_frame = tk.Frame(formulario_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
    
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
    
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # Variáveis do formulário
        nome_var = tk.StringVar(value=promocao['nome'] if promocao else "")
        descricao_var = tk.StringVar(value=promocao['descricao'] if promocao else "")
        tipo_var = tk.StringVar(value=promocao['tipo'] if promocao else "PERCENTUAL")
        valor_var = tk.StringVar(value=str(promocao['valor']) if promocao and promocao['valor'] else "")
        produto_var = tk.StringVar()
        categoria_var = tk.StringVar()
        inicio_var = tk.StringVar(value=promocao['data_inicio'].strftime('%d/%m/%Y') if promocao else datetime.now().strftime('%d/%m/%Y'))
        fim_var = tk.StringVar(value=promocao['data_fim'].strftime('%d/%m/%Y') if promocao else (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y'))
        quantidade_x_var = tk.StringVar(value=str(promocao['quantidade_x']) if promocao and promocao['quantidade_x'] else "1")
        quantidade_y_var = tk.StringVar(value=str(promocao['quantidade_y']) if promocao and promocao['quantidade_y'] else "1")
        quantidade_minima_var = tk.StringVar(value=str(promocao['quantidade_minima']) if promocao and promocao['quantidade_minima'] else "1")
    
        # Campos do formulário
        tk.Label(scrollable_frame, text="Dados da Promoção", font=('Arial', 14, 'bold')).pack(pady=10)
    
        # Nome
        tk.Label(scrollable_frame, text="Nome da Promoção:*").pack(anchor='w', pady=5)
        tk.Entry(scrollable_frame, textvariable=nome_var, width=50).pack(fill=tk.X, pady=5)
    
        # Descrição
        tk.Label(scrollable_frame, text="Descrição:").pack(anchor='w', pady=5)
        descricao_entry = tk.Text(scrollable_frame, height=3, width=50)
        descricao_entry.pack(fill=tk.X, pady=5)
        if promocao and promocao['descricao']:
            descricao_entry.insert('1.0', promocao['descricao'])
    
        # Tipo de promoção
        tk.Label(scrollable_frame, text="Tipo de Promoção:*").pack(anchor='w', pady=10)
        tipo_frame = tk.Frame(scrollable_frame)
        tipo_frame.pack(fill=tk.X, pady=5)
    
        tipos = [
            ("Percentual de Desconto", "PERCENTUAL"),
            ("Valor Fixo de Desconto", "VALOR_FIXO"),
            ("Compre X Leve Y", "COMPRE_X_LEVE_Y"),
            ("Desconto por Quantidade", "DESCONTO_POR_QUANTIDADE")
        ]
    
        for texto, valor in tipos:
            tk.Radiobutton(tipo_frame, text=texto, variable=tipo_var, value=valor).pack(anchor='w')
    
        # Frame para campos dinâmicos
        campos_dinamicos_frame = tk.Frame(scrollable_frame)
        campos_dinamicos_frame.pack(fill=tk.X, pady=10)
    
        def atualizar_campos_dinamicos():
            # Limpar campos anteriores
            for widget in campos_dinamicos_frame.winfo_children():
                widget.destroy()
    
            tipo = tipo_var.get()
            
            if tipo == "PERCENTUAL":
                tk.Label(campos_dinamicos_frame, text="Percentual de Desconto (%):*").pack(anchor='w', pady=5)
                tk.Entry(campos_dinamicos_frame, textvariable=valor_var, width=20).pack(anchor='w', pady=5)
                
            elif tipo == "VALOR_FIXO":
                tk.Label(campos_dinamicos_frame, text="Valor do Desconto (R$):*").pack(anchor='w', pady=5)
                tk.Entry(campos_dinamicos_frame, textvariable=valor_var, width=20).pack(anchor='w', pady=5)
                
            elif tipo == "COMPRE_X_LEVE_Y":
                tk.Label(campos_dinamicos_frame, text="Compre (X):*").pack(anchor='w', pady=5)
                tk.Entry(campos_dinamicos_frame, textvariable=quantidade_x_var, width=10).pack(anchor='w', pady=5)
                tk.Label(campos_dinamicos_frame, text="Leve (Y):*").pack(anchor='w', pady=5)
                tk.Entry(campos_dinamicos_frame, textvariable=quantidade_y_var, width=10).pack(anchor='w', pady=5)
                
            elif tipo == "DESCONTO_POR_QUANTIDADE":
                tk.Label(campos_dinamicos_frame, text="Percentual de Desconto (%):*").pack(anchor='w', pady=5)
                tk.Entry(campos_dinamicos_frame, textvariable=valor_var, width=20).pack(anchor='w', pady=5)
                tk.Label(campos_dinamicos_frame, text="Quantidade Mínima:*").pack(anchor='w', pady=5)
                tk.Entry(campos_dinamicos_frame, textvariable=quantidade_minima_var, width=10).pack(anchor='w', pady=5)
    
        tipo_var.trace('w', lambda *args: atualizar_campos_dinamicos())
        atualizar_campos_dinamicos()
    
        # Aplicação da promoção
        tk.Label(scrollable_frame, text="Aplicar a:*").pack(anchor='w', pady=10)
        aplicacao_var = tk.StringVar(value="TODOS")
        
        # Carregar produtos e categorias
        try:
            self.cursor.execute("SELECT id, nome FROM produtos WHERE ativo = TRUE ORDER BY nome")
            produtos = self.cursor.fetchall()
            produtos_dict = {f"{p['id']} - {p['nome']}": p['id'] for p in produtos}
            
            self.cursor.execute("SELECT id, nome FROM categorias WHERE ativo = TRUE ORDER BY nome")
            categorias = self.cursor.fetchall()
            categorias_dict = {f"{c['id']} - {c['nome']}": c['id'] for c in categorias}
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar produtos/categorias: {e}")
            return
    
        aplicacao_frame = tk.Frame(scrollable_frame)
        aplicacao_frame.pack(fill=tk.X, pady=5)
    
        def atualizar_selecao_alvo():
            for widget in aplicacao_frame.winfo_children():
                widget.destroy()
    
            tk.Radiobutton(aplicacao_frame, text="Todos os Produtos", variable=aplicacao_var, value="TODOS").pack(anchor='w')
            tk.Radiobutton(aplicacao_frame, text="Produto Específico", variable=aplicacao_var, value="PRODUTO").pack(anchor='w')
            tk.Radiobutton(aplicacao_frame, text="Categoria", variable=aplicacao_var, value="CATEGORIA").pack(anchor='w')
    
            if aplicacao_var.get() == "PRODUTO":
                produto_frame = tk.Frame(scrollable_frame)
                produto_frame.pack(fill=tk.X, pady=5)
                tk.Label(produto_frame, text="Selecionar Produto:").pack(side=tk.LEFT)
                produto_combo = ttk.Combobox(produto_frame, textvariable=produto_var, values=list(produtos_dict.keys()), state="readonly", width=40)
                produto_combo.pack(side=tk.LEFT, padx=5)
                if promocao and promocao['produto_alvo_id']:
                    for key, value in produtos_dict.items():
                        if value == promocao['produto_alvo_id']:
                            produto_var.set(key)
                            break
    
            elif aplicacao_var.get() == "CATEGORIA":
                categoria_frame = tk.Frame(scrollable_frame)
                categoria_frame.pack(fill=tk.X, pady=5)
                tk.Label(categoria_frame, text="Selecionar Categoria:").pack(side=tk.LEFT)
                categoria_combo = ttk.Combobox(categoria_frame, textvariable=categoria_var, values=list(categorias_dict.keys()), state="readonly", width=40)
                categoria_combo.pack(side=tk.LEFT, padx=5)
                if promocao and promocao['categoria_alvo_id']:
                    for key, value in categorias_dict.items():
                        if value == promocao['categoria_alvo_id']:
                            categoria_var.set(key)
                            break
    
        aplicacao_var.trace('w', lambda *args: atualizar_selecao_alvo())
        atualizar_selecao_alvo()
    
        # Datas
        tk.Label(scrollable_frame, text="Data de Início:*").pack(anchor='w', pady=10)
        tk.Entry(scrollable_frame, textvariable=inicio_var, width=12).pack(anchor='w', pady=5)
    
        tk.Label(scrollable_frame, text="Data de Fim:*").pack(anchor='w', pady=5)
        tk.Entry(scrollable_frame, textvariable=fim_var, width=12).pack(anchor='w', pady=5)
    
        def salvar_promocao():
            # Validação e salvamento
            if not nome_var.get().strip():
                messagebox.showerror("Erro", "Nome da promoção é obrigatório!")
                return
    
            try:
                data_inicio = datetime.strptime(inicio_var.get(), '%d/%m/%Y')
                data_fim = datetime.strptime(fim_var.get(), '%d/%m/%Y')
                
                if data_fim < data_inicio:
                    messagebox.showerror("Erro", "Data de fim deve ser posterior à data de início!")
                    return
                    
            except ValueError:
                messagebox.showerror("Erro", "Datas devem estar no formato DD/MM/AAAA!")
                return
    
            # Preparar dados
            produto_alvo_id = None
            categoria_alvo_id = None
            
            if aplicacao_var.get() == "PRODUTO" and produto_var.get():
                produto_alvo_id = produtos_dict[produto_var.get()]
            elif aplicacao_var.get() == "CATEGORIA" and categoria_var.get():
                categoria_alvo_id = categorias_dict[categoria_var.get()]
    
            # Salvar no banco
            try:
                if promocao:
                    # Atualizar promoção existente
                    self.cursor.execute('''
                        UPDATE promocoes SET
                        nome = %s, descricao = %s, tipo = %s, valor = %s,
                        produto_alvo_id = %s, categoria_alvo_id = %s,
                        data_inicio = %s, data_fim = %s,
                        quantidade_x = %s, quantidade_y = %s, quantidade_minima = %s
                        WHERE id = %s
                    ''', (
                        nome_var.get().strip(),
                        descricao_entry.get('1.0', tk.END).strip(),
                        tipo_var.get(),
                        float(valor_var.get()) if valor_var.get() else None,
                        produto_alvo_id,
                        categoria_alvo_id,
                        data_inicio,
                        data_fim,
                        int(quantidade_x_var.get()) if quantidade_x_var.get() else None,
                        int(quantidade_y_var.get()) if quantidade_y_var.get() else None,
                        int(quantidade_minima_var.get()) if quantidade_minima_var.get() else None,
                        promocao['id']
                    ))
                    acao_auditoria = 'EDICAO_PROMOCAO'
                    descricao_auditoria = f'Promoção editada: {nome_var.get()}'
                else:
                    # Nova promoção
                    self.cursor.execute('''
                        INSERT INTO promocoes 
                        (nome, descricao, tipo, valor, produto_alvo_id, categoria_alvo_id,
                         data_inicio, data_fim, quantidade_x, quantidade_y, quantidade_minima, criado_por)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        nome_var.get().strip(),
                        descricao_entry.get('1.0', tk.END).strip(),
                        tipo_var.get(),
                        float(valor_var.get()) if valor_var.get() else None,
                        produto_alvo_id,
                        categoria_alvo_id,
                        data_inicio,
                        data_fim,
                        int(quantidade_x_var.get()) if quantidade_x_var.get() else None,
                        int(quantidade_y_var.get()) if quantidade_y_var.get() else None,
                        int(quantidade_minima_var.get()) if quantidade_minima_var.get() else None,
                        self.operador_atual['id']
                    ))
                    acao_auditoria = 'CADASTRO_PROMOCAO'
                    descricao_auditoria = f'Nova promoção: {nome_var.get()}'
    
                self.conn.commit()
                self.registrar_auditoria(acao_auditoria, descricao_auditoria, 'promocoes', self.cursor.lastrowid if not promocao else promocao['id'])
                
                messagebox.showinfo("Sucesso", "Promoção salva com sucesso!")
                formulario_window.destroy()
                self.carregar_promocoes()
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar promoção: {e}")
    
        tk.Button(scrollable_frame, text="Salvar Promoção", command=salvar_promocao,
                 bg='#27ae60', fg='white', font=('Arial', 12, 'bold')).pack(pady=20)
    
    def editar_promocao(self):
        """Edita promoção selecionada"""
        selecao = self.tree_promocoes.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione uma promoção!")
            return
        
        if not self.verificar_acesso_supervisor():
            return
    
        item = self.tree_promocoes.item(selecao[0])
        promocao_id = item['values'][0]
    
        # Buscar dados da promoção
        self.cursor.execute('''
            SELECT * FROM promocoes WHERE id = %s
        ''', (promocao_id,))
        
        promocao = self.cursor.fetchone()
        if not promocao:
            return
    
        # Janela de edição (similar à de criação)
        self.criar_promocao(editar=True, promocao=promocao)
    
    def alterar_status_promocao(self):
        """Ativa/desativa promoção"""
        selecao = self.tree_promocoes.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione uma promoção!")
            return
        
        if not self.verificar_acesso_supervisor():
            return
    
        item = self.tree_promocoes.item(selecao[0])
        promocao_id = item['values'][0]
        promocao_nome = item['values'][1]
        status_atual = item['values'][8]  # Status
    
        novo_status = not (status_atual == "Ativa")
        status_text = "ativar" if novo_status else "desativar"
    
        if messagebox.askyesno("Confirmar", f"Deseja {status_text} a promoção '{promocao_nome}'?"):
            self.cursor.execute('UPDATE promocoes SET ativo = %s WHERE id = %s', 
                              (novo_status, promocao_id))
            
            self.registrar_auditoria('ALTERACAO_STATUS_PROMOCAO',
                                   f'Status alterado para: {status_text} - Promoção: {promocao_nome}',
                                   'promocoes', promocao_id)
            
            messagebox.showinfo("Sucesso", f"Promoção {status_text}da com sucesso!")
            self.carregar_promocoes()
     
    def relatorio_promocoes(self):
        """Relatório detalhado de promoções"""
        if not self.verificar_acesso_supervisor():
            return
    
        relatorio_window = tk.Toplevel(self.root)
        relatorio_window.title("Relatório de Promoções")
        relatorio_window.geometry("1000x600")
        relatorio_window.transient(self.root)
        
        # Frame principal
        main_frame = tk.Frame(relatorio_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        tk.Label(main_frame, text="RELATÓRIO DE PROMOÇÕES", 
                font=('Arial', 16, 'bold')).pack(pady=10)
    
        # Filtros
        filtros_frame = tk.Frame(main_frame)
        filtros_frame.pack(fill=tk.X, pady=10)
    
        tk.Label(filtros_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        status_var = tk.StringVar(value="TODAS")
        status_combo = ttk.Combobox(filtros_frame, textvariable=status_var,
                                   values=['TODAS', 'ATIVAS', 'INATIVAS'], state='readonly')
        status_combo.pack(side=tk.LEFT, padx=5)
    
        tk.Label(filtros_frame, text="Tipo:").pack(side=tk.LEFT, padx=5)
        tipo_var = tk.StringVar(value="TODOS")
        tipo_combo = ttk.Combobox(filtros_frame, textvariable=tipo_var,
                                 values=['TODOS', 'PERCENTUAL', 'VALOR_FIXO', 'COMPRE_X_LEVE_Y', 'DESCONTO_POR_QUANTIDADE'],
                                 state='readonly')
        tipo_combo.pack(side=tk.LEFT, padx=5)
    
        # Treeview
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
        columns = ('id', 'nome', 'tipo', 'valor', 'inicio', 'fim', 'produto', 'categoria', 'status')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
    
        tree.heading('id', text='ID')
        tree.heading('nome', text='Nome')
        tree.heading('tipo', text='Tipo')
        tree.heading('valor', text='Valor')
        tree.heading('inicio', text='Início')
        tree.heading('fim', text='Fim')
        tree.heading('produto', text='Produto')
        tree.heading('categoria', text='Categoria')
        tree.heading('status', text='Status')
    
        for col in columns:
            tree.column(col, width=100)
    
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
    
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        def carregar_relatorio():
            for item in tree.get_children():
                tree.delete(item)
            
            try:
                query = '''
                    SELECT p.id, p.nome, p.tipo, p.valor, p.data_inicio, p.data_fim, 
                           pr.nome as produto_nome, c.nome as categoria_nome, p.ativo
                    FROM promocoes p
                    LEFT JOIN produtos pr ON p.produto_alvo_id = pr.id
                    LEFT JOIN categorias c ON p.categoria_alvo_id = c.id
                    WHERE 1=1
                '''
                params = []
    
                if status_var.get() == 'ATIVAS':
                    query += ' AND p.ativo = TRUE'
                elif status_var.get() == 'INATIVAS':
                    query += ' AND p.ativo = FALSE'
    
                if tipo_var.get() != 'TODOS':
                    query += ' AND p.tipo = %s'
                    params.append(tipo_var.get())
    
                query += ' ORDER BY p.data_inicio DESC'
    
                self.cursor.execute(query, params)
                
                for promocao in self.cursor.fetchall():
                    # CORREÇÃO: Verificar se as datas não são None
                    data_inicio = promocao['data_inicio'].strftime('%d/%m/%Y') if promocao['data_inicio'] else "N/A"
                    data_fim = promocao['data_fim'].strftime('%d/%m/%Y') if promocao['data_fim'] else "N/A"
                    status = "Ativa" if promocao['ativo'] else "Inativa"
                    
                    tree.insert('', tk.END, values=(
                        promocao['id'],
                        promocao['nome'],
                        promocao['tipo'],
                        f"R$ {float(promocao['valor']):.2f}" if promocao['valor'] else "N/A",
                        data_inicio,
                        data_fim,
                        promocao['produto_nome'] or "N/A",
                        promocao['categoria_nome'] or "N/A",
                        status
                    ))
            except Exception as e:
                print(f"Erro ao carregar promoções: {e}")
                messagebox.showerror("Erro", f"Erro ao carregar promoções: {e}")
    
        # Botões
        botoes_frame = tk.Frame(main_frame)
        botoes_frame.pack(fill=tk.X, pady=10)
    
        tk.Button(botoes_frame, text="🔍 Filtrar", command=carregar_relatorio,
                 bg='#3498db', fg='white').pack(side=tk.LEFT, padx=5)
        
        # BOTÃO FECHAR ADICIONADO AQUI
        tk.Button(botoes_frame, text="❌ Fechar", command=relatorio_window.destroy,
                 bg='#e74c3c', fg='white').pack(side=tk.RIGHT, padx=5)
    
        # Carregar dados iniciais
        carregar_relatorio()
    
    #nome metodo promo fim            
 
    #novos metos avança fim
    # nova class impr print inici0
import os
import tempfile
import win32print
import win32ui
from PIL import Image, ImageWin
import socket

class SistemaImpressao:
    def __init__(self, sistema_vendas):
        self.sistema = sistema_vendas
        #self.config_impressora = self.carregar_config_impressora()
        self.config_impressora = self.carregar_config_impressora()
        
    def carregar_config_impressora(self):
        """Carrega configurações da impressora do .INI"""
        return {
            'tipo': self.sistema.config_manager.get('IMPRESSAO', 'tipo'),
            'nome': self.sistema.config_manager.get('IMPRESSAO', 'nome_impressora'),
            'endereco': self.sistema.config_manager.get('IMPRESSAO', 'endereco_ip'),
            'porta': self.sistema.config_manager.get('IMPRESSAO', 'porta_tcp'),
            'porta_com': self.sistema.config_manager.get('IMPRESSAO', 'porta_com')
        }
    
    def salvar_config_impressora(self, config):
        """Salva configurações da impressora no .INI"""
        self.sistema.config_manager.set('IMPRESSAO', 'tipo', config['tipo'])
        self.sistema.config_manager.set('IMPRESSAO', 'nome_impressora', config['nome'])
        self.sistema.config_manager.set('IMPRESSAO', 'endereco_ip', config['endereco'])
        self.sistema.config_manager.set('IMPRESSAO', 'porta_tcp', config['porta'])
        self.sistema.config_manager.set('IMPRESSAO', 'porta_com', config['porta_com'])
        self.sistema.config_manager.salvar_configuracoes()
        # Atualizar config local também
        self.config_impressora = config
    
    def detectar_impressoras(self):
        """Detecta impressoras disponíveis"""
        try:
            impressoras = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            return [printer[2] for printer in impressoras]
        except:
            return []
    
    def mostrar_config_impressao(self):
        """Mostra configurações de impressão"""
        # CORREÇÃO: Chamar o método diretamente
        if hasattr(self, 'impressao'):
            self.impressao.mostrar_config_impressao()
        else:
            messagebox.showwarning("Aviso", "Sistema de impressão não disponível")
    
    def imprimir_texto(self, texto):
        """Imprime texto na impressora configurada"""
        tipo = self.config_impressora.get('tipo', 'windows')
        
        if tipo == 'windows':
            self._imprimir_windows(texto)
        elif tipo == 'tcpip':
            self._imprimir_tcpip(texto)
        elif tipo == 'com':
            self._imprimir_com(texto)
        elif tipo == 'arquivo':
            self._salvar_arquivo(texto)
        else:
            self._imprimir_windows(texto)  # Fallback
    
    def _imprimir_windows(self, texto):
        """Imprime usando driver Windows"""
        try:
            printer_name = self.config_impressora.get('nome', '')
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()
            
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                # Configurar trabalho de impressão
                job_info = win32print.GetPrinter(hprinter, 2)["pPrinterName"]
                hjob = win32print.StartDocPrinter(hprinter, 1, ("Recibo", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hprinter)
                    
                    # Converter texto para bytes (ESC/POS)
                    texto_bytes = self._converter_para_escpos(texto)
                    win32print.WritePrinter(hprinter, texto_bytes)
                    
                    win32print.EndPagePrinter(hprinter)
                finally:
                    win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            raise Exception(f"Erro impressão Windows: {e}")
    
    def _imprimir_tcpip(self, texto):
        """Imprime via TCP/IP (ethernet)"""
        try:
            endereco = self.config_impressora.get('endereco', '')
            porta = int(self.config_impressora.get('porta', 9100))
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((endereco, porta))
                
                texto_bytes = self._converter_para_escpos(texto)
                sock.send(texto_bytes)
                
        except Exception as e:
            raise Exception(f"Erro impressão TCP/IP: {e}")
    
    def _imprimir_com(self, texto):
        """Imprime via porta COM (serial)"""
        try:
            import serial
            porta = self.config_impressora.get('endereco', 'COM1')
            
            with serial.Serial(porta, 9600, timeout=10) as ser:
                texto_bytes = self._converter_para_escpos(texto)
                ser.write(texto_bytes)
                
        except Exception as e:
            raise Exception(f"Erro impressão COM: {e}")
    
    def _salvar_arquivo(self, texto):
        """Salva em arquivo (para debug)"""
        try:
            filename = f"recibo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(texto)
        except Exception as e:
            raise Exception(f"Erro salvar arquivo: {e}")
    
    def _converter_para_escpos(self, texto, cortar_papel=True, abrir_gaveta=True):
        """Converte texto para comandos ESC/POS com opções avançadas"""
        # Comandos básicos ESC/POS
        comandos = [
            b'\x1B\x40',  # Inicializar
            b'\x1B\x21\x00',  # Fonte normal
            b'\x1B\x45\x00',  # Negrito off
            b'\x1B\x61\x01',  # Centralizar (para título)
        ]
        
        # Adicionar texto (convertido para bytes)
        texto_bytes = texto.encode('utf-8', errors='ignore')
        
        comandos_finais = []
        
        # Abertura de gaveta (pino 2 - geralmente 0.1s)
        if abrir_gaveta:
            comandos_finais.extend([
                b'\x1B\x70\x00\x19\x19',  # Abrir gaveta (pino 2)
            ])
        
        # Avançar papel antes de cortar
        comandos_finais.extend([
            b'\n\n\n\n\n',  # Avançar papel
        ])
        
        # Corte de papel
        if cortar_papel:
            comandos_finais.extend([
                b'\x1B\x64\x02',  # Cortar papel (parcial)
                b'\x1B\x64\x03',  # Cortar papel (completo - se suportado)
            ])
        
        # Combinar todos os bytes
        resultado = b''.join(comandos) + texto_bytes + b''.join(comandos_finais)
        return resultado
    
    def imprimir_recibo(self, recibo_texto, venda_id):
        """Imprime recibo completo com cortes e abertura de gaveta"""
        try:
            # Configurações do sistema
            cortar_papel = self.sistema.config.get('recibo_cortar_papel', True)
            abrir_gaveta = self.sistema.config.get('recibo_abrir_gaveta', True)
            
            # Adicionar cabeçalho específico para impressão
            cabecalho = "\n" + "="*42 + "\n"
            cabecalho += " " * 8 + "C O M P R O V A N T E\n"
            cabecalho += "="*42 + "\n\n"
            
            recibo_completo = cabecalho + recibo_texto
            
            # Imprimir com configurações
            texto_impressao = self._converter_para_escpos(
                recibo_completo, 
                cortar_papel=cortar_papel,
                abrir_gaveta=abrir_gaveta
            )
            
            # Enviar para impressão
            tipo = self.config_impressora.get('tipo', 'windows')
            
            if tipo == 'windows':
                self._imprimir_windows_bytes(texto_impressao)
            elif tipo == 'tcpip':
                self._imprimir_tcpip_bytes(texto_impressao)
            elif tipo == 'com':
                self._imprimir_com_bytes(texto_impressao)
            
            # Salvar backup
            self._salvar_recibo_arquivo(recibo_texto, venda_id)
            
            return True
            
        except Exception as e:
            print(f"Erro ao imprimir recibo: {e}")
            return False
    
    def _imprimir_windows_bytes(self, texto_bytes):
        """Imprime bytes diretamente no Windows"""
        try:
            printer_name = self.config_impressora.get('nome', '')
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()
            
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                hjob = win32print.StartDocPrinter(hprinter, 1, ("Recibo", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, texto_bytes)
                    win32print.EndPagePrinter(hprinter)
                finally:
                    win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
        except Exception as e:
            raise Exception(f"Erro impressão Windows: {e}")
    
    def _imprimir_tcpip_bytes(self, texto_bytes):
        """Imprime bytes via TCP/IP"""
        try:
            endereco = self.config_impressora.get('endereco', '')
            porta = int(self.config_impressora.get('porta', 9100))
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((endereco, porta))
                sock.send(texto_bytes)
        except Exception as e:
            raise Exception(f"Erro impressão TCP/IP: {e}")
    
    def _imprimir_com_bytes(self, texto_bytes):
        """Imprime bytes via porta COM"""
        try:
            import serial
            porta = self.config_impressora.get('endereco', 'COM1')
            
            with serial.Serial(porta, 9600, timeout=10) as ser:
                ser.write(texto_bytes)
        except Exception as e:
            raise Exception(f"Erro impressão COM: {e}")
    
    def _salvar_recibo_arquivo(self, recibo_texto, venda_id):
        """Salva recibo em arquivo para backup"""
        try:
            pasta_recibos = "recibos"
            if not os.path.exists(pasta_recibos):
                os.makedirs(pasta_recibos)
            
            filename = f"{pasta_recibos}/recibo_{venda_id:06d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(recibo_texto)
        except Exception as e:
            print(f"Erro ao salvar recibo: {e}")    
     
    def verificar_config_ini(self):
        """Verifica se config.ini existe e é válido"""
        if not os.path.exists('config.ini'):
            print("📝 Criando config.ini padrão...")
            # O GerenciadorConfig já cria automaticamente, mas forçamos salvamento
            self.config_manager.salvar_configuracoes()
        
        # Verificar seções essenciais
        secoes_essenciais = ['SISTEMA', 'RECIBO', 'IMPRESSAO', 'BANCO_DADOS', 'SEGURANCA']
        for secao in secoes_essenciais:
            if secao not in self.config_manager.config:
                print(f"⚠️  Adicionando seção {secao} ao config.ini")
                # O GerenciadorConfig já adiciona automaticamente
    
    # nova class impr print fim
    
    # nova class configuconf ini
    
import configparser
import os

class GerenciadorConfig:
    def __init__(self, arquivo_config='config.ini'):
        self.arquivo_config = arquivo_config
        self.config = configparser.ConfigParser()
        self.carregar_configuracoes()
    
    def carregar_configuracoes(self):
        """Carrega configurações do arquivo .ini"""
        # Configurações padrão
        self.config['SISTEMA'] = {
            'empresa_nome': 'Sistema de Vendas Professional Plus',
            'empresa_endereco': 'Rua Comercial, 123 - Centro',
            'empresa_telefone': '(11) 9999-9999',
            'empresa_cnpj': '',
            'versao': '2.0'
        }
        
        self.config['RECIBO'] = {
            'imprimir_automaticamente': 'sim',
            'cortar_papel': 'sim',
            'abrir_gaveta': 'sim',
            'numero_copias': '1',
            'mensagem_rodape': 'Obrigado pela preferência!',
            'mostrar_cnpj': 'nao'
        }
        
        self.config['IMPRESSAO'] = {
            'tipo': 'windows',
            'nome_impressora': '',
            'interface': 'USB',
            'endereco_ip': '',
            'porta_tcp': '9100',
            'porta_com': 'COM1',
            'velocidade_serial': '9600'
        }
        
        self.config['BANCO_DADOS'] = {
            'host': 'localhost',
            'usuario': 'root',
            'senha': '',
            'database': 'sistema_vendas5'
        }
        
        self.config['SEGURANCA'] = {
            'tamanho_minimo_senha': '5',
            'tempo_sessao_minutos': '60',
            'backup_automatico': 'sim',
            'log_auditoria': 'sim'
        }
        
        self.config['BALANCA'] = {
            'tipo': 'nenhuma',
            'porta': 'COM1',
            'baudrate': '9600'
        }
        
        self.config['ESTOQUE'] = {
            'alertar_estoque_baixo': 'sim',
            'nivel_alerta_estoque': '5',
            'permitir_venda_sem_estoque': 'nao',
            'controlar_validade': 'nao'
        }
        
        # Carregar do arquivo se existir
        if os.path.exists(self.arquivo_config):
            self.config.read(self.arquivo_config, encoding='utf-8')
        else:
            self.salvar_configuracoes()
    
    def salvar_configuracoes(self):
        """Salva configurações no arquivo .ini"""
        with open(self.arquivo_config, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
    
    def get(self, secao, chave, tipo=str):
        """Obtém valor da configuração com tipo específico"""
        try:
            valor = self.config[secao][chave]
            if tipo == bool:
                return valor.lower() in ('sim', 'yes', 'true', '1', 'on')
            elif tipo == int:
                return int(valor)
            elif tipo == float:
                return float(valor)
            else:
                return valor
        except:
            # Retornar valor padrão se não existir
            return self.get_valor_padrao(secao, chave, tipo)
    
    def set(self, secao, chave, valor):
        """Define valor da configuração"""
        if secao not in self.config:
            self.config[secao] = {}
        
        if isinstance(valor, bool):
            self.config[secao][chave] = 'sim' if valor else 'nao'
        else:
            self.config[secao][chave] = str(valor)
    
    def get_valor_padrao(self, secao, chave, tipo):
        """Retorna valor padrão para uma configuração"""
        padroes = {
            ('SISTEMA', 'empresa_nome'): 'Sistema de Vendas',
            ('RECIBO', 'imprimir_automaticamente'): True,
            ('RECIBO', 'cortar_papel'): True,
            ('RECIBO', 'abrir_gaveta'): True,
            ('SEGURANCA', 'tamanho_minimo_senha'): 5,
        }
        return padroes.get((secao, chave), '' if tipo == str else None)
    
    def verificar_conexao_mysql(self):
        """Verifica e reconecta ao MySQL se necessário"""
        try:
            self.cursor.execute("SELECT 1")
            return True
        except (mysql.connector.Error, AttributeError):
            try:
                print("🔁 Reconectando ao MySQL...")
                self.conectar_mysql()
                return True
            except:
                return False
    
    # Modificar métodos que usam o cursor para verificar conexão
    def executar_query_com_reconexao(self, query, params=None):
        """Executa query com verificação de conexão"""
        if not self.verificar_conexao_mysql():
            messagebox.showerror("Erro", "Não foi possível conectar ao banco de dados!")
            return None
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return True
        except mysql.connector.Error as e:
            print(f"Erro na query: {e}")
            return False
 
    # nova class configuconf fim
 
if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaVendasProfissional(root)
    
    # O login será chamado automaticamente após 500ms através do criar_interface
    # root.after(100, app.fazer_login) - REMOVER ESTA LINHA
    
    root.mainloop()
