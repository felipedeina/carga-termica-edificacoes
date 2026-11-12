import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from calculos import (
    CIDADES_CLIMA_NBR16401,
    MATERIAIS_PAREDE_NBR15220,
    CONDUTIVIDADE_MIOLO_PAREDE,
    ISOLANTES_TERMICOS_NBR15220,
    MATERIAIS_COBERTURA_NBR15220,
    RESISTENCIA_TELHAS_NBR15220,
    CONDUTIVIDADE_LAJE_FORRO,
    MATERIAIS_PISO,
    MATERIAIS_PORTA,
    TIPOS_VIDRO_ASHRAE,
    FATOR_SOMBREAMENTO_JANELA,
    IRRADIANCIA_SOLAR_ORIENTACAO,
    ABSORTANCIA_COR_SUPERFICIE,
    ATIVIDADES_OCUPANTES_ASHRAE,
    AMBIENTES_VENTILACAO_NBR16401,
    NIVEIS_INFILTRACAO_ACH,
    calcular_U_parede_camadas,
    calcular_U_cobertura_camadas,
    calcular_propriedades_vidro_visual,
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

abas = st.tabs([
    "📁 1. Projeto e Clima",
    "🧱 2. Envoltória (Casca)",
    "👥 3. Cargas Internas e Ar",
    "📊 4. Resultados e Cenários",
    "🌡️ 5. Conforto Térmico (Bônus)",
    "🧪 6. Validação e Testes",
    "📝 7. Relatório Automático",
    "📘 8. Método, Questões e IA",
])

# ------------------------------------------------------------------------------
# ABA 1: PROJETO, DADOS DO AMBIENTE, CONDIÇÕES EXTERNAS E INTERNAS + PSICROMETRIA
# ------------------------------------------------------------------------------
with abas[0]:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("📌 Identificação do Projeto e Dimensões da Sala")
        nome_projeto = st.text_input("Nome do Projeto / Edificação", "Edifício Eng. Mecânica - Sala de Projetos 01")
        equipe_autores = st.text_input("Identificação da Equipe / Autores", "Equipe 01 - Refrigeração e Climatização")
        horario_projeto = st.selectbox(
            "Horário e Condição Crítica de Projeto",
            ["15h00 - Pico de Insolação de Verão", "12h00 - Pico Solar Zenital", "18h00 - Ocupação Máxima Noturna"],
        )
        c_dim1, c_dim2, c_dim3 = st.columns(3)
        comprimento = c_dim1.number_input("Comprimento da Sala (m)", 1.0, 200.0, 10.0, 0.5)
        largura = c_dim2.number_input("Largura da Sala (m)", 1.0, 200.0, 8.0, 0.5)
        pe_direito = c_dim3.number_input("Pé-direito / Altura (m)", 2.0, 20.0, 3.0, 0.1)
        st.info(
            f"📐 **Área de Piso Calculada:** {comprimento * largura:.1f} m² | "
            f"**Volume de Ar do Ambiente:** {comprimento * largura * pe_direito:.1f} m³"
        )

    with col_p2:
        st.subheader("🌤️ Clima Externo e Condições Internas Desejadas")
        cidade_sel = st.selectbox("Cidade / Dados Climáticos Normativos (NBR 16401-1)", list(CIDADES_CLIMA_NBR16401.keys()))
        dados_cid = CIDADES_CLIMA_NBR16401[cidade_sel]
        st.caption(f"**Fonte dos dados climáticos:** {dados_cid['fonte']}")

        ce1, ce2, ce3 = st.columns(3)
        T_ext = ce1.number_input("Temperatura do Ar Externo - Tbs (°C)", 0.0, 50.0, float(dados_cid["T_bs"]), 0.2)
        UR_ext = ce2.number_input("Umidade Relativa Externa - UR (%)", 5.0, 100.0, float(dados_cid["UR"]), 1.0)
        altitude = ce3.number_input("Altitude da Cidade (m)", 0.0, 4000.0, float(dados_cid["altitude"]), 10.0)

        st.markdown("**Condições Internas Desejadas de Climatização (Conforto NBR 16401-2):**")
        ci1, ci2 = st.columns(2)
        T_int = ci1.number_input("Temperatura Interna Desejada - Tbs (°C)", 16.0, 32.0, 24.0, 0.5)
        UR_int = ci2.number_input("Umidade Relativa Interna Desejada - UR (%)", 20.0, 85.0, 50.0, 1.0)

    st.divider()
    st.subheader("💧 Quadro Psicrométrico Analítico (Ar Externo vs. Ar Interno)")
    psic_e = calcular_propriedades_psicrometricas(T_ext, UR_ext, altitude)
    psic_i = calcular_propriedades_psicrometricas(T_int, UR_int, altitude)

    df_psic = pd.DataFrame([
        {"Propriedade Psicrométrica": "Pressão Atmosférica Barométrica (P_atm)", "Unidade": "kPa", "Ar Externo": psic_e["P_atm"], "Ar Interno": psic_i["P_atm"], "Diferença (Ext - Int)": 0.0, "Significado Físico": "Pressão total exercida pela coluna de ar na altitude local"},
        {"Propriedade Psicrométrica": "Temperatura de Bulbo Seco (T_bs)", "Unidade": "°C", "Ar Externo": psic_e["T_bs"], "Ar Interno": psic_i["T_bs"], "Diferença (Ext - Int)": round(psic_e["T_bs"] - psic_i["T_bs"], 2), "Significado Físico": "Temperatura comum do ar (mede o nível de calor sensível)"},
        {"Propriedade Psicrométrica": "Umidade Relativa (UR)", "Unidade": "%", "Ar Externo": psic_e["UR"], "Ar Interno": psic_i["UR"], "Diferença (Ext - Int)": round(psic_e["UR"] - psic_i["UR"], 2), "Significado Físico": "Proporção de vapor em relação ao máximo que o ar suporta nessa temperatura"},
        {"Propriedade Psicrométrica": "Razão de Umidade / Mistura (ω)", "Unidade": "g/kg ar seco", "Ar Externo": psic_e["w_g_kg"], "Ar Interno": psic_i["w_g_kg"], "Diferença (Ext - Int)": round(psic_e["w_g_kg"] - psic_i["w_g_kg"], 2), "Significado Físico": "Gramas de água em forma de vapor por kg de ar seco (define o calor latente)"},
        {"Propriedade Psicrométrica": "Temperatura de Bulbo Úmido (T_bu)", "Unidade": "°C", "Ar Externo": psic_e["T_bu"], "Ar Interno": psic_i["T_bu"], "Diferença (Ext - Int)": round(psic_e["T_bu"] - psic_i["T_bu"], 2), "Significado Físico": "Temperatura atingida pela evaporação de água em termômetro de bulbo úmido"},
        {"Propriedade Psicrométrica": "Temperatura de Ponto de Orvalho (T_po)", "Unidade": "°C", "Ar Externo": psic_e["T_po"], "Ar Interno": psic_i["T_po"], "Diferença (Ext - Int)": round(psic_e["T_po"] - psic_i["T_po"], 2), "Significado Físico": "Temperatura em que o vapor d'água começa a condensar (formar gotas)"},
        {"Propriedade Psicrométrica": "Entalpia Específica (h)", "Unidade": "kJ/kg ar seco", "Ar Externo": psic_e["h_kj_kg"], "Ar Interno": psic_i["h_kj_kg"], "Diferença (Ext - Int)": round(psic_e["h_kj_kg"] - psic_i["h_kj_kg"], 2), "Significado Físico": "Energia térmica total (sensível + latente) contida na mistura ar-vapor"},
        {"Propriedade Psicrométrica": "Volume Específico (v)", "Unidade": "m³/kg ar seco", "Ar Externo": psic_e["v_m3_kg"], "Ar Interno": psic_i["v_m3_kg"], "Diferença (Ext - Int)": round(psic_e["v_m3_kg"] - psic_i["v_m3_kg"], 4), "Significado Físico": "Volume ocupado por 1 kg de ar seco na altitude local"},
    ])
    st.dataframe(df_psic, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# ABA 2: ENVOLTÓRIA (PAREDES, COBERTURA, PISOS, JANELAS E PORTAS)
# ------------------------------------------------------------------------------
with abas[1]:
    col_env1, col_env2 = st.columns(2)

    with col_env1:
        # 1. PAREDES EXTERNAS
        st.subheader("🧱 1. Paredes Externas")
        modo_dim_parede = st.radio(
            "Como deseja informar o tamanho das paredes externas (que pegam sol/ar livre)?",
            ["Pelas medidas das paredes da sala (Mais fácil)", "Digitar a área total em m² diretamente"],
            horizontal=True,
        )
        if "medidas" in modo_dim_parede:
            cp_par1, cp_par2 = st.columns(2)
            n_par_comp = cp_par1.selectbox(f"Quantas paredes de {comprimento:.1f} m dão para o exterior?", [0, 1, 2], index=1)
            n_par_larg = cp_par2.selectbox(f"Quantas paredes de {largura:.1f} m dão para o exterior?", [0, 1, 2], index=0)
            comp_total_ext = (n_par_comp * comprimento) + (n_par_larg * largura)
            area_parede_bruta = comp_total_ext * pe_direito
            st.caption(
                f"📏 **Cálculo automático:** Extensão externa = {comp_total_ext:.1f} m × Pé-direito = {pe_direito:.1f} m "
                f"→ **Área Bruta de Paredes Externas = {area_parede_bruta:.1f} m²**"
            )
        else:
            area_parede_bruta = st.number_input("Área bruta de paredes externas expostas (m²)", 0.0, 2000.0, 30.0, 1.0)

        modo_u_parede = st.radio(
            "Como deseja definir o material da parede (Transmitância U)?",
            ["Informar material e espessura em centímetros (Cálculo físico NBR 15220)", "Escolher parede pronta da lista"],
        )
        if "espessura" in modo_u_parede:
            miolo_sel = st.selectbox("Material principal da parede (Tijolo / Bloco)", list(CONDUTIVIDADE_MIOLO_PAREDE.keys()))
            cm1, cm2 = st.columns(2)
            esp_miolo_cm = cm1.number_input("Espessura do tijolo/bloco (cm)", 5.0, 50.0, 14.0, 1.0)
            esp_reboco_cm = cm2.number_input("Espessura total de reboco/argamassa (cm)", 0.0, 10.0, 3.0, 0.5)
            isol_par_sel = st.selectbox("Possui camada de isolante térmico na parede?", list(ISOLANTES_TERMICOS_NBR15220.keys()))
            esp_isol_par_cm = 0.0
            if ISOLANTES_TERMICOS_NBR15220[isol_par_sel] > 0:
                esp_isol_par_cm = st.number_input("Espessura do isolante na parede (cm)", 1.0, 20.0, 5.0, 0.5)
            res_u_par = calcular_U_parede_camadas(
                CONDUTIVIDADE_MIOLO_PAREDE[miolo_sel], esp_miolo_cm, esp_reboco_cm,
                ISOLANTES_TERMICOS_NBR15220[isol_par_sel], esp_isol_par_cm,
            )
            U_parede = res_u_par["U"]
            st.info(f"🔬 **Transmitância Calculada pelas Camadas:** $R_{{total}} = {res_u_par['R_total']:.2f}\\text{{ m}}^2\\text{{K/W}} \\rightarrow \\mathbf{{U = {U_parede:.2f}\\text{{ W/m}}^2\\text{{K}}}}$")
        else:
            mat_parede_sel = st.selectbox("Composição Construtiva da Parede (NBR 15220)", list(MATERIAIS_PAREDE_NBR15220.keys()))
            U_parede = float(MATERIAIS_PAREDE_NBR15220[mat_parede_sel])
            st.info(f"🔬 **Transmitância Normativa Adotada:** $\\mathbf{{U = {U_parede:.2f}\\text{{ W/m}}^2\\text{{K}}}}$")

        orient_parede_sel = st.selectbox("Orientação Solar Predominante da Parede Externa", list(IRRADIANCIA_SOLAR_ORIENTACAO.keys()))
        cor_parede_sel = st.selectbox("Cor Externa da Parede (Absortância Solar)", list(ABSORTANCIA_COR_SUPERFICIE.keys()))

        st.divider()
        # 2. COBERTURA OU TETO
        st.subheader("🏠 2. Cobertura ou Teto")
        tipo_cobertura = st.selectbox(
            "O que existe acima do teto desta sala?",
            ["Exposta ao sol", "Sob pavimento não climatizado", "Sob pavimento climatizado (ΔT = 0)"],
        )
        if tipo_cobertura == "Sob pavimento climatizado (ΔT = 0)":
            U_cobertura = 2.05
            cor_cob_sel = list(ABSORTANCIA_COR_SUPERFICIE.keys())[1]
            dT_entre_forro = 0.0
            st.success("✅ Como o andar de cima também é climatizado na mesma temperatura, não há ganho de calor pelo teto ($\dot{Q}_{cob} = 0\text{ W}$).")
        else:
            modo_u_cob = st.radio(
                "Como deseja informar a construção do telhado/teto?",
                ["Informar tipo de telha, laje/forro e espessura (Cálculo NBR 15220)", "Escolher cobertura pronta da lista"],
            )
            if "Informar" in modo_u_cob:
                telha_sel = st.selectbox("Tipo de telha superior", list(RESISTENCIA_TELHAS_NBR15220.keys()))
                possui_atico = st.checkbox("Existe espaço de ar (ático) entre a telha e a laje/forro?", value=True)
                laje_forro_sel = st.selectbox("Material da laje ou forro interno", list(CONDUTIVIDADE_LAJE_FORRO.keys()))
                esp_laje_cm = 0.0
                if CONDUTIVIDADE_LAJE_FORRO[laje_forro_sel] > 0:
                    esp_laje_cm = st.number_input("Espessura da laje ou forro (cm)", 1.0, 30.0, 10.0, 1.0)
                isol_cob_sel = st.selectbox("Possui manta térmica ou isolante no teto?", list(ISOLANTES_TERMICOS_NBR15220.keys()))
                esp_isol_cob_cm = 0.0
                if ISOLANTES_TERMICOS_NBR15220[isol_cob_sel] > 0:
                    esp_isol_cob_cm = st.number_input("Espessura do isolante na cobertura (cm)", 1.0, 20.0, 5.0, 0.5)
                res_u_cob = calcular_U_cobertura_camadas(
                    RESISTENCIA_TELHAS_NBR15220[telha_sel], possui_atico,
                    CONDUTIVIDADE_LAJE_FORRO[laje_forro_sel], esp_laje_cm,
                    ISOLANTES_TERMICOS_NBR15220[isol_cob_sel], esp_isol_cob_cm,
                )
                U_cobertura = res_u_cob["U"]
                st.info(f"🔬 **Transmitância Calculada da Cobertura:** $R_{{total}} = {res_u_cob['R_total']:.2f}\\text{{ m}}^2\\text{{K/W}} \\rightarrow \\mathbf{{U = {U_cobertura:.2f}\\text{{ W/m}}^2\\text{{K}}}}$")
            else:
                mat_cob_sel = st.selectbox("Composição da Cobertura (NBR 15220)", list(MATERIAIS_COBERTURA_NBR15220.keys()))
                U_cobertura = float(MATERIAIS_COBERTURA_NBR15220[mat_cob_sel])
                st.info(f"🔬 **Transmitância Normativa da Cobertura:** $\\mathbf{{U = {U_cobertura:.2f}\\text{{ W/m}}^2\\text{{K}}}}$")

            if tipo_cobertura == "Exposta ao sol":
                cor_cob_sel = st.selectbox("Cor Externa do Telhado / Cobertura", list(ABSORTANCIA_COR_SUPERFICIE.keys()), index=1)
                dT_entre_forro = 0.0
            else:
                cor_cob_sel = list(ABSORTANCIA_COR_SUPERFICIE.keys())[1]
                dT_entre_forro = max(0.0, 0.5 * (T_ext - T_int))
                st.caption(f"🌡️ Diferença de temperatura estimada para o pavimento superior não climatizado: **{dT_entre_forro:.1f} °C**.")

        st.divider()
        # 3. PISOS
        st.subheader("⬛ 3. Pisos")
        condicao_piso = st.selectbox(
            "O que existe embaixo do piso desta sala?",
            ["Sobre espaço climatizado (ΔT = 0)", "Sobre espaço não climatizado (garagem/pilotis)", "Em contato direto com o solo"],
        )
        if condicao_piso == "Sobre espaço climatizado (ΔT = 0)":
            mat_piso_sel = list(MATERIAIS_PISO.keys())[0]
            U_piso = float(MATERIAIS_PISO[mat_piso_sel])
            T_vizinho_piso = T_int
            st.success("✅ Sem transferência de calor pelo piso ($\dot{Q}_{piso} = 0\text{ W}$).")
        else:
            mat_piso_sel = st.selectbox("Tipo de Laje de Piso", list(MATERIAIS_PISO.keys()))
            U_piso = float(MATERIAIS_PISO[mat_piso_sel])
            T_vizinho_piso = T_ext - 3.0 if "garagem" in condicao_piso else 25.0
            st.caption(f"🔬 Transmitância do piso: **{U_piso:.2f} W/m²K** | Temperatura estimada abaixo da laje: **{T_vizinho_piso:.1f} °C**.")

    with col_env2:
        # 4. JANELAS
        st.subheader("🪟 4. Janelas (Medidas e Controle Solar)")
        n_grupos_janelas = st.number_input(
            "Quantos tamanhos diferentes de janelas existem na sala?",
            min_value=1, max_value=5, value=1, step=1,
            help="Se todas as janelas tiverem a mesma medida, deixe em 1. Se houver janelas de tamanhos diferentes, aumente para adicionar mais linhas.",
        )
        area_vidro = 0.0
        for i in range(int(n_grupos_janelas)):
            cj1, cj2, cj3 = st.columns(3)
            qtd_j = cj1.number_input(f"Qtd Janelas (Tipo {i+1})", 0, 100, 2 if i == 0 else 1, 1, key=f"qj_{i}")
            larg_j = cj2.number_input(f"Largura (m) (Tipo {i+1})", 0.1, 30.0, 2.0 if i == 0 else 1.0, 0.1, key=f"lj_{i}")
            alt_j = cj3.number_input(f"Altura (m) (Tipo {i+1})", 0.1, 15.0, 2.0 if i == 0 else 1.0, 0.1, key=f"aj_{i}")
            area_vidro += qtd_j * larg_j * alt_j
        st.info(f"📐 **Área Total de Janelas Calculada:** $\\mathbf{{{area_vidro:.2f}\\text{{ m}}^2}}$")

        est_vidro = st.selectbox("Estrutura da Janela de Vidro", ["Vidro Simples (1 folha comum)", "Vidro Duplo Insulado (2 folhas com câmara de ar)"])
        cor_vidro = st.selectbox("Aparência / Película do Vidro", ["Transparente (Incolor comum)", "Escurecido (Fumê, Verde ou Bronze)", "Com Película de Controle Solar / Refletiva (Insulfilm)"])
        esp_vidro_mm = st.select_slider("Espessura aproximada do vidro (mm)", options=[4, 6, 8, 10], value=6)

        prop_vid = calcular_propriedades_vidro_visual(est_vidro, cor_vidro, esp_vidro_mm)
        U_vidro = prop_vid["U"]
        FS_vidro = prop_vid["FS"]
        vidro_sel = f"{est_vidro} - {cor_vidro} ({esp_vidro_mm} mm)"
        st.caption(f"🔬 **Propriedades determinadas automaticamente (ASHRAE):** Transmitância $\\mathbf{{U = {U_vidro:.2f}\\text{{ W/m}}^2\\text{{K}}}}$ | Fator Solar $\\mathbf{{\\text{{FS}} = {FS_vidro:.2f}}}$")

        orient_vidro_sel = st.selectbox("Orientação Solar das Janelas (Para onde apontam?)", list(IRRADIANCIA_SOLAR_ORIENTACAO.keys()))
        somb_sel = st.selectbox("Possui Cortina, Persiana ou Proteção Solar?", list(FATOR_SOMBREAMENTO_JANELA.keys()), index=2)

        st.divider()
        # 5. PORTAS
        st.subheader("🚪 5. Portas (Medidas e Localização)")
        n_grupos_portas = st.number_input("Quantos tamanhos diferentes de portas existem na sala?", 1, 4, 1, 1)
        area_porta = 0.0
        for j in range(int(n_grupos_portas)):
            cp1, cp2, cp3 = st.columns(3)
            qtd_p = cp1.number_input(f"Qtd Portas (Tipo {j+1})", 0, 50, 1, 1, key=f"qp_{j}")
            larg_p = cp2.number_input(f"Largura Porta (m) (Tipo {j+1})", 0.4, 10.0, 0.90, 0.1, key=f"lp_{j}")
            alt_p = cp3.number_input(f"Altura Porta (m) (Tipo {j+1})", 1.0, 6.0, 2.10, 0.1, key=f"ap_{j}")
            area_porta += qtd_p * larg_p * alt_p
        st.info(f"📐 **Área Total de Portas Calculada:** $\\mathbf{{{area_porta:.2f}\\text{{ m}}^2}}$")

        porta_sel = st.selectbox("Material da Porta", list(MATERIAIS_PORTA.keys()))
        U_porta = float(MATERIAIS_PORTA[porta_sel])
        destino_porta = st.selectbox(
            "Para onde esta porta dá saída?",
            [
                "Para um corredor ou sala vizinha SEM ar-condicionado",
                "Diretamente para a rua / ambiente externo ao ar livre",
                "Para outro ambiente que TAMBÉM tem ar-condicionado ligado",
            ],
        )
        if "rua" in destino_porta:
            porta_externa = True
            dT_porta_interna = 0.0
        elif "SEM ar-condicionado" in destino_porta:
            porta_externa = False
            dT_porta_interna = max(0.0, 0.5 * (T_ext - T_int))
            st.caption(f"🌡️ Diferença de temperatura adotada para corredor não climatizado ($0,5 \\times \\Delta T$): **{dT_porta_interna:.1f} °C**.")
        else:
            porta_externa = False
            dT_porta_interna = 0.0
            st.caption("✅ Porta conectada a ambiente climatizado ($\Delta T = 0\text{ °C}$).")

# ------------------------------------------------------------------------------
# ABA 3: OCUPANTES, ILUMINAÇÃO, EQUIPAMENTOS, VENTILAÇÃO, INFILTRAÇÃO E OUTRAS
# ------------------------------------------------------------------------------
with abas[2]:
    col_int1, col_int2 = st.columns(2)
    with col_int1:
        # 6. OCUPANTES
        st.subheader("👥 6. Ocupantes (Pessoas no Ambiente)")
        n_pessoas = st.number_input("Número de pessoas no ambiente", 0, 1000, 16, 1)
        ativ_sel = st.selectbox("O que as pessoas fazem no ambiente? (Atividade Metabólica)", list(ATIVIDADES_OCUPANTES_ASHRAE.keys()), index=1)
        q_sens_pes = float(ATIVIDADES_OCUPANTES_ASHRAE[ativ_sel]["S"])
        q_lat_pes = float(ATIVIDADES_OCUPANTES_ASHRAE[ativ_sel]["L"])
        st.info(
            f"🔥 **Dissipação Metabólica Automática (ASHRAE):** Cada pessoa libera **{q_sens_pes:.0f} W Sensível** + **{q_lat_pes:.0f} W Latente** "
            f"→ **Total = {(n_pessoas * (q_sens_pes + q_lat_pes)):.0f} W**"
        )

        st.divider()
        # 7. ILUMINAÇÃO
        st.subheader("💡 7. Iluminação")
        modo_ilum = st.radio(
            "Como deseja informar as lâmpadas da sala?",
            ["Quantidade de lâmpadas × Potência de cada lâmpada", "Potência elétrica total somada (W)"],
            horizontal=True,
        )
        if "Quantidade" in modo_ilum:
            cil1, cil2 = st.columns(2)
            n_lampadas = cil1.number_input("Quantidade de lâmpadas / luminárias", 0, 500, 20, 1)
            pot_por_lamp = cil2.number_input("Potência de 1 lâmpada (W) [Ex: LED = 18 a 36 W]", 1.0, 500.0, 32.0, 2.0)
            pot_iluminacao = float(n_lampadas * pot_por_lamp)
        else:
            pot_iluminacao = st.number_input("Potência total instalada de iluminação (W)", 0.0, 50000.0, 640.0, 20.0)

        tipo_lampada = st.selectbox("Tecnologia das Lâmpadas", ["Lâmpadas LED (Dissipação direta = 1,00)", "Lâmpadas Fluorescentes com reator eletrônico (Fator = 1,20)"])
        fator_dissip_ilum = 1.00 if "LED" in tipo_lampada else 1.20

        perfil_uso_luz = st.selectbox("Quantas lâmpadas ficam acesas no horário de pico?", ["Todas acesas (100%)", "Maioria acesa (80%)", "Apenas metade acesa (50%)"])
        fator_uso_ilum = 1.00 if "100%" in perfil_uso_luz else (0.80 if "80%" in perfil_uso_luz else 0.50)

        st.divider()
        # 8. EQUIPAMENTOS INTERNOS
        st.subheader("💻 8. Equipamentos e Aparelhos Elétricos")
        st.caption("Informe a **quantidade** de cada aparelho presente na sala (o programa multiplica e soma automaticamente):")
        ceq1, ceq2 = st.columns(2)
        n_computadores = ceq1.number_input("Nº de Computadores / Notebooks", 0, 500, 16, 1)
        pot_por_computador = ceq2.selectbox("Tipo de Computador", [120.0, 65.0, 250.0], format_func=lambda x: f"Desktop comum + Monitor ({int(x)} W)" if x == 120 else (f"Notebook econômico ({int(x)} W)" if x == 65 else f"Workstation / PC Gamer ({int(x)} W)"))

        ceq3, ceq4 = st.columns(2)
        qtd_proj_tv = ceq3.number_input("Nº de Projetores / TVs grandes (200 W cada)", 0, 50, 1, 1)
        qtd_impr_cafe = ceq4.number_input("Nº de Impressoras / Bebedouros / Frigobar (100 W médios)", 0, 50, 1, 1)

        pot_motores = st.number_input("Potência de Motores ou Máquinas Especiais de Laboratório (W)", 0.0, 50000.0, 0.0, 50.0)
        pot_equip_outros = float((qtd_proj_tv * 200.0) + (qtd_impr_cafe * 100.0))

        simult_sel = st.selectbox(
            "Como esses aparelhos funcionam ao longo do dia?",
            [
                "Uso normal de escritório/aula (85% ligados ao mesmo tempo)",
                "Todos ligados em potência máxima ao mesmo tempo (100%)",
                "Uso intermitente / alternado (60% ligados ao mesmo tempo)",
            ],
        )
        fator_simult_equip = 0.85 if "85%" in simult_sel else (1.00 if "100%" in simult_sel else 0.60)

    with col_int2:
        # 9. VENTILAÇÃO HIGIÊNICA
        st.subheader("🌬️ 9. Ventilação (Renovação de Ar - NBR 16401-3)")
        amb_vent_sel = st.selectbox("Qual é o tipo de uso deste ambiente? (Define a vazão da norma)", list(AMBIENTES_VENTILACAO_NBR16401.keys()))
        vazao_pessoa_ls = float(AMBIENTES_VENTILACAO_NBR16401[amb_vent_sel]["Fp"])
        vazao_area_ls_m2 = float(AMBIENTES_VENTILACAO_NBR16401[amb_vent_sel]["Fa"])
        vazao_total_calc = (n_pessoas * vazao_pessoa_ls) + (comprimento * largura * vazao_area_ls_m2)
        st.info(
            f"🌬️ **Vazão Normativa Automática (NBR 16401-3):** {vazao_pessoa_ls:.1f} L/s por pessoa + {vazao_area_ls_m2:.2f} L/s por m² "
            f"→ **Vazão Total = {vazao_total_calc:.1f} L/s**"
        )

        st.divider()
        # 10. INFILTRAÇÃO
        st.subheader("🍃 10. Infiltração de Ar por Frestas e Portas")
        nivel_inf_sel = st.selectbox("Como é a vedação das janelas e o abre-e-fecha de portas da sala?", list(NIVEIS_INFILTRACAO_ACH.keys()), index=1)
        ach_infiltracao = float(NIVEIS_INFILTRACAO_ACH[nivel_inf_sel])
        st.caption(f"🍃 Taxa de renovação involuntária adotada: **{ach_infiltracao:.2f} trocas de ar por hora (ACH)**.")

        st.divider()
        # 11. OUTRAS CARGAS
        st.subheader("➕ 11. Outras Cargas Térmicas Justificadas")
        incluir_ventilador = st.checkbox("Incluir dissipação de calor do motor do ventilador interno do ar-condicionado (150 W)?", value=True)
        incluir_cafeteira_vapor = st.checkbox("Existe cafeteira elétrica / chaleira / geração de vapor interna (100 W Latente)?", value=False)
        outras_cargas_sens = 150.0 if incluir_ventilador else 0.0
        outras_cargas_lat = 100.0 if incluir_cafeteira_vapor else 0.0
        justificativa_outras = st.text_input("Observações Técnicas do Projetista", "Considerada dissipação eletromecânica do ventilador da unidade evaporadora.")

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

    btu_regra_bolso = res["area_piso"] * 600.0
    desvio_regra = ((btu_regra_bolso - res["unidades_total"]["BTU_h"]) / res["unidades_total"]["BTU_h"] * 100.0) if res["unidades_total"]["BTU_h"] > 0 else 0.0
    st.info(
        f"⚖️ **Discussão Crítica (Modelo Físico vs. Regra Empírica de 600 BTU/h·m²):** "
        f"Uma calculadora superficial de área estimaria **{btu_regra_bolso:,.0f} BTU/h**, enquanto a modelagem física real resultou em "
        f"**{res['unidades_total']['BTU_h']:,.0f} BTU/h** (densidade efetiva de **{res['densidade_BTUh_m2']:.0f} BTU/h·m²**). "
        f"A regra empírica apresenta desvio de **{desvio_regra:+.1f}%** por ignorar psicrometria, orientação solar, Fator Solar dos vidros e metabolismo."
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
        "Avalia a sensação térmica real das pessoas dentro da sala pelo método de **Fanger (PMV e PPD)**. "
        "A temperatura, a umidade e a atividade das pessoas já são trazidas automaticamente das abas anteriores."
    )

    cc1, cc2 = st.columns(2)
    with cc1:
        T_ar_conf = st.number_input("Temperatura do Ar Interno da Sala (°C)", 15.0, 35.0, float(T_int), 0.5)
        UR_conf = st.number_input("Umidade Relativa Interna da Sala (%)", 15.0, 95.0, float(UR_int), 1.0)
        efeito_radiante_sel = st.selectbox(
            "Como são as paredes e janelas ao redor das pessoas? (Define a Temperatura Radiante Média)",
            [
                "Sala comum com janelas protegidas por cortina/persiana (+1,0 °C sobre o ar)",
                "Sala muito bem isolada ou distante de paredes/janelas externas (Igual à temperatura do ar)",
                "Pessoas sentadas perto de janelas pegando sol ou sob telhado quente (+3,5 °C sobre o ar)",
            ],
        )
        acrescimo_trm = 1.0
