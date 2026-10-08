# ZYRA — Contexto do projeto (TCC)

> Contexto compartilhado para sessões do Claude Code. Diagnóstico feito em 29/09/2026 a partir da branch `dev` dos três repositórios. Atualize este arquivo conforme o projeto evoluir.

## O projeto

ZYRA é um aplicativo mobile assistente de vestuário para pessoas com daltonismo. É o TCC de Ciência da Computação do Instituto Mauá de Tecnologia (IMT).

- **Autores:** Gustavo Coutinho Arruda (GitHub `guctn`) e Sophia Sissi Curcio Guedes
- **Orientadora:** Ana Claudia Melo Tiessi Gomes de Oliveira

**Problema:** pessoas daltônicas têm dificuldade para identificar cores e combinar roupas. Por isso dependem de terceiros, compram peças da cor errada e repetem combinações "seguras".

A validação com 14 participantes mostrou:
- 100% já pediram ajuda para identificar uma cor;
- 92,9% já compraram roupa achando que era de outra cor;
- 57,1% já deixaram de usar uma peça por medo de errar;
- 78,6% desistiriam do app se o cadastro manual fosse extenso.

Por isso, **baixo esforço de cadastro é requisito central**.

**Três núcleos funcionais:**
1. **Câmera inteligente:** identifica a cor em tempo real e mostra o nome textual e o símbolo **ColorADD** (sistema de Miguel Neiva, entrevistado pelos autores).
2. **Closet virtual:** peças cadastradas progressivamente, a partir de fotos.
3. **Assistente conversacional (IA):** sugere looks por ocasião ou estilo, usando só as peças do usuário.

**Acessibilidade:** a informação de cor nunca deve depender só da cor. Usar sempre nome textual + símbolo ColorADD + alto contraste (WCAG 2.2 e heurísticas de Nielsen).

## Repositórios

| Repo | Stack | Papel |
|---|---|---|
| `sophiasissi/imt-tcc-zyra` | Expo, React Native, TypeScript | App mobile |
| `sophiasissi/imt-tcc-zyra-back` | NestJS, Prisma 7, PostgreSQL, AWS Cognito | API central |
| `sophiasissi/imt-tcc-zyra-vision` | Python, FastAPI, OpenCV, CLIP, OpenAI | Visão computacional |

**Fluxo de Git:** `feature/*` ou `chore/*` → PR para `dev` (branch padrão) → `main`. A `main` é protegida e até agora só tem o commit inicial.

**Convenções:**
- Commits no formato convencional em português (`feat:`, `fix:`, `chore:`, `refactor:`).
- Textos para o usuário, valores de JSON e comentários em português.
- Identificadores de código em inglês no vision e mistos no back/app (ex.: `Usuario`, `cognitoSub`).

## Estado atual

### Back-end (`imt-tcc-zyra-back`)

**Pronto:**
- **Auth via Cognito** (`src/auth`), com as rotas:
  - `POST /auth/signup`, que já grava o perfil no banco com o `userSub`;
  - `confirm-signup`, `resend-code`, `login`, `refresh-token`, `logout`;
  - `forgot-password`, `confirm-forgot-password`;
  - `register-profile` (fallback caso o banco falhe no signup).
- **Guard `CognitoAuthGuard`:** valida o access token e injeta `req.user.cognitoSub`.
- **Perfil:** `GET/PATCH /users/me` (dataNascimento, genero, tipoDaltonismo, nivelDificuldadeLooks 0–5).
- **Erros:** mensagens amigáveis em português, mapeadas a partir dos erros do Cognito (`AuthService.handleCognitoError`).
- **Validação:** `ValidationPipe` global com `whitelist` e `forbidNonWhitelisted`.
- **Qualidade de código:** ESLint, Prettier (aspas simples, printWidth 100) e Husky com lint-staged.

**Schema Prisma:**
- Só o model `Usuario`: id uuid, cognitoSub único, nome, email único, dataNascimento, genero, tipoDaltonismo, nivelDificuldadeLooks e timestamps.
- Enums `Genero` e `TipoDaltonismo`.
- 3 migrations.
- O modelo antigo, com `senhaHash`, `telefone` e `ProvedorAutenticacao`, foi abandonado com a migração para o Cognito.

**Não existe ainda:** model de peça/closet, looks, integração com OpenAI e testes.

**Em andamento:** upload para o S3, numa branch da Sophia.

### Visão (`imt-tcc-zyra-vision`)

Para rodar: `uvicorn src.api.main:app --reload`. O `OPENAI_API_KEY` fica no `.env`.

**`POST /detect-color`** (`src/color_detection`):
1. Recorta o centro da imagem (`CROP_RATIO = 0.12`, alinhado à mira do app).
2. Roda k-means com 3 clusters para achar a cor dominante (a média daria cores falsas com sombra ou estampa).
3. Dá a família da cor pela tabela de nomes de cor de van de Weijer et al. (2009): Preto, Branco, Cinza, Vermelho (rosa vira Vermelho Claro), Laranja, Amarelo, Verde, Azul, Roxo e Castanho.
   - A tabela fica em `src/color_detection/data/w2c_nomes.npy`; a origem e a avaliação estão no `README.md` da mesma pasta.
   - Ela substituiu, em 04/10/2026, os limiares feitos à mão (matiz em LCh e croma < 12 = neutro). Na mira simulada com 39 fotos reais, a família certa subiu de 54% para 64%.
4. Aplica o tom (`_CLARO` / `_ESCURO`) em relação à cor base da família, detectando pastel. No cinza, o tom vem da luminosidade L*.

O retorno tem `colorName`, `hex`, `colorAddSymbol` (ex.: `COLORADD_AZUL_CLARO`), `rgb`, `confidence` e `warningCode` (`LOW_LIGHT`, `HIGH_LIGHT` ou `LOW_CONFIDENCE`).

**`POST /validate-clothing`** (`src/clothing_analysis/validate_clothing.py`):
- CLIP zero-shot (`openai/clip-vit-base-patch32`).
- Retorna `{isClothing, confidence, reason}`, com `reason` igual a `PERSON_DETECTED` ou `NOT_CLOTHING`.

**`POST /analyze-clothing`** (`src/clothing_analysis/analyze_clothing.py`):
- Usa o gpt-4o-mini (`temperature=0`, JSON) e parte do princípio de que a imagem já passou pelo `/validate-clothing`.
- Retorna `{category, style, pattern, fabric, occasion}`, com adjetivos sempre no masculino (ex.: `liso`).
- Imagem inválida ou truncada retorna 400 ("Imagem inválida").
- Ainda não é chamado pelo app (`visionApi.ts`).

**Imagens de teste:** ficam em `tests/images/`.

**Problemas conhecidos da cor** (avaliação de 04/10/2026, 39 fotos):
- verde-oliva e azul-marinho bem escuros saem como Cinza ou Preto, e branco na sombra sai como Cinza Claro. Nos pixels da foto, essas peças são quase neutras;
- cinza muito escuro tende a sair Preto.

O rosa claro (`#AD6B6D`), que saía Vermelho, passou a sair Vermelho Claro com a tabela de van de Weijer.

O conflito entre `feature/validate-clothing` e a `dev` foi resolvido no PR #6 (29/09/2026), mantendo o algoritmo de cor da `dev`.

### App (`imt-tcc-zyra`)

- **Navegação:** `src/navigation/AppNavigator.tsx`, com native stack e `RootStackParamList` tipado.
- **Serviços:**
  - `src/services/api.ts`: `apiRequest` com `ApiError` (status HTTP e erro de rede) e renovação automática do token em 401 via `setTokenRefresher`;
  - `visionApi.ts`: `detectColorFromImage` e `validateClothingFromImage`. **O app chama a visão direto, sem passar pelo back.**
- **Estado de autenticação:** `src/contexts/AuthContext.tsx`.
- **Símbolos:** `src/utils/colorAddSymbols.ts` mapeia `colorAddSymbol` → label + imagem.
- **Tema e componentes:** `src/styles/theme.ts`; componentes `ZyraButton`, `ZyraInput`, `ZyraPopup`, `OptionPill` e `AuthLayout`.
- **Variáveis de ambiente:** `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_VISION_API_URL`.

**Pronto:**
- Splash, Intro e cadastro em 7 etapas (com retomada de cadastro interrompido).
- Login, recuperação de senha, Settings, PersonalInfo, ChangePassword e Permissions.
- Home.
- `CameraColorDetectionScreen`: detecção a cada 800 ms, com símbolo ColorADD e avisos.
- Captura → validação de vestuário → `CapturedClothingScreen`.

**Placeholder ou mock:**
- Closet: o "Selecionar" na Home só loga.
- "Cadastrar nova peça" desabilitado na `CapturedClothingScreen`.
- Galeria na câmera.
- `ChatScreen` é uma demo: um `setTimeout` exibe um SVG fixo (`look_completo.svg`).
- Botão ColorADD da Home sem ação.

## Estado em 29/09/2026 (fim do dia)

**Divisão:** a Sophia faz o cadastro de peças de ponta a ponta (model `Peca`, S3, CRUD, telas). O Gustavo faz o chat de looks.

**Visão (mergeado na `dev`, PR #7):**
- `src/clothing_analysis/taxonomy.py` é a fonte da verdade dos valores de peça. O Prisma da Sophia deve espelhar essas listas:
  - categoria: CAMISETA, CAMISA, MOLETOM, JAQUETA, BLAZER, CALCA, SHORT, SAIA, VESTIDO, TENIS, SAPATO, BOLSA;
  - estilo, estampa e ocasião;
  - aquecimento: LEVE, MEDIO, QUENTE;
  - material: JEANS, COURO.
- O `/analyze-clothing` devolve esses códigos e descarta valores fora da lista. `occasions` é uma lista. `fabric` saiu e virou `warmth` + `material`.
- Boné e chapéu são recusados pelo `/validate-clothing`. (Em 04/10, bolsa e mochila também passaram a ser recusadas.)
- `tests/eval/`: avaliação do `/analyze-clothing` com fotos rotuladas.
  - Falta o Gustavo tirar ~40 fotos: ~70% com luz natural, sem filtro, e ~30% em condições ruins.
  - O CSV registra a cor real da peça e a condição de luz.

**Back (mergeado na `dev`, PR #16):**
- **`src/looks/interpretar-pedido.ts`:** a IA (gpt-4.1-mini, via `json_schema`) transforma a mensagem numa intenção:
  - campos: tipo, ocasião, formalidade, estilo, aquecimento, paletaNeutra, incluir, evitarCategorias, evitarCores e naoMapeado;
  - o prompt é o `PROMPT_SISTEMA`;
  - `ajustarIntencao` aplica correções determinísticas.
- **`npm run avaliar:intencoes -- --conjunto todos`:** mede o acerto.
  - `test/intencoes/desenvolvimento.json` tem 66 casos, usados para ajustar o prompt.
  - `validacao.json` tem 110 casos.
  - Resultado: 86% na validação às cegas; 91% depois dos ajustes em código. O gpt-4o-mini dava 55%.
- A chave `OPENAI_API_KEY` precisa entrar no `.env` do back.

**Decisões:**
- **A IA do chat não escreve texto.** Ela só devolve filtros e, quando necessário, uma pergunta curta. O motor escolhe o look, e o app monta a explicação por template, para economizar tokens.
- **Prompt:** encurtar prejudicou a qualidade, e regras extras no prompt pioraram outros casos. Correções em código funcionaram melhor.
- **Fora do escopo por enquanto:** avaliar combinação ("azul combina com verde?") e pares de cor arriscados por tipo de daltonismo.

## Estado em 04/10/2026 (fim do dia)

**Já na `dev`:**
- **Cadastro de peças da Sophia:** model `Peca` (guarda `imagemS3Key`; a API devolve uma URL assinada), CRUD `/pecas`, upload no S3, armário na Home e Expo SDK 57.
- **BOLSA removida** da taxonomia na visão, no back (com migration) e no app. Boné, chapéu, bolsa, mochila e gravata são recusados na validação.

**PRs abertos, aguardando revisão da Sophia** (ordem sugerida de merge):
1. **visão #10** `feature/analise-gpt-4.1-mini`:
   - cor com a tabela de van de Weijer (família certa de 54% para 64% com a mira simulada);
   - `/analyze-clothing` com gpt-4.1-mini;
   - gravata recusada;
   - correção do CLIP para o `transformers` 4.x do requirements (sem ela, a `dev` da visão não sobe);
   - 39 fotos rotuladas em `tests/eval/`.
2. **back #20** `feature/motor-looks`:
   - `POST /looks/sugerir`: confere o mínimo de 5 peças de cima e 5 de baixo (vestido vale pelas duas) antes de chamar a OpenAI; a IA só gera filtros; o motor (`src/looks/motor.ts`) escolhe as peças no banco;
   - superior (camiseta, camisa ou moletom) + inferior + calçado, ou vestido + calçado; jaqueta e blazer são uma camada opcional;
   - `npm test` com 24 testes.
3. **back #21** `fix/cadastro-nao-confirmado`:
   - quem se cadastrou e nunca confirmou tem a conta recriada (o IAM `zyra-backend` já tem `AdminGetUser` e `AdminDeleteUser`);
   - mensagem neutra quando o banco está dessincronizado do Cognito, sem apagar nada.
4. **app #20** `feature/chat-looks`: `ChatScreen` chamando o endpoint e mostrando as peças com o `ClosetItemCard`.

**Ambiente local do Gustavo:**
- banco no Docker (`docker start zyra-postgres`) e esvaziado em 04/10;
- `.env` do back completo (S3, visão e OpenAI);
- `.env` do app aponta para o IP do Mac, que muda quando troca de rede (`ipconfig getifaddr en0`);
- visão sobe com `--host 0.0.0.0`.

**Decisões:**
- **Cor na câmera:** só uma cor, sem "pode ser X". Fica por visão computacional clássica, porque o GPT é caro e lento para ler a cada 800 ms.
- **Modelo próprio de cor:** treinar na Fashion Product Images não superou o van de Weijer (54% contra 64%).
- **Pares de cor por tipo de daltonismo:** fora de escopo por enquanto.

## Estado em 05/10/2026 (fim do dia)

**Na `dev`:** PRs #10 (visão), #20 e #21 (back) e #20 (app), mergeados em 05/10. A branch `fix/cadastro-pecas` da Sophia (back e app) ficou redundante e não deve ser mergeada; ela precisa apagar o registro da migration `20261001120000_remove_bolsa_da_categoria` do banco local dela.

**Mergeados na `dev` em 05/10 (back PR #22, app PR #21):**
- **back `feature/regras-ocasiao` (`7212a0a`):**
  - regras de ocasião em `src/looks/ocasioes.ts`: cada peça é adequada, aceitável ou proibida;
  - troca de parte do look (campo `trocar` da intenção);
  - jaqueta só com frio, no trabalho ou em pedido formal;
  - variedade (desempate aleatório e `pecasRecentes`);
  - concordância de gênero;
  - 39 testes.
- **app `feature/chat-ux` (`1363a54`):**
  - gestos e animações do painel do chat;
  - campo de texto que cresce;
  - cards do look maiores;
  - transição entre o armário e o chat;
  - botão de enviar novo;
  - câmera no chat.

**Testes no celular (armário real do Gustavo, 38 peças):** a câmera erra cor com luz amarela de casa (azul-marinho → cinza, cinza → castanho claro). Ficou para depois: testar com outra luz.

## Próximos passos

1. **Regras de looks controladas pelo Gustavo** (combinado em 05/10). As regras saem do código do motor e vão para um arquivo de regras por cenário (YAML), que ele edita:
   - cenários novos: jantar, chuva, faculdade...;
   - para cada cenário: o que é obrigatório, o que nunca pode e o que é preferido;
   - o interpretador lê a lista de cenários desse arquivo;
   - rodízio entre conversas: contador de sugestões por peça (migration);
   - cada cenário vira um teste automático.

   O Gustavo vai escrever os cenários numa planilha (cenário, como o usuário fala, tem que ter, nunca pode ter, prefere, um look bom), que depois vira o YAML.
2. **Gustavo:** cadastrar as peças do próprio armário (pelo menos 5 de cima e 5 de baixo), tirar fotos para a avaliação e listar looks que combinam e que não combinam, para medir o motor.
3. **Testar o recadastro de conta não confirmada** com a correção do PR #21 rodando.
4. **Prompt do chat:** o Gustavo quer acrescentar exemplos (formatura e show como FESTA, com formalidade).
5. **Motor:** restrição de combinação pedida pelo usuário ("não quero vermelho com verde"), com um novo campo `evitarCombinacoes`.
6. **Visão:** cor secundária das peças estampadas. A contagem de pixels não funcionou; o GPT acertou 7/10.
7. **Infra para os testes com usuários:** banco e back hospedados (RDS ou um Postgres gerenciado).
8. **Qualidade e pesquisa:** pedidos escritos pelos participantes (conjunto cego do chat) e testes de usabilidade.
9. **Cadastro: verificar o e-mail antes da senha** (pedido do Gustavo em 05/10). Hoje a pessoa só descobre que o e-mail já tem conta depois de criar a senha.
   - Back: `POST /auth/verificar-email`, que consulta o Cognito (`AdminGetUser`) e responde só livre ou já tem conta. Conta pendente (nunca confirmada) conta como livre, porque o cadastro a recria.
   - App: a `RegisterBasicInfoScreen` chama o endpoint no "Continuar"; se já existir conta, mostra o aviso com **Entrar** e **Recuperar senha**.
   - Segurança: o endpoint permite descobrir quem tem conta (enumeração). Proposta: limitar tentativas por IP com `@nestjs/throttler`. Falta o Gustavo decidir.
   - A checagem no `/auth/signup` continua como garantia final.
10. **Decisão pendente nas regras:** short em festa só com calor, e "encontro"/"date" tratado como festa.
11. **Apresentação do look** no estilo do mockup (peças soltas com o símbolo ColorADD ao lado).
12. **Câmera:** preview em 4:3 (hoje parece zoom) e envio só da área da mira (hoje manda a foto inteira a cada 0,8 s e às vezes estoura o tempo).
13. **Peças de duas cores** (ex.: xadrez preto e branco): mostrar as duas cores na câmera?

## Divergências em relação ao artigo (Artigo-TCC1)

O artigo precisa ser atualizado em cinco pontos:
- **Autenticação:** foi escolhido o Cognito, e não JWT próprio.
- **Validação de vestuário:** é feita com CLIP local.
- **Detecção de cor:** usa recorte central + k-means + tabela de nomes de cor de van de Weijer, e não só a "região central".
- **Chamadas de visão:** o app fala direto com a API de visão.
- **Telefone:** foi removido do cadastro.