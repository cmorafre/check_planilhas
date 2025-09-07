# CLAUDE.md - Comparador de Planilhas

## 📋 Resumo do Projeto

Aplicação web em Flask para comparar duas planilhas (Excel/CSV) e identificar diferenças, com sistema avançado de filtros e análise de linhas exclusivas.

## 🎯 Funcionalidades Implementadas

### ✅ **1. Funcionalidades Básicas**
- Upload de planilhas Excel (.xlsx, .xls) e CSV
- Comparação estrutural (dimensões, colunas)
- Identificação de diferenças célula por célula
- Interface web responsiva com Bootstrap 5

### ✅ **2. Sistema de Filtros Avançado**
- **Preview das planilhas** com visualização dos primeiros dados
- **10 operadores de filtro**: Igual, Diferente, Contém, Não contém, Inicia com, Termina com, Maior que, Menor que, Está vazio, Não está vazio
- **Filtros independentes** para cada planilha (origem e destino)
- **Seleção de colunas específicas** para comparação
- **Conversão automática de tipos** (string ↔ número)

### ✅ **3. Sistema de Totalizadores**
- **Detecção automática** de campos numéricos
- **Interface de seleção** para escolher campos a totalizar
- **5 métricas calculadas**: Soma, Média, Mínimo, Máximo, Contagem
- **Comparação visual** entre totais de origem e destino
- **Indicador de diferenças** com cores (verde/amarelo/cinza)

### ✅ **4. Identificação de Linhas Exclusivas**
- **Sistema de campos-chave** para identificação precisa
- **6 campos-chave mapeados**:
  - `loja` ↔ `LOJA`
  - `nf` ↔ `NF`
  - `cod_prod` ↔ `COD_PROD`
  - `cod_vendedor` ↔ `COD_VENDEDOR`
  - `cod_parceiro` ↔ `COD_PARCEIRO`
  - `serie` ↔ `SERIE`
- **Identificação específica** de linhas que existem apenas em uma planilha
- **Visualização completa** da linha exclusiva com todos os campos
- **Destaque visual** dos campos-chave usados na comparação

## 🏗️ Arquitetura do Projeto

```
check_planilhas/
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── README.md             # Documentação do usuário
├── CLAUDE.md             # Esta documentação (contexto do desenvolvimento)
├── uploads/              # Pasta temporária para arquivos
├── templates/            # Templates HTML
│   ├── base.html         # Template base
│   ├── index.html        # Página inicial
│   ├── preview.html      # Página de configuração de filtros
│   └── results.html      # Página de resultados
└── files/               # Arquivos de teste do usuário
    ├── comiss_24_25.xlsx        # Planilha origem (25.072 linhas)
    └── comiss_24_25_DOU.xlsx    # Planilha destino (174 linhas)
```

## 🔧 Funcionalidades Técnicas

### **Backend (app.py)**

#### **Funções Principais:**
1. **`load_spreadsheet(file_path)`** - Carrega Excel/CSV
2. **`apply_filters(df, filters)`** - Aplica filtros com conversão de tipos
3. **`find_unique_rows_by_key_fields(df1, df2)`** - Identifica linhas exclusivas usando campos-chave
4. **`calculate_totals(df, total_columns)`** - Calcula métricas numéricas
5. **`compare_spreadsheets(...)`** - Função principal de comparação

#### **Rotas:**
- **`/`** - Página inicial de upload
- **`/preview`** - Página de configuração de filtros e totalizadores
- **`/compare`** - Processamento da comparação com filtros
- **`/upload`** - Comparação direta (compatibilidade)

### **Frontend**

#### **Templates:**
- **`base.html`** - Layout base com Bootstrap 5
- **`index.html`** - Interface de upload simples
- **`preview.html`** - Interface avançada com:
  - Visualização dos dados (primeiras 5 linhas)
  - Seleção de colunas para comparação
  - Seleção de campos numéricos para totalizar
  - Interface dinâmica de filtros (adicionar/remover)
- **`results.html`** - Resultados detalhados com:
  - Configurações aplicadas (filtros, colunas, totalizadores)
  - Análise de dimensões e estrutura
  - **Seção de Linhas Exclusivas** (principal funcionalidade)
  - Totalizadores com comparação visual
  - Diferenças célula por célula

## 🎯 Caso de Uso Principal

### **Cenário Testado:**
- **Planilha Origem**: 173 linhas com `cod_vendedor = 281`
- **Planilha Destino**: 174 linhas com `COD_VENDEDOR = 281`
- **Resultado**: 1 linha exclusiva identificada no destino

### **Linha Exclusiva Encontrada:**
- **Loja**: 11
- **NF**: 8476
- **Produto**: 10575
- **Vendedor**: 281
- **Parceiro**: 10000393
- **Série**: 1

## 🐛 Problemas Resolvidos

### **1. Filtro Jinja2 Inexistente**
- **Erro**: `No filter named 'tojsonstring'`
- **Solução**: Substituído por `tojson`

### **2. Conversão de Tipos nos Filtros**
- **Problema**: Filtros não funcionavam (string vs int)
- **Solução**: Conversão automática `pd.to_numeric()` para campos numéricos

### **3. Tag Jinja2 Inexistente**
- **Erro**: `Encountered unknown tag 'break'`
- **Solução**: Substituído por acesso direto `sample[0].items()`

### **4. Erro de Indexação Pandas**
- **Erro**: `Unalignable boolean Series provided as indexer`
- **Solução**: `reset_index(drop=True)` após filtros + máscaras com índices corretos

## 🔄 Fluxo da Aplicação

1. **Upload** → Usuário faz upload de 2 planilhas
2. **Preview** → Sistema mostra dados e oferece opções de configuração
3. **Configuração** → Usuário seleciona:
   - Colunas para comparar
   - Filtros para cada planilha
   - Campos numéricos para totalizar
4. **Processamento** → Sistema aplica filtros e executa comparação
5. **Resultados** → Exibe:
   - Linhas exclusivas (principal resultado solicitado)
   - Totalizadores comparativos
   - Diferenças estruturais e de dados

## 📊 Logs de Debug

O sistema inclui logs detalhados para troubleshooting:
- Filtros recebidos e aplicados
- Número de linhas após cada filtro
- Campos-chave mapeados
- Quantidade de linhas exclusivas encontradas

## 🚀 Como Executar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar aplicação
python app.py

# 3. Acessar no navegador
http://localhost:5000
```

## 📝 Próximas Melhorias Sugeridas

1. **Exportação de Resultados** - Salvar comparações em Excel/PDF
2. **Histórico de Comparações** - Armazenar comparações anteriores
3. **API REST** - Permitir integração com outros sistemas
4. **Comparação de Múltiplas Planilhas** - Comparar mais de 2 arquivos
5. **Campos-chave Configuráveis** - Permitir usuário definir campos-chave
6. **Performance** - Otimização para planilhas muito grandes

## 🔧 Dependências

```
Flask==2.3.3
pandas==2.1.3
openpyxl==3.1.2
xlrd==2.0.1
Werkzeug==2.3.7
```

## 📈 Métricas do Projeto

- **Linhas de código**: ~600 linhas (app.py)
- **Templates HTML**: 4 arquivos
- **Funcionalidades**: 4 principais
- **Tempo de desenvolvimento**: 1 sessão
- **Status**: ✅ Funcional e testado

---

**Desenvolvido com Claude Code**  
**Data**: 2025-01-16  
**Usuário**: Cristiano  
**Objetivo**: Identificar diferenças específicas entre planilhas de comissões