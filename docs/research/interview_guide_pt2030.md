# Guião de Entrevista: Validação EVF Portugal 2030 - Consultoras PT2030

**Versão**: 1.0
**Data**: Novembro 2025
**Duração**: 45-50 minutos
**Objetivo**: Identificar os 30 requisitos PT2030 mais críticos para priorização no Sprint 2

---

## 📋 Pré-Entrevista

### Checklist de Preparação

- [ ] Enviar consentimento GDPR 24h antes
- [ ] Enviar resumo do produto (1 pager)
- [ ] Confirmar agendamento 12h antes
- [ ] Preparar ferramentas de gravação (com consentimento)
- [ ] Ter à mão: SPRINT_1_FINAL_SUMMARY.md para demo

### Contexto para o Entrevistado (enviar antes)

> Estamos a desenvolver uma plataforma SaaS inovadora que automatiza a preparação de Estudos de Viabilidade Financeira (EVF) para candidaturas PT2030, PRR e IFIC. A nossa solução utiliza IA para reduzir o tempo de preparação de EVFs de 24 horas para ~3 horas, mantendo 100% de compliance com as normas portuguesas.
>
> Esta entrevista tem como objetivo validar com profissionais experientes quais os requisitos de compliance e validação mais críticos na prática, para priorizar o desenvolvimento da nossa engine de validação automática.

---

## 🎯 Estrutura da Entrevista (50 min)

### 1. Abertura e Contexto (5 min)

**Script de Abertura:**

> "Muito obrigado por disponibilizar o seu tempo. Como mencionei no email, estou a desenvolver uma plataforma de automação de EVFs para PT2030 e gostaria de validar alguns pressupostos técnicos com profissionais experientes como você.
>
> A entrevista durará cerca de 45 minutos. Posso gravar para efeitos de notas internas? Todos os dados serão tratados de forma confidencial e anónima.
>
> Antes de começarmos, gostaria de saber um pouco sobre o seu background:"

**Perguntas de Contexto:**

1. **Experiência**: "Há quanto tempo trabalha com candidaturas PT2030/PRR/IFIC?"
   - _Objetivo_: Estabelecer credibilidade do entrevistado
   - _Notar_: Anos de experiência, volume de candidaturas/ano

2. **Perfil de Clientes**: "Que tipo de empresas costuma apoiar? (sector, dimensão, região)"
   - _Objetivo_: Entender contexto das respostas
   - _Notar_: PME vs grandes empresas, sectores específicos, regiões (Norte, Centro, Sul)

---

### 2. Dores Atuais com PT2030 (10 min)

**Introdução:**
> "Gostaria de começar por entender os principais desafios que encontra no processo atual de preparação de EVFs."

**P3. Principal Bottleneck**
"Qual é a etapa que mais tempo consome na preparação de um EVF típico?"

- [ ] Recolha de documentos do cliente
- [ ] Validação de elegibilidade
- [ ] Cálculos financeiros (VALF/TRF)
- [ ] Redação da narrativa técnica
- [ ] Verificação de compliance com avisos
- [ ] Preparação do dossier final
- [ ] Outro: _______________

_Notas de follow-up_: Porquê? Quanto tempo (horas/dias)? Como mitiga atualmente?

**P4. Principal Fonte de Rejeições**
"Na sua experiência, quais são as causas mais frequentes de rejeição ou pedidos de esclarecimento por parte do Balcão 2030?"

- [ ] Elegibilidade (PME, sector, despesas)
- [ ] Documentação insuficiente/incorreta
- [ ] Erros nos cálculos financeiros
- [ ] VALF ou TRF fora dos limites
- [ ] Narrativa técnica inadequada
- [ ] Incumprimento de requisitos específicos do aviso
- [ ] Outro: _______________

_Notas de follow-up_: Frequência (% de candidaturas)? Exemplos concretos?

**P5. Documentos Mais Problemáticos**
"Que documentos são mais difíceis de obter ou validar dos clientes?"

- [ ] SAF-T (Ficheiro contabilístico)
- [ ] Demonstrações financeiras certificadas
- [ ] Declaração de minimis
- [ ] Compromissos/declarações específicas
- [ ] Faturas/contratos de despesas elegíveis
- [ ] Certidões (fiscal, segurança social)
- [ ] Outro: _______________

_Notas de follow-up_: O que torna esses documentos problemáticos? Erros comuns?

**P6. Mudanças Regulamentares**
"Com que frequência precisa de atualizar o seu conhecimento sobre requisitos PT2030/PRR devido a mudanças na regulamentação?"

- [ ] Semanalmente (avisos novos, FAQs)
- [ ] Mensalmente (portarias, despachos)
- [ ] Trimestralmente (grandes revisões)
- [ ] Anualmente
- [ ] Raramente

_Notas de follow-up_: Como se mantém atualizado? Onde consulta informação oficial?

**P7. Automação Atual**
"Utiliza atualmente alguma ferramenta de software para apoiar a preparação de EVFs?"

- [ ] Excel/Google Sheets (templates próprios)
- [ ] Software contabilístico (SAF-T)
- [ ] Ferramentas de cálculo financeiro
- [ ] Plataformas de gestão de candidaturas
- [ ] Apenas processadores de texto
- [ ] Outro: _______________

_Notas de follow-up_: O que funciona bem? O que gostaria que fosse automatizado?

---

### 3. Requisitos de Compliance Mais Críticos (15 min)

**Introdução:**
> "Agora gostaria de focar nos requisitos específicos de PT2030 que são mais críticos para o sucesso de uma candidatura."

**P8. Top 5 Regras de Elegibilidade**
"Quais são as 5 regras de elegibilidade que verifica SEMPRE em todas as candidaturas, sem exceção?"

Exemplo: "Critérios de PME (colaboradores, volume de negócios)"

1. ________________________________
2. ________________________________
3. ________________________________
4. ________________________________
5. ________________________________

_Notas_: Para cada uma, perguntar: "Esta regra causa frequentemente rejeições?"

**P9. Requisitos Específicos por Aviso**
"Os requisitos variam muito entre diferentes avisos (e.g., Inovação Produtiva vs Qualificação PME)?"

- [ ] Sim, são muito diferentes
- [ ] Parcialmente, alguns requisitos comuns
- [ ] Não, maioria é comum

_Follow-up_: Pode dar exemplos de requisitos únicos a avisos específicos?

**P10. Cálculo VALF - Casos Edge**
"No cálculo do VALF (Valor Atual Líquido dos Fluxos Financeiros), quais são os casos que requerem mais atenção ou interpretação?"

- [ ] Escolha da taxa de desconto
- [ ] Estimativa de cash-flows futuros
- [ ] Tratamento de despesas não elegíveis
- [ ] Ajustes por região/sector
- [ ] Cenários de sensibilidade
- [ ] Outro: _______________

_Notas_: Existem regras claras ou é interpretativo? Como documenta a metodologia?

**P11. Cálculo TRF - Variações**
"O cálculo da Taxa de Rendibilidade Financeira (TRF) é uniforme ou varia consoante o programa/aviso?"

- [ ] Totalmente uniforme (mesma fórmula sempre)
- [ ] Varia ligeiramente (ajustes por programa)
- [ ] Muito diferente entre programas

_Follow-up_: Quais as variações mais comuns? Como identifica qual metodologia usar?

**P12. Intensidade de Auxílio - Validação**
"Como valida que a intensidade de auxílio solicitada está dentro dos limites permitidos?"

- [ ] Consulta tabela por região/dimensão empresa
- [ ] Verifica majorações aplicáveis (cooperação, PME)
- [ ] Confirma com regulamento europeu
- [ ] Utiliza calculadora do Balcão 2030
- [ ] Outro: _______________

_Notas_: Erros comuns nesta validação? Existe alguma margem de interpretação?

**P13. Despesas Elegíveis - Exclusões**
"Quais são as categorias de despesas que são mais frequentemente contestadas ou rejeitadas?"

Exemplos:
- Despesas com pessoal (critérios de adicionalidade)
- Equipamentos (usado vs novo)
- Serviços externos (elegibilidade de consultoria)
- Terrenos e edifícios (limites %)

_Notas_: Para cada categoria mencionada, perguntar critérios específicos que aplica.

**P14. Cross-Validation SAF-T**
"Quando recebe o ficheiro SAF-T do cliente, que validações específicas realiza para confirmar a veracidade dos dados financeiros?"

- [ ] Coerência com demonstrações financeiras
- [ ] Validação de NIF de fornecedores
- [ ] Natureza das despesas (CAE)
- [ ] Datas e valores de faturas
- [ ] Reconciliação bancária
- [ ] Outro: _______________

_Notas_: Já encontrou discrepâncias graves? Que sinais de alerta procura?

**P15. Requisitos Regionais**
"Os requisitos de elegibilidade ou intensidade variam significativamente entre regiões (Norte, Centro, Alentejo, Lisboa, etc.)?"

- [ ] Sim, muito (diferentes tabelas de intensidade)
- [ ] Moderadamente (algumas especificidades)
- [ ] Pouco (praticamente uniforme)

_Follow-up_: Pode dar exemplos de variações regionais que já causaram confusão?

---

### 4. Validação Documental (10 min)

**Introdução:**
> "Gostaria agora de entender melhor o processo de validação e preparação documental."

**P16. Checklist Documental Mínima**
"Qual é o conjunto mínimo de documentos que NUNCA pode faltar numa candidatura PT2030?"

Lista:
1. ________________________________
2. ________________________________
3. ________________________________
4. ________________________________
5. ________________________________
6. ________________________________
7. ________________________________

_Notas_: Para cada documento, perguntar: "Que validações específicas realiza?"

**P17. Extração de Metadados**
"Quando recebe documentos (SAF-T, faturas, contratos), que informação extrai sistematicamente para validação?"

Exemplos:
- NIF do fornecedor
- CAE da empresa
- Montantes e datas
- Natureza da despesa
- Conformidade com projeto

_Notas_: Faz isso manualmente? Quanto tempo demora em média?

**P18. Dossier de Submissão - Organização**
"Como organiza o dossier final de submissão? Existe um padrão que facilita a análise pelo Balcão 2030?"

- [ ] Sigo estrutura específica (qual?)
- [ ] Uso template fornecido pelo Balcão
- [ ] Organização livre mas lógica
- [ ] Depende do aviso

_Follow-up_: Já recebeu feedback sobre organização de dossiers que facilitou/dificultou análise?

**P19. Declarações e Compromissos**
"Que declarações ou termos de compromisso são obrigatórios e frequentemente esquecidos?"

- [ ] Declaração de minimis
- [ ] Compromisso de manutenção de posto de trabalho
- [ ] Declaração de não dívidas à Segurança Social/AT
- [ ] Termo de responsabilidade de dados
- [ ] Outro: _______________

_Notas_: Modelos standard ou específicos por aviso?

---

### 5. Cálculos Financeiros e Auditoria (10 min)

**Introdução:**
> "Vamos agora focar nos aspetos mais técnicos dos cálculos financeiros."

**P20. Parâmetros Regionais/Sectoriais**
"Mantém uma base de dados de parâmetros (taxas de desconto, intensidades, majorações) por região/sector/programa?"

- [ ] Sim, tenho uma tabela que actualizo
- [ ] Consulto sempre as portarias
- [ ] Uso calculadora do Balcão 2030
- [ ] Outro: _______________

_Follow-up_: Como se certifica que os parâmetros estão atualizados?

**P21. Auditoria de Cálculos**
"Como garante que não há erros nos cálculos financeiros (VALF, TRF, cash-flows)?"

- [ ] Revisão dupla (outro colega)
- [ ] Ferramentas automatizadas
- [ ] Comparação com casos anteriores
- [ ] Cenários de teste
- [ ] Outro: _______________

_Notas_: Já teve casos de erros de cálculo que passaram despercebidos? Consequências?

**P22. Rastreabilidade de Cálculos**
"Como documenta a metodologia e pressupostos usados nos cálculos para eventual auditoria?"

- [ ] Anexos técnicos detalhados
- [ ] Comentários em Excel
- [ ] Relatório de fundamentação
- [ ] Logs/histórico de cálculos
- [ ] Outro: _______________

_Follow-up_: Já foi questionado sobre cálculos numa auditoria? Como respondeu?

**P23. Ferramentas de Validação Cruzada**
"Utiliza algum método para validar que os valores financeiros da candidatura são consistentes com a realidade da empresa?"

- [ ] Comparação com anos anteriores
- [ ] Benchmarking sectorial
- [ ] Rácios financeiros
- [ ] Validação com cliente
- [ ] Outro: _______________

_Notas_: Que sinais de alerta indicam valores irrealistas?

---

### 6. Encerramento e Visão de Produto (5 min)

**Introdução:**
> "Estamos quase a terminar. Gostaria apenas de validar a nossa visão de produto."

**P24. Value Proposition - Validação**
"Se existisse uma plataforma que reduzisse o tempo de preparação de um EVF de 24h para 3h, mantendo 100% de compliance, qual seria o valor máximo mensal que consideraria pagar por essa solução?"

- [ ] <€100/mês
- [ ] €100-€300/mês
- [ ] €300-€500/mês
- [ ] €500-€1,000/mês
- [ ] >€1,000/mês
- [ ] Depende do volume de candidaturas

_Notas_: O que mais valorizaria numa solução dessas? Que preocupações teria?

**P25. Funcionalidade Mais Valiosa**
"De entre as seguintes funcionalidades, qual seria a mais valiosa para si?"

- [ ] Validação automática de elegibilidade (PT2030 rules)
- [ ] Extração automática de dados do SAF-T
- [ ] Cálculo automático de VALF/TRF
- [ ] Geração de narrativa técnica com IA
- [ ] Checklist documental inteligente
- [ ] Audit trail completo de todas as operações

_Ranking_: Pedir para ordenar top 3.

**Encerramento:**

> "Muito obrigado pelo seu tempo e pelas suas perspetivas extremamente valiosas. As suas respostas vão ajudar-nos a priorizar corretamente o desenvolvimento da plataforma.
>
> Como agradecimento, gostaria de oferecer-lhe early access gratuito à plataforma por 3 meses quando lançarmos a versão beta (prevista para Janeiro 2026). Teria interesse?
>
> Posso contactá-lo novamente se surgirem dúvidas pontuais durante o desenvolvimento?"

**Notas Pós-Entrevista:**
- [ ] Enviar email de agradecimento (máx 24h)
- [ ] Partilhar findings (se solicitado)
- [ ] Adicionar à lista de early adopters (se interesse)

---

## 📊 Framework de Análise de Respostas

### Matriz de Priorização de Requisitos

Para cada requisito/regra mencionado, avaliar:

| Critério | Peso | Pontuação (1-5) | Score Ponderado |
|----------|------|-----------------|-----------------|
| **Frequência de Menção** (quantas entrevistas mencionaram) | 40% | ___/5 | ___ |
| **Impacto em Rejeições** (% de rejeições causadas) | 30% | ___/5 | ___ |
| **Complexidade de Validação** (fácil=5, difícil=1) | 20% | ___/5 | ___ |
| **Cobertura Regulamentar** (abrangência de programas) | 10% | ___/5 | ___ |
| **TOTAL** | 100% | - | **___/5** |

**Escala de Pontuação:**
- **5**: Muito Alto (mencionado por 5+ consultoras / >20% rejeições / muito fácil / todos os programas)
- **4**: Alto
- **3**: Médio
- **2**: Baixo
- **1**: Muito Baixo (mencionado por 1 consultora / <5% rejeições / muito difícil / programa específico)

### Template de Consolidação (após 3-5 entrevistas)

```markdown
## Requisito: [Nome do Requisito]

**ID**: PT2030-XXX-NNN
**Categoria**: Elegibilidade | Intensidade | Despesas | Cálculo | Documental
**Regulamento Base**: Portaria XXX/2022, Art. XX

### Fontes
- Entrevista #1 (Consultora A): "quote relevante"
- Entrevista #3 (Consultora C): "quote relevante"
- Entrevista #5 (Consultora E): "quote relevante"

### Scoring
- Frequência: 3/5 entrevistas = 3/5 → Score: 1.2/2.0
- Impacto: ~15% rejeições = 3/5 → Score: 0.9/1.5
- Complexidade: Validação moderada = 3/5 → Score: 0.6/1.0
- Cobertura: Maioria programas = 4/5 → Score: 0.4/0.5
- **TOTAL**: **3.1/5.0** → **Prioridade: ALTA**

### Implementação Sugerida
```yaml
rules:
  - id: "PT2030-XXX-NNN"
    name: "[Nome do Requisito]"
    regulation: "Portaria XXX/2022, Art. XX"
    validator: "validators.[categoria].[função]"
    priority: "high"
    parameters:
      [parâmetros específicos]
```

### Casos Edge Identificados
1. [Descrição caso edge #1]
2. [Descrição caso edge #2]
```

---

## ✅ Checklist de Execução

### Antes da Entrevista
- [ ] Consentimento GDPR enviado e confirmado
- [ ] One-pager do produto enviado
- [ ] Confirmação de agendamento recebida
- [ ] Ferramenta de gravação testada
- [ ] Documentação Sprint 1 revista (para demo se necessário)

### Durante a Entrevista
- [ ] Gravar (com consentimento)
- [ ] Tomar notas estruturadas (usar este template)
- [ ] Pedir exemplos concretos/cases
- [ ] Anotar quotes relevantes textuais
- [ ] Observar linguagem corporal/hesitações
- [ ] Fazer follow-ups quando resposta superficial

### Depois da Entrevista
- [ ] Transcrever notas principais (máx 2h depois)
- [ ] Identificar requisitos mencionados
- [ ] Tag por categoria (elegibilidade, cálculo, documental)
- [ ] Adicionar à matriz de priorização
- [ ] Enviar email de agradecimento
- [ ] Arquivar gravação (se aplicável)

---

## 📝 Notas Metodológicas

### Boas Práticas
1. **Escuta Ativa**: Deixar o entrevistado falar, não interromper
2. **Neutralidade**: Não "vender" a solução, apenas validar pressupostos
3. **Profundidade**: Fazer follow-ups para obter exemplos concretos
4. **Flexibilidade**: Se um tópico gera insights, aprofundar mesmo que fora do guião
5. **Timing**: Respeitar os 50 min, priorizar P8-P15 se tempo curto

### Sinais de Alerta (Red Flags)
- Entrevistado muito genérico (sem exemplos concretos) → Pode não ter experiência suficiente
- Contradições nas respostas → Pode não estar a ser honesto
- Foco excessivo em vender os seus serviços → Redirecionar para validação técnica

### Indicadores de Sucesso da Entrevista
- ✅ Obteve 10+ requisitos específicos mencionados
- ✅ Identificou 3+ casos edge/pitfalls
- ✅ Confirmou value proposition (disposição a pagar)
- ✅ Entrevistado demonstrou interesse em early access

---

**Versão**: 1.0
**Última Atualização**: 9 Novembro 2025
**Próxima Revisão**: Após 2ª entrevista (ajustar perguntas com base em feedback)
