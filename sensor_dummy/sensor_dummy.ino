#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

// Pin LoRa TTGO T3 V1.6
#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 23
#define DIO0 26

// Pin OLED
#define OLED_SDA 21
#define OLED_SCL 22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
WebServer server(80);
Preferences preferences;

String sensorID;
String sensorLat;
String sensorLong;
int vibrationLevel = 0;

unsigned long lastOledToggle = 0;
bool showApInfo = true;
unsigned long lastLoRaSend = 0;
unsigned long lastVibUpdate = 0;

// Kredensial AP Dummy
const char* apSSID = "Dummy_Sensor_AP";
const char* apPass = "12345678";

void handleRoot() {
  String html = "<html><body><h2>Konfigurasi Sensor Dummy</h2>"
                "<form action='/save' method='POST'>"
                "ID Sensor: <input type='text' name='id' value='" + sensorID + "'><br><br>"
                "Latitude: <input type='text' name='lat' value='" + sensorLat + "'><br><br>"
                "Longitude: <input type='text' name='lon' value='" + sensorLong + "'><br><br>"
                "<input type='submit' value='Simpan & Restart'>"
                "</form></body></html>";
  server.send(200, "text/html", html);
}

void handleSave() {
  if (server.hasArg("id") && server.hasArg("lat") && server.hasArg("lon")) {
    preferences.begin("dummy_cfg", false);
    preferences.putString("id", server.arg("id"));
    preferences.putString("lat", server.arg("lat"));
    preferences.putString("lon", server.arg("lon"));
    preferences.end();
    
    server.send(200, "text/html", "<html><body><h2>Data Dummy Disimpan! Restarting...</h2></body></html>");
    delay(1000);
    ESP.restart();
  }
}

void setup() {
  Serial.begin(115200);
  
  // Setup OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 fail"));
    for(;;);
  }
  display.clearDisplay();
  display.setTextColor(WHITE);

  // Setup Flash Storage (Preferences)
  preferences.begin("dummy_cfg", true);
  sensorID = preferences.getString("id", "DUMMY-99");
  sensorLat = preferences.getString("lat", "-6.214600"); // Default Jakarta
  sensorLong = preferences.getString("lon", "106.845100");
  preferences.end();

  // Setup LoRa
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(433E6)) { // Sesuaikan frekuensi jika perlu (misal 433E6)
    Serial.println("LoRa init failed.");
  }

  // Setup Access Point
  WiFi.softAP(apSSID, apPass);
  
  // Setup WebServer Routing
  server.on("/", handleRoot);
  server.on("/save", HTTP_POST, handleSave);
  server.begin();
  
  // Inisialisasi seed random
  randomSeed(analogRead(0));
}

void loop() {
  server.handleClient();
  unsigned long currentMillis = millis();

  // Generate Nilai Getaran Dummy tiap 1 detik
  if (currentMillis - lastVibUpdate >= 1000) {
    // Simulasi: 10% peluang terjadi gempa buatan (getaran > 50)
    if (random(100) < 10) {
      vibrationLevel = random(55, 100); // Nilai Alert
    } else {
      vibrationLevel = random(0, 30);   // Nilai Normal
    }
    lastVibUpdate = currentMillis;
  }

  // Kirim data via LoRa setiap 2 detik
  if (currentMillis - lastLoRaSend >= 2000) {
    String payload = sensorID + "," + sensorLat + "," + sensorLong + "," + String(vibrationLevel);
    LoRa.beginPacket();
    LoRa.print(payload);
    LoRa.endPacket();
    lastLoRaSend = currentMillis;
  }

  // Toggle Tampilan OLED tiap 3 detik
  if (currentMillis - lastOledToggle >= 3000) {
    showApInfo = !showApInfo;
    lastOledToggle = currentMillis;
    
    display.clearDisplay();
    display.setCursor(0, 0);
    
    if (showApInfo) {
      display.println("--- DUMMY AP ---");
      display.println("SSID: " + String(apSSID));
      display.println("Pass: " + String(apPass));
      display.println("IP: ");
      display.println(WiFi.softAPIP().toString());
    } else {
      display.println("--- DUMMY DATA ---");
      display.println("ID: " + sensorID);
      display.println("Lat: " + sensorLat);
      display.println("Lon: " + sensorLong);
      display.println("Vib: " + String(vibrationLevel));
    }
    display.display();
  }
}
