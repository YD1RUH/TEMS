# 🌍 Tactical Earthquake Monitoring System (Proyek UTS)

Sebuah sistem pemantauan gempa bumi / aktivitas seismik taktis berbasis **Internet of Things (IoT)** menggunakan teknologi komunikasi **LoRa**, **Python**, dan visualisasi **Peta 3D Cesium**.

Sistem ini dirancang untuk mendeteksi getaran di lokasi-lokasi terpencil menggunakan node sensor jarak jauh (LoRa), mengumpulkannya di satu Gateway, dan memvisualisasikannya secara *real-time* ke dalam sebuah *Command Center Dashboard* berbasis web dengan peta satelit kontur 3D.

## ✨ Fitur Utama

* **📡 Komunikasi LoRa Jarak Jauh:** Menggunakan modul TTGO LoRa32 untuk mengirim data getaran dari area tanpa sinyal internet ke Gateway lokal.

* **🗺️ Pemetaan 3D Cesium:** Visualisasi titik sensor di atas globe satelit 3D dengan kontur medan (*terrain*) yang berfokus di wilayah Indonesia.

* **🚨 Sistem Peringatan Taktis:** Jika getaran melebihi ambang batas (Threshold > 50), titik sensor di peta akan berubah menjadi **MERAH** dan kamera 3D akan otomatis melakukan *zoom / flyTo* ke lokasi tersebut.

* **📈 Real-Time Line Chart:** Grafik riwayat getaran langsung untuk masing-masing titik sensor (menggunakan Chart.js).

* **🟩 Heatmap 24-Jam (GitHub Style):** Klik pada panel sensor untuk melihat pop-up riwayat getaran selama 24 jam terakhir dengan tampilan *heatmap* interaktif mirip grafik kontribusi GitHub.

* **🗄️ Local CSV Logging:** Data disimpan dengan aman di `sensor_data.csv`. Jika server di-*restart*, data grafik dan riwayat tidak akan hilang.

* **⚙️ Konfigurasi Web Lokal (AP Mode):** Node sensor memancarkan WiFi Access Point untuk memudahkan pengaturan ID Sensor, Latitude, dan Longitude langsung dari HP saat instalasi di lapangan (tersimpan di *Flash Memory*).

## 🏗️ Arsitektur Sistem

1. **Node Sensor (SW-420 + TTGO LoRa):** Mendeteksi getaran tanah, menampilkannya di layar OLED, dan memancarkan data secara nirkabel via LoRa.

2. **Gateway (TTGO LoRa):** Bertindak sebagai penerima sinyal LoRa dari banyak titik sensor, lalu meneruskannya ke Server Lokal melalui koneksi WiFi/TCP (HTTP POST).

3. **Python HTTP Server:** Server *multi-threaded* ringan yang memproses data, menyimpannya ke dalam file CSV, dan menyajikan UI antarmuka Web Dashboard.

4. **Tactical Dashboard:** Antarmuka web diakses via *browser* untuk visualisasi komprehensif.

## 📦 Struktur Repositori

| File | Deskripsi | 
| ----- | ----- | 
| `server.py` | Script backend Python (HTTP Server, CSV Logger, dan HTML UI Dashboard terintegrasi). | 
| `sensor.ino` | Firmware untuk Node Sensor (membaca SW-420, Web Config, Transmisi LoRa). | 
| `gateway.ino` | Firmware untuk Node Gateway (Penerima LoRa ke WiFi HTTP POST). | 
| `sensor_dummy.ino` | Firmware ESP32 *Dummy* untuk mensimulasikan sensor (menghasilkan angka getaran acak). | 
| `sensor_dummy.py` | Script Python *Dummy* untuk mengirim data simulasi langsung ke server via TCP/IP dari PC. | 

## 🛠️ Perangkat Keras yang Dibutuhkan

* **Board:** LILYGO® TTGO LoRa32 V2.1_1.6 (ESP32 + LoRa SX1276 + OLED 0.96") - *Dibutuhkan minimal 2 buah (1 untuk Sensor, 1 untuk Gateway)*.

* **Sensor:** Modul Sensor Getaran SW-420.

* **Lainnya:** Kabel jumper, power supply / baterai 18650.

**Skema Pinout (Default Node Sensor):**

* SW-420 `DO` -> ESP32 Pin `13`
* SW-420 `VCC` -> `3.3V`
* SW-420 `GND` -> `GND`

## 🚀 Cara Instalasi & Penggunaan

### Menjalankan Server & Dashboard (Python)

1. Pastikan **Python 3** sudah terinstal di komputer Anda.
2. Clone repositori ini.
3. Buka terminal/command prompt di dalam folder proyek, lalu jalankan:
   ```bash
   python server.py
   ```
4. Buka peramban (browser) dan akses alamat: `http://localhost:8000`
5. *(Opsional)* Jika peta 3D tidak muncul atau Anda ingin menggunakan peta resolusi tinggi, ganti `Cesium.Ion.defaultAccessToken` di dalam file `server.py` dengan token Cesium Anda sendiri.

### Mengatur Node Gateway

1. Buka file `gateway.ino` menggunakan Arduino IDE.
2. Sesuaikan konfigurasi WiFi lokal Anda:
   ```cpp
   const char* ssid = "NAMA_WIFI_ANDA";
   const char* password = "PASSWORD_WIFI_ANDA";
   const char* serverUrl = "http://IP_KOMPUTER_PYTHON:8000/api/data";
   ```
3. *Upload* program ke board TTGO LoRa yang akan dijadikan Gateway.

### Mengatur Node Sensor

1. Buka file `sensor.ino` dan *upload* ke board TTGO LoRa lainnya.
2. Setelah alat menyala, cari jaringan WiFi baru bernama **Sensor_XXX_AP** dari HP atau Laptop Anda.
3. Hubungkan ke WiFi tersebut (Password: `12345678`).
4. Buka peramban dan akses `http://192.168.4.1`.
5. Masukkan **ID Sensor**, **Latitude**, dan **Longitude** lokasi penempatan, lalu klik Simpan. Board akan me-restart secara otomatis dan siap mendeteksi getaran!

### Menggunakan Simulasi (Tanpa Hardware Penuh)

Jika Anda belum merakit hardware namun ingin melihat bagaimana Dashboard bekerja:

1. Jalankan `server.py` seperti pada langkah 1.
2. Buka terminal baru dan jalankan:
   ```bash
   python sensor_dummy.py
   ```
3. Lihat Dashboard web Anda, titik-titik sensor acak akan muncul di peta dan grafik akan mulai bergerak!

## 📄 Lisensi

MIT License

*Dibuat untuk mempermudah visibilitas dan respons cepat terhadap aktivitas seismik taktis.*
