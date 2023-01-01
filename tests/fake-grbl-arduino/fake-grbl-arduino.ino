//Fake GRBL for arduino

void setup() {
  Serial.begin(115200);
}
void loop() {}

void serialEvent()
{
  while (Serial.available()) {
    switch(Serial.read()) {
      case '\n':  Serial.println("ok"); break;
      case '?':   Serial.println("<Idle|MPos:0.000,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>"); break;
    }
    //delay(5);
  }
}
