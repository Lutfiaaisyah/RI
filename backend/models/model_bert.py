import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tqdm import tqdm
from joblib import Parallel, delayed
from sklearn.feature_extraction.text import CountVectorizer
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from umap import UMAP
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary
from bertopic.representation import KeyBERTInspired
import joblib
import requests
import json
import requests
import json
from .preprocessing import preprocess_dataframe,simple_tokenizer
import torch
import plotly.io as pio
import torch
import plotly.io as pio
import plotly.express as px
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from scipy.cluster import hierarchy as sch
from scipy.spatial.distance import squareform
from sklearn.metrics.pairwise import cosine_similarity
from bertopic import BERTopic


def bertopic_analysis(df):
    try:
        df_processed = preprocess_dataframe(df)
        docs_series = df_processed['Title'].astype(str) + " " + df_processed['Abstract'].astype(str)
        docs = docs_series.tolist()
        n_docs = len(docs)
        print(f"Total dokumen valid: {n_docs}")

        if n_docs < 5:
            raise ValueError("Terlalu sedikit dokumen untuk analisis topic modeling")

        print("Membuat embeddings...")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        embeddings = embedding_model.encode(docs, show_progress_bar=True, batch_size=64, device=device)

        try:
            umap_model = joblib.load("save_models/umap_model.joblib")
            vectorizer_model = joblib.load("save_models/vectorizer_model.joblib")
            ctfidf_model = joblib.load("save_models/ctfidf_model.joblib")
            representation_model = KeyBERTInspired()
        except Exception as e:
            print(f"Error loading models: {e}")
            return {"error": f"Model files tidak ditemukan: {str(e)}", "plot_html": None}

        print("Tokenizing documents...")
        docs_tokenized = simple_tokenizer(docs)
        dictionary = Dictionary(docs_tokenized)

        # Step 6: Tentukan range min_cluster_size berdasarkan jumlah dokumen
        if n_docs < 500:
            min_cluster_range = range(4, 18)
        elif n_docs < 1000:
            min_cluster_range = range(8, 25)
        elif n_docs < 1500:
            min_cluster_range = range(12, 30)
        elif n_docs < 2500:
            min_cluster_range = range(15, 35)
        elif n_docs < 3500:
            min_cluster_range = range(18, 42)
        elif n_docs < 4500:
            min_cluster_range = range(20, 45)
        elif n_docs < 5500:
            min_cluster_range = range(21, 50)
        elif n_docs < 6500:
            min_cluster_range = range(23, 50)
        elif n_docs < 7500:
            min_cluster_range = range(25, 55)
        elif n_docs < 8500:
            min_cluster_range = range(30, 60)
        elif n_docs < 10000:
            min_cluster_range = range(35, 65)
        else:
            min_cluster_range = range(50, 85)

        print(f"Evaluasi min_cluster_size: {list(min_cluster_range)}")

        def evaluate_min_cluster(min_cluster):
            try:
                hdbscan_model = HDBSCAN(
                    min_cluster_size=min_cluster,
                    metric='euclidean',
                    cluster_selection_method='eom',
                    prediction_data=False,
                    core_dist_n_jobs=-2
                )
                topic_model = BERTopic(
                    embedding_model=embedding_model,
                    umap_model=umap_model,
                    hdbscan_model=hdbscan_model,
                    vectorizer_model=vectorizer_model,
                    ctfidf_model=ctfidf_model,
                    verbose=False
                )
                topic_model.fit(docs, embeddings)
                topic_words = []
                topic_freq = topic_model.get_topic_freq()
                topic_ids = topic_freq[(topic_freq['Count'] >= 5) & (topic_freq['Topic'] != -1)]['Topic'].tolist()
                topic_ids = [t for t in topic_ids if t != -1]
                for topic_id in topic_ids:
                    words = topic_model.get_topic(topic_id)
                    if isinstance(words, list):
                        topic_words.append([word for word, _ in words])
                if len(topic_words) > 1:
                    coherence_model = CoherenceModel(
                        topics=topic_words,
                        texts=docs_tokenized,
                        dictionary=dictionary,
                        coherence='c_v',
                        processes=1,
                        topn=15
                    )
                    coherence = coherence_model.get_coherence()
                    return (min_cluster, coherence, topic_model)
                else:
                    return (min_cluster, np.nan, None)
            except Exception as e:
                print(f"min_cluster_size = {min_cluster} → ERROR: {str(e)}")
                return (min_cluster, np.nan, None)

        results = []
        for m in tqdm(min_cluster_range, desc="Evaluating cluster sizes"):
            result = evaluate_min_cluster(m)
            results.append(result)

        best_score = -1
        best_size = None
        best_model = None
        # Simpan opsi cluster yang valid untuk dropdown
        valid_clusters = []
        
        for min_cluster, coherence, model in results:
            if not np.isnan(coherence):
                print(f"min_cluster_size = {min_cluster} → Coherence = {coherence:.4f}")
                
                valid_clusters.append(min_cluster)
                if coherence > best_score:
                    best_score = coherence
                    best_size = min_cluster
                    best_model = model
            else:
                print(f"min_cluster_size = {min_cluster} → Tidak cukup topik atau error")

        filtered = [(m, c) for m, c, _ in results if not np.isnan(c)]
        plot_html = None

        if filtered:
            min_clusters = [x[0] for x in filtered]
            scores = [x[1] for x in filtered]

            plot_df = pd.DataFrame({
                'min_cluster_size': min_clusters,
                'coherence_score': scores
            })

            fig = px.line(
                plot_df,
                x='min_cluster_size',
                y='coherence_score',
                markers=True,
                title="Coherence Score vs. min_cluster_size (HDBSCAN)",
                labels={
                    'min_cluster_size': 'Min Cluster Size',
                    'coherence_score': 'Coherence Score'
                }
            )

            fig.update_layout(width=800, height=500, showlegend=False)

            if best_score > -1 and best_size is not None:
                fig.add_vline(
                    x=best_size,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Best: {best_size} (Score: {best_score:.4f})",
                    annotation_position="top left"
                )

            plot_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', div_id="coherence-plot")

        # Siapkan data untuk cache (untuk generate topics nanti)
        cache_data = {
            "docs": docs,
            "embeddings": embeddings,
            "embedding_model": embedding_model,
            "umap_model": umap_model,
            "vectorizer_model": vectorizer_model,
            "ctfidf_model": ctfidf_model,
            "representation_model": representation_model,
        }

        # Siapkan data untuk cache (untuk generate topics nanti)
        cache_data = {
            "docs": docs,
            "embeddings": embeddings,
            "embedding_model": embedding_model,
            "umap_model": umap_model,
            "vectorizer_model": vectorizer_model,
            "ctfidf_model": ctfidf_model,
            "representation_model": representation_model,
        }

        return {
            "plot_html": plot_html,
            "best_params": {
                "min_cluster_size": best_size,
                "coherence_score": best_score
            },
            "cluster_options": sorted(valid_clusters),  # Kirim opsi cluster yang valid
            "cache_data": cache_data  # Data untuk di-cache
        }

    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "plot_html": None
        }

    
def generate_topics_with_label(
    docs,
    embeddings,
    embedding_model,
    umap_model,
    vectorizer_model,
    ctfidf_model,
    representation_model,
    min_cluster_size
):
    try:
        print(f"Generating topics with min_cluster_size: {min_cluster_size}")
        
        # Buat model HDBSCAN baru dengan parameter yang dipilih user
        hdbscan_model = HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric='euclidean',
            cluster_selection_method='eom',
            prediction_data=True
        )

        # Buat model BERTopic dengan semua komponen yang sudah ada
        topic_model = BERTopic(
            embedding_model=embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            ctfidf_model=ctfidf_model,
            representation_model=representation_model,
            calculate_probabilities=True,
            verbose=True
        )

        print("Fitting topic model...")
        topics, probs = topic_model.fit_transform(docs, embeddings)
        
        print("Reducing outliers...")
        new_topics = topic_model.reduce_outliers(docs, topics, strategy="distributions")
        topic_model.update_topics(docs, topics=new_topics, vectorizer_model=vectorizer_model)

        print("Getting topic info...")
        topic_info = topic_model.get_topic_info()
        
        # Generate labels menggunakan Groq API
        print("Generating labels with Groq API...")
        auto_labels = generate_labels_with_groq(topic_info)

        # Update topic info dengan labels
        for topic_id, label in auto_labels.items():
            topic_info.loc[topic_info['Topic'] == topic_id, 'Name'] = label
        try:
            if hasattr(topic_model, "set_topic_labels"):
                topic_model.set_topic_labels({tid: lbl for tid, lbl in auto_labels.items()})
        except Exception as e:
            print(f"Warning: set_topic_labels not available/failed: {e}")

        return topic_model, topic_info

    except Exception as e:
        import traceback
        print("Error in generate_topics_with_label:")
        print(traceback.format_exc())
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def generate_labels_with_groq(topic_info):
    """Generate labels untuk setiap topik menggunakan Groq API"""
    auto_labels = {}
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        print("Warning: GROQ_API_KEY is not set. Using fallback labels.")
        # fallback: pakai "Topic {id}"
        for _, row in topic_info.iterrows():
            tid = row["Topic"]
            if tid == -1: 
                continue
            auto_labels[tid] = f"Topic {tid}"
        return auto_labels

    base_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for _, row in topic_info.iterrows():
        topic_id = row["Topic"]
        if topic_id == -1:
            continue  # Skip outlier topics

        words = row["Representation"]
        prompt = f"""Generate a short and clear topic label (maximum 5 words) based on the following keywords:
{words}
The label must:
- Be in English
- Accurately represent the core meaning of the keywords
- Be concise and descriptive
- Return only the label text (no explanations)"""

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 20
        }

        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                label = response.json()['choices'][0]['message']['content'].strip()
                auto_labels[topic_id] = label
                print(f"Topic {topic_id}: {label}")
            else:
                print(f"API Error for topic {topic_id}: {response.status_code}")
                auto_labels[topic_id] = f"Topic {topic_id}"
        except Exception as e:
            print(f"Error generating label for topic {topic_id}: {str(e)}")
            auto_labels[topic_id] = f"Topic {topic_id}"

    return auto_labels

# ---------- 1) VISUALISASI HIERARKI (MANDIRI) ----------
def build_hierarchy_figure(
    topic_model: BERTopic,
    docs: List[str],
    linkage_method: str = "ward",
    optimal_ordering: bool = False,
) -> str:
    """
    Bangun visualisasi hirarki topik BERTopic dan kembalikan HTML (Plotly) siap-embed.
    Tidak memakai variabel global dan tidak memodifikasi state eksternal.

    Returns:
        plot_html (str): HTML figure dari Plotly (tanpa full HTML wrapper).
    """
    linkage_function = lambda x: sch.linkage(x, linkage_method, optimal_ordering=optimal_ordering)
    hierarchical_topics = topic_model.hierarchical_topics(docs, linkage_function=linkage_function)
    fig = topic_model.visualize_hierarchy(hierarchical_topics=hierarchical_topics)
    plot_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', div_id="topic-hierarchy")
    return plot_html


# ---------- 2) KELOMPOK RISET DARI CLUSTER + PENAMAAN LLM (MANDIRI) ----------
def _topic_matrix_from_model(
    topic_model: BERTopic,
    topics: List[int],
    use_ctfidf: bool = True
):
    """Ambil matriks fitur per-topik secara deterministik, tanpa state eksternal."""
    topic_order = topic_model.get_topic_info()['Topic'].tolist()
    topic_indices = [topic_order.index(t) for t in topics if t in topic_order]
    if use_ctfidf:
        X = topic_model.c_tf_idf_[topic_indices]
    else:
        X = topic_model.topic_embeddings_[topic_indices]
    return X

def _fallback_group_name(labels: List[str], max_words: int = 4) -> str:
    """Fallback nama kelompok jika LLM gagal."""
    from collections import Counter
    stop = {
        "and","of","the","for","to","in","on","with","by","from",
        "data","study","studies","research","analysis","model","models",
        "system","systems","based","using","approach","approaches","method"
    }
    toks = []
    for lbl in labels:
        toks += [t.lower() for t in str(lbl).replace("-", " ").replace("/", " ").split()]
    toks = [t for t in toks if t.isalpha() and t not in stop]
    common = [w for w,_ in Counter(toks).most_common(8)]
    return (" ".join(common[:max_words]).title()) if common else "General Focus Research Group"

def _name_group_with_groq(
    labels: List[str],
    api_key: str,
    model: str = "llama-3.3-70b-versatile",
    max_words: int = 4,
    timeout: int = 30
) -> Optional[str]:
    """Minta nama kelompok ke Groq. Return None jika gagal."""
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    prompt = f"""Name this research group based on its topic labels.
Topic labels: {', '.join(map(str, labels))}
Requirements:
- Output language: English
- Up to {max_words} words (excluding "Research Group")
- Descriptive and specific (capture the common theme)
- Professional and academic tone
- Must end with "Research Group"
- Should represent the common research domain
- No extra punctuation, no explanations
- Examples: "Machine Learning Research Group", "Social Media Research Group", "Health Information Research Group"
Return ONLY the group name."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.15,
        "max_tokens": 24
    }
    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def make_research_groups(
    topic_model: BERTopic,
    use_ctfidf: bool = True,
    color_threshold: float = 1.0,
    linkage_method: str = "ward",
    optimal_ordering: bool = True,
    distance: str = "cosine",
    groq_api_key: Optional[str] = None,
    groq_model: str = "llama-3.3-70b-versatile",
    max_name_words: int = 4,
    save_markdown_path: Optional[str] = None,
    topic_info_df: Optional[pd.DataFrame] = None,   # <<< NEW
) -> Tuple[pd.DataFrame, str]:
    """
    Bentuk 'Research Groups' dari cluster dendrogram.
    Selalu pakai label dari topic_info_df (hasil labeling awal) jika tersedia.
    """
    # 1) Sumber topic_info: pakai override kalau ada
    if topic_info_df is not None:
        topic_info = topic_info_df.copy()
    else:
        topic_info = topic_model.get_topic_info().copy()

    # Hanya topik valid
    topic_info = topic_info[topic_info["Topic"] != -1].copy()

    # Pastikan kolom Name ada & tidak kosong
    if "Name" not in topic_info.columns:
        topic_info["Name"] = None
    if topic_info["Name"].isna().all() or (topic_info["Name"].astype(str).str.strip() == "").all():
        # fallback: pakai top-words dari tiap topik
        names = []
        for tid in topic_info["Topic"].tolist():
            words = topic_model.get_topic(tid) or []
            label = " ".join([w for w, _ in words[:4]]) if words else f"Topic {tid}"
            names.append(label)
        topic_info["Name"] = names

    # Daftar topic ids
    topics = topic_info["Topic"].tolist()
    if not topics:
        raise ValueError("Tidak ada topik valid (selain -1). Coba min_cluster_size yang lebih kecil.")

    # 2) Matriks fitur per-topik
    X = _topic_matrix_from_model(topic_model, topics, use_ctfidf=use_ctfidf)

    # 3) Jarak + linkage
    if distance == "cosine":
        D = 1.0 - cosine_similarity(X)
    elif distance == "euclidean":
        X_arr = X.toarray() if hasattr(X, "toarray") else X
        from sklearn.metrics import pairwise_distances
        D = pairwise_distances(X_arr, metric="euclidean")
    else:
        raise ValueError("distance must be 'cosine' or 'euclidean'")

    Z = sch.linkage(squareform(D, checks=False), method=linkage_method, optimal_ordering=optimal_ordering)

    # 4) Potong dendrogram -> cluster labels
    cluster_labels = sch.fcluster(Z, t=color_threshold, criterion='distance')
    df_clusters = pd.DataFrame({"topic": topics, "cluster": cluster_labels}).sort_values(["cluster","topic"])

    # 5) Join label & Count
    dfm = df_clusters.merge(
        topic_info[["Topic","Name","Count"]],
        left_on="topic", right_on="Topic",
        how="left"
    ).rename(columns={"Name":"topic_label"}).drop(columns=["Topic"]).sort_values(["cluster","Count"], ascending=[True, False])

    # 6) Kelompok + nama
    groups, lines = [], []
    for cid, sub in dfm.groupby("cluster", sort=True):
        topic_ids = sub["topic"].tolist()

        # Selalu pakai label 'Name' (hasil labeling awal); kalau kosong -> fallback top-words
        labels_in_cluster = []
        for _, r in sub.iterrows():
            lbl = str(r["topic_label"]).strip() if pd.notna(r["topic_label"]) else ""
            if not lbl:
                words = topic_model.get_topic(int(r["topic"])) or []
                lbl = " ".join([w for w,_ in words[:4]]) if words else f"Topic {int(r['topic'])}"
            labels_in_cluster.append(lbl)

        # Nama grup: Groq -> fallback heuristik
        group_name = None
        if groq_api_key:
            group_name = _name_group_with_groq(labels_in_cluster, groq_api_key, model=groq_model, max_words=max_name_words)
        if not group_name:
            group_name = _fallback_group_name(labels_in_cluster, max_words=max_name_words)
        if not group_name.lower().endswith("research group"):
            group_name = f"{group_name} Research Group" if group_name else "General Focus Research Group"

        groups.append({
            "research_group": int(cid),
            "group_name": group_name,
            "n_topics": len(topic_ids),
            "topics": topic_ids,
            "topic_labels": labels_in_cluster
        })

        # markdown (boleh diabaikan di frontend)
        lines.append(group_name)
        for lbl in labels_in_cluster:
            lines.append(f"- {lbl}")
        lines.append("")

    groups_df = pd.DataFrame(groups).sort_values("research_group").reset_index(drop=True)
    markdown_text = "\n".join(lines)

    if save_markdown_path:
        with open(save_markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)

    return groups_df, markdown_text
