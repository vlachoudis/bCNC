void setup() {
  Serial.begin(115200);
}

void loop() {
  if (Serial.available()) {
    Serial.write(Serial.read());
  }
}
