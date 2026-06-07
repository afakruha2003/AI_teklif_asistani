FROM node:18-alpine

WORKDIR /app

# package.json'ı kopyala
COPY package*.json ./

# Bağımlılıkları yükle
RUN npm install

# Kaynak kodları kopyala
COPY . .

EXPOSE 5173

# Dev server'ı tüm network interface'lerinde dinle
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
