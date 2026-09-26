# Quatro endpoints externos do MVP - Sprint: Arquitetura de Software



| Endpoint da FastAPI (POST) | Endpoint externo (GET) | Uso |

| --- | --- | --- |

| `/api/clientes/geocodificar` | Nominatim `/search` | Endereço para coordenadas |

| `/api/clientes/geocodificar-reverso` | Nominatim `/reverse` | Coordenadas para endereço próximo |

| `/api/rotas/calcular` | OSRM `/route/v1/driving/{coordenadas}` | Trajeto na ordem das entregas |

| `/api/rotas/matriz` | OSRM `/table/v1/driving/{coordenadas}` | Distâncias e tempos entre todos os pontos |



As URLs base continuam definidas por `NOMINATIM_URL` e `OSRM_URL`. São quatro

endpoints de dois serviços externos. As imagens do mapa são recursos adicionais.



## Usar na tela



Na aba **Rotas**, arraste o alvo do canto inferior direito até o local da entrega.

Ao soltar, o popup consulta o endereço automaticamente. Confira a referência, nome,

data e observações e clique em **Inserir entrega avulsa**. O ponto salvo é exatamente

onde o alvo foi solto, mesmo que o Nominatim retorne um objeto próximo. Sem resultado,

informe uma referência manualmente. Também é possível clicar no alvo e depois no mapa.



A entrega avulsa não exige cliente cadastrado. Entregas de hoje entram selecionadas

na lista de rotas; para outras datas, consulte a aba Entregas. Avulsas podem ser

editadas e excluídas nessa aba e participam de rotas e matrizes normalmente.



Selecione de 1 a 24 entregas e clique em **Comparar paradas**, abaixo do mapa.

A tabela inclui a empresa como primeiro ponto. Cada linha é uma origem e cada

coluna é um destino, com distância em quilômetros e duração em minutos.

“Sem trajeto” significa que o provedor não encontrou conexão. A matriz é descartada

quando a seleção ou os dados dos pontos mudam. Comparar não salva uma rota e não

otimiza nem altera a sequência das paradas.



## Testar pelo Swagger



Com o backend ativo, abra http://localhost:8001/docs (porta publicada pelo Compose

desta cópia do projeto). Escolha o endpoint, clique em **Try it out** e **Execute**.



Geocodificação reversa:



```json

{"latitude": -29.886, "longitude": -50.268}

```



Matriz (substitua pelos IDs reais das suas entregas):



```json

{"entrega_ids": [1, 2]}

```



A matriz mantém a ordem dos IDs recebidos e adiciona a empresa no início.

IDs duplicados, coordenadas inválidas, ausência da empresa ou entregas sem

coordenadas são rejeitados. Pontos sem conexão aparecem como `null` nas matrizes.

Erros de roteamento podem retornar 502 (resposta inválida), 503 (indisponibilidade), 504 (demora) ou 422 (trajeto/pontos inválidos). Endereço não encontrado retorna 404.



As consultas `/search` e `/reverse` compartilham cache limitado a 500 entradas e

intervalo mínimo de 1,05 segundo no processo do backend. Esse controle é local ao

processo; múltiplas réplicas exigem um limitador compartilhado. O cache se perde ao reiniciar.



## Atualizar o ambiente Docker



Na raiz do projeto, para desenvolvimento:



```powershell

docker compose -f compose.yaml -f compose.dev.yaml up -d --build

```



Para o build servido pelo Nginx:



```powershell

docker compose up -d --build

```



## Testes automatizados



Com as dependências do backend instaladas, execute na pasta `backend`:



```powershell

python -m unittest discover -s tests -v

```



Os testes usam um banco SQLite temporário e respostas HTTP simuladas, sem alterar

o MySQL ou consumir cotas dos provedores.



Referências: [Nominatim Reverse](https://nominatim.org/release-docs/latest/api/Reverse/)

e [OSRM Table](https://project-osrm.org/docs/v5.24.0/api/#table-service).







## Endpoints de entregas avulsas



- `POST /api/entregas/avulsas`: cria sem cliente, retorna 201 e `avulsa: true`.

- `PUT /api/entregas/avulsas/{entrega_id}`: edita os dados e invalida rotas vinculadas.

- `GET /api/entregas`: lista entregas de clientes e avulsas.

- `DELETE /api/entregas/{entrega_id}`: exclui também os dados avulsos e rotas vinculadas.



Exemplo de criação (ajuste a data):



```json

{"nome":"Entrega avulsa","endereco":"Avenida Paulista, São Paulo, SP","latitude":-23.5614,"longitude":-46.6559,"data_prevista":"2026-09-18","request_id":"7c5ab7c5-6df9-4cf6-b5f1-88b7617b8f50"}

```



Use o mesmo request_id para repetir uma tentativa com o mesmo conteúdo sem duplicar

cadastros. Reutilizar com conteúdo diferente retorna 409. O campo é opcional no Swagger;

quando omitido, um novo UUID é gerado. Nome/referência em branco e coordenadas inválidas

retornam 422. A resposta mantém cliente_id e endereco_id nulos para avulsas.



### Banco existente



A inicialização cria a tabela `entregas_avulsas` e torna `cliente_id` e `endereco_id`

nullable na tabela `entregas` do MySQL. A migração em `app/migrations.py` é idempotente,

preserva os registros e mantém as chaves estrangeiras. O usuário do banco precisa

ter permissão ALTER. O schema.sql foi atualizado para instalações novas.



## Falhas de cálculo e gravação de rotas

O backend interpreta os códigos OSRM mesmo quando a resposta HTTP indica erro.
`NoRoute` significa trajeto não encontrado; `NoSegment`, ponto sem associação com
uma via; `TooBig`, consulta acima do limite do provedor. Demora retorna HTTP 504,
indisponibilidade ou excesso de chamadas retorna 503, e respostas inválidas retornam 502.
O envelope `detail` contém `codigo`, `mensagem`, `orientacao` e `tentar_novamente`.
Mensagens técnicas brutas do provedor e detalhes SQL não são mostrados ao usuário.

Falhas de persistência são revertidas e retornam 500 / `PersistenceError`, com uma
mensagem que distingue o cálculo da gravação. O modelo utiliza LONGTEXT no MySQL
para `rotas.geometria_geojson`; a migração automática amplia campos antigos do tipo
TEXT, preservando os registros. Isso corrige erros de armazenamento de trajetos
com mais de 65 KB de geometria.

A tela limpa o trajeto anterior ao iniciar uma nova tentativa, impede cliques
repetidos durante o cálculo e apresenta o erro próximo ao botão Calcular rota.


## Cadastro, custo e condições de uso

Os endpoints públicos configurados são consultados sem login, cadastro obrigatório
ou chave de API. Não há pagamento configurado neste MVP; isso não representa
garantia de disponibilidade ou direito a uso ilimitado.

### Nominatim

Base: https://nominatim.openstreetmap.org. Usamos GET /search e GET /reverse.
A política do servidor público exige identificação da aplicação, atribuição,
cache e no máximo 1 requisição por segundo no total da aplicação. Não é permitido
autocomplete nem consultas sistemáticas. Este MVP consulta por ação do usuário,
identifica o User-Agent e espaça as consultas no único processo do backend.
Não envie dados pessoais/confidenciais; na demonstração utilize locais públicos.
O endereço base é configurável por NOMINATIM_URL.

Fonte: https://operations.osmfoundation.org/policies/nominatim/

### OSRM

Base: https://router.project-osrm.org. Usamos GET /route/v1/driving/{coordenadas}
e GET /table/v1/driving/{coordenadas}. É um servidor demonstrativo; não há garantia
de serviço. Evite uso excessivo e identifique a aplicação. OSRM_URL permite
trocar de instância. O software OSRM tem licença BSD de duas cláusulas, distinta
da licença dos dados cartográficos e das condições de acesso ao servidor.

Fontes:
https://github.com/Project-OSRM/osrm-backend/blob/master/LICENSE.TXT
https://github.com/Project-OSRM/osrm-backend/wiki/Api-usage-policy

### Dados e recursos do mapa

Os dados OpenStreetMap são disponibilizados sob ODbL, com atribuição aos
contribuidores e obrigações de compartilhamento nos casos previstos pela licença.
A interface inclui atribuição e link para a página de direitos.
Tiles são recursos de exibição do navegador, separados dos quatro endpoints
funcionais. Cadastro de clientes e persistência são responsabilidade da API própria.

Fontes:
https://www.openstreetmap.org/copyright
https://operations.osmfoundation.org/policies/tiles/

Não há redirecionamento para consumir as APIs: a FastAPI recebe e trata o JSON.
Links de referência e Swagger são recursos de documentação.
