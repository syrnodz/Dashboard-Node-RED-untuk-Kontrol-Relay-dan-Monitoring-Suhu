import time
import random
import threading
import paho.mqtt.client as mqtt


NIM = "2410010012"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = f"PythonDevice-{NIM}"

TOPIC_SUHU = f"iot/{NIM}/sensor/suhu"
TOPIC_RELAY = f"iot/{NIM}/aktuator/relay"
TOPIC_PWM = f"iot/{NIM}/aktuator/pwm"
TOPIC_STATUS_RELAY = f"iot/{NIM}/status/relay"

INTERVAL_PUBLISH = 3  


relay_state = "OFF"
pwm_value = 0

# ================= CALLBACK MQTT =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Terhubung ke broker")
        client.subscribe(TOPIC_RELAY, qos=0)
        client.subscribe(TOPIC_PWM, qos=0)
        print(f"[MQTT] Subscribe: {TOPIC_RELAY}")
        print(f"[MQTT] Subscribe: {TOPIC_PWM}")
    else:
        print(f"[MQTT] Gagal terhubung, kode: {rc}")

def on_message(client, userdata, msg):
    global relay_state, pwm_value
    payload = msg.payload.decode("utf-8").strip()
    print(f"[MQTT] Pesan masuk [{msg.topic}]: {payload}")

    # Kontrol Relay (GPIO 26)
    if msg.topic == TOPIC_RELAY:
        if payload in ("ON", "1"):
            relay_state = "ON"
            print("[AKTUATOR] Relay GPIO 26 -> MENYALA (ON)")
        elif payload in ("OFF", "0"):
            relay_state = "OFF"
            print("[AKTUATOR] Relay GPIO 26 -> MATI (OFF)")
        else:
            print(f"[AKTUATOR] Perintah relay tidak dikenal: {payload}")
            return
        client.publish(TOPIC_STATUS_RELAY, relay_state, qos=0)

    # Kontrol PWM LED (GPIO 2, rentang 0-255)
    elif msg.topic == TOPIC_PWM:
        try:
            val = int(float(payload))
            if 0 <= val <= 255:
                pwm_value = val
                persen = round((pwm_value / 255) * 100, 1)
                print(f"[AKTUATOR] PWM LED GPIO 2 -> {pwm_value}/255 ({persen}%)")
            else:
                print(f"[AKTUATOR] Nilai PWM di luar rentang 0-255: {val}")
        except ValueError:
            print(f"[AKTUATOR] Nilai PWM tidak valid: {payload}")

def on_disconnect(client, userdata, rc):
    print(f"[MQTT] Terputus (kode: {rc}). Mencoba reconnect...")


def baca_suhu():
    base = 27.0
    noise = random.uniform(-2.0, 3.0)
    return round(base + noise, 2)

# ================= THREAD PUBLISH SENSOR =================
def publish_loop(client):
    while True:
        try:
            suhu = baca_suhu()
            client.publish(TOPIC_SUHU, str(suhu), qos=0)
            print(f"[SENSOR] Publish suhu: {TOPIC_SUHU} -> {suhu} °C")
        except Exception as e:
            print(f"[ERROR] Publish gagal: {e}")
        time.sleep(INTERVAL_PUBLISH)

# ================= MAIN =================
def main():
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    print(f"[MQTT] Menghubungkan ke {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)

    publisher = threading.Thread(target=publish_loop, args=(client,), daemon=True)
    publisher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Menghentikan program...")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
