# 📱 Guia de Responsividade Mobile - Pet Shop Pro

## 🎯 Visão Geral

O sistema foi adaptado para funcionar perfeitamente em dispositivos móveis (smartphones e tablets). Este guia explica as melhorias implementadas e como utilizar os componentes responsivos.

---

## ✨ Melhorias Implementadas

### 1. Layout Responsivo

- **Menu Hamburguer Mobile**: Menu lateral se transforma em overlay em telas pequenas
- **Sidebar Adaptativa**: 
  - Desktop: sidebar fixa com toggle para expandir/recolher
  - Mobile: sidebar em overlay que desliza da esquerda
- **Header Mobile**: Informações do usuário otimizadas para telas pequenas
- **Backdrop**: Fundo escuro ao abrir menu mobile (fechar tocando fora)
- **Auto-close**: Menu fecha automaticamente ao clicar em um item

### 2. Componentes Responsivos Criados

#### 📊 ResponsiveTable
Wrapper para tabelas com scroll horizontal automático em mobile.

```jsx
import ResponsiveTable from '../components/ResponsiveTable';

<ResponsiveTable>
  <table className="min-w-full divide-y divide-gray-200">
    <thead>...</thead>
    <tbody>...</tbody>
  </table>
</ResponsiveTable>
```

#### 🃏 MobileCard
Alternativa a tabelas em mobile - exibe dados em formato de card.

```jsx
import MobileCard from '../components/MobileCard';

<MobileCard 
  title="João Silva"
  subtitle="Cliente desde 2024"
  items={[
    { label: 'Email', value: 'joao@email.com' },
    { label: 'Telefone', value: '(11) 99999-9999' },
    { label: 'CPF', value: '123.456.789-00' }
  ]}
  actions={
    <>
      <button>Editar</button>
      <button>Excluir</button>
    </>
  }
  onClick={() => console.log('Card clicado')}
/>
```

#### 📐 ResponsiveGrid
Grid que se adapta automaticamente ao tamanho da tela.

```jsx
import ResponsiveGrid, { FormGroup } from '../components/ResponsiveGrid';

<ResponsiveGrid cols={2} gap="md">
  <FormGroup label="Nome" required>
    <input type="text" />
  </FormGroup>
  
  <FormGroup label="Email" required>
    <input type="email" />
  </FormGroup>
</ResponsiveGrid>
```

#### 📝 ResponsiveForm
Container de formulário com espaçamento responsivo.

```jsx
import { ResponsiveForm, FormActions } from '../components/ResponsiveGrid';

<ResponsiveForm onSubmit={handleSubmit}>
  {/* campos do formulário */}
  
  <FormActions align="right">
    <button type="button">Cancelar</button>
    <button type="submit">Salvar</button>
  </FormActions>
</ResponsiveForm>
```

#### 🔖 ResponsiveTabs
Abas responsivas com scroll horizontal em mobile.

```jsx
import ResponsiveTabs, { TabContent } from '../components/ResponsiveTabs';

function MeuComponente() {
  const [activeTab, setActiveTab] = useState('dados');
  
  return (
    <>
      <ResponsiveTabs
        tabs={[
          { id: 'dados', label: '📋 Dados', count: null },
          { id: 'imagens', label: '🖼️ Imagens', count: 5 },
          { id: 'config', label: '⚙️ Config', count: null }
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />
      
      {activeTab === 'dados' && (
        <TabContent>
          {/* conteúdo da aba */}
        </TabContent>
      )}
    </>
  );
}
```

### 3. Hooks Customizados

#### useIsMobile
Hook para detectar se está em dispositivo móvel.

```jsx
import { useIsMobile, useDeviceType } from '../hooks/useIsMobile';

function MeuComponente() {
  const isMobile = useIsMobile(); // true se < 768px
  const isMobileXL = useIsMobile(1024); // breakpoint customizado
  const deviceType = useDeviceType(); // 'mobile', 'tablet' ou 'desktop'
  
  return (
    <div>
      {isMobile ? (
        <MobileCard {...props} />
      ) : (
        <ResponsiveTable>...</ResponsiveTable>
      )}
    </div>
  );
}
```

---

## 📱 Breakpoints do Sistema

- **Mobile**: `< 768px` (smartphones)
- **Tablet**: `768px - 1024px` (tablets)
- **Desktop**: `> 1024px` (computadores)

---

## 🎨 Classes CSS Responsivas Disponíveis

### Tailwind Responsive Prefixes

```jsx
// Exemplo de uso
<div className="
  w-full          // 100% sempre
  md:w-1/2        // 50% em telas médias+
  lg:w-1/3        // 33% em telas grandes+
  
  p-3             // padding 12px sempre
  md:p-6          // padding 24px em médias+
  
  text-sm         // texto pequeno sempre
  md:text-base    // texto normal em médias+
">
  Conteúdo responsivo
</div>
```

### Classes Utilitárias Customizadas

O `index.css` já possui media queries para elementos comuns:

- Tabelas com scroll horizontal automático
- Botões com tamanho mínimo tocável (44px)
- Inputs com tamanho de fonte otimizado (previne zoom no iOS)
- Grids convertidos para 1 coluna em mobile
- Modais em fullscreen em mobile

---

## ✅ Checklist de Responsividade

Ao criar uma nova página, garanta:

- [ ] Usar `ResponsiveGrid` para layouts de formulários
- [ ] Envolver tabelas com `ResponsiveTable`
- [ ] Considerar `MobileCard` como alternativa a tabelas em mobile
- [ ] Testar em diferentes resoluções (Chrome DevTools)
- [ ] Verificar se botões têm tamanho mínimo de 44px
- [ ] Garantir que inputs não causem zoom no iOS (font-size mínimo 16px)
- [ ] Usar classes Tailwind responsivas (`md:`, `lg:`, etc)

---

## 🧪 Como Testar

### No Chrome DevTools:

1. Pressione `F12` para abrir DevTools
2. Clique no ícone de dispositivos móveis (ou `Ctrl+Shift+M`)
3. Teste em diferentes resoluções:
   - iPhone SE (375px)
   - iPhone 12 Pro (390px)
   - iPad (768px)
   - iPad Pro (1024px)
4. Teste orientação paisagem e retrato
5. Teste o menu mobile (abrir, fechar, clicar em itens)

---

## 🚀 Exemplo Completo

```jsx
import { useState } from 'react';
import { useIsMobile } from '../hooks/useIsMobile';
import ResponsiveTable from '../components/ResponsiveTable';
import MobileCard from '../components/MobileCard';
import ResponsiveGrid, { ResponsiveForm, FormGroup, FormActions } from '../components/ResponsiveGrid';

function MinhaLista() {
  const isMobile = useIsMobile();
  const [dados, setDados] = useState([]);
  
  return (
    <div>
      <h1 className="text-xl md:text-2xl font-bold mb-4">
        Minha Lista
      </h1>
      
      {/* Formulário Responsivo */}
      <ResponsiveForm onSubmit={handleSubmit}>
        <ResponsiveGrid cols={3}>
          <FormGroup label="Nome" required>
            <input type="text" className="w-full" />
          </FormGroup>
          
          <FormGroup label="Email" required>
            <input type="email" className="w-full" />
          </FormGroup>
          
          <FormGroup label="Telefone">
            <input type="tel" className="w-full" />
          </FormGroup>
        </ResponsiveGrid>
        
        <FormActions>
          <button type="button">Cancelar</button>
          <button type="submit">Salvar</button>
        </FormActions>
      </ResponsiveForm>
      
      {/* Tabela/Cards Responsivos */}
      {isMobile ? (
        // Mobile: Cards
        <div className="mt-6">
          {dados.map(item => (
            <MobileCard
              key={item.id}
              title={item.nome}
              items={[
                { label: 'Email', value: item.email },
                { label: 'Telefone', value: item.telefone }
              ]}
              actions={
                <>
                  <button>Editar</button>
                  <button>Excluir</button>
                </>
              }
            />
          ))}
        </div>
      ) : (
        // Desktop: Tabela
        <ResponsiveTable className="mt-6">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Email</th>
                <th>Telefone</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {dados.map(item => (
                <tr key={item.id}>
                  <td>{item.nome}</td>
                  <td>{item.email}</td>
                  <td>{item.telefone}</td>
                  <td>
                    <button>Editar</button>
                    <button>Excluir</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ResponsiveTable>
      )}
    </div>
  );
}
```

---

## 📚 Recursos Adicionais

- [Tailwind CSS - Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [MDN - Media Queries](https://developer.mozilla.org/pt-BR/docs/Web/CSS/Media_Queries)
- [Google - Mobile-Friendly Test](https://search.google.com/test/mobile-friendly)

---

## 🐛 Problemas Conhecidos e Soluções

### Calculadora em mobile
**Problema**: Calculadora flutuante difícil de usar em mobile, drag não funciona bem em touch  
**Solução**: 
- Calculadora fixada no topo direito em mobile (não arrasta)
- Modal fullscreen em mobile com botões maiores
- Desabilitado drag em telas < 768px

### Zoom no iOS ao focar input
**Solução**: Garantir `font-size: 16px` mínimo em inputs (já implementado no CSS global)

### Tabelas muito largas
**Solução**: Usar `ResponsiveTable` ou considerar `MobileCard` para mobile

### Abas (tabs) com muitos itens
**Problema**: Abas não cabem na tela em mobile  
**Solução**: 
- Scroll horizontal automático
- Usar componente `ResponsiveTabs`
- CSS customizado para nav.flex com abas

### Menu não fecha em mobile
**Solução**: Verificar se está usando `handleMenuClick` nos links do menu

---

## 🎯 Próximos Passos

- [ ] Testar em dispositivos reais (iOS e Android)
- [ ] Otimizar imagens para mobile (lazy loading)
- [ ] Implementar PWA (Progressive Web App)
- [ ] Adicionar touch gestures (swipe para abrir menu)
- [ ] Otimizar performance em mobile (code splitting)
- [x] ~~Adaptar calculadora para mobile~~ ✅ (18/02/2026)
- [x] ~~Tornar abas responsivas~~ ✅ (18/02/2026)

---

**Data de Atualização**: 18/02/2026  
**Versão**: 1.1.0  
**Última build**: index-1771387828651.js
