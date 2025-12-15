import os
import sqlite3
from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from flask_mail import Mail, Message
import qrcode
from io import BytesIO
import base64
from dotenv import load_dotenv
import requests
from datetime import datetime
import hashlib
from functools import wraps
import time

# 1. Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

# Chave secreta para sessões (necessária para login admin)
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-mudar-em-producao')

# 2. Configuração de E-mail (Mais robusta)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_DEBUG'] = True  # Isso ajuda a ver detalhes do erro no terminal

mail = Mail(app)
DB = 'loja.db'

# --- VERIFICAÇÃO INICIAL ---
# Isso avisa logo de cara se a senha não foi configurada
if app.config['MAIL_PASSWORD'] == 'sua_senha_de_app_16_caracteres':
    print("\n⚠️  ATENÇÃO: Você não configurou a Senha de App no arquivo .env!")
    print("   O envio de e-mail VAI FALHAR. Edite o arquivo .env agora.\n")

def conectar():
    """Conecta ao banco de dados SQLite"""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

# --- ROTAS DE PÁGINAS (FRONTEND) ---

@app.route('/')
def index():
    """Página inicial com catálogo"""
    try:
        con = conectar()
        livros = con.execute("SELECT id, titulo, autor, preco, imagem FROM livros LIMIT 10").fetchall()
        con.close()
        return render_template('index.html', livros=[dict(l) for l in livros])
    except Exception as e:
        return f"Erro ao carregar banco de dados: {e}. Verifique se rodou 'criar_banco.py'."

@app.route('/livro/<int:livro_id>')
def livro(livro_id):
    """Página de detalhes do livro"""
    con = conectar()
    livro = con.execute("SELECT * FROM livros WHERE id=?", (livro_id,)).fetchone()
    con.close()
    if not livro:
        return "Livro não encontrado", 404
    return render_template('livro.html', livro=dict(livro))

@app.route('/cadastro')
def cadastro_page():
    return render_template('cadastroForm.html')

@app.route('/login')
def login_page():
    return render_template('loginForm.html')

@app.route('/terms')
def terms_page():
    return render_template('terms&politc.html')

@app.route('/faq')
def faq_page():
    """Página de perguntas frequentes"""
    return render_template('faq.html')

@app.route('/localizacao')
def localizacao_page():
    """Página de localização com mapa"""
    return render_template('localizacao.html')

@app.route('/contato')
def contato_page():
    """Página de contato"""
    return render_template('contato.html')

@app.route('/sobre')
def sobre_page():
    """Página sobre a empresa"""
    return render_template('sobre.html')

@app.route('/admin')
def admin_page():
    """Página de administração"""
    # Verificar se admin está logado
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin.html')

@app.route('/perfil')
def perfil_page():
    """Página de perfil do usuário"""
    return render_template('perfil.html')

@app.route('/api/perfil/<int:usuario_id>')
def api_perfil(usuario_id):
    """API para buscar dados do perfil do usuário"""
    con = conectar()
    
    # Dados do usuário
    usuario = con.execute("""
        SELECT id, nome, email, criado_em 
        FROM usuarios 
        WHERE id=?
    """, (usuario_id,)).fetchone()
    
    if not usuario:
        con.close()
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    # Estatísticas do usuário
    stats = con.execute("""
        SELECT 
            COUNT(*) as total_pedidos,
            COUNT(CASE WHEN status='PAGO' THEN 1 END) as pedidos_pagos,
            COUNT(CASE WHEN status='PENDENTE' THEN 1 END) as pedidos_pendentes,
            COALESCE(SUM(CASE WHEN status='PAGO' THEN l.preco ELSE 0 END), 0) as total_gasto
        FROM pedidos p
        LEFT JOIN livros l ON p.livro_id = l.id
        WHERE p.usuario_id=?
    """, (usuario_id,)).fetchone()
    
    # Histórico de pedidos
    pedidos = con.execute("""
        SELECT 
            p.id,
            p.status,
            p.criado_em,
            l.titulo,
            l.autor,
            l.preco,
            l.imagem
        FROM pedidos p
        LEFT JOIN livros l ON p.livro_id = l.id
        WHERE p.usuario_id=?
        ORDER BY p.criado_em DESC
    """, (usuario_id,)).fetchall()
    
    con.close()
    
    return jsonify({
        'usuario': {
            'id': usuario['id'],
            'nome': usuario['nome'],
            'email': usuario['email'],
            'membro_desde': usuario['criado_em']
        },
        'stats': {
            'total_pedidos': stats['total_pedidos'],
            'pedidos_pagos': stats['pedidos_pagos'],
            'pedidos_pendentes': stats['pedidos_pendentes'],
            'total_gasto': float(stats['total_gasto'])
        },
        'pedidos': [{
            'id': p['id'],
            'titulo': p['titulo'],
            'autor': p['autor'],
            'preco': float(p['preco']) if p['preco'] else 0,
            'status': p['status'],
            'data': p['criado_em'],
            'imagem': p['imagem']
        } for p in pedidos]
    })

@app.route('/ebooks/<path:filename>')
def ebooks(filename):
    """Rota para servir arquivos locais se necessário"""
    return send_from_directory(os.path.join(app.static_folder, 'ebooks'), filename)

# --- APIs (BACKEND) ---

@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    """Cria o pedido e gera o PIX real via Mercado Pago"""
    data = request.json
    email = data.get('email')
    livro_id = data.get('livro_id')
    usuario_id = data.get('usuario_id')  # Novo: ID do usuário logado
    
    if not email or not livro_id:
        return jsonify({'error': 'Dados incompletos'}), 400

    con = conectar()
    livro = con.execute("SELECT id, titulo, preco FROM livros WHERE id=?", (livro_id,)).fetchone()
    
    if not livro:
        con.close()
        return jsonify({'error': 'Livro indisponível'}), 404

    # 1. Registrar pedido com usuario_id
    cur = con.cursor()
    # Verificar se coluna usuario_id existe, senão criar
    try:
        cur.execute("""INSERT INTO pedidos (email, livro_id, usuario_id, status) 
                       VALUES (?, ?, ?, ?)""",
                    (email, livro_id, usuario_id, 'PENDENTE'))
    except sqlite3.OperationalError:
        # Coluna não existe, adicionar e tentar novamente
        cur.execute("ALTER TABLE pedidos ADD COLUMN usuario_id INTEGER")
        cur.execute("""INSERT INTO pedidos (email, livro_id, usuario_id, status) 
                       VALUES (?, ?, ?, ?)""",
                    (email, livro_id, usuario_id, 'PENDENTE'))
    
    pedido_id = cur.lastrowid
    con.commit()

    # Gerar PIX Simulado
    valor = f"{livro['preco']:.2f}"
    texto_pix = f"00020126580014BR.GOV.BCB.PIX0136{email}520400005303986540{valor}5802BR5911ClicLeitura6009Sao_Paulo62070503***6304"
    
    img = qrcode.make(texto_pix)
    buf = BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    cur.execute("UPDATE pedidos SET pix_code=? WHERE id=?", 
               (f"SIMULADO_{pedido_id}", pedido_id))
    con.commit()
    con.close()
    
    print(f"✅ PIX SIMULADO gerado para pedido #{pedido_id}")

    return jsonify({
        'pedido_id': pedido_id, 
        'qr_base64': qr_b64, 
        'pix_text': texto_pix,
        'real_pix': False
    })

# WEBHOOK DESATIVADO - Envio manual pelo painel admin
# Para reativar envio automático, descomente o código abaixo

# @app.route('/webhook/mercadopago', methods=['POST'])
# def webhook_mercadopago():
#     """Recebe notificações automáticas de pagamento do Mercado Pago"""
#     try:
#         data = request.json
#         print(f"\n🔔 Webhook recebido: {data}")
#         
#         # Mercado Pago envia notificações de pagamento
#         if data.get('type') == 'payment':
#             payment_id = data['data']['id']
#             
#             # Buscar detalhes do pagamento
#             payment_info = sdk.payment().get(payment_id)
#             payment = payment_info["response"]
#             
#             print(f"💳 Status do pagamento: {payment['status']}")
#             
#             # Se o pagamento foi aprovado
#             if payment['status'] == 'approved':
#                 external_ref = payment.get('external_reference')  # Nosso pedido_id
#                 
#                 if external_ref:
#                     pedido_id = int(external_ref)
#                     print(f"✅ Pagamento aprovado! Processando pedido #{pedido_id}")
#                     
#                     # Enviar o livro por email automaticamente
#                     enviar_livro_email(pedido_id)
#                     
#         return jsonify({'status': 'ok'}), 200
#         
#     except Exception as e:
#         print(f"❌ Erro no webhook: {e}")
#         return jsonify({'error': str(e)}), 500

def enviar_livro_email(pedido_id):
    """Função auxiliar para enviar o livro por email"""
    con = conectar()
    query = """
        SELECT p.id, p.email, l.pdf, l.titulo, l.origem, l.autor 
        FROM pedidos p 
        JOIN livros l ON p.livro_id = l.id 
        WHERE p.id=?
    """
    pedido = con.execute(query, (pedido_id,)).fetchone()
    
    if not pedido:
        con.close()
        print(f"❌ Pedido #{pedido_id} não encontrado")
        return False

    # Baixar/localizar PDF
    pdf_content = None
    pdf_name = f"{pedido['titulo'][:30].replace(' ', '_')}.pdf"
    autor = pedido['autor'] if pedido['autor'] else 'Desconhecido'
    
    print(f"📖 Preparando envio: {pedido['titulo']}")

    try:
        if pedido['pdf'].startswith('http'):
            print(f"⏳ Baixando PDF de: {pedido['pdf'][:70]}...")
            
            # Para Archive.org, usar sessão com headers de navegador real
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://archive.org/',
                'DNT': '1',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            })
            
            # Tentar múltiplas vezes
            tentativas = 0
            max_tentativas = 3
            
            while tentativas < max_tentativas and not pdf_content:
                tentativas += 1
                
                try:
                    print(f"   Tentativa {tentativas}/{max_tentativas}...")
                    
                    # Aguardar entre tentativas para parecer mais humano
                    if tentativas > 1:
                        time.sleep(3)
                    
                    response = session.get(pedido['pdf'], timeout=60, stream=True, allow_redirects=True)
                    
                    if response.status_code == 200:
                        # Verificar se é realmente PDF
                        content_type = response.headers.get('Content-Type', '')
                        if 'pdf' not in content_type.lower() and 'application/octet-stream' not in content_type:
                            print(f"⚠️  Resposta não é PDF: {content_type}")
                            continue
                        
                        # Baixar em chunks
                        chunks = []
                        downloaded = 0
                        print(f"   📥 Baixando...", end='', flush=True)
                        
                        for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                            if chunk:
                                chunks.append(chunk)
                                downloaded += len(chunk)
                                if downloaded % (1024 * 1024) == 0:  # A cada 1MB
                                    print(f" {downloaded // (1024*1024)}MB", end='', flush=True)
                        
                        print()  # Nova linha
                        pdf_content = b''.join(chunks)
                        
                        if len(pdf_content) > 10000:  # Pelo menos 10KB
                            print(f"✅ PDF baixado: {len(pdf_content):,} bytes ({len(pdf_content)/1024/1024:.2f} MB)")
                        else:
                            print(f"⚠️  Arquivo muito pequeno ({len(pdf_content)} bytes) - pode não ser válido")
                            pdf_content = None
                            
                    elif response.status_code in [403, 401]:
                        print(f"❌ Acesso negado ({response.status_code}) - Archive.org bloqueou o acesso")
                        if tentativas < max_tentativas:
                            print(f"   ⏳ Aguardando antes de tentar novamente...")
                            time.sleep(5)
                    else:
                        print(f"❌ Erro HTTP {response.status_code}")
                        if tentativas < max_tentativas:
                            time.sleep(2)
                        
                except requests.exceptions.Timeout:
                    print(f"⏱️  Timeout na tentativa {tentativas}")
                    if tentativas < max_tentativas:
                        print(f"   ⏳ Aumentando timeout e tentando novamente...")
                        time.sleep(3)
                except Exception as err:
                    print(f"❌ Erro na tentativa {tentativas}: {err}")
                    if tentativas < max_tentativas:
                        time.sleep(2)
                        
            if not pdf_content:
                print(f"❌ Não foi possível baixar o PDF após {tentativas} tentativas")
                print(f"💡 O Archive.org pode estar bloqueando downloads automáticos")
                con.close()
                return False
                
        else:
            # PDF local
            caminho = os.path.join(app.static_folder, 'ebooks', pedido['pdf'])
            if os.path.exists(caminho):
                with open(caminho, 'rb') as f:
                    pdf_content = f.read()
                print(f"✅ PDF local encontrado: {len(pdf_content):,} bytes")
            else:
                print(f"❌ Arquivo local não encontrado: {caminho}")
                con.close()
                return False

    except requests.exceptions.Timeout:
        print(f"❌ Timeout ao baixar PDF (excedeu 60s)")
        con.close()
        return False
    except Exception as e:
        print(f"❌ Erro ao obter PDF: {e}")
        con.close()
        return False

    if not pdf_content:
        con.close()
        print("❌ PDF vazio ou não disponível")
        return False

    # Buscar nome do usuário
    nome_cliente = "Cliente"
    try:
        usuario = con.execute("""
            SELECT u.nome 
            FROM pedidos p 
            LEFT JOIN usuarios u ON p.usuario_id = u.id 
            WHERE p.id=?
        """, (pedido_id,)).fetchone()
        if usuario and usuario['nome']:
            nome_cliente = usuario['nome']
    except:
        pass
    
    # Enviar email
    try:
        print(f"📧 Enviando para: {pedido['email']}")
        
        with app.app_context():
            msg = Message(
                subject="Tudo certo! Seu ebook já está com você 📚✨",
                recipients=[pedido['email']]
            )
            
            # Corpo do email formatado
            msg.body = (
                f"Olá, {nome_cliente}!\n\n"
                f"Que ótima notícia: seu pagamento foi confirmado! ✅\n\n"
                f"O arquivo do seu novo e-book, \"{pedido['titulo']}\", já está anexado a este e-mail. "
                f"Agora é só baixar, preparar um café (ou chá!) e aproveitar a leitura.\n\n"
                f"Instruções rápidas:\n"
                f"• Baixe o anexo.\n"
                f"• Salve em seu dispositivo preferido.\n"
                f"• Comece a ler!\n\n"
                f"Caso tenha alguma dúvida sobre o uso do arquivo, você pode consultar nossos "
                f"Termos e Políticas de Uso em http://localhost:5000/terms ou responder a este e-mail.\n\n"
                f"Obrigada por escolher a ClicLeitura. Esperamos que essa história seja incrível!\n\n"
                f"Um abraço,\n"
                f"Equipe ClicLeitura!\n"
            )
            
            msg.attach(pdf_name, 'application/pdf', pdf_content)
            mail.send(msg)
        
        print("✅ E-MAIL ENVIADO COM SUCESSO!")

        # Atualizar status
        con.execute("UPDATE pedidos SET status=? WHERE id=?", ('PAGO', pedido_id))
        con.commit()
        con.close()
        
        return True

    except Exception as e:
        con.close()
        print(f"❌ Erro ao enviar email: {e}")
        return False

@app.route('/api/confirmar_pagamento', methods=['POST'])
def confirmar_pagamento():
    """Simula pagamento PIX e coloca pedido aguardando aprovação do admin"""
    data = request.json
    pedido_id = data.get('pedido_id')
    
    print(f"\n🔄 Pagamento simulado para pedido #{pedido_id}...")
    
    # Atualizar status do pedido para aguardar aprovação do admin
    con = conectar()
    con.execute("UPDATE pedidos SET status=? WHERE id=?", ('PENDENTE_APROVACAO', pedido_id))
    con.commit()
    con.close()
    
    return jsonify({
        'ok': True, 
        'message': 'Pagamento confirmado! Seu pedido está aguardando aprovação do administrador. Você receberá o e-book em breve.'
    })

@app.route('/api/cadastro', methods=['POST'])
def api_cadastro():
    data = request.json or request.form
    con = conectar()
    try:
        con.execute("INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)", 
                   (data['nome'], data['email'], data['senha']))
        con.commit()
        return jsonify({'ok': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'E-mail já existe'}), 400
    finally:
        con.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or request.form
    con = conectar()
    user = con.execute("SELECT * FROM usuarios WHERE email=? AND senha=?", 
                      (data.get('email'), data.get('senha'))).fetchone()
    con.close()
    if user:
        return jsonify({'ok': True, 'usuario': {
            'id': user['id'],
            'nome': user['nome'],
            'email': user['email']
        }})
    return jsonify({'error': 'Dados inválidos'}), 401

@app.route('/api/atualizar-perfil', methods=['POST'])
def api_atualizar_perfil():
    """Atualiza os dados pessoais do usuário"""
    data = request.json
    usuario_id = data.get('usuario_id')
    novo_nome = data.get('nome')
    novo_email = data.get('email')
    
    if not usuario_id or not novo_nome or not novo_email:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    con = conectar()
    try:
        # Verificar se o novo email já está em uso por outro usuário
        email_existe = con.execute(
            "SELECT id FROM usuarios WHERE email=? AND id!=?", 
            (novo_email, usuario_id)
        ).fetchone()
        
        if email_existe:
            con.close()
            return jsonify({'error': 'Este e-mail já está em uso'}), 400
        
        # Atualizar dados
        con.execute(
            "UPDATE usuarios SET nome=?, email=? WHERE id=?",
            (novo_nome, novo_email, usuario_id)
        )
        con.commit()
        con.close()
        
        return jsonify({'ok': True, 'message': 'Dados atualizados com sucesso'})
        
    except Exception as e:
        con.close()
        return jsonify({'error': f'Erro ao atualizar dados: {str(e)}'}), 500

@app.route('/api/alterar-senha', methods=['POST'])
def api_alterar_senha():
    """Altera a senha do usuário"""
    data = request.json
    usuario_id = data.get('usuario_id')
    senha_atual = data.get('senha_atual')
    nova_senha = data.get('nova_senha')
    
    if not usuario_id or not senha_atual or not nova_senha:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    con = conectar()
    try:
        # Verificar senha atual
        usuario = con.execute(
            "SELECT id FROM usuarios WHERE id=? AND senha=?",
            (usuario_id, senha_atual)
        ).fetchone()
        
        if not usuario:
            con.close()
            return jsonify({'error': 'Senha atual incorreta'}), 401
        
        # Atualizar senha
        con.execute(
            "UPDATE usuarios SET senha=? WHERE id=?",
            (nova_senha, usuario_id)
        )
        con.commit()
        con.close()
        
        return jsonify({'ok': True, 'message': 'Senha alterada com sucesso'})
        
    except Exception as e:
        con.close()
        return jsonify({'error': f'Erro ao alterar senha: {str(e)}'}), 500

# --- APIs DO CARRINHO ---

@app.route('/api/carrinho/adicionar', methods=['POST'])
def api_carrinho_adicionar():
    """Adiciona um livro ao carrinho"""
    data = request.json
    usuario_id = data.get('usuario_id')
    livro_id = data.get('livro_id')
    
    if not usuario_id or not livro_id:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    con = conectar()
    try:
        # Verificar se o livro existe
        livro = con.execute("SELECT id FROM livros WHERE id=?", (livro_id,)).fetchone()
        if not livro:
            con.close()
            return jsonify({'error': 'Livro não encontrado'}), 404
        
        # Adicionar ao carrinho (UNIQUE constraint previne duplicatas)
        try:
            con.execute(
                "INSERT INTO carrinho (usuario_id, livro_id) VALUES (?, ?)",
                (usuario_id, livro_id)
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return jsonify({'error': 'Este livro já está no carrinho'}), 400
        
        con.close()
        return jsonify({'ok': True, 'message': 'Livro adicionado ao carrinho'})
        
    except Exception as e:
        con.close()
        return jsonify({'error': f'Erro ao adicionar ao carrinho: {str(e)}'}), 500

@app.route('/api/carrinho/<int:usuario_id>')
def api_carrinho_listar(usuario_id):
    """Lista os itens do carrinho do usuário"""
    con = conectar()
    try:
        itens = con.execute("""
            SELECT 
                c.id,
                c.livro_id,
                l.titulo,
                l.autor,
                l.preco,
                l.imagem
            FROM carrinho c
            JOIN livros l ON c.livro_id = l.id
            WHERE c.usuario_id = ?
            ORDER BY c.adicionado_em DESC
        """, (usuario_id,)).fetchall()
        
        total = sum(item['preco'] for item in itens)
        
        con.close()
        
        return jsonify({
            'itens': [{
                'id': item['id'],
                'livro_id': item['livro_id'],
                'titulo': item['titulo'],
                'autor': item['autor'],
                'preco': float(item['preco']),
                'imagem': item['imagem']
            } for item in itens],
            'total': float(total)
        })
        
    except Exception as e:
        con.close()
        return jsonify({'error': f'Erro ao carregar carrinho: {str(e)}'}), 500

@app.route('/api/carrinho/remover/<int:item_id>', methods=['DELETE'])
def api_carrinho_remover(item_id):
    """Remove um item do carrinho"""
    con = conectar()
    try:
        con.execute("DELETE FROM carrinho WHERE id=?", (item_id,))
        con.commit()
        con.close()
        
        return jsonify({'ok': True, 'message': 'Item removido do carrinho'})
        
    except Exception as e:
        con.close()
        return jsonify({'error': f'Erro ao remover item: {str(e)}'}), 500

@app.route('/api/carrinho/finalizar', methods=['POST'])
def api_carrinho_finalizar():
    """Finaliza a compra criando pedidos para todos os itens do carrinho"""
    data = request.json
    usuario_id = data.get('usuario_id')
    
    if not usuario_id:
        return jsonify({'error': 'Usuário não informado'}), 400
    
    con = conectar()
    try:
        # Buscar usuário
        usuario = con.execute("SELECT email FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
        if not usuario:
            con.close()
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Buscar itens do carrinho
        itens = con.execute("""
            SELECT c.id, c.livro_id
            FROM carrinho c
            WHERE c.usuario_id = ?
        """, (usuario_id,)).fetchall()
        
        if not itens:
            con.close()
            return jsonify({'error': 'Carrinho vazio'}), 400
        
        # Criar pedidos para cada item
        pedidos_criados = []
        for item in itens:
            cursor = con.cursor()
            cursor.execute(
                "INSERT INTO pedidos (email, livro_id, usuario_id, status) VALUES (?, ?, ?, ?)",
                (usuario['email'], item['livro_id'], usuario_id, 'PENDENTE')
            )
            pedidos_criados.append(cursor.lastrowid)
        
        # Limpar carrinho
        con.execute("DELETE FROM carrinho WHERE usuario_id=?", (usuario_id,))
        con.commit()
        con.close()
        
        return jsonify({
            'ok': True,
            'message': f'{len(pedidos_criados)} pedido(s) criado(s) com sucesso',
            'pedidos': pedidos_criados
        })
        
    except Exception as e:
        con.close()
        return jsonify({'error': f'Erro ao finalizar compra: {str(e)}'}), 500


@app.route('/api/carrinho/finalizar-pix', methods=['POST'])
def api_carrinho_finalizar_pix():
    """Finaliza a compra criando UM pedido consolidado e gerando PIX"""
    data = request.json
    usuario_id = data.get('usuario_id')
    email = data.get('email')
    
    if not usuario_id or not email:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    con = conectar()
    try:
        # Buscar itens do carrinho com informações dos livros
        itens = con.execute("""
            SELECT c.livro_id, l.titulo, l.preco
            FROM carrinho c
            JOIN livros l ON c.livro_id = l.id
            WHERE c.usuario_id = ?
        """, (usuario_id,)).fetchall()
        
        if not itens:
            con.close()
            return jsonify({'error': 'Carrinho vazio'}), 400
        
        # Calcular total
        total = sum(item['preco'] for item in itens)
        quantidade = len(itens)
        
        # Criar UM pedido consolidado com múltiplos livros
        # Vamos usar o primeiro livro como referência e adicionar observação com todos os títulos
        livro_ids = [str(item['livro_id']) for item in itens]
        titulos = [item['titulo'] for item in itens]
        
        observacao = f"PEDIDO CONSOLIDADO - {quantidade} livro(s): " + ", ".join(titulos)
        
        cursor = con.cursor()
        cursor.execute(
            """INSERT INTO pedidos (email, livro_id, usuario_id, status, observacao) 
               VALUES (?, ?, ?, ?, ?)""",
            (email, itens[0]['livro_id'], usuario_id, 'PENDENTE', observacao)
        )
        pedido_id = cursor.lastrowid
        con.commit()
        
        # Gerar PIX
        valor_str = f"{total:.2f}"
        texto_pix = f"00020126580014BR.GOV.BCB.PIX0136{email}520400005303986540{valor_str}5802BR5911ClicLeitura6009Sao_Paulo62070503***6304"
        
        img = qrcode.make(texto_pix)
        buf = BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        cursor.execute("UPDATE pedidos SET pix_code=? WHERE id=?", 
                      (f"SIMULADO_{pedido_id}", pedido_id))
        con.commit()
        
        # Limpar carrinho
        con.execute("DELETE FROM carrinho WHERE usuario_id=?", (usuario_id,))
        con.commit()
        con.close()
        
        print(f"✅ Pedido consolidado #{pedido_id} criado - {quantidade} livro(s) - Total: R$ {total:.2f}")
        
        return jsonify({
            'pedido_id': pedido_id,
            'qr_base64': qr_b64,
            'pix_text': texto_pix,
            'total': total,
            'quantidade': quantidade,
            'livros': titulos
        })
        
    except Exception as e:
        con.close()
        print(f"❌ Erro ao finalizar compra com PIX: {str(e)}")
        return jsonify({'error': f'Erro ao gerar pagamento PIX: {str(e)}'}), 500


@app.route('/api/pedido/<int:pedido_id>/confirmar-pix', methods=['POST'])
def api_confirmar_pagamento_pix(pedido_id):
    """Marca o pedido como aguardando aprovação após confirmação de pagamento"""
    con = conectar()
    try:
        # Verificar se pedido existe
        pedido = con.execute("SELECT id, status FROM pedidos WHERE id=?", (pedido_id,)).fetchone()
        
        if not pedido:
            con.close()
            return jsonify({'error': 'Pedido não encontrado'}), 404
        
        # Atualizar status para PENDENTE_APROVACAO
        con.execute("UPDATE pedidos SET status=? WHERE id=?", 
                   ('PENDENTE_APROVACAO', pedido_id))
        con.commit()
        con.close()
        
        print(f"✅ Pagamento PIX confirmado para pedido #{pedido_id} - Aguardando aprovação do admin")
        
        return jsonify({
            'ok': True,
            'message': 'Pagamento confirmado! Aguardando aprovação do administrador.',
            'pedido_id': pedido_id
        })
        
    except Exception as e:
        con.close()
        print(f"❌ Erro ao confirmar pagamento PIX: {str(e)}")
        return jsonify({'error': f'Erro ao confirmar pagamento: {str(e)}'}), 500


# --- ROTAS ADMINISTRATIVAS ---

def login_required(f):
    """Decorator para proteger rotas admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        # Debug
        print(f"\n🔍 DEBUG LOGIN:")
        print(f"   Email recebido: '{email}'")
        print(f"   Senha recebida: '{senha}'")
        
        if not email or not senha:
            return render_template('loginAdmin.html', error='Preencha todos os campos')
        
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        print(f"   Hash gerado: {senha_hash}")
        
        con = conectar()
        admin = con.execute("SELECT * FROM admins WHERE email=? AND senha_hash=?", 
                           (email, senha_hash)).fetchone()
        
        # Debug: verificar se encontrou
        if admin:
            print(f"   ✓ Admin encontrado: ID={admin['id']}")
        else:
            print(f"   ✗ Nenhum admin encontrado com esse email/senha")
            # Verificar se email existe
            check_email = con.execute("SELECT email FROM admins WHERE email=?", (email,)).fetchone()
            if check_email:
                print(f"   → Email existe no banco, mas senha incorreta")
            else:
                print(f"   → Email não existe no banco")
        
        con.close()
        
        if admin:
            session['admin_id'] = admin['id']
            session['admin_email'] = admin['email']
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('loginAdmin.html', error='E-mail ou senha inválidos')
    
    return render_template('loginAdmin.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    con = conectar()
    
    # Estatísticas básicas
    total_pedidos = con.execute("SELECT COUNT(*) as total FROM pedidos").fetchone()['total']
    pedidos_pagos = con.execute("SELECT COUNT(*) as total FROM pedidos WHERE status='PAGO'").fetchone()['total']
    pedidos_pendentes = con.execute("SELECT COUNT(*) as total FROM pedidos WHERE status='PENDENTE'").fetchone()['total']
    pedidos_aguardando_aprovacao = con.execute("SELECT COUNT(*) as total FROM pedidos WHERE status='PENDENTE_APROVACAO'").fetchone()['total']
    
    # Receita total
    receita = con.execute("""
        SELECT SUM(l.preco) as total 
        FROM pedidos p 
        LEFT JOIN livros l ON p.livro_id = l.id 
        WHERE p.status='PAGO' AND l.preco IS NOT NULL
    """).fetchone()
    receita_total = receita['total'] if receita['total'] else 0
    
    # Estatísticas do dashboard
    pedidos_hoje = con.execute("""
        SELECT COUNT(*) as total FROM pedidos 
        WHERE DATE(criado_em) = DATE('now')
    """).fetchone()['total']
    
    receita_hoje = con.execute("""
        SELECT SUM(l.preco) as total 
        FROM pedidos p 
        LEFT JOIN livros l ON p.livro_id = l.id 
        WHERE p.status='PAGO' AND DATE(p.criado_em) = DATE('now')
    """).fetchone()
    receita_hoje_valor = receita_hoje['total'] if receita_hoje['total'] else 0
    
    total_livros = con.execute("SELECT COUNT(*) as total FROM livros").fetchone()['total']
    total_clientes = con.execute("SELECT COUNT(*) as total FROM usuarios").fetchone()['total']
    
    # Livro mais vendido
    livro_mais_vendido = con.execute("""
        SELECT l.titulo, COUNT(*) as vendas
        FROM pedidos p
        JOIN livros l ON p.livro_id = l.id
        WHERE p.status = 'PAGO'
        GROUP BY l.titulo
        ORDER BY vendas DESC
        LIMIT 1
    """).fetchone()
    livro_mais_vendido_nome = livro_mais_vendido['titulo'][:50] if livro_mais_vendido else None
    
    # Clientes novos este mês
    clientes_mes = con.execute("""
        SELECT COUNT(*) as total FROM usuarios 
        WHERE strftime('%Y-%m', criado_em) = strftime('%Y-%m', 'now')
    """).fetchone()['total']
    
    # Últimos pedidos
    pedidos = con.execute("""
        SELECT 
            p.id,
            p.email,
            p.livro_id,
            p.status,
            p.criado_em,
            p.usuario_id,
            COALESCE(u.nome, 'Cliente não identificado') as nome_cliente,
            COALESCE(l.titulo, 'Livro não disponível (ID: ' || p.livro_id || ')') as titulo,
            COALESCE(l.preco, 0) as preco
        FROM pedidos p 
        LEFT JOIN livros l ON p.livro_id = l.id
        LEFT JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY p.criado_em DESC 
        LIMIT 50
    """).fetchall()
    
    # Todos os livros
    livros = con.execute("""
        SELECT id, titulo, autor, preco, imagem, origem
        FROM livros
        ORDER BY id DESC
    """).fetchall()
    
    # Clientes com estatísticas
    clientes = con.execute("""
        SELECT 
            u.id,
            u.nome,
            u.email,
            u.criado_em,
            COUNT(p.id) as total_compras,
            COALESCE(SUM(CASE WHEN p.status='PAGO' THEN l.preco ELSE 0 END), 0) as total_gasto
        FROM usuarios u
        LEFT JOIN pedidos p ON u.id = p.usuario_id
        LEFT JOIN livros l ON p.livro_id = l.id
        GROUP BY u.id, u.nome, u.email, u.criado_em
        ORDER BY total_gasto DESC
    """).fetchall()
    
    con.close()
    
    stats = {
        'total_pedidos': total_pedidos,
        'pedidos_pagos': pedidos_pagos,
        'pedidos_pendentes': pedidos_pendentes,
        'pedidos_aguardando_aprovacao': pedidos_aguardando_aprovacao,
        'receita_total': receita_total,
        'pedidos_hoje': pedidos_hoje,
        'receita_hoje': receita_hoje_valor,
        'total_livros': total_livros,
        'total_clientes': total_clientes,
        'livro_mais_vendido': livro_mais_vendido_nome,
        'clientes_mes': clientes_mes
    }
    
    return render_template('dashboard.html', 
                         admin_email=session['admin_email'],
                         stats=stats,
                         pedidos=pedidos,
                         livros=livros,
                         clientes=clientes)

@app.route('/admin/enviar-livro', methods=['POST'])
@login_required
def admin_enviar_livro():
    """Envia o livro manualmente via painel admin"""
    data = request.json
    pedido_id = data.get('pedido_id')
    
    if not pedido_id:
        return jsonify({'error': 'Pedido não informado'}), 400
    
    print(f"\n📤 Admin solicitou envio do pedido #{pedido_id}")
    
    # Usar a função auxiliar que já criamos
    sucesso = enviar_livro_email(pedido_id)
    
    if sucesso:
        return jsonify({'ok': True, 'message': 'Livro enviado com sucesso'})
    else:
        return jsonify({'error': 'Falha ao enviar o livro. Verifique os logs.'}), 500

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    return redirect(url_for('admin_login'))

@app.route('/api/admin/pedidos-pendentes')
@login_required
def listar_pedidos_pendentes():
    """Lista todos os pedidos aguardando aprovação do admin"""
    con = conectar()
    cur = con.cursor()
    
    pedidos = cur.execute("""
        SELECT p.id, p.criado_em, l.preco, p.status,
               u.nome as cliente_nome, u.email as cliente_email,
               l.titulo as livro_titulo, l.imagem as livro_capa
        FROM pedidos p
        JOIN usuarios u ON p.usuario_id = u.id
        JOIN livros l ON p.livro_id = l.id
        WHERE p.status = 'PENDENTE_APROVACAO'
        ORDER BY p.criado_em DESC
    """).fetchall()
    
    con.close()
    
    pedidos_lista = []
    for p in pedidos:
        pedidos_lista.append({
            'id': p[0],
            'data_pedido': p[1],
            'preco_final': p[2] if p[2] else 0,
            'status': p[3],
            'cliente_nome': p[4],
            'cliente_email': p[5],
            'livro_titulo': p[6],
            'livro_capa': p[7]
        })
    
    return jsonify({'ok': True, 'pedidos': pedidos_lista})

@app.route('/api/admin/aprovar/<int:pedido_id>', methods=['POST'])
@login_required
def aprovar_pedido(pedido_id):
    """Aprova pedido, envia o e-book e atualiza status para PAGO"""
    print(f"\n✅ Admin aprovando pedido #{pedido_id}...")
    
    # Enviar o e-book
    sucesso = enviar_livro_email(pedido_id)
    
    if sucesso:
        return jsonify({
            'ok': True, 
            'message': f'Pedido #{pedido_id} aprovado! E-book enviado ao cliente.'
        })
    else:
        return jsonify({
            'error': 'Falha ao enviar o e-book. Verifique os logs.'
        }), 500

@app.route('/api/admin/rejeitar/<int:pedido_id>', methods=['POST'])
@login_required
def rejeitar_pedido(pedido_id):
    """Rejeita pedido com motivo"""
    data = request.json
    motivo = data.get('motivo', 'Não especificado')
    
    print(f"\n❌ Admin rejeitando pedido #{pedido_id}. Motivo: {motivo}")
    
    con = conectar()
    
    # Verificar se a coluna observacao existe, caso não, adicioná-la
    try:
        con.execute("ALTER TABLE pedidos ADD COLUMN observacao TEXT")
        con.commit()
        print("✅ Coluna 'observacao' adicionada à tabela pedidos")
    except:
        pass  # Coluna já existe
    
    con.execute("UPDATE pedidos SET status=?, observacao=? WHERE id=?", 
                ('REJEITADO', motivo, pedido_id))
    con.commit()
    con.close()
    
    return jsonify({
        'ok': True, 
        'message': f'Pedido #{pedido_id} rejeitado.'
    })

if __name__ == '__main__':
    print("🚀 Servidor iniciando em http://localhost:5000")
    app.run(debug=True)
