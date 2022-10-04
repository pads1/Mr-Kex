import json, os, random, re, pytz
from flask import Flask, request, make_response
from datetime import datetime
from typing import Union
from google.cloud import firestore
from google.cloud import dialogflowcx_v3 as dialogflowcx

from exceptions import ItemNotFoundException

agent_id = os.getenv('AGENT_ID')
project_id = os.getenv('PROJECT_ID')
location = os.getenv('LOCATION')

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "config/credentials.json"

app = Flask(__name__)
db = firestore.Client()

orders = []
order_counter = 1

def get_item_in_order(name: str):
    global orders
    for i in range(0, len(orders)):
        if name == orders[i]['name']:
            return orders[i]
    raise ItemNotFoundException

def set_item_in_order(name: str, quantity: int, op: str):
    global orders
    for i in range(0, len(orders)):
        if name == orders[i]['name']:
            if op == "+":
                orders[i]['quantity'] += quantity
            elif op == "-":
                orders[i]['quantity'] -= quantity
                if orders[i]['quantity'] == 0:
                    del orders[i]
            break
@app.route("/send_order", methods=['POST'])
def send_order():

    json_data = request.get_json(silent=True, force=True)
    session_name = json_data['sessionInfo']['session']
    parameters = json_data['sessionInfo']['parameters']

    content = { 
        "fulfillmentMessages": {
            "payload": {
                "message": "",
                "platform": "kommunicate"
            }
        }
    }
    print(json_data)
    parameters = json_data['sessionInfo']['parameters']

    ph_timezone = pytz.timezone("Asia/Hong_Kong")
    ts = datetime.now(ph_timezone)
    print(ts)

    order = {}
    order['customer_name'] = str(parameters['person-name']['name'])
    order['placed_on'] = ts

    # temporary
    order['mode'] = "pickup"

    global orders, order_counter
    order['orders'] = orders

    doc_id = f"order{order_counter}"
    db.collection('orders').document(doc_id).set(order)

    doc_ref = db.collection("karinderya_proper").document("menu")
    doc = doc_ref.get()
    val = doc.to_dict()

    for item in orders:
        identifier = item['id']
        stock = item['quantity']
        val[identifier]['stock'] -= stock
        db.collection("karinderya_proper").document("menu").set(val)

    order_counter += 1


    res = json.dumps(content, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route("/reset_values", methods=['POST'])
def reset_values():

    json_data = request.get_json(silent=True, force=True)

    session_name = json_data['sessionInfo']['session']
    content = { 
        "fulfillmentMessages": {
            "payload": {
                "message": "",
                "platform": "kommunicate"
            }
        }
    }

    try:
        content['session_info']['parameters']['servings'] = None
    except:
        pass

    res = json.dumps(content, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r
    
@app.route("/webhook", methods=['POST'])
def webhook():
    global orders
    json_data = request.get_json(silent=True, force=True)

    session_name = json_data['sessionInfo']['session']
    parameters = json_data['sessionInfo']['parameters']

    collection_name = parameters['module']
    custom_response_key = parameters['custom_response_key']

    doc_ref = db.collection(collection_name).document(custom_response_key)
    doc = doc_ref.get()
    val = doc.to_dict()

    payload = {}
    payload['platform'] = "kommunicate"

    # check availability of items, assumes that it is only food items
    if "availability" in custom_response_key:
        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        food_available_list = []
        food_not_available_list = []
        food_more_than_expected_list = []

        try:
            foods = parameters['servings']
        except:
            foods = [{"food": food, "quantity": val[food]['stock']} for food in list(val.keys())]

        # supplying the quantities first
        for i in range(0, len(foods)):
            try:
                int(foods[i]['quantity'])
            except:
                foods[i]['quantity'] = foods[i - 1]['quantity'] if i != 0 else 1
        
        for food in foods:
            quantity = int(food['quantity'])
            name = val[food['food']]['name']
            stock = int(val[food['food']]['stock'])

            if stock == 0:
                food_not_available_list.append(name)
            elif quantity > stock:
                food_more_than_expected_list.append({"name": name, "stock": stock})
            else:
                food_available_list.append({"name": name, "stock": stock})

        doc_ref = db.collection("chatbot_responses").document(custom_response_key)
        doc = doc_ref.get()
        val = doc.to_dict()

        chunks = []
        if len(food_not_available_list) > 0:
            message = str(val['item-not-available-list'][random.randint(0, len(val['item-not-available-list']) - 1)])
            message = message.replace("<ulam>", " and ".join(food_not_available_list))
            chunks.append(message)

        if len(food_available_list) > 0:
            message = str(val['item-available-specific-list'][random.randint(0, len(val['item-available-specific-list']) - 1)])
            message = message.replace("<servings>", ", ".join([f"{item['stock']} {'servings' if item['stock'] > 1 else 'serving'} of {item['name']}" for item in food_available_list]))
            chunks.append(str(message).lower() if len(chunks) > 0 else message)

        if len(food_more_than_expected_list) > 0:
            message = str(val['item-more-than-expected-list'][random.randint(0, len(val['item-more-than-expected-list']) - 1)])
            message = message.replace("<servings>", ", ".join([f"{item['stock']} {'servings' if item['stock'] > 1 else 'serving'} of {item['name']}" for item in food_more_than_expected_list]))
            chunks.append(str(message).lower() if len(chunks) > 0 else message)

        payload['text'] = ". ".join(chunks)

    elif "how-much" in custom_response_key:

        string = ""

        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        try:
            foods = parameters['servings']
        except:
            foods = [{"food": food, "quantity": val[food]['stock']} for food in list(val.keys())]

        # supplying the quantities first
        for i in range(0, len(foods)):
            try:
                int(foods[i]['quantity'])
            except:
                foods[i]['quantity'] = foods[i - 1]['quantity'] if i != 0 else 1

        if len(foods) == 1:

            name = val[foods[0]['food']]['name']
            quantity = int(foods[0]['quantity'])
            cost = val[foods[0]['food']]['price'] * quantity

            doc_ref_2 = db.collection("chatbot_responses").document(custom_response_key)
            doc_2 = doc_ref_2.get()
            val_2 = doc_2.to_dict()

            string += str(val_2["single-item"][random.randint(0, len(val_2["single-item"]) - 1)])
            string = string.replace("<number>", str(quantity)).replace("<ulam>", name).replace("<serving>", "servings" if quantity > 1 else "serving").replace("<total-cost>", str(cost))
        else:
            quantity1 = int(foods[0]['quantity'])
            ulam1 = val[foods[0]['food']]['name']
            quantity2 = int(foods[1]['quantity'])
            ulam2 = val[foods[1]['food']]['name']

            doc_ref_2 = db.collection("chatbot_responses").document(custom_response_key)
            doc_2 = doc_ref_2.get()
            val_2 = doc_2.to_dict()

            string += str(val_2["multiple-item"][0]).replace("<number>", str(quantity1)).replace("<ulam>", ulam1) \
                        .replace("<number2>", str(quantity2)).replace("<ulam2>", ulam2) \
                        + " and ".join([f"{str(int(foods[i]['quantity']))} {foods[i]['name']}" for i in range(2, len(foods))])

            string += " "
            qs = sum([food['quantity'] * val[food['food']]['price'] for food in foods])

            string += str(val_2["multiple-item"][1]).replace("<total-cost>", str(int(qs)))
        payload['text'] = string
    elif any([c in custom_response_key for c in ["so-far", "no-more"]]):
        if len(orders) == 0:
            payload['text'] = val['order-empty']
        else:
            string = "\n".join([str(val['heading'])])
            total_price = 0
            for order in orders:
                quantity = order['quantity']
                name = order['name']
                price = order['cost']
                total_price += price
                string += str(val['order-format']).replace("<number>", str(quantity)).replace("<ulam>", name).replace("<cost>", str(price)) + "\n"
            string += str(val['total']).replace("<total-cost>", str(total_price)) + "\n"
            try:
                string += "\n" + val['confirmation_message']
            except:
                string += "\n"
            payload['text'] = string
    elif "remove" in custom_response_key:
        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        foods = parameters['servings']

        # supplying the quantities first
        for i in range(0, len(foods)):
            try:
                int(foods[i]['quantity'])
            except:
                foods[i]['quantity'] = foods[i - 1]['quantity'] if i != 0 else 1
        
        existing_orders = []
        there_but_requested_for_more_orders = []
        not_existing_orders = []

        for food in foods:
            stock = val[food['food']]['stock']
            name = val[food['food']]['name']
            quantity = int(food['quantity'])

            if name not in list([f['name'] for f in orders]):
                not_existing_orders.append(name)
            else:
                order = get_item_in_order(name)
                ordered_stock = int(order['quantity'])
                if quantity > ordered_stock:
                    there_but_requested_for_more_orders.append({"name": name, "req_stock": quantity, "actual_quantity": ordered_stock})
                    set_item_in_order(order['name'], ordered_stock, "-")
                else:
                    existing_orders.append({"name": name, "quantity": quantity})
                    set_item_in_order(order['name'], quantity, "-")
            
        doc_ref = db.collection("chatbot_responses").document(custom_response_key)
        doc = doc_ref.get()
        val = doc.to_dict()

        chunks = []

        if len(not_existing_orders) > 0:
            message = str(val['responses']['not-existing-order'])
            message = message.replace("<orders>", " and ".join(not_existing_orders) + "are" if len(there_but_requested_for_more_orders) > 1 else "is")
            chunks.append(message)
        if len(there_but_requested_for_more_orders) > 0:
            message = str(val['responses']['more-than-removed-item'])
            message = message.replace("<old-orders>", " and ".join([f"{item['req_stock']} {item['name']} "for item in there_but_requested_for_more_orders])) \
                    .replace('new-orders', " and ".join([f"{item['actual_quantity']} {item['name']}" for item in there_but_requested_for_more_orders])) \
                    .replace("<modifier>", " are " if len(there_but_requested_for_more_orders) > 1 else "is")
            chunks.append(message)
        if len(existing_orders) > 0:
            message = str(val['responses']['existing-order'])
            message = message.replace("<orders>", " and ".join([f"{item['quantity']} {item['name']}" for item in existing_orders])) \
                    .replace("<modifier>", " are " if len(existing_orders) > 1 else "is")
            chunks.append(message)

        payload['text'] = ". ".join(chunks)

    elif "list" in custom_response_key:

        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        foods = parameters['servings']

        # supplying the quantities first
        for i in range(0, len(foods)):
            try:
                int(foods[i]['quantity'])
            except:
                foods[i]['quantity'] = foods[i - 1]['quantity'] if i != 0 else 1
        
        available_orders = []
        more_than_available_orders = []
        not_available_orders = []

        for food in foods:
            stock = val[food['food']]['stock']
            name = val[food['food']]['name']
            quantity = int(food['quantity'])
            cost = val[food['food']]['price']

            try:
                ordered_item = get_item_in_order(name)
            # if the item is not currently in the orders list
            except:
                if stock == 0:
                    not_available_orders.append(name)
                elif quantity > stock:
                    more_than_available_orders.append({"name": name, "req_stock": quantity, "placed_stock": stock})
                    orders.append({"id":food['food'], "name": name, "quantity": stock, "cost": quantity * cost})
                else:
                    available_orders.append({"name": name, "quantity": quantity})
                    orders.append({"id":food['food'], "name": name, "quantity": quantity, "cost": quantity * cost})
            else:
                current_quantity = ordered_item['quantity']
                if stock - quantity - current_quantity < 0:
                    more_than_available_orders.append({"name": name, "req_stock": quantity, "placed_stock": stock})
                    set_item_in_order(ordered_item['name'], stock, op="+")
                else:
                    available_orders.append({"name": name, "quantity": quantity})
                    set_item_in_order(ordered_item['name'], quantity, op="+")

        doc_ref = db.collection("chatbot_responses").document(custom_response_key)
        doc = doc_ref.get()
        val = doc.to_dict()

        chunks = []

        if len(not_available_orders) > 0:
            message = str(val['responses']['not-available-order'])
            message = message.replace("<ulam>", " and ".join(not_available_orders))
            chunks.append(message)
        if len(more_than_available_orders) > 0:
            message = str(val['responses']['not-added-orders'])
            message = message.replace("<old-orders>", " and ".join([f"{item['req_stock']} {item['name']}" for item in more_than_available_orders])) \
                    .replace('new-orders', " and ".join([f"{item['placed_stock']} {item['name']}" for item in more_than_available_orders]))
            chunks.append(message)
        if len(available_orders) > 0:
            message = str(val['responses']['added-orders'])
            message = message.replace("<orders>", " and ".join([f"{item['quantity']} {item['name']}" for item in available_orders]))
            chunks.append(message)

        payload['text'] = ". ".join(chunks)
    elif "confirmation" in custom_response_key:
        mode = str(parameters['mode'])
        payload['text'] = str(val["responses"][mode]).replace("<total>", str(sum([f['cost'] for f in orders])))
    elif "total" in custom_response_key:
        if len(orders) == 0:
            payload['text'] = val['order-empty']
        else:
            total = sum([t['cost'] for t in orders])
            string = str(val[f'order-full{random.randint(0, 1)}']).replace("<total-cost>", str(total))
            payload['text'] = string
    elif "intro" in custom_response_key:
        doc_ref = db.collection("karinderya_proper").document("menu")
        doc = doc_ref.get()
        val = doc.to_dict()

        current_stock = []
        for item in list(val.keys()):
            stock = val[item]['stock']
            if stock > 0:
                current_stock.append({"name": val[item]['name'], "stock": stock})
        
        doc_ref_2 = db.collection("chatbot_responses").document(custom_response_key)
        doc_2 = doc_ref_2.get()
        val_2 = doc_2.to_dict()

        if len(current_stock) == 0:
            payload['text'] = val_2['not-available']
        else:
            val_2['responses'][1] = str(val_2['responses'][1]).replace("<ulam>", " and ".join([item['name'] for item in current_stock]))
            payload['text'] = "\n".join([_ for _ in val_2['responses']])
    else:
        if not bool(val['iterating']):
            print("not iterating")
            if len(val['responses']) == 1:
                payload['text'] = val['responses'][0]
            else:
                random_number = random.randint(0, len(val['responses']) - 1)
                payload['text'] = val['responses'][random_number]

        else:
            payload['text'] = "\n".join([_ for _ in val['responses']])
    
    """
    content = {}
    content['fulfillment_response'] = {}
    content['fulfillment_response']['messages'] = []

    content['fulfillment_response']['messages'].append({'payload' : payload})
    content['session_info'] = {"session": session_name}
    content['platform'] = "kommunicate"

    # Send to Kommunicate
    res = json.dumps(content, indent=4)
    r = make_response(res)

    return r
    """
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
    orders = []
    app.secret_key = "secret_key"
    app.debug = True
    app.run(port=3000)
    