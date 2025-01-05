from time import sleep
import dht
from machine import Pin, WDT
import network
from simple import MQTTClient
from wifi_config import WIFI_SSID, WIFI_PASSWORD


# Configuration

DHT_PIN = 0  # GPIO2 for DHT sensor (D4 on ESP8266)
MQTT_SERVER = "192.168.1.152"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "/home/sensor/outdoor"
CLIENT_ID = "RobotLab"
led = Pin("LED", Pin.OUT)

OFFSET = 0 # offset the temp by this many degrees

# Watchdog timer setup (10-second timeout)
wdt = WDT(timeout=8000)  # Reset if the loop freezes for 5 seconds

# Initialize DHT sensor
dht_sensor = dht.DHT22(Pin(DHT_PIN))

# Global MQTT client
client = None

# Connect to Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            wdt.feed()
            sleep(0.5)
            print("Waiting for Wi-Fi connection...")
    print("Connected to Wi-Fi:", wlan.ifconfig())

# Connect to MQTT broker
def connect_mqtt():
    global client
    try:
        client = MQTTClient(CLIENT_ID, MQTT_SERVER, MQTT_PORT)
        client.connect()
        print("Connected to MQTT Broker")
    except OSError as e:
        print(f"Failed to connect to MQTT broker: {e}")
        for _ in range(10): # wait for 5 seconds
            wdt.feed()
            sleep(0.5)
        machine.reset()  # Force reset to recover

# Publish data to MQTT broker
def publish_data(temp, hum):
    global client
    payload = '{"temperature": %.2f, "humidity": %.2f}' % (temp, hum)
    try:
        led.value(0)
        wdt.feed()
        sleep(0.5)
        client.publish(MQTT_TOPIC, payload)
        print(f"Data sent: {payload}")
        led.value(1)
    except OSError as e:
        print(f"Failed to publish data: {e}")
        led.value(1)
        reconnect_mqtt()

# Reconnect to MQTT broker
def reconnect_mqtt():
    global client
    try:
        print("Attempting to reconnect to MQTT broker...")
        client.disconnect()
    except OSError:
        pass  # Ignore disconnect errors
    connect_mqtt()

# Main program loop
try:
    connect_wifi()
    connect_mqtt()
    while True:
        wdt.feed()  # Reset the watchdog timer
        
        try:
            # Read DHT sensor data
            dht_sensor.measure()
            temperature = dht_sensor.temperature() - OFFSET
            humidity = dht_sensor.humidity()
            print(f"Temperature: {temperature}°C, Humidity: {humidity}%")
            
            # Publish data
            publish_data(temperature, humidity)
        except OSError as e:
            print(f"Failed to read sensor or publish data: {e}")
        
        # Wait before the next cycle
        wdt.feed()  # Reset the watchdog timer
        sleep(1)
        wdt.feed()  # Reset the watchdog timer
        sleep(1)

except KeyboardInterrupt:
    print("Program stopped manually")
finally:
    if client:
        client.disconnect()
    print("Disconnected from MQTT Broker")
