import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "your_verify_token")
GRAPH_API_TOKEN = os.getenv("GRAPH_API_TOKEN", "your_graph_api_token")

user_sessions = {}  # Store user order progress

CATEGORIES = {
    "Fruits": ["Apple", "Banana", "Mango"],
    "Nuts": ["Almonds", "Cashews", "Walnuts"],
    "Chocolates": ["Dairy Milk", "KitKat", "Snickers"]
}


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Incoming message:", data)

    # Extract message
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
        user_number = message["from"]
    except KeyError:
        return "No message", 200

    # Initialize user session if not exists
    if user_number not in user_sessions:
        user_sessions[user_number] = {"step": 1}

    # Check if it's a button reply or text
    if "interactive" in message:
        selected_option = message["interactive"]["list_reply"]["title"]
    else:
        selected_option = message["text"]["body"].strip().lower()

    response_text = ""

    # Step 1: Greet and show category list
    if user_sessions[user_number]["step"] == 1:
        send_whatsapp_list(user_number, phone_number_id, "Select a category", "Please choose a category:", list(CATEGORIES.keys()))
        user_sessions[user_number]["step"] = 2

    # Step 2: Show items in selected category
    elif user_sessions[user_number]["step"] == 2:
        if selected_option in CATEGORIES:
            user_sessions[user_number]["category"] = selected_option
            send_whatsapp_list(user_number, phone_number_id, f"Select a {selected_option}", f"Here are the available {selected_option}:", CATEGORIES[selected_option])
            user_sessions[user_number]["step"] = 3
        else:
            send_whatsapp_message(user_number, "Please select a valid category.", phone_number_id)

    # Step 3: Confirm quantity
    elif user_sessions[user_number]["step"] == 3:
        user_sessions[user_number]["item"] = selected_option
        send_whatsapp_message(user_number, f"How many {selected_option} would you like to order?", phone_number_id)
        user_sessions[user_number]["step"] = 4

    # Step 4: Confirm order
    elif user_sessions[user_number]["step"] == 4:
        user_sessions[user_number]["quantity"] = selected_option
        order_summary = f"You are ordering {selected_option} {user_sessions[user_number]['item']}. Confirm? (Yes/No)"
        send_whatsapp_message(user_number, order_summary, phone_number_id)
        user_sessions[user_number]["step"] = 5

    # Step 5: Finalize order
    elif user_sessions[user_number]["step"] == 5:
        if selected_option.lower() == "yes":
            send_whatsapp_message(user_number, "Order confirmed! ✅ Proceed to payment: https://dummy-payment.com/order123", phone_number_id)
        else:
            send_whatsapp_message(user_number, "Order canceled. Type 'order' to start again.", phone_number_id)
        del user_sessions[user_number]  # Clear session

    return "OK", 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


def send_whatsapp_message(to, text, phone_number_id):
    """ Sends a plain text message to WhatsApp """
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)


def send_whatsapp_list(to, phone_number_id, header, body, options):
    """ Sends a list message to WhatsApp """
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "action": {
                "button": "Select",
                "sections": [{"title": "Options", "rows": [{"id": opt, "title": opt} for opt in options]}]
            }
        }
    }
    requests.post(url, headers=headers, json=data)


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000, debug=True)
