# TUDUN — aceite do Beta fechado em homologação local

Data da validação: 11 de novembro de 2026.

## Decisão e escopo

A base está **pronta e revalidada para homologação local com dados fictícios**. Isso não significa Beta externo liberado ou produção aprovada. Comunidade, agenda e gestão estão implementadas; reservas, check-in, pedidos, pagamentos, storage R2 e Máquina de Cortes continuam fora do escopo.

Nenhum serviço foi contratado, nenhuma credencial real foi usada e não houve revisão humana com Karine.

## Preparo concluído e evidências

- **63 testes aprovados em 71,213 s**, sem falhas; `makemigrations --check --dry-run` não encontrou alterações e `manage.py check` não encontrou problemas.
- Administradores e moderadores criam, editam, publicam e cancelam eventos com validações, slug único por comunidade, isolamento e auditoria. Membros e externos recebem 403; evento de outra comunidade não pode ser alterado pela URL local.
- Superusuário provisiona comunidade e nomeia administrador com conta ativa e e-mail verificado. Criador e administrador recebem papel `ADMIN`, com auditoria.
- Cinco eventos fictícios continuam no seed, com quatro situações e preços apenas demonstrativos. Não há ações falsas de compra, reserva ou check-in.
- **4 jornadas E2E no Chrome**: MFA e convite; aceite com isolamento; aprovação por moderador; cadastro com confirmação de e-mail e CSS.
- E-mail único por `LOWER(email)`, verificação assinada e expirada, limites de requisição, MFA administrativo, recuperação e permissões mantidos e revalidados.
- Django Admin operacional somente leitura; mudanças de negócio passam pelos serviços da aplicação.
- Configuração Redis nativa por `CACHE_URL`, prefixo de chaves e fallback local explícito. `DJANGO_REQUIRE_SHARED_CACHE=True` rejeita produção sem Redis; nenhum serviço Redis externo foi testado.
- `DJANGO_REQUIRE_SMTP=True` rejeita backend de arquivo ou configuração incompleta. `LOG_TO_FILE=False` direciona logs somente ao stdout na hospedagem. Cinco testes cobrem essas configurações.
- `scripts/production.py --validate-only` validou a configuração de produção sem iniciar servidor. A inicialização normal aplica migrações, coleta estáticos e inicia Waitress, sem exceções HTTP locais.
- Logs locais rotativos e ocultação de tokens mantidos. `/saude/` executa `SELECT 1`, devolve 200 quando saudável e 503 sem detalhes internos.
- Homologação local validada com `DEBUG=False`, Waitress e WhiteNoise. `/`, login, privacidade, saúde e CSS responderam HTTP 200; o servidor temporário foi encerrado.
- `check --deploy` apresentou apenas `security.W021`. HSTS preload permanece desativado até existir domínio real e aprovação.
- Backup `backups/tudun-20261111-160025.dump` e restauração em banco separado concluídos: **2 usuários, 1 comunidade, 2 perfis, 0 eventos de auditoria e 1 índice único de e-mail** conferidos. O banco temporário foi removido.
- **19 capturas** em desktop e celular: páginas públicas, membro, agenda, detalhes, criação/edição/cancelamento de eventos e provisionamento. Não houve overflow horizontal; as novas telas foram inspecionadas sem quebra de layout.
- As capturas administrativas usaram contas temporárias e MFA real de teste. Nenhum formulário foi enviado e as contas foram removidas ao final.
- Procedimentos-base de suporte, incidentes e rollback estão em `OPERACAO-BETA.md`; responsáveis, ativação e ensaios continuam pendentes.

## Executar e repetir a validação

```bash
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py test --verbosity 1
.venv/Scripts/python scripts/validate_staging.py
.venv/Scripts/python scripts/visual_check.py
.venv/Scripts/python manage.py backup_database
.venv/Scripts/python scripts/validate_restore.py
DJANGO_DEBUG=False .venv/Scripts/python manage.py check --deploy
```

Desenvolvimento e homologação local:

```bash
npm run dev
.venv/Scripts/python scripts/staging.py
```

A homologação local mantém exceções explícitas para HTTP em loopback. Essas exceções não existem no script de produção.

## Monitoramento local

- Consultar `/saude/` e acompanhar `.runtime/logs/tudun.log` ou stdout.
- Alertas, métricas, retenção centralizada e notificações dependem do ambiente externo.
- Sem `CACHE_URL`, o rate limiting usa memória de um processo. Em múltiplas instâncias, Redis compartilhado é obrigatório.

## Pendências obrigatórias antes do Beta externo

1. Provisionar opção A: hospedagem, PostgreSQL gerenciado, Redis, domínio e HTTPS; validar proxy, hosts e CSRF.
2. Guardar segredos adequadamente e não usar contas ou senhas fictícias do seed.
3. Configurar SMTP e testar entrega, SPF, DKIM, DMARC, bounce e reclamações.
4. Testar rate limiting distribuído com Redis e revisar limites para o volume esperado.
5. Implantar monitoramento, alertas, métricas e retenção de logs.
6. Configurar backups externos, retenção e restaurações periódicas.
7. Aprovar privacidade, retenção, canal do titular e exclusão incluindo backups.
8. Revisar com Karine, realizar segurança/carga externa e aceite com participantes.
9. Nomear suporte e plantão, ensaiar incidentes/rollback e formalizar participantes, métricas e encerramento.

## Critérios de rollback

Interromper abertura ou retirar a versão se houver falha persistente de saúde/inicialização, elevação indevida de permissão, acesso cruzado, falha de MFA, tokens expostos, cookies inseguros, divergência de dados, indisponibilidade impeditiva de e-mail ou erros/latência acima dos limites aprovados.

Preservar artefato anterior e backup verificado. Não reverter migrações destrutivamente por impulso. Restaurar banco somente com responsável designado e janela de perda expressamente aprovada. O roteiro completo está em `OPERACAO-BETA.md`; o rollback externo ainda não foi ensaiado.

Restauração manual somente no ambiente fictício:

```bash
.venv/Scripts/python manage.py restore_database "backups/arquivo.dump" --confirm RESTAURAR
```

## Aceite

- **Homologação local técnica:** validada nos limites acima em 11/11/2026.
- **Beta externo:** pendente de provedores, credenciais, monitoramento, ensaios e aceite humano.
- **Beta público / produção:** não aprovados por esta validação.
