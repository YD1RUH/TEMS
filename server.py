import http.server
import socketserver
import json
import csv
import os
import datetime
import threading
import urllib.parse
from http.server import ThreadingHTTPServer

# Konfigurasi Server
PORT = 8000
CSV_FILE = "sensor_data.csv"
VIB_THRESHOLD = 50 # Tambahkan variabel batas getaran di sisi backend
# Ubah struktur DATA_STORE untuk menyimpan history dan logs
DATA_STORE = {"sensors": {}, "logs": [], "alert_logs": []} # Tambahkan alert_logs
DATA_LOCK = threading.Lock() # Mencegah data rusak karena diakses bersamaan

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "ID", "Latitude", "Longitude", "Vibration"])
else:
    # Load data histori dari CSV saat server dimulai
    print(f"Memuat data histori dari {CSV_FILE}...")
    try:
        with open(CSV_FILE, mode='r') as file:
            # Gunakan DictReader agar mudah membaca berdasar nama kolom
            reader = csv.DictReader(file)
            all_rows = list(reader)
            
            for row in all_rows:
                try:
                    s_id = row["ID"]
                    s_lat = float(row["Latitude"])
                    s_long = float(row["Longitude"])
                    s_vib = float(row["Vibration"])
                    
                    # Ambil jam:menit:detik dari format YYYY-MM-DD HH:MM:SS
                    timestamp_str = row["Timestamp"]
                    timestamp_short = timestamp_str.split(" ")[1] if " " in timestamp_str else timestamp_str

                    # 0. Kumpulkan semua log yang melebihi threshold untuk fitur filter All-Time
                    if s_vib > VIB_THRESHOLD:
                        DATA_STORE["alert_logs"].append({
                            "time": timestamp_short, 
                            "id": s_id, 
                            "vib": s_vib
                        })

                    # 1. Update data grafik (maksimal 30 titik per sensor)
                    if s_id not in DATA_STORE["sensors"]:
                        DATA_STORE["sensors"][s_id] = {"lat": s_lat, "long": s_long, "history": []}
                    
                    # Perbarui posisi lintang/bujur terbaru
                    DATA_STORE["sensors"][s_id]["lat"] = s_lat
                    DATA_STORE["sensors"][s_id]["long"] = s_long
                    DATA_STORE["sensors"][s_id]["history"].append({"time": timestamp_short, "vib": s_vib})
                    
                    if len(DATA_STORE["sensors"][s_id]["history"]) > 30:
                        DATA_STORE["sensors"][s_id]["history"].pop(0)

                except (ValueError, KeyError):
                    continue # Abaikan baris jika data kosong atau formatnya salah

            # Balik urutan alert agar yang terbaru ada di atas
            DATA_STORE["alert_logs"].reverse()

            # 2. Update data logs tabel (maksimal 100 baris terbaru)
            latest_100_rows = all_rows[-100:]
            for row in reversed(latest_100_rows): # Di-reverse agar data paling baru ada di urutan paling atas (index 0)
                try:
                    timestamp_str = row["Timestamp"]
                    timestamp_short = timestamp_str.split(" ")[1] if " " in timestamp_str else timestamp_str
                    DATA_STORE["logs"].append({
                        "time": timestamp_short, 
                        "id": row["ID"], 
                        "vib": float(row["Vibration"])
                    })
                except (ValueError, KeyError):
                    pass
    except Exception as e:
        print(f"Gagal memuat riwayat data: {e}")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tactical Earthquake Dashboard</title>
    <script src="https://cesium.com/downloads/cesiumjs/releases/1.105/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.105/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        html, body { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; background: #111; color: #eee; display: flex; font-family: sans-serif; }
        #cesiumContainer { flex-grow: 1; position: relative; height: 100vh; }
        #infoPanel { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); color: white; padding: 15px; border-radius: 8px; z-index: 100; border: 1px solid #444; }
        
        /* Sidebar Layout */
        .sidebar { width: 320px; height: 100vh; background: #1a1a1a; display: flex; flex-direction: column; z-index: 10; border-right: 1px solid #333; }
        .sidebar-right { border-left: 1px solid #333; border-right: none; }
        .sidebar-header { padding: 15px; text-align: center; background: #222; border-bottom: 1px solid #333; margin: 0; font-size: 16px; font-weight: bold; }
        
        /* Search Box */
        .search-box { width: 90%; margin: 10px auto; padding: 8px; border-radius: 5px; border: 1px solid #444; background: #333; color: white; outline: none; display: block; box-sizing: border-box; }
        .search-box:focus { border-color: #00ff88; }
        
        /* Filter Button */
        .filter-btn { background: #333; border: 1px solid #444; color: white; padding: 0 10px; border-radius: 5px; cursor: pointer; font-size: 16px; transition: all 0.2s; }
        .filter-btn:hover { background: #444; }
        .filter-btn.active { background: rgba(255, 60, 60, 0.2); border-color: #ff5555; }
        
        .scrollable { flex-grow: 1; overflow-y: auto; padding: 10px; scrollbar-width: thin; scrollbar-color: #555 #1a1a1a; }
        
        /* Chart Styles */
        .chart-card { background: #252525; border-radius: 8px; padding: 10px; margin-bottom: 15px; border: 1px solid #333; cursor: pointer; transition: border-color 0.2s, background-color 0.2s; }
        .chart-card:hover { border-color: #00ff88; background-color: #2a2a2a; }
        .chart-title { margin: 0 0 10px 0; font-size: 14px; color: #00ff88; text-align: center; pointer-events: none; }
        
        /* Log Styles */
        .log-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
        .log-table th, .log-table td { padding: 8px 5px; border-bottom: 1px solid #333; }
        .log-table th { background: #2a2a2a; position: sticky; top: -10px; }
        .log-row-alert { background: rgba(255, 60, 60, 0.15); color: #ff5555; font-weight: bold; }

        /* Modal Heatmap */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.8); align-items: center; justify-content: center; }
        .modal.show { display: flex; }
        .modal-content { background-color: #0d1117; padding: 25px; border-radius: 8px; border: 1px solid #30363d; position: relative; max-width: 600px; color: #c9d1d9; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .close-btn { position: absolute; top: 15px; right: 20px; color: #8b949e; font-size: 24px; cursor: pointer; line-height: 1; }
        .close-btn:hover { color: #fff; }
        .modal-title { margin: 0 0 20px 0; font-size: 16px; color: #fff; font-weight: 600; }
        
        /* Heatmap Grid Layout */
        .heatmap-container { display: flex; flex-direction: column; gap: 5px; }
        .heatmap-x-axis { display: grid; grid-template-columns: repeat(24, 14px); gap: 3px; margin-left: 32px; font-size: 10px; color: #8b949e; text-align: center; }
        .heatmap-body { display: flex; gap: 10px; }
        .heatmap-y-axis { display: grid; grid-template-rows: repeat(6, 14px); gap: 3px; font-size: 10px; color: #8b949e; text-align: right; line-height: 14px; }
        .heatmap-grid { display: grid; grid-template-rows: repeat(6, 14px); grid-template-columns: repeat(24, 14px); gap: 3px; grid-auto-flow: column; }
        
        /* Heatmap Cells (GitHub Colors) */
        .heatmap-cell { width: 14px; height: 14px; border-radius: 2px; cursor: pointer; }
        .heatmap-cell:hover { outline: 1px solid #fff; z-index: 2; }
        .cell-0 { background-color: #161b22; }
        .cell-1 { background-color: #0e4429; }
        .cell-2 { background-color: #006d32; }
        .cell-3 { background-color: #26a641; }
        .cell-4 { background-color: #39d353; }
        .cell-alert { background-color: #da3633; } /* Red for Alert > 50 */
        
        /* Legend */
        .heatmap-legend { display: flex; justify-content: flex-end; align-items: center; gap: 5px; font-size: 11px; color: #8b949e; margin-top: 15px; }
        
        /* Tooltip */
        #tooltip { position: fixed; background: rgba(0,0,0,0.9); color: #fff; padding: 6px 10px; border-radius: 5px; font-size: 12px; pointer-events: none; z-index: 1001; display: none; border: 1px solid #444; white-space: nowrap; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .tooltip-time { color: #8b949e; margin-bottom: 3px; }
        .tooltip-val { font-weight: bold; color: #39d353; }
        .tooltip-val.alert { color: #da3633; }
    </style>
</head>
<body>
    <!-- Tooltip Element -->
    <div id="tooltip"></div>

    <!-- Sidebar Kiri: Grafik -->
    <div class="sidebar" id="leftSidebar">
        <h3 class="sidebar-header">Grafik Sensor</h3>
        <input type="text" id="searchLeft" class="search-box" placeholder="Cari ID Sensor...">
        <div id="chartContainer" class="scrollable"></div>
    </div>

    <!-- Tengah: Map 3D Cesium -->
    <div id="cesiumContainer">
        <div id="infoPanel">
            <h3 style="margin:0 0 5px 0;">Tactical Dashboard</h3>
            <p style="margin:0;">Status: <span id="status" style="color:#00ff88;">Menunggu data...</span></p>
        </div>
    </div>

    <!-- Sidebar Kanan: Time Series Logs -->
    <div class="sidebar sidebar-right" id="rightSidebar">
        <h3 class="sidebar-header">Log Time Series</h3>
        <div style="display: flex; gap: 5px; width: 90%; margin: 10px auto;">
            <input type="text" id="searchRight" class="search-box" placeholder="Cari ID / Waktu..." style="margin: 0; flex-grow: 1;">
            <button id="btnFilterAlert" class="filter-btn" title="Tampilkan hanya peringatan getaran tinggi">⚠️</button>
        </div>
        <div class="scrollable" style="padding: 0 10px;">
            <table class="log-table">
                <thead><tr><th>Waktu</th><th>ID</th><th>Vib</th></tr></thead>
                <tbody id="logBody"></tbody>
            </table>
        </div>
    </div>

    <!-- Modal Heatmap -->
    <div id="heatmapModal" class="modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeHeatmap()">&times;</span>
            <h3 class="modal-title" id="heatmapTitle">Aktivitas 24 Jam Terakhir</h3>
            <div class="heatmap-container">
                <div class="heatmap-x-axis" id="heatmapXAxis"></div>
                <div class="heatmap-body">
                    <div class="heatmap-y-axis">
                        <div>00m</div><div>10m</div><div>20m</div>
                        <div>30m</div><div>40m</div><div>50m</div>
                    </div>
                    <div class="heatmap-grid" id="heatmapGrid" onmousemove="moveTooltip(event)"></div>
                </div>
            </div>
            <div class="heatmap-legend">
                Aman 
                <div class="heatmap-cell cell-0"></div>
                <div class="heatmap-cell cell-1"></div>
                <div class="heatmap-cell cell-2"></div>
                <div class="heatmap-cell cell-3"></div>
                <div class="heatmap-cell cell-4"></div>
                <span style="margin: 0 5px;">|</span>
                Peringatan 
                <div class="heatmap-cell cell-alert"></div>
            </div>
        </div>
    </div>

    <script>
        // Menggunakan Token Cesium Ion Anda
        Cesium.Ion.defaultAccessToken = '#################### ganti token anda ##############################################';

        const viewer = new Cesium.Viewer('cesiumContainer', {
            terrainProvider: Cesium.createWorldTerrain(),
            baseLayerPicker: false,
            animation: false, 
            timeline: false,  
            geocoder: false   
        });

        viewer.camera.setView({
            destination: Cesium.Cartesian3.fromDegrees(118.0, -2.5, 5000000), 
            orientation: { heading: 0.0, pitch: Cesium.Math.toRadians(-90.0), roll: 0.0 }
        });
        
        let entities = {};
        let chartInstances = {};
        const VIB_THRESHOLD = 50;

        // Global variables state for live search
        let lastSensorsData = {};
        let lastLogsData = [];
        let lastAlertsData = []; // State khusus untuk semua history alert
        let showAlertsOnly = false;

        // Fitur Pencarian (Search)
        const searchLeft = document.getElementById('searchLeft');
        const searchRight = document.getElementById('searchRight');
        const btnFilterAlert = document.getElementById('btnFilterAlert');
        const tooltip = document.getElementById('tooltip');
        
        searchLeft.addEventListener('input', () => updateCharts(lastSensorsData));
        searchRight.addEventListener('input', () => updateLogs());
        
        // Fitur Toggle Filter Button
        btnFilterAlert.addEventListener('click', () => {
            showAlertsOnly = !showAlertsOnly;
            btnFilterAlert.classList.toggle('active', showAlertsOnly);
            updateLogs(); // Refresh data tabel
        });

        function updateCharts(sensorsData) {
            const container = document.getElementById('chartContainer');
            const filter = searchLeft.value.toLowerCase();

            for (const id in sensorsData) {
                if (filter && !id.toLowerCase().includes(filter)) {
                    if (document.getElementById(`chart-card-${id}`)) {
                        document.getElementById(`chart-card-${id}`).style.display = 'none';
                    }
                    continue;
                }

                const sensor = sensorsData[id];
                let card = document.getElementById(`chart-card-${id}`);
                
                if (!card) {
                    // Buat Canvas Chart Baru
                    card = document.createElement('div');
                    card.className = 'chart-card';
                    card.id = `chart-card-${id}`;
                    card.title = "Klik untuk melihat Heatmap 24 Jam";
                    card.onclick = () => openHeatmap(id); // Event klik untuk buka modal Heatmap
                    
                    const title = document.createElement('h4');
                    title.className = 'chart-title';
                    title.innerText = `Sensor: ${id}`;
                    
                    const canvas = document.createElement('canvas');
                    canvas.id = `canvas-${id}`;
                    
                    card.appendChild(title);
                    card.appendChild(canvas);
                    container.appendChild(card);

                    // Konfigurasi Chart.js
                    const ctx = canvas.getContext('2d');
                    chartInstances[id] = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{ label: 'Getaran', data: [], borderColor: '#00ff88', backgroundColor: 'rgba(0, 255, 136, 0.1)', borderWidth: 2, fill: true, tension: 0.4, pointRadius: 1 }]
                        },
                        options: {
                            responsive: true,
                            animation: false,
                            plugins: { legend: { display: false }, tooltip: { enabled: false } },
                            scales: {
                                x: { display: true, ticks: { color: '#888', font: {size: 10} } },
                                y: { display: true, min: 0, max: 100, ticks: { color: '#888' } }
                            },
                            interaction: { mode: 'index', intersect: false }
                        }
                    });
                }

                card.style.display = 'block';

                // Update data grafik
                const chart = chartInstances[id];
                chart.data.labels = sensor.history.map(h => h.time);
                chart.data.datasets[0].data = sensor.history.map(h => h.vib);
                
                const latestVib = sensor.history.length > 0 ? sensor.history[sensor.history.length - 1].vib : 0;
                
                // Ubah warna merah jika melebihi threshold
                if (latestVib > VIB_THRESHOLD) {
                    chart.data.datasets[0].borderColor = '#ff5555';
                    chart.data.datasets[0].backgroundColor = 'rgba(255, 85, 85, 0.2)';
                    card.querySelector('.chart-title').style.color = '#ff5555';
                } else {
                    chart.data.datasets[0].borderColor = '#00ff88';
                    chart.data.datasets[0].backgroundColor = 'rgba(0, 255, 136, 0.1)';
                    card.querySelector('.chart-title').style.color = '#00ff88';
                }
                chart.update();
            }
        }

        function updateLogs() {
            const tbody = document.getElementById('logBody');
            const filter = searchRight.value.toLowerCase();
            tbody.innerHTML = ''; 
            
            // Gunakan array alert semua waktu jika filter aktif, atau 100 log terbaru jika tidak
            const dataSource = showAlertsOnly ? lastAlertsData : lastLogsData;
            
            dataSource.forEach(log => {
                const isAlert = log.vib > VIB_THRESHOLD;

                if (filter && !log.id.toLowerCase().includes(filter) && !log.time.includes(filter)) {
                    return; // Skip filter teks
                }
                
                const tr = document.createElement('tr');
                if (isAlert) tr.className = 'log-row-alert';
                
                tr.innerHTML = `<td>${log.time}</td><td>${log.id}</td><td>${log.vib}</td>`;
                tbody.appendChild(tr);
            });
        }

        // ==========================================
        // Logika Interaksi Heatmap Github Style
        // ==========================================
        async function openHeatmap(sensorId) {
            const modal = document.getElementById('heatmapModal');
            document.getElementById('heatmapTitle').innerText = `Aktivitas 24 Jam Terakhir: ${sensorId}`;
            modal.classList.add('show');
            
            // Tampilkan state memuat data
            const grid = document.getElementById('heatmapGrid');
            grid.innerHTML = '<div style="color: #888; grid-column: span 24; padding: 20px;">Mengambil history 24 Jam...</div>';
            
            try {
                // Panggil Endpoint API khusus Heatmap
                const response = await fetch(`/api/heatmap?id=${encodeURIComponent(sensorId)}`);
                const data = await response.json();
                renderHeatmap(data);
            } catch (err) {
                grid.innerHTML = '<div style="color: #ff5555; grid-column: span 24;">Gagal memuat data Heatmap.</div>';
            }
        }

        function closeHeatmap() {
            document.getElementById('heatmapModal').classList.remove('show');
            hideTooltip();
        }

        function renderHeatmap(data) {
            // Render X-Axis Label (0, 3, 6, 9... 21)
            const xAxisGrid = document.getElementById('heatmapXAxis');
            let xAxisHtml = '';
            for (let h = 0; h < 24; h++) {
                if (h % 3 === 0) {
                    xAxisHtml += `<div>${h.toString().padStart(2, '0')}</div>`;
                } else {
                    xAxisHtml += `<div></div>`;
                }
            }
            xAxisGrid.innerHTML = xAxisHtml;

            // Render 144 Kotak (24 Kolom Jam x 6 Baris 10-Menitan)
            // Karena grid-auto-flow: column, urutan loop: Kolom(Jam) -> Baris(Menit)
            const grid = document.getElementById('heatmapGrid');
            let gridHtml = '';
            for (let h = 0; h < 24; h++) {
                for (let m = 0; m < 6; m++) {
                    const key = `${h.toString().padStart(2, '0')}-${m}`;
                    const vib = data[key] || 0;
                    
                    let colorClass = 'cell-0';
                    if (vib >= VIB_THRESHOLD) colorClass = 'cell-alert';
                    else if (vib > 30) colorClass = 'cell-4';
                    else if (vib > 20) colorClass = 'cell-3';
                    else if (vib > 10) colorClass = 'cell-2';
                    else if (vib > 0)  colorClass = 'cell-1';

                    const timeStr = `Jam ${h.toString().padStart(2, '0')}:${m}0 - ${h.toString().padStart(2, '0')}:${m}9`;
                    
                    gridHtml += `<div class="heatmap-cell ${colorClass}" 
                                      data-time="${timeStr}" 
                                      data-vib="${vib}" 
                                      onmouseover="showTooltip(event, this)" 
                                      onmouseout="hideTooltip()"></div>`;
                }
            }
            grid.innerHTML = gridHtml;
        }

        function showTooltip(e, element) {
            const time = element.getAttribute('data-time');
            const vib = parseFloat(element.getAttribute('data-vib'));
            const isAlert = vib >= VIB_THRESHOLD;
            
            tooltip.innerHTML = `
                <div class="tooltip-time">${time}</div>
                <div>Max Getaran: <span class="tooltip-val ${isAlert ? 'alert' : ''}">${vib.toFixed(1)}</span></div>
            `;
            tooltip.style.display = 'block';
            tooltip.style.left = (e.pageX + 15) + 'px';
            tooltip.style.top = (e.pageY + 15) + 'px';
        }

        function hideTooltip() {
            tooltip.style.display = 'none';
        }

        function moveTooltip(e) {
            if(tooltip.style.display === 'block') {
                tooltip.style.left = (e.pageX + 15) + 'px';
                tooltip.style.top = (e.pageY + 15) + 'px';
            }
        }

        // ==========================================
        // Polling Data Real-Time
        // ==========================================
        setInterval(async () => {
            try {
                const response = await fetch('/data');
                const data = await response.json();
                
                lastSensorsData = data.sensors || {};
                lastLogsData = data.logs || [];
                lastAlertsData = data.alert_logs || []; // Ambil dari backend
                
                document.getElementById('status').innerText = "Terhubung - Memantau " + Object.keys(lastSensorsData).length + " Titik";
                
                updateCharts(lastSensorsData);
                updateLogs();
                
                for (const id in lastSensorsData) {
                    const sensor = lastSensorsData[id];
                    const latestVib = sensor.history.length > 0 ? sensor.history[sensor.history.length-1].vib : 0;
                    const isAlert = latestVib > VIB_THRESHOLD;
                    const pointColor = isAlert ? Cesium.Color.RED : Cesium.Color.LIMEGREEN;
                    
                    if (!entities[id]) {
                        entities[id] = viewer.entities.add({
                            id: id,
                            position: Cesium.Cartesian3.fromDegrees(sensor.long, sensor.lat),
                            point: { pixelSize: 20, color: pointColor, outlineColor: Cesium.Color.WHITE, outlineWidth: 2 },
                            label: { text: id + '\\nGetaran: ' + latestVib, font: '14pt sans-serif', style: Cesium.LabelStyle.FILL_AND_OUTLINE, outlineWidth: 2, verticalOrigin: Cesium.VerticalOrigin.BOTTOM, pixelOffset: new Cesium.Cartesian2(0, -15) }
                        });
                        entities[id].isAlerting = false;
                    } else {
                        entities[id].position = Cesium.Cartesian3.fromDegrees(sensor.long, sensor.lat);
                        entities[id].point.color = pointColor;
                        entities[id].label.text = id + '\\nGetaran: ' + latestVib;
                    }

                    if (isAlert && !entities[id].isAlerting) {
                        viewer.flyTo(entities[id], { duration: 2.0, offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), 5000) });
                        entities[id].isAlerting = true;
                    } else if (!isAlert) {
                        entities[id].isAlerting = false;
                    }
                }
            } catch (err) {
                console.error("Gagal mengambil data", err);
            }
        }, 2000); // Polling setiap 2 detik
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
        elif parsed_path.path == '/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            with DATA_LOCK: # Kunci saat membaca agar aman
                self.wfile.write(json.dumps(DATA_STORE).encode('utf-8'))
                
        # Endpoint API baru khusus membuat data grafik Heatmap 24 Jam
        elif parsed_path.path == '/api/heatmap':
            query = urllib.parse.parse_qs(parsed_path.query)
            s_id = query.get('id', [''])[0]
            
            heatmap_data = {}
            try:
                now = datetime.datetime.now()
                start_time = now - datetime.timedelta(hours=24) # Filter hanya 24 jam terakhir
                
                with DATA_LOCK:
                    # Buka dan pindai CSV
                    if os.path.exists(CSV_FILE):
                        with open(CSV_FILE, mode='r') as file:
                            reader = csv.DictReader(file)
                            for row in reader:
                                if row.get("ID") == s_id:
                                    try:
                                        dt = datetime.datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")
                                        # Jika timestamp ada di rentang 24 jam terakhir
                                        if dt >= start_time:
                                            h = dt.hour
                                            m_bucket = dt.minute // 10 # Bagi menit menjadi bucket per 10 menit (0-5)
                                            vib = float(row["Vibration"])
                                            
                                            # Key format: 'HH-M_bucket' (e.g., '14-3' untuk 14:30 hingga 14:39)
                                            key = f"{h:02d}-{m_bucket}"
                                            
                                            # Kita simpan nilai getaran maksimum dalam interval 10 menit tersebut
                                            if key not in heatmap_data or vib > heatmap_data[key]:
                                                heatmap_data[key] = vib
                                    except Exception:
                                        pass
            except Exception as e:
                print(f"Error memuat heatmap: {e}")
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(heatmap_data).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == '/api/data':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                s_id = payload.get("id", "UNKNOWN")
                s_lat = float(payload.get("lat", 0.0))
                s_long = float(payload.get("long", 0.0))
                s_vib = float(payload.get("vib", 0.0))
                
                timestamp_full = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                timestamp_short = datetime.datetime.now().strftime("%H:%M:%S")

                with DATA_LOCK: # Kunci RAM dan File saat menulis data baru
                    # 1. Update Cache RAM Sensors (Histori untuk Line Chart)
                    if s_id not in DATA_STORE["sensors"]:
                        DATA_STORE["sensors"][s_id] = {"lat": s_lat, "long": s_long, "history": []}
                    
                    DATA_STORE["sensors"][s_id]["lat"] = s_lat
                    DATA_STORE["sensors"][s_id]["long"] = s_long
                    DATA_STORE["sensors"][s_id]["history"].append({"time": timestamp_short, "vib": s_vib})
                    
                    # Batasi history maksimal 30 titik chart agar UI tidak lemot
                    if len(DATA_STORE["sensors"][s_id]["history"]) > 30:
                        DATA_STORE["sensors"][s_id]["history"].pop(0)

                    # 2. Update Cache RAM Logs (Untuk tabel Time Series kanan)
                    DATA_STORE["logs"].insert(0, {"time": timestamp_short, "id": s_id, "vib": s_vib})
                    
                    # Batasi log maksimal 100 baris terbaru
                    if len(DATA_STORE["logs"]) > 100:
                        DATA_STORE["logs"].pop()
                    
                    # 2.5 Simpan log alert ke list khusus (semua history tanpa dibatasi 100)
                    if s_vib > VIB_THRESHOLD:
                        DATA_STORE["alert_logs"].insert(0, {"time": timestamp_short, "id": s_id, "vib": s_vib})

                    # 3. Simpan ke CSV Utama
                    with open(CSV_FILE, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([timestamp_full, s_id, s_lat, s_long, s_vib])

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                print(f"Error parsing data: {e}")
        else:
            self.send_response(404)
            self.end_headers()

# Gunakan ThreadingHTTPServer agar server tidak single-threaded (anti freeze)
with ThreadingHTTPServer(("", PORT), DashboardHandler) as httpd:
    print(f"🚀 Server Tactical Dashboard berjalan di port {PORT} (Multi-Threaded)")
    print(f"Buka browser dan akses: http://localhost:{PORT}")
    httpd.serve_forever()
