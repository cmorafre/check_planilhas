# Comparador de Planilhas - Versão Inteligente

Uma aplicação web em Flask com **análise inteligente** que permite comparar duas planilhas (Excel ou CSV) **independente de sua estrutura** e mostrar as diferenças entre elas.

## 🚀 Funcionalidades Principais

### 🧠 **Sistema de Mapeamento Inteligente** (NOVA FUNCIONALIDADE)
- **Análise automática** de correspondências entre colunas com nomes diferentes
- **Algoritmo de similaridade** avançado com normalização de texto
- **Análise de conteúdo** para identificar tipos de dados e padrões
- **Interface visual** para confirmar e ajustar mapeamentos
- **Campos-chave automáticos** identificados por pontuação inteligente

### 📊 Funcionalidades de Comparação
- Upload de planilhas Excel (.xlsx, .xls) e CSV
- 👁️ **Preview das planilhas** com visualização dos dados
- 🎯 **Seleção de colunas específicas** para comparação
- 🔍 **Sistema de filtros avançado** com múltiplos operadores:
  - Igual a / Diferente de
  - Contém / Não contém
  - Inicia com / Termina com
  - Maior que / Menor que
  - Está vazio / Não está vazio
- 📐 Análise de dimensões (linhas e colunas)
- 🗂️ Identificação de colunas exclusivas
- 📏 **Detecção inteligente de linhas únicas** usando campos-chave
- 🌐 Interface web responsiva e amigável
- ⚙️ **Configuração independente de filtros** para cada planilha

## 🛠️ Como usar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar a aplicação

```bash
python app.py
```

### 3. Acessar no navegador

Abra seu navegador e acesse: `http://localhost:5000`

### 4. Novo Fluxo Inteligente de Comparação

#### **Etapa 1: Upload e Análise Automática**
1. Faça upload da planilha origem
2. Faça upload da planilha destino
3. Clique em "🤖 Analisar e Mapear Automaticamente"

#### **Etapa 2: Revisão do Mapeamento Inteligente**
- 📊 Visualize as **correspondências encontradas automaticamente**
- 🔑 Confira os **campos-chave sugeridos** (com pontuação)
- ✏️ **Ajuste o mapeamento** se necessário
- 👀 **Preview dos dados** das duas planilhas

#### **Etapa 3: Escolha o Tipo de Comparação**
- **🚀 Comparação Rápida**: Identifica apenas diferenças principais
- **⚙️ Comparação Avançada**: Permite configurar filtros e totalizadores adicionais

#### **Etapa 4: Resultados**
- 📊 **Linhas exclusivas** encontradas em cada planilha
- 📈 **Campos-chave utilizados** na comparação
- 🔢 **Mapeamento aplicado** entre as colunas
- 📊 **Totalizadores** (se configurados)

### 5. Comparação Tradicional (ainda disponível)

Você ainda pode usar a rota `/upload` diretamente para comparação sem análise inteligente, mas recomendamos o **novo fluxo inteligente**.

## O que a aplicação detecta

- **Diferenças estruturais**: Colunas que existem apenas em uma das planilhas
- **Diferenças dimensionais**: Número diferente de linhas e colunas
- **Diferenças nos dados**: Valores diferentes nas células correspondentes
- **Células vazias**: Identifica quando uma célula está vazia em uma planilha mas não na outra

## Limitações

- Tamanho máximo de arquivo: 16MB
- Para performance, mostra no máximo 100 diferenças de dados
- Suporta apenas formatos .xlsx, .xls e .csv

## Tecnologias utilizadas

- **Backend**: Flask (Python)
- **Análise de dados**: Pandas
- **Frontend**: Bootstrap 5
- **Manipulação de arquivos**: openpyxl, xlrd

## Estrutura do projeto

```
check_planilhas/
│
├── app.py              # Aplicação principal Flask
├── requirements.txt    # Dependências Python
├── README.md          # Documentação
├── uploads/           # Pasta temporária para uploads
└── templates/         # Templates HTML
    ├── base.html      # Template base
    ├── index.html     # Página inicial
    └── results.html   # Página de resultados
```