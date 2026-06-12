# ⚡ Smart Grid House

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Dash-2.18-008DE4?style=for-the-badge&logo=plotly&logoColor=white"/>
  <img src="https://img.shields.io/badge/Lógica-Fuzzy-10B981?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-F59E0B?style=for-the-badge"/>
</p>

> Painel de controle interativo para gestão inteligente de energia residencial com painel solar e banco de baterias. A IA decide, em tempo real, quanto carregar ou descarregar a bateria com base em **Lógica Fuzzy (Mamdani)**, com simulação visual animada do ciclo solar completo.

**Projeto A3 — Sistemas de Controle e Inteligência Artificial — USJT**

---

## 📋 Índice

- [O que é o Smart Grid House](#-o-que-é-o-smart-grid-house)
- [Como usar o painel](#-como-usar-o-painel)
  - [Sidebar — Controles](#sidebar--controles)
  - [Cards de Métricas](#cards-de-métricas)
  - [Aba Visão Geral](#aba--visão-geral)
  - [Aba Previsão & Decisões](#aba--previsão--decisões)
  - [Aba Simulação ao Vivo](#aba--simulação-ao-vivo)
- [Como executar](#-como-executar)
- [Arquitetura técnica](#-arquitetura-técnica)
- [Lógica Fuzzy — detalhamento](#-lógica-fuzzy--detalhamento)
- [Cálculo de Economia](#-cálculo-de-economia)
- [API de Clima](#-api-de-clima)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Stack tecnológica](#-stack-tecnológica)

---

## 🏠 O que é o Smart Grid House

O Smart Grid House simula o "cérebro" de uma residência com energia solar e banco de baterias. A cada hora do dia, o sistema lê dois valores — **geração solar** e **consumo da casa** — e decide de forma contínua e suave quanto carregar ou descarregar a bateria.

O diferencial em relação a sistemas convencionais é o uso de **Lógica Fuzzy**: em vez de ligar/desligar bruscamente (On/Off), a IA calcula um valor proporcional entre -100% e +100%, eliminando o efeito *chattering* e protegendo a vida útil da bateria.

O projeto inclui também um **rastreador solar físico** (Arduino) que acompanha o sol em 2 eixos, representado visualmente na simulação ao vivo com o painel rotacionando em direção ao sol.

---

## 🖥️ Como usar o painel

### Sidebar — Controles

A barra lateral esquerda concentra todos os controles do sistema. Ela acompanha o scroll da página (sticky). Cada campo tem um ícone **i** com tooltip explicativo.

#### Objetivo de Economia (%)
Slider de 0% a 50% que simula uma meta de redução de consumo. Ao aumentar esse valor, o sistema multiplica a demanda simulada da casa, forçando a IA a ser mais conservadora e priorizar o carregamento da bateria. Use 0% para ver o comportamento natural do sistema e 50% para simular uma casa com forte gestão de consumo.

#### Cenário Climático
Menu dropdown com quatro opções que alteram os perfis de geração solar e consumo da casa:

| Cenário | Geração Solar | Consumo da Casa | Quando usar |
|---------|--------------|-----------------|-------------|
| ⛅ Dia Normal | 100% (base) | 100% (base) | Dia típico de São Paulo |
| 🌧️ Chuva / Sem Sol | 30% da base | 110% da base | Dias nublados ou chuvosos |
| ☀️ Verão Extremo | 110% da base | 140% da base | Dias quentes com A/C ligado |
| ✈️ Casa Vazia | 100% da base | 20% da base | Viagem — só consumo de standby |

#### Controle da Bateria
Três opções de modo de operação:

- **🧠 Automático (IA)** — a lógica fuzzy decide a cada hora com base na geração e demanda. É o modo padrão e recomendado.
- **🔋 Forçar Carga (+)** — sobrescreve a IA e força carregamento máximo da bateria independente das condições.
- **🔌 Forçar Uso (−)** — sobrescreve a IA e força descarga máxima.

#### SoC Inicial (%)
Slider de 0% a 100% que define o nível de carga da bateria no início da simulação de 24h. Permite simular cenários como "bateria quase vazia ao amanhecer" ou "bateria cheia após dia ensolarado".

#### Painel "IA — Decisão Atual"
No rodapé da sidebar, um painel com borda verde mostra em linguagem natural o que a IA está decidindo **neste momento** (hora atual do relógio), com os valores de geração e demanda da hora. Atualiza automaticamente ao mudar qualquer controle.

---

### Cards de Métricas

Cinco cards no topo da área principal mostram os indicadores mais importantes. Todos têm altura fixa, barra de progresso colorida na base e cor dinâmica.

| Card | O que mostra | Cor |
|------|-------------|-----|
| **Bateria Atual** | SoC no início da simulação (definido pelo slider) | Verde / Amarelo / Vermelho conforme nível |
| **Bateria Estimada** | SoC projetado ao final das 24h com seta de tendência ↑↓ | Verde / Amarelo / Vermelho conforme nível |
| **Pico Geração** | Valor máximo de geração solar no dia simulado | Âmbar |
| **Pico Demanda** | Valor máximo de consumo da casa no dia simulado | Azul |
| **Demanda da IA** | Média da intensidade de atuação da IA ao longo do dia | Verde |

Quando a aba **Simulação ao Vivo** está ativa, os cards mudam para mostrar dados em tempo real: Bateria (Live), Geração Agora, Demanda Agora, Ação da IA e Hora simulada.

Cores dinâmicas da bateria:
- 🔴 Vermelho — abaixo de 20% (zona crítica)
- 🟡 Amarelo — entre 20% e 50% (zona de atenção)
- 🟢 Verde — acima de 50% (zona saudável)

---

### Aba ⚡ Visão Geral

#### Economia Estimada
Painel discreto no topo mostrando a economia diária e mensal em R$ comparando a casa com painel+bateria+IA vs. casa sem solar. Inclui nota explicativa com os parâmetros do cálculo.

#### Balanço Energético 24h
Gráfico de linhas com três séries:
- **☀️ Geração** (âmbar) — curva de produção solar hora a hora
- **⚡ Consumo** (azul) — curva de demanda da casa
- **🧠 IA Atuação** (verde pontilhado) — decisão da IA: positivo = carregando, negativo = descarregando

Uma linha vertical verde tracejada marca a **hora atual** com a anotação "Agora".

#### Divisão do Consumo
Gráfico de rosca (donut) mostrando a composição percentual do consumo. Rótulos horizontais que mudam conforme o cenário:
- Normal/Verão: Chuveiro, A/C, Geladeira, Outros
- Chuva: Chuveiro, Geladeira, Lavanderia, Outros
- Casa Vazia: Geladeira, Segurança, Standby, Outros

#### Evolução do SoC (State of Charge)
Gráfico de linha com marcadores mostrando o nível da bateria hora a hora. Faixa verde translúcida destaca a **zona ideal** (20%–80%).

---

### Aba 🔮 Previsão & Decisões

#### Botão Exportar CSV
Botão discreto no topo que baixa um arquivo `smart_grid_simulacao.csv` com todos os dados da simulação de 24h: hora, geração, demanda, ação da IA, SoC, cenário e meta de economia.

#### Comparativo: IA Fuzzy vs Controle On/Off
Gráfico de linhas mostrando duas curvas de SoC lado a lado:
- **🧠 IA Fuzzy** (verde, contínua) — controle suave e proporcional
- **⚡ On/Off** (vermelho, tracejada) — controlador bang-bang clássico (liga se sol>50% e soc<80%, desliga se sol<20% e soc>30%)

A diferença visual demonstra a superioridade do controle fuzzy: transições suaves vs. degraus bruscos, melhor aproveitamento da faixa ideal, menos ciclos de carga/descarga.

#### Linha do Tempo da IA — hora a hora
Painel visual mostrando o que a IA decidiu em cada hora do dia (00h–23h):
- **Card de destaque** com o percentual de autossuficiência do dia e a economia (R$/dia · R$/mês)
- **Barras horizontais** coloridas por estado: verde (carregando bateria), roxo (usando bateria), cinza (parado). A largura indica a intensidade da ação.
- **Texto da ação** em cada hora (ex: "carregando +15%", "usando bateria -19%")
- **Nível da bateria** na ponta direita, colorido por faixa (verde/amarelo/vermelho)
- Horas futuras aparecem com opacidade reduzida; a hora atual é destacada com seta `←`

#### Previsão de 7 Dias
Gráfico de barras com dados reais da API Open-Meteo (São Paulo):
- **Barras azuis** — consumo diário projetado (baseado na temperatura)
- **Barras âmbar** — geração solar estimada (baseada na duração do sol)

Linha verde marca o dia de hoje. Valores ajustados pelo cenário e meta de economia.

---

### Aba 🌍 Simulação ao Vivo

Simulação visual animada do ciclo completo de 24 horas com representação gráfica dos elementos do sistema.

#### Cena Visual
- **Sol** — percorre um arco parabólico da esquerda (nascer, 6h) até a direita (pôr do sol, 18h), tocando o horizonte nos extremos e atingindo o zênite ao meio-dia
- **Lua** — mesmo percurso durante a noite (18h–6h), com estrelas decorativas
- **Painel Solar** — no centro, rotaciona automaticamente apontando para o sol (simulando o rastreador Arduino), fica horizontal à noite
- **Bateria** — à esquerda, com barra de nível que enche/esvazia com cor dinâmica
- **Casa** — à direita, com janelas que acendem proporcionalmente à demanda
- **Partículas de fluxo** — pontos coloridos animados mostrando o caminho da energia: amarelo (sol→painel), verde (painel→bateria), vermelho (bateria→casa)
- **Céu** — muda de cor conforme a hora: azul escuro à noite, azul claro de dia, laranja no pôr do sol
- **Nuvens** — aparecem no cenário "Chuvoso"
- **Terreno** — base verde escura com linha de horizonte

#### Controles
- **▶ Play / ⏸ Pause / ↺ Reset** — controla a simulação
- **1× / 2× / 4×** — velocidade (1× = 0.5s por 5min simulados, ciclo completo em ~2.4min)

#### KPIs em Tempo Real
- Relógio grande (HH:MM) no topo
- Emoji + nome do cenário climático
- Geração solar e demanda nos cantos
- Decisão da IA na base (Carregando/Mantendo/Descarregando com cor)

#### Log da IA
Terminal estilo monospace mostrando as últimas 8 decisões com hora, geração, demanda, ação e SoC resultante. Registra a cada hora cheia.

---

### Botão de Download

Cada gráfico tem um ícone de câmera discreto no canto superior. Ao clicar, baixa o gráfico como imagem PNG em alta resolução (escala 2×).

---

## 🚀 Como executar

### Pré-requisitos
- Python 3.10 ou superior
- pip

### 1. Clone o repositório
```bash
git clone https://github.com/Vindilino01/Smart-Grid-House.git
cd Smart-Grid-House
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Execute
```bash
python3 app_dash.py
```

### 4. Acesse no navegador
```
http://127.0.0.1:8050
```

O servidor inicia na porta 8050. Para parar, pressione `Ctrl+C` no terminal.

---

## 🏗️ Arquitetura técnica

```
┌─────────────────────────────────────────────────────────┐
│                    ENTRADAS (Sensores)                  │
│   geracao_solar [0–100%]     demanda_casa [0–100%]      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               MOTOR FUZZY — Mamdani                     │
│  1. Fuzzificação (trimf)                                │
│  2. Inferência (9 regras If-Then)                       │
│  3. Defuzzificação (Centroide)                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                SAÍDA — Atuador                          │
│         acao_bateria [-100% a +100%]                    │
│  < 0 = descarregar  |  0 = manter  |  > 0 = carregar   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│           MALHA FECHADA — SoC Acumulado                 │
│   SoC(t+1) = clip(SoC(t) + ação × 0.15,  0, 100)       │
└─────────────────────────────────────────────────────────┘
```

O sistema roda em **malha fechada**: a ação da IA em cada hora afeta o SoC, que é acumulado ao longo das 24 horas. O fator de conversão `0.15` (modo Auto) representa a eficiência do ciclo de carga/descarga de uma bateria LiFePO4 de ~10kWh com inversor de 3kW.

A superfície de controle fuzzy é calculada sob demanda (lazy load, grade 20×20) apenas quando necessária, mantendo o startup rápido.

O horário exibido (relógio da simulação, marcador "agora") usa o fuso de **São Paulo/Brasília (UTC-3)**, independente do servidor.

---

## 🧠 Lógica Fuzzy — detalhamento

### Variáveis linguísticas

**Entradas (Antecedentes) — funções triangulares (trimf):**

| Variável | Conjunto | Pontos da trimf |
|----------|----------|-----------------|
| `geracao_solar` | baixa | [0, 0, 50] |
| `geracao_solar` | media | [0, 50, 100] |
| `geracao_solar` | alta | [50, 100, 100] |
| `demanda_casa` | baixa | [0, 0, 50] |
| `demanda_casa` | media | [0, 50, 100] |
| `demanda_casa` | alta | [50, 100, 100] |

**Saída (Consequente):**

| Variável | Conjunto | Pontos da trimf |
|----------|----------|-----------------|
| `acao_bateria` | descarregar | [-100, -100, 0] |
| `acao_bateria` | manter | [-50, 0, 50] |
| `acao_bateria` | carregar | [0, 100, 100] |

### Base de regras (matriz 3×3)

| Solar ↓ / Demanda → | Baixa | Média | Alta |
|---------------------|-------|-------|------|
| **Alta** | Carregar | Carregar | Manter |
| **Média** | Carregar | Manter | Descarregar |
| **Baixa** | Manter | Descarregar | Descarregar |

### Defuzzificação

Método **Centroide (Centro de Gravidade)**: calcula o centro de massa da área geométrica resultante da sobreposição das regras ativadas. Produz um valor contínuo e suave — nunca há saltos bruscos entre decisões consecutivas.

### Parâmetros da simulação

```python
SOC_INICIAL    = 50.0   # configurável via slider (0-100%)
TAXA_CONVERSAO = 0.15   # modo Auto — bateria dura ~10h em descarga contínua
TAXA_CONVERSAO = 0.40   # modo Manual (Forçar Carga/Uso) — mais agressivo
SOC_MIN        = 0.0    # limite inferior (clip)
SOC_MAX        = 100.0  # limite superior (clip)
```

---

## 💰 Cálculo de Economia

O painel mostra uma estimativa de economia comparando a casa **com** painel+bateria+IA vs. **sem** solar (100% rede elétrica).

### Metodologia

```
Consumo total (kWh/dia) = Σ(demanda_hora) / 100 × 3.5 kW
Custo sem solar = consumo_total × R$ 0,75/kWh

Solar direto = Σ(min(geração, demanda)) / 100 × 3.5 kW
Excesso solar = Σ(max(geração - demanda, 0)) / 100 × 3.5 kW
Bateria disponível = excesso × 0.85 (eficiência ciclo LiFePO4)
Bateria usada = min(bateria_disponível, demanda_noturna)

Consumo da rede com IA = total - solar_direto - bateria_usada
Economia = custo_sem_solar - (consumo_rede_com_ia × tarifa)
```

### Premissas
- Tarifa: R$ 0,75/kWh (média residencial SP 2024)
- Potência média da casa: 3.5 kW
- Eficiência de ciclo da bateria: 85%
- A IA maximiza o aproveitamento do excesso solar armazenando na bateria

---

## 🌤️ API de Clima

O gráfico de Previsão de 7 Dias consome a API pública **Open-Meteo** (sem chave, sem cadastro):

```
https://api.open-meteo.com/v1/forecast
  ?latitude=-23.5505
  &longitude=-46.6333
  &daily=temperature_2m_max,precipitation_sum,sunshine_duration
  &past_days=15
  &forecast_days=7
  &timezone=America/Sao_Paulo
```

Campos utilizados:
- `temperature_2m_max` — temperatura máxima diária (usada para estimar consumo)
- `sunshine_duration` — duração do sol em segundos (usada para estimar geração)

Se a API estiver indisponível, o sistema usa dados mock (25°C e 10h de sol por dia) para que o gráfico nunca fique vazio.

---

## 🗂️ Estrutura do projeto

```
Smart-Grid-House/
│
├── app_dash.py                    # Aplicação principal — lógica fuzzy + dashboard + simulação
├── assets/
│   └── custom.css                 # Estilos globais — tema escuro, cards, sidebar, tooltips
├── painel-solar-movel/
│   ├── rastreador-solar.ino       # Firmware Arduino — rastreador solar 2 eixos com LDR
│   └── README.md                  # Documentação do hardware
├── requirements.txt               # Dependências Python
├── PRD.md                         # Documento de produto e fundamentação teórica
└── readme.md                      # Este arquivo
```

### `app_dash.py` — organização interna

| Seção | Responsabilidade |
|-------|-----------------|
| Helpers de UI | `GRAPH_CONFIG`, `info_icon()`, `label_with_info()` |
| Lógica Fuzzy | `build_fuzzy_system()` — variáveis, pertinência, 9 regras |
| Pré-cômputo Fuzzy | `get_z_surface()` — superfície de controle (lazy load) |
| API de Clima | `fetch_weather_cache()` — dados reais com fallback mock |
| Layout | Estrutura HTML — sidebar + cards + tabs + gráficos + stores |
| Callback Master | `update_dashboard()` — simulação 24h, cards, gráficos, economia |
| Exportar CSV | `export_csv()` — download dos dados simulados |
| Cards Live | `update_cards_live()` — atualiza cards na tab de simulação |
| Simulação | `sky_color()`, `build_sim_scene()` — cena visual animada |
| Sim Controls | `sim_controls()` — play/pause/reset/velocidade |
| Sim Tick | `sim_tick()` — avança 5min×velocidade por tick (500ms) |
| Sim Render | `render_sim()` — renderiza cena + controles + log |

---

## 📦 Stack tecnológica

| Biblioteca | Versão | Papel |
|------------|--------|-------|
| Dash | 2.18 | Framework web reativo — layout + callbacks |
| Dash Bootstrap Components | 1.6 | Grid, cards, tabs, tooltips, select, radio |
| Plotly | 6.7 | Gráficos interativos (linha, rosca, barra, comparativo) + cena visual da simulação ao vivo (shapes posicionadas com trigonometria) |
| NumPy | 2.4 | Arrays, universos de discurso, cálculos matriciais |
| scikit-fuzzy | 0.5 | Motor de inferência fuzzy Mamdani |
| SciPy | 1.17 | Dependência interna do scikit-fuzzy |
| NetworkX | 3.6 | Dependência interna do scikit-fuzzy |
| Pandas | 2.3 | Manipulação dos dados da API de clima + exportação CSV |
| Requests | 2.32 | Chamada HTTP para a API Open-Meteo |

### Hardware complementar — `painel-solar-movel/`

O repositório inclui o firmware Arduino de um **rastreador solar de 2 eixos** com 4 sensores LDR. O sistema lê a diferença de luminosidade entre os sensores e ajusta dois servomotores para manter o painel sempre apontado para o sol. Tolerância configurável (`tol = 90`) evita micro-movimentos desnecessários.

Na simulação ao vivo, o painel solar rotaciona visualmente seguindo o sol — representando o comportamento do hardware real.

---

## 🔄 Comparativo: IA Fuzzy vs On/Off

| Aspecto | IA Fuzzy (Mamdani) | Controle On/Off |
|---------|-------------------|-----------------|
| Transições | Suaves e contínuas | Degraus bruscos |
| Chattering | Eliminado | Presente |
| Vida útil da bateria | Preservada | Degradada |
| Aproveitamento solar | Máximo (proporcional) | Parcial (tudo ou nada) |
| Faixa ideal (20-80%) | Mantida naturalmente | Violada frequentemente |
| Complexidade | 9 regras + centroide | 2 thresholds |

---

*Projeto A3 — Sistemas de Controle e Inteligência Artificial — USJT*
