FROM nginx:1.27-alpine
COPY index.html /usr/share/nginx/html/index.html
# La imagen oficial procesa /etc/nginx/templates/*.template con envsubst y
# escribe el resultado en /etc/nginx/conf.d/ al arrancar.
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000
EXPOSE 80
