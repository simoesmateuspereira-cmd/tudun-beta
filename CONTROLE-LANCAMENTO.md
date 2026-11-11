# TUDUN — Controle de lançamento

**Atualizado em:** 11 de novembro de 2026
**Decisão atual:** **NO-GO para Beta externo**. O produto está validado no limite local; hospedagem, provedores, operação e aceites externos continuam pendentes.
**Escopo fechado do primeiro lançamento:** Beta fechado de **comunidade + agenda**, com usuários convidados e **sem cobrança**. Reservas, pedidos, pagamentos, ingressos e check-in ficam para fases posteriores.

Este documento controla a prontidão do produto. “Concluído localmente” não significa validado em hospedagem, domínio público ou operação real.

## 1. Legenda e regra de controle

- **Concluído localmente:** existe implementação e evidência no ambiente local, na data registrada.
- **Pendente / bloqueador:** precisa de implementação, configuração ou aceite antes do Beta externo.
- **Posterior:** fora do escopo do primeiro lançamento recomendado.
- **Responsável:** “A definir” até que uma pessoa assuma formalmente o item.
- **Evidência:** link, relatório, captura, log ou registro de teste que permita verificar o aceite.

Revisar semanalmente. Só alterar um status quando houver **evidência e data**. A decisão muda para **GO** somente quando todos os bloqueadores pendentes da seção 3 estiverem aceitos e registrados. Não usar percentual estimado de conclusão como critério de lançamento.

## 2. O que o site já tem — concluído localmente

| ID | Capacidade | Situação | Evidência conhecida | Última verificação | Observação |
|---|---|---|---|---|---|
| L01 | Cadastro, login, logout e recuperação de acesso | Concluído localmente | Suíte integral | 11/11/2026 | SMTP real ainda é bloqueador |
| L02 | Verificação de e-mail | Concluído localmente | Testes locais e E2E | 11/11/2026 | Entregabilidade externa não validada |
| L03 | MFA administrativo | Concluído localmente | Testes, E2E e captura autenticada | 11/11/2026 | Validar novamente na hospedagem |
| L04 | Controle de acesso por papéis (RBAC) | Concluído localmente | Testes de permissão e isolamento | 11/11/2026 | Revisar no piloto |
| L05 | Comunidades privadas e provisionamento | Concluído localmente | Testes e capturas de `comunidades/nova/` | 11/11/2026 | Superusuário nomeia administrador ativo e verificado |
| L06 | Convites e solicitações de participação | Concluído localmente | Interface, testes e E2E | 11/11/2026 | Fluxo de gestão disponível |
| L07 | Avisos da comunidade | Concluído localmente | Interface e suíte | 11/11/2026 | Sem assumir notificações externas |
| L08 | Agenda e gestão de eventos | Concluído localmente | Testes e capturas de criar, editar e cancelar | 11/11/2026 | Administradores e moderadores autorizados; auditoria registrada |
| L09 | Registros de auditoria | Concluído localmente | Implementação e testes | 11/11/2026 | Reter e monitorar em produção |
| L10 | Limitação de requisições | Concluído localmente | Implementação e testes | 11/11/2026 | Redis externo ainda pendente |
| L11 | Endpoint de saúde `/saude/` | Concluído localmente | Homologação HTTP 200 | 11/11/2026 | Falta monitoramento externo |
| L12 | Logs locais e em stdout | Concluído localmente | Configuração e testes | 11/11/2026 | Centralização e alertas pendentes |
| L13 | Backup e restauração local | Concluído localmente | Dump e banco separado validado | 11/11/2026 | Backup externo continua bloqueador |
| L14 | Interface responsiva | Concluído localmente | 19 capturas desktop/celular inspecionadas | 11/11/2026 | Sem overflow horizontal; repetir no destino |
| L15 | Base automatizada | Concluído localmente | **63 testes aprovados** | **11/11/2026** | Inclui 4 jornadas E2E, gestão e configurações |
| L16 | Inicialização para hospedagem gerenciada | Concluído localmente | `scripts/production.py --validate-only` | 11/11/2026 | Nenhum provedor contratado ou validado |
| L17 | Suporte a Redis compartilhado | Concluído localmente | Backend nativo e 5 testes de configuração | 11/11/2026 | Serviço externo e rate limit distribuído não testados |

### Registro da checagem de 11/11/2026

O PostgreSQL local foi recuperado em uma cópia preservada, sem encerrar o processo residual do usuário. As checagens de migração e Django passaram; a suíte executou **63 testes em 71,213 s**, com resultado `OK`. Waitress, WhiteNoise, backup e restauração foram revalidados. `check --deploy` apresentou apenas `security.W021`, pois HSTS preload permanece desativado até existir domínio real e aprovação.

## 3. O que falta para abrir o Beta — bloqueadores

| ID | Bloqueador | Critério objetivo de aceite | Situação | Evidência | Responsável | Próxima ação |
|---|---|---|---|---|---|---|
| B01 | Hospedagem de homologação e produção | Aplicação inicia de forma reproduzível, persiste dados e passa pela suíte no destino | Pendente | Inicialização local pronta; destino a anexar | A definir | Provisionar a opção A |
| B02 | PostgreSQL gerenciado | Banco externo configurado, migrações aplicadas, acesso restrito e rotina definida | Pendente | A anexar | A definir | Provisionar banco e executar migrações |
| B03 | Domínio e HTTPS | Domínio responde com HTTPS válido e redirecionamento correto | Pendente | A anexar | A definir | Configurar DNS e certificado |
| B04 | Proxy, hosts e CSRF | Proxy, `ALLOWED_HOSTS`, origens CSRF e cookies validados externamente | Pendente | Configuração preparada; teste externo a anexar | A definir | Validar no destino |
| B05 | Segredos e configuração | Nenhum segredo no código; variáveis protegidas, rotação e acesso mínimo documentados | Pendente | Modelo sem segredos; cofre a anexar | A definir | Criar variáveis protegidas |
| B06 | SMTP real e entregabilidade | Verificação, convite e recuperação chegam a provedores reais; SPF/DKIM/DMARC e falhas verificados | Pendente | Obrigatoriedade local implementada; entrega a anexar | A definir | Configurar SMTP e testar entrega |
| B07 | Cache compartilhado | Rate limiting funciona entre múltiplas instâncias sem memória local | Pendente | Backend Redis testado; serviço a anexar | A definir | Configurar Redis e testar limites |
| B08 | Gestão de eventos em autoatendimento | Gestor autorizado cria, edita, publica e cancela sem seed; permissões testadas | **Concluído localmente** | 7 testes de gestão e 6 capturas em 11/11/2026 | A definir | Revalidar no ambiente de destino |
| B09 | Provisionamento de comunidades | Processo controlado cria comunidade e nomeia gestor verificado, sem acesso indevido | **Concluído localmente** | 2 testes de provisionamento e 2 capturas em 11/11/2026 | A definir | Nomear responsável e revalidar no destino |
| B10 | Monitoramento e alertas | `/saude/`, erros, latência e indisponibilidade monitorados; alerta testado até um responsável | Pendente | A anexar | A definir | Configurar e testar observabilidade |
| B11 | Backups externos e restauração | Backup automático fora do servidor, retenção e restauração ensaiada | Pendente | Local validado; externo a anexar | A definir | Configurar cópia externa e ensaiar |
| B12 | Privacidade e LGPD | Política, base legal, finalidade, retenção, titulares e operadores revisados | Pendente | A anexar | A definir | Revisão jurídica e ajustes |
| B13 | Revisão humana do conteúdo e experiência | Karine revisa textos, jornada e apresentação; pendências e aceites registrados | Pendente | A anexar | A definir | Realizar revisão com Karine |
| B14 | Segurança externa | Dependências, exposição, autenticação, autorização e configuração pública revisadas | Pendente | Local validado; externo a anexar | A definir | Avaliar homologação externa |
| B15 | Teste de carga e capacidade | Jornadas testadas com meta definida, sem degradação inaceitável | Pendente | A anexar | A definir | Definir meta e executar carga |
| B16 | Suporte do piloto | Canal, horário, responsável e procedimento publicados | Pendente | Procedimento-base em `OPERACAO-BETA.md`; ativação a anexar | A definir | Nomear e publicar canal |
| B17 | Resposta a incidentes | Severidades, contatos, comunicação, contenção e registro documentados e ensaiados | Pendente | Procedimento-base pronto; simulação a anexar | A definir | Nomear contatos e simular |
| B18 | Rollback e recuperação | Versão anterior restaurável, migrações avaliadas e rollback ensaiado | Pendente | Procedimento-base e restore local; ensaio externo a anexar | A definir | Preparar artefato e ensaiar |
| B19 | Revalidação completa para o piloto | Suíte, migrações, desktop/celular e cada papel aprovados no destino | Pendente | Local validado em 11/11/2026; destino a anexar | A definir | Repetir após B01–B07 |
| B20 | Critérios e participantes do Beta | Comunidade, convidados, período, métricas e encerramento formalizados | Pendente | A anexar | A definir | Formalizar desenho do piloto |

## 4. Fora do primeiro lançamento — fases posteriores

| ID | Capacidade | Situação atual | Condição para entrar no roadmap de execução |
|---|---|---|---|
| P01 | Reservas de eventos | Não implementada | Escopo, estados, concorrência e cancelamento definidos |
| P02 | Pedidos | Não implementada | Jornada de reserva validada |
| P03 | Pagamentos reais | Não implementada | Provedor, cobrança, reembolso, conciliação e segurança definidos |
| P04 | Ingressos e QR Code | Não implementada | Pedido, emissão, validação e antifraude projetados |
| P05 | Check-in | Não implementada | Ingresso, operação offline/online e permissões definidos |
| P06 | Storage R2 para arquivos | Não implementada | Mídia, privacidade, limites e lifecycle definidos |
| P07 | Integração com Máquina de Cortes | Não implementada | Contrato, dados, autenticação e responsabilidades definidos |

## 5. Roteiro de decisão

1. **Escopo fechado:** comunidade + agenda, sem cobrança; falta formalizar B20.
2. **Etapa C concluída no limite local:** gestão, provisionamento, configuração, suíte, responsividade e restore validados.
3. **Preparar a opção A:** concluir B01–B07 no ambiente gerenciado.
4. **Completar operação e aceites:** concluir B10–B20 e anexar evidências.
5. **Reunião go/no-go:** somente com bloqueadores aceitos, responsáveis nomeados e rollback ensaiado.
6. **Depois do piloto:** avaliar métricas antes de priorizar P01–P07.

## 6. Histórico de controle

| Data | Alteração | Resultado |
|---|---|---|
| 02/11/2026 | Suíte e revisões locais anteriores | 49 testes aprovados; validação somente local |
| 11/11/2026 | Inventário e controle criados | NO-GO externo; bloqueadores objetivos registrados |
| 11/11/2026 | Falha do PostgreSQL local | Cópia recuperada preservada; execução restabelecida |
| 11/11/2026 | Gestão, provisionamento e preparação de produção | B08 e B09 concluídos localmente; suporte a Redis/SMTP e operação preparados |
| 11/11/2026 | Regressão completa | 63 testes, homologação, 19 capturas, backup e restore aprovados localmente; NO-GO externo mantido |
