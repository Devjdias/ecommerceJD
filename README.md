# ClicLeitura - E-commerce de E-books Gratuitos

E-commerce de e-books com **livros reais em PDF gratuitos** do Internet Archive e Project Gutenberg. Sistema completo com pagamento PIX simulado e entrega automática por e-mail.

## 📚 Características

- ✅ **Livros reais em PDF** baixados de APIs públicas
- ✅ **Catálogo dinâmico** renderizado do banco de dados
- ✅ **Checkout completo** com PIX simulado
- ✅ **Entrega automática** via e-mail com PDF anexado
- ✅ **Autenticação** de usuários (cadastro/login)
- ✅ **Frontend integrado** com Jinja2 + JavaScript

## 🚀 Setup Rápido

### 1. Instalar Dependências

```powershell
pip install -r requirements.txt
```

### 2. Configurar E-mail (Gmail)

Crie arquivo `.env` na raiz:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu_email@gmail.com
MAIL_PASSWORD=sua_senha_de_app_16_caracteres
```

**⚠️ Importante:** Use "Senha de App" do Gmail, não a senha normal:
1. Acesse https://myaccount.google.com/security
2. Ative verificação em 2 etapas
3. Gere "Senha de app" (16 caracteres)

### 3. Importar Livros de APIs Gratuitas

```powershell
# Opção 1: Script simples (Project Gutenberg)
python importar_livros_api.py

# Opção 2: Script completo (Internet Archive + Gutenberg)
python importar_livros_completo.py
```

Isso vai:
- Buscar livros gratuitos em PDF de APIs públicas
- Popular o banco `loja.db` automaticamente
- Inserir 10-25 livros com PDFs reais

### 4. Iniciar Servidor

```powershell
python app.py
```

Acesse: **http://localhost:5000**

## 📖 Fontes de Livros Gratuitos

### Internet Archive (archive.org)
- 30+ milhões de livros digitalizados
- PDFs em domínio público
- Categorias: programação, ciência, história, ficção

### Project Gutenberg (gutenberg.org)
- 70.000+ livros em domínio público
- Formato: PDF e EPUB
- Clássicos da literatura mundial

## 🎯 Como Funciona

### Fluxo de Compra:

1. **Catálogo**: Livros carregados do banco via API REST
2. **Detalhes**: Cliente clica em "Ver detalhes" de um livro
3. **Checkout**: Insere e-mail e clica em "Gerar PIX"
4. **QR Code**: Sistema gera QR code PIX simulado (base64)
5. **Pagamento**: Cliente clica em "Simular Pagamento"
6. **Download**: Sistema baixa PDF da URL remota (Internet Archive/Gutenberg)
7. **E-mail**: PDF anexado e enviado automaticamente via Flask-Mail

### Estrutura de Dados:

```sql
livros:
  - id, titulo, autor, preco
  - imagem (URL da capa)
  - pdf (URL do PDF no archive.org ou gutenberg.org)
  - origem ('archive.org', 'gutenberg.org')

pedidos:
  - id, email, livro_id, status (PENDENTE → PAGO)
  - pix_code, criado_em

usuarios:
  - id, nome, email, senha (texto plano - ⚠️ produção requer hash)
```

## 🔧 Comandos Úteis

### Verificar banco de dados:

```powershell
sqlite3 loja.db "SELECT titulo, autor, origem FROM livros LIMIT 5"
```

### Recriar banco do zero:

```powershell
Remove-Item loja.db -Force
python criar_banco.py
python importar_livros_completo.py
```

### Testar download de PDF:

```powershell
# Abrir Python interativo
python

# No console Python:
import requests
url = "https://archive.org/download/perltopythonmigr0000brow/perltopythonmigr0000brow.pdf"
r = requests.get(url, timeout=30)
print(f"Status: {r.status_code}, Size: {len(r.content)} bytes")
```

## 📁 Estrutura do Projeto

```
ecommerceOfic/
├── app.py                          # Flask backend
├── loja.db                         # SQLite database
├── requirements.txt                # Dependências Python
├── .env                            # Credenciais (não commitar!)
│
├── static/
│   ├── css/                        # Estilos CSS
│   ├── js/
│   │   └── app.js                  # Funções JS auxiliares
│   ├── images/                     # Imagens do site
│
└── templates/
    ├── index.html                  # Principal que direciona para as outras páginas
```

## 🐛 Troubleshooting

### E-mails não enviam
- Verificar credenciais em `.env`
- Usar senha de app do Gmail (16 caracteres)
- Testar com outro e-mail destinatário

### PDFs não chegam no e-mail
- Verificar se URL do PDF está acessível
- Timeout pode ocorrer com arquivos grandes (>10MB)
- Logs aparecem no terminal Flask

### Livros não aparecem
- Executar `python importar_livros_completo.py`
- Verificar banco: `sqlite3 loja.db "SELECT COUNT(*) FROM livros"`

### Imagens quebradas (404)
- Imagens das capas são URLs externas
- Algumas podem estar indisponíveis
- Adicionar fallback no CSS para `<img>` com erro

## 🚀 Próximos Passos (Produção)

- [ ] Hash de senhas com `bcrypt`
- [ ] Sessões Flask ou JWT para autenticação
- [ ] Proteção CSRF em formulários
- [ ] Migrar para PostgreSQL
- [ ] Integração PIX real (Mercado Pago, PagSeguru)
- [ ] Cache de PDFs baixados
- [ ] Fila de e-mails (Celery)
- [ ] Upload de capas personalizadas
- [ ] Sistema de carrinho de compras
- [ ] Histórico de compras do usuário

## 📜 Licença

Código: MIT License  
Livros: Domínio público (Internet Archive, Project Gutenberg)

## 🤝 APIs Utilizadas

- **Gutendex API**: https://gutendex.com/ (Project Gutenberg)
- **Internet Archive API**: https://archive.org/advancedsearch.php
- **Flask-Mail**: Envio de e-mails via SMTP
- **qrcode[pil]**: Geração de QR codes PIX

---
🔍 OPÇÕES PARA VISUALIZAR O BANCO:
1. Extensão do VS Code (RECOMENDADO) ⭐
Instale uma dessas extensões no VS Code para visualizar seu banco:
SQLite
SQLite Viewer
SQLite3 Editor

  Após instalar:
  Clique no arquivo loja.db no Explorer
  Ele abrirá automaticamente em uma visualização interativa
  Você verá todas as tabelas, poderá executar queries SQL, ver os dados, etc.

2. Via Terminal (Rápido) 💻
python -c "import sqlite3; import pandas as pd; con = sqlite3.connect('loja.db'); print('\n=== TABELA: LIVROS ===\n'); print(pd.read_sql_query('SELECT id, titulo, autor, preco FROM livros LIMIT 5', con)); print('\n=== TABELA: USUARIOS ===\n'); print(pd.read_sql_query('SELECT id, nome, email, criado_em FROM usuarios', con)); print('\n=== TABELA: PEDIDOS (últimos 5) ===\n'); print(pd.read_sql_query('SELECT id, email, status, criado_em FROM pedidos ORDER BY id DESC LIMIT 5', con)); con.close()"

3. Ferramenta Online 🌐
Acesse: https://sqliteonline.com/
Clique em "File" → "Open DB"
Selecione seu loja.db

4. DB Browser for SQLite (Aplicativo Desktop)
Download: https://sqlitebrowser.org/
Abra o arquivo loja.db
Interface gráfica completa
Recomendo instalar a extensão do VS Code - é a forma mais prática! 😊
_________________________________________________________________________
✅ Backend: Flask com 1211 linhas
✅ Banco de dados: 15 livros, 3 usuários, 47 pedidos
✅ Frontend: 12 páginas HTML + 14 arquivos CSS
✅ Funcionalidades: Carrinho, PIX, Admin, Perfil, FAQ, Contato
✅ Sistema de pagamento: PIX simulado funcionando
✅ Email: Envio automático de e-books
✅ Repositório: No GitHub (Devjdias/ecommerceJD)

**Desenvolvido com Flask + SQLite + APIs públicas de livros gratuitos** 📚
