from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
import tempfile
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_spreadsheet(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        return df
    except Exception as e:
        return None

def apply_filters(df, filters):
    # Verificar se df é válido
    if not isinstance(df, pd.DataFrame):
        print(f"[ERROR] apply_filters recebeu {type(df)} ao invés de DataFrame!")
        return pd.DataFrame()  # Retornar DataFrame vazio
    
    if not filters:
        print(f"[DEBUG] Nenhum filtro para aplicar. Retornando DF original com {len(df)} linhas.")
        return df.copy()  # Retornar cópia para segurança
    
    print(f"[DEBUG] Aplicando {len(filters)} filtro(s) em DF com {len(df)} linhas.")
    
    try:
        filtered_df = df.copy()
    except Exception as e:
        print(f"[ERROR] Erro ao fazer cópia do DataFrame: {e}")
        return df
    
    for i, filter_config in enumerate(filters):
        column = filter_config.get('column')
        operator = filter_config.get('operator')
        value = filter_config.get('value')
        
        print(f"[DEBUG] Filtro {i+1}: {column} {operator} '{value}'")
        
        if not column or column not in filtered_df.columns:
            print(f"[DEBUG] Coluna '{column}' não encontrada. Colunas disponíveis: {list(filtered_df.columns)}")
            continue
        
        initial_rows = len(filtered_df)
        
        try:
            if operator == 'equals':
                # Tentar converter para o tipo correto
                print(f"[DEBUG] Valor original: '{value}' (tipo: {type(value)})")
                print(f"[DEBUG] Coluna é numérica? {pd.api.types.is_numeric_dtype(filtered_df[column])}")
                if pd.api.types.is_numeric_dtype(filtered_df[column]):
                    try:
                        value = pd.to_numeric(value)
                        print(f"[DEBUG] Valor convertido: {value} (tipo: {type(value)})")
                    except Exception as conv_e:
                        print(f"[DEBUG] Erro na conversão: {conv_e}")
                        pass
                else:
                    print(f"[DEBUG] Mantendo como string")
                
                # Verificar amostra da coluna
                print(f"[DEBUG] Primeiros valores da coluna {column}: {filtered_df[column].head(3).tolist()}")
                
                filtered_df = filtered_df[filtered_df[column] == value]
            elif operator == 'not_equals':
                if pd.api.types.is_numeric_dtype(filtered_df[column]):
                    try:
                        value = pd.to_numeric(value)
                    except:
                        pass
                filtered_df = filtered_df[filtered_df[column] != value]
            elif operator == 'contains':
                filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(str(value), na=False, case=False)]
            elif operator == 'not_contains':
                filtered_df = filtered_df[~filtered_df[column].astype(str).str.contains(str(value), na=False, case=False)]
            elif operator == 'starts_with':
                filtered_df = filtered_df[filtered_df[column].astype(str).str.startswith(str(value), na=False)]
            elif operator == 'ends_with':
                filtered_df = filtered_df[filtered_df[column].astype(str).str.endswith(str(value), na=False)]
            elif operator == 'greater_than':
                numeric_col = pd.to_numeric(filtered_df[column], errors='coerce')
                numeric_val = pd.to_numeric(value, errors='coerce')
                filtered_df = filtered_df[numeric_col > numeric_val]
            elif operator == 'less_than':
                numeric_col = pd.to_numeric(filtered_df[column], errors='coerce')
                numeric_val = pd.to_numeric(value, errors='coerce')
                filtered_df = filtered_df[numeric_col < numeric_val]
            elif operator == 'is_empty':
                filtered_df = filtered_df[filtered_df[column].isna() | (filtered_df[column] == '')]
            elif operator == 'is_not_empty':
                filtered_df = filtered_df[filtered_df[column].notna() & (filtered_df[column] != '')]
            
            final_rows = len(filtered_df)
            print(f"[DEBUG] Filtro {i+1} aplicado: {initial_rows} -> {final_rows} linhas")
            
        except Exception as e:
            print(f"[DEBUG] Erro ao aplicar filtro {i+1}: {str(e)}")
            continue
    
    print(f"[DEBUG] Total final após todos os filtros: {len(filtered_df)} linhas")
    print(f"[DEBUG] Tipo do retorno: {type(filtered_df)}")
    
    # Verificar se é um DataFrame válido antes do retorno
    if not isinstance(filtered_df, pd.DataFrame):
        print(f"[ERROR] apply_filters retornou {type(filtered_df)} ao invés de DataFrame!")
        print(f"[ERROR] Retornando DataFrame original como fallback")
        return df.copy()  # Retornar DataFrame original em caso de erro
    
    # Verificar se o DataFrame não está corrompido
    try:
        _ = len(filtered_df)
        _ = list(filtered_df.columns)
    except Exception as e:
        print(f"[ERROR] DataFrame filtrado parece estar corrompido: {e}")
        return df.copy()
    
    return filtered_df

def normalize_column_name(col_name):
    """Normaliza nome de coluna para comparação"""
    import re
    if not col_name:
        return ""
    
    # Converter para string e minúsculas
    normalized = str(col_name).lower()
    
    # Remover acentos comuns
    accents = {'ç': 'c', 'ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a',
               'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'í': 'i', 'ì': 'i', 
               'î': 'i', 'ï': 'i', 'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 
               'ö': 'o', 'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u'}
    
    for accented, normal in accents.items():
        normalized = normalized.replace(accented, normal)
    
    # Remover caracteres especiais e substituir por espaço
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    
    # Remover espaços extras e substituir por underscore
    normalized = re.sub(r'\s+', '_', normalized.strip())
    
    return normalized

def calculate_column_similarity(col1, col2):
    """Calcula similaridade entre duas colunas (0-1)"""
    if not col1 or not col2:
        return 0.0
    
    # Normalizar nomes
    norm1 = normalize_column_name(col1)
    norm2 = normalize_column_name(col2)
    
    # Correspondência exata
    if norm1 == norm2:
        return 1.0
    
    # Calcular similaridade por subsequência comum
    def longest_common_subsequence(s1, s2):
        m, n = len(s1), len(s2)
        if m == 0 or n == 0:
            return 0
        
        # Criar matriz DP
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    # Calcular LCS e similaridade
    lcs_length = longest_common_subsequence(norm1, norm2)
    max_length = max(len(norm1), len(norm2))
    
    if max_length == 0:
        return 0.0
    
    similarity = lcs_length / max_length
    
    # Bonificação se uma contém a outra
    if norm1 in norm2 or norm2 in norm1:
        similarity += 0.2
    
    # Bonificação para palavras-chave comuns
    keywords = ['cod', 'codigo', 'id', 'num', 'numero', 'nome', 'descr', 'descricao',
                'valor', 'preco', 'qtd', 'quantidade', 'data', 'loja', 'produto']
    
    for keyword in keywords:
        if keyword in norm1 and keyword in norm2:
            similarity += 0.1
            break
    
    return min(1.0, similarity)

def analyze_column_content(df, column, sample_size=100):
    """Analisa o conteúdo de uma coluna para determinar tipo e características"""
    if column not in df.columns or len(df) == 0:
        return {'type': 'unknown', 'sample': [], 'patterns': []}
    
    # Pegar amostra dos dados
    sample_data = df[column].dropna().head(sample_size).tolist()
    
    # Determinar tipo predominante
    numeric_count = 0
    text_count = 0
    date_count = 0
    patterns = set()
    
    for value in sample_data:
        if pd.api.types.is_numeric_dtype(type(value)):
            numeric_count += 1
        elif isinstance(value, str):
            text_count += 1
            # Detectar padrões comuns
            if value.isdigit():
                patterns.add('digits_only')
            elif '/' in value or '-' in value:
                patterns.add('date_like')
            elif value.replace('.', '').replace(',', '').isdigit():
                patterns.add('decimal_like')
        try:
            pd.to_datetime(value)
            date_count += 1
        except:
            pass
    
    total = len(sample_data)
    if total == 0:
        content_type = 'empty'
    elif numeric_count > total * 0.7:
        content_type = 'numeric'
    elif date_count > total * 0.7:
        content_type = 'date'
    else:
        content_type = 'text'
    
    return {
        'type': content_type,
        'sample': sample_data[:10],  # Primeiros 10 valores
        'patterns': list(patterns),
        'stats': {
            'numeric_ratio': numeric_count / max(1, total),
            'text_ratio': text_count / max(1, total),
            'date_ratio': date_count / max(1, total)
        }
    }

def find_intelligent_column_mapping(df1, df2):
    """Encontra mapeamento inteligente entre colunas de duas planilhas"""
    cols1 = list(df1.columns)
    cols2 = list(df2.columns)
    
    print(f"[DEBUG] Analisando mapeamento entre {len(cols1)} e {len(cols2)} colunas")
    
    # Analisar conteúdo das colunas
    content1 = {col: analyze_column_content(df1, col) for col in cols1}
    content2 = {col: analyze_column_content(df2, col) for col in cols2}
    
    # Calcular matriz de similaridade
    similarity_matrix = []
    for i, col1 in enumerate(cols1):
        row = []
        for j, col2 in enumerate(cols2):
            # Similaridade por nome
            name_sim = calculate_column_similarity(col1, col2)
            
            # Similaridade por conteúdo
            content_sim = 0.0
            if content1[col1]['type'] == content2[col2]['type'] and content1[col1]['type'] != 'empty':
                content_sim = 0.3  # Bonus por mesmo tipo
                
                # Bonus adicional por padrões similares
                patterns1 = set(content1[col1]['patterns'])
                patterns2 = set(content2[col2]['patterns'])
                if patterns1 & patterns2:  # Interseção de padrões
                    content_sim += 0.2
            
            # Similaridade total
            total_sim = name_sim * 0.7 + content_sim * 0.3
            row.append({
                'col2': col2,
                'total_similarity': total_sim,
                'name_similarity': name_sim,
                'content_similarity': content_sim,
                'same_type': content1[col1]['type'] == content2[col2]['type']
            })
        
        # Ordenar por similaridade
        row.sort(key=lambda x: x['total_similarity'], reverse=True)
        similarity_matrix.append(row)
    
    # Encontrar mapeamentos únicos com threshold mínimo
    threshold = 0.3
    mapping = {}
    used_cols2 = set()
    mapping_details = {}
    
    # Ordenar colunas por melhor match
    col1_scores = [(i, max(row, key=lambda x: x['total_similarity'])['total_similarity']) 
                   for i, row in enumerate(similarity_matrix)]
    col1_scores.sort(key=lambda x: x[1], reverse=True)
    
    for i, _ in col1_scores:
        col1 = cols1[i]
        best_matches = similarity_matrix[i]
        
        for match in best_matches:
            col2 = match['col2']
            similarity = match['total_similarity']
            
            if similarity >= threshold and col2 not in used_cols2:
                mapping[col1] = col2
                used_cols2.add(col2)
                mapping_details[col1] = match
                print(f"[DEBUG] Mapeado: {col1} -> {col2} (similaridade: {similarity:.2f})")
                break
    
    # Identificar colunas não mapeadas
    unmapped_cols1 = [col for col in cols1 if col not in mapping]
    unmapped_cols2 = [col for col in cols2 if col not in used_cols2]
    
    print(f"[DEBUG] Mapeamento concluído: {len(mapping)} correspondências encontradas")
    print(f"[DEBUG] Não mapeadas - Origem: {len(unmapped_cols1)}, Destino: {len(unmapped_cols2)}")
    
    return {
        'mapping': mapping,
        'mapping_details': mapping_details,
        'unmapped_origin': unmapped_cols1,
        'unmapped_destination': unmapped_cols2,
        'content_analysis': {
            'origin': content1,
            'destination': content2
        },
        'similarity_matrix': similarity_matrix
    }

def find_column_mapping(df1_cols, df2_cols):
    """Função mantida para compatibilidade - versão simplificada"""
    mapping = {}
    
    # Primeiro, mapeamento exato
    for col1 in df1_cols:
        if col1 in df2_cols:
            mapping[col1] = col1
    
    # Depois, mapeamento case-insensitive
    for col1 in df1_cols:
        if col1 not in mapping:
            for col2 in df2_cols:
                if col1.lower() == col2.lower():
                    mapping[col1] = col2
                    break
    
    # Mapeamento por similaridade (remove underscores, case-insensitive)
    for col1 in df1_cols:
        if col1 not in mapping:
            col1_clean = normalize_column_name(col1)
            for col2 in df2_cols:
                col2_clean = normalize_column_name(col2)
                if col1_clean == col2_clean:
                    mapping[col1] = col2
                    break
    
    return mapping

def calculate_key_field_score(df, column):
    """Calcula pontuação de uma coluna como campo-chave (0-100)"""
    if column not in df.columns or len(df) == 0:
        return 0
    
    score = 0
    col_data = df[column].dropna()
    
    if len(col_data) == 0:
        return 0
    
    total_rows = len(df)
    non_null_ratio = len(col_data) / total_rows
    
    # 1. Presença de dados (0-25 pontos)
    score += non_null_ratio * 25
    
    # 2. Uniqueness (0-30 pontos)
    unique_values = col_data.nunique()
    uniqueness_ratio = unique_values / len(col_data)
    score += uniqueness_ratio * 30
    
    # 3. Tipo de dados (0-20 pontos)
    column_name = column.lower()
    if any(keyword in column_name for keyword in ['id', 'cod', 'codigo', 'key', 'chave']):
        score += 20
    elif any(keyword in column_name for keyword in ['num', 'numero', 'nf', 'serie']):
        score += 15
    elif pd.api.types.is_numeric_dtype(col_data):
        score += 10
    
    # 4. Consistência no formato (0-15 pontos)
    if pd.api.types.is_numeric_dtype(col_data):
        score += 15  # Números são mais consistentes
    else:
        # Verificar consistência de strings
        str_data = col_data.astype(str)
        length_variance = str_data.str.len().var()
        if length_variance < 10:  # Baixa variância no comprimento
            score += 10
    
    # 5. Distribuição dos dados (0-10 pontos)
    # Penalizar se muitos valores se repetem (não é bom para chave)
    value_counts = col_data.value_counts()
    max_frequency = value_counts.max()
    if max_frequency / len(col_data) < 0.1:  # Nenhum valor representa mais que 10%
        score += 10
    elif max_frequency / len(col_data) < 0.3:  # Nenhum valor representa mais que 30%
        score += 5
    
    return min(100, score)

def identify_best_key_fields(column_mapping, df1, df2, min_fields=2, max_fields=6):
    """Identifica os melhores campos para usar como chave de comparação"""
    if not column_mapping:
        return [], []
    
    # Calcular pontuação para cada par de colunas mapeadas
    field_scores = []
    for col1, col2 in column_mapping.items():
        score1 = calculate_key_field_score(df1, col1)
        score2 = calculate_key_field_score(df2, col2)
        combined_score = (score1 + score2) / 2
        
        field_scores.append({
            'col1': col1,
            'col2': col2,
            'score1': score1,
            'score2': score2,
            'combined_score': combined_score
        })
        
        print(f"[DEBUG] Campo {col1} <-> {col2}: Score {combined_score:.1f} (df1: {score1:.1f}, df2: {score2:.1f})")
    
    # Ordenar por pontuação
    field_scores.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Selecionar os melhores campos
    selected_fields = field_scores[:max_fields]
    
    # Filtrar campos com pontuação mínima
    min_score_threshold = 40  # Pontuação mínima para ser considerado
    selected_fields = [f for f in selected_fields if f['combined_score'] >= min_score_threshold]
    
    # Garantir número mínimo de campos se possível
    if len(selected_fields) < min_fields:
        # Relaxar o threshold se necessário
        additional_fields = field_scores[len(selected_fields):min_fields]
        selected_fields.extend(additional_fields)
    
    # Extrair listas de colunas
    key_cols1 = [f['col1'] for f in selected_fields]
    key_cols2 = [f['col2'] for f in selected_fields]
    
    print(f"[DEBUG] Campos-chave selecionados: {len(key_cols1)}")
    for i, field in enumerate(selected_fields):
        print(f"[DEBUG] {i+1}. {field['col1']} <-> {field['col2']} (score: {field['combined_score']:.1f})")
    
    return key_cols1, key_cols2, selected_fields

def find_unique_rows_by_intelligent_keys(df1, df2, column_mapping=None):
    """Encontra linhas exclusivas usando campos-chave identificados automaticamente"""
    if column_mapping is None:
        # Se não há mapeamento, usar análise inteligente
        mapping_result = find_intelligent_column_mapping(df1, df2)
        column_mapping = mapping_result['mapping']
    
    if not column_mapping:
        print("[DEBUG] Nenhum mapeamento de colunas disponível, usando comparação simples")
        return find_unique_rows(df1, df2, 'smart')
    
    # Identificar melhores campos-chave
    key_cols1, key_cols2, field_details = identify_best_key_fields(column_mapping, df1, df2)
    
    if len(key_cols1) < 1:
        print("[DEBUG] Nenhum campo-chave adequado encontrado, usando comparação simples")
        return find_unique_rows(df1, df2, 'smart')
    
    # Criar chaves compostas para comparação
    def create_composite_key(df, key_cols):
        if not key_cols:
            return []
        
        key_values = []
        for col in key_cols:
            # Converter para string e tratar valores nulos
            values = df[col].fillna('NULL').astype(str)
            key_values.append(values)
        
        # Concatenar valores com separador
        return ["|".join(row) for row in zip(*key_values)]
    
    # Criar chaves compostas
    keys_origem = create_composite_key(df1, key_cols1)
    keys_destino = create_composite_key(df2, key_cols2)
    
    print(f"[DEBUG] Chaves criadas - Origem: {len(keys_origem)}, Destino: {len(keys_destino)}")
    
    # Converter para sets para encontrar diferenças
    set_origem = set(keys_origem)
    set_destino = set(keys_destino)
    
    # Encontrar chaves exclusivas
    only_in_origem = set_origem - set_destino
    only_in_destino = set_destino - set_origem
    
    print(f"[DEBUG] Exclusivas - Origem: {len(only_in_origem)}, Destino: {len(only_in_destino)}")
    
    # Recuperar linhas completas
    # Criar máscaras booleanas com índices corretos
    mask_origem = pd.Series(keys_origem, index=df1.index).isin(only_in_origem)
    mask_destino = pd.Series(keys_destino, index=df2.index).isin(only_in_destino)
    
    rows_only_in_origem = df1[mask_origem].copy()
    rows_only_in_destino = df2[mask_destino].copy()
    
    # Adicionar informação sobre os campos-chave usados
    comparison_info = [f"{f['col1']} ↔ {f['col2']} (score: {f['combined_score']:.1f})" for f in field_details]
    
    return rows_only_in_origem, rows_only_in_destino, comparison_info

def find_unique_rows_by_key_fields(df1, df2):
    """Função mantida para compatibilidade - agora usa sistema inteligente"""
    return find_unique_rows_by_intelligent_keys(df1, df2)

def find_unique_rows(df1, df2, comparison_strategy='smart'):
    """
    Encontra linhas que existem em uma planilha mas não na outra
    Strategy: 'smart' (mapeia colunas similares) ou 'index' (compara por posição)
    """
    
    if len(df1) == 0 and len(df2) == 0:
        return [], [], []
    
    # Estratégia 1: Tentar mapear colunas similares
    if comparison_strategy == 'smart':
        column_mapping = find_column_mapping(df1.columns, df2.columns)
        mapped_columns = list(column_mapping.keys())
        
        print(f"[DEBUG] Mapeamento de colunas encontrado: {len(column_mapping)} colunas")
        print(f"[DEBUG] Primeiras 5 mapeadas: {dict(list(column_mapping.items())[:5])}")
        
        if len(mapped_columns) >= 2:  # Precisamos de pelo menos 2 colunas para comparar
            # Criar subsets com colunas mapeadas
            df1_subset = df1[mapped_columns].copy()
            df2_subset = df2[[column_mapping[col] for col in mapped_columns]].copy()
            
            # Renomear colunas do df2 para corresponder ao df1
            rename_dict = {column_mapping[col]: col for col in mapped_columns}
            df2_subset = df2_subset.rename(columns=rename_dict)
            
            # Criar hashes para comparação
            df1_subset['_hash'] = df1_subset.apply(lambda x: hash(tuple(x.astype(str))), axis=1)
            df2_subset['_hash'] = df2_subset.apply(lambda x: hash(tuple(x.astype(str))), axis=1)
            
            # Encontrar hashes únicos
            hashes1 = set(df1_subset['_hash'])
            hashes2 = set(df2_subset['_hash'])
            
            unique_in_1 = hashes1 - hashes2
            unique_in_2 = hashes2 - hashes1
            
            print(f"[DEBUG] Hashes únicos - Origem: {len(unique_in_1)}, Destino: {len(unique_in_2)}")
            
            # Recuperar linhas originais
            rows_only_in_1 = df1[df1_subset['_hash'].isin(unique_in_1)].copy()
            rows_only_in_2 = df2[df2_subset['_hash'].isin(unique_in_2)].copy()
            
            return rows_only_in_1, rows_only_in_2, mapped_columns
    
    # Estratégia 2: Comparação simples por número de linhas (fallback)
    print("[DEBUG] Usando estratégia fallback - comparação por quantidade de linhas")
    
    # Se uma planilha tem mais linhas, as extras são "únicas"
    len_diff = len(df2) - len(df1)
    
    if len_diff > 0:
        # Destino tem mais linhas
        rows_only_in_1 = pd.DataFrame()  # Vazio
        rows_only_in_2 = df2.tail(len_diff).copy()  # Últimas linhas extras
        comparison_cols = ['Todas as colunas (por posição)']
    elif len_diff < 0:
        # Origem tem mais linhas  
        rows_only_in_1 = df1.tail(abs(len_diff)).copy()  # Últimas linhas extras
        rows_only_in_2 = pd.DataFrame()  # Vazio
        comparison_cols = ['Todas as colunas (por posição)']
    else:
        # Mesmo número de linhas
        rows_only_in_1 = pd.DataFrame()
        rows_only_in_2 = pd.DataFrame()
        comparison_cols = ['Nenhuma diferença no número de linhas']
    
    return rows_only_in_1, rows_only_in_2, comparison_cols

def calculate_totals(df, total_columns):
    """Calcula totais para colunas numéricas especificadas"""
    totals = {}
    for col in total_columns:
        if col in df.columns:
            try:
                # Converter para numérico e somar, ignorando valores não numéricos
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                totals[col] = {
                    'sum': float(numeric_series.sum()),
                    'count': int(numeric_series.count()),
                    'mean': float(numeric_series.mean()) if numeric_series.count() > 0 else 0,
                    'min': float(numeric_series.min()) if numeric_series.count() > 0 else 0,
                    'max': float(numeric_series.max()) if numeric_series.count() > 0 else 0
                }
            except:
                totals[col] = {
                    'sum': 0,
                    'count': 0,
                    'mean': 0,
                    'min': 0,
                    'max': 0,
                    'error': 'Erro no cálculo'
                }
    return totals

def compare_spreadsheets_with_mapping(file1_path, file2_path, column_mapping, filters1=None, filters2=None, total_columns=None):
    """Compara planilhas usando mapeamento específico de colunas"""
    try:
        print(f"[DEBUG] Iniciando comparação com mapeamento")
        print(f"[DEBUG] Arquivo 1: {file1_path}")
        print(f"[DEBUG] Arquivo 2: {file2_path}")
        print(f"[DEBUG] Mapeamento: {column_mapping}")
        print(f"[DEBUG] Filtros1: {filters1}")
        print(f"[DEBUG] Filtros2: {filters2}")
        
        # Ler as planilhas
        df1 = load_spreadsheet(file1_path)
        df2 = load_spreadsheet(file2_path)
        
        print(f"[DEBUG] DF1 carregado: {type(df1)}, shape: {df1.shape if df1 is not None else 'None'}")
        print(f"[DEBUG] DF2 carregado: {type(df2)}, shape: {df2.shape if df2 is not None else 'None'}")
        
        if df1 is None or df2 is None:
            return {'error': 'Erro ao carregar as planilhas'}
        
        # Aplicar filtros se especificados
        if filters1:
            print(f"[DEBUG] Aplicando filtros em DF1...")
            df1_filtered = apply_filters(df1, filters1)
            print(f"[DEBUG] DF1 após filtros: {type(df1_filtered)}, shape: {df1_filtered.shape if hasattr(df1_filtered, 'shape') else 'N/A'}")
            df1 = df1_filtered.reset_index(drop=True)
            
        if filters2:
            print(f"[DEBUG] Aplicando filtros em DF2...")
            df2_filtered = apply_filters(df2, filters2)
            print(f"[DEBUG] DF2 após filtros: {type(df2_filtered)}, shape: {df2_filtered.shape if hasattr(df2_filtered, 'shape') else 'N/A'}")
            df2 = df2_filtered.reset_index(drop=True)
        
        results = {}
        
        # Informações sobre mapeamento usado
        results['mapping_info'] = {
            'column_mapping': column_mapping,
            'mapped_columns_count': len(column_mapping),
            'original_columns': {
                'file1': len(df1.columns),
                'file2': len(df2.columns)
            }
        }
        
        # Comparar dimensões
        results['dimensions'] = {
            'file1': {'rows': len(df1), 'cols': len(df1.columns)},
            'file2': {'rows': len(df2), 'cols': len(df2.columns)},
            'mapped_cols': len(column_mapping)
        }
        
        # Comparar colunas (necessário para o template results.html)
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        results['columns'] = {
            'only_in_file1': list(cols1 - cols2),
            'only_in_file2': list(cols2 - cols1),
            'common': list(cols1 & cols2)
        }
        
        # Identificar linhas exclusivas usando mapeamento específico
        if len(df1) > 0 or len(df2) > 0:
            rows_only_in_1, rows_only_in_2, comparison_columns = find_unique_rows_by_intelligent_keys(df1, df2, column_mapping)
            
            results['unique_rows'] = {
                'only_in_file1': {
                    'count': len(rows_only_in_1),
                    'sample': rows_only_in_1.head(10).to_dict('records') if len(rows_only_in_1) > 0 else []
                },
                'only_in_file2': {
                    'count': len(rows_only_in_2),
                    'sample': rows_only_in_2.head(10).to_dict('records') if len(rows_only_in_2) > 0 else []
                },
                'comparison_columns': comparison_columns
            }
        
        # Calcular totalizadores se especificado
        if total_columns:
            # Filtrar apenas colunas que existem no mapeamento
            valid_total_cols1 = [col for col in total_columns if col in column_mapping]
            valid_total_cols2 = [column_mapping[col] for col in valid_total_cols1]
            
            results['totals'] = {
                'file1': calculate_totals(df1, valid_total_cols1),
                'file2': calculate_totals(df2, valid_total_cols2),
                'columns': valid_total_cols1
            }
        
        # Adicionar informações sobre filtros aplicados
        results['filters_applied'] = {
            'file1': filters1 if filters1 else [],
            'file2': filters2 if filters2 else [],
            'column_mapping_used': True,
            'total_columns': total_columns if total_columns else []
        }
        
        return results
        
    except Exception as e:
        return {'error': str(e)}

def compare_spreadsheets(file1_path, file2_path, filters1=None, filters2=None, selected_columns=None, total_columns=None):
    try:
        # Ler as planilhas
        df1 = load_spreadsheet(file1_path)
        df2 = load_spreadsheet(file2_path)
        
        if df1 is None or df2 is None:
            return {'error': 'Erro ao carregar as planilhas'}
        
        # Aplicar filtros
        if filters1:
            df1 = apply_filters(df1, filters1)
            df1 = df1.reset_index(drop=True)  # Reset index após filtros
        if filters2:
            df2 = apply_filters(df2, filters2)
            df2 = df2.reset_index(drop=True)  # Reset index após filtros
        
        # Selecionar apenas colunas específicas se especificado
        if selected_columns:
            available_cols1 = [col for col in selected_columns if col in df1.columns]
            available_cols2 = [col for col in selected_columns if col in df2.columns]
            if available_cols1:
                df1 = df1[available_cols1]
            if available_cols2:
                df2 = df2[available_cols2]
        
        results = {}
        
        # Comparar dimensões
        results['dimensions'] = {
            'file1': {'rows': len(df1), 'cols': len(df1.columns)},
            'file2': {'rows': len(df2), 'cols': len(df2.columns)}
        }
        
        # Comparar colunas
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        results['columns'] = {
            'only_in_file1': list(cols1 - cols2),
            'only_in_file2': list(cols2 - cols1),
            'common': list(cols1 & cols2)
        }
        
        # Se têm as mesmas colunas, comparar dados
        if cols1 == cols2:
            # Reordenar colunas para comparação
            df2 = df2[df1.columns]
            
            # Comparar valores célula por célula
            differences = []
            min_rows = min(len(df1), len(df2))
            
            for i in range(min_rows):
                for col in df1.columns:
                    val1 = df1.iloc[i][col]
                    val2 = df2.iloc[i][col]
                    
                    # Tratar valores NaN
                    if pd.isna(val1) and pd.isna(val2):
                        continue
                    elif pd.isna(val1) or pd.isna(val2) or val1 != val2:
                        differences.append({
                            'row': i + 2,  # +2 porque linha 1 é cabeçalho e começamos do 0
                            'column': col,
                            'file1_value': str(val1) if not pd.isna(val1) else 'VAZIO',
                            'file2_value': str(val2) if not pd.isna(val2) else 'VAZIO'
                        })
            
            results['data_differences'] = differences[:100]  # Limitar a 100 diferenças
            results['total_differences'] = len(differences)
            
            # Linhas extras
            if len(df1) > len(df2):
                results['extra_rows_file1'] = len(df1) - len(df2)
            elif len(df2) > len(df1):
                results['extra_rows_file2'] = len(df2) - len(df1)
        
        # Identificar linhas exclusivas usando análise inteligente de campos-chave
        if len(df1) > 0 or len(df2) > 0:
            rows_only_in_1, rows_only_in_2, comparison_columns = find_unique_rows_by_intelligent_keys(df1, df2)
            
            results['unique_rows'] = {
                'only_in_file1': {
                    'count': len(rows_only_in_1),
                    'sample': rows_only_in_1.head(10).to_dict('records') if len(rows_only_in_1) > 0 else []
                },
                'only_in_file2': {
                    'count': len(rows_only_in_2),
                    'sample': rows_only_in_2.head(10).to_dict('records') if len(rows_only_in_2) > 0 else []
                },
                'comparison_columns': comparison_columns
            }
        
        # Calcular totalizadores se especificado
        if total_columns:
            results['totals'] = {
                'file1': calculate_totals(df1, total_columns),
                'file2': calculate_totals(df2, total_columns),
                'columns': total_columns
            }
        
        # Adicionar informações sobre filtros aplicados
        results['filters_applied'] = {
            'file1': filters1 if filters1 else [],
            'file2': filters2 if filters2 else [],
            'selected_columns': selected_columns if selected_columns else [],
            'total_columns': total_columns if total_columns else []
        }
        
        return results
        
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_files():
    """Nova rota para análise inteligente de mapeamento"""
    if 'file1' not in request.files or 'file2' not in request.files:
        flash('Por favor, selecione ambos os arquivos')
        return redirect(url_for('index'))
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        flash('Por favor, selecione ambos os arquivos')
        return redirect(url_for('index'))
    
    if file1 and allowed_file(file1.filename) and file2 and allowed_file(file2.filename):
        # Salvar arquivos temporariamente
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename1 = secure_filename(f"origem_{timestamp}_{file1.filename}")
        filename2 = secure_filename(f"destino_{timestamp}_{file2.filename}")
        
        file1_path = os.path.join(UPLOAD_FOLDER, filename1)
        file2_path = os.path.join(UPLOAD_FOLDER, filename2)
        
        file1.save(file1_path)
        file2.save(file2_path)
        
        # Carregar planilhas para análise
        df1 = load_spreadsheet(file1_path)
        df2 = load_spreadsheet(file2_path)
        
        if df1 is None or df2 is None:
            flash('Erro ao carregar as planilhas')
            return redirect(url_for('index'))
        
        # Fazer análise inteligente de mapeamento
        mapping_result = find_intelligent_column_mapping(df1, df2)
        
        # Armazenar informações na sessão
        session['file1_path'] = file1_path
        session['file2_path'] = file2_path
        session['file1_name'] = file1.filename
        session['file2_name'] = file2.filename
        session['column_mapping'] = mapping_result['mapping']
        
        # Identificar campos-chave sugeridos
        if mapping_result['mapping']:
            key_cols1, key_cols2, key_details = identify_best_key_fields(
                mapping_result['mapping'], df1, df2, min_fields=1, max_fields=5
            )
            session['suggested_keys'] = {
                'cols1': key_cols1,
                'cols2': key_cols2,
                'details': key_details
            }
        else:
            session['suggested_keys'] = {'cols1': [], 'cols2': [], 'details': []}
        
        # Preparar dados para a interface de mapeamento
        mapping_data = {
            'file1': {
                'columns': list(df1.columns),
                'sample_data': df1.head(3).to_dict('records'),
                'total_rows': len(df1),
                'content_analysis': mapping_result['content_analysis']['origin']
            },
            'file2': {
                'columns': list(df2.columns),
                'sample_data': df2.head(3).to_dict('records'),
                'total_rows': len(df2),
                'content_analysis': mapping_result['content_analysis']['destination']
            },
            'mapping': mapping_result['mapping'],
            'mapping_details': mapping_result['mapping_details'],
            'unmapped_origin': mapping_result['unmapped_origin'],
            'unmapped_destination': mapping_result['unmapped_destination'],
            'suggested_keys': session['suggested_keys']['details']
        }
        
        return render_template('mapping.html',
                             mapping=mapping_data,
                             file1_name=file1.filename,
                             file2_name=file2.filename)
    
    flash('Tipos de arquivo não permitidos. Use apenas .xlsx, .xls ou .csv')
    return redirect(url_for('index'))

@app.route('/preview_with_mapping', methods=['POST'])
def preview_with_mapping():
    """Preview com mapeamento confirmado pelo usuário"""
    if 'file1_path' not in session or 'file2_path' not in session:
        flash('Sessão expirou. Por favor, faça upload dos arquivos novamente.')
        return redirect(url_for('index'))
    
    try:
        # Obter mapeamento confirmado
        confirmed_mapping_json = request.form.get('confirmed_mapping', '{}')
        confirmed_mapping = json.loads(confirmed_mapping_json)
        session['column_mapping'] = confirmed_mapping
        
        print(f"[DEBUG] Mapeamento confirmado: {confirmed_mapping}")
        
        # Carregar planilhas para preview
        df1 = load_spreadsheet(session['file1_path'])
        df2 = load_spreadsheet(session['file2_path'])
        
        if df1 is None or df2 is None:
            flash('Erro ao carregar as planilhas')
            return redirect(url_for('index'))
        
        # Identificar colunas numéricas com base no mapeamento
        mapped_cols1 = list(confirmed_mapping.keys())
        mapped_cols2 = list(confirmed_mapping.values())
        
        numeric_columns1 = [col for col in mapped_cols1 if pd.api.types.is_numeric_dtype(df1[col])]
        numeric_columns2 = [col for col in mapped_cols2 if pd.api.types.is_numeric_dtype(df2[col])]
        
        # Preparar dados para preview (primeiras 5 linhas)
        preview_data = {
            'file1': {
                'columns': mapped_cols1,
                'numeric_columns': numeric_columns1,
                'sample_data': df1[mapped_cols1].head().to_dict('records') if mapped_cols1 else [],
                'total_rows': len(df1)
            },
            'file2': {
                'columns': mapped_cols2,
                'numeric_columns': numeric_columns2,
                'sample_data': df2[mapped_cols2].head().to_dict('records') if mapped_cols2 else [],
                'total_rows': len(df2)
            }
        }
        
        return render_template('preview.html', 
                             preview=preview_data,
                             file1_name=session['file1_name'],
                             file2_name=session['file2_name'],
                             mapping_mode=True)
    except Exception as e:
        flash(f'Erro no preview: {str(e)}')
        return redirect(url_for('index'))

@app.route('/quick_compare', methods=['POST'])
def quick_compare():
    """Comparação rápida usando apenas o mapeamento"""
    if 'file1_path' not in session or 'file2_path' not in session:
        flash('Sessão expirou. Por favor, faça upload dos arquivos novamente.')
        return redirect(url_for('index'))
    
    try:
        # Obter mapeamento confirmado
        confirmed_mapping_json = request.form.get('confirmed_mapping', '{}')
        confirmed_mapping = json.loads(confirmed_mapping_json)
        
        print(f"[DEBUG] Comparação rápida com mapeamento: {confirmed_mapping}")
        
        # Fazer comparação com mapeamento
        results = compare_spreadsheets_with_mapping(
            session['file1_path'], 
            session['file2_path'],
            confirmed_mapping
        )
        
        return render_template('results.html', 
                             results=results,
                             file1_name=session['file1_name'],
                             file2_name=session['file2_name'],
                             quick_mode=True)
    except Exception as e:
        flash(f'Erro na comparação: {str(e)}')
        return redirect(url_for('index'))
    finally:
        # Limpar arquivos temporários
        if 'file1_path' in session and os.path.exists(session['file1_path']):
            os.remove(session['file1_path'])
        if 'file2_path' in session and os.path.exists(session['file2_path']):
            os.remove(session['file2_path'])
        # Limpar sessão
        session.pop('file1_path', None)
        session.pop('file2_path', None)
        session.pop('file1_name', None)
        session.pop('file2_name', None)
        session.pop('column_mapping', None)
        session.pop('suggested_keys', None)

@app.route('/compare_with_filters_and_mapping', methods=['POST'])
def compare_with_filters_and_mapping():
    """Nova rota principal: Comparação com mapeamento inteligente + filtros"""
    if 'file1_path' not in session or 'file2_path' not in session:
        flash('Sessão expirou. Por favor, faça upload dos arquivos novamente.')
        return redirect(url_for('index'))
    
    try:
        # Obter mapeamento confirmado
        confirmed_mapping_json = request.form.get('confirmed_mapping', '{}')
        print(f"[DEBUG] Mapeamento JSON recebido: '{confirmed_mapping_json}'")
        
        try:
            confirmed_mapping = json.loads(confirmed_mapping_json) if confirmed_mapping_json else {}
        except json.JSONDecodeError as e:
            print(f"[ERROR] Erro ao fazer parse do mapeamento: {e}")
            confirmed_mapping = {}
        
        # Obter filtros
        filters1_raw = request.form.get('filters1', '[]')
        filters2_raw = request.form.get('filters2', '[]')
        print(f"[DEBUG] Filtros1 JSON recebido: '{filters1_raw}'")
        print(f"[DEBUG] Filtros2 JSON recebido: '{filters2_raw}'")
        
        try:
            filters1 = json.loads(filters1_raw) if filters1_raw else []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Erro ao fazer parse dos filtros1: {e}")
            filters1 = []
            
        try:
            filters2 = json.loads(filters2_raw) if filters2_raw else []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Erro ao fazer parse dos filtros2: {e}")
            filters2 = []
        
        # Obter totalizadores
        total_columns_raw = request.form.get('total_columns', '[]')
        print(f"[DEBUG] Totalizadores JSON recebido: '{total_columns_raw}'")
        
        try:
            total_columns = json.loads(total_columns_raw) if total_columns_raw else []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Erro ao fazer parse dos totalizadores: {e}")
            total_columns = []
        
        print(f"[DEBUG] Comparação completa:")
        print(f"[DEBUG] Mapeamento: {len(confirmed_mapping)} correspondências")
        print(f"[DEBUG] Filtros ORIGEM: {len(filters1)} filtros")
        print(f"[DEBUG] Filtros DESTINO: {len(filters2)} filtros")
        print(f"[DEBUG] Totalizadores: {len(total_columns)} campos")
        
        # Fazer comparação completa
        results = compare_spreadsheets_with_mapping(
            session['file1_path'], 
            session['file2_path'],
            confirmed_mapping,
            filters1,
            filters2,
            total_columns
        )
        
        return render_template('results.html', 
                             results=results,
                             file1_name=session['file1_name'],
                             file2_name=session['file2_name'],
                             advanced_mode=True)
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"[DEBUG] Erro na comparação completa: {str(e)}")
        print(f"[DEBUG] Traceback completo:")
        print(error_traceback)
        flash(f'Erro na comparação: {str(e)}')
        return redirect(url_for('index'))
    finally:
        # Limpar arquivos temporários
        if 'file1_path' in session and os.path.exists(session['file1_path']):
            os.remove(session['file1_path'])
        if 'file2_path' in session and os.path.exists(session['file2_path']):
            os.remove(session['file2_path'])
        # Limpar sessão
        session.pop('file1_path', None)
        session.pop('file2_path', None)
        session.pop('file1_name', None)
        session.pop('file2_name', None)
        session.pop('column_mapping', None)
        session.pop('suggested_keys', None)

@app.route('/preview_filters', methods=['POST'])
def preview_filters():
    """Rota AJAX para preview dos dados após aplicação de filtros"""
    if 'file1_path' not in session or 'file2_path' not in session:
        return jsonify({'error': 'Sessão expirou'})
    
    try:
        # Obter parâmetros
        planilha_num = int(request.form.get('planilha_num', 1))
        filters_raw = request.form.get('filters', '[]')
        filters = json.loads(filters_raw)
        
        # Carregar planilha apropriada
        file_path = session['file1_path'] if planilha_num == 1 else session['file2_path']
        df = load_spreadsheet(file_path)
        
        if df is None:
            return jsonify({'error': 'Erro ao carregar planilha'})
        
        # Aplicar filtros
        original_count = len(df)
        print(f"[DEBUG] Preview - DF original: {type(df)}, {original_count} linhas")
        
        if filters:
            print(f"[DEBUG] Preview - Aplicando {len(filters)} filtros...")
            df_filtered = apply_filters(df, filters)
            print(f"[DEBUG] Preview - DF filtrado: {type(df_filtered)}")
        else:
            df_filtered = df
        
        # Verificar se df_filtered é válido
        if not isinstance(df_filtered, pd.DataFrame):
            print(f"[ERROR] Preview - df_filtered não é DataFrame: {type(df_filtered)}")
            return jsonify({'error': f'Erro interno: resultado dos filtros é {type(df_filtered)}'})
        
        filtered_count = len(df_filtered)
        print(f"[DEBUG] Preview - Contagem final: {filtered_count} linhas")
        
        # Preparar preview (primeiras 5 linhas)
        preview_data = []
        if filtered_count > 0:
            # Limitar colunas para preview (primeiras 6 colunas)
            display_cols = list(df_filtered.columns)[:6]
            preview_data = df_filtered[display_cols].head(5).fillna('VAZIO').to_dict('records')
        
        return jsonify({
            'success': True,
            'original_count': original_count,
            'filtered_count': filtered_count,
            'preview_data': preview_data,
            'columns': list(df_filtered.columns)[:6] if filtered_count > 0 else [],
            'filters_applied': len(filters)
        })
        
    except Exception as e:
        print(f"[DEBUG] Erro no preview de filtros: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/preview', methods=['POST'])
def preview_files():
    if 'file1' not in request.files or 'file2' not in request.files:
        flash('Por favor, selecione ambos os arquivos')
        return redirect(url_for('index'))
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        flash('Por favor, selecione ambos os arquivos')
        return redirect(url_for('index'))
    
    if file1 and allowed_file(file1.filename) and file2 and allowed_file(file2.filename):
        # Salvar arquivos temporariamente
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename1 = secure_filename(f"origem_{timestamp}_{file1.filename}")
        filename2 = secure_filename(f"destino_{timestamp}_{file2.filename}")
        
        file1_path = os.path.join(UPLOAD_FOLDER, filename1)
        file2_path = os.path.join(UPLOAD_FOLDER, filename2)
        
        file1.save(file1_path)
        file2.save(file2_path)
        
        # Carregar planilhas para preview
        df1 = load_spreadsheet(file1_path)
        df2 = load_spreadsheet(file2_path)
        
        if df1 is None or df2 is None:
            flash('Erro ao carregar as planilhas')
            return redirect(url_for('index'))
        
        # Armazenar caminhos na sessão
        session['file1_path'] = file1_path
        session['file2_path'] = file2_path
        session['file1_name'] = file1.filename
        session['file2_name'] = file2.filename
        
        # Identificar colunas numéricas
        numeric_columns1 = [col for col in df1.columns if pd.api.types.is_numeric_dtype(df1[col])]
        numeric_columns2 = [col for col in df2.columns if pd.api.types.is_numeric_dtype(df2[col])]
        
        # Preparar dados para preview (primeiras 5 linhas)
        preview_data = {
            'file1': {
                'columns': list(df1.columns),
                'numeric_columns': numeric_columns1,
                'sample_data': df1.head().to_dict('records'),
                'total_rows': len(df1)
            },
            'file2': {
                'columns': list(df2.columns),
                'numeric_columns': numeric_columns2,
                'sample_data': df2.head().to_dict('records'),
                'total_rows': len(df2)
            }
        }
        
        return render_template('preview.html', 
                             preview=preview_data,
                             file1_name=file1.filename,
                             file2_name=file2.filename)
    
    flash('Tipos de arquivo não permitidos. Use apenas .xlsx, .xls ou .csv')
    return redirect(url_for('index'))

@app.route('/compare', methods=['POST'])
def compare_with_filters():
    if 'file1_path' not in session or 'file2_path' not in session:
        flash('Sessão expirou. Por favor, faça upload dos arquivos novamente.')
        return redirect(url_for('index'))
    
    try:
        # Obter filtros do formulário
        filters1_raw = request.form.get('filters1', '[]')
        filters2_raw = request.form.get('filters2', '[]')
        filters1 = json.loads(filters1_raw)
        filters2 = json.loads(filters2_raw)
        selected_columns = request.form.getlist('selected_columns')
        total_columns = request.form.getlist('total_columns')
        
        print(f"[DEBUG] Filtros1 recebidos: {filters1}")
        print(f"[DEBUG] Filtros2 recebidos: {filters2}")
        print(f"[DEBUG] Colunas selecionadas: {selected_columns}")
        print(f"[DEBUG] Colunas para totalizar: {total_columns}")
        
        # Verificar se há mapeamento de colunas na sessão
        column_mapping = session.get('column_mapping', {})
        
        # Usar função apropriada baseada na existência de mapeamento
        if column_mapping:
            print(f"[DEBUG] Usando mapeamento de colunas da sessão: {column_mapping}")
            results = compare_spreadsheets_with_mapping(
                session['file1_path'], 
                session['file2_path'],
                column_mapping,
                filters1, 
                filters2,
                total_columns if total_columns else None
            )
        else:
            print(f"[DEBUG] Usando comparação tradicional")
            results = compare_spreadsheets(
                session['file1_path'], 
                session['file2_path'],
                filters1, 
                filters2, 
                selected_columns if selected_columns else None,
                total_columns if total_columns else None
            )
        
        return render_template('results.html', 
                             results=results,
                             file1_name=session['file1_name'],
                             file2_name=session['file2_name'])
    except Exception as e:
        flash(f'Erro na comparação: {str(e)}')
        return redirect(url_for('index'))
    finally:
        # Limpar arquivos temporários
        if 'file1_path' in session and os.path.exists(session['file1_path']):
            os.remove(session['file1_path'])
        if 'file2_path' in session and os.path.exists(session['file2_path']):
            os.remove(session['file2_path'])
        # Limpar sessão
        session.pop('file1_path', None)
        session.pop('file2_path', None)
        session.pop('file1_name', None)
        session.pop('file2_name', None)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'file1' not in request.files or 'file2' not in request.files:
        flash('Por favor, selecione ambos os arquivos')
        return redirect(request.url)
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        flash('Por favor, selecione ambos os arquivos')
        return redirect(request.url)
    
    if file1 and allowed_file(file1.filename) and file2 and allowed_file(file2.filename):
        filename1 = secure_filename(f"origem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file1.filename}")
        filename2 = secure_filename(f"destino_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file2.filename}")
        
        file1_path = os.path.join(UPLOAD_FOLDER, filename1)
        file2_path = os.path.join(UPLOAD_FOLDER, filename2)
        
        file1.save(file1_path)
        file2.save(file2_path)
        
        results = compare_spreadsheets(file1_path, file2_path)
        
        # Limpar arquivos temporários
        os.remove(file1_path)
        os.remove(file2_path)
        
        return render_template('results.html', results=results, 
                             file1_name=file1.filename, file2_name=file2.filename)
    
    flash('Tipos de arquivo não permitidos. Use apenas .xlsx, .xls ou .csv')
    return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)