let pedidoAtual = null;
let usuarioLogado = null;

window.addEventListener('DOMContentLoaded', () => {
    const usuario = JSON.parse(localStorage.getItem('usuario') || 'null');
    usuarioLogado = usuario;
    const emailInput = document.getElementById('emailInput');

    if (usuario) {
        emailInput.value = usuario.email;
        emailInput.readOnly = true;
    }

    // Atualizar header
    const loginLink = document.getElementById('loginLink');
    const perfilLink = document.getElementById('perfilLink');
    const userInfo = document.getElementById('userInfo');
    const logoutBtn = document.getElementById('logoutBtn');

    if (usuario) {
        loginLink.style.display = 'none';
        perfilLink.style.display = 'inline';
        userInfo.style.display = 'inline';
        userInfo.textContent = `Olá, ${usuario.nome.split(' ')[0]}!`;
        logoutBtn.style.display = 'inline-block';

        logoutBtn.addEventListener('click', () => {
            if (confirm('Deseja sair?')) {
                localStorage.removeItem('usuario');
                location.reload();
            }
        });
    }
});

function fecharModal() {
    document.getElementById('modalLivro').classList.remove('active');
    setTimeout(() => {
        window.location.href = "/";
    }, 300);
}

function abrirModalCheckout() {
    const usuario = JSON.parse(localStorage.getItem('usuario') || 'null');

    if (!usuario) {
        alert('⚠️ Você precisa fazer login antes de comprar!');
        sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
        window.location.href = '/login';
        return;
    }

    document.getElementById('modalCheckout').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function fecharCheckoutModal() {
    document.getElementById('modalCheckout').classList.remove('active');
    document.body.style.overflow = 'auto';
    document.getElementById('qrContainer').classList.remove('active');
    document.getElementById('mensagemStatus').innerHTML = '';
}

function fecharModalSeForaConteudo(event) {
    if (event.target === event.currentTarget) {
        fecharCheckoutModal();
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        fecharCheckoutModal();
    }
});

async function adicionarAoCarrinho() {
    if (!usuarioLogado) {
        alert('⚠️ Você precisa fazer login para adicionar ao carrinho!');
        sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
        window.location.href = '/login';
        return;
    }

    // Pega o ID do livro da página (você precisa adicionar um data-attribute no HTML)
    const livroId = document.querySelector('[data-livro-id]').dataset.livroId;

    try {
        const response = await fetch('/api/carrinho/adicionar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                usuario_id: usuarioLogado.id,
                livro_id: livroId
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('✅ Livro adicionado ao carrinho!');
        } else {
            alert(data.error || 'Erro ao adicionar ao carrinho');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao conectar com o servidor');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const checkoutForm = document.getElementById('checkoutForm');
    
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const usuario = JSON.parse(localStorage.getItem('usuario') || 'null');

            if (!usuario) {
                alert('⚠️ Você precisa fazer login antes de comprar!');
                return;
            }

            const email = document.getElementById('emailInput').value;
            const livroId = document.querySelector('[data-livro-id]').dataset.livroId;

            try {
                const response = await fetch('/api/checkout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, livro_id: livroId, usuario_id: usuario.id })
                });

                const data = await response.json();

                if (response.ok) {
                    pedidoAtual = data.pedido_id;
                    document.getElementById('qrImage').src = 'data:image/png;base64,' + data.qr_base64;
                    document.getElementById('pixText').textContent = data.pix_text;
                    document.getElementById('qrContainer').classList.add('active');
                } else {
                    alert('Erro: ' + data.error);
                }
            } catch (error) {
                alert('Erro ao processar compra: ' + error.message);
            }
        });
    }
});

async function simularPagamento() {
    if (!pedidoAtual) {
        alert('Nenhum pedido em andamento!');
        return;
    }

    const statusDiv = document.getElementById('mensagemStatus');
    statusDiv.className = 'mensagem-sucesso';
    statusDiv.innerHTML = '🔄 Validando pagamento e enviando e-book...';

    try {
        const response = await fetch('/api/confirmar_pagamento', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pedido_id: pedidoAtual })
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.innerHTML = '✅ Pagamento confirmado! E-book enviado para seu e-mail!';

            setTimeout(() => {
                fecharCheckoutModal();
                window.location.href = '/';
            }, 3000);
        } else {
            statusDiv.className = 'mensagem-erro';
            statusDiv.innerHTML = '❌ Erro: ' + data.error;
        }
    } catch (error) {
        statusDiv.className = 'mensagem-erro';
        statusDiv.innerHTML = '❌ Erro ao confirmar pagamento: ' + error.message;
    }
}