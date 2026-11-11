# TUDUN — implantação da opção A

**Objetivo:** homologação externa do Beta fechado em plataforma gerenciada, com Django, PostgreSQL e Redis.
**Situação:** pacote provider-neutral preparado; nenhum serviço externo provisionado.
**Validação local do contêiner:** pendente, pois Docker não está instalado nesta máquina.

## 1. Recursos a provisionar

1. Plataforma de aplicação com suporte a Docker e proxy HTTPS.
2. PostgreSQL gerenciado com backups e acesso restrito.
3. Redis gerenciado compatível com URL `redis://` ou `rediss://`.
4. SMTP transacional com remetente e domínio autenticados.
5. Domínio ou subdomínio de homologação.
6. Monitoramento externo de `/saude/`, logs, erros e alertas.
7. Canal de suporte e responsáveis definidos em `OPERACAO-BETA.md`.

Não usar o seed nem as credenciais fictícias no ambiente externo.

## 2. Variáveis de ambiente

Preencher no cofre da plataforma. Nunca gravar valores reais no repositório.

| Variável | Valor esperado |
|---|---|
| `DJANGO_SECRET_KEY` | Segredo aleatório longo, exclusivo da homologação |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | URL PostgreSQL fornecida pelo serviço |
| `DATABASE_TIME_ZONE` | `UTC` |
| `DATABASE_CONN_MAX_AGE` | `60` inicialmente; revisar após teste de carga |
| `CACHE_URL` | URL Redis compartilhada, preferencialmente `rediss://` |
| `CACHE_KEY_PREFIX` | `tudun-homologacao` |
| `DJANGO_ALLOWED_HOSTS` | Hostname da plataforma e domínio, separados por vírgula |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origens HTTPS completas, separadas por vírgula |
| `DJANGO_TRUST_PROXY_SSL` | `True` quando o proxy definir `X-Forwarded-Proto` |
| `SESSION_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_SECURE` | `True` |
| `SECURE_SSL_REDIRECT` | `True` |
| `SECURE_HSTS_SECONDS` | `300` no primeiro teste; elevar somente após validação |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` inicialmente |
| `SECURE_HSTS_PRELOAD` | `False` até decisão expressa |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | Host do provedor SMTP |
| `EMAIL_PORT` | Porta recomendada pelo provedor |
| `EMAIL_HOST_USER` | Usuário SMTP, se exigido |
| `EMAIL_HOST_PASSWORD` | Segredo SMTP, se exigido |
| `EMAIL_USE_TLS` | Conforme o provedor; não combinar com SSL |
| `EMAIL_USE_SSL` | Conforme o provedor; não combinar com TLS |
| `EMAIL_TIMEOUT` | `10` |
| `DEFAULT_FROM_EMAIL` | Remetente autenticado no provedor |
| `LOG_TO_FILE` | `False` |
| `PORT` | Porta definida pela plataforma; padrão local do contêiner: `8000` |

O script de produção força as exigências de Redis e SMTP e falha antes de abrir o servidor se faltarem variáveis essenciais.

## 3. Comandos de implantação

Validar configuração sem conectar ao Redis ou iniciar servidor:

```bash
python scripts/production.py --validate-only
```

Executar migrações e arquivos estáticos uma única vez:

```bash
python scripts/production.py --release-only
```

Iniciar o processo web sem repetir a release:

```bash
python scripts/production.py --serve-only
```

Se a plataforma não oferecer release separado, o comando padrão executa release e servidor na mesma inicialização:

```bash
python scripts/production.py
```

Nesse caso, iniciar somente uma instância durante a implantação. Não executar releases concorrentes.

## 4. Contêiner

O `Dockerfile` usa Python 3.12, instala apenas dependências de produção, executa como usuário não root e respeita `PORT` pelo script de inicialização. A imagem não contém `.env`, banco local, backups, capturas ou ambiente virtual.

Build e execução local, quando Docker estiver disponível e as variáveis reais estiverem configuradas:

```bash
docker build -t tudun-homologacao .
docker run --rm --env-file .env.production -p 8000:8000 tudun-homologacao
```

`.env.production` é apenas um exemplo de nome local protegido e não deve ser commitado. Esses comandos ainda não foram executados nesta máquina.

## 5. Sequência de provisionamento

1. Escolher plataforma e registrar responsável.
2. Criar PostgreSQL e Redis; guardar URLs no cofre.
3. Criar aplicação Docker e configurar todas as variáveis.
4. Executar `--validate-only` e depois `--release-only`.
5. Iniciar uma instância com `--serve-only`.
6. Configurar domínio, HTTPS, hosts e origens CSRF.
7. Configurar SMTP e autenticação do remetente.
8. Criar o primeiro superusuário por comando interativo protegido, sem senha no histórico ou no repositório.
9. Provisionar comunidade piloto pela interface e nomear administrador verificado.
10. Configurar monitoramento, backups externos e alertas antes dos convites.

## 6. Aceite obrigatório da homologação

- `/saude/` responde 200 pelo domínio HTTPS e 503 em falha controlada do banco.
- Redirecionamento HTTP→HTTPS, cookies `Secure`, hosts e CSRF validados.
- Cadastro, verificação, recuperação e convites chegam a caixas reais.
- Rate limiting é compartilhado entre duas instâncias.
- MFA administrativo e isolamento entre comunidades são testados.
- Administrador/moderador gerencia evento; membro não obtém acesso indevido.
- Desktop e celular passam pelas jornadas principais.
- Backup externo e restauração são ensaiados; rollback de aplicação é ensaiado.
- Suporte, incidentes, participantes, métricas e responsáveis são formalizados.

Cada aceite precisa de data, responsável e evidência em `CONTROLE-LANCAMENTO.md`. A etapa C local não autoriza abrir o Beta externo sem esses resultados.

## 7. Rollback da implantação

Preservar a imagem anterior por tag imutável e o backup anterior à release. Em falha, retirar a nova versão do tráfego, manter evidências e restaurar a imagem compatível com o banco. Não reverter migrações destrutivamente por impulso. Restauração de banco exige responsável nomeado e janela de perda aprovada.

## 8. Referência preparada para Render

O arquivo `render.yaml` define web Docker, PostgreSQL 16 e Key Value compatível com Redis na mesma região. Banco e Key Value usam conexões internas, sem liberação pública de IP. O web service executa release no `preDeployCommand`, inicia com `--serve-only`, mantém uma instância e desativa deploy automático.

Os planos declarados são `0.5c-512mb` para web, `0.1c-256mb` para PostgreSQL e `256mb` para Key Value. O comando de release exige web pago. Revisar planos, limites e preços atuais no painel antes de aplicar; este arquivo não representa contratação nem autorização de cobrança.

### Antes de aplicar

1. Criar ou escolher um repositório Git **privado** cuja raiz contenha `render.yaml`, `Dockerfile` e o código de `tudun/`. O diretório atual ainda não é um repositório Git.
2. Confirmar que `.env`, bancos locais, backups e arquivos de execução não serão enviados.
3. No Render, abrir **Blueprints → New Blueprint Instance** e conectar o repositório.
4. Revisar recursos, região `virginia`, planos e custos. Não aplicar sem autorização.
5. Preencher `DJANGO_CSRF_TRUSTED_ORIGINS` com a URL HTTPS inicial `https://<hostname>.onrender.com` e os valores SMTP solicitados.
6. Aplicar o Blueprint e aguardar build, release e health check.

O `DJANGO_ALLOWED_HOSTS` inicial é derivado de `RENDER_EXTERNAL_HOSTNAME`. Ao adicionar domínio próprio, alterar essa variável para uma lista com o hostname do Render e o domínio, e incluir a nova origem HTTPS em `DJANGO_CSRF_TRUSTED_ORIGINS`.

Nenhum repositório, serviço ou cobrança foi criado nesta etapa.
