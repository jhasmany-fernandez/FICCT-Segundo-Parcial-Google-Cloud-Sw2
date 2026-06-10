FROM node:22-bookworm

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY tsconfig.json ./
COPY src ./src

EXPOSE 8080

CMD ["npm", "run", "start"]
