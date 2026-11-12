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
        nome_projeto = st.text_input("Nome do Projeto / Edificação", "Sala Teste")
        equipe_autores = st.text_input("Identificação da Equipe / Autores", "Equipe - Felipe Deina de Farias (GRR20202697); Guilherme de Souza (GRR20202692); Lucca Binotto (GRR20224221)")
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
            st.info(f"🔬 **Transmitância Calculada pelas Camadas:** R_total = {res_u_par['R_total']:.2f} m²K/W → **U = {U_parede:.2f} W/m²K**")
        else:
            mat_parede_sel = st.selectbox("Composição Construtiva da Parede (NBR 15220)", list(MATERIAIS_PAREDE_NBR15220.keys()))
            U_parede = float(MATERIAIS_PAREDE_NBR15220[mat_parede_sel])
            st.info(f"🔬 **Transmitância Normativa Adotada:** **U = {U_parede:.2f} W/m²K**")

        orient_parede_sel = st.selectbox("Orientação Solar Predominante da Parede Externa", list(IRRADIANCIA_SOLAR_ORIENTACAO.keys()))
        cor_parede_sel = st.selectbox("Cor Externa da Parede (Absortância Solar)", list(ABSORTANCIA_COR_SUPERFICIE.keys()))

        st.divider()
        st.subheader("🏠 2. Cobertura ou Teto")
        tipo_cobertura = st.selectbox(
            "O que existe acima do teto desta sala?",
            ["Exposta ao sol", "Sob pavimento não climatizado", "Sob pavimento climatizado (ΔT = 0)"],
        )
        if tipo_cobertura == "Sob pavimento climatizado (ΔT = 0)":
            U_cobertura = 2.05
            cor_cob_sel = list(ABSORTANCIA_COR_SUPERFICIE.keys())[1]
            dT_entre_forro = 0.0
            st.success("✅ Como o andar de cima também é climatizado na mesma temperatura, não há ganho de calor pelo teto (Q_cob = 0 W).")
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
                st.info(f"🔬 **Transmitância Calculada da Cobertura:** R_total = {res_u_cob['R_total']:.2f} m²K/W → **U = {U_cobertura:.2f} W/m²K**")
            else:
                mat_cob_sel = st.selectbox("Composição da Cobertura (NBR 15220)", list(MATERIAIS_COBERTURA_NBR15220.keys()))
                U_cobertura = float(MATERIAIS_COBERTURA_NBR15220[mat_cob_sel])
                st.info(f"🔬 **Transmitância Normativa da Cobertura:** **U = {U_cobertura:.2f} W/m²K**")

            if tipo_cobertura == "Exposta ao sol":
                cor_cob_sel = st.selectbox("Cor Externa do Telhado / Cobertura", list(ABSORTANCIA_COR_SUPERFICIE.keys()), index=1)
                dT_entre_forro = 0.0
            else:
                cor_cob_sel = list(ABSORTANCIA_COR_SUPERFICIE.keys())[1]
                dT_entre_forro = max(0.0, 0.5 * (T_ext - T_int))
                st.caption(f"🌡️ Diferença de temperatura estimada para o pavimento superior não climatizado: **{dT_entre_forro:.1f} °C**.")

        st.divider()
        st.subheader("⬛ 3. Pisos")
        condicao_piso = st.selectbox(
            "O que existe embaixo do piso desta sala?",
            ["Sobre espaço climatizado (ΔT = 0)", "Sobre espaço não climatizado (garagem/pilotis)", "Em contato direto com o solo"],
        )
        if condicao_piso == "Sobre espaço climatizado (ΔT = 0)":
            mat_piso_sel = list(MATERIAIS_PISO.keys())[0]
            U_piso = float(MATERIAIS_PISO[mat_piso_sel])
            T_vizinho_piso = T_int
            st.success("✅ Sem transferência de calor pelo piso (Q_piso = 0 W).")
        else:
            mat_piso_sel = st.selectbox("Tipo de Laje de Piso", list(MATERIAIS_PISO.keys()))
            U_piso = float(MATERIAIS_PISO[mat_piso_sel])
            T_vizinho_piso = T_ext - 3.0 if "garagem" in condicao_piso else 25.0
            st.caption(f"🔬 Transmitância do piso: **{U_piso:.2f} W/m²K** | Temperatura estimada abaixo da laje: **{T_vizinho_piso:.1f} °C**.")

    with col_env2:
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
        st.info(f"📐 **Área Total de Janelas Calculada:** **{area_vidro:.2f} m²**")

        est_vidro = st.selectbox("Estrutura da Janela de Vidro", ["Vidro Simples (1 folha comum)", "Vidro Duplo Insulado (2 folhas com câmara de ar)"])
        cor_vidro = st.selectbox("Aparência / Película do Vidro", ["Transparente (Incolor comum)", "Escurecido (Fumê, Verde ou Bronze)", "Com Película de Controle Solar / Refletiva (Insulfilm)"])
        esp_vidro_mm = st.select_slider("Espessura aproximada do vidro (mm)", options=[4, 6, 8, 10], value=6)

        prop_vid = calcular_propriedades_vidro_visual(est_vidro, cor_vidro, esp_vidro_mm)
        U_vidro = prop_vid["U"]
        FS_vidro = prop_vid["FS"]
        vidro_sel = f"{est_vidro} - {cor_vidro} ({esp_vidro_mm} mm)"
        st.caption(f"🔬 **Propriedades automáticas (ASHRAE):** Transmitância **U = {U_vidro:.2f} W/m²K** | Fator Solar **FS = {FS_vidro:.2f}**")

        orient_vidro_sel = st.selectbox("Orientação Solar das Janelas (Para onde apontam?)", list(IRRADIANCIA_SOLAR_ORIENTACAO.keys()))
        somb_sel = st.selectbox("Possui Cortina, Persiana ou Proteção Solar?", list(FATOR_SOMBREAMENTO_JANELA.keys()), index=2)

        st.divider()
        st.subheader("🚪 5. Portas (Medidas e Localização)")
        n_grupos_portas = st.number_input("Quantos tamanhos diferentes de portas existem na sala?", 1, 4, 1, 1)
        area_porta = 0.0
        for j in range(int(n_grupos_portas)):
            cp1, cp2, cp3 = st.columns(3)
            qtd_p = cp1.number_input(f"Qtd Portas (Tipo {j+1})", 0, 50, 1, 1, key=f"qp_{j}")
            larg_p = cp2.number_input(f"Largura Porta (m) (Tipo {j+1})", 0.4, 10.0, 0.90, 0.1, key=f"lp_{j}")
            alt_p = cp3.number_input(f"Altura Porta (m) (Tipo {j+1})", 1.0, 6.0, 2.10, 0.1, key=f"ap_{j}")
            area_porta += qtd_p * larg_p * alt_p
        st.info(f"📐 **Área Total de Portas Calculada:** **{area_porta:.2f} m²**")

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
            st.caption(f"🌡️ Diferença de temperatura adotada para corredor não climatizado (0,5 × ΔT): **{dT_porta_interna:.1f} °C**.")
        else:
            porta_externa = False
            dT_porta_interna = 0.0
            st.caption("✅ Porta conectada a ambiente climatizado (ΔT = 0 °C).")

# ------------------------------------------------------------------------------
# ABA 3: OCUPANTES, ILUMINAÇÃO, EQUIPAMENTOS, VENTILAÇÃO, INFILTRAÇÃO E OUTRAS
# ------------------------------------------------------------------------------
with abas[2]:
    col_int1, col_int2 = st.columns(2)
    with col_int1:
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
        st.subheader("🍃 10. Infiltração de Ar por Frestas e Portas")
        nivel_inf_sel = st.selectbox("Como é a vedação das janelas e o abre-e-fecha de portas da sala?", list(NIVEIS_INFILTRACAO_ACH.keys()), index=1)
        ach_infiltracao = float(NIVEIS_INFILTRACAO_ACH[nivel_inf_sel])
        st.caption(f"🍃 Taxa de renovação involuntária adotada: **{ach_infiltracao:.2f} trocas de ar por hora (ACH)**.")

        st.divider()
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
        acrescimo_trm = 1.0 if "+1,0" in efeito_radiante_sel else (0.0 if "Igual" in efeito_radiante_sel else 3.5)
        T_rm_conf = T_ar_conf + acrescimo_trm

    with cc2:
        vento_sel = st.selectbox(
            "Movimentação do ar sobre as pessoas (Velocidade do ar):",
            [
                "Brisa leve normal de ar-condicionado central/Split (0,15 m/s)",
                "Ar praticamente parado / Sem corrente de ar perceptível (0,08 m/s)",
                "Vento perceptível de difusor próximo ou ventilador de apoio (0,35 m/s)",
            ],
        )
        v_ar_conf = 0.15 if "0,15" in vento_sel else (0.08 if "0,08" in vento_sel else 0.35)

        vestimenta_opcoes = {
            "Roupas leves de verão: calça leve e camisa de manga curta (0,50 clo)": 0.50,
            "Traje de escritório/aula: calça social, camisa manga longa ou jaleco (0,75 clo)": 0.75,
            "Traje formal completo / terno ou agasalho de inverno (1,00 clo)": 1.00,
        }
        vest_sel = st.selectbox("Que tipo de roupa as pessoas estão vestindo?", list(vestimenta_opcoes.keys()), index=0)
        clo_conf = float(vestimenta_opcoes[vest_sel])
        met_conf = float(ATIVIDADES_OCUPANTES_ASHRAE[ativ_sel]["met"])
        st.info(
            f"📌 **Parâmetros Físicos Adotados (ISO 7730):** Temperatura Radiante Média T_rm = {T_rm_conf:.1f} °C | "
            f"Atividade M = {met_conf:.1f} met (trazida da Aba 3) | Vestimenta I_cl = {clo_conf:.2f} clo"
        )

    res_conf = calcular_conforto_pmv_ppd(T_ar_conf, T_rm_conf, v_ar_conf, UR_conf, met_conf, clo_conf)

    for av in res_conf["avisos_validade"]:
        st.warning(f"⚠️ **Limite de Validade ISO 7730:** {av}")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Índice PMV (Sensação)", f"{res_conf['PMV']:+.2f}", res_conf["sensacao"])
    k2.metric("Índice PPD (Pessoas Insatisfeitas)", f"{res_conf['PPD']:.1f}%", "Meta da Norma <= 10%")
    k3.metric("Temperatura Operativa Sentida (T_op)", f"{res_conf['T_op']:.1f} °C")
    k4.metric("Temp. Externa da Roupa (T_cl)", f"{res_conf['T_cl']:.1f} °C")

    if -0.5 <= res_conf["PMV"] <= 0.5:
        st.success(f"✅ **Diagnóstico Normativo:** {res_conf['status']}")
    else:
        st.error(f"❌ **Diagnóstico Normativo:** {res_conf['status']}")

    pmv_eixo = [x / 10.0 for x in range(-30, 31)]
    ppd_eixo = [100.0 - 95.0 * (2.718281828 ** (-0.03353 * (p ** 4) - 0.2179 * (p ** 2))) for p in pmv_eixo]
    fig_fanger = go.Figure()
    fig_fanger.add_trace(go.Scatter(x=pmv_eixo, y=ppd_eixo, mode="lines", name="Curva Teórica de Fanger", line=dict(color="#1D3557", width=3)))
    fig_fanger.add_vrect(x0=-0.5, x1=0.5, fillcolor="seagreen", opacity=0.2, line_width=0, annotation_text="Zona Conforto (-0,5 a +0,5)")
    fig_fanger.add_trace(go.Scatter(
        x=[res_conf["PMV"]],
        y=[res_conf["PPD"]],
        mode="markers+text",
        text=[f"Sala Atual (PMV={res_conf['PMV']:+.2f}, PPD={res_conf['PPD']:.1f}%)"],
        textposition="top center",
        marker=dict(size=14, color="#E63946"),
        name="Condição do Ambiente",
    ))
    fig_fanger.update_layout(
        title="Curva Clássica de Fanger: PMV vs. PPD (ABNT NBR ISO 7730)",
        xaxis_title="PMV (Escala: -3 Muito Frio | 0 Neutro Confortável | +3 Muito Quente)",
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

    c_conv = converter_unidades_potencia(3516.85284)
    p_teste = calcular_propriedades_psicrometricas(30.0, 50.0, 0.0)
    q_ilum_1 = calcular_carga_iluminacao(500.0, 1.0, 1.0)
    q_ilum_2 = calcular_carga_iluminacao(1000.0, 1.0, 1.0)
    u_cam_teste = calcular_U_parede_camadas(0.45, 14.0, 3.0, 0.0, 0.0)

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
            "Caso de Teste / Validação": "6. Associação de Resistências Térmicas em Série (NBR 15220: Tijolo 14 cm + Reboco 3 cm)",
            "Valor Esperado (Referência)": "R_tot = 0,507 m²K/W | U = 1,97 W/m²K",
            "Valor Calculado pelo Código": f"R_tot = {u_cam_teste['R_total']:.3f} m²K/W | U = {u_cam_teste['U']:.2f} W/m²K",
            "Status": "✅ APROVADO" if abs(u_cam_teste["U"] - 1.97) < 0.02 else "❌ FALHOU",
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
<p>Modelo físico estacionário baseado em balanço de primeira lei da termodinâmica, resistência térmica por camadas em série (ABNT NBR 15220-2), conceito de Temperatura Sol-Ar para superfícies opacas (ASHRAE Cap. 18), psicrometria analítica (ASHRAE Cap. 1) e modelo de conforto de Fanger (ABNT NBR ISO 7730). Observação adicional: {justificativa_outras}</p>
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
# ABA 8: SOBRE O MÉTODO, RESPOSTAS DA SEÇÃO 13 E USO CRÍTICO DE IA
# ------------------------------------------------------------------------------
with abas[7]:
    st.subheader("📘 Fundamentação Teórica e Sobre o Método")
    st.markdown("""
    * **Regime Permanente Estacionário e Associação de Camadas (NBR 15220-2):** A transmitância térmica ($U$) de paredes e coberturas é obtida pelo inverso da resistência térmica total ($R_{tot} = R_{si} + \\sum (e_i / k_i) + R_{ar} + R_{se}$).
    * **Temperatura Sol-Ar ($T_{sol-ar}$):** Incorpora a radiação solar incidente absorvida pela superfície opaca externa:
      $$T_{sol-ar} = T_{ext} + \\frac{\\alpha \\cdot I_{solar}}{h_{ext}} \\implies \\dot{Q}_{opaco} = U \\cdot A \\cdot (T_{sol-ar} - T_{int})$$
    * **Fenestração (Vidros):** Divide o ganho térmico em condução ($U_v A_v \\Delta T$) e radiação solar transmitida ($A_v \\cdot \\text{FS} \\cdot I_{sol} \\cdot F_{somb}$).
    * **Psicrometria Analítica:** Corrige a pressão barométrica pela altitude ($Z$), determina a pressão de saturação de vapor por Tetens/ASHRAE, razão de mistura ($\\omega$), ponto de orvalho ($T_{po}$), bulbo úmido ($T_{bu}$) por bisseção termodinâmica exata, entalpia específica ($h$) e volume específico ($v$).
    """)

    st.divider()
    st.subheader("🎓 Respostas às 10 Questões para Discussão (Seção 13 do Trabalho)")
    with st.expander("Clique para expandir as 10 Respostas Técnicas Fundamentadas no Aplicativo", expanded=True):
        st.markdown("""
        **1. Qual parcela teve maior influência na carga térmica calculada?**
        No cenário com cobertura exposta ao sol, a parcela dominante é a **condução pela cobertura/teto** (devido à grande área horizontal sob irradiância de $820\\text{ W/m}^2$ e elevada Temperatura Sol-Ar), seguida pela **radiação solar nas janelas a Oeste** e pelas **cargas internas (ocupantes + computadores)**. Já em pavimentos intermediários (sob andar climatizado), a radiação solar nos vidros e a dissipação interna assumem a liderança.

        **2. Quais hipóteses possuem maior impacto sobre o resultado?**
        A hipótese de **Regime Permanente Estacionário (ausência de amortecimento e atraso térmico por inércia das paredes/lajes)** e a hipótese de **simultaneidade máxima de pico** (considerar clima externo de $1\\%$ da NBR 16401, pico solar e ocupação máxima ocorrendo exatamente no mesmo instante).

        **3. Qual entrada apresenta maior incerteza?**
        A **Taxa de Infiltração de Ar Externo ($\\text{ACH}$)**, pois depende da estanqueidade real de frestas, pressão de vento e frequência de abertura de portas, seguida pelo **Fator de Simultaneidade de equipamentos**.

        **4. Como a equipe validou o programa?**
        Em 4 etapas (ver Aba 6 e `test_calculos.py`): (i) comparação algébrica com cálculo manual (erro $0,00\\%$); (ii) testes unitários automatizados via `pytest` cobrindo conversões ($1\\text{ TR} = 3.516,85\\text{ W} = 12.000\\text{ BTU/h}$); (iii) testes de casos-limite nulos ($A=0, \\Delta T=0, P=0 \\implies \\dot{Q}=0$) e invariantes psicrométricas ($T_{po} \\le T_{bu} \\le T_{bs}$); e (iv) análise paramétrica de sensibilidade e verificação de ordem de grandeza ($\\text{W/m}^2$).

        **5. A Inteligência Artificial produziu algum erro técnico durante o desenvolvimento? Explique.**
        Sim. Na versão preliminar (v1.0), a IA adotou massa específica do ar constante ($\\rho = 1,20\\text{ kg/m}^3$ ao nível do mar), o que gerava erro de até $12\\%$ a $15\\%$ na vazão mássica em cidades de maior altitude como Curitiba ($908\\text{ m}$) e Brasília ($1.159\\text{ m}$). Além disso, omitia parcelas de piso/portas/infiltração e exigia parâmetros brutos difíceis para o usuário ($\\omega$ em $\\text{g/kg}$, $U$ manual e $\\text{ACH}$ bruto). Tudo foi auditado e corrigido pela equipe.

        **6. Qual modificação na edificação seria mais eficiente para reduzir a carga térmica?**
        Isolamento térmico com pintura reflexiva clara ($\\alpha = 0,30$) na cobertura (reduzindo a carga de teto em mais de $75\\%$) combinado com vidro de controle solar (baixo $\\text{FS}$) e sombreamento externo nas janelas, conforme demonstrado no gráfico de *Retrofit* da Aba 4.

        **7. Como a orientação das superfícies transparentes influencia os resultados?**
        Altera diretamente a irradiância solar incidente ($I_{sol}$): enquanto uma fachada Sul recebe cerca de $220\\text{ W/m}^2$ (radiação difusa), a fachada Oeste recebe $680\\text{ W/m}^2$ à tarde, mais que triplicando o ganho solar transmitido ($\\dot{Q}_{vid,sol} = A_v \\cdot \\text{FS} \\cdot I_{sol} \\cdot F_{somb}$) para a mesma área de janela.

        **8. Qual é a diferença entre carga térmica sensível, latente e total?**
        A **carga sensível ($\\dot{Q}_S = \\dot{m} c_p \\Delta T$)** provoca variação da Temperatura de Bulbo Seco ($T_{bs}$); a **carga latente ($\\dot{Q}_L = \\dot{m} h_{lv} \\Delta \\omega$)** está associada à adição de vapor d'água (respiração/suor e umidade externa) que precisa ser condensado na serpentina; e a **carga total ($\\dot{Q}_{tot} = \\dot{Q}_S + \\dot{Q}_L = \\dot{m} \\Delta h$)** é a variação da entalpia total.

        **9. Por que a carga térmica não deve ser estimada exclusivamente por área do ambiente?**
        Porque regras empíricas como $600\\text{ BTU/h}\\cdot\\text{m}^2$ ignoram orientação solar, tipo de vidro, isolamento de cobertura, altitude psicrométrica, taxa de ocupação e separação entre calor sensível e latente ($\\text{FCS}$), levando a graves erros de sub ou superdimensionamento.

        **10. Qual é a principal limitação da metodologia implementada?**
        O cálculo em **regime permanente estacionário**, que não modela o amortecimento e o atraso térmico transiente da massa térmica das paredes e lajes ao longo das 24 horas (como fariam os métodos horários dinâmicos RTS ou Balanço de Calor da ASHRAE).
        """)

    st.divider()
    st.subheader("🤖 Registro de Auditoria e Uso Crítico de Inteligência Artificial (Rubrica Seção 9)")
    st.markdown("""
    | Etapa / Iteração | Prompt / Solicitação Realizada | Falha ou Limitação Identificada na Resposta da IA | Correção Técnica e Aprendizado de Engenharia Aplicado |
    | :--- | :--- | :--- | :--- |
    | **1. Protótipo Inicial (v1.0)** | Geração de estrutura inicial em Python + Streamlit para cálculo de carga térmica. | Código monolítico em arquivo único, omissão de Pisos, Portas e Infiltração, e exigência de umidade absoluta ($\\text{g/kg}$) manual. | Separação modular (`calculos.py`, `app.py`, `test_calculos.py`), inclusão das 11 parcelas e cálculo psicrométrico a partir de $\\text{UR}$ e Altitude. |
    | **2. Psicrometria e Altitude (Seção 4)** | Implementação das 7 propriedades psicrométricas analíticas. | Uso de densidade fixa ($\\rho = 1,20\\text{ kg/m}^3$), gerando erro em cidades altas (Curitiba/Brasília). | Substituição pela equação barométrica da ASHRAE e volume específico real ($\\dot{m}_{ar} = \\dot{V}/v_{ext}$). |
    | **3. Validação e Bônus ISO 7730 (Seções 7 a 12)** | Inclusão de `pytest`, `iniciar.bat` e modelo de Fanger (PMV/PPD). | Necessidade de garantir invariantes ($T_{po} \\le T_{bu} \\le T_{bs}$) e funcionamento do `.bat` como Administrador no Windows. | Solução por bisseção para $T_{bu}$, comando `cd /d "%~dp0"` no `iniciar.bat` e bateria de testes automatizados. |
    | **4. Revisão Crítica de Usabilidade e Camadas (NBR 15220)** | Inspeção visual das telas pela equipe identificando campos pouco intuitivos para usuários reais. | O programa pedia áreas prontas em $\\text{m}^2$ e coeficientes técnicos manuais ($U$, $\\text{FS}$, $\\text{ACH}$, $\\text{L/s}$, $T_{rm}$, $\\text{met}$ e campo duplicado de $\\text{clo}$). | Implementou-se cálculo de áreas por dimensões e múltiplos tamanhos de janelas/portas, cálculo físico de $U = 1/R_{tot}$ pela espessura em $\\text{cm}$ das camadas (NBR 15220-2) e seletores normativos automáticos. |
    """)

# === FIM DO ARQUIVO app.py ===
