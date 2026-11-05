"""
Módulo de Engenharia: Modelagem Termodinâmica, Psicrometria, Carga Térmica e Conforto.
Referências Técnicas:
- ABNT NBR 16401-1, 16401-2 e 16401-3 (Instalações de ar-condicionado)
- ABNT NBR 15220-2 (Desempenho térmico de edificações - Transmitância e Capacidade Térmica)
- ASHRAE Handbook - Fundamentals (Cap. 1 Psychrometrics / Cap. 18 Nonresidential Cooling Loads)
- ABNT NBR ISO 7730 / ASHRAE Standard 55 (Ambientes térmicos moderados - PMV e PPD)
"""

import math
from typing import Dict, Any, List

# ==============================================================================
# 1. BANCOS DE DADOS NORMATIVOS RASTREÁVEIS
# ==============================================================================

CIDADES_CLIMA_NBR16401: Dict[str, Dict[str, Any]] = {
    "Curitiba - PR (NBR 16401-1: 1%)": {"T_bs": 30.8, "UR": 52.0, "altitude": 908.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "São Paulo - SP (NBR 16401-1: 1%)": {"T_bs": 31.6, "UR": 50.0, "altitude": 760.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Rio de Janeiro - RJ (NBR 16401-1: 1%)": {"T_bs": 36.2, "UR": 54.0, "altitude": 5.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Brasília - DF (NBR 16401-1: 1%)": {"T_bs": 31.2, "UR": 38.0, "altitude": 1159.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Belo Horizonte - MG (NBR 16401-1: 1%)": {"T_bs": 32.0, "UR": 46.0, "altitude": 852.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Porto Alegre - RS (NBR 16401-1: 1%)": {"T_bs": 34.4, "UR": 49.0, "altitude": 10.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Manaus - AM (NBR 16401-1: 1%)": {"T_bs": 35.1, "UR": 64.0, "altitude": 72.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Fortaleza - CE (NBR 16401-1: 1%)": {"T_bs": 32.5, "UR": 62.0, "altitude": 25.0, "fonte": "ABNT NBR 16401-1 (Anexo A - 1% Verão)"},
    "Personalizado (Entrada livre do usuário)": {"T_bs": 34.0, "UR": 55.0, "altitude": 500.0, "fonte": "Definido manualmente pelo projetista"},
}

MATERIAIS_PAREDE_NBR15220: Dict[str, float] = {
    "Alvenaria tijolo cerâmico 6 furos (15 cm) rebocada (U = 2,40 W/m²K)": 2.40,
    "Alvenaria bloco de concreto (19 cm) rebocada (U = 2,85 W/m²K)": 2.85,
    "Parede dupla de tijolo maciço com câmara de ar (U = 1,55 W/m²K)": 1.55,
    "Divisória Drywall com lã de vidro 50 mm (U = 0,75 W/m²K)": 0.75,
    "Painel pré-moldado de concreto maciço 12 cm (U = 3,60 W/m²K)": 3.60,
}

MATERIAIS_COBERTURA_NBR15220: Dict[str, float] = {
    "Laje concreto 10 cm + telha fibrocimento sem forro (U = 2,05 W/m²K)": 2.05,
    "Laje concreto 10 cm + telha cerâmica ventilada (U = 1,75 W/m²K)": 1.75,
    "Telhado com forro de gesso/mineral e lã de vidro 50 mm (U = 0,85 W/m²K)": 0.85,
    "Telha termoacústica sanduíche PIR/PUR 30 mm (U = 0,65 W/m²K)": 0.65,
}

MATERIAIS_PISO: Dict[str, float] = {
    "Laje de concreto 12 cm com revestimento cerâmico (U = 2,65 W/m²K)": 2.65,
    "Laje de concreto com piso vinílico/madeira (U = 2,10 W/m²K)": 2.10,
    "Laje isolada termicamente sobre pilotis/garagem (U = 1,10 W/m²K)": 1.10,
}

MATERIAIS_PORTA: Dict[str, float] = {
    "Porta de madeira compensada oca 35 mm (U = 2,90 W/m²K)": 2.90,
    "Porta de madeira maciça 40 mm (U = 2,20 W/m²K)": 2,
    "Porta de alumínio/metálica sem isolamento (U = 5,20 W/m²K)": 5.20,
    "Porta corta-fogo / isolada acusticamente (U = 1,40 W/m²K)": 1.40,
}
MATERIAIS_PORTA["Porta de madeira maciça 40 mm (U = 2,20 W/m²K)"] = 2.20

TIPOS_VIDRO_ASHRAE: Dict[str, Dict[str, float]] = {
    "Vidro Simples Incolor 6 mm (U = 5,70 W/m²K | FS = 0,82)": {"U": 5.70, "FS": 0.82},
    "Vidro Simples Verde/Fumê 6 mm (U = 5,70 W/m²K | FS = 0,62)": {"U": 5.70, "FS": 0.62},
    "Vidro Laminado de Controle Solar (U = 5,10 W/m²K | FS = 0,45)": {"U": 5.10, "FS": 0.45},
    "Vidro Duplo Insulado Low-E (U = 2,60 W/m²K | FS = 0,32)": {"U": 2.60, "FS": 0.32},
}

FATOR_SOMBREAMENTO_JANELA: Dict[str, float] = {
    "Sem proteção solar interna ou externa (Fator = 1,00)": 1.00,
    "Cortina ou persiana interna escura (Fator = 0,75)": 0.75,
    "Cortina ou persiana interna clara (Fator = 0,58)": 0.58,
    "Brise-soleil ou beiral externo sombreado (Fator = 0,35)": 0.35,
}

IRRADIANCIA_SOLAR_ORIENTACAO: Dict[str, float] = {
    "Oeste (Pico vespertino - 680 W/m²)": 680.0,
    "Noroeste / Nordeste (Alta insolação - 600 W/m²)": 600.0,
    "Norte (Insolação direta Hemisfério Sul - 540 W/m²)": 540.0,
    "Leste (Pico matinal - 520 W/m²)": 520.0,
    "Sul (Predominância de radiação difusa - 220 W/m²)": 220.0,
    "Horizontal / Cobertura exposta ao sol (820 W/m²)": 820.0,
}

ABSORTANCIA_COR_SUPERFICIE: Dict[str, float] = {
    "Cor Clara / Pintura Branca (α = 0,30)": 0.30,
    "Cor Média / Concreto Aparente / Cerâmica (α = 0,60)": 0.60,
    "Cor Escura / Fibrocimento / Cinza Escuro (α = 0,85)": 0.85,
}

ATIVIDADES_OCUPANTES_ASHRAE: Dict[str, Dict[str, float]] = {
    "Sentado em repouso / Teatro / Auditório (70 W Sensível | 35 W Latente | 1,0 met)": {"S": 70.0, "L": 35.0, "met": 1.0},
    "Trabalho de escritório / Sala de aula (75 W Sensível | 55 W Latente | 1,2 met)": {"S": 75.0, "L": 55.0, "met": 1.2},
    "Laboratório / Comércio em pé (90 W Sensível | 95 W Latente | 1,6 met)": {"S": 90.0, "L": 95.0, "met": 1.6},
    "Trabalho industrial leve / Academia moderada (150 W Sensível | 270 W Latente | 2,4 met)": {"S": 150.0, "L": 270.0, "met": 2.4},
}


# ==============================================================================
# 2. MÓDULO PSICROMÉTRICO ANALÍTICO (ASHRAE FUNDAMENTALS CAP. 1)
# ==============================================================================

def calcular_pressao_atmosferica(altitude_m: float) -> float:
    """Calcula a pressão barométrica padrão (kPa) em função da altitude Z (m)."""
    altitude_segura = max(-500.0, min(5000.0, float(altitude_m)))
    return 101.325 * ((1.0 - 2.25577e-5 * altitude_segura) ** 5.2559)


def calcular_pressao_saturacao_vapor(T_bs_c: float) -> float:
    """Calcula a pressão de saturação do vapor d'água P_vs (kPa) pela equação de Tetens/ASHRAE."""
    T = float(T_bs_c)
    if T >= 0.0:
        return 0.61078 * math.exp((17.27 * T) / (T + 237.3))
    else:
        return 0.61078 * math.exp((21.875 * T) / (T + 265.5))


def calcular_propriedades_psicrometricas(T_bs: float, UR: float, altitude_m: float = 0.0) -> Dict[str, float]:
    """
    Calcula as 7 propriedades psicrométricas fundamentais do ar úmido:
    T_bs (°C), UR (%), w (kg/kg e g/kg), T_po (°C), T_bu (°C), h (kJ/kg_as), v (m³/kg_as) e P_atm (kPa).
    """
    if not (0.1 <= UR <= 100.0):
        raise ValueError("A umidade relativa (UR) deve estar entre 0,1% e 100,0%.")

    P_atm = calcular_pressao_atmosferica(altitude_m)
    P_vs = calcular_pressao_saturacao_vapor(T_bs)
    P_v = (UR / 100.0) * P_vs

    # Proteção contra P_v >= P_atm em temperaturas extremas
    P_v = min(P_v, 0.95 * P_atm)

    # 1. Razão de mistura / umidade absoluta (w em kg_vapor / kg_ar_seco)
    w_kg_kg = 0.62198 * P_v / (P_atm - P_v)
    w_g_kg = w_kg_kg * 1000.0

    # 2. Temperatura de Ponto de Orvalho (T_po em °C)
    gamma = math.log(max(1e-6, P_v / 0.61078))
    T_po = (237.3 * gamma) / (17.27 - gamma)
    T_po = min(T_po, T_bs)

    # 3. Entalpia específica do ar úmido (h em kJ/kg de ar seco)
    h_kj_kg = 1.006 * T_bs + w_kg_kg * (2501.0 + 1.86 * T_bs)

    # 4. Volume específico do ar úmido (v em m³/kg de ar seco)
    T_kelvin = T_bs + 273.15
    v_m3_kg = (0.287042 * T_kelvin * (1.0 + 1.607858 * w_kg_kg)) / P_atm
    rho_kg_m3 = 1.0 / v_m3_kg

    # 5. Temperatura de Bulbo Úmido (T_bu em °C) por bisseção psicrométrica exata no intervalo [T_po, T_bs]
    low, high = T_po, T_bs
    for _ in range(30):
        mid = 0.5 * (low + high)
        p_vs_bu = calcular_pressao_saturacao_vapor(mid)
        w_sat_bu = 0.62198 * p_vs_bu / (P_atm - p_vs_bu)
        numerador = (2501.0 - 2.326 * mid) * w_sat_bu - 1.006 * (T_bs - mid)
        denominador = 2501.0 + 1.86 * T_bs - 4.186 * mid
        w_est = numerador / denominador
        if w_est > w_kg_kg:
            high = mid
        else:
            low = mid
    T_bu = 0.5 * (low + high)

    return {
        "T_bs": round(T_bs, 2),
        "UR": round(UR, 2),
        "P_atm": round(P_atm, 3),
        "P_v_Pa": round(P_v * 1000.0, 1),
        "w_kg_kg": w_kg_kg,
        "w_g_kg": round(w_g_kg, 2),
        "T_po": round(T_po, 2),
        "T_bu": round(T_bu, 2),
        "h_kj_kg": round(h_kj_kg, 2),
        "v_m3_kg": round(v_m3_kg, 4),
        "rho_kg_m3": round(rho_kg_m3, 4),
    }


# ==============================================================================
# 3. CONVERSÕES DE UNIDADES E EQUAÇÕES DAS PARCELAS DE CARGA TÉRMICA
# ==============================================================================

def converter_unidades_potencia(potencia_w: float) -> Dict[str, float]:
    """Converte potência térmica em Watts (W) para kW, BTU/h e TR."""
    w = float(potencia_w)
    return {
        "W": w,
        "kW": w / 1000.0,
        "BTU_h": w * 3.41214163,
        "TR": w / 3516.85284,
    }


def calcular_temperatura_sol_ar(T_ext: float, alpha: float, I_solar: float, h_ext: float = 17.0) -> Dict[str, float]:
    """
    Calcula a Temperatura Sol-Ar (T_sol_ar) para superfícies opacas expostas à radiação:
    T_sol_ar = T_ext + (alpha * I_solar) / h_ext
    """
    acrescimo_solar = (max(0.0, alpha) * max(0.0, I_solar)) / max(1.0, h_ext)
    return {
        "acrescimo_sol_ar": acrescimo_solar,
        "T_sol_ar": T_ext + acrescimo_solar,
    }


def calcular_conducao_opaca(U: float, area: float, delta_T_eq: float) -> float:
    """Calcula fluxo de calor por condução em regime permanente: Q = U * A * dT_eq (W)."""
    if U < 0 or area < 0:
        raise ValueError("Transmitância U e Área devem ser não-negativas.")
    return max(0.0, float(U) * float(area) * max(0.0, float(delta_T_eq)))


def calcular_carga_janelas(
    U_vidro: float,
    area_vidro: float,
    delta_T: float,
    fator_solar: float,
    irradiancia_w_m2: float,
    fator_sombreamento: float = 1.0,
) -> Dict[str, float]:
    """Calcula separadamente a condução térmica e o ganho solar radiativo nos vidros (W)."""
    if area_vidro < 0 or U_vidro < 0 or fator_solar < 0:
        raise ValueError("Parâmetros de vidro não podem ser negativos.")
    q_cond = float(U_vidro) * float(area_vidro) * max(0.0, float(delta_T))
    q_solar = float(area_vidro) * float(fator_solar) * max(0.0, float(irradiancia_w_m2)) * max(0.0, float(fator_sombreamento))
    return {
        "Q_vidro_cond": q_cond,
        "Q_vidro_solar": q_solar,
        "Q_vidro_total": q_cond + q_solar,
    }


def calcular_carga_ocupantes(n_pessoas: int, q_sens_por_pessoa: float, q_lat_por_pessoa: float) -> Dict[str, float]:
    """Calcula rejeição metabólica sensível e latente dos ocupantes (W)."""
    n = max(0, int(n_pessoas))
    qs = n * max(0.0, float(q_sens_por_pessoa))
    ql = n * max(0.0, float(q_lat_por_pessoa))
    return {"Q_ocup_sens": qs, "Q_ocup_lat": ql, "Q_ocup_total": qs + ql}


def calcular_carga_iluminacao(potencia_w: float, fator_uso: float = 1.0, fator_dissipacao: float = 1.0) -> float:
    """Calcula carga térmica sensível de iluminação elétrica: Q = P * F_uso * F_dissipacao (W)."""
    return max(0.0, float(potencia_w)) * max(0.0, float(fator_uso)) * max(0.0, float(fator_dissipacao))


def calcular_carga_ar_externo(
    vazao_ls: float,
    psic_ext: Dict[str, float],
    psic_int: Dict[str, float],
) -> Dict[str, float]:
    """
    Calcula as cargas sensível e latente associadas à entrada de ar externo (Ventilação ou Infiltração).
    Usa a vazão mássica de ar seco real: m_dot = (V_dot_m3s) / v_ext.
    """
    vazao_m3s = max(0.0, float(vazao_ls)) / 1000.0
    m_dot_ar_seco = vazao_m3s / psic_ext["v_m3_kg"]

    cp_ar_umido = 1006.0 + 1860.0 * psic_ext["w_kg_kg"]  # J/(kg_as·K)
    h_lv = 2501000.0  # Entalpia de vaporização da água a 0°C (J/kg)

    delta_T = max(0.0, psic_ext["T_bs"] - psic_int["T_bs"])
    delta_w = max(0.0, psic_ext["w_kg_kg"] - psic_int["w_kg_kg"])

    q_sens = m_dot_ar_seco * cp_ar_umido * delta_T
    q_lat = m_dot_ar_seco * h_lv * delta_w

    return {
        "vazao_ls": vazao_ls,
        "m_dot_kg_s": m_dot_ar_seco,
        "Q_sens": q_sens,
        "Q_lat": q_lat,
        "Q_total": q_sens + q_lat,
    }


def processar_carga_termica_completa(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executa o balanço térmico global das 11 parcelas do ambiente, retornando resultados
    intermediários, psicrometria, conversões e alertas físicos de engenharia.
    """
    # 1. Psicrometria Externa e Interna
    psic_ext = calcular_propriedades_psicrometricas(dados["T_ext"], dados["UR_ext"], dados["altitude"])
    psic_int = calcular_propriedades_psicrometricas(dados["T_int"], dados["UR_int"], dados["altitude"])

    area_piso = dados["comprimento"] * dados["largura"]
    volume_amb = area_piso * dados["pe_direito"]
    delta_T_ar = psic_ext["T_bs"] - psic_int["T_bs"]
    delta_T_positivo = max(0.0, delta_T_ar)

    # 2. Parcela 1: Paredes Externas (com Temperatura Sol-Ar)
    sol_ar_par = calcular_temperatura_sol_ar(
        psic_ext["T_bs"], dados["alpha_parede"], dados["I_sol_parede"]
    )
    dT_eq_parede = max(0.0, sol_ar_par["T_sol_ar"] - psic_int["T_bs"])
    area_aberturas = dados["area_vidro"] + (dados["area_porta"] if dados["porta_externa"] else 0.0)
    area_parede_liq = max(0.0, dados["area_parede_bruta"] - area_aberturas)
    Q_paredes = calcular_conducao_opaca(dados["U_parede"], area_parede_liq, dT_eq_parede)

    # 3. Parcela 2: Cobertura ou Teto
    if dados["tipo_cobertura"] == "Exposta ao sol":
        sol_ar_cob = calcular_temperatura_sol_ar(
            psic_ext["T_bs"], dados["alpha_cobertura"], 820.0
        )
        dT_eq_cob = max(0.0, sol_ar_cob["T_sol_ar"] - psic_int["T_bs"])
        Q_cobertura = calcular_conducao_opaca(dados["U_cobertura"], area_piso, dT_eq_cob)
    elif dados["tipo_cobertura"] == "Sob pavimento não climatizado":
        dT_eq_cob = max(0.0, dados["dT_entre_forro"])
        Q_cobertura = calcular_conducao_opaca(dados["U_cobertura"], area_piso, dT_eq_cob)
    else:
        dT_eq_cob = 0.0
        Q_cobertura = 0.0

    # 4. Parcela 3: Pisos
    if dados["condicao_piso"] == "Sobre espaço não climatizado (garagem/pilotis)":
        dT_piso = max(0.0, dados["T_vizinho_piso"] - psic_int["T_bs"])
        Q_piso = calcular_conducao_opaca(dados["U_piso"], area_piso, dT_piso)
    elif dados["condicao_piso"] == "Em contato direto com o solo":
        dT_piso = max(0.0, dados["T_vizinho_piso"] - psic_int["T_bs"])
        Q_piso = calcular_conducao_opaca(1.20, area_piso, dT_piso)
    else:
        dT_piso = 0.0
        Q_piso = 0.0

    # 5. Parcela 4: Janelas (Condução + Radiação Solar com Fator de Sombreamento)
    res_janelas = calcular_carga_janelas(
        dados["U_vidro"],
        dados["area_vidro"],
        delta_T_positivo,
        dados["FS_vidro"],
        dados["I_sol_vidro"],
        dados["fator_sombreamento"],
    )

    # 6. Parcela 5: Portas
    dT_porta = delta_T_positivo if dados["porta_externa"] else max(0.0, dados["dT_porta_interna"])
    Q_portas = calcular_conducao_opaca(dados["U_porta"], dados["area_porta"], dT_porta)

    # 7. Parcela 6: Ocupantes (Sensível e Latente)
    res_ocup = calcular_carga_ocupantes(dados["n_pessoas"], dados["q_sens_pes"], dados["q_lat_pes"])

    # 8. Parcela 7: Iluminação
    Q_iluminacao = calcular_carga_iluminacao(
        dados["pot_iluminacao"], dados["fator_uso_ilum"], dados["fator_dissip_ilum"]
    )

    # 9. Parcela 8: Equipamentos (Computadores + Motores + Outros/Laboratório)
    pot_comp_total = dados["n_computadores"] * dados["pot_por_computador"]
    pot_bruta_equip = pot_comp_total + dados["pot_motores"] + dados["pot_equip_outros"]
    Q_equipamentos = pot_bruta_equip * dados["fator_simult_equip"]

    # 10. Parcela 9: Ventilação Higiênica (NBR 16401-3: por pessoa + por área de piso)
    vazao_vent_ls = (dados["n_pessoas"] * dados["vazao_pessoa_ls"]) + (area_piso * dados["vazao_area_ls_m2"])
    res_ventilacao = calcular_carga_ar_externo(vazao_vent_ls, psic_ext, psic_int)

    # 11. Parcela 10: Infiltração (Método das Trocas de Ar por Hora - ACH)
    vazao_inf_ls = (volume_amb * dados["ach_infiltracao"] * 1000.0) / 3600.0
    res_infiltracao = calcular_carga_ar_externo(vazao_inf_ls, psic_ext, psic_int)

    # 12. Parcela 11: Outras Cargas (Dutos, ventiladores ou fontes justificadas)
    Q_outras_sens = max(0.0, float(dados["outras_cargas_sens"]))
    Q_outras_lat = max(0.0, float(dados["outras_cargas_lat"]))

    # Consolidação
    Q_sensivel_total = (
        Q_paredes
        + Q_cobertura
        + Q_piso
        + res_janelas["Q_vidro_cond"]
        + res_janelas["Q_vidro_solar"]
        + Q_portas
        + res_ocup["Q_ocup_sens"]
        + Q_iluminacao
        + Q_equipamentos
        + res_ventilacao["Q_sens"]
        + res_infiltracao["Q_sens"]
        + Q_outras_sens
    )
    Q_latente_total = (
        res_ocup["Q_ocup_lat"]
        + res_ventilacao["Q_lat"]
        + res_infiltracao["Q_lat"]
        + Q_outras_lat
    )
    Q_total = Q_sensivel_total + Q_latente_total
    fcs = Q_sensivel_total / Q_total if Q_total > 0 else 1.0

    # Diagnóstico e Alertas Físicos Automáticos (Seção 10)
    alertas: List[str] = []
    if delta_T_ar < 0:
        alertas.append(
            f"Inversão Térmica Detectada: A temperatura externa ({psic_ext['T_bs']} °C) é menor que a interna ({psic_int['T_bs']} °C). "
            "As parcelas de condução externa foram zeradas para o cálculo de resfriamento (potencial de Free-Cooling)."
        )
    if area_aberturas > dados["area_parede_bruta"]:
        alertas.append(
            f"Inconsistência Geométrica: A soma das áreas de vidros e portas externas ({area_aberturas:.1f} m²) "
            f"supera a área bruta de parede externa ({dados['area_parede_bruta']:.1f} m²). A área líquida opaca foi ajustada para 0 m²."
        )
    densidade_w_m2 = Q_total / area_piso if area_piso > 0 else 0.0
    if densidade_w_m2 > 280.0:
        alertas.append(
            f"Alta Densidade de Carga Térmica ({densidade_w_m2:.1f} W/m²): Valor superior à faixa comercial típica (80 a 220 W/m²). "
            "Verifique se há alta insolação nos vidros, grande ocupação ou excesso de ar externo."
        )
    elif 0.0 < densidade_w_m2 < 45.0:
        alertas.append(
            f"Baixa Densidade de Carga Térmica ({densidade_w_m2:.1f} W/m²): Valor inferior à faixa usual de projeto."
        )
    if fcs < 0.62 and Q_total > 0:
        alertas.append(
            f"Alto Teor de Calor Latente (FCS = {fcs:.2f}): Equipamentos Split convencionais operam com FCS próximo de 0,75. "
            "Recomenda-se prever controle dedicado de desumidificação ou reaquecimento."
        )

    parcelas_lista = [
        {"Categoria": "1. Paredes Externas", "Fenômeno Físico": "Condução Opaca (Lei de Fourier + Sol-Ar)", "Natureza": "Sensível", "W": Q_paredes},
        {"Categoria": "2. Cobertura / Teto", "Fenômeno Físico": "Condução em Fechamento Superior", "Natureza": "Sensível", "W": Q_cobertura},
        {"Categoria": "3. Pisos", "Fenômeno Físico": "Condução pela Laje Inferior", "Natureza": "Sensível", "W": Q_piso},
        {"Categoria": "4a. Janelas (Condução)", "Fenômeno Físico": "Condução/Convecção em Vidros (U·A·ΔT)", "Natureza": "Sensível", "W": res_janelas["Q_vidro_cond"]},
        {"Categoria": "4b. Janelas (Radiação Solar)", "Fenômeno Físico": "Radiação de Onda Curta Transmitida (A·FS·I·Fsomb)", "Natureza": "Sensível", "W": res_janelas["Q_vidro_solar"]},
        {"Categoria": "5. Portas", "Fenômeno Físico": "Condução em Portas (U·A·ΔT)", "Natureza": "Sensível", "W": Q_portas},
        {"Categoria": "6a. Ocupantes (Sensível)", "Fenômeno Físico": "Metabolismo Humano (Convecção + Radiação)", "Natureza": "Sensível", "W": res_ocup["Q_ocup_sens"]},
        {"Categoria": "6b. Ocupantes (Latente)", "Fenômeno Físico": "Metabolismo Humano (Evaporação/Sudorese)", "Natureza": "Latente", "W": res_ocup["Q_ocup_lat"]},
        {"Categoria": "7. Iluminação", "Fenômeno Físico": "Dissipação Eletrotérmica (Efeito Joule)", "Natureza": "Sensível", "W": Q_iluminacao},
        {"Categoria": "8. Equipamentos", "Fenômeno Físico": "Dissipação de Computadores, Motores e Máquinas", "Natureza": "Sensível", "W": Q_equipamentos},
        {"Categoria": "9a. Ventilação (Sensível)", "Fenômeno Físico": "Ar Externo Higiênico (m_ar·cp·ΔT)", "Natureza": "Sensível", "W": res_ventilacao["Q_sens"]},
        {"Categoria": "9b. Ventilação (Latente)", "Fenômeno Físico": "Umidade da Renovação de Ar (m_ar·hlv·Δω)", "Natureza": "Latente", "W": res_ventilacao["Q_lat"]},
        {"Categoria": "10a. Infiltração (Sensível)", "Fenômeno Físico": "Entrada Não Controlada por Frestas (Sensível)", "Natureza": "Sensível", "W": res_infiltracao["Q_sens"]},
        {"Categoria": "10b. Infiltração (Latente)", "Fenômeno Físico": "Entrada Não Controlada por Frestas (Latente)", "Natureza": "Latente", "W": res_infiltracao["Q_lat"]},
        {"Categoria": "11a. Outras Cargas (Sensível)", "Fenômeno Físico": "Ganhos em Dutos / Ventiladores / Extras", "Natureza": "Sensível", "W": Q_outras_sens},
        {"Categoria": "11b. Outras Cargas (Latente)", "Fenômeno Físico": "Fontes Latentes Adicionais", "Natureza": "Latente", "W": Q_outras_lat},
    ]

    return {
        "area_piso": area_piso,
        "volume_amb": volume_amb,
        "area_parede_liq": area_parede_liq,
        "psic_ext": psic_ext,
        "psic_int": psic_int,
        "sol_ar_par": sol_ar_par,
        "dT_eq_parede": dT_eq_parede,
        "dT_eq_cob": dT_eq_cob,
        "dT_piso": dT_piso,
        "dT_porta": dT_porta,
        "res_janelas": res_janelas,
        "res_ocup": res_ocup,
        "res_ventilacao": res_ventilacao,
        "res_infiltracao": res_infiltracao,
        "Q_paredes": Q_paredes,
        "Q_cobertura": Q_cobertura,
        "Q_piso": Q_piso,
        "Q_portas": Q_portas,
        "Q_iluminacao": Q_iluminacao,
        "Q_equipamentos": Q_equipamentos,
        "Q_outras_sens": Q_outras_sens,
        "Q_outras_lat": Q_outras_lat,
        "Q_sensivel_total": Q_sensivel_total,
        "Q_latente_total": Q_latente_total,
        "Q_total": Q_total,
        "unidades_total": converter_unidades_potencia(Q_total),
        "unidades_sens": converter_unidades_potencia(Q_sensivel_total),
        "unidades_lat": converter_unidades_potencia(Q_latente_total),
        "FCS": fcs,
        "densidade_W_m2": densidade_w_m2,
        "densidade_BTUh_m2": (Q_total * 3.41214163) / area_piso if area_piso > 0 else 0.0,
        "parcelas_lista": parcelas_lista,
        "alertas": alertas,
    }


# ==============================================================================
# 4. MÓDULO BÔNUS: CONFORTO TÉRMICO (ABNT NBR ISO 7730 / ASHRAE 55 - PMV E PPD)
# ==============================================================================

def calcular_conforto_pmv_ppd(
    T_ar: float,
    T_rm: float,
    v_ar: float,
    UR: float,
    met: float,
    clo: float,
) -> Dict[str, Any]:
    """
    Calcula o Voto Médio Estimado (PMV), Percentual Estimado de Insatisfeitos (PPD)
    e Temperatura Operativa (T_op) segundo o modelo analítico de Fanger (ABNT NBR ISO 7730).
    """
    M = float(met) * 58.15  # Taxa metabólica em W/m²
    W = 0.0  # Trabalho mecânico externo (assumido nulo para ocupantes em edificações)
    MW = M - W

    I_cl = float(clo) * 0.155  # Isolamento térmico da roupa em m²·K/W
    f_cl = 1.00 + 1.290 * I_cl if I_cl <= 0.078 else 1.05 + 0.645 * I_cl

    # Pressão parcial de vapor d'água em Pascal (Pa)
    p_vs_kpa = calcular_pressao_saturacao_vapor(T_ar)
    p_a = (float(UR) / 100.0) * p_vs_kpa * 1000.0

    T_aa = float(T_ar) + 273.15
    T_ra = float(T_rm) + 273.15
    v = max(0.05, float(v_ar))

    # Coeficiente de transferência de calor por convecção forçada
    h_cf = 12.1 * math.sqrt(v)

    # Estimativa inicial da temperatura superficial da vestimenta (T_cla em Kelvin)
    T_cla = T_aa + (35.5 - float(T_ar)) / (3.5 * I_cl + 0.1)
    p1 = I_cl * f_cl
    p2 = p1 * 3.96
    p3 = p1 * 100.0
    p4 = p1 * T_aa
    p5 = 308.7 - 0.028 * MW + p2 * ((T_ra / 100.0) ** 4)

    xn = T_cla / 100.0
    xf = xn
    eps = 0.00015
    h_c = h_cf

    for _ in range(150):
        xf = 0.5 * (xf + xn)
        h_cn = 2.38 * (abs(100.0 * xf - T_aa) ** 0.25)
        h_c = max(h_cf, h_cn)
        xn = (p5 + p4 * h_c - p2 * (xf ** 4)) / (100.0 + p3 * h_c)
        if abs(xn - xf) <= eps:
            break

    T_cl = 100.0 * xn - 273.15

    # Perdas térmicas do corpo humano (W/m²)
    hl1 = 3.05 * 0.001 * (5733.0 - 6.99 * MW - p_a)  # Difusão de vapor pela pele
    hl2 = 0.42 * (MW - 58.15) if MW > 58.15 else 0.0  # Sudorese (evaporação de suor)
    hl3 = 1.7 * 0.00001 * M * (5867.0 - p_a)  # Respiração latente
    hl4 = 0.0014 * M * (34.0 - float(T_ar))  # Respiração sensível
    hl5 = 3.96 * f_cl * ((xn ** 4) - ((T_ra / 100.0) ** 4))  # Radiação térmica
    hl6 = f_cl * h_c * (T_cl - float(T_ar))  # Convecção

    ts = 0.303 * math.exp(-0.036 * M) + 0.028
    pmv = ts * (MW - hl1 - hl2 - hl3 - hl4 - hl5 - hl6)
    pmv_clamped = max(-3.0, min(3.0, pmv))

    ppd = 100.0 - 95.0 * math.exp(-0.03353 * (pmv ** 4) - 0.2179 * (pmv ** 2))
    ppd = max(5.0, min(100.0, ppd))

    # Temperatura Operativa (ASHRAE 55 / ISO 7730)
    peso_A = 0.5 if v < 0.2 else (0.6 if v < 0.6 else 0.7)
    T_op = peso_A * float(T_ar) + (1.0 - peso_A) * float(T_rm)

    # Classificação normativa (ISO 7730 / NBR 16401-2)
    if -0.5 <= pmv <= 0.5:
        status = "Confortável (Dentro da Zona Normativa ASHRAE 55 / NBR 16401-2: -0,5 <= PMV <= +0,5)"
        sensacao = "Neutro / Conforto Térmico"
    elif pmv > 0.5:
        status = "Desconforto por Calor (PMV > +0,5)"
        sensacao = "Levemente Quente a Muito Quente"
    else:
        status = "Desconforto por Frio (PMV < -0,5)"
        sensacao = "Levemente Frio a Muito Frio"

    # Verificação dos limites de aplicação da ISO 7730
    avisos_validade: List[str] = []
    if not (0.8 <= met <= 4.0):
        avisos_validade.append(f"Taxa metabólica ({met} met) fora da faixa ISO 7730 (0,8 a 4,0 met).")
    if not (0.0 <= clo <= 2.0):
        avisos_validade.append(f"Isolamento de vestimenta ({clo} clo) fora da faixa ISO 7730 (0 a 2,0 clo).")
    if not (10.0 <= T_ar <= 30.0):
        avisos_validade.append(f"Temperatura do ar ({T_ar} °C) fora da faixa ISO 7730 (10 a 30 °C).")
    if not (10.0 <= T_rm <= 40.0):
        avisos_validade.append(f"Temperatura radiante média ({T_rm} °C) fora da faixa ISO 7730 (10 a 40 °C).")
    if not (0.0 <= v_ar <= 1.0):
        avisos_validade.append(f"Velocidade do ar ({v_ar} m/s) fora da faixa ISO 7730 (0 a 1,0 m/s).")
    if p_a > 2700.0:
        avisos_validade.append(f"Pressão parcial de vapor ({p_a:.0f} Pa) acima do limite ISO 7730 (2700 Pa).")

    return {
        "PMV": round(pmv_clamped, 2),
        "PPD": round(ppd, 1),
        "T_op": round(T_op, 2),
        "T_cl": round(T_cl, 2),
        "p_a_Pa": round(p_a, 1),
        "status": status,
        "sensacao": sensacao,
        "avisos_validade": avisos_validade,
    }
