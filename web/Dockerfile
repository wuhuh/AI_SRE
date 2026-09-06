FROM node:20-alpine AS build

WORKDIR /app
# P1-FE-01: 锁定依赖（npm ci 用 package-lock.json）+ 国内源（同 pip 镜像思路）
RUN npm config set registry https://registry.npmmirror.com
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]