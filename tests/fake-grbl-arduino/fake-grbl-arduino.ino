//Fake GRBL for arduino
int8_t readcnt;
char buff[128];
void printPgmString(const char *s)
{
    char c;
    while ((c = pgm_read_byte_near(s++)))
        Serial.write(c);
}
void setup() {
    Serial.begin(115200);
}
void loop() {}
void serialEvent() 
{
    while (Serial.available()) {
        memset(buff, 0, sizeof(buff));
        readcnt = Serial.readBytesUntil(0x0A, buff, sizeof(buff));
        if (readcnt > 0) 
        {
            buff[readcnt] = 0;
            if ((strncmp(buff, "?", 1) == 0)) {
                printPgmString("<Idle|MPos:0.000,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>\n");
                Serial.println("ok");
                break;
            }
            if ((strncmp(buff, "$G", 2) == 0)) {
                printPgmString("[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]\n");
                Serial.println("ok");
                break;
            }
            printPgmString("ok\r\n");
        }
        //delay(5);
    }
}
