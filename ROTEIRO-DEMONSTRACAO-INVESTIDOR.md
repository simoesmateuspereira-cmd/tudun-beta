# TUDUN — roteiro de demonstração para investidor

## Objetivo da apresentação

Demonstrar que a TUDUN já possui uma fundação navegável para comunidades privadas e uma agenda de eventos integrada ao produto, deixando claros o valor da proposta, o funcionamento atual e o próximo marco do Beta.

**Duração sugerida:** 8 a 10 minutos, seguida de perguntas.

**Mensagem central:** a TUDUN reúne relacionamento, conteúdo e experiências em um único espaço privado, com uma base técnica preparada para evoluir para reservas, ingressos e pagamentos.

## Preparação antes da reunião

1. Abrir a prévia local da TUDUN.
2. Confirmar que os cinco eventos fictícios aparecem em **Comunidade Fictícia → Eventos**.
3. Entrar com a conta local `membro_teste` e senha fictícia `TudunTeste-2026!`.
4. Usar somente essa conta no roteiro principal; a conta administrativa pode exigir MFA.
5. Deixar uma segunda aba aberta na página inicial para retomar a apresentação se necessário.
6. Manter as capturas de `.runtime/screenshots/` como contingência visual.
7. Não executar pagamentos, alterar dados ou improvisar funcionalidades ainda não implementadas.

## Abertura — 30 segundos

**Tela:** página inicial.

**Fala sugerida:**

> “A TUDUN está sendo construída para aproximar pessoas, comunidades e experiências. Hoje vou mostrar uma jornada real dentro do produto: um participante entra em sua comunidade privada, descobre a programação e entende o acesso e as condições de cada evento.”

**Argumento de valor:** a proposta não é apenas publicar eventos; é criar continuidade entre comunidade e experiências.

## 1. Entrada e comunidade privada — 1 minuto

**Ação:** entrar com `membro_teste` e abrir a **Comunidade Fictícia**.

**Fala sugerida:**

> “Cada participante acessa somente as comunidades às quais pertence. A experiência já começa em um ambiente privado, com identidade, vínculos e permissões associadas a cada comunidade.”

**O que demonstrar:**

- Acesso autenticado.
- Comunidade privada, sem catálogo público de comunidades.
- Navegação entre visão geral e eventos.
- Identificação clara do ambiente de teste.

**Transição:**

> “Dentro dessa comunidade, a agenda passa a fazer parte da experiência do participante.”

## 2. Visão geral da comunidade — 1 minuto

**Tela:** `/comunidades/comunidade-ficticia/`.

**Fala sugerida:**

> “A visão geral reúne comunicados e uma prévia dos próximos eventos. O participante não precisa procurar a programação em outro canal: ele descobre o próximo encontro no mesmo espaço em que acompanha a comunidade.”

**O que destacar:**

- Três próximos eventos na página inicial da comunidade.
- Evento em destaque com tratamento visual discreto.
- Datas, locais e categorias visíveis antes de abrir os detalhes.
- Avisos da moderação na mesma experiência.

**Argumento de valor:** mais proximidade e menos dispersão entre comunicação e programação.

## 3. Catálogo de eventos — 2 minutos

**Ação:** clicar em **Ver agenda completa** ou **Eventos**.

**Tela:** `/comunidades/comunidade-ficticia/eventos/`.

**Fala sugerida:**

> “O catálogo apresenta diferentes formatos e situações de uma agenda real. Temos encontros incluídos na assinatura, experiências com ingresso adicional e estados como disponível, últimas vagas, esgotado e cancelado.”

**Sequência recomendada:**

1. **Encontro da Comunidade:** mostrar destaque, disponibilidade e inclusão na assinatura.
2. **Laboratório de Ideias:** mostrar últimas vagas e preço fictício de R$ 45,00.
3. **Noite de Histórias:** reforçar outro exemplo de benefício incluído.
4. **Sessão Encerrada:** mostrar como a lotação esgotada é comunicada.
5. **Encontro Cancelado:** mostrar que cancelamentos permanecem claros e não induzem uma ação comercial.

**Argumentos de valor:**

- A mesma estrutura comporta benefícios da assinatura e receitas adicionais.
- Os estados visuais tornam a disponibilidade compreensível.
- Categorias, preços, capacidade e locais estão persistidos no PostgreSQL, não apenas desenhados em telas estáticas.

**Observação transparente, se necessário:**

> “Os valores e eventos desta apresentação são fictícios. A cobrança ainda não está habilitada.”

## 4. Detalhes do evento — 1 minuto e 30 segundos

**Ação:** abrir **Encontro da Comunidade** em **Ver detalhes**.

**Tela:** `/comunidades/comunidade-ficticia/eventos/encontro-da-comunidade/`.

**Fala sugerida:**

> “Na página de detalhes, o participante encontra a proposta da experiência e todas as informações necessárias para decidir se quer participar: descrição, data, horário, local, capacidade, condição de acesso e situação.”

**O que demonstrar:**

- Hierarquia editorial e leitura confortável.
- Informações organizadas em um resumo lateral no desktop.
- Indicação de inclusão na assinatura fictícia.
- Ausência de botões falsos de compra ou reserva.

**Ação complementar:** voltar à agenda e abrir **Laboratório de Ideias** para mostrar o caso de ingresso adicional.

**Transição:**

> “A próxima evolução natural desta jornada é transformar o interesse em participação confirmada.”

## 5. Responsividade e acabamento — 45 segundos

**Ação:** mostrar as capturas de celular ou redimensionar a prévia previamente preparada.

**Fala sugerida:**

> “A experiência foi validada em desktop e celular. No celular, os cartões e as informações se reorganizam em uma coluna, preservando leitura, estados e navegação.”

**Evidência disponível:**

- Catálogo com os cinco eventos.
- Detalhes do evento.
- Visão geral da comunidade.
- Ausência de overflow horizontal nas capturas validadas.

## 6. Segurança e fundação técnica — 1 minuto

**Fala sugerida:**

> “Por trás dessa jornada existe uma base de Beta fechado: Django e PostgreSQL, autenticação, verificação de e-mail, MFA administrativo, papéis e permissões, convites, solicitações de participação e auditoria. A versão atual passou por 49 testes, incluindo acesso e isolamento entre comunidades.”

**Pontos que podem ser mencionados com segurança:**

- Comunidades, eventos e vínculos persistidos no PostgreSQL.
- Membros e convidados podem consultar eventos de suas comunidades.
- Usuários externos recebem bloqueio de acesso.
- Eventos de outra comunidade não aparecem no catálogo nem podem ser lidos pela URL local.
- Seed de demonstração idempotente, sem duplicação dos eventos.

**Limite que deve permanecer claro:** a homologação é local; segurança, carga e infraestrutura ainda precisam ser validadas no ambiente externo antes de um Beta público.

## 7. Próximo marco e encerramento — 1 minuto

**Fala sugerida:**

> “O próximo marco é completar a jornada de participação: reserva, pedido, emissão do ingresso e check-in, seguidos da integração de pagamentos. A agenda atual estabelece a base de dados, a navegação e as regras de acesso sobre as quais essa jornada será construída.”

**Fechamento:**

> “Hoje já é possível demonstrar a proposta central da TUDUN com uma jornada navegável e dados persistentes. O próximo passo é converter essa descoberta em participação confirmada e validar o fluxo completo com um grupo fechado de comunidades.”

Não apresentar reservas, pagamentos, ingressos ou check-in como funcionalidades existentes.

## Perguntas prováveis do investidor

### “A plataforma já recebe pagamentos?”

> “Ainda não. Os preços exibidos são fictícios e demonstram os dois modelos previstos: acesso incluído e ingresso adicional. Pedidos e pagamentos fazem parte da próxima etapa.”

### “O que já está funcionando de verdade?”

> “Autenticação, comunidades privadas, permissões, convites, avisos, auditoria e a agenda persistida com catálogo e detalhes. A demonstração percorre essas telas com dados reais do banco fictício.”

### “Como a TUDUN pode gerar receita?”

> “A interface já representa dois mecanismos: benefícios incluídos na assinatura e experiências vendidas separadamente. A estratégia comercial e as cobranças ainda precisam ser validadas; nenhuma receita é afirmada nesta demonstração.”

### “Como os dados de uma comunidade ficam protegidos?”

> “O acesso depende de vínculo ativo e permissões. Os testes verificam bloqueio de externos e isolamento entre comunidades. Administradores também possuem MFA e registros de auditoria.”

### “Está pronta para produção?”

> “Não. A base está homologada localmente para dados fictícios. Antes do Beta externo são necessários hospedagem, HTTPS, SMTP, cache compartilhado, monitoramento, backups externos, revisão de segurança e aceite com participantes.”

### “Qual é o próximo marco mensurável?”

> “Concluir uma jornada fictícia de reserva e ingresso, depois validar o fluxo com uma comunidade fechada antes de habilitar cobranças reais.”

## Roteiro resumido de cliques

1. Página inicial.
2. Entrar como `membro_teste`.
3. Comunidade Fictícia.
4. Ver agenda completa.
5. Encontro da Comunidade → Ver detalhes.
6. Voltar para a agenda.
7. Laboratório de Ideias → Ver detalhes.
8. Voltar para a agenda e apresentar os quatro estados.
9. Mostrar a versão de celular.
10. Encerrar com o próximo marco do Beta.

## Contingência

Se a prévia não abrir, não tentar demonstrar funcionalidades inexistentes. Reiniciar a prévia local ou utilizar as capturas de `.runtime/screenshots/`, explicando que a demonstração ao vivo será retomada em seguida. Não executar seed, migrações ou comandos operacionais durante a reunião sem necessidade.
