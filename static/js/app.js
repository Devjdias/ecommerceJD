// ClicLeitura - Frontend JavaScript

// Função para carregar livros dinamicamente (alternativa ao Jinja2)
async function carregarLivrosDinamicamente() {
    try {
        const response = await fetch('/api/livros');
        const livros = await response.json();
        
        const container = document.querySelector('.produtos');
        if (!container) return;
        
        // Limpar container se necessário
        // container.innerHTML = '';
        
        // Renderizar cada livro (caso queira usar fetch em vez de Jinja2)
        livros.forEach(livro => {
            const card = criarCardLivro(livro);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Erro ao carregar livros:', error);
    }
}

// Criar card de livro
function criarCardLivro(livro) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
        <img src="/static/images/${livro.imagem}" alt="${livro.titulo}" />
        <h4>${livro.titulo}</h4>
        <p>Por ${livro.autor}</p>
        <h3>R$ ${livro.preco.toFixed(2)}</h3>
        <a href="/livro/${livro.id}">
            <button>Ver detalhes</button>
        </a>
    `;
    return card;
}

// Função para realizar checkout
async function realizarCheckout(livroId, email) {
    try {
        const response = await fetch('/api/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                livro_id: livroId,
                email: email
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            return data; // {pedido_id, qr_base64, pix_text}
        } else {
            throw new Error(data.error || 'Erro ao realizar checkout');
        }
    } catch (error) {
        console.error('Erro no checkout:', error);
        throw error;
    }
}

// Função para confirmar pagamento
async function confirmarPagamento(pedidoId) {
    try {
        const response = await fetch('/api/confirmar_pagamento', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pedido_id: pedidoId
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            return data; // {ok: true}
        } else {
            throw new Error(data.error || 'Erro ao confirmar pagamento');
        }
    } catch (error) {
        console.error('Erro ao confirmar pagamento:', error);
        throw error;
    }
}

// Função auxiliar para exibir mensagens ao usuário
function exibirMensagem(mensagem, tipo = 'info') {
    alert(mensagem); // Pode ser substituído por toast/modal mais elaborado
}

// Carregar conteúdo ao inicializar página
// document.addEventListener('DOMContentLoaded', () => {
//     // Descomente se quiser usar fetch em vez de Jinja2 server-side
//     // carregarLivrosDinamicamente();
// });
