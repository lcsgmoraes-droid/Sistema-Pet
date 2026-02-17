/**
 * 🔍 DIAGNÓSTICO DE AUTENTICAÇÃO - Frontend
 * 
 * Execute este script no console do navegador para diagnosticar problemas de autenticação.
 * 
 * Como usar:
 * 1. Abra DevTools (F12)
 * 2. Cole todo este código no Console
 * 3. Pressione Enter
 * 4. Copie o resultado e envie para análise
 */

(function diagnosticoAuth() {
  console.log('\n\n========================================');
  console.log('🔍 DIAGNÓSTICO DE AUTENTICAÇÃO');
  console.log('========================================\n');

  // 1. Verificar token no localStorage
  const token = localStorage.getItem('access_token');
  console.log('1️⃣ TOKEN NO LOCALSTORAGE:');
  console.log('   Existe:', !!token);
  
  if (token) {
    console.log('   Preview:', token.substring(0, 50) + '...');
    console.log('   Tamanho:', token.length, 'caracteres');
    
    // Tentar decodificar o token JWT
    try {
      const parts = token.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        console.log('   Payload decodificado:', payload);
        
        // Verificar expiração
        if (payload.exp) {
          const expDate = new Date(payload.exp * 1000);
          const now = new Date();
          const expired = expDate < now;
          
          console.log('   Expira em:', expDate.toLocaleString());
          console.log('   Status:', expired ? '❌ EXPIRADO' : '✅ VÁLIDO');
          
          if (expired) {
            const diffMinutes = Math.floor((now - expDate) / 1000 / 60);
            console.log('   Expirou há:', diffMinutes, 'minutos');
          } else {
            const diffMinutes = Math.floor((expDate - now) / 1000 / 60);
            console.log('   Expira em:', diffMinutes, 'minutos');
          }
        }
      }
    } catch (e) {
      console.warn('   ⚠️ Não foi possível decodificar o token:', e.message);
    }
  } else {
    console.log('   ❌ NENHUM TOKEN ENCONTRADO');
  }

  // 2. Verificar tenant
  console.log('\n2️⃣ TENANT:');
  const tenants = localStorage.getItem('tenants');
  console.log('   Tenants:', tenants);

  // 3. Verificar configuração do Axios
  console.log('\n3️⃣ CONFIGURAÇÃO DO AXIOS:');
  console.log('   VITE_API_URL:', import.meta.env.VITE_API_URL);
  console.log('   Modo:', import.meta.env.MODE);
  console.log('   Production:', import.meta.env.PROD);
  console.log('   Development:', import.meta.env.DEV);

  // 4. Testar requisição de teste
  console.log('\n4️⃣ TESTE DE REQUISIÇÃO:');
  console.log('   Tentando chamar /racoes/analises/opcoes-filtros...');
  
  const testUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000') + '/racoes/analises/opcoes-filtros';
  console.log('   URL completa:', testUrl);
  
  fetch(testUrl, {
    headers: {
      'Authorization': token ? `Bearer ${token}` : 'NO TOKEN',
      'Content-Type': 'application/json'
    }
  })
  .then(response => {
    console.log('\n   ✅ Resposta recebida:');
    console.log('   Status:', response.status, response.statusText);
    console.log('   Headers:', [...response.headers.entries()]);
    return response.json();
  })
  .then(data => {
    console.log('   Dados:', data);
  })
  .catch(error => {
    console.error('\n   ❌ Erro na requisição:');
    console.error('   ', error);
  });

  // 5. Verificar cookies
  console.log('\n5️⃣ COOKIES:');
  console.log('   ', document.cookie || 'Nenhum cookie');

  // 6. Verificar URL atual
  console.log('\n6️⃣ CONTEXTO:');
  console.log('   URL:', window.location.href);
  console.log('   Origin:', window.location.origin);
  console.log('   Pathname:', window.location.pathname);

  console.log('\n========================================');
  console.log('✅ DIAGNÓSTICO CONCLUÍDO');
  console.log('========================================\n\n');
})();
