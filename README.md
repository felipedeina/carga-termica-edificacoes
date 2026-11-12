# ❄️ Simulador Físico de Carga Térmica e Conforto Térmico de Edificações

Aplicação computacional desenvolvida em **Python + Streamlit** para a disciplina de **Refrigeração e Climatização**, destinada ao cálculo analítico e rastreável da carga térmica de edificações (11 parcelas físicas), resistência térmica por camadas (ABNT NBR 15220-2), psicrometria completa e avaliação de conforto térmico pelo método de Fanger (PMV/PPD).

---

## 📂 Arquitetura e Estrutura de Arquivos do Projeto

* **`app.py`**: Interface gráfica interativa em Streamlit dividida em 8 abas temáticas (Projeto e Clima, Envoltória, Cargas Internas e Ar, Resultados e Cenários, Conforto Térmico Bônus, Validação e Testes, Relatório Automático e Sobre o Método/Questões/IA).
* **`calculos.py`**: Módulo de engenharia contendo os bancos de dados normativos, cálculo de transmitância térmica $U$ por espessura de camadas em série, equações psicrométricas analíticas, as 11 parcelas de transferência de calor e o solver iterativo da ABNT NBR ISO 7730 (PMV/PPD).
* **`test_calculos.py`**: Suíte de testes automatizados com `pytest` validando conversões, resistências térmicas em série, casos-limite nulos, tendências físicas lineares, invariantes psicrométricas e tratamento de exceções.
* **`iniciar.bat`**: Script de execução rápida para Windows (força o diretório local `cd /d "%~dp0"`, verifica o Python, instala dependências do `requirements.txt`, roda os testes do `pytest` e abre o navegador com o Streamlit).
* **`requirements.txt`**: Declaração enxuta das bibliotecas necessárias (`streamlit`, `pandas`, `plotly`, `pytest`).

---

## 🚀 Como Executar em Outra Máquina (Windows / Linux / Web)

### Opção 1: Execução Automática no Windows (1 Clique)
Basta dar dois cliques no arquivo **`iniciar.bat`** na pasta raiz do projeto descompactado.

### Opção 2: Execução Manual via Terminal
```bash
pip install -r requirements.txt
pytest test_calculos.py -v
streamlit run app.py
