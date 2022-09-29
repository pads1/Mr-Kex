import json, os, random, re, pytz, datetime, uuid
from flask import Flask, request, make_response
from typing import Union
from google.cloud import firestore
from google.cloud import dialogflowcx_v3 as dialogflowcx

agent_id = os.getenv('AGENT_ID')
project_id = os.getenv('PROJECT_ID')
location = os.getenv('LOCATION')

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "config/credentials.json"

app = Flask(__name__)
db = firestore.Client()

orders = []

@app.route("/")
def home():
    return "Hello World"

def check_availability(food_items: list[dict]):
    available_items = []

    string = ""

    for i in range(0, food_items):
        actual_name = food_items[i]['name']
        c_stock = food_items[i]["stock"]
        if c_stock > 0:
            available_items.append((actual_name, c_stock))

    doc_ref = db.collection("chatbot_responses").document("availability")
    doc = doc_ref.get()
    val = doc.to_dict()

    if len(available_items) == 0:
        not_available_msgs = val['item-not-available-list']
        string = str(not_available_msgs[random.randint(0, len(not_available_msgs) - 1)])
        string = string.replace("<ulam>", food_items[0]["name"]) + (" ".join(["and {}".format(food_items[i]["name"]) for i in range(1, len(food_items))]) if len(food_items) > 1 else "")
    else:
        available_msgs = val['item-available-specific-list']
        string = str(available_msgs[random.randint(0, len(available_msgs) - 1)])
        string = string.replace("<number>", available_items[0][0]).replace("<ulam>", available_items[0][1]) + (" ".join(["and {} {} {}".format(available_items[i][0], "cup" if available_items[i][0] == 1 else "cups", available_items[i][1]) for i in range(1, len(available_items))]) if len(available_items) > 1 else "")
    return string

def check_cost(food_items: list[dict], key: str):
    string = ""

    doc_ref = db.collection("chatbot_responses").document("how-much-{}".format(key))
    doc = doc_ref.get()
    val = doc.to_dict()

    if key == "specific":
        # The price of <number> <qty> of <ulam> is <cost> pesos.
        if len(food_items) == 1:
            name = food_items[0]["name"]
            quantity = int(food_items[0]["quantity"])
            unit_price = int(food_items[0]["cost"])

            string += str(val["responses"][0])
            string = string.replace("<number>", quantity).replace("<ulam>", name).replace("<qty>", "cups" if quantity > 1 else "cup").replace("<cost>", quantity * unit_price)
        # The total cost of the items is <number> pesos.
        else:
            string += str(val["responses"][1])
            qs = []
            for i in range(0, len(food_items)):
                quantity = int(food_items[i]["quantity"])
                unit_price = int(food_items[i]["cost"])
                qs.append(quantity * unit_price)
            string = string.replace("<number>", sum(qs))
    else:
        # Here are the prices of each item in the menu:
        string += str(val["responses"][0]) + "\n"
        string += "Name      Price (in pesos)\n"
        for i in range(0, len(food_items)):
            unit_price = int(food_items[i]["cost"])
            name = str(food_items[i]["name"])
            string += "{} {}\n".format(name, unit_price)
    return string

@app.route("/send_order", methods=['POST'])
def send_order():

    json_data = request.get_json(silent=True, force=True)
    session_name = json_data['sessionInfo']['session']
    parameters = json_data['sessionInfo']['parameters']

    content = { 
        "fulfillment_response": {
            "messages": [
                    {
                    }
                ]
            },
            "session_info":{
                "session": session_name,
                "parameters":{
                }
            }
    }
    print(json_data)
    parameters = json_data['sessionInfo']['parameters']

    ph_timezone = pytz.timezone("Asia/Hong_Kong")
    ts = datetime.now(ph_timezone)
    print(ts)

    order = {}
    order['customer_name'] = str(parameters['person-name.original'])
    order['placed_on'] = ts
    order['mode'] = parameters['mode']
    
    doc_ref = db.collection("karinderya_proper").document("menu")
    doc = doc_ref.get()
    val = doc.to_dict()

    for o in orders:
        pass



    doc_id = "customer{}".format(uuid.uuid1())
    doc_ref = db.collection('orders').document(doc_id).set(order)

    res = json.dumps(content, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route("/webhook", methods=['POST'])
def webhook():
    json_data = request.get_json(silent=True, force=True)

    print(json_data)
    session_name = json_data['sessionInfo']['session']
    parameters = json_data['sessionInfo']['parameters']
    # text = str(json_data['sessionInfo']['text'])

    collection_name = parameters['module']
    custom_response_key = parameters['custom_response_key']

    doc_ref = db.collection(collection_name).document(custom_response_key)
    doc = doc_ref.get()
    val = doc.to_dict()

    payload = {}

    # check availability of items
    if "availability" in custom_response_key:
        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        food_list = list(parameters['foods']) if len(parameters['foods']) > 0 else ["adobo", "sinigang", "torta", "kanin"]

        food_stock_list = []
        for food_name in food_list:
            food_stock_list.append({"name": val[food_name]["name"], "stock": val[food_name]["stock"]})
        
        payload['text'] = check_availability(food_stock_list)

    # check price of items, assumes that food_list == food_quantity_list or food_quantity_list == 0
    elif "how-much" in custom_response_key:
        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        food_list = list(parameters['foods']) if len(parameters['foods']) > 0 else ["adobo", "sinigang", "torta", "kanin"]
        food_quantity_list = list(parameters['number']) if len(parameters['number']) > 0 else [1] * len(food_list) 
        cost_list = [val[name]["price"] for name in food_list]

        food_price_checklist = []
        for name, quantity, cost in zip(food_list, food_quantity_list, cost_list):
            food_price_checklist.append({"name": val[name]["name"], "quantity": quantity, "cost": cost})
        payload['text'] = check_cost(food_price_checklist, key = "specific" if "specific" in custom_response_key else "all")
    elif "confirmation" in custom_response_key:
        mode = str(parameters['mode'])
        payload['text'] = val["responses"][mode]
    elif "no-more" in custom_response_key:
        string = "\n".join([str(val['responses']['heading'])])
        total_price = 0
        for order in orders:
            quantity = order['quantity']
            name = order['name']
            price = order['cost'] * quantity
            total_price += price
            string += "\n".join([str(val['order-format']).replace("<number>", quantity).replace("<item>", name).replace("<cost>", price)])
        string += "\n".join([str(val['total']).replace("<total_cost>", total_price)])
        payload['text'] = string
    elif "so-far" in custom_response_key:
        if len(orders) == 0:
            payload['text'] = val['responses']['order-empty']
        else:
            string = "\n".join([str(val['responses']['heading'])])
            total_price = 0
            for order in orders:
                quantity = order['quantity']
                name = order['name']
                price = order['cost'] * quantity
                total_price += price
                string += "\n".join([str(val['item-format']).replace("<qty>", quantity).replace("<ulam>", name).replace("<cost>", price)])
            string += "\n".join([str(val['total']).replace("<total_cost>", total_price)])
            payload['text'] = string
    else:
        if val['iterating'] == False:
            if len(val['responses']) == 1:
                payload['text'] = val['responses'][0]
            else:
                random_number = random.randint(0, len(val['responses'] - 1))
                payload['text'] = val['responses'][random_number]
        else:
            s = ""
            for response in val['responses']:
                s += "\n".join(response)
            payload['text'] = s

    content = {}
    content['fulfillment_response'] = {}
    content['fulfillment_response']['messages'] = []

    content['fulfillment_response']['messages'].append({'payload' : payload})
    content['session_info'] = {"session": session_name}

    res = json.dumps(content, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

if __name__ == '__main__':
    app.run(port=3000)
    