# Publicação e entrega

## Dois repositórios públicos

A pasta geral de desenvolvimento não substitui os dois repositórios exigidos.
Publique **o conteúdo de frontend** como raiz do repositório da interface e
**o conteúdo de backend** como raiz do repositório da API.

Nomes sugeridos: mvp-arquitetura-frontend e mvp-arquitetura-backend.
Não há URLs confirmadas nesta documentação: informe o usuário GitHub e os
repositórios efetivamente criados antes de preencher a mensagem de entrega.

Cada raiz contém Dockerfile, README.md, .gitignore e código próprio.
O Compose é publicado na raiz do frontend. Para executar, clone a interface
como frontend e a API como backend, lado a lado; ou ajuste BACKEND_CONTEXT.

A ferramenta preparar-entrega.ps1 da pasta geral cria cópias limpas dos dois
componentes, sem .env real, node_modules, ambientes Python, caches ou bancos.
As cópias não são publicadas automaticamente e não incluem credenciais.

## Validação da publicação

1. Crie dois repositórios públicos na conta correta.
2. Envie cada componente para o seu repositório.
3. Confira README e imagem da arquitetura em ambos.
4. Abra os links sem autenticação.
5. Clone em diretório novo e execute as instruções do README da interface.
6. Registre os links verdadeiros abaixo e grave o vídeo.

## Mensagem de entrega para preencher

Olá, seguem os dados referentes à entrega do meu MVP - Sprint: Arquitetura de Software.

Vídeo: PREENCHER_URL_COMPLETA
Repositório da interface: PREENCHER_URL_COMPLETA
Repositório da API: PREENCHER_URL_COMPLETA

Serviços externos utilizados:
https://nominatim.openstreetmap.org
https://router.project-osrm.org

Cenário 1.1: interface React, API FastAPI, persistência MySQL e integração com
Nominatim/OSRM. As instruções e os Dockerfiles estão nos respectivos repositórios.
