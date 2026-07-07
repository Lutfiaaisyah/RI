from flask import Flask, render_template, request, jsonify
import os
import pandas as pd
from flask import render_template_string
# Import dari backend
from backend.models.preprocessing import preprocess_dataframe
from backend.models.model_bert import bertopic_analysis, generate_topics_with_label
from backend.models.model_match import keyword_matching,group_fields_with_groq, get_top10_chart_df
from backend.models.model_match import keyword_matching
from backend.models.model_bert import build_hierarchy_figure,make_research_groups
import base64
from io import BytesIO

app = Flask(__name__,
            template_folder='frontend/templates',
            static_folder='frontend/static')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory cache untuk menyimpan model dan data
analysis_cache = {}

@app.route('/')
def index():
    return render_template(
        'index.html', 
        plot_html="", 
        best_params={})


@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file and file.filename.lower().endswith(('.csv', '.xlsx')):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(filepath):
            return 'DUPLICATE'
        file.save(filepath)
        return 'OK'
    return 'Format salah'


@app.route('/files')
def list_files():
    files = []
    for fname in os.listdir(app.config['UPLOAD_FOLDER']):
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        if os.path.isfile(fpath):
            files.append({
                'name': fname,
                'size': os.path.getsize(fpath),
                'status': 'success' if fname.lower().endswith(('.csv', '.xlsx')) else 'fail'
            })
    return jsonify(files)


@app.route('/delete', methods=['POST'])
def delete_file():
    try:
        file_name = request.form.get('name')
        if not file_name:
            return "No filename provided", 400

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            # Hapus dari cache juga
            analysis_cache.pop(file_name, None)
            return "OK"
        else:
            return "File not found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        filename = request.form.get('filename')
        metode = request.form.get('metode')
        
        print(f"=== ANALYZE REQUEST ===")
        print(f"Filename: {filename}")
        print(f"Method: {metode}")
        
        if not filename:
            return jsonify({'error': 'Filename tidak ditemukan'}), 400
        if not metode:
            return jsonify({'error': 'Metode tidak ditemukan'}), 400
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File tidak ditemukan'}), 404

        print(f"Processing file: {filepath}")

        # Load dan preprocessing
        df = pd.read_csv(filepath)
        df = preprocess_dataframe(df)

        if metode == 'bertopic':
            print("Starting BERTopic analysis...")
            hasil = bertopic_analysis(df)
            
            print(f"Analysis result keys: {list(hasil.keys()) if isinstance(hasil, dict) else 'Not a dict'}")

            if 'error' in hasil:
                print(f"Analysis error: {hasil['error']}")
                return jsonify({'error': hasil['error']}), 500

            # Simpan cache untuk generate topics nanti
            if 'cache_data' in hasil:
                analysis_cache[filename] = hasil['cache_data']
                print(f"Cache saved for {filename}")

            # Ambil min_cluster_range yang sudah dievaluasi untuk dropdown
            cluster_options = hasil.get('cluster_options', [])
            
            response_data = {
                "plot_html": hasil["plot_html"],
                "best_params": hasil["best_params"],
                "cluster_options": cluster_options  # Kirim opsi cluster ke frontend
            }
            
            print("Sending response to client")
            return jsonify(response_data)

        elif metode == 'keyword':
            print("Starting Match analysis...")
            hasil = keyword_matching(df)
            
            # Perbaikan: pass DataFrame lengkap, bukan hanya kolom
            grouped_result = group_fields_with_groq(hasil, 5)  # Default 5 groups

            # Hitung Top 10 bidang ilmu
            img_base64 = get_top10_chart_df(hasil)
            
            # Store hasil untuk generate_groups endpoint
            analysis_cache[filename] = {
                "hasil_df": hasil,
                "top_fields": hasil['Bidang_Ilmu_ACM'].tolist() if 'Bidang_Ilmu_ACM' in hasil.columns else []
            }

            return jsonify({
                "chart": img_base64,
                "grouped": grouped_result
            })

        else:
            return jsonify({'error': 'Metode tidak dikenali'}), 400

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route("/generate_topics", methods=["POST"])
def generate_topics():
    data = request.get_json()
    filename = data.get("filename")
    min_cluster_size = int(data.get("min_cluster_size"))
    

    print(f"Generate topics request - File: {filename}, Min cluster: {min_cluster_size}")

    if not filename or filename not in analysis_cache:
        return jsonify({"error": "Data analisis tidak ditemukan. Silakan jalankan analisis BERTopic terlebih dahulu."}), 400

    try:
        cache = analysis_cache[filename]
        print(f"Using cached data for {filename}")
        
        # Panggil fungsi generate topics dengan data yang sudah di-cache
        result = generate_topics_with_label(
            docs=cache["docs"],
            embeddings=cache["embeddings"],
            embedding_model=cache["embedding_model"],
            umap_model=cache["umap_model"],
            vectorizer_model=cache["vectorizer_model"],
            ctfidf_model=cache["ctfidf_model"],
            representation_model=cache["representation_model"],
            min_cluster_size=min_cluster_size
        )

        if isinstance(result, dict) and "error" in result:
            return jsonify(result), 500

        topic_model, topic_info = result
        
        # Filter topik yang valid (bukan outlier)
        valid_topics = topic_info[topic_info["Topic"] != -1][["Topic", "Name", "Count"]]
        valid_topics = valid_topics.rename(columns={"Topic": "topic", "Name": "label", "Count": "count"})

        if filename in analysis_cache:
            analysis_cache[filename].update({
                "topic_model": topic_model,
                "topic_info": topic_info
            })
        else:
            # fallback (harusnya tidak kejadian karena di-check di atas)
            analysis_cache[filename] = {
                "docs": cache.get("docs"),
                "topic_model": topic_model,
                "topic_info": topic_info
            }
        
        return jsonify({
            "topic_count": len(valid_topics),
            "topics": valid_topics.to_dict(orient="records")
        })

    except Exception as e:
        import traceback
        print("Generate topics error:")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route("/generate_groups", methods=["POST"])
def generate_groups():
    data = request.get_json()
    filename = data.get("filename")
    num_groups = int(data.get("num_groups", 5))
    
    if not filename or filename not in analysis_cache:
        return jsonify({
            "error": "Data analisis tidak ditemukan. Silakan jalankan keyword matching terlebih dahulu."
        }), 400
    
    try:
        # Ambil hasil DataFrame dari cache
        cache = analysis_cache[filename]
        hasil_df = cache.get("hasil_df")
        
        if hasil_df is None:
            return jsonify({
                "error": "DataFrame hasil tidak ditemukan dalam cache"
            }), 400
        
        # Panggil Groq untuk mengelompokkan dengan jumlah group yang diminta
        from backend.models.model_match import group_fields_with_groq
        grouped = group_fields_with_groq(hasil_df, num_groups)
        
        return jsonify({
            "group_count": len(grouped),
            "groups": grouped
        })
        
    except Exception as e:
        import traceback
        print("Error in generate_groups:")
        print(traceback.format_exc())
        return jsonify({
            "error": f"Terjadi kesalahan: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500
    

@app.route("/bert_hierarchy", methods=["POST"])
def bert_hierarchy():
    try:
        data = request.get_json()
        filename = data.get("filename")
        linkage_method = data.get("linkage_method", "ward")
        optimal_ordering = bool(data.get("optimal_ordering", True))

        if not filename or filename not in analysis_cache:
            return jsonify({"error": "Cache tidak ditemukan. Jalankan BERTopic dulu."}), 400

        cache = analysis_cache[filename]
        topic_model = cache.get("topic_model")
        docs = cache.get("docs")

        if topic_model is None or docs is None:
            return jsonify({"error": "Model/Docs belum tersedia. Jalankan generate topics dulu."}), 400

        plot_html = build_hierarchy_figure(
            topic_model=topic_model,
            docs=docs,
            linkage_method=linkage_method,
            optimal_ordering=optimal_ordering
        )
        return jsonify({"plot_html": plot_html})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
    
    
@app.route("/bert_research_groups", methods=["POST"])
def bert_research_groups():
    """
    Bentuk kelompok riset sinkron dengan pewarnaan dendrogram.
    Param penting di body JSON:
      - filename (wajib)
      - color_threshold (float, default 1.0)
      - linkage_method ("ward"/"complete"/"average"/"single")
      - optimal_ordering (bool)
      - distance ("cosine"/"euclidean")
      - use_ctfidf (bool)
      - groq_api_key (opsional; kalau None, fallback naming)
      - groq_model (default "llama-3.3-70b-versatile")
      - max_name_words (int)
    """
    try:
        data = request.get_json()
        filename = data.get("filename")
        if not filename or filename not in analysis_cache:
            return jsonify({"error": "Cache tidak ditemukan. Jalankan BERTopic dulu."}), 400

        cache = analysis_cache[filename]
        topic_model = cache.get("topic_model")
        if topic_model is None:
            return jsonify({"error": "topic_model belum ada. Jalankan generate topics dulu."}), 400

        groups_df, md = make_research_groups(
            topic_model=topic_model,
            use_ctfidf=bool(data.get("use_ctfidf", True)),
            color_threshold=float(data.get("color_threshold", 1.0)),
            linkage_method=data.get("linkage_method", "ward"),
            optimal_ordering=bool(data.get("optimal_ordering", True)),
            distance=data.get("distance", "cosine"),
            groq_api_key=data.get("groq_api_key") or os.getenv("GROQ_API_KEY"),
            groq_model=data.get("groq_model", "llama-3.3-70b-versatile"),
            max_name_words=int(data.get("max_name_words", 4)),
            topic_info_df=cache.get("topic_info"),
            save_markdown_path=None
        )

        # simpan ke cache bila perlu
        analysis_cache[filename]["research_groups"] = groups_df

        return jsonify({
            "group_count": int(groups_df.shape[0]),
            "groups": groups_df.to_dict(orient="records"),
            "markdown": md
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == '__main__':
    app.run(debug=False)