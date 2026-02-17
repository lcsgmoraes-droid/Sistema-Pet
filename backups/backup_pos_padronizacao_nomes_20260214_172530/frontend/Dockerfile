# ============================================================================
# DOCKERFILE - FRONTEND (React + Vite)
# Sistema Pet Shop Pro - Interface Web
# ============================================================================

# Usar Node 18 como base
FROM node:18-alpine

# Definir diretório de trabalho
WORKDIR /app

# Copiar package.json e package-lock.json
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar todo o código da aplicação
COPY . .

# Expor porta 5173 (Vite dev server)
EXPOSE 5173

# Comando para rodar o Vite em modo desenvolvimento
# Usar --host para aceitar conexões externas
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
