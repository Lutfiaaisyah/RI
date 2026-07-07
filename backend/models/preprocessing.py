"""
Preprocessing module untuk Research Intelligence
Handles data cleaning and preparation
"""

import pandas as pd
import re
import numpy as np
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import os

def remove_copyright(text):
    """
    Menghapus bagian copyright (©) dan semua teks setelahnya
    
    Args:
        text: String input text
        
    Returns:
        str: Cleaned text without copyright
    """
    if pd.isnull(text):
        return ""
    
    # Mencari posisi simbol copyright
    copyright_pos = text.find('©')
    
    if copyright_pos != -1:
        # Memotong teks sebelum simbol copyright dan menghapus whitespace di akhir
        cleaned_text = text[:copyright_pos].rstrip()
        return cleaned_text
    else:
        # Jika tidak ada simbol copyright, kembalikan teks asli
        return text


def clean_abstract(text):
    """
    Membersihkan abstract dari berbagai elemen yang tidak dibutuhkan
    
    Args:
        text: Raw abstract text
        
    Returns:
        str: Cleaned abstract text
    """
    if pd.isnull(text):
        return ""
    
    # LANGKAH 1: Hapus copyright terlebih dahulu (prioritas utama)
    text = remove_copyright(text)
    
    # LANGKAH 2: Hapus label-label struktural
    structural_labels = [
        r'Design/methodology/approach:',
        r'Originality/value:',
        r'Purpose:',
        r'Findings:',
        r'Research limitations:',
        r'Practical implications:',
        r'Social implications:',
        r'Managerial implications:'
    ]
    
    for label in structural_labels:
        text = re.sub(label, '', text, flags=re.IGNORECASE)
    
    # LANGKAH 3: Hapus informasi editorial atau publikasi
    editorial_patterns = [
        r'Copyright:',
        r'corrected-proof ts1',
        r'Peer review.*?responsibility.*?\.',
        r'©.*?All rights reserved\.'
    ]
    
    for pattern in editorial_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # LANGKAH 4: Hapus bagian metadata & keywords
    metadata_patterns = [
        r'Keywords?:.*',
        r'Article info.*'
    ]
    
    for pattern in metadata_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # LANGKAH 5: Hapus karakter non-ASCII
    text = re.sub(r'[^\x00-\x7F]+', '', text)

    # LANGKAH 6: Normalisasi spasi
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def validate_dataframe(df):
    """
    Validasi dataframe sebelum analisis
    
    Args:
        df: pandas DataFrame
        
    Returns:
        pandas DataFrame: Validated dataframe
        
    Raises:
        ValueError: Jika kolom yang dibutuhkan tidak ditemukan
    """
    required_columns = ['Title', 'Abstract']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        # Cek alternatif nama kolom
        alt_mapping = {
            'Title': ['title', 'Title', 'TITLE', 'paper_title', 'document_title'],
            'Abstract': ['abstract', 'Abstract', 'ABSTRACT', 'abs', 'summary']
        }
        
        for req_col in missing_columns[:]:  # Copy list to avoid modification during iteration
            found = False
            for alt_col in alt_mapping.get(req_col, []):
                if alt_col in df.columns:
                    df[req_col] = df[alt_col]
                    missing_columns.remove(req_col)
                    found = True
                    print(f"[OK] Kolom '{alt_col}' digunakan sebagai '{req_col}'")
                    break
        
        # Jika masih ada kolom yang missing
        if missing_columns:
            available_cols = list(df.columns)
            raise ValueError(
                f"Kolom yang dibutuhkan tidak ditemukan: {missing_columns}. "
                f"Kolom yang tersedia: {available_cols}"
            )
    
    return df


def preprocess_dataframe(df):
    """
    Preprocessing dataframe dengan pembersihan copyright dan konten
    
    Args:
        df: pandas DataFrame with Title and Abstract columns
        
    Returns:
        pandas DataFrame: Preprocessed dataframe
    """
    print("Memulai preprocessing data...")
    
    # Validasi dataframe terlebih dahulu
    df = validate_dataframe(df)
    
    original_count = len(df)
    print(f"Data asli: {original_count} dokumen")

    # Proses kolom Abstract
    if 'Abstract' in df.columns:
        df['Abstract'] = df['Abstract'].apply(clean_abstract)
        print("[OK] Kolom 'Abstract' telah diproses")
    
    # Proses kolom Title (jika ada)
    if 'Title' in df.columns:
        df['Title'] = df['Title'].apply(clean_abstract)
        print("[OK] Kolom 'Title' telah diproses")

    # Hapus baris yang null/kosong di Title atau Abstract
    before_cleaning = len(df)
    
    if 'Title' in df.columns and 'Abstract' in df.columns:
        df = df.dropna(subset=['Title', 'Abstract'])
        df = df[(df['Title'].str.strip() != '') & (df['Abstract'].str.strip() != '')]
    elif 'Abstract' in df.columns:
        df = df.dropna(subset=['Abstract'])
        df = df[df['Abstract'].str.strip() != '']
    elif 'Title' in df.columns:
        df = df.dropna(subset=['Title'])
        df = df[df['Title'].str.strip() != '']

    after_null_removal = len(df)
    print(f"[OK] Setelah menghapus data kosong: {after_null_removal} dokumen")

    # Hapus duplikat
    if 'Title' in df.columns and 'Abstract' in df.columns:
        df = df.drop_duplicates(subset=['Title', 'Abstract'])
    elif 'Abstract' in df.columns:
        df = df.drop_duplicates(subset=['Abstract'])
    elif 'Title' in df.columns:
        df = df.drop_duplicates(subset=['Title'])

    final_count = len(df)
    duplicates_removed = after_null_removal - final_count
    
    print(f"[OK] Setelah menghapus duplikat: {final_count} dokumen")
    print(f"[OK] Total data yang dihapus: {original_count - final_count} dokumen")
    print(f"  - Data kosong: {before_cleaning - after_null_removal}")
    print(f"  - Duplikat: {duplicates_removed}")
    
    if final_count < 5:
        raise ValueError(f"Data terlalu sedikit setelah preprocessing ({final_count} dokumen). Minimal 5 dokumen diperlukan.")

    return df


def combine_title_abstract(df):
    """
    Menggabungkan kolom Title dan Abstract menjadi satu teks
    
    Args:
        df: pandas DataFrame with Title and Abstract columns
        
    Returns:
        list: List of combined texts
    """
    if 'Title' in df.columns and 'Abstract' in df.columns:
        # Gabungkan Title dan Abstract
        combined = df['Title'].astype(str) + " " + df['Abstract'].astype(str)
    elif 'Abstract' in df.columns:
        combined = df['Abstract'].astype(str)
    elif 'Title' in df.columns:
        combined = df['Title'].astype(str)
    else:
        raise ValueError("Tidak ada kolom Title atau Abstract yang dapat digunakan")
    
    # Konversi pandas Series ke list biasa
    docs = combined.tolist()
    
    print(f"[OK] Berhasil menggabungkan teks: {len(docs)} dokumen")
    return docs


def get_preprocessing_stats(original_df, processed_df):
    """
    Mendapatkan statistik preprocessing
    
    Args:
        original_df: DataFrame asli
        processed_df: DataFrame setelah preprocessing
        
    Returns:
        dict: Dictionary berisi statistik preprocessing
    """
    stats = {
        'original_count': len(original_df),
        'processed_count': len(processed_df),
        'removed_count': len(original_df) - len(processed_df),
        'removal_percentage': ((len(original_df) - len(processed_df)) / len(original_df)) * 100
    }
    
    return stats


def clean_text_for_analysis(text):
    """
    Pembersihan teks khusus untuk analisis (lebih aggressive)
    
    Args:
        text: Input text
        
    Returns:
        str: Cleaned text
    """
    if pd.isnull(text):
        return ""
    
    # Hapus URL
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Hapus email
    text = re.sub(r'\S+@\S+', '', text)
    
    # Hapus angka yang berlebihan
    text = re.sub(r'\b\d{4,}\b', '', text)  # Hapus tahun atau angka panjang
    
    # Hapus karakter khusus berlebihan
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Normalisasi spasi
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# Fungsi utilitas tambahan
def check_data_quality(df):
    """
    Mengecek kualitas data
    
    Args:
        df: pandas DataFrame
        
    Returns:
        dict: Report kualitas data
    """
    report = {
        'total_rows': len(df),
        'columns': list(df.columns),
        'missing_data': {},
        'empty_strings': {},
        'duplicates': 0
    }
    
    # Cek missing data
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        empty_count = (df[col].astype(str).str.strip() == '').sum()
        
        report['missing_data'][col] = missing_count
        report['empty_strings'][col] = empty_count
    
    # Cek duplikat
    if 'Title' in df.columns and 'Abstract' in df.columns:
        report['duplicates'] = df.duplicated(subset=['Title', 'Abstract']).sum()
    elif 'Abstract' in df.columns:
        report['duplicates'] = df.duplicated(subset=['Abstract']).sum()
    
    return report

# Tambahkan path nltk_data lokal
nltk_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'save_models', 'nltk_data'))
nltk.data.path.append(nltk_data_path)

# Opsional: validasi resource
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    raise RuntimeError("Resource NLTK tidak ditemukan di save_models/nltk_data. Pastikan sudah lengkap.")

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()
def simple_tokenizer(texts):
    tokenized = []
    for doc in texts:
        doc = doc.lower()     
        doc = re.sub(r'[^a-zA-Z\s]', '', doc)
        doc = re.sub(r'\s+', ' ', doc).strip()  
        tokens = word_tokenize(doc)
        tokens = [lemmatizer.lemmatize(w, pos='v') for w in tokens if w not in stop_words and len(w) > 2]
        tokenized.append(tokens)
    return tokenized