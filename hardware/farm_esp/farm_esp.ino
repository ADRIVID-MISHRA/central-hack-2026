#include <DHT.h>

//DHT
constexpr uint8_t PIN_DHT = 4;
#define DHTTYPE DHT22
DHT dht(PIN_DHT, DHTTYPE);

//LDR
#define LIGHT_SENSOR_PIN 34



void setup() {
  Serial.begin(9600);
  dht.begin();
//  analogSetAttenuation(ADC_11db); //for LDR
}




void loop() {
  // float air_temperature = dht.readTemperature();
  // float air_humidity = dht.readHumidity();

  // if (isnan(air_temperature) || isnan(air_humidity)) {
  //   Serial.println("DHT read failed");
  // } else {
  //   Serial.print("Temp: ");
  //   Serial.print(air_temperature);
  //   Serial.print(" °C  | Humidity: ");
  //   Serial.print(air_humidity);
  //   Serial.println(" %");
  // }


  //LDR
  float lux = (analogRead(LIGHT_SENSOR_PIN) / 4095.0) * 15000.0;
  Serial.println(lux);
  



  delay(2000);  
}
