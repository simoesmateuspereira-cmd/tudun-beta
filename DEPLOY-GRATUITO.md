# TUDUN — homologação gratuita

**Objetivo:** publicar uma homologação externa sem mensalidade, usando Render Free, Neon Free, Upstash Free e a API oficial do Gmail.

**Limites aceitos:** o site pode hibernar após 15 minutos sem tráfego; os serviços têm cotas gratuitas; este ambiente não é a configuração final recomendada para produção.

**Cobrança:** nenhum plano pago é criado pelo `render.free.yaml`. Não cadastrar cobrança por uso sem autorização expressa.

## Ordem de configuração

1. Criar o projeto PostgreSQL no Neon, selecionando uma região próxima de `virginia` quando disponível.
2. Copiar a URL de conexão do banco. Ela será informada somente no campo secreto `DATABASE_URL` do Render.
3. Criar uma base Redis no Upstash, preferencialmente na mesma região ou próxima dela.
4. Copiar a URL TLS `rediss://...` para o campo secreto `CACHE_URL` do Render.
5. No Google Cloud, criar credenciais OAuth de aplicativo para computador e ativar a Gmail API. O app usa somente o escopo `gmail.send`.
6. Executar `scripts/gmail_oauth_setup.py` localmente para autorizar a conta e guardar o refresh token em `.runtime/gmail-oauth-credentials.json`, fora do Git.
7. No Render, criar um Blueprint a partir do repositório privado e selecionar `render.free.yaml`.
8. Conferir que o único recurso declarado é `tudun-homologacao`, com plano `free`.
9. Preencher os valores solicitados sem gravar segredos no repositório ou enviá-los pelo chat.

## Valores solicitados pelo Blueprint

| Variável | Origem |
|---|---|
| `DATABASE_URL` | URL PostgreSQL copiada do Neon |
| `CACHE_URL` | URL TLS Redis copiada do Upstash |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://tudun-homologacao.onrender.com`, ajustando se o hostname efetivo for diferente |
| `GMAIL_CLIENT_ID` | ID do cliente OAuth criado no Google Cloud |
| `GMAIL_CLIENT_SECRET` | Segredo do cliente OAuth, copiado diretamente para o campo secreto |
| `GMAIL_REFRESH_TOKEN` | Token de longa duração gerado localmente pela autorização OAuth |
| `DEFAULT_FROM_EMAIL` | O mesmo endereço Gmail autorizado no OAuth |

O Blueprint usa `identity.gmail_backend.GmailAPIBackend`, que envia mensagens MIME pela API HTTPS oficial do Gmail. Essa abordagem não usa senha de app nem portas SMTP. A entrega real precisa ser comprovada no aceite externo.

## Publicação e aceite

1. Aplicar o Blueprint e aguardar o build Docker.
2. A primeira inicialização executa migrações, coleta os estáticos e inicia o Waitress.
3. Confirmar `/saude/` com HTTP 200 pelo endereço HTTPS.
4. Testar página inicial, login, cadastro, recuperação de senha e envio real de e-mail.
5. Confirmar persistência no Neon após reiniciar o site.
6. Confirmar funcionamento do Redis e das proteções que dependem de cache compartilhado.
7. Revisar responsividade, logs, cookies seguros, CSRF e isolamento entre comunidades.
8. Registrar data, resultado e evidências em `CONTROLE-LANCAMENTO.md`.

Se a autorização OAuth for revogada ou expirar, gerar um novo refresh token localmente e atualizar somente o campo secreto no Render. Não usar backend de e-mail em arquivo no ambiente externo.

## Upgrade planejado

Para retirar a hibernação antes do Beta fechado, alterar somente o web service para o plano pago inicial. O `render.yaml` permanece como referência da estrutura paga toda no Render e não é aplicado nesta homologação gratuita.
