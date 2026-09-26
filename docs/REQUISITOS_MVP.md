# Verificação dos requisitos do MVP

Referência: PDF fornecido pelo aluno, páginas 1 a 6.
Arquitetura adotada: **cenário 1.1**, interface → API própria → serviços externos;
API própria → MySQL. Esta análise não garante nota nem substitui a avaliação.

## Matriz de atendimento

| Critério do enunciado | Evidência no MVP | Situação |
| --- | --- | --- |
| Pelo menos 3 módulos e integração REST/GraphQL | React + FastAPI + Nominatim/OSRM; HTTP/JSON | Implementado |
| Persistência SQLite, MySQL ou PostgreSQL | SQLAlchemy/MySQL e volume mysql_data | Implementado |
| Interface consome GET, POST, PUT, DELETE (2,0) | CRUD de clientes em App.jsx, além de entregas | Implementado |
| README da interface, instalação e imagem (1,0) | frontend/README.md e public/arquitetura.svg | Preparado |
| Dockerfile da interface (1,0) | frontend/Dockerfile, build React + Nginx | Build e execução Docker validados |
| Criatividade/inovação (1,0) | Domínio logístico, alvo arrastável, avulsas, ordenação e matriz | Evidências presentes; avaliação qualitativa |
| API desenvolvida com pelo menos 4 rotas (2,0) | 17 operações HTTP no OpenAPI | Implementado |
| README próprio da API (0,5) | backend/README.md | Preparado |
| Dockerfile próprio da API (0,5) | backend/Dockerfile, Python/FastAPI | Build e execução Docker validados |
| Serviço externo público não pago (0,5) | Nominatim e OSRM, sem chave na integração atual | Integrado; sujeito às políticas dos provedores |
| Documentar APIs, licença, cadastro e rotas (0,5) | APIS_EXTERNAS.md e menu Documentação | Preparado |
| Sem redirecionamento no consumo externo | FastAPI trata o JSON; mapa e respostas na própria tela | Implementado |
| Compose na raiz da interface | frontend/compose.yaml | Validado com contextos frontend e backend separados |
| Dois repositórios públicos e organização (1,0) | frontend e backend com raízes independentes prontas | Publicação e URLs ainda pendentes |
| Vídeo de até 6 minutos, com as 5 etapas | ROTEIRO_VIDEO.md | Gravação, revisão e URL pendentes |

Os 4 endpoints externos são um recurso do projeto. O mínimo de 4 rotas do
enunciado se refere à API desenvolvida. Não é necessário criar outra API própria
para este cenário. O banco não é contado como API REST.

## Conferência antes do envio

- Executar a versão entregue com Docker, desde um banco vazio.
- Confirmar que frontend e backend possuem, cada um, README.md e Dockerfile na raiz.
- Publicar cada componente em um repositório GitHub público diferente.
- Testar os dois links em janela anônima e seguir o README após um clone novo.
- Confirmar que .env real, senhas e dados de clientes não foram publicados.
- Gravar as cinco etapas; demonstrar todas as operações da API, conforme o PDF.
- Conferir duração final até 6:00 e acesso ao vídeo.
- Enviar as URLs completas do vídeo e dos dois repositórios.

Se código das aulas foi utilizado, o aluno deve verificar a exigência de pelo
menos 50% de código novo. Não é possível atestar esse percentual sem as bases
fornecidas em aula. O funcionamento local não comprova publicação pública nem
a entrega do vídeo.


## Validação executada nesta revisão

- Imagens frontend (React/Nginx) e backend (Python) construídas pelos Dockerfiles.
- Compose da raiz do frontend iniciado com MySQL vazio em ambiente isolado,
  portas 18080 e 18001; serviços responderam aos healthchecks.
- 35 testes automatizados do backend aprovados dentro da imagem Docker.
- 17 operações HTTP exercitadas: CRUD, empresa, avulsas e quatro integrações.
- Nominatim respondeu às consultas reais; OSRM teve falha transitória de conexão,
  retornando erro tratado 503, e respondeu ao cálculo e à matriz na nova tentativa.
- Sequência das paradas da rota e dimensão 3 × 3 da matriz conferidas.
- Navegação de Ajuda e Documentação e carregamento do diagrama conferidos no navegador.
- Exportação dos dois componentes testada sem .env real ou dependências locais.

A validação comprova a execução local na data desta revisão, não a disponibilidade
futura dos provedores nem a publicação no GitHub. Não foi alterado o banco do
ambiente de trabalho para executar esses testes.
