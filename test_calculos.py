"""
Suíte de Testes Automatizados (pytest) - Seção 7: Validação e Testes.
Cobre conversões de unidades, equações térmicas, resistências em série (NBR 15220),
psicrometria, casos-limite, invariantes físicas e verificação de tendências.
"""

import pytest
from calculos import (
    calcular_U_parede_camadas,
    calcular_propriedades_psicrometricas,
    converter_unidades_potencia,
    calcular_conducao_opaca,
    calcular_carga_janelas,
    calcular_carga_ocupantes,
    calcular_carga_iluminacao,
    calcular_conforto_pmv_ppd,
)


def test_conversoes_unidades_padrao():
    """Verifica se 1 TR (3516,85284 W) equivale a ~12.000 BTU/h e 3,51685 kW."""
    conv = converter_unidades_potencia(3516.85284)
    assert conv["TR"] == pytest.approx(1.0, rel=1e-5)
    assert conv["BTU_h"] == pytest.approx(12000.0, rel=1e-3)
    assert conv["kW"] == pytest.approx(3.51685284, rel=1e-5)


def test_casos_limite_nulos():
    """Testa casos-limite: área nula, potência nula e diferença de temperatura nula."""
    assert calcular_conducao_opaca(U=2.5, area=0.0, delta_T_eq=15.0) == 0.0
    assert calcular_conducao_opaca(U=2.5, area=30.0, delta_T_eq=0.0) == 0.0
    assert calcular_carga_iluminacao(potencia_w=0.0, fator_uso=1.0, fator_dissipacao=1.0) == 0.0

    jan_nula = calcular_carga_janelas(U_vidro=5.7, area_vidro=0.0, delta_T=10.0, fator_solar=0.8, irradiancia_w_m2=600.0)
    assert jan_nula["Q_vidro_total"] == 0.0


def test_verificacao_tendencias_lineares():
    """Se a potência de iluminação ou o número de ocupantes dobra, a carga correspondente deve dobrar."""
    q_ilum_base = calcular_carga_iluminacao(500.0, 0.9, 1.0)
    q_ilum_dobro = calcular_carga_iluminacao(1000.0, 0.9, 1.0)
    assert q_ilum_dobro == pytest.approx(2.0 * q_ilum_base, rel=1e-6)

    ocup_base = calcular_carga_ocupantes(10, 75.0, 55.0)
    ocup_dobro = calcular_carga_ocupantes(20, 75.0, 55.0)
    assert ocup_dobro["Q_ocup_total"] == pytest.approx(2.0 * ocup_base["Q_ocup_total"], rel=1e-6)


def test_resistencia_termica_camadas_nbr15220():
    """Verifica se a adição de isolante térmico reduz a transmitância U da parede."""
    sem_isol = calcular_U_parede_camadas(k_miolo=0.45, esp_miolo_cm=14.0, esp_reboco_total_cm=3.0)
    com_isol = calcular_U_parede_camadas(k_miolo=0.45, esp_miolo_cm=14.0, esp_reboco_total_cm=3.0, k_isolante=0.04, esp_isolante_cm=5.0)
    assert com_isol["R_total"] > sem_isol["R_total"]
    assert com_isol["U"] < sem_isol["U"]


def test_invariantes_fisicas_psicrometria():
    """Para UR < 100%, deve valer T_po < T_bu < T_bs; em UR = 100%, T_po == T_bu == T_bs."""
    psic_50 = calcular_propriedades_psicrometricas(T_bs=32.0, UR=50.0, altitude_m=900.0)
    assert psic_50["T_po"] < psic_50["T_bu"] < psic_50["T_bs"]
    assert psic_50["w_g_kg"] > 0.0
    assert psic_50["P_atm"] < 101.325

    psic_100 = calcular_propriedades_psicrometricas(T_bs=25.0, UR=100.0, altitude_m=0.0)
    assert psic_100["T_po"] == pytest.approx(25.0, abs=0.05)
    assert psic_100["T_bu"] == pytest.approx(25.0, abs=0.05)


def test_entradas_invalidas_levantam_erro():
    """Verifica se entradas fisicamente inválidas disparam ValueError."""
    with pytest.raises(ValueError):
        calcular_propriedades_psicrometricas(T_bs=25.0, UR=120.0, altitude_m=0.0)
    with pytest.raises(ValueError):
        calcular_conducao_opaca(U=-1.5, area=10.0, delta_T_eq=5.0)


def test_conforto_termico_fanger_limites():
    """Verifica coerência física do modelo PMV/PPD (ISO 7730) em condição neutra, quente e fria."""
    neutro = calcular_conforto_pmv_ppd(T_ar=24.0, T_rm=24.0, v_ar=0.10, UR=50.0, met=1.2, clo=0.6)
    quente = calcular_conforto_pmv_ppd(T_ar=30.0, T_rm=30.0, v_ar=0.10, UR=60.0, met=1.2, clo=0.6)
    frio = calcular_conforto_pmv_ppd(T_ar=18.0, T_rm=18.0, v_ar=0.20, UR=40.0, met=1.0, clo=0.5)

    assert -0.5 <= neutro["PMV"] <= 0.5
    assert neutro["PPD"] <= 10.5
    assert quente["PMV"] > neutro["PMV"]
    assert frio["PMV"] < neutro["PMV"]
