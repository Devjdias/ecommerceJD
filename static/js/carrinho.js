// Função para atualizar o contador do carrinho
async function atualizarContadorCarrinho() {
    const usuario = JSON.parse(localStorage.getItem('usuario') || 'null');
    const countBadge = document.getElementById('carrinhoCount');
    
    if (!countBadge) return;
    
    if (!usuario) {
        countBadge.style.display = 'none';
        return;
    }

    try {
        // Tentar carregar do servidor
        const response = await fetch(`/api/carrinho/${usuario.id}`);
        if (response.ok) {
            const data = await response.json();
            const quantidade = data.itens ? data.itens.length : 0;
            
            if (quantidade > 0) {
                countBadge.style.display = 'flex';
                countBadge.textContent = quantidade;
            } else {
                countBadge.style.display = 'none';
            }
        } else {
            // Fallback para localStorage se a API falhar
            usarCarrinhoLocal(usuario.id, countBadge);
        }
    } catch (error) {
        // Fallback para localStorage em caso de erro
        usarCarrinhoLocal(usuario.id, countBadge);
    }
}

// Função auxiliar para usar o carrinho do localStorage
function usarCarrinhoLocal(usuarioId, countBadge) {
    const carrinho = JSON.parse(localStorage.getItem(`carrinho_${usuarioId}`) || '[]');
    
    if (carrinho.length > 0) {
        countBadge.style.display = 'flex';
        countBadge.textContent = carrinho.length;
    } else {
        countBadge.style.display = 'none';
    }
}

// Atualizar contador ao carregar a página
window.addEventListener('DOMContentLoaded', atualizarContadorCarrinho);

// Permitir atualização manual do contador
window.atualizarContadorCarrinho = atualizarContadorCarrinho;
