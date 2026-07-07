
// Sidebar Navigation
const hamburgerBtn   = document.getElementById('hamburgerBtn');
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const mainArea       = document.getElementById('mainArea');

function toggleSidebar() {
  hamburgerBtn.classList.toggle('active');
  sidebar.classList.toggle('open');
  sidebarOverlay.classList.toggle('active');

  const backItem = document.querySelector('.back-item');
  if (sidebar.classList.contains('open')) {
    backItem.style.display = 'flex';
  } else {
    backItem.style.display = 'none';
  }

  if (window.innerWidth >= 1200) {
    mainArea.classList.toggle('sidebar-open');
  }
}

hamburgerBtn.addEventListener('click', toggleSidebar);
sidebarOverlay.addEventListener('click', toggleSidebar);

document.addEventListener('click', function(e) {
  if (
    window.innerWidth < 1200 &&
    !sidebar.contains(e.target) &&
    !hamburgerBtn.contains(e.target) &&
    sidebar.classList.contains('open')
  ) {
    toggleSidebar();
  }
});

window.addEventListener('resize', function() {
  if (window.innerWidth >= 1200) {
    sidebarOverlay.classList.remove('active');
  } else {
    mainArea.classList.remove('sidebar-open');
  }
});

// Page Navigation
const pages = {
  home:      document.getElementById('homePage'),
  dashboard: document.getElementById('dashboardPage'),
  upload:    document.getElementById('uploadPage'),
  analisis:  document.getElementById('analisisPage')
};

function showPage(page) {
  // Hide all pages
  Object.values(pages).forEach(p => {
    if (p) {
      p.style.display = 'none';
    }
  });
  
  // Show selected page
  if (pages[page]) {
    pages[page].style.display = 'block';
    
    // Load files when showing upload page
    if (page === 'upload') {
      loadFilesFromServer();
    }
  }

  // Update active navigation item
  document.querySelectorAll('.nav-item').forEach(nav => {
    if (nav.dataset.page) {
      nav.classList.toggle('active', nav.dataset.page === page);
    }
  });

  // Close sidebar on mobile after navigation
  if (window.innerWidth < 1200 && sidebar.classList.contains('open')) {
    toggleSidebar();
  }
}

function goToHome() {
  showPage('home');
  if (sidebar.classList.contains('open')) toggleSidebar();
}

function handleGetStarted() {
  showPage('upload');
}

function closeSidebar() {
  if (sidebar.classList.contains('open')) toggleSidebar();
}

// Initialize with home page
showPage('home');

// Add click event listeners to navigation items
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', function(e) {
    e.preventDefault();
    const page = this.dataset.page;
    if (page) {
      showPage(page);
    }
  });
});

// Upload & File Table
let uploadedFiles = [];

const dropzone       = document.querySelector('.dropzone');
const uploadBtn      = document.querySelector('.upload-btn');
const fileInput      = document.getElementById('fileInput');
const fileTableBody  = document.getElementById('fileTableBody');

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderTable() {
  if (!fileTableBody) return;
  
  fileTableBody.innerHTML = '';
  uploadedFiles.forEach((file, idx) => {
    let statusText = '❌ Format Salah';
    if (file.status === 'success') statusText = '✅ Berhasil Diupload';
    if (file.status === 'duplicate') statusText = '❌ File Sudah Ada';
    
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${file.name}</td>
      <td>${formatSize(file.size)}</td>
      <td>${statusText}</td>
      <td>
        <button class="action-btn" title="Delete" onclick="deleteFile(${idx})">🗑️</button>
      </td>
    `;
    fileTableBody.appendChild(row);
  });
}

function loadFilesFromServer() {
  fetch('/files')
    .then(res => {
      if (!res.ok) {
        throw new Error('Network response was not ok');
      }
      return res.json();
    })
    .then(files => {
      uploadedFiles = files || [];
      renderTable();
    })
    .catch(error => {
      console.error('Error loading files:', error);
      uploadedFiles = [];
      renderTable();
    });
}

function deleteFile(idx) {
  if (idx < 0 || idx >= uploadedFiles.length) return;
  
  const file = uploadedFiles[idx];
  const formData = new FormData();
  formData.append('name', file.name);

  fetch('/delete', {
    method: 'POST',
    body: formData
  })
  .then(res => res.text())
  .then(msg => {
    if (msg === 'OK') {
      loadFilesFromServer();
    } else {
      alert('Gagal menghapus file');
    }
  })
  .catch(error => {
    console.error('Error deleting file:', error);
    alert('Gagal menghapus file');
  });
}

// Make deleteFile available globally
window.deleteFile = deleteFile;

// Upload button click handler
if (uploadBtn) {
  uploadBtn.addEventListener('click', () => {
    if (fileInput) {
      fileInput.click();
    }
  });
}

// File input change handler
if (fileInput) {
  fileInput.addEventListener('change', function() {
    const file = this.files[0];
    if (!file) return;

    // Validate file type
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx') {
      alert('File harus berformat CSV atau XLSX');
      this.value = '';
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    // Show loading state
    uploadBtn.textContent = 'Uploading...';
    uploadBtn.disabled = true;

    fetch('/upload', {
      method: 'POST',
      body: formData
    })
    .then(res => res.text())
    .then(msg => {
      let status = 'fail';
      if (msg === 'OK') status = 'success';
      if (msg === 'DUPLICATE') status = 'duplicate';

      if (status === 'duplicate') {
        alert('File sudah ada di server');
      } else if (status === 'success') {
        alert('File berhasil diupload');
      } else {
        alert('Gagal mengupload file');
      }

      loadFilesFromServer();
    })
    .catch(error => {
      console.error('Error uploading file:', error);
      alert('Gagal mengupload file');
    })
    .finally(() => {
      // Reset upload button
      uploadBtn.textContent = 'Upload File';
      uploadBtn.disabled = false;
      this.value = '';
    });
  });
}

// Drag and drop handlers
if (dropzone) {
  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.style.borderColor = '#8B2E2E';
    dropzone.style.backgroundColor = '#f9f9f9';
  });

  dropzone.addEventListener('dragleave', e => {
    e.preventDefault();
    dropzone.style.borderColor = '#ccc';
    dropzone.style.backgroundColor = 'transparent';
  });

  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.style.borderColor = '#ccc';
    dropzone.style.backgroundColor = 'transparent';
    
    const file = e.dataTransfer.files[0];
    if (!file) return;

    // Validate file type
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx') {
      alert('File harus berformat CSV atau XLSX');
      return;
    }

    // Trigger file upload
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
      method: 'POST',
      body: formData
    })
    .then(res => res.text())
    .then(msg => {
      if (msg === 'OK') {
        alert('File berhasil diupload');
        loadFilesFromServer();
      } else if (msg === 'DUPLICATE') {
        alert('File sudah ada di server');
      } else {
        alert('Gagal mengupload file');
      }
    })
    .catch(error => {
      console.error('Error uploading file:', error);
      alert('Gagal mengupload file');
    });
  });

  // Make dropzone clickable
  dropzone.addEventListener('click', () => {
    if (fileInput) {
      fileInput.click();
    }
  });
}

// Analisis & Plot Handling
function showAnalisisSlide(mode) {
  // Hide all analysis slides
  document.querySelectorAll('#analisisPage .analisis-slide').forEach(el => {
    el.classList.remove('active');
  });
  
  // Show selected slide
  const slideId = `analisis${mode.charAt(0).toUpperCase() + mode.slice(1)}`;
  const target = document.getElementById(slideId);
  if (target) {
    target.classList.add('active');
  }
}

// Initialize with default slide
showAnalisisSlide('default');

// Run Analysis Button Handler
const runAnalysisBtn = document.getElementById("runAnalysisBtn");
if (runAnalysisBtn) {
  runAnalysisBtn.addEventListener("click", function() {
    // Check if files are uploaded
    if (uploadedFiles.length === 0) {
      alert("Silakan unggah file terlebih dahulu.");
      return;
    }

    // Get analysis method
    const metodeSelect = document.getElementById("metodeAnalisis");
    const metode = metodeSelect ? metodeSelect.value : null;

    if (!metode) {
      alert("Silakan pilih metode analisis.");
      return;
    }

    // Get first uploaded file name
    const namaFile = uploadedFiles[0].name;

    // Navigate to analysis page
    showPage('analisis');
    
    // Show appropriate analysis slide
    showAnalisisSlide(metode);

    // Run analysis based on method
    if (metode === "bertopic") {
      jalankanAnalisisBertopic(namaFile);
    } else if (metode === "keyword") {
      jalankanAnalisisKeyword(namaFile);
    } else {
      alert("Metode analisis belum didukung.");
    }
  });
}

// Analysis Functions
// Fungsi untuk menyisipkan HTML berisi <script> dan mengeksekusinya
function setInnerHTMLWithScripts(el, html) {
  // Kosongkan elemen terlebih dahulu
  el.innerHTML = "";

  // Buat elemen sementara untuk parsing
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = html;

  // Pindahkan semua elemen non-script terlebih dahulu
  const scripts = [];
  const nodes = Array.from(tempDiv.childNodes);
  
  nodes.forEach(node => {
    if (node.tagName === "SCRIPT") {
      scripts.push(node);
    } else {
      el.appendChild(node.cloneNode(true));
    }
  });

  // Eksekusi script setelah DOM siap
  scripts.forEach(oldScript => {
    const newScript = document.createElement("script");
    
    // Copy semua atribut
    Array.from(oldScript.attributes).forEach(attr => {
      newScript.setAttribute(attr.name, attr.value);
    });
    
    // Set content
    if (oldScript.src) {
      newScript.src = oldScript.src;
      newScript.onload = () => {
        console.log("External script loaded:", oldScript.src);
      };
    } else {
      newScript.textContent = oldScript.textContent;
    }
    
    // Append ke head atau body untuk eksekusi
    document.head.appendChild(newScript);
    
    // Log untuk debugging
    console.log("Script executed:", newScript.src || "inline script");
  });
}

// Updated functions for topic generation

function generateTopikDenganLabel() {
  const minClusterSizeSelect = document.getElementById("minClusterInput");
  const topicResultDiv = document.getElementById("hasilTopik");
  const minCluster = parseInt(minClusterSizeSelect.value);

  // Gunakan currentFilename yang sudah disimpan saat analisis BERTopic
  if (!currentFilename) {
    alert("File belum diupload atau analisis BERTopic belum dijalankan.");
    return;
  }

  if (!minCluster || isNaN(minCluster)) {
    alert("Pilih nilai min_cluster_size yang valid.");
    return;
  }

  // Show loading with spinner
  topicResultDiv.innerHTML = `
    <div style="text-align:center;padding:20px;">
      <p>Generating topics and labels...</p>
      <div class="spinner"></div>
    </div>
  `;

  fetch("/generate_topics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: currentFilename,
      min_cluster_size: minCluster
    }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.error) {
        topicResultDiv.innerHTML = `
          <div style="color:red;padding:10px;border:1px solid red;border-radius:5px;">
            <strong>Error:</strong> ${data.error}
          </div>
        `;
        return;
      }

      // Tampilkan hasil dengan styling yang sesuai dengan CSS
      let html = `<p><strong>Total Topics:</strong> ${data.topic_count}</p>`;

      if (data.topics && data.topics.length > 0) {
        html += `
          <table style="width:100%; border-collapse:collapse; margin-top:10px;">
            <thead>
              <tr>
                <th style="background-color:#4CAF50; color:white; padding:10px; text-align:left;">Topic ID</th>
                <th style="background-color:#4CAF50; color:white; padding:10px; text-align:left;">Label</th>
                <th style="background-color:#4CAF50; color:white; padding:10px; text-align:left;">Document Count</th>
              </tr>
            </thead>
            <tbody>
        `;

        data.topics.forEach((item) => {
          html += `
            <tr style="border-bottom:1px solid #ddd;">
              <td style="padding:10px;">${item.topic}</td>
              <td style="padding:10px; font-weight:bold;">${item.label || `Topic ${item.topic}`}</td>
              <td style="padding:10px;">${item.count || 'N/A'}</td>
            </tr>
          `;
        });

        html += `
            </tbody>
          </table>
        `;
      } else {
        html += `<p style="color:orange;">No topics generated.</p>`;
      }

      topicResultDiv.innerHTML = html;

      // === SISIPAN: simpan peta TopicID -> Label utk render groups selanjutnya ===
      window.topicIdToName = {};
      (data.topics || []).forEach(t => {
        window.topicIdToName[t.topic] = t.label || `Topic ${t.topic}`;
      });

      // === SISIPAN: tampilkan section Hierarchy & Research Groups ===
      const hierSec = document.getElementById("bertHierarchyAndGroups");
      if (hierSec) hierSec.style.display = "block";

      // === SISIPAN: auto-generate Research Groups (tanpa klik tombol) ===
      if (typeof generateResearchGroupsBert === "function") {
        generateResearchGroupsBert();
      }
    })
    .catch((error) => {
      console.error("Gagal generate topic:", error);
      topicResultDiv.innerHTML = `
        <div style="color:red;padding:10px;border:1px solid red;border-radius:5px;">
          <strong>Error:</strong> ${error.message || 'Gagal mengambil data topik.'}
        </div>
      `;
    });
}

// Function to populate dropdown with cluster options
function populateClusterDropdown(options) {
  const dropdown = document.getElementById("minClusterInput");
  if (!dropdown || !options || options.length === 0) {
    console.warn("No cluster options to populate or dropdown not found");
    return;
  }

  // Clear existing options
  dropdown.innerHTML = '';
  
  // Add default option
  const defaultOption = document.createElement('option');
  defaultOption.value = '';
  defaultOption.textContent = 'Pilih min_cluster_size';
  defaultOption.disabled = true;
  defaultOption.selected = true;
  dropdown.appendChild(defaultOption);
  
  // Add options from analysis results
  options.forEach(option => {
    const optionElement = document.createElement('option');
    optionElement.value = option;
    optionElement.textContent = option;
    dropdown.appendChild(optionElement);
  });
  
  console.log(`Populated dropdown with ${options.length} options:`, options);
}

// Updated BERTopic analysis function
function jalankanAnalisisBertopic(namaFile) {
  const hasilDiv = document.getElementById("hasilBertopic");
  const paramDiv = document.getElementById("parameterTerbaik");
  const containerDiv = document.getElementById("analisisBertopic");
  const clusterSizeSection = document.getElementById("pilihClusterSize");

  // Store filename for later use
  currentFilename = namaFile;

  // Tampilkan loading
  hasilDiv.innerHTML = `
    <div style="text-align:center;padding:20px;">
      <p>Memproses analisis BERTopic...</p>
      <div class="loader"></div>
    </div>
  `;

  fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `filename=${encodeURIComponent(namaFile)}&metode=bertopic`,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        hasilDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
        return;
      }

      console.log("Received data:", data);

      // Display plot
      hasilDiv.innerHTML = data.plot_html;

      // Execute scripts in the plot HTML
      const scripts = hasilDiv.querySelectorAll('script');
      console.log("Found scripts:", scripts.length);

      // Eksekusi setiap script
      scripts.forEach((oldScript, index) => {
        const newScript = document.createElement('script');
        
        if (oldScript.src) {
          newScript.src = oldScript.src;
          console.log(`Loading external script ${index}:`, oldScript.src);
        } else {
          newScript.textContent = oldScript.textContent;
          console.log(`Executing inline script ${index}`);
        }

        // Replace script lama dengan yang baru
        oldScript.parentNode.replaceChild(newScript, oldScript);
      });

      // Tampilkan parameter
      if (data.best_params) {
        paramDiv.innerHTML = `
          <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:15px 0;">
            <p><strong>Parameter Terbaik:</strong></p>
            <p><strong>min_cluster_size:</strong> ${data.best_params.min_cluster_size}</p>
            <p><strong>Coherence Score:</strong> ${parseFloat(data.best_params.coherence_score).toFixed(4)}</p>
          </div>
        `;
      }

      // Populate cluster dropdown with options from analysis
      if (data.cluster_options && data.cluster_options.length > 0) {
        clusterOptions = data.cluster_options;
        populateClusterDropdown(clusterOptions);
        
        // Show cluster selection section
        if (clusterSizeSection) {
          clusterSizeSection.style.display = 'block';
        }
      } else {
        console.warn("No cluster options received from server");
      }

      containerDiv.classList.add("active");

      // Debug check after 2 seconds
      setTimeout(() => {
        const plotDivs = hasilDiv.querySelectorAll('.plotly-graph-div');
        console.log("Plot divs found:", plotDivs.length);
        
        if (plotDivs.length > 0) {
          plotDivs.forEach((div, i) => {
            console.log(`Plot div ${i}:`, div.id, div.style.width, div.style.height);
          });
        } else {
          console.error("No plot divs found after script execution!");
        }
      }, 2000);
    })
    .catch((error) => {
      console.error("Error:", error);
      hasilDiv.innerHTML = `<p style="color:red;">Terjadi kesalahan: ${error.message}</p>`;
    });
}

// Make function available globally
window.generateTopikDenganLabel = generateTopikDenganLabel;

function jalankanAnalisisKeyword(namaFile) {
  const hasilDiv = document.getElementById("hasilKeyword");
  const containerDiv = document.getElementById("analisisKeyword");
  const chartImg = document.getElementById("topFieldsChartImg");
  const clusterSelector = document.getElementById("clusterSelector");
  const recommendationCard = document.querySelector(".recommendation-card");
  const fundamentalGroupsList = document.querySelector(".fundamental-groups-list");

  // Simpan nama file untuk digunakan lagi kalau perlu
  currentFilename = namaFile;

  // Tampilkan loading
  if (hasilDiv) {
    hasilDiv.innerHTML = `
      <div style="text-align:center;padding:20px;">
        <p>Memproses analisis Keyword Matching...</p>
        <div class="loader"></div>
      </div>
    `;
  }

  // Reset tampilan
  if (chartImg) chartImg.style.display = "none";
  if (recommendationCard) recommendationCard.innerHTML = "";
  if (fundamentalGroupsList) fundamentalGroupsList.innerHTML = "";

  fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `filename=${encodeURIComponent(namaFile)}&metode=keyword`,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        if (hasilDiv) {
          hasilDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
        }
        return;
      }

      console.log("Hasil Keyword Matching:", data);

      // Tampilkan chart base64 di img element
      if (data.chart && chartImg) {
        chartImg.src = `data:image/png;base64,${data.chart}`;
        chartImg.style.display = "block";
      }

      // Tampilkan grouped result jika ada
      if (data.grouped && recommendationCard) {
        displayGroupedResults(data.grouped);
      }

      // Clear hasil div jika ada
      if (hasilDiv) {
        hasilDiv.innerHTML = "";
      }

      // Aktifkan container
      containerDiv.classList.add("active");

      // Setup event listener untuk dropdown cluster
      setupClusterSelector(namaFile);
    })
    .catch((error) => {
      console.error("Error:", error);
      if (hasilDiv) {
        hasilDiv.innerHTML = `<p style="color:red;">Terjadi kesalahan: ${error.message}</p>`;
      }
    });
}

function setupClusterSelector(filename) {
  const clusterSelector = document.getElementById("clusterSelector");
  
  if (clusterSelector) {
    // Remove existing event listeners
    clusterSelector.replaceWith(clusterSelector.cloneNode(true));
    const newClusterSelector = document.getElementById("clusterSelector");
    
    newClusterSelector.addEventListener("change", function() {
      const numGroups = parseInt(this.value);
      generateGroups(filename, numGroups);
    });

    // Generate default groups (5)
    generateGroups(filename, 5);
  }
}

function generateGroups(filename, numGroups) {
  const recommendationCard = document.querySelector(".recommendation-card");
  const fundamentalGroupsList = document.querySelector(".fundamental-groups-list");

  // Show loading
  if (recommendationCard) {
    recommendationCard.innerHTML = `
      <div style="text-align:center;padding:10px;">
        <p>Mengelompokkan bidang ilmu...</p>
        <div class="loader" style="width:20px;height:20px;"></div>
      </div>
    `;
  }

  fetch("/generate_groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: filename,
      num_groups: numGroups
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        if (recommendationCard) {
          recommendationCard.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
        }
        return;
      }

      console.log("Generated Groups:", data);
      displayGroupedResults(data.groups);
    })
    .catch(error => {
      console.error("Error generating groups:", error);
      if (recommendationCard) {
        recommendationCard.innerHTML = `<p style="color:red;">Terjadi kesalahan: ${error.message}</p>`;
      }
    });
}

function displayGroupedResults(groups) {
  const recommendationCard = document.querySelector(".recommendation-card");
  const fundamentalGroupsList = document.querySelector(".fundamental-groups-list");

  // Handle different response formats (array of objects vs string)
  let parsedGroups = groups;
  if (typeof groups === 'string') {
    try {
      parsedGroups = JSON.parse(groups);
    } catch (e) {
      console.warn("Could not parse groups as JSON, treating as string");
      if (recommendationCard) {
        recommendationCard.innerHTML = `
          <div class="text-response">
            <h4>Hasil Pengelompokan:</h4>
            <pre style="white-space: pre-wrap; font-family: Arial; font-size: 14px;">${groups}</pre>
          </div>
        `;
      }
      if (fundamentalGroupsList) {
        fundamentalGroupsList.innerHTML = "";
      }
      return;
    }
  }

  if (!parsedGroups || !Array.isArray(parsedGroups) || parsedGroups.length === 0) {
    if (recommendationCard) {
      recommendationCard.innerHTML = `<p>Tidak ada hasil pengelompokan yang ditemukan.</p>`;
    }
    return;
  }

  // Display summary in recommendation card
  if (recommendationCard) {
    const totalFields = parsedGroups.reduce((total, group) => {
      return total + (group.fields && Array.isArray(group.fields) ? group.fields.length : 0);
    }, 0);

    recommendationCard.innerHTML = `
      <div class="summary-stats">
        <div class="stat-item">
          <span class="stat-number">${parsedGroups.length}</span>
          <span class="stat-label">Kelompok Riset</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">${totalFields}</span>
          <span class="stat-label">Total Bidang</span>
        </div>
      </div>
      <p class="summary-text">Hasil pengelompokan bidang ilmu berdasarkan kesamaan topik dan fokus penelitian.</p>
    `;
  }

  // Display detailed groups
  if (fundamentalGroupsList) {
    let groupsHtml = "";
    
    parsedGroups.forEach((group, index) => {
      const fieldsHtml = group.fields && Array.isArray(group.fields) 
        ? group.fields.map(field => `<span class="field-tag">${field}</span>`).join(" ")
        : "<span class='field-tag'>Tidak ada bidang</span>";

      groupsHtml += `
        <div class="group-card">
          <div class="group-header">
            <h4 class="group-title">${group.name || `Kelompok ${index + 1}`}</h4>
            <span class="field-count">${group.fields ? group.fields.length : 0} bidang</span>
          </div>
          <div class="group-description">
            <p>${group.description || "Deskripsi tidak tersedia"}</p>
          </div>
          <div class="group-fields">
            ${fieldsHtml}
          </div>
        </div>
      `;
    });

    fundamentalGroupsList.innerHTML = groupsHtml;
  }
}

// Initialize Application
document.addEventListener("DOMContentLoaded", function() {
  console.log("Research Intelligence App initialized");
  
  // Load files if on upload page
  if (pages.upload && pages.upload.style.display !== 'none') {
    loadFilesFromServer();
  }
  
  // Initialize default analysis slide
  showAnalisisSlide('default');

});

function buildHierarchyBertDefault() {
  const plotDiv = document.getElementById("bertHierarchyPlot");
  if (!currentFilename) { alert("Jalankan BERTopic dulu."); return; }
  plotDiv.innerHTML = `<div style="text-align:center;padding:10px;"><p>Membangun hierarchy…</p><div class="loader"></div></div>`;
  fetch("/bert_hierarchy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: currentFilename,
      linkage_method: "ward",
      optimal_ordering: true
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) { plotDiv.innerHTML = `<p style="color:red;">${data.error}</p>`; return; }
    plotDiv.innerHTML = data.plot_html;
    const scripts = plotDiv.querySelectorAll("script");
    scripts.forEach(s => { const n = document.createElement("script"); if (s.src) n.src = s.src; else n.textContent = s.textContent; s.parentNode.replaceChild(n, s); });
  })
  .catch(err => { plotDiv.innerHTML = `<p style="color:red;">${err.message}</p>`; });
}

function generateResearchGroupsBertDefault() {
  const outDiv = document.getElementById("bertGroupsResult");
  if (!currentFilename) { alert("Jalankan BERTopic dulu."); return; }
  outDiv.innerHTML = `<div style="text-align:center;padding:10px;"><p>Mengelompokkan topik…</p><div class="loader"></div></div>`;
  fetch("/bert_research_groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: currentFilename,
      // default yg “bagus umum”
      color_threshold: 1.0,
      linkage_method: "ward",
      optimal_ordering: true,
      distance: "cosine",
      use_ctfidf: true,
      max_name_words: 4
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) { outDiv.innerHTML = `<p style="color:red;">${data.error}</p>`; return; }

    // tampilkan MARKDOWN + tabel yang memuat LABEL topik (BUKAN representation)
    let html = `<h4 style="margin:10px 0;">${data.group_count} Research Groups</h4>`;
    html += `<pre style="white-space:pre-wrap;background:#fafafa;border:1px solid #eee;padding:12px;border-radius:8px;">${data.markdown}</pre>`;

    if (data.groups && data.groups.length) {
      html += `
        <table style="width:100%;border-collapse:collapse;margin-top:10px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">Group ID</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">Group Name</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">#Topics</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">Topic IDs</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">Topic Labels</th>
            </tr>
          </thead>
          <tbody>
      `;
      data.groups.forEach(g => {
        const labels = (g.topic_labels || []).map(t => `<span style="display:inline-block;margin:2px 6px 2px 0;padding:4px 8px;border:1px solid #e5e7eb;border-radius:999px;background:#f9fafb;">${t}</span>`).join("");
        html += `
          <tr>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;">${g.research_group}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;font-weight:bold;">${g.group_name}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;">${g.n_topics}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;">${(g.topics || []).join(", ")}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;">${labels}</td>
          </tr>
        `;
      });
      html += `</tbody></table>`;
    }
    outDiv.innerHTML = html;
  })
  .catch(err => { outDiv.innerHTML = `<p style="color:red;">${err.message}</p>`; });
}

// optional: auto-run setelah sukses /generate_topics
// panggil generateResearchGroupsBertDefault() dari .then() di generateTopikDenganLabel jika mau otomatis


function generateResearchGroupsBert() {
  const outDiv = document.getElementById("bertGroupsResult");
  if (!currentFilename) {
    alert("Jalankan analisis BERTopic terlebih dahulu.");
    return;
  }

  outDiv.innerHTML = `
    <div style="text-align:center;padding:10px;">
      <p>Mengelompokkan topik menjadi Research Groups…</p>
      <div class="loader"></div>
    </div>`;

  fetch("/bert_research_groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: currentFilename,
      color_threshold: 1.0,
      linkage_method: "ward",
      optimal_ordering: true,
      distance: "cosine",
      use_ctfidf: true,
      max_name_words: 4
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      outDiv.innerHTML = `<p style="color:red;">${data.error}</p>`;
      return;
    }

    // ---- HANYA TABEL (tanpa markdown/heading jumlah grup) ----
    const rows = (data.groups || []).map(g => {
      const ids = (g.topics || []).join(", ");

      // pakai label dari backend; kalau kosong fallback ke map hasil generate_topics
      const labelArr = (g.topic_labels && g.topic_labels.length)
        ? g.topic_labels
        : (g.topics || []).map(id => (window.topicIdToName && window.topicIdToName[id]) ? window.topicIdToName[id] : `Topic ${id}`);

      // gabungkan label jadi satu string
      const labels = labelArr.join(", ");

      return `
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:10px;">${g.research_group}</td>
          <td style="padding:10px;font-weight:600;">${g.group_name}</td>
          <td style="padding:10px;">${g.n_topics}</td>
          <td style="padding:10px;">${ids}</td>
          <td style="padding:10px;white-space:normal;word-wrap:break-word;">${labels}</td>
        </tr>
      `;
    }).join("");

    const table = `
      <table style="width:100%;border-collapse:collapse;margin-top:8px;">
        <thead>
          <tr>
            <th style="text-align:left;padding:10px;border-bottom:2px solid #ddd;">Group ID</th>
            <th style="text-align:left;padding:10px;border-bottom:2px solid #ddd;">Group Name</th>
            <th style="text-align:left;padding:10px;border-bottom:2px solid #ddd;">#Topics</th>
            <th style="text-align:left;padding:10px;border-bottom:2px solid #ddd;">Topic IDs</th>
            <th style="text-align:left;padding:10px;border-bottom:2px solid #ddd;">Topic Labels</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    outDiv.innerHTML = table; // <- tidak render data.markdown sama sekali
  })
  .catch(err => {
    outDiv.innerHTML = `<p style="color:red;">${err.message}</p>`;
  });
}

// expose
window.buildHierarchyBert = buildHierarchyBert;
window.generateResearchGroupsBert = generateResearchGroupsBert;
