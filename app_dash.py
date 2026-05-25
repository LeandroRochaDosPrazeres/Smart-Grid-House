import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# HELPERS DE UI
# ──────────────────────────────────────────────
# Config de toolbar: apenas botão de download, discreto
GRAPH_CONFIG = {
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d",
        "autoScale2d", "resetScale2d", "hoverClosestCartesian",
        "hoverCompareCartesian", "zoom3d", "pan3d", "orbitRotation",
        "tableRotation", "resetCameraDefault3d", "resetCameraLastSave3d",
        "hoverClosest3d", "zoomInGeo", "zoomOutGeo", "resetGeo",
        "hoverClosestGeo", "sendDataToCloud", "toggleHover", "resetViews",
        "toggleSpikelines", "resetViewMapbox"
    ],
    "displayModeBar": True,
    "displaylogo": False,
    "toImageButtonOptions": {"format": "png", "filename": "smart_grid_chart", "scale": 2},
}

def info_icon(tooltip_id, text):
    """Ícone i minimalista com tooltip padronizado."""
    return html.Span([
        html.Span("i", id=tooltip_id, className="info-icon"),
        dbc.Tooltip(
            text,
            target=tooltip_id,
            placement="right",
            delay={"show": 100, "hide": 50},
        )
    ], style={"display": "inline-flex", "alignItems": "center"})


def label_with_info(label_text, tooltip_id, tooltip_text):
    """Label de sidebar com ícone i alinhado."""
    return html.Div([
        html.Span(label_text, className="form-label"),
        info_icon(tooltip_id, tooltip_text)
    ], className="sidebar-label-row")

# ──────────────────────────────────────────────
# LÓGICA FUZZY BASE
# ──────────────────────────────────────────────
def build_fuzzy_system():
    geracao_solar = ctrl.Antecedent(np.arange(0, 101, 1), 'geracao_solar')
    demanda_casa  = ctrl.Antecedent(np.arange(0, 101, 1), 'demanda_casa')
    acao_bateria  = ctrl.Consequent(np.arange(-100, 101, 1), 'acao_bateria')

    geracao_solar['baixa'] = fuzz.trimf(geracao_solar.universe, [0,   0,  50])
    geracao_solar['media'] = fuzz.trimf(geracao_solar.universe, [0,  50, 100])
    geracao_solar['alta']  = fuzz.trimf(geracao_solar.universe, [50, 100, 100])

    demanda_casa['baixa'] = fuzz.trimf(demanda_casa.universe, [0,   0,  50])
    demanda_casa['media'] = fuzz.trimf(demanda_casa.universe, [0,  50, 100])
    demanda_casa['alta']  = fuzz.trimf(demanda_casa.universe, [50, 100, 100])

    acao_bateria['descarregar'] = fuzz.trimf(acao_bateria.universe, [-100, -100,  0])
    acao_bateria['manter']      = fuzz.trimf(acao_bateria.universe, [ -50,    0, 50])
    acao_bateria['carregar']    = fuzz.trimf(acao_bateria.universe, [   0,  100, 100])

    regras = [
        ctrl.Rule(geracao_solar['alta']  & demanda_casa['baixa'], acao_bateria['carregar']),
        ctrl.Rule(geracao_solar['alta']  & demanda_casa['media'], acao_bateria['carregar']),
        ctrl.Rule(geracao_solar['alta']  & demanda_casa['alta'],  acao_bateria['manter']),
        ctrl.Rule(geracao_solar['media'] & demanda_casa['baixa'], acao_bateria['carregar']),
        ctrl.Rule(geracao_solar['media'] & demanda_casa['media'], acao_bateria['manter']),
        ctrl.Rule(geracao_solar['media'] & demanda_casa['alta'],  acao_bateria['descarregar']),
        ctrl.Rule(geracao_solar['baixa'] & demanda_casa['baixa'], acao_bateria['manter']),
        ctrl.Rule(geracao_solar['baixa'] & demanda_casa['media'], acao_bateria['descarregar']),
        ctrl.Rule(geracao_solar['baixa'] & demanda_casa['alta'],  acao_bateria['descarregar']),
    ]
    return ctrl.ControlSystem(regras)

sistema_fuzzy = build_fuzzy_system()
simulador = ctrl.ControlSystemSimulation(sistema_fuzzy)

# ──────────────────────────────────────────────
# PRÉ-COMPULAR SUPERFÍCIE 3D PARA PERFORMANCE
# ──────────────────────────────────────────────
x_grid = np.linspace(0, 100, 20)
y_grid = np.linspace(0, 100, 20)
Z_surface = np.zeros((20, 20))
for i, x_val in enumerate(x_grid):
    for j, y_val in enumerate(y_grid):
        simulador.input['geracao_solar'] = x_val
        simulador.input['demanda_casa'] = y_val
        try:
            simulador.compute()
            Z_surface[j, i] = simulador.output['acao_bateria']
        except:
            Z_surface[j, i] = 0

# ──────────────────────────────────────────────
# API DE CLIMA (Memória local simples)
# ──────────────────────────────────────────────
def fetch_weather_cache():
    url = "https://api.open-meteo.com/v1/forecast?latitude=-23.5505&longitude=-46.6333&current=temperature_2m,weather_code,is_day&daily=temperature_2m_max,precipitation_sum,sunshine_duration&past_days=15&forecast_days=7&timezone=America%2FSao_Paulo"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        pass

    # MOCK DATA FALLBACK
    hoje = datetime.now()
    datas = [(hoje + timedelta(days=i-14)).strftime("%Y-%m-%d") for i in range(22)]
    return {
        "current": {"temperature_2m": 25.0, "weather_code": 1, "is_day": 1},
        "daily": {
            "time": datas,
            "temperature_2m_max": [25.0]*22,
            "sunshine_duration": [36000.0]*22,
        }
    }


def weather_code_to_info(code, is_day=1):
    """Converte WMO weather code da Open-Meteo em emoji + descrição."""
    if code == 0:
        return ('☀️', 'Céu limpo') if is_day else ('🌙', 'Céu limpo')
    if code in (1, 2):
        return ('🌤️', 'Predominantemente claro') if is_day else ('🌙', 'Pouca nuvem')
    if code == 3:
        return ('☁️', 'Nublado')
    if code in (45, 48):
        return ('🌫️', 'Neblina')
    if code in (51, 53, 55, 56, 57):
        return ('🌦️', 'Chuvisco')
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ('🌧️', 'Chuva')
    if code in (71, 73, 75, 77, 85, 86):
        return ('🌨️', 'Neve')
    if code in (95, 96, 99):
        return ('⛈️', 'Tempestade')
    return ('⛅', 'Variável')


def detectar_cenario_real(weather_data):
    """A partir do clima atual da API, sugere um cenário automático."""
    try:
        cur = weather_data.get('current', {})
        code = cur.get('weather_code', 1)
        temp = cur.get('temperature_2m', 25)
        # Chuva
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
            return 'Chuvoso'
        # Verão extremo
        if temp >= 30:
            return 'Verao'
        return 'Normal'
    except:
        return 'Normal'


WEATHER_DATA = fetch_weather_cache()

# ──────────────────────────────────────────────
# APP DASH E ESTILOS
# ──────────────────────────────────────────────
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"], suppress_callback_exceptions=True, update_title=None)
app.title = "Smart Grid House"
server = app.server  # exposto para Vercel/Gunicorn

# CORES EXATAS DO PLOTLY
COR_SOL  = '#F59E0B'
COR_CASA = '#0EA5E9'
COR_IA   = '#10B981'
COR_SOC  = '#8B5CF6'

# ──────────────────────────────────────────────
# LAYOUT GLOBAL
# ──────────────────────────────────────────────
app.layout = dbc.Container([
    dcc.Store(id='sidebar-state', data=True),
    dcc.Store(id='welcome-seen', data=False),
    dcc.Download(id='download-csv'),

    # Modal de boas-vindas
    dbc.Modal([
        dbc.ModalBody([
            html.H4("👋 Bem-vindo ao Smart Grid House", style={'color': '#F8FAFC', 'fontWeight': '700', 'marginBottom': '12px'}),
            html.P("Este painel mostra como sua casa usa energia solar de forma inteligente.",
                   style={'color': '#D1D5DB', 'fontSize': '0.95rem', 'marginBottom': '8px'}),
            html.P("☀️ Durante o dia, o painel solar gera energia e carrega a bateria.",
                   style={'color': '#D1D5DB', 'fontSize': '0.9rem', 'marginBottom': '6px'}),
            html.P("🌙 À noite, a bateria alimenta a casa sem usar a rede elétrica.",
                   style={'color': '#D1D5DB', 'fontSize': '0.9rem', 'marginBottom': '6px'}),
            html.P("🧠 A IA decide automaticamente quando carregar ou usar a bateria para maximizar sua economia.",
                   style={'color': '#D1D5DB', 'fontSize': '0.9rem', 'marginBottom': '16px'}),
            html.P("Use o menu lateral para mudar o clima, a meta de economia e o modo da bateria.",
                   style={'color': '#9CA3AF', 'fontSize': '0.82rem'}),
        ], style={'backgroundColor': '#161B22', 'padding': '24px'}),
        dbc.ModalFooter(
            dbc.Button("Entendi ✓", id="close-welcome", className="ms-auto",
                       style={'backgroundColor': '#10B981', 'border': 'none', 'fontWeight': '600'}),
            style={'backgroundColor': '#161B22', 'borderTop': '1px solid #1F2937'}
        ),
    ], id="welcome-modal", is_open=True, centered=True,
       style={'--bs-modal-bg': '#161B22', '--bs-modal-border-color': '#374151'}),
    
    dbc.Button("≡", id="btn_sidebar", n_clicks=0, style={'position': 'fixed', 'top': '15px', 'left': '30px', 'zIndex': 9999, 'backgroundColor': 'transparent', 'color': '#10B981', 'border': 'none', 'fontSize': '2rem', 'padding': '0', 'lineHeight': '1'}),
    
    dbc.Row([
        # SIDEBAR COMPACTA
        dbc.Col([
            html.P("⚡ Smart Grid", className="sidebar-title"),
            html.P("Sua casa inteligente", className="sidebar-subtitle"),

            # ─── Indicador de Clima Real (API Open-Meteo) ───
            html.Div(id='clima-real-card'),

            # ─── Divisor + Modo Simulação ───
            html.Div([
                html.Hr(style={'borderColor': '#1F2937', 'margin': '14px 0 10px 0'}),
                html.P("🔧 Modo Simulação", style={'color': '#6B7280', 'fontSize': '0.7rem',
                                                     'fontWeight': '600', 'letterSpacing': '0.08em',
                                                     'textTransform': 'uppercase', 'marginBottom': '4px'}),
                html.P("Force cenários para testar a IA", style={'color': '#4B5563', 'fontSize': '0.7rem',
                                                                    'marginBottom': '12px'}),
            ]),

            label_with_info("Quanto quer economizar?", "tip-economia",
                            "Quanto maior, mais a IA prioriza guardar energia na bateria para usar à noite."),
            dcc.Slider(0, 50, 5, value=20, id='meta_economia',
                       marks={0: {'label': '0%', 'style': {'color': '#6B7280', 'fontSize': '0.7rem'}},
                              50: {'label': '50%', 'style': {'color': '#6B7280', 'fontSize': '0.7rem'}}},
                       className="mb-3 pb-2"),

            label_with_info("Forçar clima (teste)", "tip-cenario",
                            "Força um clima específico para testar a IA. Em produção, o clima vem automaticamente da API."),
            dbc.Select(
                options=[
                    {'label': '🌐 Auto (API real)',      'value': 'Auto'},
                    {'label': '⛅ Dia Normal',           'value': 'Normal'},
                    {'label': '🌧️ Chuva / Sem Sol',      'value': 'Chuvoso'},
                    {'label': '☀️ Verão Extremo',         'value': 'Verao'},
                    {'label': '✈️ Casa Vazia (Viagem)',   'value': 'Vazia'}
                ],
                value='Auto',
                id='cenario_drop',
                className="mb-2",
                style={'backgroundColor': '#1F2937', 'color': 'white',
                       'borderColor': '#374151', 'boxShadow': 'none',
                       'fontSize': '0.82rem', 'padding': '6px 10px'}
            ),

            label_with_info("Quem controla a bateria?", "tip-bateria",
                            "Automático: a IA cuida de tudo. Ou você pode forçar manualmente."),
            dbc.RadioItems(
                options=[
                    {'label': '🧠 Deixar a IA decidir', 'value': 'Auto'},
                    {'label': '🔋 Carregar agora', 'value': 'Carregar'},
                    {'label': '🔌 Usar bateria agora',   'value': 'Descarregar'}
                ],
                value='Auto',
                id='modo_bateria',
                labelStyle={'display': 'block', 'marginBottom': '8px',
                            'color': '#D1D5DB', 'fontSize': '0.82rem'},
                className="mb-2"
            ),

            label_with_info("Bateria começa com quanto?", "tip-soc",
                            "Nível de carga da bateria no início do dia simulado."),
            dcc.Slider(0, 100, 10, value=50, id='soc_inicial_slider',
                       marks={0: {'label': '0%', 'style': {'color': '#6B7280', 'fontSize': '0.7rem'}},
                              100: {'label': '100%', 'style': {'color': '#6B7280', 'fontSize': '0.7rem'}}},
                       className="mb-3 pb-2"),

            # Painel de status da IA
            html.Div(id='ia-status-panel')
        ], id="sidebar", width=12, md=3, lg=3, className="sidebar"),

        # MAIN CONTENT
        dbc.Col([
            
            
            dbc.Row(id='metric-cards', className="mb-2 px-2"),

            html.Div([
                dbc.Tabs([
                    dbc.Tab(tab_id="tab-home", label="🏠 Minha Casa"),
                    dbc.Tab(tab_id="tab-1", label="⚡ Visão Geral"),
                    dbc.Tab(tab_id="tab-2", label="🔮 Previsão & Decisões"),
                    dbc.Tab(tab_id="tab-3", label="🌍 Simulação ao Vivo"),
                ], id="tabs", active_tab="tab-home"),
                
                html.Div(id='charts-wrapper', className="mt-4")
                
            ], className="px-3"),

            # Simulação ao vivo — stores e interval
            dcc.Store(id='sim-state', data={'time': 0.0, 'soc': 50.0, 'playing': False, 'log': [], 'speed': 1}),
            dcc.Interval(id='sim-interval', interval=500, disabled=True),
            
        ], id="page-content", width=12, md=9, lg=9, style={'padding': '60px 30px 15px 30px'})
    ], className="m-0")
], fluid=True, style={'padding': '0px'})

# ──────────────────────────────────────────────
# CALLBACK TOGGLE SIDEBAR
# ──────────────────────────────────────────────
@app.callback(
    [Output("sidebar", "style"),
     Output("page-content", "md"),
     Output("page-content", "lg"),
     Output("sidebar-state", "data")],
    [Input("btn_sidebar", "n_clicks")],
    [State("sidebar-state", "data")]
)
def toggle_sidebar(n, is_open):
    if n:
        is_open = not is_open
    if is_open:
        return {'display': 'block'}, 9, 9, is_open
    else:
        return {'display': 'none'}, 12, 12, is_open

# ──────────────────────────────────────────────
# CALLBACK CLIMA REAL — sidebar
# ──────────────────────────────────────────────
@app.callback(
    Output('clima-real-card', 'children'),
    [Input('cenario_drop', 'value')]
)
def update_clima_real(cenario_input):
    cur = WEATHER_DATA.get('current', {})
    code = cur.get('weather_code', 1)
    is_day = cur.get('is_day', 1)
    temp = cur.get('temperature_2m', 25.0)
    emoji, desc = weather_code_to_info(code, is_day)
    cenario_auto = detectar_cenario_real(WEATHER_DATA)
    is_auto = (cenario_input == 'Auto')

    return html.Div([
        html.Div([
            html.Span("🌐 SÃO PAULO · AGORA", style={'color': '#10B981', 'fontSize': '0.62rem',
                                                       'fontWeight': '700', 'letterSpacing': '0.08em'}),
            html.Span(" • Auto ✓" if is_auto else " • Forçado", style={'color': '#10B981' if is_auto else '#F59E0B',
                                                                          'fontSize': '0.62rem', 'fontWeight': '600'}),
        ], style={'marginBottom': '6px'}),
        html.Div([
            html.Span(emoji, style={'fontSize': '1.6rem', 'marginRight': '8px'}),
            html.Div([
                html.Span(f"{temp:.0f}°C ", style={'color': '#F8FAFC', 'fontSize': '1rem', 'fontWeight': '700'}),
                html.Span(desc, style={'color': '#9CA3AF', 'fontSize': '0.78rem'}),
            ], style={'display': 'flex', 'flexDirection': 'column'}),
        ], style={'display': 'flex', 'alignItems': 'center'}),
    ], style={'padding': '10px 12px', 'backgroundColor': '#0D1117',
              'borderRadius': '6px', 'border': '1px solid #1F2937',
              'borderLeft': '2px solid #10B981', 'marginTop': '4px'})


# ──────────────────────────────────────────────
# CALLBACK MASTER
# ──────────────────────────────────────────────
@app.callback(
    [Output('metric-cards', 'children'),
     Output('charts-wrapper', 'children'),
     Output('ia-status-panel', 'children')],
    [Input('meta_economia', 'value'),
     Input('cenario_drop', 'value'),
     Input('modo_bateria', 'value'),
     Input('tabs', 'active_tab'),
     Input('soc_inicial_slider', 'value')],
    [State('sim-state', 'data')]
)
def update_dashboard(meta_eco, cenario, modo_bat, active_tab, soc_inicial_input, sim_state):
    # DADOS BASE
    horas = list(range(24))

    # Se "Auto", detecta o cenário a partir do clima real da API
    cenario_auto = detectar_cenario_real(WEATHER_DATA)
    if cenario == 'Auto':
        cenario = cenario_auto
    sol_base = np.array([0, 0, 0, 0, 0, 5, 25, 50, 75, 90, 100, 95, 85, 70, 50, 30, 10, 2, 0, 0, 0, 0, 0, 0])
    casa_base = np.array([10,10,10,10,15,40, 80, 50, 30, 20,  20, 30, 40, 30, 40, 60, 90,100,85,60,40,20,10,10])

    if cenario == "Chuvoso":
        sol_dia = sol_base * 0.3
        casa_dia = casa_base * 1.1
    elif cenario == "Verao":
        sol_dia = sol_base * 1.1
        casa_dia = casa_base * 1.4
    elif cenario == "Vazia":
        sol_dia = sol_base * 1.0
        casa_dia = casa_base * 0.2
    else:
        sol_dia = sol_base
        casa_dia = casa_base

    sol_dia = np.clip(sol_dia, 0, 100)
    casa_dia = np.clip(casa_dia, 0, 100)

    # SIMULAÇÃO
    SOC_INICIAL = float(soc_inicial_input) if soc_inicial_input is not None else 50.0
    soc_atual = SOC_INICIAL
    # Taxas distintas: carga rápida, descarga lenta (preserva vida útil — comum em LiFePO4)
    TAXA_CARGA = 0.15 if modo_bat == "Auto" else 0.4
    TAXA_DESCARGA = 0.08 if modo_bat == "Auto" else 0.4
    respostas_ia = []
    soc_historico = [SOC_INICIAL]

    for h in range(24):
        if modo_bat == "Carregar":
            acao = 80.0
        elif modo_bat == "Descarregar":
            acao = -80.0
        else:
            simulador.input['geracao_solar'] = float(sol_dia[h])
            demanda_ajustada = np.clip(casa_dia[h] * (1.0 + (meta_eco / 100.0)), 0, 100)
            simulador.input['demanda_casa']  = float(demanda_ajustada)
            try:
                simulador.compute()
                acao = simulador.output['acao_bateria']
            except:
                acao = 0.0
        respostas_ia.append(acao)
        # Aplica taxa diferente para carga vs descarga
        taxa = TAXA_CARGA if acao >= 0 else TAXA_DESCARGA
        novo_soc = np.clip(soc_atual + acao * taxa, 0, 100)
        soc_historico.append(novo_soc)
        soc_atual = novo_soc

    soc_plot = soc_historico[:24]

    # hora atual para linha "Agora"
    hora_atual = datetime.now().hour

    # CARDS — altura fixa, % inline, cor dinâmica na bateria
    def soc_color(val):
        if val < 20:
            return '#EF4444'
        if val < 50:
            return '#F59E0B'
        return '#10B981'

    def make_card(title, value_str, color_accent, progress_val=None, trend=None):
        top_row = [html.H3(value_str, className="metric-value", style={"margin": 0})]
        if trend is not None:
            t_color = '#10B981' if trend >= 0 else '#EF4444'
            t_arrow = '↑' if trend >= 0 else '↓'
            top_row.append(
                html.Span(f"{t_arrow}{abs(trend):.0f}%", className="metric-trend-inline",
                          style={"color": t_color})
            )
        body_children = [
            html.P(title, className="metric-title"),
            html.Div(top_row, className="metric-top-row"),
        ]
        if progress_val is not None:
            body_children.append(html.Div(
                html.Div(className="metric-progress-bar",
                         style={"width": f"{min(progress_val, 100):.1f}%",
                                "backgroundColor": color_accent}),
                className="metric-progress-track"
            ))
        return dbc.Col(
            dbc.Card(
                dbc.CardBody(body_children, className="metric-card-body"),
                style={'borderTop': f'3px solid {color_accent}'}
            ),
            width=12, md=2, lg=2, className="mb-3 flex-grow-1"
        )

    soc_final   = soc_historico[-1]
    soc_cor     = soc_color(soc_final)
    soc_ini_cor = soc_color(SOC_INICIAL)
    tendencia   = soc_final - SOC_INICIAL

    cards = [
        make_card("Bateria Atual",    f"{SOC_INICIAL:.0f}%",              soc_ini_cor, SOC_INICIAL),
        make_card("Bateria Estimada", f"{soc_final:.1f}%",                soc_cor,     soc_final,  tendencia),
        make_card("Pico Geração",     f"{max(sol_dia):.0f}%",             COR_SOL,     max(sol_dia)),
        make_card("Pico Demanda",     f"{max(casa_dia):.0f}%",            COR_CASA,    max(casa_dia)),
        make_card("Demanda da IA",    f"{sum(np.abs(respostas_ia))/24:.1f}%", COR_IA,  sum(np.abs(respostas_ia))/24),
    ]

    # ── Economia estimada em R$ ──
    # Comparação: casa COM painel+bateria+IA vs casa SÓ com rede elétrica
    TARIFA_KWH = 0.75  # R$/kWh (média residencial SP 2024)
    POTENCIA_CASA_KW = 3.5  # potência média da casa em kW

    # Consumo total da casa no dia (kWh) — sem nenhum painel solar
    consumo_total_kwh = sum(casa_dia) / 100.0 * POTENCIA_CASA_KW
    custo_sem_solar = consumo_total_kwh * TARIFA_KWH

    # Com painel + IA: solar cobre demanda direta + bateria cobre noite
    # Energia solar usada diretamente (quando geração >= demanda, usa demanda; senão usa geração)
    solar_direto = sum(np.minimum(sol_dia, casa_dia)) / 100.0 * POTENCIA_CASA_KW
    # Energia armazenada na bateria (excesso solar que a IA guardou)
    excesso_solar = sum(np.maximum(sol_dia - casa_dia, 0)) / 100.0 * POTENCIA_CASA_KW
    # Eficiência de ciclo da bateria (~85%)
    energia_bateria_disponivel = excesso_solar * 0.85
    # Demanda noturna que a bateria pode cobrir
    demanda_noturna = sum(np.maximum(casa_dia - sol_dia, 0)) / 100.0 * POTENCIA_CASA_KW
    energia_bateria_usada = min(energia_bateria_disponivel, demanda_noturna)

    # Consumo da rede com IA = total - solar direto - bateria
    consumo_rede_com_ia = consumo_total_kwh - solar_direto - energia_bateria_usada
    consumo_rede_com_ia = max(0, consumo_rede_com_ia)
    custo_com_ia = consumo_rede_com_ia * TARIFA_KWH

    economia_dia = custo_sem_solar - custo_com_ia
    economia_mes = economia_dia * 30

    # CONFIGURAÇÃO DE GRÁFICOS
    HOVER_STYLE = dict(
        bgcolor='#1A1F2B',
        bordercolor='#374151',
        font=dict(color='#E2E8F0', family='Inter, sans-serif', size=13),
    )

    minimal_layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color='#9CA3AF', family="Inter, sans-serif", size=12),
        margin=dict(t=30, l=10, r=20, b=40),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=HOVER_STYLE,
    )

    # FIG 1: 24h
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=horas, y=sol_dia, name='☀️ Geração', fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.1)', line=dict(color=COR_SOL, width=3), mode='lines'))
    fig1.add_trace(go.Scatter(x=horas, y=casa_dia, name='⚡ Consumo', fill='tozeroy', fillcolor='rgba(14, 165, 233, 0.1)', line=dict(color=COR_CASA, width=3), mode='lines'))
    fig1.add_trace(go.Scatter(x=horas, y=respostas_ia, name='🧠 IA Atuação', mode='lines', line=dict(color=COR_IA, dash='dot', width=3)))
    fig1.add_vline(x=hora_atual, line_width=1, line_dash="dash", line_color="#10B981",
                   annotation_text="Agora", annotation_position="top right",
                   annotation_font_color="#10B981", annotation_font_size=11)
    fig1.update_layout(**minimal_layout, hovermode='x unified', title="Balanço Energético 24h")
    # FIG 2: SOC
    fig2 = go.Figure()
    fig2.add_hrect(y0=20, y1=80, fillcolor='rgba(16,185,129,0.05)', line_width=0, annotation_text="Faixa Ideal", annotation_position="top left", annotation_font_color="#10B981")
    fig2.add_trace(go.Scatter(x=horas, y=soc_plot, name='🔋 Nível da Bateria', mode='lines+markers', marker=dict(size=8), line=dict(color=COR_SOC, width=3), fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.1)'))
    fig2.update_layout(**minimal_layout, hovermode='x unified', title="Evolução do SoC (State of Charge)")
    fig2.update_yaxes(range=[0, 105])

    # FIG 3: 3D
    fig3 = go.Figure(data=[go.Surface(z=Z_surface, x=x_grid, y=y_grid, colorscale='Viridis', opacity=0.7)])
    # Sincronia: Adicionar a jornada de 24h na superfície Fuzzy!
    fig3.add_trace(go.Scatter3d(
        x=sol_dia, y=casa_dia, z=respostas_ia,
        mode='lines+markers', line=dict(color='#EF4444', width=6), marker=dict(size=4, color='#EF4444'),
        name='Ações de Hoje (Curva)'
    ))
    fig3.update_layout(
        scene=dict(
            xaxis_title='Geração Solar', yaxis_title='Demanda Casa', zaxis_title='Atuação Bateria',
            xaxis=dict(gridcolor='rgba(255,255,255,0.08)', backgroundcolor='rgba(0,0,0,0)', title_font=dict(color='#E2E8F0')),
            yaxis=dict(gridcolor='rgba(255,255,255,0.08)', backgroundcolor='rgba(0,0,0,0)', title_font=dict(color='#E2E8F0')),
            zaxis=dict(gridcolor='rgba(255,255,255,0.08)', backgroundcolor='rgba(0,0,0,0)', title_font=dict(color='#E2E8F0'))
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color='#9CA3AF', family="Inter, sans-serif"),
        margin=dict(l=0, r=0, t=30, b=0), title="Mapa de Decisão da IA",
        hoverlabel=HOVER_STYLE,
    )

    # FIG 4: WEATHER
    fig4 = go.Figure()
    if WEATHER_DATA:
        df_clima = pd.DataFrame(WEATHER_DATA['daily'])
        df_clima['time'] = pd.to_datetime(df_clima['time'])
        
        # Sincronia 1: Ajuste da Meta Econômica e Cenário Climático Menu Lateral
        mod_cenario = 1.0
        mod_sol = 1.0
        if cenario == "Verao": mod_cenario = 1.4; mod_sol = 1.1
        elif cenario == "Chuvoso": mod_cenario = 1.1; mod_sol = 0.3
        elif cenario == "Vazia": mod_cenario = 0.2; mod_sol = 1.0
        
        df_clima['Consumo Estimado'] = df_clima['temperature_2m_max'] * 1.5 * mod_cenario * (1.0 + (meta_eco / 100.0))
        df_clima['Geração Estimada'] = (df_clima['sunshine_duration'] / 3600 * 5) * mod_sol
        
        fig4.add_trace(go.Bar(x=df_clima['time'], y=df_clima['Consumo Estimado'], name='Consumo Diário Projetado', marker_color='#3B82F6', marker_line_width=0))
        fig4.add_trace(go.Bar(x=df_clima['time'], y=df_clima['Geração Estimada'], name='Geração Diária Projetada', marker_color='#F59E0B', marker_line_width=0))
        fig4.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_dash="dash", line_color="#10B981", annotation_text="Hoje", annotation_position="top right")

    fig4.update_layout(**minimal_layout, barmode='group', hovermode='x unified', title="Previsão de 7 Dias")
    fig4.update_xaxes(showgrid=False)
    fig4.update_yaxes(showgrid=False)

    # FIG 5: PIE
    if cenario == "Verao":
        lbl = ['A/C', 'Geladeira', 'Chuveiro', 'Outros']
        val = [50, 20, 15, 15]
    elif cenario == "Chuvoso":
        lbl = ['Chuveiro', 'Geladeira', 'Lavanderia', 'Outros']
        val = [45, 25, 15, 15]
    elif cenario == "Vazia":
        lbl = ['Geladeira', 'Segurança', 'Standby', 'Outros']
        val = [60, 20, 15, 5]
    else:
        lbl = ['Chuveiro', 'A/C', 'Geladeira', 'Outros']
        val = [30, 25, 20, 25]

    fig5 = go.Figure(data=[go.Pie(
        labels=lbl, values=val, hole=.5,
        textinfo='percent+label',
        insidetextorientation='horizontal',
        marker=dict(line=dict(color='#0B0E14', width=2))
    )])
    fig5.update_layout(**minimal_layout, showlegend=False, title="Divisão do Consumo")

    # Painel de status da IA
    hora_idx   = min(hora_atual, 23)
    sol_agora  = sol_dia[hora_idx]
    casa_agora = casa_dia[hora_idx]
    acao_agora = respostas_ia[hora_idx]

    if modo_bat == "Carregar":
        ia_msg = "🔋 Carga forçada manualmente — modo manual ativo."
    elif modo_bat == "Descarregar":
        ia_msg = "🔌 Descarga forçada manualmente — modo manual ativo."
    elif acao_agora > 20:
        ia_msg = f"🧠 Carregando bateria — geração alta ({sol_agora:.0f}%), demanda baixa ({casa_agora:.0f}%)."
    elif acao_agora < -20:
        ia_msg = f"🧠 Descarregando bateria — geração baixa ({sol_agora:.0f}%), demanda alta ({casa_agora:.0f}%)."
    else:
        ia_msg = f"🧠 Mantendo bateria — geração ({sol_agora:.0f}%) e demanda ({casa_agora:.0f}%) equilibradas."

    ia_panel = html.Div([
        html.P("IA — Decisão Atual", className="ia-status-label"),
        html.P(ia_msg, style={"margin": 0})
    ], className="ia-status-panel")

    # Cálculo de kWh para uso em comparativos e cards
    kwh_gerado = sum(sol_dia) / 100.0 * 3.5
    kwh_consumido = sum(casa_dia) / 100.0 * 3.5

    # ── Simulação On/Off para comparativo (controlador "bang-bang" simples) ──
    # Sem histerese — liga/desliga só pelo threshold do sol. Comportamento de On/Off barato.
    soc_onoff = SOC_INICIAL
    soc_onoff_hist = [SOC_INICIAL]
    acoes_onoff = []
    for h in range(24):
        # On/Off ingênuo: carrega se sol > 50%, descarrega se sol < 50% e demanda > 30%
        if sol_dia[h] >= 50:
            acao_onoff = 100.0  # full power carga
        elif casa_dia[h] > 30:
            acao_onoff = -100.0  # full power descarga
        else:
            acao_onoff = 0.0
        acoes_onoff.append(acao_onoff)
        taxa_onoff = 0.15 if acao_onoff >= 0 else 0.08
        soc_onoff = float(np.clip(soc_onoff + acao_onoff * taxa_onoff, 0, 100))
        soc_onoff_hist.append(soc_onoff)
    soc_onoff_plot = soc_onoff_hist[:24]

    # ── Métricas comparativas IA vs On/Off ──
    # 1) Chaveamentos: número de mudanças de estado (carregar↔descarregar↔manter)
    def count_chaveamentos(acoes):
        cnt = 0
        prev_estado = None
        for a in acoes:
            if a > 10:
                e = 'C'
            elif a < -10:
                e = 'D'
            else:
                e = 'M'
            if prev_estado is not None and e != prev_estado:
                cnt += 1
            prev_estado = e
        return cnt
    chav_fuzzy = count_chaveamentos(respostas_ia)
    chav_onoff = count_chaveamentos(acoes_onoff)

    # 2) Tempo na faixa ideal (20-80%)
    tempo_ideal_fuzzy = sum(1 for s in soc_plot if 20 <= s <= 80) / 24 * 100
    tempo_ideal_onoff = sum(1 for s in soc_onoff_plot if 20 <= s <= 80) / 24 * 100

    # 3) Energia da rede elétrica (quando bateria não cobre demanda)
    # Considera potência média 3.5kW
    def calc_economia_real(soc_hist, sol_arr, casa_arr):
        kwh_rede = 0
        for h in range(24):
            demanda_kwh = casa_arr[h] / 100.0 * 3.5
            solar_direto_kwh = min(sol_arr[h], casa_arr[h]) / 100.0 * 3.5
            # Bateria pode contribuir se SoC > 20%
            if soc_hist[h] > 20:
                # Quanto a bateria descarrega na próxima hora
                if h + 1 < len(soc_hist):
                    delta = max(0, soc_hist[h] - soc_hist[h+1]) / 100.0 * 3.5
                    bateria_kwh = min(delta, demanda_kwh - solar_direto_kwh)
                else:
                    bateria_kwh = 0
            else:
                bateria_kwh = 0
            rede_kwh = max(0, demanda_kwh - solar_direto_kwh - bateria_kwh)
            kwh_rede += rede_kwh
        return kwh_rede

    kwh_rede_fuzzy = calc_economia_real(soc_historico, sol_dia, casa_dia)
    kwh_rede_onoff = calc_economia_real(soc_onoff_hist, sol_dia, casa_dia)
    economia_fuzzy_dia = (kwh_consumido - kwh_rede_fuzzy) * 0.75
    economia_onoff_dia = (kwh_consumido - kwh_rede_onoff) * 0.75
    diff_economia_mes = (economia_fuzzy_dia - economia_onoff_dia) * 30

    # FIG 6: Comparativo IA Fuzzy vs On/Off
    fig6 = go.Figure()
    fig6.add_hrect(y0=20, y1=80, fillcolor='rgba(16,185,129,0.04)', line_width=0,
                   annotation_text="Faixa ideal", annotation_position="top left",
                   annotation_font_color="#10B981", annotation_font_size=10)
    fig6.add_trace(go.Scatter(x=horas, y=soc_plot, name='🧠 IA Fuzzy', mode='lines',
                              line=dict(color=COR_IA, width=3)))
    fig6.add_trace(go.Scatter(x=horas, y=soc_onoff_plot, name='⚡ On/Off (sem IA)', mode='lines',
                              line=dict(color='#EF4444', width=2, dash='dash')))
    fig6.update_layout(**minimal_layout, hovermode='x unified', title="Comparativo: IA Fuzzy vs Controle On/Off")
    fig6.update_yaxes(range=[0, 105])

    # ROTEAMENTO DE TABS AGRUPADO
    if active_tab == "tab-home":
        # ── ABA MINHA CASA — clean, denso e informativo ──
        soc_agora = soc_historico[hora_atual] if hora_atual < len(soc_historico) else soc_final

        # Status visual
        if soc_agora >= 50:
            status_dot, status_txt, status_cor = "🟢", "Tudo certo", '#10B981'
        elif soc_agora >= 20:
            status_dot, status_txt, status_cor = "🟡", "Atenção", '#F59E0B'
        else:
            status_dot, status_txt, status_cor = "🔴", "Bateria baixa", '#EF4444'

        # Mini-stats helper
        def mini_stat(label, value, color, sub=None):
            children = [
                html.P(label, style={'color': '#6B7280', 'fontSize': '0.65rem',
                                     'letterSpacing': '0.08em', 'textTransform': 'uppercase',
                                     'marginBottom': '2px'}),
                html.H4(value, style={'color': color, 'fontWeight': '700',
                                       'fontSize': '1.15rem', 'margin': '0', 'lineHeight': '1.2'}),
            ]
            if sub:
                children.append(html.P(sub, style={'color': '#6B7280', 'fontSize': '0.7rem', 'margin': '2px 0 0 0'}))
            return html.Div(children, style={
                'padding': '10px 14px', 'backgroundColor': '#161B22',
                'borderRadius': '8px', 'border': '1px solid #1F2937',
                'borderLeft': f'2px solid {color}', 'flex': '1', 'minWidth': '0'
            })

        # Calcular dados extras
        melhor_hora = int(np.argmax(sol_dia - casa_dia))
        horas_sol = int(sum(1 for s in sol_dia if s > 30))
        autonomia_pct = min(100, (kwh_gerado / kwh_consumido * 100) if kwh_consumido > 0 else 0)

        # Calcular hora que a bateria zera (se zerar)
        hora_bat_zera = None
        for h_idx in range(hora_atual + 1, 24):
            if soc_historico[h_idx] < 5:
                hora_bat_zera = h_idx
                break
        if hora_bat_zera is not None:
            autonomia_txt = f"até {hora_bat_zera:02d}h"
        else:
            autonomia_txt = "noite toda"

        # Mini-chart 1: geração 24h (sparkline-style)
        fig_mini_sol = go.Figure()
        fig_mini_sol.add_trace(go.Scatter(x=horas, y=sol_dia, mode='lines',
                                          fill='tozeroy', fillcolor='rgba(245,158,11,0.2)',
                                          line=dict(color='#F59E0B', width=2), hoverinfo='skip'))
        fig_mini_sol.add_vline(x=hora_atual, line_width=1, line_dash='dot', line_color='#10B981')
        fig_mini_sol.update_layout(
            xaxis=dict(visible=False, range=[0, 23]),
            yaxis=dict(visible=False, range=[0, 105]),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0), height=60, showlegend=False,
        )

        # Mini-chart 2: evolução bateria 24h
        fig_mini_bat = go.Figure()
        fig_mini_bat.add_trace(go.Scatter(x=horas, y=soc_plot, mode='lines',
                                          fill='tozeroy', fillcolor='rgba(139,92,246,0.2)',
                                          line=dict(color='#8B5CF6', width=2), hoverinfo='skip'))
        fig_mini_bat.add_hrect(y0=20, y1=80, fillcolor='rgba(16,185,129,0.05)', line_width=0)
        fig_mini_bat.add_vline(x=hora_atual, line_width=1, line_dash='dot', line_color='#10B981')
        fig_mini_bat.update_layout(
            xaxis=dict(visible=False, range=[0, 23]),
            yaxis=dict(visible=False, range=[0, 105]),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0), height=60, showlegend=False,
        )

        # Mini-chart 3: consumo 24h
        fig_mini_casa = go.Figure()
        fig_mini_casa.add_trace(go.Scatter(x=horas, y=casa_dia, mode='lines',
                                            fill='tozeroy', fillcolor='rgba(14,165,233,0.2)',
                                            line=dict(color='#0EA5E9', width=2), hoverinfo='skip'))
        fig_mini_casa.add_vline(x=hora_atual, line_width=1, line_dash='dot', line_color='#10B981')
        fig_mini_casa.update_layout(
            xaxis=dict(visible=False, range=[0, 23]),
            yaxis=dict(visible=False, range=[0, 105]),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0), height=60, showlegend=False,
        )

        # Cena visual (menor)
        time_now = float(hora_atual) + (datetime.now().minute / 60.0)
        fig_casa = build_sim_scene(time_now, soc_agora,
                                    sol_dia[hora_atual] if hora_atual < 24 else 0,
                                    casa_dia[hora_atual] if hora_atual < 24 else 0,
                                    respostas_ia[hora_atual] if hora_atual < 24 else 0,
                                    cenario)

        # Dica curta contextual
        if cenario == "Chuvoso":
            dica_curta = "🌧️ Pouco sol hoje — evite consumo pesado para preservar a bateria."
        elif sol_dia[melhor_hora] > 50:
            dica_curta = f"☀️ Use chuveiro/máquina às {melhor_hora}h — sol forte e demanda baixa."
        else:
            dica_curta = "⏸️ Sem horário ideal hoje — IA gerencia automaticamente."

        # Mini-card de chart com título
        def mini_chart_card(titulo, valor, fig, cor):
            return html.Div([
                html.Div([
                    html.Span(titulo, style={'color': '#9CA3AF', 'fontSize': '0.72rem',
                                             'fontWeight': '500', 'letterSpacing': '0.04em'}),
                    html.Span(valor, style={'color': cor, 'fontSize': '0.92rem',
                                             'fontWeight': '700', 'float': 'right'}),
                ], style={'padding': '8px 12px 0 12px'}),
                dcc.Graph(figure=fig, config={'displayModeBar': False, 'staticPlot': True},
                          style={'height': '60px'}),
            ], style={'backgroundColor': '#161B22', 'borderRadius': '8px',
                      'border': '1px solid #1F2937', 'flex': '1', 'minWidth': '0'})

        # ── Banner de clima real (API Open-Meteo) ──
        cur = WEATHER_DATA.get('current', {})
        clima_emoji, clima_desc = weather_code_to_info(cur.get('weather_code', 1), cur.get('is_day', 1))
        clima_temp = cur.get('temperature_2m', 25.0)
        cenario_detect = detectar_cenario_real(WEATHER_DATA)
        cen_label = {'Normal': 'Dia normal', 'Chuvoso': 'Dia chuvoso', 'Verao': 'Verão extremo', 'Vazia': 'Casa vazia'}.get(cenario, 'Dia normal')

        layout_charts = html.Div([
            # ─── Linha 1: Status compacto ───
            html.Div([
                mini_stat("Status", f"{status_dot} {status_txt}", status_cor),
                mini_stat("Economia/dia", f"R$ {economia_dia:.2f}", '#10B981', f"R$ {economia_mes:.0f}/mês"),
                mini_stat("Bateria agora", f"{soc_agora:.0f}%", status_cor, f"dura {autonomia_txt}"),
                mini_stat("Autonomia solar", f"{autonomia_pct:.0f}%", '#F59E0B', f"{horas_sol}h de sol forte"),
                mini_stat("Energia gerada", f"{kwh_gerado:.1f} kWh", '#0EA5E9', f"de {kwh_consumido:.1f} consumidos"),
            ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '14px'}),

            # ─── Linha 2: Mini-charts 24h ───
            html.Div([
                mini_chart_card("☀️ Geração nas 24h", f"pico {max(sol_dia):.0f}%", fig_mini_sol, '#F59E0B'),
                mini_chart_card("🔋 Bateria nas 24h", f"agora {soc_agora:.0f}%", fig_mini_bat, '#8B5CF6'),
                mini_chart_card("⚡ Consumo nas 24h", f"pico {max(casa_dia):.0f}%", fig_mini_casa, '#0EA5E9'),
            ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '14px'}),

            # ─── Linha 3: Cena visual + dica + IA ───
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Span("🏠 Sua casa agora", style={'color': '#F8FAFC', 'fontSize': '0.85rem', 'fontWeight': '600'}),
                            html.Span(f"  ·  {hora_atual:02d}h", style={'color': '#6B7280', 'fontSize': '0.75rem'}),
                        ], style={'padding': '10px 14px', 'borderBottom': '1px solid #1F2937'}),
                        dcc.Graph(figure=fig_casa, config={'displayModeBar': False, 'staticPlot': True},
                                  style={'height': '420px'}),
                    ], style={'backgroundColor': '#161B22', 'borderRadius': '10px',
                              'border': '1px solid #1F2937', 'overflow': 'hidden'}),
                ], width=12, lg=8, className="mb-2"),
                dbc.Col([
                    # Clima real (compacto, primeiro)
                    html.Div([
                        html.Div([
                            html.Span(clima_emoji, style={'fontSize': '1.4rem', 'marginRight': '10px'}),
                            html.Div([
                                html.Span(f"{clima_temp:.0f}°C ", style={'color': '#F8FAFC', 'fontSize': '0.95rem',
                                                                            'fontWeight': '700'}),
                                html.Span(clima_desc, style={'color': '#9CA3AF', 'fontSize': '0.78rem'}),
                                html.Div("São Paulo · API Open-Meteo", style={'color': '#4B5563', 'fontSize': '0.65rem',
                                                                                'marginTop': '1px'}),
                            ], style={'flex': '1'}),
                        ], style={'display': 'flex', 'alignItems': 'center'}),
                    ], style={'padding': '10px 12px', 'backgroundColor': '#161B22', 'borderRadius': '10px',
                              'border': '1px solid #1F2937', 'borderLeft': '2px solid #10B981',
                              'marginBottom': '10px'}),
                    html.Div([
                        html.P("💡 DICA", style={'color': '#F59E0B', 'fontSize': '0.65rem', 'fontWeight': '600',
                                                  'letterSpacing': '0.08em', 'marginBottom': '6px'}),
                        html.P(dica_curta, style={'color': '#E2E8F0', 'fontSize': '0.85rem', 'margin': '0'}),
                    ], style={'padding': '14px', 'backgroundColor': '#161B22', 'borderRadius': '10px',
                              'border': '1px solid #1F2937', 'borderLeft': '2px solid #F59E0B',
                              'marginBottom': '10px'}),
                    html.Div([
                        html.P("🧠 IA AGORA", style={'color': '#10B981', 'fontSize': '0.65rem', 'fontWeight': '600',
                                                      'letterSpacing': '0.08em', 'marginBottom': '6px'}),
                        html.P(ia_msg, style={'color': '#E2E8F0', 'fontSize': '0.85rem', 'margin': '0'}),
                    ], style={'padding': '14px', 'backgroundColor': '#161B22', 'borderRadius': '10px',
                              'border': '1px solid #1F2937', 'borderLeft': '2px solid #10B981',
                              'marginBottom': '10px'}),
                    html.Div([
                        html.P("⏰ MELHOR HORÁRIO", style={'color': '#0EA5E9', 'fontSize': '0.65rem', 'fontWeight': '600',
                                                            'letterSpacing': '0.08em', 'marginBottom': '6px'}),
                        html.H4(f"{melhor_hora:02d}h", style={'color': '#F8FAFC', 'fontWeight': '700',
                                                                'fontSize': '1.6rem', 'marginBottom': '2px'}),
                        html.P("para chuveiro/máquina", style={'color': '#9CA3AF', 'fontSize': '0.78rem', 'margin': '0'}),
                    ], style={'padding': '14px', 'backgroundColor': '#161B22', 'borderRadius': '10px',
                              'border': '1px solid #1F2937', 'borderLeft': '2px solid #0EA5E9'}),
                ], width=12, lg=4),
            ]),
        ])

    elif active_tab == "tab-1":
        # Nota de economia discreta
        economia_note = html.Div([
            html.P(f"💰 Economia estimada: R$ {economia_dia:.2f}/dia · R$ {economia_mes:.0f}/mês",
                   style={'color': '#10B981', 'fontSize': '0.78rem', 'fontWeight': '500', 'margin': '0'}),
            html.P(f"vs. casa sem painel solar · tarifa R$ 0,75/kWh · {consumo_total_kwh:.1f} kWh/dia consumidos · {energia_bateria_usada:.1f} kWh cobertos pela bateria",
                   style={'color': '#4B5563', 'fontSize': '0.65rem', 'margin': '2px 0 0 0'}),
        ], style={'padding': '8px 12px', 'backgroundColor': '#0D1117', 'borderRadius': '6px',
                  'border': '1px solid #1F2937', 'marginBottom': '16px'})

        layout_charts = dbc.Row([
            dbc.Col(economia_note, width=12, className="mb-2"),
            dbc.Col(html.Div(dcc.Graph(figure=fig1, config=GRAPH_CONFIG, style={'height': '380px'}), className="card border-0 bg-transparent shadow-none"), width=12, lg=12, className="mb-5 pb-3"),
            dbc.Col(html.Div(dcc.Graph(figure=fig5, config=GRAPH_CONFIG, style={'height': '380px'}), className="card border-0 bg-transparent shadow-none"), width=12, lg=12, className="mb-5 pb-3"),
            dbc.Col(html.Div(dcc.Graph(figure=fig2, config=GRAPH_CONFIG, style={'height': '320px'}), className="card border-0 bg-transparent shadow-none"), width=12, lg=12, className="mb-5 pb-3"),
        ])
    elif active_tab == "tab-2":
        # Botão exportar CSV
        btn_csv = html.Div(
            dbc.Button("📥 Exportar CSV", id='btn-export-csv', n_clicks=0, size='sm',
                       style={'backgroundColor': '#1F2937', 'border': '1px solid #374151',
                              'color': '#9CA3AF', 'fontSize': '0.75rem', 'fontWeight': '500'}),
            style={'marginBottom': '12px', 'textAlign': 'right'}
        )

        # ─── Painel de métricas comparativas ───
        def metric_compare(label, valor_fuzzy, valor_onoff, sufixo='', vencedor='fuzzy', menor_eh_melhor=False):
            cor_fuzzy = '#10B981' if vencedor == 'fuzzy' else '#9CA3AF'
            cor_onoff = '#EF4444' if vencedor == 'fuzzy' else '#9CA3AF'
            return html.Div([
                html.P(label, style={'color': '#9CA3AF', 'fontSize': '0.7rem',
                                     'letterSpacing': '0.05em', 'textTransform': 'uppercase',
                                     'marginBottom': '8px'}),
                html.Div([
                    html.Div([
                        html.Span("🧠 IA Fuzzy", style={'color': '#9CA3AF', 'fontSize': '0.72rem'}),
                        html.H5(f"{valor_fuzzy}{sufixo}", style={'color': cor_fuzzy, 'fontWeight': '700',
                                                                   'margin': '2px 0 0 0', 'fontSize': '1.1rem'}),
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Span("⚡ On/Off", style={'color': '#9CA3AF', 'fontSize': '0.72rem'}),
                        html.H5(f"{valor_onoff}{sufixo}", style={'color': cor_onoff, 'fontWeight': '700',
                                                                   'margin': '2px 0 0 0', 'fontSize': '1.1rem'}),
                    ], style={'flex': '1'}),
                ], style={'display': 'flex', 'gap': '12px'}),
            ], style={'padding': '12px 14px', 'backgroundColor': '#161B22',
                      'borderRadius': '8px', 'border': '1px solid #1F2937',
                      'flex': '1', 'minWidth': '0'})

        diff_chav = chav_onoff - chav_fuzzy
        diff_ideal = tempo_ideal_fuzzy - tempo_ideal_onoff

        metrics_panel = html.Div([
            html.Div([
                metric_compare("Chaveamentos no dia", chav_fuzzy, chav_onoff,
                               sufixo='×', vencedor='fuzzy'),
                metric_compare("Tempo na faixa ideal", f"{tempo_ideal_fuzzy:.0f}", f"{tempo_ideal_onoff:.0f}",
                               sufixo='%', vencedor='fuzzy'),
                metric_compare("Economia mensal", f"R$ {economia_fuzzy_dia*30:.0f}", f"R$ {economia_onoff_dia*30:.0f}",
                               sufixo='', vencedor='fuzzy'),
            ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '12px'}),

            # Veredito
            html.Div([
                html.Span("✨ ", style={'fontSize': '1.2rem'}),
                html.Span(f"A IA Fuzzy economiza ", style={'color': '#E2E8F0', 'fontSize': '0.9rem'}),
                html.Span(f"R$ {abs(diff_economia_mes):.0f}/mês", style={'color': '#10B981', 'fontWeight': '700', 'fontSize': '0.95rem'}),
                html.Span(" a mais, com ", style={'color': '#E2E8F0', 'fontSize': '0.9rem'}),
                html.Span(f"{diff_chav}× menos chaveamentos", style={'color': '#10B981', 'fontWeight': '700', 'fontSize': '0.95rem'}),
                html.Span(" e ", style={'color': '#E2E8F0', 'fontSize': '0.9rem'}),
                html.Span(f"{diff_ideal:.0f}% mais tempo na faixa ideal.", style={'color': '#10B981', 'fontWeight': '700', 'fontSize': '0.95rem'}),
            ], style={'padding': '14px 16px', 'backgroundColor': '#0D1117',
                      'borderRadius': '8px', 'border': '1px solid #10B98133',
                      'borderLeft': '2px solid #10B981', 'marginBottom': '20px'}),
        ])

        layout_charts = dbc.Row([
            dbc.Col(btn_csv, width=12),
            dbc.Col(html.Div(dcc.Graph(figure=fig6, config=GRAPH_CONFIG, style={'height': '360px'}), className="card border-0 bg-transparent shadow-none"), width=12, lg=12, className="mb-2"),
            dbc.Col(metrics_panel, width=12),
            dbc.Col(html.Div(dcc.Graph(figure=fig3, config=GRAPH_CONFIG, style={'height': '450px'}), className="card border-0 bg-transparent shadow-none"), width=12, lg=12, className="mb-5 pb-3"),
            dbc.Col(html.Div(dcc.Graph(figure=fig4, config=GRAPH_CONFIG, style={'height': '450px'}), className="card border-0 bg-transparent shadow-none"), width=12, lg=12, className="mb-5 pb-3"),
        ])
    else:
        # Tab 3: Simulação ao Vivo — renderizada por callback separado
        layout_charts = html.Div(id='sim-live-container')

    return cards, layout_charts, ia_panel


# ──────────────────────────────────────────────
# MODAL DE BOAS-VINDAS
# ──────────────────────────────────────────────
@app.callback(
    Output("welcome-modal", "is_open"),
    [Input("close-welcome", "n_clicks")],
    [State("welcome-modal", "is_open")],
    prevent_initial_call=True
)
def close_welcome(n, is_open):
    return False


# ──────────────────────────────────────────────
# EXPORTAR CSV
# ──────────────────────────────────────────────
@app.callback(
    Output('download-csv', 'data'),
    [Input('btn-export-csv', 'n_clicks')],
    [State('meta_economia', 'value'),
     State('cenario_drop', 'value'),
     State('modo_bateria', 'value'),
     State('soc_inicial_slider', 'value')],
    prevent_initial_call=True
)
def export_csv(n, meta_eco, cenario, modo_bat, soc_ini):
    if not n:
        raise dash.exceptions.PreventUpdate

    horas = list(range(24))
    sol_base = np.array([0,0,0,0,0,5,25,50,75,90,100,95,85,70,50,30,10,2,0,0,0,0,0,0], dtype=float)
    casa_base = np.array([10,10,10,10,15,40,80,50,30,20,20,30,40,30,40,60,90,100,85,60,40,20,10,10], dtype=float)

    if cenario == "Chuvoso":
        sol_arr = sol_base * 0.3; casa_arr = casa_base * 1.1
    elif cenario == "Verao":
        sol_arr = sol_base * 1.1; casa_arr = casa_base * 1.4
    elif cenario == "Vazia":
        sol_arr = sol_base; casa_arr = casa_base * 0.2
    else:
        sol_arr = sol_base.copy(); casa_arr = casa_base.copy()
    sol_arr = np.clip(sol_arr, 0, 100)
    casa_arr = np.clip(casa_arr, 0, 100)

    soc_val = float(soc_ini) if soc_ini else 50.0
    taxa_carga = 0.15 if modo_bat == "Auto" else 0.4
    taxa_descarga = 0.08 if modo_bat == "Auto" else 0.4
    rows = []
    for h in range(24):
        if modo_bat == "Carregar":
            acao = 80.0
        elif modo_bat == "Descarregar":
            acao = -80.0
        else:
            simulador.input['geracao_solar'] = float(sol_arr[h])
            simulador.input['demanda_casa'] = float(np.clip(casa_arr[h] * (1.0 + meta_eco / 100.0), 0, 100))
            try:
                simulador.compute()
                acao = simulador.output['acao_bateria']
            except:
                acao = 0.0
        taxa = taxa_carga if acao >= 0 else taxa_descarga
        soc_val = float(np.clip(soc_val + acao * taxa, 0, 100))
        rows.append({'Hora': f'{h:02d}:00', 'Geração Solar (%)': f'{sol_arr[h]:.1f}',
                     'Demanda Casa (%)': f'{casa_arr[h]:.1f}', 'Ação IA (%)': f'{acao:.1f}',
                     'SoC Bateria (%)': f'{soc_val:.1f}', 'Cenário': cenario, 'Meta Economia': meta_eco})

    df = pd.DataFrame(rows)
    return dcc.send_data_frame(df.to_csv, "smart_grid_simulacao.csv", index=False)


# ──────────────────────────────────────────────
# CARDS AO VIVO (tab 3) — atualiza sem re-renderizar tudo
# ──────────────────────────────────────────────
@app.callback(
    Output('metric-cards', 'children', allow_duplicate=True),
    [Input('sim-state', 'data')],
    [State('tabs', 'active_tab')],
    prevent_initial_call=True
)
def update_cards_live(sim_state, active_tab):
    if active_tab != 'tab-3' or not sim_state:
        raise dash.exceptions.PreventUpdate

    sim_soc = sim_state.get('soc', 50.0)
    sim_geracao = sim_state.get('last_geracao', 0)
    sim_demanda = sim_state.get('last_demanda', 0)
    sim_acao = sim_state.get('last_acao', 0)

    def soc_color(val):
        if val < 20:
            return '#EF4444'
        if val < 50:
            return '#F59E0B'
        return '#10B981'

    def make_card(title, value_str, color_accent, progress_val=None, trend=None):
        top_row = [html.H3(value_str, className="metric-value", style={"margin": 0})]
        if trend is not None:
            t_color = '#10B981' if trend >= 0 else '#EF4444'
            t_arrow = '↑' if trend >= 0 else '↓'
            top_row.append(
                html.Span(f"{t_arrow}{abs(trend):.0f}%", className="metric-trend-inline",
                          style={"color": t_color})
            )
        body_children = [
            html.P(title, className="metric-title"),
            html.Div(top_row, className="metric-top-row"),
        ]
        if progress_val is not None:
            body_children.append(html.Div(
                html.Div(className="metric-progress-bar",
                         style={"width": f"{min(progress_val, 100):.1f}%",
                                "backgroundColor": color_accent}),
                className="metric-progress-track"
            ))
        return dbc.Col(
            dbc.Card(
                dbc.CardBody(body_children, className="metric-card-body"),
                style={'borderTop': f'3px solid {color_accent}'}
            ),
            width=12, md=2, lg=2, className="mb-3 flex-grow-1"
        )

    sim_soc_cor = soc_color(sim_soc)
    return [
        make_card("Bateria (Live)", f"{sim_soc:.1f}%", sim_soc_cor, sim_soc),
        make_card("Geração Agora", f"{sim_geracao:.0f}%", COR_SOL, sim_geracao),
        make_card("Demanda Agora", f"{sim_demanda:.0f}%", COR_CASA, sim_demanda),
        make_card("Ação da IA", f"{sim_acao:+.0f}%", COR_IA, min(abs(sim_acao), 100)),
        make_card("Hora", f"{int(sim_state.get('time', 0)):02d}:{int((sim_state.get('time', 0) % 1) * 60):02d}", '#8B5CF6', (sim_state.get('time', 0) / 24) * 100),
    ]


# ──────────────────────────────────────────────
# SIMULAÇÃO AO VIVO — CALLBACKS
# ──────────────────────────────────────────────
import math

def sky_color(hora):
    """Retorna cor do céu baseada na hora."""
    if hora <= 4:
        return '#0B1628'
    elif hora <= 6:
        return '#1a2744'
    elif hora <= 8:
        return '#2a4a6b'
    elif hora <= 16:
        return '#1e3d5c'
    elif hora <= 18:
        return '#3d2a1a'
    elif hora <= 19:
        return '#1a2744'
    else:
        return '#0B1628'


def build_sim_scene(time_h, soc, geracao, demanda, acao_ia, cenario):
    """Constrói a cena. time_h é float 0.0-24.0."""
    fig = go.Figure()
    hora_int = int(time_h) % 24
    minuto = int((time_h % 1) * 60)

    fig.update_layout(
        xaxis=dict(range=[0, 100], visible=False, fixedrange=True),
        yaxis=dict(range=[0, 100], visible=False, fixedrange=True),
        paper_bgcolor=sky_color(hora_int),
        plot_bgcolor=sky_color(hora_int),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        height=520,
    )

    # ── TERRENO ──
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=22,
                  fillcolor='#1a2e1a', line=dict(width=0), opacity=0.7)
    fig.add_shape(type="line", x0=0, y0=22, x1=100, y1=22,
                  line=dict(color='#3d5c3d', width=1))

    # ── SOL / LUA ──
    # Arco: nasce no horizonte ESQUERDO (y=22), sobe até zênite (y=90), desce até horizonte DIREITO (y=22)
    # Ambos vão da esquerda para a direita
    ground_y = 22  # nível do chão — sol/lua TOCAM aqui nos extremos
    peak_y = 75
    x_start, x_end = -5, 105
    is_day = 6.0 <= time_h < 18.0

    # Órbita tracejada (visual)
    orb_n = 50
    orb_x = [x_start + (x_end - x_start) * (i / orb_n) for i in range(orb_n + 1)]
    orb_y = [ground_y + (peak_y - ground_y) * math.sin((i / orb_n) * math.pi) for i in range(orb_n + 1)]
    fig.add_trace(go.Scatter(x=orb_x, y=orb_y, mode='lines',
                             line=dict(color='rgba(255,255,255,0.04)', width=1, dash='dot'),
                             hoverinfo='skip'))

    if is_day:
        prog = (time_h - 6.0) / 12.0
        sol_x = x_start + (x_end - x_start) * prog
        sol_y = ground_y + (peak_y - ground_y) * math.sin(prog * math.pi)
        fig.add_shape(type="circle", x0=sol_x-5.5, y0=sol_y-5.5, x1=sol_x+5.5, y1=sol_y+5.5,
                      fillcolor='rgba(251,191,36,0.12)', line=dict(width=0))
        fig.add_shape(type="circle", x0=sol_x-3.5, y0=sol_y-3.5, x1=sol_x+3.5, y1=sol_y+3.5,
                      fillcolor='#FBBF24', line=dict(width=0))
    else:
        sol_x, sol_y = -10, -10
        if time_h >= 18.0:
            prog = (time_h - 18.0) / 12.0
        else:
            prog = (time_h + 6.0) / 12.0
        lua_x = x_start + (x_end - x_start) * prog
        lua_y = ground_y + (peak_y - ground_y) * math.sin(prog * math.pi)
        fig.add_shape(type="circle", x0=lua_x-2.5, y0=lua_y-2.5, x1=lua_x+2.5, y1=lua_y+2.5,
                      fillcolor='#E2E8F0', line=dict(width=0), opacity=0.9)
        # Estrelas
        import random
        random.seed(42)
        for _ in range(15):
            sx, sy = random.uniform(5, 95), random.uniform(45, 94)
            fig.add_shape(type="circle", x0=sx-0.3, y0=sy-0.3, x1=sx+0.3, y1=sy+0.3,
                          fillcolor='rgba(255,255,255,0.25)', line=dict(width=0))

    # ── PAINEL SOLAR (centro, no chão) ──
    panel_cx, panel_cy = 50, 36
    panel_w, panel_h = 13, 2.2
    if is_day:
        panel_angle = math.degrees(math.atan2(sol_y - panel_cy, sol_x - panel_cx)) + 90
    else:
        panel_angle = 90
    cos_a = math.cos(math.radians(panel_angle))
    sin_a = math.sin(math.radians(panel_angle))
    corners = [(-panel_w/2, -panel_h/2), (panel_w/2, -panel_h/2),
               (panel_w/2, panel_h/2), (-panel_w/2, panel_h/2)]
    rotated = [(panel_cx + x*cos_a - y*sin_a, panel_cy + x*sin_a + y*cos_a) for x, y in corners]
    fig.add_trace(go.Scatter(
        x=[p[0] for p in rotated] + [rotated[0][0]],
        y=[p[1] for p in rotated] + [rotated[0][1]],
        fill='toself', fillcolor='#1E3A8A', line=dict(color='#3B82F6', width=2),
        hoverinfo='skip', mode='lines'))
    # Células
    mid_top = ((rotated[0][0]+rotated[1][0])/2, (rotated[0][1]+rotated[1][1])/2)
    mid_bot = ((rotated[2][0]+rotated[3][0])/2, (rotated[2][1]+rotated[3][1])/2)
    fig.add_shape(type="line", x0=mid_top[0], y0=mid_top[1], x1=mid_bot[0], y1=mid_bot[1],
                  line=dict(color='#60A5FA', width=0.7))
    # Poste
    fig.add_shape(type="line", x0=50, y0=panel_cy-3, x1=50, y1=24,
                  line=dict(color='#6B7280', width=2.5))
    fig.add_shape(type="rect", x0=48, y0=22, x1=52, y1=24,
                  fillcolor='#4B5563', line=dict(width=0))

    # ── BATERIA (esquerda) ──
    bat_cx, bat_y0, bat_w, bat_h = 22, 23, 6, 13
    fig.add_shape(type="rect", x0=bat_cx-bat_w/2, y0=bat_y0, x1=bat_cx+bat_w/2, y1=bat_y0+bat_h,
                  fillcolor='#111827', line=dict(color='#374151', width=1.5))
    fig.add_shape(type="rect", x0=bat_cx-1.2, y0=bat_y0+bat_h, x1=bat_cx+1.2, y1=bat_y0+bat_h+1.2,
                  fillcolor='#4B5563', line=dict(width=0))
    fill_h = (bat_h - 2) * (soc / 100.0)
    bat_color = '#EF4444' if soc < 20 else ('#F59E0B' if soc < 50 else '#10B981')
    fig.add_shape(type="rect", x0=bat_cx-bat_w/2+0.8, y0=bat_y0+0.8,
                  x1=bat_cx+bat_w/2-0.8, y1=bat_y0+0.8+fill_h,
                  fillcolor=bat_color, line=dict(width=0), opacity=0.85)
    for pct in [0.25, 0.5, 0.75]:
        fig.add_shape(type="line", x0=bat_cx-bat_w/2, y0=bat_y0+bat_h*pct,
                      x1=bat_cx+bat_w/2, y1=bat_y0+bat_h*pct,
                      line=dict(color='rgba(255,255,255,0.08)', width=0.5))
    fig.add_annotation(x=bat_cx, y=bat_y0+bat_h/2, text=f"<b>{soc:.0f}%</b>",
                       showarrow=False, font=dict(color='white', size=10, family='Inter'))

    # ── CASA (direita) ──
    casa_cx, casa_y0, casa_w, casa_h = 78, 23, 14, 12
    fig.add_shape(type="rect", x0=casa_cx-casa_w/2, y0=casa_y0, x1=casa_cx+casa_w/2, y1=casa_y0+casa_h,
                  fillcolor='#1F2937', line=dict(color='#374151', width=1.5))
    fig.add_trace(go.Scatter(
        x=[casa_cx-casa_w/2-1, casa_cx, casa_cx+casa_w/2+1],
        y=[casa_y0+casa_h, casa_y0+casa_h+5.5, casa_y0+casa_h],
        fill='toself', fillcolor='#2D3748', line=dict(color='#4B5563', width=1.5),
        hoverinfo='skip', mode='lines'))
    fig.add_shape(type="rect", x0=casa_cx-1.2, y0=casa_y0, x1=casa_cx+1.2, y1=casa_y0+4,
                  fillcolor='#4B5563', line=dict(color='#6B7280', width=0.5))
    j_op = max(0.08, min(demanda / 80.0, 1.0))
    j_col = f'rgba(251, 191, 36, {j_op:.2f})'
    fig.add_shape(type="rect", x0=casa_cx-casa_w/2+1.5, y0=casa_y0+6, x1=casa_cx-1.5, y1=casa_y0+9.5,
                  fillcolor=j_col, line=dict(color='#78350F', width=0.5))
    fig.add_shape(type="rect", x0=casa_cx+1.5, y0=casa_y0+6, x1=casa_cx+casa_w/2-1.5, y1=casa_y0+9.5,
                  fillcolor=j_col, line=dict(color='#78350F', width=0.5))

    # ── LABELS EMBAIXO DO TERRENO ──
    fig.add_annotation(x=bat_cx, y=16, text=f"🔋 <b>{soc:.0f}%</b>",
                       showarrow=False, font=dict(color=bat_color, size=12, family='Inter'))
    fig.add_annotation(x=bat_cx, y=12, text="BATERIA",
                       showarrow=False, font=dict(color='#6B7280', size=8))
    fig.add_annotation(x=casa_cx, y=16, text=f"🏠 <b>{demanda:.0f}%</b>",
                       showarrow=False, font=dict(color='#0EA5E9', size=12, family='Inter'))
    fig.add_annotation(x=casa_cx, y=12, text="DEMANDA",
                       showarrow=False, font=dict(color='#6B7280', size=8))
    fig.add_annotation(x=panel_cx, y=16, text="☀️ PAINEL SOLAR",
                       showarrow=False, font=dict(color='#6B7280', size=8))

    # ── KPIs TOPO ──
    fig.add_annotation(x=50, y=97, text=f"<b>{hora_int:02d}:{minuto:02d}</b>",
                       showarrow=False, font=dict(color='#F8FAFC', size=32, family='Inter'))
    cenario_map = {'Normal': '⛅ Normal', 'Chuvoso': '🌧️ Chuvoso', 'Verao': '☀️ Verão', 'Vazia': '✈️ Viagem'}
    fig.add_annotation(x=50, y=91, text=cenario_map.get(cenario, '⛅'),
                       showarrow=False, font=dict(color='#9CA3AF', size=11))
    fig.add_annotation(x=10, y=97, text=f"☀️ <b>{geracao:.0f}%</b>",
                       showarrow=False, font=dict(color='#F59E0B', size=13))
    fig.add_annotation(x=90, y=97, text=f"⚡ <b>{demanda:.0f}%</b>",
                       showarrow=False, font=dict(color='#0EA5E9', size=13))

    # Decisão da IA
    if acao_ia > 10:
        fig.add_annotation(x=50, y=5, text=f"🧠 Carregando  <b>+{acao_ia:.0f}%</b>",
                           showarrow=False, font=dict(color='#10B981', size=13, family='Inter'))
    elif acao_ia < -10:
        fig.add_annotation(x=50, y=5, text=f"🧠 Descarregando  <b>{acao_ia:.0f}%</b>",
                           showarrow=False, font=dict(color='#EF4444', size=13, family='Inter'))
    else:
        fig.add_annotation(x=50, y=5, text=f"🧠 Mantendo  <b>{acao_ia:.0f}%</b>",
                           showarrow=False, font=dict(color='#9CA3AF', size=13, family='Inter'))

    # Nuvens
    if cenario == 'Chuvoso':
        for nx, ny in [(20, 72), (48, 78), (75, 70)]:
            fig.add_shape(type="circle", x0=nx-7, y0=ny-2, x1=nx+7, y1=ny+3,
                          fillcolor='rgba(148,163,184,0.45)', line=dict(width=0))
            fig.add_shape(type="circle", x0=nx-3, y0=ny+1, x1=nx+9, y1=ny+5,
                          fillcolor='rgba(148,163,184,0.3)', line=dict(width=0))

    # ── Partículas de fluxo de energia ──
    # Pontos que se movem entre elementos baseado no tick (time_h como seed)
    frac_tick = (time_h * 12) % 1.0  # cicla a cada 5 min simulados
    particle_size = 5

    if is_day and geracao > 5:
        # Partículas sol → painel (3 pontos em posições diferentes)
        for offset in [0.0, 0.33, 0.66]:
            t = (frac_tick + offset) % 1.0
            px = sol_x + (panel_cx - sol_x) * t
            py = sol_y + (panel_cy - sol_y) * t
            fig.add_trace(go.Scatter(x=[px], y=[py], mode='markers',
                                     marker=dict(size=particle_size, color='#FBBF24', opacity=0.6 * (1 - t * 0.5)),
                                     hoverinfo='skip'))

    if acao_ia > 10:
        # Partículas painel → bateria
        bat_target_x, bat_target_y = 22 + 3, 23 + 7
        for offset in [0.0, 0.33, 0.66]:
            t = (frac_tick + offset) % 1.0
            px = panel_cx + (bat_target_x - panel_cx) * t
            py = panel_cy + (bat_target_y - panel_cy) * t
            fig.add_trace(go.Scatter(x=[px], y=[py], mode='markers',
                                     marker=dict(size=particle_size, color='#10B981', opacity=0.6 * (1 - t * 0.3)),
                                     hoverinfo='skip'))
    elif acao_ia < -10:
        # Partículas bateria → casa
        bat_src_x, bat_src_y = 22 + 3, 23 + 7
        casa_target_x, casa_target_y = 78 - 7, 23 + 6
        for offset in [0.0, 0.33, 0.66]:
            t = (frac_tick + offset) % 1.0
            px = bat_src_x + (casa_target_x - bat_src_x) * t
            py = bat_src_y + (casa_target_y - bat_src_y) * t
            fig.add_trace(go.Scatter(x=[px], y=[py], mode='markers',
                                     marker=dict(size=particle_size, color='#EF4444', opacity=0.6 * (1 - t * 0.3)),
                                     hoverinfo='skip'))

    return fig


# ── Callbacks da simulação ──

@app.callback(
    [Output('sim-state', 'data', allow_duplicate=True),
     Output('sim-interval', 'disabled')],
    [Input('sim-play-btn', 'n_clicks'),
     Input('sim-pause-btn', 'n_clicks'),
     Input('sim-reset-btn', 'n_clicks'),
     Input('sim-speed-1x', 'n_clicks'),
     Input('sim-speed-2x', 'n_clicks'),
     Input('sim-speed-4x', 'n_clicks')],
    [State('sim-state', 'data')],
    prevent_initial_call=True
)
def sim_controls(play_c, pause_c, reset_c, s1, s2, s4, state):
    triggered = dash.ctx.triggered_id
    if triggered == 'sim-play-btn':
        state['playing'] = True
        return state, False
    elif triggered == 'sim-pause-btn':
        state['playing'] = False
        return state, True
    elif triggered == 'sim-reset-btn':
        return {'time': 0.0, 'soc': 50.0, 'playing': False, 'log': [], 'speed': 1}, True
    elif triggered == 'sim-speed-1x':
        state['speed'] = 1
        return state, not state.get('playing', False)
    elif triggered == 'sim-speed-2x':
        state['speed'] = 2
        return state, not state.get('playing', False)
    elif triggered == 'sim-speed-4x':
        state['speed'] = 4
        return state, not state.get('playing', False)
    return state, not state.get('playing', False)


@app.callback(
    Output('sim-state', 'data', allow_duplicate=True),
    [Input('sim-interval', 'n_intervals')],
    [State('sim-state', 'data'),
     State('cenario_drop', 'value'),
     State('meta_economia', 'value'),
     State('modo_bateria', 'value')],
    prevent_initial_call=True
)
def sim_tick(n, state, cenario, meta_eco, modo_bat):
    if not state.get('playing', False):
        raise dash.exceptions.PreventUpdate

    time_h = state.get('time', 0.0)
    soc = state['soc']
    speed = state.get('speed', 1)
    hora_int = int(time_h) % 24
    step_h = (5 * speed) / 60.0

    sol_base = np.array([0,0,0,0,0,5,25,50,75,90,100,95,85,70,50,30,10,2,0,0,0,0,0,0], dtype=float)
    casa_base = np.array([10,10,10,10,15,40,80,50,30,20,20,30,40,30,40,60,90,100,85,60,40,20,10,10], dtype=float)

    if cenario == "Chuvoso":
        sol_arr = sol_base * 0.3; casa_arr = casa_base * 1.1
    elif cenario == "Verao":
        sol_arr = sol_base * 1.1; casa_arr = casa_base * 1.4
    elif cenario == "Vazia":
        sol_arr = sol_base; casa_arr = casa_base * 0.2
    else:
        sol_arr = sol_base.copy(); casa_arr = casa_base.copy()
    sol_arr = np.clip(sol_arr, 0, 100)
    casa_arr = np.clip(casa_arr, 0, 100)

    frac = time_h % 1.0
    h0, h1 = hora_int, (hora_int + 1) % 24
    geracao = float(sol_arr[h0] * (1 - frac) + sol_arr[h1] * frac)
    demanda = float(casa_arr[h0] * (1 - frac) + casa_arr[h1] * frac)

    taxa_carga_step = (0.15 if modo_bat == "Auto" else 0.4) * step_h
    taxa_descarga_step = (0.08 if modo_bat == "Auto" else 0.4) * step_h

    if modo_bat == "Carregar":
        acao = 80.0
    elif modo_bat == "Descarregar":
        acao = -80.0
    else:
        simulador.input['geracao_solar'] = geracao
        simulador.input['demanda_casa'] = float(np.clip(demanda * (1.0 + meta_eco / 100.0), 0, 100))
        try:
            simulador.compute()
            acao = simulador.output['acao_bateria']
        except:
            acao = 0.0

    taxa_step = taxa_carga_step if acao >= 0 else taxa_descarga_step
    novo_soc = float(np.clip(soc + acao * taxa_step, 0, 100))

    log = state.get('log', [])
    new_time = (time_h + step_h) % 24.0
    if int(new_time) != hora_int:
        decisao = "Carregando" if acao > 10 else ("Descarregando" if acao < -10 else "Mantendo")
        log.append(f"{hora_int:02d}:00 — Sol {geracao:.0f}% | Casa {demanda:.0f}% → {decisao} ({acao:+.1f}%) | SoC {novo_soc:.1f}%")
        if len(log) > 24:
            log = log[-24:]

    state['time'] = new_time
    state['soc'] = novo_soc
    state['log'] = log
    state['last_geracao'] = geracao
    state['last_demanda'] = demanda
    state['last_acao'] = acao
    return state


@app.callback(
    Output('sim-live-container', 'children'),
    [Input('sim-state', 'data'),
     Input('tabs', 'active_tab')],
    [State('cenario_drop', 'value')]
)
def render_sim(state, active_tab, cenario):
    if active_tab != 'tab-3':
        raise dash.exceptions.PreventUpdate

    # Garantir state válido — se None ou inválido, usa default
    if not state or not isinstance(state, dict):
        state = {'time': 0.0, 'soc': 50.0, 'playing': False, 'log': [], 'speed': 1}

    time_h = state.get('time', 0.0)
    soc = state.get('soc', 50.0)
    geracao = state.get('last_geracao', 0)
    demanda = state.get('last_demanda', 0)
    acao = state.get('last_acao', 0)
    log = state.get('log', [])
    is_playing = state.get('playing', False) is True  # explícito
    speed = state.get('speed', 1)

    fig = build_sim_scene(time_h, soc, geracao, demanda, acao, cenario)

    def spd_style(active):
        if active:
            return {'backgroundColor': '#10B981', 'border': 'none', 'fontWeight': '700', 'color': 'white', 'minWidth': '36px'}
        return {'backgroundColor': '#1F2937', 'border': '1px solid #374151', 'fontWeight': '500', 'color': '#9CA3AF', 'minWidth': '36px'}

    controls = html.Div([
        dbc.Button("▶", id='sim-play-btn', n_clicks=0, size='sm',
                   className="me-1", disabled=is_playing,
                   style={'backgroundColor': '#10B981', 'border': 'none', 'fontWeight': '700', 'fontSize': '1rem'}),
        dbc.Button("⏸", id='sim-pause-btn', n_clicks=0, size='sm',
                   className="me-1", disabled=not is_playing,
                   style={'backgroundColor': '#F59E0B', 'border': 'none', 'fontWeight': '700', 'fontSize': '1rem'}),
        dbc.Button("↺", id='sim-reset-btn', n_clicks=0, size='sm',
                   className="me-3",
                   style={'backgroundColor': '#374151', 'border': '1px solid #4B5563', 'fontWeight': '700', 'fontSize': '1rem'}),
        dbc.Button("1×", id='sim-speed-1x', n_clicks=0, size='sm', className="me-1", style=spd_style(speed == 1)),
        dbc.Button("2×", id='sim-speed-2x', n_clicks=0, size='sm', className="me-1", style=spd_style(speed == 2)),
        dbc.Button("4×", id='sim-speed-4x', n_clicks=0, size='sm', style=spd_style(speed == 4)),
    ], style={'marginBottom': '10px', 'display': 'flex', 'alignItems': 'center'})

    log_text = '\n'.join(log[-8:]) if log else 'Pressione ▶ para iniciar a simulação...'
    log_panel = html.Div([
        html.P("📟 LOG DA IA", style={'color': '#10B981', 'fontSize': '0.65rem',
                                       'fontWeight': '700', 'letterSpacing': '0.1em',
                                       'marginBottom': '4px', 'textTransform': 'uppercase'}),
        html.Pre(log_text, style={
            'color': '#9CA3AF', 'fontSize': '0.72rem', 'fontFamily': 'JetBrains Mono, monospace',
            'backgroundColor': '#0D1117', 'border': '1px solid #1F2937',
            'borderRadius': '6px', 'padding': '8px 12px', 'margin': 0,
            'maxHeight': '150px', 'overflowY': 'auto', 'whiteSpace': 'pre-wrap'
        })
    ], style={'marginTop': '10px'})

    return html.Div([
        controls,
        dcc.Graph(figure=fig, config={'displayModeBar': False, 'staticPlot': False},
                  style={'height': '520px', 'borderRadius': '12px', 'overflow': 'hidden'}),
        log_panel,
    ])


# Clientside callback: fechar sidebar automaticamente no mobile na primeira visita
app.clientside_callback(
    """
    function(n_loads) {
        if (window.innerWidth <= 768 && !window._mobileSidebarHandled) {
            window._mobileSidebarHandled = true;
            setTimeout(function() {
                const btn = document.getElementById('btn_sidebar');
                if (btn) btn.click();
            }, 200);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('sidebar-state', 'data', allow_duplicate=True),
    Input('sidebar-state', 'data'),
    prevent_initial_call='initial_duplicate'
)


if __name__ == '__main__':
    app.run(debug=True, dev_tools_ui=False, port=8050)
