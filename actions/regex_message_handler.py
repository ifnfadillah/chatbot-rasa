from rasa.shared.nlu.constants import TEXT

def handle_message(message):
    user_text = message.get(TEXT, "").strip() if message.get(TEXT) else ""