# Stack Tecnológica — Smart Grid House

## Python 3.10+
Linguagem principal do projeto. Escolhida por ter o ecossistema mais completo para IA, cálculo numérico e dashboards web em um único ambiente.

---

## scikit-fuzzy 0.5
**O que faz:** Motor de inferência fuzzy (Mamdani).  
**Onde usamos:** Núcleo da IA — define as variáveis linguísticas (geração solar, demanda, ação bateria), as 9 regras If-Then e a defuzzificação por centroide.  
**Por que:** É a única lib Python madura para lógica fuzzy com suporte a Mamdani completo (fuzzificação → inferência → defuzzificação).

---

## NumPy 2.4
**O que faz:** Cálculos numéricos com arrays.  
**Onde usamos:** Universos de discurso (0–100 com passo 1), perfis de geração/demanda de 24h, clip de limites, interpolação de valores entre horas, pré-cômputo da superfície 3D (grade 20×20).  
**Por que:** Performance — opera sobre arrays inteiros sem loops Python.

---

## Dash 2.18
**O que faz:** Framework web reativo para dashboards.  
**Onde usamos:** Toda a interface — layout HTML, callbacks reativos (quando o usuário muda um slider, o gráfico atualiza automaticamente), stores de estado, interval para animação da simulação ao vivo.  
**Por que:** Permite criar uma aplicação web interativa completa sem escrever JavaScript. Callbacks em Python puro.

---

## Dash Bootstrap Components 1.6
**O que faz:** Componentes visuais prontos (grid, cards, tabs, botões, tooltips).  
**Onde usamos:** Sidebar (Select, RadioItems, Slider), cards de métricas, sistema de abas, botões da simulação, tooltips dos ícones "i".  
**Por que:** Dá aparência profissional sem CSS manual para cada componente.

---

## Plotly 6.7
**O que faz:** Gráficos interativos (hover, zoom, download PNG).  
**Onde usamos:** Todos os 6 gráficos (linhas 24h, donut, SoC, superfície 3D, barras clima, comparativo) + a cena visual da simulação ao vivo (shapes posicionadas com trigonometria).  
**Por que:** Integração nativa com Dash + suporte a 3D + interatividade sem código extra.

---

## Pandas 2.3
**O que faz:** Manipulação de dados tabulares.  
**Onde usamos:** Processar os dados da API de clima (JSON → DataFrame → gráfico de barras) e gerar o CSV de exportação.  
**Por que:** Converte JSON da API em tabela manipulável em 1 linha de código.

---

## Requests 2.32
**O que faz:** Chamadas HTTP.  
**Onde usamos:** Buscar dados reais de clima da API Open-Meteo (temperatura e duração do sol para São Paulo, 15 dias passados + 7 dias futuros).  
**Por que:** Lib padrão para HTTP em Python — simples, confiável, com timeout.

---

## SciPy 1.17 + NetworkX 3.6
**O que fazem:** Dependências internas do scikit-fuzzy.  
**Onde usamos:** Não diretamente — o scikit-fuzzy usa SciPy para cálculos de interpolação e NetworkX para o grafo interno de regras.  
**Por que:** Vêm junto com o scikit-fuzzy, não são opcionais.

---

## Resumo visual

```
┌─────────────────────────────────────────────┐
│  INTERFACE (o que o usuário vê)             │
│  Dash + DBC + Plotly + CSS                  │
├─────────────────────────────────────────────┤
│  LÓGICA (o cérebro)                         │
│  scikit-fuzzy + NumPy                       │
├─────────────────────────────────────────────┤
│  DADOS (alimentação externa)                │
│  Requests + Pandas + Open-Meteo API         │
└─────────────────────────────────────────────┘
```
