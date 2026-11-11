# TUDUN — fundação para Beta fechado

Aplicação Django full-stack para homologação local de comunidades privadas, somente com dados fictícios. A base técnica está validada localmente; não é um MVP público, uma produção aprovada ou um Beta externo já liberado.

Ingressos, reservas, check-in, pedidos, pagamentos, storage R2 e integração com Máquina de Cortes continuam fora do escopo.

## Implementado

- Agenda privada com catálogo, detalhes e prévia na comunidade, integrada ao PostgreSQL e às permissões existentes.
- Administradores e moderadores criam, editam, publicam e cancelam eventos, com validações, isolamento e auditoria.
- Provisionamento de comunidade por superusuário, com administrador ativo e e-mail verificado.
- Cinco eventos fictícios idempotentes no seed, com datas futuras relativas, categorias, locais, capacidade, preços fictícios e quatro situações visuais.
- Django 5.2, PostgreSQL 16 local, migrações e servidor de desenvolvimento via `npm run dev`.
- Cadastro, entrada e saída; e-mail normalizado e único no banco por `LOWER(email)`.
- Verificação de e-mail com token assinado, URL-safe, expiração de 48 horas e reenvio limitado.
- MFA TOTP obrigatório para superusuários e administradores ativos.
- Dez códigos de recuperação de uso único, reemissão autenticada e redefinição local com confirmação.
- Comunidades privadas sem diretório público e isolamento de permissões entre comunidades.
- Papéis `admin`, `moderator`, `member` e `guest`; situações `pending`, `active`, `suspended`, `removed` e `declined`.
- Convites com hash do token, expiração, revogação, uso único e conferência do e-mail verificado.
- Solicitações com aprovação/recusa, gestão de vínculos e proteção transacional do último administrador ativo.
- Avisos e auditoria administrativa imutável pela aplicação, com detalhes filtrados por lista segura.
- Rate limiting com HTTP 429 nas rotas sensíveis, sem executar operações excedentes.
- Cache local explícito ou Redis por `CACHE_URL`, com prefixo de chaves.
- Admin operacional somente leitura; mudanças de negócio passam pelos serviços da aplicação.
- Página de privacidade e retenção específica do ambiente local.
- Endpoint `/saude/`, logs rotativos ou stdout e ocultação de tokens nos caminhos de log.
- Homologação com `DEBUG=False`, Waitress e WhiteNoise; configurações SMTP e HTTPS por ambiente.
- Inicialização provider-neutral para hospedagem gerenciada, com Redis e SMTP obrigatórios.
- Backup e restauração PostgreSQL locais com validação em banco separado.

## Executar localmente

No diretório do projeto:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_demo
npm run dev
```

A prévia padrão usa `localhost:7100`. O script encaminha host e porta:

```bash
npm run dev -- --host 127.0.0.1 --port 51234
```

### Contas fictícias

- `admin_teste`
- `membro_teste`
- Senha local fictícia de ambas: `TudunTeste-2026!`

No primeiro acesso administrativo, cadastre um TOTP próprio de teste. Não reutilize essas contas ou essa senha fora do ambiente local.

### E-mails e verificação

Por padrão, os e-mails são gravados em `.runtime/outbox/`. Isso inclui confirmação de e-mail e convites. Não há provedor externo configurado.

Novos cadastros precisam confirmar o e-mail antes de aceitar convites ou solicitar participação. Contas fictícias existentes antes da migração foram preservadas como verificadas; o seed também mantém as duas contas de demonstração utilizáveis.

Convites continuam com token bruto somente no e-mail e SHA-256 no banco. Tokens de convite e verificação são ocultados nos caminhos gravados pelo logging da aplicação.

Para marcar convites vencidos:

```bash
.venv/Scripts/python manage.py expire_invitations
```

O aceite também confere `expires_at`; portanto, um convite vencido é recusado mesmo antes dessa rotina.

## Homologação local

Inicia Waitress em `127.0.0.1:7101`, aplica migrações e coleta arquivos estáticos:

```bash
.venv/Scripts/python scripts/staging.py
```

Esse perfil usa `DEBUG=False`, mas mantém exceções explícitas para testar HTTP em loopback. Não use essas exceções em um ambiente externo. Para executar e encerrar uma validação automática:

```bash
.venv/Scripts/python scripts/validate_staging.py
```

## Preparar a opção A — hospedagem gerenciada

Configure as variáveis de `.env.example` com segredos reais no provedor, sem gravar esses valores no projeto. O script de produção exige PostgreSQL e Redis externos, SMTP, hosts e origens CSRF; usa HTTPS, logs em stdout e não contém as exceções de loopback.

Validar sem abrir servidor:

```bash
.venv/Scripts/python scripts/production.py --validate-only
```

Em uma única release, antes de direcionar tráfego:

```bash
.venv/Scripts/python scripts/production.py --host 0.0.0.0 --port 8000
```

O comando aplica migrações, coleta estáticos e inicia Waitress. Se a plataforma separar release e processo web, execute migrações/coleta apenas uma vez. Não execute `seed_demo` com dados reais. Nenhum provedor foi contratado ou validado nesta etapa.

## Verificações executadas

### Suíte completa

```bash
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py test --verbosity 1
```

Resultado observado em 11 de novembro de 2026:

- `No changes detected`.
- `System check identified no issues`.
- **63 testes aprovados em 71,213 s**, sem falhas.
- Banco PostgreSQL de testes criado e destruído corretamente.

A suíte inclui quatro jornadas E2E no Chrome, identidade, MFA, permissões, convites, avisos, auditoria, gestão de eventos, provisionamento e cinco testes das configurações de produção.

### Homologação e segurança

```bash
.venv/Scripts/python scripts/validate_staging.py
DJANGO_DEBUG=False .venv/Scripts/python manage.py check --deploy
```

A homologação respondeu HTTP 200 em página inicial, login, privacidade, saúde e CSS. A checagem de deploy deixou somente `security.W021`: HSTS preload permanece desativado até existir domínio real e aprovação.

### Backup e restauração

```bash
.venv/Scripts/python manage.py backup_database
.venv/Scripts/python scripts/validate_restore.py
```

Em 11 de novembro, o backup `backups/tudun-20261111-160025.dump` foi criado e restaurado em banco separado. Foram conferidos **2 usuários, 1 comunidade, 2 perfis de identidade, 0 eventos de auditoria e 1 índice único de e-mail**. O banco temporário foi removido.

Restauração manual somente no ambiente fictício:

```bash
.venv/Scripts/python manage.py restore_database "backups/arquivo.dump" --confirm RESTAURAR
```

A operação substitui objetos do banco configurado. Não a utilize em dados reais sem procedimento aprovado.

### Interface

```bash
.venv/Scripts/python scripts/visual_check.py
```

Foram geradas **19 capturas** em desktop e celular: páginas públicas, membro, agenda, detalhe, criação/edição/cancelamento de eventos e provisionamento. O script valida MFA administrativo, cinco eventos e ausência de overflow horizontal. As contas temporárias são removidas e o servidor é encerrado automaticamente. As novas telas foram inspecionadas sem quebra de layout.

## Notas operacionais

- O PostgreSQL local usa aliases ASCII e caminhos curtos no Windows. Se `.postgres-recovered/` existir, ele é utilizado para preservar o cluster original.
- A sessão local usa `GMT`, equivalente a UTC para `timestamptz`; a interface usa `America/Sao_Paulo`.
- Sem `CACHE_URL`, o rate limiting serve apenas um processo. Múltiplos processos exigem Redis compartilhado.
- `/saude/` verifica o banco com `SELECT 1` e não expõe credenciais ou mensagens internas.
- Logs locais ficam em `.runtime/logs/tudun.log`; na hospedagem, `LOG_TO_FILE=False` usa somente stdout.
- Não há exclusão automática de contas, dados ou backups nesta etapa.
- Suporte, incidentes e rollback têm procedimento-base em `OPERACAO-BETA.md`, ainda sem responsáveis ou ensaio externo.

## Aceite e pendências

`BETA-FECHADO-HOMOLOGACAO.md` registra as evidências atuais. `CONTROLE-LANCAMENTO.md` controla o que já existe e os bloqueadores. Provedores, credenciais, dados reais, segurança/carga externa, operação e aceite humano com Karine continuam pendentes.
