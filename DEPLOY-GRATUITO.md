# TUDUN — homologação gratuita

**Objetivo:** publicar uma homologação externa sem mensalidade, usando Render Free, Neon Free, Upstash Free e Brevo Free.

**Limites aceitos:** o site pode hibernar após 15 minutos sem tráfego; os serviços têm cotas gratuitas; este ambiente não é a configuração final recomendada para produção.

**Cobrança:** nenhum plano pago é criado pelo `render.free.yaml`. Não cadastrar cobrança por uso sem autorização expressa.

## Ordem de configuração

1. Criar o projeto PostgreSQL no Neon, selecionando uma região próxima de `virginia` quando disponível.
2. Copiar a URL de conexão do banco. Ela será informada somente no campo secreto `DATABASE_URL` do Render.
3. Criar uma base Redis no Upstash, preferencialmente na mesma região ou próxima dela.
4. Copiar a URL TLS `rediss://...` para o campo secreto `CACHE_URL` do Render.
5. Criar a conta Brevo, validar o remetente e gerar uma chave SMTP.
6. No Render, criar um Blueprint a partir do repositório privado e selecionar `render.free.yaml`.
7. Conferir que o único recurso declarado é `tudun-homologacao`, com plano `free`.
8. Preencher os valores solicitados sem gravar segredos no repositório.

## Valores solicitados pelo Blueprint

| Variável | Origem |
|---|---|
| `DATABASE_URL` | URL PostgreSQL copiada do Neon |
| `CACHE_URL` | URL TLS Redis copiada do Upstash |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://tudun-homologacao.onrender.com`, ajustando se o hostname efetivo for diferente |
| `EMAIL_HOST_USER` | Usuário SMTP da Brevo |
| `EMAIL_HOST_PASSWORD` | Chave SMTP da Brevo, não a senha da conta |
| `DEFAULT_FROM_EMAIL` | Remetente previamente validado na Brevo |

O Blueprint já define `EMAIL_HOST=smtp-relay.brevo.com`, `EMAIL_PORT=2525` e TLS. O Render Free bloqueia as portas 25, 465 e 587; a Brevo documenta 2525 como alternativa. A conectividade externa e a entrega real precisam ser comprovadas no aceite.

## Publicação e aceite

1. Aplicar o Blueprint e aguardar o build Docker.
2. A primeira inicialização executa migrações, coleta os estáticos e inicia o Waitress.
3. Confirmar `/saude/` com HTTP 200 pelo endereço HTTPS.
4. Testar página inicial, login, cadastro, recuperação de senha e envio real de e-mail.
5. Confirmar persistência no Neon após reiniciar o site.
6. Confirmar funcionamento do Redis e das proteções que dependem de cache compartilhado.
7. Revisar responsividade, logs, cookies seguros, CSRF e isolamento entre comunidades.
8. Registrar data, resultado e evidências em `CONTROLE-LANCAMENTO.md`.

Se a porta 2525 não for alcançável, interromper o aceite de e-mails e preparar a integração transacional por API. Não usar backend de e-mail em arquivo no ambiente externo.

## Upgrade planejado

Para retirar a hibernação antes do Beta fechado, alterar somente o web service para o plano pago inicial. O `render.yaml` permanece como referência da estrutura paga toda no Render e não é aplicado nesta homologação gratuita.
