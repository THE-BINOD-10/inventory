import time
import paho.mqtt.client as paho
weight_topic = 'hdrn/weight/values'
test_val = 0
is_updated = False

weight_client = paho.Client("client-001")

def weight_on_message(client, userdata, message):
    #time.sleep(10)
    global test_val, is_updated
    print("received message =",str(message.payload.decode("utf-8")))
    test_val = str(message.payload.decode("utf-8"))
    is_updated = True


def weigh_on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(weight_topic, qos=0)
    #client.will_set(weight_topic, 0, qos=0, retain=True)


def get_integration_weight_val():
    global test_val, is_updated
    broker = "m14.cloudmqtt.com"
    port = 17235
    weight_client.username_pw_set("agytzduj", "j7xM0xetz3NG")
    weight_client.connect(broker, port, 60)#connect
    weight_client.loop_start()
    time.sleep(10)
    weight_client.disconnect()
    weight_client.loop_stop()
    test_val_cp = test_val
    test_val = 0
    is_updated_cp = is_updated
    is_updated = False
    return test_val_cp, is_updated_cp

weight_client.on_message = weight_on_message
weight_client.on_connect = weigh_on_connect