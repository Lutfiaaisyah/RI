"""
Keyword Matching + Groq API module untuk Research Intelligence
Handles keyword matching analysis dengan RapidFuzz, lalu grouping pakai Groq API
"""

from pathlib import Path
import pandas as pd
import ast
from rapidfuzz import fuzz
import requests
from backend.models.preprocessing import preprocess_dataframe, combine_title_abstract
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import os
import re
import json

# ==============================
# BAGIAN 1: Utility Keyword Matching
# ==============================
def fix_and_eval_keywords(x):
    """Perbaiki string list keywords yang rusak lalu eval jadi list Python"""
    if isinstance(x, str):
        if x.strip().startswith('[,'):
            x = x.replace('[,', '[', 1)
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            return []
    return []

def load_cleaned_keywords():
    """Load CSV keyword ACM yang sudah dibersihkan"""
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dataset'))
    dataset_path = os.path.join(data_path, 'topik_keyword_bersih_final.csv.xls')

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"File tidak ditemukan: {dataset_path}")

    df_topik = pd.read_csv(dataset_path)
    df_topik['Keywords'] = df_topik['Keywords'].apply(fix_and_eval_keywords)
    return df_topik


def cari_bidang_ilmu_terbaik_dengan_fallback(text, df_topik, threshold=80):
    """Cari bidang ilmu terbaik berdasarkan kemiripan keyword"""
    teks = text.lower()
    skor_tertinggi = 0
    topik_terbaik = None
    topik_di_atas_threshold = None
    skor_di_atas_threshold = 0
    
    for _, row in df_topik.iterrows():
        topik = row['Topik_Utama']
        keywords = row['Keywords'] if isinstance(row['Keywords'], list) else []
        
        for kw in keywords:
            if isinstance(kw, str):
                skor = fuzz.partial_ratio(teks, kw.lower())
                if skor > skor_tertinggi:
                    skor_tertinggi = skor
                    topik_terbaik = topik
                if skor >= threshold and skor > skor_di_atas_threshold:
                    skor_di_atas_threshold = skor
                    topik_di_atas_threshold = topik
    
    return topik_di_atas_threshold if topik_di_atas_threshold else topik_terbaik


# ==============================
# BAGIAN 2: Pemanggilan Groq API
# ==============================
api_key = os.getenv("GROQ_API_KEY", "")  # Diambil dari environment variable untuk keamanan
base_url = "https://api.groq.com/openai/v1/chat/completions"

def get_groq_response(prompt, model="llama3-70b-8192"):
    """Panggil Groq API untuk dapatkan jawaban AI"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for research topic classification and grouping."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print("Error:", response.status_code, response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

def generate_prompt(fields, n_groups=5):
    """Buat prompt grouping ke Groq API"""
    daftar = "\n".join(f"- {field}" for field in fields)
    return f"""
I have the following scientific research fields:

{daftar}

Please group them into {n_groups} fundamental research groups based on thematic similarity.

For each group, provide:
1. A descriptive group name (1-2 words)
2. A brief description explaining the group's focus
3. List all fields that belong to this group

Return ONLY a valid JSON array, with no extra text, like this:
[
  {{
    "name": "Group Name",
    "description": "Brief description of the group's focus",
    "fields": ["Field 1", "Field 2", "Field 3"]
  }},

]

Make sure each field appears in exactly one group.
Do not include any explanations outside the JSON.
"""

import re
import json

def parse_groq_response(response_text):
    """Parse respons Groq menjadi format yang konsisten"""
    if not response_text:
        return []
    
    # Coba temukan potongan JSON di dalam teks
    try:
        match = re.search(r'(\[.*\]|\{.*\})', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except json.JSONDecodeError:
        pass
    
    # Jika bukan JSON, parse manual (backup)
    groups = []
    lines = response_text.split('\n')
    current_group = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect group headers
        if line.startswith(('1.', '2.', '3.', '4.', '5.')) or \
           line.startswith(('**', '#')) or \
           (line.isupper() and len(line.split()) <= 4):
            
            if current_group:
                groups.append(current_group)
            
            group_name = re.sub(r'^\d+\.', '', line).replace('*', '').replace('#', '').strip()
            current_group = {
                "name": group_name,
                "description": "Research group focusing on related topics",
                "fields": []
            }
        
        # Detect fields
        elif line.startswith(('-', '•', '*')) and current_group:
            field = line[1:].strip()
            if field:
                current_group["fields"].append(field)
    
    if current_group:
        groups.append(current_group)
    
    return groups


# ==============================
# BAGIAN 3: Proses Keyword Matching + Groq Grouping
# ==============================
def keyword_matching(df):
    """Jalankan proses keyword matching dan kembalikan DataFrame hasil"""
    df_topik = load_cleaned_keywords()
    df_processed = preprocess_dataframe(df)
    docs = combine_title_abstract(df_processed)
    
    hasil = [cari_bidang_ilmu_terbaik_dengan_fallback(text, df_topik) for text in docs]
    df_processed['Bidang_Ilmu_ACM'] = hasil
    
    return df_processed

def get_top_n_fields(df_processed, n=10):
    """Ambil Top N bidang ilmu dari hasil keyword matching"""
    if isinstance(df_processed, pd.Series):
        # Jika input adalah Series, buat DataFrame sementara
        temp_df = pd.DataFrame({'Bidang_Ilmu_ACM': df_processed})
        df_processed = temp_df
    
    if 'Bidang_Ilmu_ACM' not in df_processed.columns:
        return [], {}
    
    semua_topik = [item for item in df_processed['Bidang_Ilmu_ACM'] if isinstance(item, str)]
    
    field_counts = pd.Series(semua_topik).value_counts()
    top_fields = field_counts.head(n)
    
    return top_fields.index.tolist(), top_fields.to_dict()

def group_fields_with_groq(df_or_series, n_groups=5):
    """Group bidang ilmu dengan Groq API"""
    # Handle both DataFrame and Series input
    if isinstance(df_or_series, pd.Series):
        df_processed = pd.DataFrame({'Bidang_Ilmu_ACM': df_or_series})
    else:
        df_processed = df_or_series
    
    top_fields, field_counts = get_top_n_fields(df_processed)
    
    if not top_fields:
        return [{
            "name": "No Data",
            "description": "No fields found to group",
            "fields": []
        }]
    
    prompt = generate_prompt(top_fields, n_groups)
    response = get_groq_response(prompt)
    
    if not response:
        # Fallback: buat grouping sederhana
        return create_fallback_groups(top_fields, field_counts, n_groups)
    
    parsed_groups = parse_groq_response(response)
    
    if not parsed_groups:
        return create_fallback_groups(top_fields, field_counts, n_groups)
    
    return parsed_groups

def create_fallback_groups(fields, field_counts, n_groups):
    """Buat grouping fallback jika Groq API gagal"""
    groups = []
    fields_per_group = len(fields) // n_groups + (1 if len(fields) % n_groups > 0 else 0)
    
    for i in range(0, len(fields), fields_per_group):
        group_fields = fields[i:i+fields_per_group]
        # Nama grup diambil dari field teratas di grup ini
        main_field = group_fields[0] if group_fields else f"Group {len(groups)+1}"
        groups.append({
            "name": f"{main_field} & Related",
            "description": f"Group berdasarkan bidang {main_field}, total {len(group_fields)} bidang",
            "fields": group_fields
        })
    
    return groups



# ==============================
# BAGIAN 4: Chart Generator (Top 10 Bidang Ilmu)
# ==============================
def get_top10_chart_df(df_processed):
    """Buat chart horizontal bar untuk Top 10 bidang ilmu"""
    top_fields, counts = get_top_n_fields(df_processed, n=10)
    
    if not top_fields:
        # Buat chart kosong jika tidak ada data
        plt.figure(figsize=(8, 5))
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title("Top 10 Bidang Ilmu (Keyword Matching)")
    else:
        plt.figure(figsize=(8, 5))
        plt.barh(top_fields[::-1], [counts[field] for field in top_fields[::-1]])
        plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    return img_base64