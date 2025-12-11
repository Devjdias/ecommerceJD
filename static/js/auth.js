// Verificar login em todas as páginas
window.addEventListener('DOMContentLoaded', () => {
    const usuario = JSON.parse(localStorage.getItem('usuario') || 'null');
    const loginLink = document.getElementById('loginLink');
    const perfilLink = document.getElementById('perfilLink');
    const userInfo = document.getElementById('userInfo');
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (usuario) {
        if (loginLink) loginLink.style.display = 'none';
        if (perfilLink) perfilLink.style.display = 'inline';
        if (userInfo) {
            userInfo.style.display = 'inline';
            userInfo.textContent = `Olá, ${usuario.nome.split(' ')[0]}!`;
        }
        if (logoutBtn) {
            logoutBtn.style.display = 'inline-block';
            
            logoutBtn.addEventListener('click', () => {
                if (confirm('Deseja sair?')) {
                    localStorage.removeItem('usuario');
                    window.location.href = '/';
                }
            });
        }
    }
});