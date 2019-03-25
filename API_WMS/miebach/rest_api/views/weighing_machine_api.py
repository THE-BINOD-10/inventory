import time
import paho.mqtt.client as paho
weight_topic = 'hdrn/weight/values'
weight_broker = 'm24.cloudmqtt.com'
weight_username = 'deiqblox'
weight_password = 'jq2RLMfhpRTG'
weight_port = 15853
test_val = 0
is_updated = False

weight_client = paho.Client("client-001")

def weight_on_message(client, userdata, message):
    #time.sleep(10)
    global test_val, is_updated
    #print("received message =",str(message.payload.decode("utf-8")))
    test_val = str(message.payload.decode("utf-8"))
    is_updated = True


def weigh_on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    #client.subscribe(weight_topic, qos=0)
    #client.will_set(weight_topic, 0, qos=0, retain=True)


def get_integration_weight_val(weight_topic):
    global test_val, is_updated
    weight_client.username_pw_set(weight_username, weight_password)
    weight_client.connect(weight_broker, weight_port, 60)#connect
    weight_client.subscribe(weight_topic, qos=0)
    weight_client.loop_start()
    time.sleep(1)
    #weight_client.disconnect()
    weight_client.loop_stop()
    test_val_cp = test_val
    test_val = 0
    is_updated_cp = is_updated
    is_updated = False
    return test_val_cp, is_updated_cp

weight_client.on_message = weight_on_message
weight_client.on_connect = weigh_on_connect