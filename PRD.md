# PRD — Smart Grid House
## Gestão Inteligente de Energia com Lógica Fuzzy

**Projeto A3 — Sistemas de Controle e Inteligência Artificial**  
**Metodologia:** Software-in-the-Loop (SITL) — Simulação Computacional  
**Status:** `fase de testes`

---

## 1. Visão Geral

Este projeto implementa um **Controlador Inteligente de Gestão de Energia** para residências sustentáveis equipadas com painéis solares e banco de baterias (*Smart Grid*). O sistema atua como o "cérebro" da matriz energética residencial, tomando decisões autônomas e em tempo real sobre o fluxo de energia com base em **Lógica Fuzzy (Nebulosa)**.

### Problema que resolve

Sistemas comerciais de gerenciamento de energia (BMS) de baixo custo operam com **Lógica Booleana (On/Off)**, o que causa três problemas principais:

| Problema | Impacto | Como a IA resolve |
|----------|---------|-------------------|
| **Chattering** | Liga/desliga dezenas de vezes por minuto, desgastando relés e chaves | Controle suave e contínuo via graus de pertinência |
| **Degradação da bateria** | Correntes bruscas aceleram o desgaste químico (efeito Joule) | Ajuste proporcional da corrente — como um dimmer |
| **Curtailment solar** | Excesso de energia é desperdiçado por falta de controle fino | Absorção gradual previne sobrecarga |

---

## 2. Objetivos

- Implementar um controlador baseado em **Lógica Fuzzy (Inferência de Mamdani)**
- Simular **24 horas de operação** em malha fechada com rastreamento de SoC
- Gerar um **dashboard interativo** com os resultados da simulação
- Demonstrar a superioridade do controle fuzzy frente ao controle On/Off clássico

---

## 3. Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────┐
│                  ENTRADAS (Sensores)                │
│   Geração Solar [0–100%]   Demanda da Casa [0–100%] │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│              MOTOR FUZZY (Mamdani)                  │
│  1. Fuzzificação  →  2. Inferência  →  3. Defuzz.   │
│     (trimf)            (9 regras)     (centroide)   │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│               SAÍDA (Atuador)                       │
│         Ação na Bateria [-100% a +100%]             │
│  Negativo = descarregar | Zero = manter | Positivo = carregar  │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│         MALHA FECHADA — SoC Acumulado               │
│   SoC(t+1) = SoC(t) + ação × taxa_conversão        │
│   Limites: 0% ≤ SoC ≤ 100%                         │
└─────────────────────────────────────────────────────┘
```

---

## 4. Lógica Fuzzy — Detalhamento

### 4.1 Variáveis Linguísticas

**Entradas (Antecedentes):**

| Variável | Universo | Conjuntos |
|----------|----------|-----------|
| `geracao_solar` | [0, 100] % | baixa, média, alta |
| `demanda_casa` | [0, 100] % | baixa, média, alta |

**Saída (Consequente):**

| Variável | Universo | Conjuntos |
|----------|----------|-----------|
| `acao_bateria` | [-100, 100] % | descarregar, manter, carregar |

Todas as funções de pertinência são **triangulares (trimf)**.

### 4.2 Base de Regras (Matriz 3×3)

| Solar ↓ / Demanda → | Baixa | Média | Alta |
|---------------------|-------|-------|------|
| **Alta** | Carregar | Carregar | Manter |
| **Média** | Carregar | Manter | Descarregar |
| **Baixa** | Manter | Descarregar | Descarregar |

### 4.3 Defuzzificação

Método utilizado: **Centroide (Centro de Gravidade)** — calcula o centro de massa da área geométrica gerada pela sobreposição das regras ativadas, produzindo um valor contínuo e suave.

---

## 5. Simulação — Perfil de 24 Horas

| Período | Geração Solar | Demanda da Casa | Comportamento esperado da IA |
|---------|--------------|-----------------|------------------------------|
| 00h–05h | 0% | 10–15% | Descarregar levemente / manter |
| 06h–11h | 5–100% | 20–80% | Carregar progressivamente |
| 12h–15h | 70–100% | 20–40% | Carregar com força máxima |
| 16h–19h | 2–50% | 40–100% | Transição para descarga |
| 20h–23h | 0% | 20–85% | Descarregar para suprir a casa |

**Parâmetros da simulação:**

```python
SOC_INICIAL     = 50.0   # bateria começa na metade
SOC_MIN         = 0.0    # limite inferior
SOC_MAX         = 100.0  # limite superior
TAXA_CONVERSAO  = 0.3    # fator de conversão ação → variação do SoC por hora
```

---

## 6. Dashboard — Visualizações

O arquivo `smart_grid_dashboard.html` gerado contém **3 gráficos interativos**:

### Gráfico 01 — Simulação das 24 Horas
Exibe as três curvas do sistema ao longo do dia: geração solar, demanda residencial e ação da IA na bateria. Permite zoom, pan e hover com valores exatos por hora.

### Gráfico 02 — State of Charge (SoC) em Malha Fechada
Mostra o nível de carga real da bateria acumulado hora a hora como resultado das decisões da IA. Destaca a zona ótima de operação (30–80%) e os pontos de máximo e mínimo do ciclo.

### Gráfico 03 — Superfície de Controle 3D
Mapa completo de decisão do controlador fuzzy para qualquer combinação de geração solar × demanda. Pode ser rotacionado livremente. Demonstra a continuidade e suavidade do controle — ausência dos degraus do controle On/Off.

---

## 7. Stack Tecnológica

| Tecnologia | Versão | Papel no Projeto |
|------------|--------|-----------------|
| Python | 3.14+ | Linguagem principal |
| NumPy | 2.4.4 | Arrays, cálculos matemáticos, universos de discurso |
| scikit-fuzzy | 0.5.0 | Motor de inferência fuzzy (Mamdani) |
| networkx | 3.6.1 | Dependência interna do scikit-fuzzy |
| Plotly | 6.7.0 | Geração dos gráficos interativos e exportação HTML |

---

## 8. Estrutura do Repositório

```
smart-grid-fuzzy/
│
├── ia_plotly.py                  # Script principal — lógica fuzzy + geração do dashboard
├── smart_grid_dashboard.html     # Dashboard interativo gerado (abrir no navegador)
├── requirements.txt              # Dependências do projeto
├── PRD.md                        # Este documento
└── README.md                     # Instruções de instalação e uso
```

---

## 9. Como Executar

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/smart-grid-fuzzy.git
cd smart-grid-fuzzy

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o controlador e gere o dashboard
python ia_plotly.py

# 4. Abra o dashboard no navegador
#    (o arquivo será salvo na mesma pasta do script)
start smart_grid_dashboard.html   # Windows
open smart_grid_dashboard.html    # macOS
xdg-open smart_grid_dashboard.html  # Linux
```

---

## 10. Resultados Obtidos

| Métrica | Valor |
|---------|-------|
| SoC inicial | 50% |
| Ação máxima de carregamento | +62.9% |
| Ação máxima de descarga | -66.6% |
| Regras fuzzy na base | 9 |
| Horas simuladas | 24h |
| Resolução do universo de discurso | 1% |
| Resolução da superfície 3D | 25×25 pontos |

> O fato de a ação máxima da IA nunca atingir ±100% confirma o comportamento **proporcional e suave** do controlador fuzzy, em contraste com o comportamento On/Off de sistemas convencionais.

---

## 11. Fundamentação Teórica

- **Lógica Fuzzy:** Zadeh, L. A. (1965). *Fuzzy sets*. Information and Control, 8(3), 338–353.
- **Inferência de Mamdani:** Mamdani, E. H. & Assilian, S. (1975). *An experiment in linguistic synthesis with a fuzzy logic controller*. International Journal of Man-Machine Studies, 7(1), 1–13.
- **Defuzzificação por Centroide:** Ross, T. J. (2010). *Fuzzy Logic with Engineering Applications* (3rd ed.). Wiley.
- **Smart Grids e controle de energia:** Fang, X. et al. (2012). *Smart Grid — The New and Improved Power Grid*. IEEE Communications Surveys & Tutorials, 14(4).

---

## 12. Limitações e Trabalhos Futuros

- O modelo atual não considera variações de temperatura da bateria
- O perfil de geração solar e demanda é fixo (não usa dados meteorológicos reais)
- Possível evolução: integrar API de previsão do tempo para tornar o perfil dinâmico
- Possível evolução: adicionar a variável SoC atual como terceira entrada do sistema fuzzy, criando um controlador adaptativo completo

---

*Projeto A3 — Sistemas de Controle e Inteligência Artificial*
