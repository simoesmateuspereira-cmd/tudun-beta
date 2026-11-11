# TUDUN — operação do Beta fechado

**Situação:** procedimento-base preparado localmente; ainda não ativado nem ensaiado em hospedagem.
**Escopo:** comunidade + agenda, sem cobrança, reservas, ingressos ou check-in.
**Responsáveis, canal de suporte e horários:** **A definir** antes de convidar participantes.

Este documento não comprova aceite humano, monitoramento externo ou recuperação em produção. Os bloqueadores correspondentes continuam registrados em `CONTROLE-LANCAMENTO.md`.

## 1. Papéis operacionais obrigatórios

| Função | Responsável | Obrigação antes do Beta |
|---|---|---|
| Dono do piloto | A definir | Aprovar participantes, escopo, métricas e encerramento |
| Suporte | A definir | Receber solicitações, registrar ocorrências e orientar participantes |
| Plantão técnico | A definir | Receber alertas, conter falhas e autorizar rollback técnico |
| Dados e privacidade | A definir | Atender titulares e coordenar retenção, incidentes e operadores |
| Comunicação | A definir | Avisar participantes sobre indisponibilidade e recuperação |

Nenhuma função pode ser considerada atribuída enquanto constar “A definir”.

## 2. Suporte do piloto

Antes do convite, publicar aos participantes:

- canal único de atendimento, horário e expectativa de resposta;
- instruções de acesso, verificação de e-mail e MFA para gestores;
- aviso de que o ambiente usa dados controlados e não realiza cobranças;
- canal alternativo para indisponibilidade do canal principal.

Cada solicitação deve registrar data, comunidade, conta identificada sem expor senha ou token, jornada afetada, mensagem apresentada, captura quando segura e resultado. Não solicitar senhas, códigos MFA, tokens de convite ou conteúdo integral de e-mails.

## 3. Incidentes

### Classificação inicial

- **S1 — crítico:** acesso cruzado entre comunidades, elevação indevida de permissão, exposição de segredo ou suspeita de perda/corrupção de dados. Interromper acesso afetado e acionar imediatamente o plantão.
- **S2 — alto:** aplicação ou banco indisponível, falha generalizada de login, MFA ou e-mail que impeça o piloto. Avaliar suspensão temporária do Beta.
- **S3 — moderado:** falha limitada de agenda, avisos ou gestão, com contorno disponível e sem impacto de segurança ou dados.
- **S4 — baixo:** dúvida, texto, apresentação ou problema individual sem impacto na jornada principal.

### Sequência de atendimento

1. Registrar horário, versão, ambiente, alcance e evidências sem dados sensíveis.
2. Classificar e nomear o responsável pelo incidente.
3. Conter: bloquear rota afetada, suspender convites ou retirar a versão do tráfego, conforme o caso.
4. Preservar logs e registros de auditoria; não alterar evidências.
5. Comunicar participantes afetados pelo canal definido, sem especular sobre causa.
6. Recuperar e validar `/saude/`, autenticação, permissões, agenda e e-mail.
7. Encerrar somente com causa, impacto, ações, responsáveis e prevenção registrados. Incidentes de privacidade seguem avaliação específica do responsável designado.

## 4. Rollback e recuperação

Antes de cada implantação:

- identificar o artefato atual e o anterior por versão imutável;
- confirmar backup externo recente e evidência de restauração;
- revisar se as migrações são compatíveis com a versão anterior;
- guardar logs e o resultado das verificações da implantação.

Ao acionar rollback:

1. Interromper o direcionamento de tráfego para a versão afetada.
2. Preservar logs, banco e evidências antes de qualquer restauração.
3. Restaurar o artefato anterior compatível; não reverter migrações destrutivamente por impulso.
4. Se houver divergência de dados, manter o serviço contido e submeter a janela de perda ao responsável **A definir** para decisão formal.
5. Validar saúde, login, MFA, isolamento entre comunidades e agenda antes de reabrir.
6. Comunicar o resultado e registrar o pós-incidente.

O rollback externo continua **pendente de ensaio**. O teste local de restauração não substitui essa evidência.

## 5. Entrada da opção A — hospedagem gerenciada

Configurar segredos e variáveis conforme `.env.example`, sem reutilizar contas ou senhas fictícias. A inicialização exige PostgreSQL externo, Redis, SMTP, hosts e origens CSRF. O proxy gerenciado deve encaminhar HTTPS com `X-Forwarded-Proto`.

Validar configuração sem iniciar o servidor:

```bash
python scripts/production.py --validate-only
```

Executar a release em uma única instância antes de direcionar tráfego:

```bash
python scripts/production.py --host 0.0.0.0 --port 8000
```

O comando aplica migrações, coleta estáticos e inicia Waitress. Em plataformas com release separado, separar migrações/coleta do processo web para evitar execução concorrente. Não executar `seed_demo` em dados reais.

Após a release, verificar `/saude/`, HTTPS, cookies, SMTP real, Redis compartilhado, contas de cada papel, isolamento, gestão de eventos e provisionamento controlado. Anexar data e evidência ao controle de lançamento.

## 6. Registro operacional mínimo

| Data | Ambiente/versão | Ocorrência ou validação | Responsável | Evidência | Resultado |
|---|---|---|---|---|---|
| A definir | A definir | A definir | A definir | A anexar | Pendente |
