#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Kredensial WiFi dan Server URL
const char* ssid = "YD1RUH_HP";
const char* password = "abcdefgh.";
const char* serverUrl = "http://10.113.222.227:8000/api/data"; // Ubah sesuai IP Server Python Anda

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
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  Serial.begin(115200);

  // Setup OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setCursor(0, 0);
  display.println("LoRa Gateway");
  display.display();

  // Koneksi WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  display.println("WiFi Connected!");
  display.println(WiFi.localIP());
  display.display();

  // Setup LoRa
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed.");
    while(1);
  }
  display.println("LoRa Ready!");
  display.display();
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incoming = "";
    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }
    
    // Parsing String CSV sederhana: "SENS-01,-6.20,106.81,45"
    int firstComma = incoming.indexOf(',');
    int secondComma = incoming.indexOf(',', firstComma + 1);
    int thirdComma = incoming.indexOf(',', secondComma + 1);

    if (firstComma > 0 && secondComma > 0 && thirdComma > 0) {
      String id = incoming.substring(0, firstComma);
      String lat = incoming.substring(firstComma + 1, secondComma);
      String lon = incoming.substring(secondComma + 1, thirdComma);
      String vib = incoming.substring(thirdComma + 1);

      // Membuat Payload JSON
      String jsonPayload = "{\"id\":\"" + id + "\",\"lat\":" + lat + ",\"long\":" + lon + ",\"vib\":" + vib + "}";
      
      // Mengirim Data via HTTP POST
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        http.addHeader("Content-Type", "application/json");
        int httpResponseCode = http.POST(jsonPayload);
        http.end();

        // Update Layar
        display.clearDisplay();
        display.setCursor(0, 0);
        display.println("Data Diterima:");
        display.println(id + " | Vib:" + vib);
        display.println("HTTP Code: " + String(httpResponseCode));
        display.display();
      }
    }
  }
}
