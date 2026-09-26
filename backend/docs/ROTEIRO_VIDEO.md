# Roteiro de apresentação - limite de 6 minutos

Meta: **5 minutos e 40 segundos**, com 20 segundos de margem.
O vídeo deve mostrar execução real, não apenas slides. Use dados fictícios.
A duração sugerida por etapa no PDF é orientativa; as cinco etapas são obrigatórias.

| Tempo | Etapa | O que mostrar e explicar |
| --- | --- | --- |
| 0:00–0:30 | 1. Objetivo | Problema: organizar entregas e trajetos a partir da empresa. Autor, curso e nome do MVP. |
| 0:30–1:15 | 2. Arquitetura | Imagem do README. React/Nginx, FastAPI, MySQL e dois provedores. HTTP/JSON e persistência. Mostre docker compose ps. |
| 1:15–1:55 | 3. API externa | Documentação: Nominatim search/reverse e OSRM route/table. Sem cadastro/chave nos endpoints usados, políticas, ODbL. Dados tratados na aplicação. |
| 1:55–3:25 | 4. API desenvolvida | Swagger com a API em Docker. Mostre as operações listadas abaixo, seus dados enviados e respostas. |
| 3:25–5:40 | 5. Interface | Cadastro, edição e exclusão de cliente; entregas; alvo; ordenar cards; calcular; matriz; lixeira; Ajuda e Documentação. Mostre as chamadas na aba Network. |

## Preparação e ordem de demonstração da API

Prepare as abas e exemplos antes de gravar; substitua IDs pelas respostas reais.
As 17 operações são:

1. GET /api/health.
2. POST /api/empresa/endereco e GET /api/empresa/endereco.
3. POST /api/clientes/geocodificar e POST /api/clientes/geocodificar-reverso.
4. POST /api/clientes, GET /api/clientes, PUT /api/clientes/{cliente_id}.
5. POST /api/entregas, GET /api/entregas, PUT /api/entregas/{entrega_id}.
6. POST /api/entregas/avulsas, PUT /api/entregas/avulsas/{entrega_id}.
7. POST /api/rotas/calcular e POST /api/rotas/matriz.
8. DELETE /api/entregas/{entrega_id} para remover as entregas de demonstração.
9. DELETE /api/clientes/{cliente_id}, após remover suas entregas.

O PDF pede interação com todas as rotas implementadas. Ensaie para mostrar
requisição/resposta de cada operação dentro do tempo, sem omitir etapas.
As APIs públicas podem demorar; não faça testes em massa ou chamadas simultâneas
ao Nominatim. Não apresente respostas simuladas como evidência de acesso real.

## Falas de apoio

- “Escolhi o cenário 1.1. Desenvolvi a interface e o backend; Nominatim e OSRM
  são componentes externos. O banco persiste os dados da aplicação.”
- “GET consulta, POST cadastra ou calcula, PUT edita e DELETE exclui.”
- “O backend consulta o provedor, trata sua resposta e devolve dados à interface.
  O usuário não é redirecionado para outra aplicação.”
- “O alvo cria entregas avulsas. A ordem dos cards define o percurso. A matriz
  compara os pontos, mas não otimiza automaticamente a sequência.”
- “As falhas apresentam motivo e orientação; o sistema diferencia não encontrar
  um trajeto de falhar ao gravar a rota.”

Antes do envio, revise áudio, legibilidade, cinco etapas, duração e links públicos.
