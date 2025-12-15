// Funções compartilhadas do carrinho para todas as páginas

let usuarioLogado = null;

// Inicializar ao carregar a página
document.addEventListener('DOMContentLoaded', () => {
    usuarioLogado = JSON.parse(localStorage.getItem('usuario') || 'null');
    
    if (usuarioLogado) {
        carregarCarrinho();
    }
    
    // Adicionar evento ao ícone do carrinho
    const carrinhoIcon = document.getElementById('carrinhoIcon');
    if (carrinhoIcon) {
        carrinhoIcon.addEventListener('click', abrirCarrinho);
    }
    
    // Fechar modal ao clicar fora
    const carrinhoModal = document.getElementById('carrinhoModal');
    if (carrinhoModal) {
        carrinhoModal.addEventListener('click', (e) => {
            if (e.target.id === 'carrinhoModal') {
                fecharCarrinho();
            }
        });
    }
});

async function carregarCarrinho() {
    if (!usuarioLogado) return;

    try {
        const response = await fetch(`/api/carrinho/${usuarioLogado.id}`);
        const data = await response.json();

        if (response.ok) {
            atualizarCarrinhoUI(data.itens, data.total);
        }
    } catch (error) {
        console.error('Erro ao carregar carrinho:', error);
    }
}

function atualizarCarrinhoUI(itens, total) {
    const countBadge = document.getElementById('carrinhoCount');
    const itensContainer = document.getElementById('carrinhoItens');
    const totalElement = document.getElementById('carrinhoTotal');

    if (!countBadge || !itensContainer || !totalElement) return;

    // Atualizar badge de contagem
    if (itens.length > 0) {
        countBadge.style.display = 'flex';
        countBadge.textContent = itens.length;
    } else {
        countBadge.style.display = 'none';
    }

    // Atualizar total
    totalElement.textContent = `R$ ${total.toFixed(2)}`;

    // Atualizar lista de itens
    if (itens.length === 0) {
        itensContainer.innerHTML = `
            <div class="carrinho-vazio">
                <i class="fas fa-shopping-cart"></i>
                <h3>Carrinho Vazio</h3>
                <p>Adicione livros ao seu carrinho para começar!</p>
            </div>
        `;
    } else {
        itensContainer.innerHTML = itens.map(item => `
            <div class="carrinho-item">
                <img src="${item.imagem.startsWith('http') ? item.imagem : '/static/images/' + item.imagem}" 
                     alt="${item.titulo}" 
                     onerror="this.src='/static/images/default-book.jpg'">
                <div class="carrinho-item-info">
                    <h4>${item.titulo.substring(0, 50)}${item.titulo.length > 50 ? '...' : ''}</h4>
                    <p>${item.autor}</p>
                    <p class="carrinho-item-preco">R$ ${item.preco.toFixed(2)}</p>
                </div>
                <button class="carrinho-item-remover" onclick="removerDoCarrinho(${item.id})" title="Remover">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }
}

async function removerDoCarrinho(itemId) {
    try {
        const response = await fetch(`/api/carrinho/remover/${itemId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            carregarCarrinho();
        } else {
            alert(data.error || 'Erro ao remover item');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao conectar com o servidor');
    }
}

function abrirCarrinho() {
    if (!usuarioLogado) {
        alert('Você precisa fazer login para ver o carrinho!');
        window.location.href = '/login';
        return;
    }
    const modal = document.getElementById('carrinhoModal');
    if (modal) {
        modal.classList.add('show');
        modal.style.display = 'flex';
    }
}

function fecharCarrinho() {
    const modal = document.getElementById('carrinhoModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
    }
}

async function fecharPedidoEPagarComPix() {
    if (!usuarioLogado) {
        alert('Faça login para continuar!');
        return;
    }

    try {
        const response = await fetch(`/api/carrinho/${usuarioLogado.id}`);
        const data = await response.json();

        if (!response.ok || data.itens.length === 0) {
            alert('Seu carrinho está vazio!');
            return;
        }

        // Criar pedidos e gerar PIX
        const responseFinalizacao = await fetch('/api/carrinho/finalizar-pix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                usuario_id: usuarioLogado.id,
                email: usuarioLogado.email
            })
        });

        const resultado = await responseFinalizacao.json();

        if (responseFinalizacao.ok) {
            // Exibir modal com QR Code PIX
            mostrarModalPix(resultado);
            fecharCarrinho();
            carregarCarrinho();
        } else {
            alert(resultado.error || 'Erro ao gerar pagamento PIX');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao conectar com o servidor');
    }
}

function mostrarModalPix(dados) {
    const pixInfo = document.getElementById('pixInfo');
    if (!pixInfo) {
        alert('Erro: Modal PIX não encontrado!');
        return;
    }

    let html = `
        <div style="margin-bottom: 2rem;">
            <h3 style="color: #702727; margin-bottom: 1rem;">Pedido #${dados.pedido_id} criado!</h3>
            <p style="font-size: 1.4rem; color: #555;">Total: <strong style="color: #702727;">R$ ${dados.total.toFixed(2)}</strong></p>
            <p style="font-size: 1.3rem; color: #777; margin-top: 0.5rem;">${dados.quantidade} livro(s)</p>
        </div>

        <div style="background: #f8f8f8; padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
            <img src="data:image/png;base64,${dados.qr_base64}" 
                 alt="QR Code PIX" 
                 style="max-width: 300px; width: 100%; margin: 0 auto; display: block;" />
        </div>

        <div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem;">
            <p style="font-size: 1.3rem; font-weight: bold; color: #856404; margin-bottom: 1rem;">
                <i class="fas fa-copy"></i> Código PIX Copia e Cola:
            </p>
            <div style="background: white; padding: 1rem; border-radius: 5px; font-family: monospace; font-size: 1.1rem; word-break: break-all; color: #333; margin-bottom: 1rem;">
                ${dados.pix_text}
            </div>
            <button onclick="copiarCodigoPix('${dados.pix_text}')" 
                    style="background: #702727; color: white; border: none; padding: 1rem 2rem; border-radius: 5px; cursor: pointer; font-size: 1.4rem; width: 100%;">
                <i class="fas fa-copy"></i> Copiar Código PIX
            </button>
        </div>

        <div style="background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 1.5rem; border-radius: 5px; margin-bottom: 2rem;">
            <p style="font-size: 1.3rem; color: #0c5460; margin: 0;">
                <i class="fas fa-info-circle"></i> <strong>Importante:</strong><br/>
                Após o pagamento, seu pedido será enviado para aprovação do administrador.
                Você receberá seu(s) e-book(s) por email após a aprovação.
            </p>
        </div>

        <button onclick="confirmarPagamentoPix(${dados.pedido_id})" 
                style="background: #28a745; color: white; border: none; padding: 1.2rem 2rem; border-radius: 5px; cursor: pointer; font-size: 1.5rem; width: 100%; margin-bottom: 1rem;">
            <i class="fas fa-check-circle"></i> Pagamento Efetuado
        </button>

        <button onclick="fecharPixModal()" 
                style="background: #6c757d; color: white; border: none; padding: 1rem 2rem; border-radius: 5px; cursor: pointer; font-size: 1.4rem; width: 100%;">
            Fechar
        </button>
    `;

    pixInfo.innerHTML = html;
    document.getElementById('pixModal').style.display = 'flex';
}

function copiarCodigoPix(codigo) {
    navigator.clipboard.writeText(codigo).then(() => {
        alert('✅ Código PIX copiado! Cole no seu aplicativo bancário.');
    }).catch(() => {
        alert('❌ Erro ao copiar. Tente selecionar e copiar manualmente.');
    });
}

async function confirmarPagamentoPix(pedidoId) {
    try {
        const response = await fetch('/api/confirmar-pagamento-pix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pedido_id: pedidoId })
        });

        const data = await response.json();

        if (response.ok) {
            alert('✅ ' + data.message);
            fecharPixModal();
            window.location.href = '/perfil';
        } else {
            alert('❌ ' + data.error);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao conectar com o servidor');
    }
}

function fecharPixModal() {
    const modal = document.getElementById('pixModal');
    if (modal) {
        modal.style.display = 'none';
    }
}
