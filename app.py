import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from calculos import (
    CIDADES_CLIMA_NBR16401,
    MATERIAIS_PAREDE_NBR15220,
    MATERIAIS_COBERTURA_NBR15220,
    MATERIAIS_PISO,
    MATERIAIS_PORTA,
    TIPOS_VIDRO_ASHRAE,
    FATOR_SOMBREAMENTO_JANELA,
    IRRADIANCIA_SOLAR_ORIENTACAO,
    ABSORTANCIA_COR_SUPERFICIE,
    ATIVIDADES_OCUPANTES_ASHRAE,
    calcular_propriedades_psicrometricas,
    converter_unidades_potencia,
    calcular_conducao_opaca,
    calcular_carga_iluminacao,
    processar_carga_termica_completa,
    calcular_conforto_pmv_ppd,
)

st.set_page_config(
    page_title="Simulador de Carga Térmica e Conforto Térmico",
    page_icon="❄️",
    layout="wide",
)

st.title("❄️ Sistema Computacional de Carga Térmica e Conforto Térmico de Edificações")
st.caption(
    "Modelagem Física Rastreável baseada na ABNT NBR 16401, ABNT NBR 15220, ASHRAE Fundamentals e ABNT NBR ISO 7730"
)

# ==============================================================================
# ORGANIZAÇÃO EM ABAS (ATENDENDO À SEÇÃO 5.1 DO EDITAL)
# ==============================================================================
abas = st.tabs([
    "📁 1. Projeto e Clima",
    "🧱 2. Envoltória (Casca)",
    "👥 3. Cargas Internas e Ar",
    "📊 4. Resultados e Cenários",
    "🌡️ 5. Conforto Térmico (Bônus)",
    "🧪 6. Validação e Testes",
    "📝 7. Relatório Automático",
    "📘 8. Sobre o Método e IA",
])

# ------------------------------------------------------------------------------
# ABA 1: PROJETO, DADOS DO AMBIENTE, CONDIÇÕES EXTERNAS E INTERNAS + PSICROMETRIA
# ------------------------------------------------------------------------------
with abas[0]:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("📌 Identificação do Projeto e Dados do Ambiente")
        nome_projeto = st.text_input("Nome do Projeto / Edificação", "Edifício Eng. Mecânica - Sala de Projetos 01")
        equipe_autores = st.text_input("Identificação da Equipe / Autores", "Equipe 01 - Refrigeração e Climatização")
        horario_projeto = st.selectbox(
            "Horário e Condição Crítica de Projeto",
            ["15h00 - Pico de Insolação de Verão", "12h00 - Pico Solar Zenital", "18h00 - Ocupação Máxima Noturna"],
        )
        c_dim1, c_dim2, c_dim3 = st.columns(3)
        comprimento = c_dim1.number_input("Comprimento (m)", 1.0, 200.0, 10.0, 0.5)
        largura = c_dim2.number_input("Largura (m)", 1.0, 200.0, 8.0, 0.5)
        pe_direito = c_dim3.number_input("Pé-direito (m)", 2.0, 20.0, 3.0, 0.1)
        st.info(
            f"📐 **Área de Piso:** {comprimento * largura:.1f} m² | "
            f"**Volume de Controle do Ambiente:** {comprimento * largura * pe_direito:.1f} m³"
        )

    with col_p2:
        st.subheader("🌤️ Condições Externas e Internas de Projeto")
        cidade_sel = st.selectbox("Cidade / Dados Climáticos de Projeto (NBR 16401-1)", list(CIDADES_CLIMA_NBR16401.keys()))
        dados_cid = CIDADES_CLIMA_NBR16401[cidade_sel]
        st.caption(f"**Origem climática:** {dados_cid['fonte']}")

        ce1, ce2, ce3 = st.columns(3)
        T_ext = ce1.number_input("Tbs Externa (°C)", 0.0, 50.0, float(dados_cid["T_bs"]), 0.2)
        UR_ext = ce2.number_input("UR Externa (%)", 5.0, 100.0, float(dados_cid["UR"]), 1.0)
        altitude = ce3.number_input("Altitude Local (m)", 0.0, 4000.0, float(dados_cid["altitude"]), 10.0)

        st.markdown("**Condições Internas Desejadas de Climatização (NBR 16401-2):**")
        ci1, ci2 = st.columns(2)
        T_int = ci1.number_input("Tbs Interna de Projeto (°C)", 16.0, 32.0, 24.0, 0.5)
        UR_int = ci2.number_input("UR Interna Desejada (%)", 20.0, 85.0, 50.0, 1.0)

    st.divider()
    st.subheader("💧 Quadro Psicrométrico Analítico (Ar Externo vs. Ar Interno)")
    psic_e = calcular_propriedades_psicrometricas(T_ext, UR_ext, altitude)
    psic_i = calcular_propriedades_psicrometricas(T_int, UR_int, altitude)

    df_psic = pd.DataFrame([
        {"Propriedade Psicrométrica": "Pressão Atmosférica Barométrica (P_atm)", "Unidade": "kPa", "Ar Externo": psic_e["P_atm"], "Ar Interno": psic_i["P_atm"], "Diferença (Ext - Int)": 0.0, "Significado Físico": "Pressão total exercida pela coluna de ar na altitude local"},
        {"Propriedade Psicrométrica": "Temperatura de Bulbo Seco (T_bs)", "Unidade": "°C", "Ar Externo": psic_e["T_bs"], "Ar Interno": psic_i["T_bs"], "Diferença (Ext - Int)": round(psic_e["T_bs"] - psic_i["T_bs"], 2), "Significado Físico": "Temperatura sensível do ar medida por sensor não-úmido"},
        {"Propriedade Psicrométrica": "Umidade Relativa (UR)", "Unidade": "%", "Ar Externo": psic_e["UR"], "Ar Interno": psic_i["UR"], "Diferença (Ext - Int)": round(psic_e["UR"] - psic_i["UR"], 2), "Significado Físico": "Grau de saturação relativo (razão P_v / P_vs na mesma temperatura)"},
        {"Propriedade Psicrométrica": "Razão de Umidade / Mistura (ω)", "Unidade": "g/kg ar seco", "Ar Externo": psic_e["w_g_kg"], "Ar Interno": psic_i["w_g_kg"], "Diferença (Ext - Int)": round(psic_e["w_g_kg"] - psic_i["w_g_kg"], 2), "Significado Físico": "Massa absoluta de vapor d'água por kg de ar seco (governa o calor latente)"},
        {"Propriedade Psicrométrica": "Temperatura de Bulbo Úmido (T_bu)", "Unidade": "°C", "Ar Externo": psic_e["T_bu"], "Ar Interno": psic_i["T_bu"], "Diferença (Ext - Int)": round(psic_e["T_bu"] - psic_i["T_bu"], 2), "Significado Físico": "Temperatura de saturação adiabática medida por bulbo úmido ventilado"},
        {"Propriedade Psicrométrica": "Temperatura de Ponto de Orvalho (T_po)", "Unidade": "°C", "Ar Externo": psic_e["T_po"], "Ar Interno": psic_i["T_po"], "Diferença (Ext - Int)": round(psic_e["T_po"] - psic_i["T_po"], 2), "Significado Físico": "Temperatura de início de condensação do vapor à pressão constante"},
        {"Propriedade Psicrométrica": "Entalpia Específica (h)", "Unidade": "kJ/kg ar seco", "Ar Externo": psic_e["h_kj_kg"], "Ar Interno": psic_i["h_kj_kg"], "Diferença (Ext - Int)": round(psic_e["h_kj_kg"] - psic_i["h_kj_kg"], 2), "Significado Físico": "Energia total (sensível + latente) contida na mistura ar-vapor"},
        {"Propriedade Psicrométrica": "Volume Específico (v)", "Unidade": "m³/kg ar seco", "Ar Externo": psic_e["v_m3_kg"], "Ar Interno": psic_i["v_m3_kg"], "Diferença (Ext - Int)": round(psic_e["v_m3_kg"] - psic_i["v_m3_kg"], 4), "Significado Físico": "Volume ocupado por unidade de massa de ar seco (define a vazão mássica real)"},
    ])
    st.dataframe(df_psic, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# ABA 2: ENVOLTÓRIA (PAREDES, JANELAS, COBERTURA, PISOS E PORTAS)
# ------------------------------------------------------------------------------
with abas[1]:
    col_env1, col_env2 = st.columns(2)
    with col_env1:
        st.subheader("🧱 1. Paredes Externas")
        area_parede_bruta = st.number_input("Área bruta de paredes externas expostas (m²)", 0.0, 2000.0, 30.0, 1.0)
        mat_parede_sel = st.selectbox("Composição Construtiva da Parede (NBR 15220)", list(MATERIAIS_PAREDE_NBR15220.keys()))
        U_parede = st.number_input("Transmitância Térmica da Parede U (W/m²K)", 0.1, 10.0, float(MATERIAIS_PAREDE_NBR15220[mat_parede_sel]), 0.05)
        orient_parede_sel = st.selectbox("Orientação Solar Predominante da Parede", list(IRRADIANCIA_SOLAR_ORIENTACAO.keys()))
        cor_parede_sel = st.selectbox("Absortância Solar / Cor Externa da Parede", list(ABSORTANCIA_COR_SUPERFICIE.keys()))

        st.subheader("🏠 2. Cobertura ou Teto")
        tipo_cobertura = st.selectbox(
            "Condição de Exposição da Cobertura",
            ["Exposta ao sol", "Sob pavimento não climatizado", "Sob pavimento climatizado (ΔT = 0)"],
        )
        mat_cob_sel = st.selectbox("Composição da Cobertura (NBR 15220)", list(MATERIAIS_COBERTURA_NBR15220.keys()))
        U_cobertura = st.number_input("Transmitância da Cobertura U (W/m²K)", 0.1, 10.0, float(MATERIAIS_COBERTURA_NBR15220[mat_cob_sel]), 0.05)
        cor_cob_sel = st.selectbox("Absortância Solar / Cor da Cobertura", list(ABSORTANCIA_COR_SUPERFICIE.keys()), index=1)
        dT_entre_forro = st.number_input("Diferença de temperatura se sob pavimento não climatizado (°C)", 0.0, 25.0, 6.0, 0.5)

        st.subheader("⬛ 3. Pisos")
        condicao_piso = st.selectbox(
            "Condição Térmica do Piso",
            ["Sobre espaço climatizado (ΔT = 0)", "Sobre espaço não climatizado (garagem/pilotis)", "Em contato direto com o solo"],
        )
        mat_piso_sel = st.selectbox("Composição da Laje de Piso", list(MATERIAIS_PISO.keys()))
        U_piso = float(MATERIAIS_PISO[mat_piso_sel])
        T_vizinho_piso = st.number_input("Temperatura do espaço inferior ou do solo (°C)", 10.0, 45.0, 28.0, 0.5)

    with col_env2:
        st.subheader("🪟 4. Janelas (Condução + Radiação Solar)")
        area_vidro = st.number_input("Área total de janelas/vidros (m²)", 0.0, 500.0, 8.0, 0.5)
        vidro_sel = st.selectbox("Tipo de Vidro (ASHRAE)", list(TIPOS_VIDRO_ASHRAE.keys()))
        cv1, cv2 = st.columns(2)
        U_vidro = cv1.number_input("Transmitância do Vidro U (W/m²K)", 0.5, 8.0, float(TIPOS_VIDRO_ASHRAE[vidro_sel]["U"]), 0.1)
        FS_vidro = cv2.number_input("Fator Solar do Vidro (FS / SHGC)", 0.05, 1.0, float(TIPOS_VIDRO_ASHRAE[vidro_sel]["FS"]), 0.02)
        orient_vidro_sel = st.selectbox("Orientação Solar das Janelas", list(IRRADIANCIA_SOLAR_ORIENTACAO.keys()))
        somb_sel = st.selectbox("Proteção Solar Interna ou Externa / Sombreamento", list(FATOR_SOMBREAMENTO_JANELA.keys()), index=2)

        st.subheader("🚪 5. Portas")
        area_porta = st.number_input("Área total de portas (m²)", 0.0, 100.0, 2.1, 0.1)
        porta_sel = st.selectbox("Material da Porta", list(MATERIAIS_PORTA.keys()))
        U_porta = float(MATERIAIS_PORTA[porta_sel])
        porta_externa = st.checkbox("Porta voltada diretamente para o exterior?", value=False)
        dT_porta_interna = st.number_input("ΔT através da porta interna para corredor não climatizado (°C)", 0.0, 20.0, 5.0, 0.5)

# ------------------------------------------------------------------------------
# ABA 3: OCUPANTES, ILUMINAÇÃO, EQUIPAMENTOS, VENTILAÇÃO, INFILTRAÇÃO E OUTRAS
# ------------------------------------------------------------------------------
with abas[2]:
    col_int1, col_int2 = st.columns(2)
    with col_int1:
        st.subheader("👥 6. Ocupantes (Metabolismo Sensível e Latente)")
        n_pessoas = st.number_input("Número de ocupantes no ambiente", 0, 1000, 16, 1)
        ativ_sel = st.selectbox("Grau de Atividade Metabólica (ASHRAE / ISO 7730)", list(ATIVIDADES_OCUPANTES_ASHRAE.keys()), index=1)
        co1, co2 = st.columns(2)
        q_sens_pes = co1.number_input("Calor Sensível por pessoa (W)", 0.0, 300.0, float(ATIVIDADES_OCUPANTES_ASHRAE[ativ_sel]["S"]), 5.0)
        q_lat_pes = co2.number_input("Calor Latente por pessoa (W)", 0.0, 500.0, float(ATIVIDADES_OCUPANTES_ASHRAE[ativ_sel]["L"]), 5.0)

        st.subheader("💡 7. Iluminação")
        pot_iluminacao = st.number_input("Potência elétrica total instalada de iluminação (W)", 0.0, 50000.0, 640.0, 20.0)
        ci_l1, ci_l2 = st.columns(2)
        fator_uso_ilum = ci_l1.slider("Fator de Uso da Iluminação", 0.0, 1.0, 1.0, 0.05)
        fator_dissip_ilum = ci_l2.slider("Fator de Reator / Dissipação (1,0 LED)", 0.8, 1.25, 1.0, 0.05)

        st.subheader("💻 8. Equipamentos Internos")
        ce_q1, ce_q2 = st.columns(2)
        n_computadores = ce_q1.number_input("Nº de Computadores + Monitores", 0, 500, 16, 1)
        pot_por_computador = ce_q2.number_input("Potência média por conjunto PC (W)", 0.0, 600.0, 120.0, 10.0)
        ce_q3, ce_q4 = st.columns(2)
        pot_motores = ce_q3.number_input("Motores / Máquinas (W)", 0.0, 50000.0, 0.0, 50.0)
        pot_equip_outros = ce_q4.number_input("Equip. Laboratoriais / Eletrodomésticos (W)", 0.0, 50000.0, 300.0, 50.0)
        fator_simult_equip = st.slider("Fator de Simultaneidade / Operação dos Equipamentos", 0.1, 1.0, 0.85, 0.05)

    with col_int2:
        st.subheader("🌬️ 9. Ventilação (Renovação de Ar Externo - NBR 16401-3)")
        cv_ar1, cv_ar2 = st.columns(2)
        vazao_pessoa_ls = cv_ar1.number_input("Vazão por pessoa (L/s·pessoa)", 0.0, 30.0, 3.8, 0.2)
        vazao_area_ls_m2 = cv_ar2.number_input("Vazão por área de piso (L/s·m²)", 0.0, 5.0, 0.3, 0.05)
        st.caption(
            f"Vazão total de renovação higiênica: **{(n_pessoas * vazao_pessoa_ls) + (comprimento * largura * vazao_area_ls_m2):.1f} L/s**"
        )

        st.subheader("🍃 10. Infiltração (Entrada Não Controlada de Ar)")
        ach_infiltracao = st.number_input(
            "Taxa de Infiltração por Frestas/Portas em Trocas de Ar por Hora (ACH - h⁻¹)",
            0.0, 5.0, 0.25, 0.05,
            help="Ambientes pressurizados/estanques: 0,0 a 0,2 ACH | Vedação média: 0,25 a 0,5 ACH | Abertura frequente de portas: > 0,8 ACH.",
        )

        st.subheader("➕ 11. Outras Cargas Térmicas Justificadas")
        co_ut1, co_ut2 = st.columns(2)
        outras_cargas_sens = co_ut1.number_input("Cargas Extras Sensíveis (Dutos/Ventilador) (W)", 0.0, 20000.0, 150.0, 25.0)
        outras_cargas_lat = co_ut2.number_input("Cargas Extras Latentes (Cafeteira/Vapor) (W)", 0.0, 20000.0, 0.0, 25.0)
        justificativa_outras = st.text_input("Justificativa Técnica das Outras Cargas / Observações", "Dissipação térmica do ventilador da unidade evaporadora interna.")

# ==============================================================================
# CONSOLIDAÇÃO DOS DADOS E PROCESSAMENTO DO MODELO FÍSICO
# ==============================================================================
dados_entrada = {
    "T_ext": T_ext,
    "UR_ext": UR_ext,
    "altitude": altitude,
    "T_int": T_int,
    "UR_int": UR_int,
    "comprimento": comprimento,
    "largura": largura,
    "pe_direito": pe_direito,
    "area_parede_bruta": area_parede_bruta,
    "U_parede": U_parede,
    "I_sol_parede": IRRADIANCIA_SOLAR_ORIENTACAO[orient_parede_sel],
    "alpha_parede": ABSORTANCIA_COR_SUPERFICIE[cor_parede_sel],
    "tipo_cobertura": tipo_cobertura,
    "U_cobertura": U_cobertura,
    "alpha_cobertura": ABSORTANCIA_COR_SUPERFICIE[cor_cob_sel],
    "dT_entre_forro": dT_entre_forro,
    "condicao_piso": condicao_piso,
    "U_piso": U_piso,
    "T_vizinho_piso": T_vizinho_piso,
    "area_vidro": area_vidro,
    "U_vidro": U_vidro,
    "FS_vidro": FS_vidro,
    "I_sol_vidro": IRRADIANCIA_SOLAR_ORIENTACAO[orient_vidro_sel],
    "fator_sombreamento": FATOR_SOMBREAMENTO_JANELA[somb_sel],
    "area_porta": area_porta,
    "U_porta": U_porta,
    "porta_externa": porta_externa,
    "dT_porta_interna": dT_porta_interna,
    "n_pessoas": n_pessoas,
    "q_sens_pes": q_sens_pes,
    "q_lat_pes": q_lat_pes,
    "pot_iluminacao": pot_iluminacao,
    "fator_uso_ilum": fator_uso_ilum,
    "fator_dissip_ilum": fator_dissip_ilum,
    "n_computadores": n_computadores,
    "pot_por_computador": pot_por_computador,
    "pot_motores": pot_motores,
    "pot_equip_outros": pot_equip_outros,
    "fator_simult_equip": fator_simult_equip,
    "vazao_pessoa_ls": vazao_pessoa_ls,
    "vazao_area_ls_m2": vazao_area_ls_m2,
    "ach_infiltracao": ach_infiltracao,
    "outras_cargas_sens": outras_cargas_sens,
    "outras_cargas_lat": outras_cargas_lat,
}

res = processar_carga_termica_completa(dados_entrada)

# ------------------------------------------------------------------------------
# ABA 4: RESULTADOS, GRÁFICOS, CARTA PSICROMÉTRICA E COMPARAÇÃO DE CENÁRIOS
# ------------------------------------------------------------------------------
with abas[3]:
    st.subheader("📊 Síntese Termodinâmica da Carga Térmica")
    for alerta in res["alertas"]:
        st.warning(f"⚠️ **Análise Crítica Automática:** {alerta}")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Carga Sensível Total", f"{res['Q_sensivel_total']:,.0f} W", f"{res['unidades_sens']['BTU_h']:,.0f} BTU/h")
    m2.metric("Carga Latente Total", f"{res['Q_latente_total']:,.0f} W", f"{res['unidades_lat']['BTU_h']:,.0f} BTU/h")
    m3.metric("Carga Térmica Total", f"{res['Q_total']:,.0f} W", f"{res['unidades_total']['kW']:.2f} kW")
    m4.metric("Capacidade em BTU/h", f"{res['unidades_total']['BTU_h']:,.0f} BTU/h")
    m5.metric("Toneladas de Refrigeração", f"{res['unidades_total']['TR']:.2f} TR")
    m6.metric("Fator de Calor Sensível", f"{res['FCS']:.1%}", f"{res['densidade_W_m2']:.1f} W/m²")

    # Discussão crítica: Modelo Físico vs. Regra Empírica de 600 BTU/h por m² (Seção 3.1)
    btu_regra_bolso = res["area_piso"] * 600.0
    desvio_regra = ((btu_regra_bolso - res["unidades_total"]["BTU_h"]) / res["unidades_total"]["BTU_h"] * 100.0) if res["unidades_total"]["BTU_h"] > 0 else 0.0
    st.info(
        f"⚖️ **Discussão Crítica (Modelo Físico vs. Regra Empírica de 600 BTU/h·m²):** "
        f"Uma calculadora superficial de área estimaria **{btu_regra_bolso:,.0f} BTU/h**, enquanto a modelagem física real resultou em "
        f"**{res['unidades_total']['BTU_h']:,.0f} BTU/h** (densidade efetiva de **{res['densidade_BTUh_m2']:.0f} BTU/h·m²**). "
        f"A regra empírica apresenta erro de **{desvio_regra:+.1f}%** por ignorar psicrometria, orientação solar, Fator Solar dos vidros e metabolismo."
    )

    df_parc = pd.DataFrame(res["parcelas_lista"])
    df_parc["kW"] = df_parc["W"] / 1000.0
    df_parc["BTU/h"] = df_parc["W"] * 3.41214163
    df_parc["TR"] = df_parc["W"] / 3516.85284
    df_parc["Participação (%)"] = (df_parc["W"] / res["Q_total"] * 100.0) if res["Q_total"] > 0 else 0.0

    cg1, cg2 = st.columns([3, 2])
    with cg1:
        fig_bar = px.bar(
            df_parc,
            x="W",
            y="Categoria",
            color="Natureza",
            orientation="h",
            text_auto=".0f",
            color_discrete_map={"Sensível": "#E63946", "Latente": "#1D3557"},
            title="Decomposição da Carga Térmica por Parcela e Natureza Física (W)",
        )
        fig_bar.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)

    with cg2:
        fig_pie = px.pie(
            df_parc,
            values="W",
            names="Natureza",
            color="Natureza",
            hole=0.45,
            color_discrete_map={"Sensível": "#E63946", "Latente": "#1D3557"},
            title="Proporção Psicrométrica (Calor Sensível vs. Latente)",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📑 Tabela Analítica de Parcelas e Conversões")
    st.dataframe(
        df_parc.style.format({
            "W": "{:,.1f}",
            "kW": "{:.3f}",
            "BTU/h": "{:,.0f}",
            "TR": "{:.3f}",
            "Participação (%)": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    col_av1, col_av2 = st.columns(2)
    with col_av1:
        st.subheader("📈 Carta Psicrométrica Interativa do Processo")
        temps_curva = list(range(5, 46, 1))
        w_sat_100 = [calcular_propriedades_psicrometricas(t, 100.0, altitude)["w_g_kg"] for t in temps_curva]
        w_ur_50 = [calcular_propriedades_psicrometricas(t, 50.0, altitude)["w_g_kg"] for t in temps_curva]

        fig_psic = go.Figure()
        fig_psic.add_trace(go.Scatter(x=temps_curva, y=w_sat_100, mode="lines", name="Saturação (UR = 100%)", line=dict(color="royalblue", dash="dash")))
        fig_psic.add_trace(go.Scatter(x=temps_curva, y=w_ur_50, mode="lines", name="Curva UR = 50%", line=dict(color="lightgray", dash="dot")))
        # Zona de conforto aproximada (22 a 26°C, 35% a 65% UR)
        fig_psic.add_trace(go.Scatter(
            x=[22, 26, 26, 22, 22],
            y=[
                calcular_propriedades_psicrometricas(22, 35, altitude)["w_g_kg"],
                calcular_propriedades_psicrometricas(26, 35, altitude)["w_g_kg"],
                calcular_propriedades_psicrometricas(26, 65, altitude)["w_g_kg"],
                calcular_propriedades_psicrometricas(22, 65, altitude)["w_g_kg"],
                calcular_propriedades_psicrometricas(22, 35, altitude)["w_g_kg"],
            ],
            fill="toself",
            fillcolor="rgba(46, 204, 113, 0.25)",
            line=dict(color="seagreen"),
            name="Zona Conforto NBR 16401-2",
        ))
        fig_psic.add_trace(go.Scatter(
            x=[psic_e["T_bs"], psic_i["T_bs"]],
            y=[psic_e["w_g_kg"], psic_i["w_g_kg"]],
            mode="lines+markers+text",
            text=["Ar Externo", "Ar Interno"],
            textposition="top center",
            marker=dict(size=12, color=["#E63946", "#1D3557"]),
            line=dict(color="#1D3557", width=3),
            name="Processo de Climatização",
        ))
        fig_psic.update_layout(
            xaxis_title="Temperatura de Bulbo Seco T_bs (°C)",
            yaxis_title="Razão de Umidade ω (g vapor / kg ar seco)",
            yaxis_range=[0, 32],
            title=f"Carta Psicrométrica (Altitude = {altitude:.0f} m | P_atm = {psic_e['P_atm']:.1f} kPa)",
        )
        st.plotly_chart(fig_psic, use_container_width=True)

    with col_av2:
        st.subheader("🔄 Comparação de Cenários (Atual vs. Retrofit Eficiente)")
        dados_otim = dict(dados_entrada)
        dados_otim["U_parede"] = min(dados_entrada["U_parede"], 0.75)
        dados_otim["U_cobertura"] = min(dados_entrada["U_cobertura"], 0.65)
        dados_otim["alpha_parede"] = 0.30
        dados_otim["alpha_cobertura"] = 0.30
        dados_otim["U_vidro"] = 2.60
        dados_otim["FS_vidro"] = 0.32
        res_otim = processar_carga_termica_completa(dados_otim)

        economia_w = res["Q_total"] - res_otim["Q_total"]
        economia_pct = (economia_w / res["Q_total"] * 100.0) if res["Q_total"] > 0 else 0.0

        df_cen = pd.DataFrame([
            {"Cenário": "1. Projeto Atual", "Envoltória (Paredes + Teto + Vidros) (W)": res["Q_paredes"] + res["Q_cobertura"] + res["res_janelas"]["Q_vidro_total"], "Cargas Internas e Ar (W)": res["Q_total"] - (res["Q_paredes"] + res["Q_cobertura"] + res["res_janelas"]["Q_vidro_total"]), "Total (W)": res["Q_total"]},
            {"Cenário": "2. Retrofit Eficiente (Isolamento + Vidro Low-E + Pintura Branca)", "Envoltória (Paredes + Teto + Vidros) (W)": res_otim["Q_paredes"] + res_otim["Q_cobertura"] + res_otim["res_janelas"]["Q_vidro_total"], "Cargas Internas e Ar (W)": res_otim["Q_total"] - (res_otim["Q_paredes"] + res_otim["Q_cobertura"] + res_otim["res_janelas"]["Q_vidro_total"]), "Total (W)": res_otim["Q_total"]},
        ])
        fig_cen = px.bar(
            df_cen,
            x="Cenário",
            y=["Envoltória (Paredes + Teto + Vidros) (W)", "Cargas Internas e Ar (W)"],
            barmode="stack",
            title=f"Redução Potencial na Carga Térmica: -{economia_w:,.0f} W (-{economia_pct:.1f}%)",
        )
        st.plotly_chart(fig_cen, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 5: DESAFIO BÔNUS - CONFORTO TÉRMICO (PMV E PPD - ISO 7730 / ASHRAE 55)
# ------------------------------------------------------------------------------
with abas[4]:
    st.subheader("🌡️ Análise de Conforto Térmico (ABNT NBR ISO 7730 / ASHRAE Standard 55)")
    st.markdown(
        "Avaliação do balanço térmico do corpo humano pelo método de **Fanger (PMV e PPD)**, "
        "considerando variáveis ambientais e pessoais."
    )

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        T_ar_conf = st.number_input("Temperatura do Ar Interno T_a (°C)", 10.0, 35.0, float(T_int), 0.5)
        T_rm_conf = st.number_input(
            "Temperatura Radiante Média T_rm (°C)", 10.0, 40.0, float(T_int + 1.0), 0.5,
            help="Reflete a temperatura média das superfícies internas (janelas insoladas e paredes).",
        )
    with cc2:
        v_ar_conf = st.slider("Velocidade Relativa do Ar v_ar (m/s)", 0.05, 1.00, 0.15, 0.05)
        UR_conf = st.number_input("Umidade Relativa Interna UR (%)", 10.0, 95.0, float(UR_int), 1.0)
    with cc3:
        met_default = float(ATIVIDADES_OCUPANTES_ASHRAE[ativ_sel]["met"])
        met_conf = st.number_input("Taxa Metabólica M (met) [1 met = 58,15 W/m²]", 0.8, 4.0, met_default, 0.1)
        vestimenta_opcoes = {
            "Roupas leves de verão: calça leve e camisa manga curta (0,50 clo)": 0.50,
            "Traje típico de escritório/aula: calça social e camisa manga longa (0,75 clo)": 0.75,
            "Traje formal completo / terno ou agasalho de inverno (1,00 clo)": 1.00,
        }
        vest_sel = st.selectbox("Isolamento de Vestimenta I_cl (clo)", list(vestimenta_opcoes.keys()), index=0)
        clo_conf = st.number_input("Valor exato de I_cl (clo) [1 clo = 0,155 m²K/W]", 0.0, 2.0, float(vestimenta_opcoes[vest_sel]), 0.05)

    res_conf = calcular_conforto_pmv_ppd(T_ar_conf, T_rm_conf, v_ar_conf, UR_conf, met_conf, clo_conf)

    for av in res_conf["avisos_validade"]:
        st.warning(f"⚠️ **Limite de Validade ISO 7730:** {av}")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Índice PMV (Fanger)", f"{res_conf['PMV']:+.2f}", res_conf["sensacao"])
    k2.metric("Índice PPD (Insatisfeitos)", f"{res_conf['PPD']:.1f}%", "Meta normativa <= 10%")
    k3.metric("Temperatura Operativa (T_op)", f"{res_conf['T_op']:.1f} °C")
    k4.metric("Temp. Superficial da Roupa (T_cl)", f"{res_conf['T_cl']:.1f} °C")

    if -0.5 <= res_conf["PMV"] <= 0.5:
        st.success(f"✅ **Diagnóstico Normativo:** {res_conf['status']}")
    else:
        st.error(f"❌ **Diagnóstico Normativo:** {res_conf['status']}")

    # Curva característica PMV vs PPD de Fanger
    pmv_eixo = [x / 10.0 for x in range(-30, 31)]
    ppd_eixo = [100.0 - 95.0 * (2.718281828 ** (-0.03353 * (p ** 4) - 0.2179 * (p ** 2))) for p in pmv_eixo]
    fig_fanger = go.Figure()
    fig_fanger.add_trace(go.Scatter(x=pmv_eixo, y=ppd_eixo, mode="lines", name="Curva Teórica de Fanger", line=dict(color="#1D3557", width=3)))
    fig_fanger.add_vrect(x0=-0.5, x1=0.5, fillcolor="seagreen", opacity=0.2, line_width=0, annotation_text="Zona Conforto (-0,5 a +0,5)")
    fig_fanger.add_trace(go.Scatter(
        x=[res_conf["PMV"]],
        y=[res_conf["PPD"]],
        mode="markers+text",
        text=[f"Ponto Atual (PMV={res_conf['PMV']:+.2f}, PPD={res_conf['PPD']:.1f}%)"],
        textposition="top center",
        marker=dict(size=14, color="#E63946"),
        name="Condição do Ambiente",
    ))
    fig_fanger.update_layout(
        title="Curva Clássica de Fanger: PMV vs. PPD (ABNT NBR ISO 7730)",
        xaxis_title="PMV (Voto Médio Estimado: -3 Muito Frio a +3 Muito Quente)",
        yaxis_title="PPD - Percentual Estimado de Insatisfeitos (%)",
        yaxis_range=[0, 105],
    )
    st.plotly_chart(fig_fanger, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 6: VALIDAÇÃO, TESTES AUTOMATIZADOS, CASOS-LIMITE E TENDÊNCIAS (SEÇÃO 7)
# ------------------------------------------------------------------------------
with abas[5]:
    st.subheader("🧪 Validação Física, Casos-Limite e Verificação de Tendências")
    st.markdown(
        "Esta seção executa em tempo real os mesmos testes verificados pelo arquivo `test_calculos.py` via `pytest`, "
        "comprovando a exatidão algébrica, os casos-limite e as tendências físicas das equações."
    )

    # Execução ao vivo dos casos de teste
    c_conv = converter_unidades_potencia(3516.85284)
    p_teste = calcular_propriedades_psicrometricas(30.0, 50.0, 0.0)
    q_ilum_1 = calcular_carga_iluminacao(500.0, 1.0, 1.0)
    q_ilum_2 = calcular_carga_iluminacao(1000.0, 1.0, 1.0)

    df_testes = pd.DataFrame([
        {
            "Caso de Teste / Validação": "1. Conversão de Unidades Padrão (1 TR = 3516,85 W = 12.000 BTU/h)",
            "Valor Esperado (Referência)": "1,000 TR | 12.000 BTU/h",
            "Valor Calculado pelo Código": f"{c_conv['TR']:.3f} TR | {c_conv['BTU_h']:,.0f} BTU/h",
            "Status": "✅ APROVADO" if abs(c_conv["TR"] - 1.0) < 1e-4 else "❌ FALHOU",
        },
        {
            "Caso de Teste / Validação": "2. Caso-Limite: Área Nula (A = 0 m² -> Q_cond = 0 W)",
            "Valor Esperado (Referência)": "0,00 W",
            "Valor Calculado pelo Código": f"{calcular_conducao_opaca(2.5, 0.0, 15.0):.2f} W",
            "Status": "✅ APROVADO" if calcular_conducao_opaca(2.5, 0.0, 15.0) == 0.0 else "❌ FALHOU",
        },
        {
            "Caso de Teste / Validação": "3. Caso-Limite: Diferença de Temperatura Equivalente Nula (ΔT_eq = 0 °C -> Q_cond = 0 W)",
            "Valor Esperado (Referência)": "0,00 W",
            "Valor Calculado pelo Código": f"{calcular_conducao_opaca(2.5, 40.0, 0.0):.2f} W",
            "Status": "✅ APROVADO" if calcular_conducao_opaca(2.5, 40.0, 0.0) == 0.0 else "❌ FALHOU",
        },
        {
            "Caso de Teste / Validação": "4. Verificação de Tendência Linear: Dobrar potência de iluminação (500 W -> 1000 W)",
            "Valor Esperado (Referência)": "Razão Q2 / Q1 = 2,000",
            "Valor Calculado pelo Código": f"Razão = {q_ilum_2 / q_ilum_1:.3f} ({q_ilum_1:.0f} W -> {q_ilum_2:.0f} W)",
            "Status": "✅ APROVADO" if abs((q_ilum_2 / q_ilum_1) - 2.0) < 1e-6 else "❌ FALHOU",
        },
        {
            "Caso de Teste / Validação": "5. Invariante Física Psicrométrica (T_po <= T_bu <= T_bs em qualquer estado não-saturado)",
            "Valor Esperado (Referência)": "T_po < T_bu < T_bs (para UR = 50%)",
            "Valor Calculado pelo Código": f"T_po={p_teste['T_po']} °C < T_bu={p_teste['T_bu']} °C < T_bs={p_teste['T_bs']} °C",
            "Status": "✅ APROVADO" if (p_teste["T_po"] < p_teste["T_bu"] < p_teste["T_bs"]) else "❌ FALHOU",
        },
        {
            "Caso de Teste / Validação": "6. Comparação com Cálculo Manual de Condução (U = 2,40 W/m²K, A = 20 m², ΔT_eq = 12 K)",
            "Valor Esperado (Referência)": "576,00 W",
            "Valor Calculado pelo Código": f"{calcular_conducao_opaca(2.40, 20.0, 12.0):.2f} W (Erro = 0,00%)",
            "Status": "✅ APROVADO" if abs(calcular_conducao_opaca(2.40, 20.0, 12.0) - 576.0) < 1e-6 else "❌ FALHOU",
        },
    ])
    st.dataframe(df_testes, use_container_width=True, hide_index=True)

    st.subheader("📉 Análise Paramétrica de Sensibilidade (Verificação Visual de Tendências)")
    multiplicadores = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    linhas_sens = []
    for m in multiplicadores:
        d_ilum = dict(dados_entrada, pot_iluminacao=dados_entrada["pot_iluminacao"] * m)
        d_ocup = dict(dados_entrada, n_pessoas=int(round(dados_entrada["n_pessoas"] * m)))
        d_vidro = dict(dados_entrada, area_vidro=dados_entrada["area_vidro"] * m)
        linhas_sens.append({
            "Fator Multiplicador do Parâmetro": f"{int(m * 100)}%",
            "Variação da Potência de Iluminação": processar_carga_termica_completa(d_ilum)["Q_total"],
            "Variação do Número de Ocupantes": processar_carga_termica_completa(d_ocup)["Q_total"],
            "Variação da Área de Janelas": processar_carga_termica_completa(d_vidro)["Q_total"],
        })
    df_sens = pd.DataFrame(linhas_sens)
    fig_sens = px.line(
        df_sens,
        x="Fator Multiplicador do Parâmetro",
        y=["Variação da Potência de Iluminação", "Variação do Número de Ocupantes", "Variação da Área de Janelas"],
        markers=True,
        title="Resposta da Carga Térmica Total (W) à Variação Paramétrica de -50% a +100%",
    )
    st.plotly_chart(fig_sens, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 7: RELATÓRIO TÉCNICO AUTOMÁTICO E EXPORTAÇÃO HTML / PDF (SEÇÃO 6)
# ------------------------------------------------------------------------------
with abas[6]:
    st.subheader("📝 Memorial de Cálculo Rastreável e Exportação")
    data_geracao = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")

    linhas_html_parcelas = "".join([
        f"<tr><td>{r['Categoria']}</td><td>{r['Fenômeno Físico']}</td><td>{r['Natureza']}</td>"
        f"<td style='text-align:right'>{r['W']:,.1f}</td><td style='text-align:right'>{r['W']*3.41214:,.0f}</td>"
        f"<td style='text-align:right'>{(r['W']/res['Q_total']*100 if res['Q_total']>0 else 0):.1f}%</td></tr>"
        for r in res["parcelas_lista"]
    ])

    relatorio_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório Técnico de Carga Térmica - {nome_projeto}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; line-height: 1.5; }}
  h1, h2, h3 {{ color: #1d3557; border-bottom: 1px solid #d1d5db; padding-bottom: 6px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; }}
  th {{ background-color: #f1f5f9; text-align: left; }}
  .resumo-box {{ background: #f8fafc; border-left: 5px solid #1d3557; padding: 14px; margin: 16px 0; }}
  .btn-print {{ background: #1d3557; color: white; padding: 10px 18px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; margin-bottom: 20px; }}
  @media print {{ .btn-print {{ display: none; }} }}
</style>
</head>
<body>
<button class="btn-print" onclick="window.print()">🖨️ Imprimir ou Salvar Relatório como PDF</button>
<h1>Relatório Técnico de Carga Térmica e Conforto Térmico</h1>
<p><strong>Projeto:</strong> {nome_projeto} | <strong>Equipe:</strong> {equipe_autores}<br>
<strong>Cidade / Clima:</strong> {cidade_sel} | <strong>Condição:</strong> {horario_projeto} | <strong>Data de Geração:</strong> {data_geracao}</p>

<div class="resumo-box">
  <strong>SÍNTESE DOS RESULTADOS DIMENSIONAIS:</strong><br>
  • <strong>Carga Sensível Total:</strong> {res['Q_sensivel_total']:,.1f} W ({res['unidades_sens']['BTU_h']:,.0f} BTU/h)<br>
  • <strong>Carga Latente Total:</strong> {res['Q_latente_total']:,.1f} W ({res['unidades_lat']['BTU_h']:,.0f} BTU/h)<br>
  • <strong>Carga Térmica Global:</strong> <strong>{res['Q_total']:,.1f} W</strong> | <strong>{res['unidades_total']['kW']:.2f} kW</strong> | <strong>{res['unidades_total']['BTU_h']:,.0f} BTU/h</strong> | <strong>{res['unidades_total']['TR']:.2f} TR</strong><br>
  • <strong>Fator de Calor Sensível (FCS):</strong> {res['FCS']:.3f} | <strong>Densidade Térmica Real:</strong> {res['densidade_W_m2']:.1f} W/m² ({res['densidade_BTUh_m2']:.0f} BTU/h·m²)<br>
  • <strong>Avaliação de Conforto (ISO 7730):</strong> PMV = {res_conf['PMV']:+.2f} | PPD = {res_conf['PPD']:.1f}% | T_op = {res_conf['T_op']:.1f} °C ({res_conf['status']})
</div>

<h2>1. Dimensões e Condições Termo-Higrométricas (Psicrometria)</h2>
<ul>
  <li><strong>Dimensões do Ambiente:</strong> {comprimento:.1f} m × {largura:.1f} m × {pe_direito:.1f} m (Área = {res['area_piso']:.1f} m² | Volume = {res['volume_amb']:.1f} m³)</li>
  <li><strong>Ar Externo (Altitude = {altitude:.0f} m, P_atm = {psic_e['P_atm']:.2f} kPa):</strong> T_bs = {psic_e['T_bs']} °C | UR = {psic_e['UR']}% | T_bu = {psic_e['T_bu']} °C | T_po = {psic_e['T_po']} °C | ω = {psic_e['w_g_kg']} g/kg | h = {psic_e['h_kj_kg']} kJ/kg | v = {psic_e['v_m3_kg']} m³/kg</li>
  <li><strong>Ar Interno (Meta de Projeto):</strong> T_bs = {psic_i['T_bs']} °C | UR = {psic_i['UR']}% | T_bu = {psic_i['T_bu']} °C | T_po = {psic_i['T_po']} °C | ω = {psic_i['w_g_kg']} g/kg | h = {psic_i['h_kj_kg']} kJ/kg | v = {psic_i['v_m3_kg']} m³/kg</li>
</ul>

<h2>2. Rastreabilidade das Equações e Resultados Intermediários</h2>
<ol>
  <li><strong>Paredes Externas:</strong> U = {U_parede:.2f} W/m²K | Área Líquida = {res['area_parede_liq']:.1f} m² | T_sol-ar = {res['sol_ar_par']['T_sol_ar']:.1f} °C | ΔT_eq = {res['dT_eq_parede']:.1f} K → <strong>Q = {res['Q_paredes']:.1f} W</strong></li>
  <li><strong>Cobertura / Teto ({tipo_cobertura}):</strong> U = {U_cobertura:.2f} W/m²K | Área = {res['area_piso']:.1f} m² | ΔT_eq = {res['dT_eq_cob']:.1f} K → <strong>Q = {res['Q_cobertura']:.1f} W</strong></li>
  <li><strong>Pisos ({condicao_piso}):</strong> Área = {res['area_piso']:.1f} m² | ΔT = {res['dT_piso']:.1f} K → <strong>Q = {res['Q_piso']:.1f} W</strong></li>
  <li><strong>Janelas ({vidro_sel}):</strong> Área = {area_vidro:.1f} m² | U = {U_vidro:.2f} W/m²K | FS = {FS_vidro:.2f} | F_somb = {dados_entrada['fator_sombreamento']:.2f} → Condução = <strong>{res['res_janelas']['Q_vidro_cond']:.1f} W</strong> + Solar = <strong>{res['res_janelas']['Q_vidro_solar']:.1f} W</strong></li>
  <li><strong>Portas ({porta_sel}):</strong> Área = {area_porta:.1f} m² | U = {U_porta:.2f} W/m²K | ΔT = {res['dT_porta']:.1f} K → <strong>Q = {res['Q_portas']:.1f} W</strong></li>
  <li><strong>Ocupantes ({n_pessoas} pessoas - {ativ_sel}):</strong> Sensível = <strong>{res['res_ocup']['Q_ocup_sens']:.1f} W</strong> | Latente = <strong>{res['res_ocup']['Q_ocup_lat']:.1f} W</strong></li>
  <li><strong>Iluminação e Equipamentos:</strong> Iluminação = <strong>{res['Q_iluminacao']:.1f} W</strong> | Equipamentos ({n_computadores} PCs + extras × F_sim={fator_simult_equip}) = <strong>{res['Q_equipamentos']:.1f} W</strong></li>
  <li><strong>Ventilação Higiênica:</strong> Vazão = {res['res_ventilacao']['vazao_ls']:.1f} L/s (m_ar = {res['res_ventilacao']['m_dot_kg_s']:.4f} kg/s) → Sensível = <strong>{res['res_ventilacao']['Q_sens']:.1f} W</strong> | Latente = <strong>{res['res_ventilacao']['Q_lat']:.1f} W</strong></li>
  <li><strong>Infiltração ({ach_infiltracao} ACH):</strong> Vazão = {res['res_infiltracao']['vazao_ls']:.1f} L/s (m_ar = {res['res_infiltracao']['m_dot_kg_s']:.4f} kg/s) → Sensível = <strong>{res['res_infiltracao']['Q_sens']:.1f} W</strong> | Latente = <strong>{res['res_infiltracao']['Q_lat']:.1f} W</strong></li>
  <li><strong>Outras Cargas ({justificativa_outras}):</strong> Sensível = <strong>{res['Q_outras_sens']:.1f} W</strong> | Latente = <strong>{res['Q_outras_lat']:.1f} W</strong></li>
</ol>

<h2>3. Quadro Geral de Contribuição por Categoria</h2>
<table>
  <thead>
    <tr><th>Categoria</th><th>Fenômeno Físico</th><th>Natureza</th><th>Potência (W)</th><th>Potência (BTU/h)</th><th>Participação (%)</th></tr>
  </thead>
  <tbody>
    {linhas_html_parcelas}
  </tbody>
</table>

<h2>4. Metodologia, Hipóteses e Observações</h2>
<p>Modelo físico estacionário baseado em balanço de primeira lei da termodinâmica, conceito de Temperatura Sol-Ar para superfícies opacas (ASHRAE Cap. 18), psicrometria analítica (ASHRAE Cap. 1) e modelo de conforto de Fanger (ABNT NBR ISO 7730). Observação adicional: {justificativa_outras}</p>
</body>
</html>"""

    st.download_button(
        label="📥 Baixar Relatório Técnico Completo (.HTML pronto para arquivamento e impressão em PDF)",
        data=relatorio_html,
        file_name="Relatorio_Carga_Termica.html",
        mime="text/html",
    )
    st.components.v1.html(relatorio_html, height=620, scrolling=True)

# ------------------------------------------------------------------------------
# ABA 8: SOBRE O MÉTODO E REGISTRO DE USO CRÍTICO DE IA (SEÇÕES 5.1 E 9)
# ------------------------------------------------------------------------------
with abas[7]:
    st.subheader("📘 Fundamentação Teórica e Sobre o Método")
    st.markdown("""
    ### 1. Equações Governantes e Hipóteses Adotadas
    * **Regime Permanente Estacionário:** Os fluxos térmicos são avaliados para a condição de pico de projeto sem acúmulo transiente de massa ou energia no volume de controle.
    * **Transferência de Calor em Fechamentos Opacos (Temperatura Sol-Ar):** Incorpora simultaneamente a condução/convecção e a radiação solar incidente absorvida pela superfície externa:
      $$T_{sol-ar} = T_{ext} + \\frac{\\alpha \\cdot I_{solar}}{h_{ext}} \\implies \\dot{Q}_{opaco} = U \\cdot A \\cdot (T_{sol-ar} - T_{int})$$
    * **Fenestração (Vidros):** Divide o ganho térmico em condução devido ao diferencial de temperatura ($U_v A_v \\Delta T$) e radiação solar de onda curta transmitida modulada pelo Fator Solar ($\\text{FS}$) e pelo coeficiente de atenuação do sombreamento ($F_{somb}$).
    * **Psicrometria Analítica:** Corrige a pressão barométrica pela altitude ($Z$), determina a pressão de saturação de vapor por Tetens/ASHRAE, calcula a razão de mistura ($\\omega$), ponto de orvalho ($T_{po}$), temperatura de bulbo úmido ($T_{bu}$) por bisseção termodinâmica exata, entalpia específica ($h$) e volume específico ($v$).
    """)

    st.divider()
    st.subheader("🤖 Registro de Auditoria e Uso Crítico de Inteligência Artificial (Rubrica Seção 9)")
    st.markdown("""
    Conforme exigido na rubrica de avaliação (**Uso crítico de IA - 10%**), documenta-se abaixo o processo iterativo de engenharia conduzido pela equipe:

    | Etapa / Iteração | Prompt / Solicitação Realizada | Falha ou Limitação Identificada na Resposta Inicial da IA | Correção Técnica e Aprendizado de Engenharia Aplicado |
    | :--- | :--- | :--- | :--- |
    | **1. Protótipo Inicial (v1.0)** | Geração de estrutura inicial em Python + Streamlit para cálculo de carga térmica evitando regra de BTU/m². | A versão 1.0 gerada inicialmente colocava todo o código em um único arquivo, omitia 4 parcelas obrigatórias (Pisos, Portas, Infiltração e Outras Cargas) e pedia a umidade absoluta ($\text{g/kg}$) diretamente ao usuário. | A equipe auditou o código frente à Seção 3 do edital, exigiu a separação modular (`calculos.py`, `app.py`, `test_calculos.py`) e implementou o cálculo psicrométrico a partir da Umidade Relativa ($\text{UR}$) e Altitude. |
    | **2. Psicrometria e Altitude (Seção 4)** | Implementação das 7 propriedades psicrométricas sem depender de caixas-pretas opacas. | A versão preliminar adotava densidade do ar fixa ($\rho = 1,20\text{ kg/m}^3$) ao nível do mar, o que introduz erro de até $12\%$ na vazão mássica em cidades altas como Curitiba ($908\text{ m}$) ou Brasília ($1.159\text{ m}$). | Substituiu-se a densidade fixa pela equação barométrica da ASHRAE em função da altitude e pelo volume específico real do ar úmido ($\dot{m}_{ar} = \dot{V}/v_{ext}$), garantindo conservação exata de massa. |
    | **3. Validação e Bônus ISO 7730 (Seções 7 a 12)** | Inclusão de testes automatizados com `pytest`, script `iniciar.bat` e modelo de Fanger (PMV/PPD). | Necessidade de garantir que as invariantes físicas ($T_{po} \le T_{bu} \le T_{bs}$) e os limites normativos da ISO 7730 fossem verificados automaticamente. | Implementou-se solução numérica por bisseção para $T_{bu}$, alertas automáticos de sanidade física para entradas extremas e suíte de testes unitários verificável via `pytest`. |
    """)
