import urllib.request
import json
import time
import random

SERVER_URL = "http://localhost:8000/api/data"

# Data Dasar Koordinat
DUMMY_SENSORS = [
    {"id": "SENS-JAKPUS", "lat": -6.1754, "long": 106.8272},
    {"id": "SENS-JAKSEL", "lat": -6.2615, "long": 106.8106},
]

print("📡 Memulai Simulasi Sensor Dummy (Direct TCP/IP)...")

while True:
    for sensor in DUMMY_SENSORS:
        # Simulasi getaran (10% peluang terjadi gempa > 50)
        is_quake = random.random() < 0.1
        vib_value = random.randint(60, 100) if is_quake else random.randint(0, 20)
        
        payload = {
            "id": sensor["id"],
            "lat": sensor["lat"],
            "long": sensor["long"],
            "vib": vib_value
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(SERVER_URL, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            response = urllib.request.urlopen(req)
            print(f"[{time.strftime('%H:%M:%S')}] Terkirim ke {sensor['id']} | Getaran: {vib_value}")
        except Exception as e:
            print(f"Gagal mengirim data ke server: {e}")
            
    time.sleep(5) # Interval pengiriman 2 detik