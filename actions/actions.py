from typing import Any, Coroutine, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
from meteostat import Point, Hourly
import json
import random

from rasa_sdk.types import DomainDict

# Load environment variables
load_dotenv()

# Load data JSON
with open("actions/data.json", encoding="utf-8") as file:
    data = json.load(file)

intents_data = {}
for item in data.get("intents", []):
    intents_data.update(item)

events_data = data["events"]
kampungs_data = data["kampungs"]
situss_data = data["situss"]
kuliners_data = data["kuliners"]
kesehatans_data = data["kesehatans"]
    
#TIME GREETING
class ActionGetTimeGreeting(Action):
    def name(self) -> Text:
        return "action_get_time_greeting"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Set Time Indonesian
        tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(tz)
        hour = current_time.hour

        # Time Clasification
        if 4 <= hour < 11:
            greeting = "pagi"
        elif 11 <= hour < 15:
            greeting = "siang"
        elif 15 <= hour < 18:
            greeting = "sore"
        else:
            greeting = "malam"

        return [SlotSet("time", greeting)]

##REAL TIME WEATHER
def get_real_time_weather():
    location = Point(-7.3667, 112.7667)
    now_utc = datetime.now(pytz.utc)
    now = now_utc.replace(tzinfo=None)
    start = now - timedelta(hours=1)

    print(f"[DEBUG] Fetching weather data from {start} to {now}")
    
    try:
        data = Hourly(location, start, now)
        data = data.fetch()

        if not data.empty:
            temp = data.iloc[-1]['temp']
            print(f"[DEBUG] Temperature: {temp}°C")
            if temp <= 25:
                return "dingin"
            else:
                return "panas"
        else:
            print("[DEBUG] No weather data available.")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch weather data: {e}")
        return None

class ActionProvideQuickAsk(Action):

    def name(self) -> str:
        return "action_provide_quick_ask"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        entity_types = ["event", "kampung"]
        intents_related_to_entities = ["tanya_general_event", "tanya_tujuan_event", "tanya_sejarah_event", "tanya_tanggal_event", "tanya_lokasi_event", "tanya_kegiatan_event", "tanya_berita_event", "tanya_kuliner_lokasi_event", "tanya_rekomendasi_kuliner_berdasarkan_cuaca_event",
                                       "tanya_general_kampung", "tanya_sejarah_kampung", "tanya_layanan_masyarakat_kampung", "tanya_layanan_kesehatan_lokasi_kampung", "tanya_kategori_layanan_kesehatan_lokasi_kampung", "tanya_jenis_gejala_layanan_kesehatan_lokasi_kampung", "tanya_situs_lokasi_kampung", "tanya_event_lokasi_kampung", "tanya_lokasi_kelurahan_kampung", "tanya_general_situs"]

        # Ambil intent terakhir yang digunakan
        last_intent = tracker.latest_message['intent'].get('name')

        # Ambil entitas terbaru dari pesan pengguna
        entities = tracker.latest_message.get("entities", [])
        new_entity_type = None
        new_entity_value = None

        for entity in entities:
            if entity["entity"] in entity_types:
                new_entity_type = entity["entity"]
                new_entity_value = entity["value"]
                break  # Ambil entitas pertama yang ditemukan

        # Ambil entitas terakhir dari slot jika tidak ada entitas baru
        last_entity_type = tracker.get_slot("last_entity_type")
        last_entity_value = tracker.get_slot("last_entity_value")

        # **RESET ENTITY JIKA INTENT TIDAK BERHUBUNGAN DENGAN ENTITAS**
        if last_intent not in intents_related_to_entities:
            last_entity_type = None
            last_entity_value = None

        # Jika ada entitas baru, gunakan entitas baru dan perbarui slot
        if new_entity_value:
            current_entity_type = new_entity_type
            current_entity_value = new_entity_value
        else:
            current_entity_type = last_entity_type
            current_entity_value = last_entity_value

        # Jika tidak ada entitas, coba ambil Quick Ask berdasarkan intent dari `data.json`
        if not current_entity_value:
            next_intents = intents_data.get(last_intent, [])
            max_questions = 5
            quick_asks = random.sample(next_intents, min(max_questions, len(next_intents))) if next_intents else []

            quick_asks = [intent.replace("_", " ").capitalize() for intent in quick_asks]

            # Jika tetap kosong, gunakan fallback Quick Ask default
            if not quick_asks:
                quick_asks = [
                ]
        else:
            # Quick Ask berdasarkan entitas yang diingat
            quick_ask_entity_based = {
                "event": [
                    f"Ada kegiatan apa saja di {current_entity_value}?",
                    f"Bagaimana sejarah dari {current_entity_value}?",
                    f"Apa media sosial {current_entity_value}?",
                    f"Dimana lokasi {current_entity_value}?",
                    f"Ada kuliner apa saja di {current_entity_value}?"
                ], 
                "kampung": [
                    f"Bagaimana sejarah dari {current_entity_value}?",
                    f"Cara mengurus layanan administrasi di {current_entity_value}?",
                    f"Layanan Kesehatan di {current_entity_value}?",
                    f"Ada kuliner apa saja di {current_entity_value}?",
                    f"Ada situs apa saja di {current_entity_value}?",
                    f"Ada event budaya apa saja di {current_entity_value}",
                    f"Dimana lokasi kantor kelurahan {current_entity_value}?",
                    f"Berikan rekomendasi kuliner yang cocok untuk cuaca saat ini di {current_entity_value}",
                    f"Bagaimana cara mendapatkan informasi {current_entity_value}?"
                ], 
                "situs": [
                    f"Dimana lokasi {current_entity_value}?"
                ]
            }

            # Ambil quick asks berdasarkan entity type dan random max 5
            all_quick_asks = quick_ask_entity_based.get(current_entity_type, [])
            quick_asks = random.sample(all_quick_asks, min(5, len(all_quick_asks))) if all_quick_asks else []

            # Jika entitas tidak ditemukan di daftar quick ask berbasis entitas, gunakan dari `data.json`
            if not quick_asks:
                next_intents = intents_data.get(last_intent, [])
                quick_asks = random.sample(next_intents, min(5, len(next_intents))) if next_intents else []
                quick_asks = [intent.replace("_", " ").capitalize() for intent in quick_asks]

            # Jika tetap kosong, gunakan fallback Quick Ask default
            if not quick_asks:
                quick_asks = [
                    "Ada informasi lain yang bisa saya bantu?",
                    "Ingin tahu lebih lanjut tentang KLK?"
                ]

        dispatcher.utter_message(
            text="Berikut beberapa pertanyaan yang mungkin Anda tanyakan:",
            json_message={"quick_asks": quick_asks}
        )

        # **Perbarui slot hanya jika ada entitas baru atau kosongkan jika intent tidak terkait entitas**
        if new_entity_value:
            return [
                SlotSet("last_entity_type", new_entity_type),
                SlotSet("last_entity_value", new_entity_value)
            ]
        elif last_intent not in intents_related_to_entities:
            return [
                SlotSet("last_entity_type", None),
                SlotSet("last_entity_value", None)
            ]
        else:
            return []


##DATA KLK
# EVENT KLK
class ActionGetEvent(Action):
    def name(self):
        return "action_get_event_klk"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        response_text = {
                "text_upper": f"Kampung Lingkar Kampus turut serta dalam event atau festival yang ada di kampung-kampung sekitar Universitas Brawijaya. Berikut beberapa event yang ada di Kampung Lingkar Kampus:\n\n",        
                "list": [
                    {
                        "name": event["name"],
                        "desc": event["informGeneralEvent"],}
                        for event in events_data
                ],
                "text_under": "\n\n Event atau Festival mana yang ingin kamu tanyakan?"
            }
        dispatcher.utter_message(json_message=response_text)
        
        return []

# SITUS KLK
class ActionGetSitus(Action):
    def name(self):
        return "action_get_situs_klk"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        response_text = {
                "text_upper": f"Berikut situs-situs yang ada di Kampung Lingkar Kampus: \n\n",        
                "list": [
                    {
                        "name": situs["name"],
                        "desc": situs["informGeneralSitus"],}
                        for situs in situss_data
                ],
                "text_under": "\n\n Situs atau cagar budaya mana yang ingin kamu tanyakan?"
            }
        dispatcher.utter_message(json_message=response_text)
        
        return []
    
# LAYANAN KESEHATAN KLK
class ActionGetLayananKesehatan(Action):
    def name(self):
        return "action_get_layanan_kesehatan_klk"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        response_text = {
                "text_upper": f"Berikut beberapa layanan kesehatan yang Kaboo ketahui ada di Kampung Sekitar Kampus Universitas Brawijaya: \n\n",
                "listLayananKesehatan": [
                    {
                        "name": kesehatans["name"],
                        "operationalHour": kesehatans["operationalHour"],
                        "lokasiKesehatan": kesehatans["lokasiKesehatan"],}
                        for kesehatans in kesehatans_data
                ],
                "text_under": "\n\n Layanan kesehatan mana yang ingin kamu tanyakan?"
            }
        dispatcher.utter_message(json_message=response_text)
        
        return []
    
# BERITA KLK
# class ActionGetBerita(Action):
#     def name(self):
#         return "action_get_berita_klk"

#     def run(self, dispatcher, tracker, domain):
#         # Get API from .env
#         openai.api_key = os.getenv("OPENAI_API_KEY")

#         if not openai.api_key:
#             dispatcher.utter_message(text="API Key tidak ditemukan. Pastikan file .env sudah dikonfigurasi.")
#             return []

#         # Prompt to APIs
#         prompt_text = "Berikan ringkasan berita terbaru tentang Kampung Lingkar Kampus (KLK) sertakan list dan link sumber beritanya."

#         try:
#             response = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[{"role": "system", "content": prompt_text}]
#             )

#             berita = response["choices"][0]["message"]["content"].strip()

#         except Exception as e:
#             berita = "Maaf, saya tidak dapat mengambil berita saat ini."

#         dispatcher.utter_message(text=f"Berita terbaru KLK: {berita}")
#         return []



##### DATA EVENT or FESTIVAL
#GENERAL
class ActionInformGeneralEvent(Action):
    def name(self) -> Text:
        return "action_get_inform_general_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["informGeneralEvent"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []

#KAMPUNG EVENT
KAMPUNG_KHUSUS = {
    "kampung sumbersari": "Mohon maaf, Kaboo tidak memiliki daftar event atau festival yang ada di Kampung Sumbersari. Mungkin Sobat KLK dapat mendatangi event-event atau festival lain yang ada di kampung-kampung sekitar kampus"
}

#EVENT DI KAMPUNG
class ActionEventLokasiKampung(Action):
    def name(self) -> Text:
        return "action_get_event_lokasi_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if not kampung_name:
            dispatcher.utter_message(
                json_message={"status": "error", "message": "Silakan sebutkan nama kampung agar saya bisa memberikan event budaya yang ada!"}
            )
            return [] 

        kampung_name = kampung_name.lower()

        if kampung_name in KAMPUNG_KHUSUS:
            dispatcher.utter_message(
                json_message={"status": "info", "kampung": kampung_name, "message": KAMPUNG_KHUSUS[kampung_name]}
            )
            return []

        event_di_kampung = [
            item for item in events_data 
            if item["kampung"].lower() == kampung_name
        ]

        if event_di_kampung:
            response_text = {
                "status": "success",
                "kampung": kampung_name,
                "text_upper": f"Berikut adalah event budaya yang tersedia di {kampung_name}:\n\n",
                "list": [
                    {
                        "name": event["name"],
                        "desc": event["informGeneralEvent"]
                    }
                    for event in event_di_kampung
                ],
                "text_under": f"Kaboo tunggu kedatangan dan partisipasi Sobat KLK di event-event tersebut!"
            }
            dispatcher.utter_message(json_message=response_text)

        else:
            dispatcher.utter_message(
                json_message={"status": "error", "message": f"Maaf, saya tidak menemukan event atau festival yang tersedia di {kampung_name}. Coba tanyakan kampung lainnya!"}
            )

        return []
    
#TUJUAN EVENT
class ActionTujuanEvent(Action):
    def name(self) -> Text:
        return "action_get_tujuan_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["tujuanEvent"])
                    return []
        
        dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []
    
#SEJARAH EVENT
class ActionSejarahEvent(Action):
    def name(self) -> Text:
        return "action_get_sejarah_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["sejarahEvent"])
                    return []
        
        dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []
    
#TANGGAL EVENT
class ActionTanggalEvent(Action):
    def name(self) -> Text:
        return "action_get_tanggal_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["tanggalEvent"])
                    return []
        
        dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []

#LOKASI EVENT
class ActionLokasiEvent(Action):
    def name(self) -> Text:
        return "action_get_lokasi_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["lokasiEvent"])
                    return []
        
        dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []

#KEGIATAN EVENT
class ActionKegiatanEvent(Action):
    def name(self) -> Text:
        return "action_get_kegiatan_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["kegiatanEvent"])
                    return []
        
        dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []
    

# #BERITA EVENT
# class ActionBeritaEvent(Action):
#     def name(self) -> Text:
#         return "action_get_berita_event"

#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
#         # Nama event from entities
#         event_name = next(tracker.get_latest_entity_values("event"), None)
        
#         # API key from env
#         openai.api_key = os.getenv("OPENAI_API_KEY")

#         if not openai.api_key:
#             dispatcher.utter_message(text="Maaf, tidak dapat mengakses layanan berita saat ini.")
#             return []

#         if event_name:
#             try:
#                 # Custom Prompt
#                 prompt_text = f"Berikan ringkasan berita terbaru tentang {event_name} di Malang. Sertakan list dan link sumber beritanya."

#                 # Call OpenAI
#                 response = openai.ChatCompletion.create(
#                     model="gpt-4",
#                     messages=[{"role": "system", "content": prompt_text}]
#                 )

#                 berita = response["choices"][0]["message"]["content"].strip()
#                 dispatcher.utter_message(text=f"Berita terbaru tentang {event_name}: {berita}")
                
#             except Exception as e:
#                 dispatcher.utter_message(text=f"Maaf, saya tidak dapat menemukan berita terbaru tentang {event_name} saat ini.")
#         else:
#             dispatcher.utter_message(text="Maaf, saya tidak mengenali event yang Anda maksud.")
            
#         return []
    
#CONTACT EVENT
class ActionContactEvent(Action):
    def name(self) -> Text:
        return "action_get_contact_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)

        if event_name:
            for event in events_data:
                if event["name"].lower() == event_name.lower():
                    dispatcher.utter_message(text=event["contactEvent"])
                    return []
        else:
            dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang event tersebut.")
        return []

#KULINER ACTION
#GENERAL
class ActionInformGeneralKuliner(Action):
    def name(self) -> Text:
        return "action_get_inform_general_kuliner"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kuliner_name = next(tracker.get_latest_entity_values("kuliner"), None)

        user_input = tracker.latest_message.get("text", "").lower()
        
        daftar_kuliner = [kuliner["name"].lower() for kuliner in kuliners_data]
        
        kuliner_name = next((nama for nama in daftar_kuliner if nama in user_input), None)

        if kuliner_name:
            for kuliner in kuliners_data:
                if kuliner["name"].lower() == kuliner_name.lower():
                    dispatcher.utter_message(text=kuliner["desc"])
                    return []
        dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang kuliner tersebut.")
        return []

#KULINER EVENT
EVENT_KHUSUS = {
    "festival keramik dinoyo": "Mohon maaf, Kaboo tidak memiliki daftar kuliner yang ada di Festival Keramik Dinoyo. Namun, Sobat KLK dapat belanja berbagai jenis kerajinan keramik seperti vas bunga, guci, asbak, piring, hingga hiasan dinding yang memiliki desain unik dan khas.",
    "festival kali brantas": "Mohon maaf, Kaboo tidak memiliki informasi daftar kuliner yang ada di Festival Kali Brantas. Namun, Sobat KLK dapat mengunjungi langsung stand-stand kuliner UMKM yang ada di 6 titik lokasi Festival Kali Brantas."
}

class ActionKulinerLokasiEvent(Action):
    def name(self) -> Text:
        return "action_get_kuliner_lokasi_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        event_name = next(tracker.get_latest_entity_values("event"), None)
        kategori_kuliner = next(tracker.get_latest_entity_values("kategor"), None)

        if not event_name:
            dispatcher.utter_message(
                json_message={"status": "error", "message": "Silakan sebutkan nama event agar saya bisa memberikan rekomendasi kuliner yang tersedia!"}
            )
            return []

        event_name = event_name.lower()
        kategori_kuliner = kategori_kuliner.casefold().strip() if kategori_kuliner else None

        if event_name in EVENT_KHUSUS:
            dispatcher.utter_message(
                json_message={"status": "info", "event": event_name, "message": EVENT_KHUSUS[event_name]}
            )
            return []

        kuliner_di_event = [
            item for item in kuliners_data 
            if any(event.lower() == event_name for event in item["event"])
        ]

        if kategori_kuliner:
            kuliner_di_event = [item for item in kuliner_di_event if item["kategori"].casefold().strip() == kategori_kuliner]

        if kuliner_di_event:
            response_text = {
                "status": "success",
                "event": event_name,
                "kategori": kategori_kuliner if kategori_kuliner else "Semua Kategori",
                "text_upper": f"Berikut adalah {kategori_kuliner if kategori_kuliner else 'kuliner'} yang tersedia di {event_name}: \n \n",
                "list": [
                    {"name": kuliner["name"], "desc": kuliner["desc"]} for kuliner in kuliner_di_event
                ],
                "text_under": f"Dan masih banyak lagi {kategori_kuliner if kategori_kuliner else 'kuliner'} yang tersedia di {event_name}, Sobat KLK bisa mendapatkan informasi lebih lanjut dengan mendatangi langsung lokasi di {event_name}."
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={"status": "error", "message": f"Maaf, Kaboo tidak menemukan {kategori_kuliner if kategori_kuliner else 'kuliner'} yang tersedia di {event_name}. Coba tanyakan event lain!"}
            )

        return []
    
class ActionKulinerLokasiKampung(Action):
    def name(self) -> Text:
        return "action_get_kuliner_lokasi_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)
        kategori_kuliner = next(tracker.get_latest_entity_values("kategori"), None)

        if not kampung_name:
            dispatcher.utter_message(
                json_message={"status": "error", "message": "Silakan sebutkan nama event agar saya bisa memberikan rekomendasi kuliner yang tersedia!"}
            )
            return []
          
        kampung_name = kampung_name.lower()
        kategori_kuliner = kategori_kuliner.casefold().strip() if kategori_kuliner else None

        kuliner_di_kampung = [
            item for item in kuliners_data 
            if any(kampung.lower() == kampung_name for kampung in item["kampung"])
        ]

        if kategori_kuliner:
            kuliner_di_kampung= [item for item in kuliner_di_kampung if item["kategori"].casefold().strip() == kategori_kuliner]

        if kuliner_di_kampung:
            response_text = {
                "status": "success",
                "event": kampung_name,
                "kategori": kategori_kuliner if kategori_kuliner else "Semua Kategori",
                "text_upper": f"Berikut adalah {kategori_kuliner if kategori_kuliner else 'kuliner'} yang tersedia di {kampung_name}: \n \n",
                "list": [
                    {
                        "name": kuliner["name"],
                        "desc": kuliner["desc"]
                    }
                    for kuliner in kuliner_di_kampung
                ],
                "text_under": f"Dan masih banyak lagi {kategori_kuliner if kategori_kuliner else 'kuliner'} yang tersedia di {kampung_name}, Sobat KLK bisa mendapatkan informasi lebih lanjut dengan mendatangi langsung lokasi di {kampung_name}."
            }
            dispatcher.utter_message(json_message=response_text)

        else:
            dispatcher.utter_message(
                json_message={"status": "error", "message": f"Maaf, Kaboo tidak menemukan {kategori_kuliner if kategori_kuliner else 'kuliner'} yang tersedia di {kampung_name}. Coba tanyakan event lain!"}
            )

        return []

CUACA_MAPPING = {
    "hujan": "dingin",
    "malam": "dingin",
    "cerah": "panas",
    "gerah": "panas",
    "mendung": "panas",
    "pagi": "panas",
    "siang": "panas",
    "sore": "panas"
}
class ActionRekomendasiKulinerBerdasarkanCuaca(Action):
    def name(self) -> Text:
        return "action_get_rekomendasi_kuliner_berdasarkan_cuaca"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        cuaca_name = next(tracker.get_latest_entity_values("cuaca"), None)
        kategori_kuliner = next(tracker.get_latest_entity_values("kategori"), None)

        latest_message = tracker.latest_message
        original_text = None

        if 'entities' in latest_message:
            for entity in latest_message['entities']:
                if entity['entity'] == 'cuaca':
                    original_text = entity['value']
                    break

        if not cuaca_name:
            cuaca_name = get_real_time_weather()
            original_text = cuaca_name
            if not cuaca_name:
                dispatcher.utter_message(text="Saya tidak bisa mendapatkan informasi cuaca saat ini. Silakan sebutkan cuaca secara manual!")
                return []

        cuaca_mapped = CUACA_MAPPING.get(cuaca_name.lower(), cuaca_name.lower())
        kategori_kuliner = kategori_kuliner.casefold().strip() if kategori_kuliner else None

        kuliner_rekomendasi = [item for item in kuliners_data if cuaca_mapped in [c.lower() for c in item["cuaca"]]]
        
        if kategori_kuliner:
            kuliner_rekomendasi = [
                item for item in kuliner_rekomendasi 
                if item["kategori"].casefold().strip() == kategori_kuliner
            ]

        if kuliner_rekomendasi:
            response_text = {
                "status": "success",
                "event": cuaca_name,
                "kategori": kategori_kuliner if kategori_kuliner else "Semua Kategori",
                "text_upper": f"Berikut adalah {kategori_kuliner if kategori_kuliner else 'kuliner'} yang cocok ketika {original_text}:\n\n",
                "list": [
                    {
                        "name": kuliner["name"],
                        "desc": kuliner["desc"],
                    }
                    for kuliner in kuliner_rekomendasi
                ],
            "text_under": f"Dan masih banyak lagi {kategori_kuliner if kategori_kuliner else 'kuliner'} yang cocok ketika {original_text}, Sobat KLK bisa mendapatkan informasi lebih lanjut dengan mendatangi langsung event-event atau kampung-kampung di sekitar kampus Universitas Brawijaya."
            }
            dispatcher.utter_message(json_message=response_text)
        
        else:
            dispatcher.utter_message(text=f"Maaf, saya tidak menemukan kuliner yang cocok ketika {original_text}. Coba tanyakan cuaca lain!")

        return []

class ActionRekomendasiKulinerBerdasarkanCuacaEvent(Action):
    def name(self) -> Text:
        return "action_get_rekomendasi_kuliner_berdasarkan_cuaca_event"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        cuaca_name = next(tracker.get_latest_entity_values("cuaca"), None)
        event_name = next(tracker.get_latest_entity_values("event"), None)
        kategori_kuliner = next(tracker.get_latest_entity_values("kategori"), None)

        original_text = None
        latest_message = tracker.latest_message
        if 'entities' in latest_message:
            for entity in latest_message['entities']:
                if entity['entity'] == 'cuaca':
                    original_text = entity['value']
                    break
        
        if not cuaca_name:
            cuaca_name = get_real_time_weather()
            original_text = cuaca_name
            if not cuaca_name or not event_name: 
                dispatcher.utter_message(
                    text="Saya tidak bisa mendapatkan informasi cuaca saat ini. Silakan sebutkan cuaca secara manual!"
                )
                return []
        
        cuaca_name = CUACA_MAPPING.get(cuaca_name.lower(), cuaca_name.lower())
        event_name = event_name.lower() if event_name else None
        kategori_kuliner = kategori_kuliner.casefold().strip() if kategori_kuliner else None
        
        if event_name in EVENT_KHUSUS:
            dispatcher.utter_message(
                json_message={"status": "info", "event": event_name, "message": EVENT_KHUSUS[event_name]}
            )
            return []

        kuliner_rekomendasi_di_event= [
            item for item in kuliners_data 
            if cuaca_name in [c.lower() for c in item["cuaca"]] 
            and event_name in [e.lower() for e in item["event"]]
        ]
        
        if kategori_kuliner:
            kuliner_rekomendasi_di_event = [
                item for item in kuliner_rekomendasi_di_event
                if item["kategori"].casefold().strip() == kategori_kuliner
            ]

        if kuliner_rekomendasi_di_event:
            response_text = {
                "status": "success",
                "event": event_name,
                "kategori": kategori_kuliner if kategori_kuliner else "Semua Kategori",
                "text_upper": (
                    f"Berikut adalah {kategori_kuliner if kategori_kuliner else 'kuliner'} "
                    f"yang cocok ketika {original_text} di {event_name}:\n\n"
                ),
                "list": [
                    {"name": kuliner["name"], "desc": kuliner["desc"]}
                    for kuliner in kuliner_rekomendasi_di_event
                ],  
                "text_under": (
                    f"Dan masih banyak lagi kuliner yang cocok ketika {original_text} di {event_name}, "
                    f"Sobat KLK bisa mendapatkan informasi lebih lanjut dengan mendatangi langsung lokasi di {event_name}."
                )
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                text=f"Maaf, saya tidak menemukan kuliner yang cocok ketika {original_text} di {event_name}. Coba tanyakan cuaca lain!"
            )
        
        return []
    
class ActionRekomendasiKulinerBerdasarkanCuacaKampung(Action):
    def name(self) -> Text:
        return "action_get_rekomendasi_kuliner_berdasarkan_cuaca_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        cuaca_name = next(tracker.get_latest_entity_values("cuaca"), None)
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)
        kategori_kuliner = next(tracker.get_latest_entity_values("kategori"), None)

        original_text = None
        latest_message = tracker.latest_message
        if 'entities' in latest_message:
            for entity in latest_message['entities']:
                if entity['entity'] == 'cuaca':
                    original_text = entity['value']
                    break
        
        if not cuaca_name:
            cuaca_name = get_real_time_weather()
            original_text = cuaca_name
            if not cuaca_name or not kampung_name: 
                dispatcher.utter_message(
                    text="Saya tidak bisa mendapatkan informasi cuaca saat ini. Silakan sebutkan cuaca secara manual!"
                )
                return []
        
        cuaca_name = CUACA_MAPPING.get(cuaca_name.lower(), cuaca_name.lower())
        kampung_name = kampung_name.lower() if kampung_name else None
        kategori_kuliner = kategori_kuliner.casefold().strip() if kategori_kuliner else None
        
        kuliner_rekomendasi_di_kampung = [
            item for item in kuliners_data 
            if cuaca_name in [c.lower() for c in item["cuaca"]] 
            and kampung_name in [e.lower() for e in item["kampung"]]
        ]
        
        if kategori_kuliner:
            kuliner_rekomendasi_di_kampung = [
                item for item in kuliner_rekomendasi_di_kampung
                if item["kategori"].casefold().strip() == kategori_kuliner
            ]

        if kuliner_rekomendasi_di_kampung:
            response_text = {
                "status": "success",
                "event": kampung_name,
                "kategori": kategori_kuliner if kategori_kuliner else "Semua Kategori",
                "text_upper": (
                    f"Berikut adalah {kategori_kuliner if kategori_kuliner else 'kuliner'} "
                    f"yang cocok ketika {original_text} di {kampung_name}:\n\n"
                ),
                "list": [
                    {"name": kuliner["name"], "desc": kuliner["desc"]}
                    for kuliner in kuliner_rekomendasi_di_kampung
                ],  
                "text_under": (
                    f"Dan masih banyak lagi kuliner yang cocok ketika {original_text} di {kampung_name}, "
                    f"Sobat KLK bisa mendapatkan informasi lebih lanjut dengan mendatangi langsung lokasi di {kampung_name}."
                )
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                text=f"Maaf, saya tidak menemukan kuliner yang cocok ketika {original_text} di {kampung_name}. Coba tanyakan cuaca lain!"
            )
        
        return []

#KAMPUNG
class ActionInformGeneralKampung(Action):
    def name(self) -> Text:
        return "action_get_inform_general_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if kampung_name:
            for kampung in kampungs_data:
                if kampung["name"].lower() == kampung_name.lower():
                    dispatcher.utter_message(text=kampung["informGeneralKampung"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, saya tidak dapat menemukan informasi tentang kampung tersebut.")
        return []

class ActionGetSejarahKampung(Action):
    def name(self) -> Text:
        return "action_get_sejarah_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if kampung_name:
            for kampung in kampungs_data:
                if kampung["name"].lower() == kampung_name.lower():
                    dispatcher.utter_message(text=kampung["sejarahKampung"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, Kaboo tidak dapat menemukan sejarah tentang kampung tersebut.")
        return []
    
class ActionGetLayananMasyarakatKampung(Action):
    def name(self) -> Text:
        return "action_get_layanan_masyarakat_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if kampung_name:
            for kampung in kampungs_data:
                if kampung["name"].lower() == kampung_name.lower():
                    dispatcher.utter_message(text=kampung["layananMasyarakatKampung"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, Kaboo tidak dapat menemukan informasi tentang layanan masyarakat kampung tersebut.")
        return []

class ActionGetLayananKesehatanLokasiKampung(Action):
    def name(self) -> Text:
        return "action_get_layanan_kesehatan_lokasi_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if not kampung_name:
            dispatcher.utter_message(
                json_message={"status": "error", "message": "Silakan sebutkan nama kampung agar saya bisa memberikan layanan kesehatan yang ada di kampung tersebut!"}
            )
            return [] 

        kampung_name = kampung_name.lower()

        # Perbaikan: Cek apakah kampung ada dalam list kampung pada setiap item kesehatan
        layanan_kesehatan_di_kampung = [
            item for item in kesehatans_data 
            if kampung_name in [k.lower() for k in item["kampung"]]  # Ubah pengecekan untuk list
        ]

        if layanan_kesehatan_di_kampung:
            response_text = {
                "status": "success",
                "kampung": kampung_name,
                "text_upper": f"Berikut adalah layanan kesehatan yang tersedia di {kampung_name}:\n\n",
                "listLayananKesehatan": [
                    {
                        "name": kesehatan["name"],
                        "operationalHour": kesehatan["operationalHour"],
                        "lokasiKesehatan": kesehatan["lokasiKesehatan"]
                    }
                    for kesehatan in layanan_kesehatan_di_kampung
                ],
                "text_under": f"Kaboo tunggu kedatangan Sobat KLK di layanan kesehatan {kampung_name}!"
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={"status": "error", "message": f"Maaf, saya tidak menemukan layanan kesehatan yang ada di {kampung_name}. Coba tanyakan kampung lainnya!"}
            )

        return []
    
class ActionGetKategoriLayananKesehatanLokasiKampung(Action):
    def name(self) -> Text:
        return "action_get_kategori_layanan_kesehatan_lokasi_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)
        kategori_name = next(tracker.get_latest_entity_values("kategori"), None)

        if not kampung_name or not kategori_name:
            dispatcher.utter_message(text="Maaf, Kaboo membutuhkan informasi kampung dan kategori layanan kesehatan yang lebih spesifik")
            return []

        # Filter layanan kesehatan berdasarkan kampung dan kategori
        kategori_layanan_kesehatan_di_kampung= []
        for kesehatan in kesehatans_data:
            if (kampung_name.lower() in [k.lower() for k in kesehatan.get("kampung", [])] and 
                kategori_name.lower() == kesehatan.get("kategori", "").lower()):
                kategori_layanan_kesehatan_di_kampung.append(kesehatan)

        if not kategori_layanan_kesehatan_di_kampung:
            dispatcher.utter_message(text=f"Maaf, Kaboo tidak menemukan layanan kesehatan kategori {kategori_name} di {kampung_name}")
            return []
        
        if kategori_layanan_kesehatan_di_kampung:
            response_text = {
                "status": "success",
                "kampung": kampung_name,
                "text_upper": f"Berikut adalah {kategori_name} yang tersedia di {kampung_name}:\n\n",
                "listLayananKesehatan": [
                    {
                        "name": kesehatan["name"],
                        "operationalHour": kesehatan["operationalHour"],
                        "lokasiKesehatan": kesehatan["lokasiKesehatan"]
                    }
                    for kesehatan in kategori_layanan_kesehatan_di_kampung
                ],
                "text_under": f"\n \n Kaboo tunggu kedatangan Sobat KLK pada {kategori_name} yang ada di {kampung_name}!"
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={"status": "error", "message": f"Maaf, saya tidak menemukan layanan kesehatan yang ada di {kampung_name}. Coba tanyakan kampung lainnya!"}
            )

        return []

GEJALA_MAPPING = {
    "batuk": "sakit umum",
    "flu": "sakit umum",
    "demam": "sakit umum",
    "pusing": "sakit umum",
    "maag": "sakit umum",
    "sakit kepala": "sakit khusus",
    "sakit gigi": "sakit khusus",
    "sakit tenggorokan": "sakit khusus",
    "sakit perut": "sakit khusus"
}

class ActionGetJenisGejalaLayananKesehatanLokasiKampung(Action):
    def name(self) -> Text:
        return "action_get_jenis_gejala_layanan_kesehatan_lokasi_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)
        gejala = next(tracker.get_latest_entity_values("gejala"), None)

        if not kampung_name or not gejala:
            dispatcher.utter_message(
                json_message={"status": "error", "message": "Silakan sebutkan nama kampung dan gejala yang dialami agar Kaboo bisa memberikan rekomendasi layanan kesehatan yang sesuai!"}
            )
            return []

        kampung_name = kampung_name.lower()
        gejala = gejala.lower()

        # Dapatkan jenis gejala dari mapping
        jenis_gejala = GEJALA_MAPPING.get(gejala)
        if not jenis_gejala:
            dispatcher.utter_message(
                json_message={"status": "error", "message": f"Maaf, Kaboo tidak mengenali gejala {gejala}. Silakan coba gejala lain!"}
            )
            return []

        # Filter layanan kesehatan berdasarkan kampung dan jenis gejala
        layanan_kesehatan_sesuai = [
            item for item in kesehatans_data 
            if kampung_name in [k.lower() for k in item["kampung"]]
            and jenis_gejala in item["gejala"]
        ]

        if layanan_kesehatan_sesuai:
            response_text = {
                "status": "success",
                "kampung": kampung_name,
                "gejala": gejala,
                "text_upper": f"Untuk gejala {gejala} yang termasuk kategori {jenis_gejala}, berikut adalah layanan kesehatan yang tersedia di {kampung_name}:\n\n",
                "listLayananKesehatan": [
                    {
                        "name": kesehatan["name"],
                        "operationalHour": kesehatan["operationalHour"],
                        "lokasiKesehatan": kesehatan["lokasiKesehatan"]
                    }
                    for kesehatan in layanan_kesehatan_sesuai
                ],
                "text_under": f"Kaboo harap Sobat KLK segera mendapat penanganan yang tepat!"
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": f"Maaf, Kaboo tidak menemukan layanan kesehatan yang menangani gejala {gejala} di {kampung_name}. Silakan coba kampung lain!"
                }
            )

        return []
    
class ActionGetLokasiKelurahanKampung(Action):
    def name(self) -> Text:
        return "action_get_lokasi_kelurahan_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if kampung_name:
            for kampung in kampungs_data:
                if kampung["name"].lower() == kampung_name.lower():
                    response_text = {
                        "status": "success",
                        "kampung": kampung_name,
                        "text": kampung["lokasiKelurahanKampung"],
                        "maps": kampung["mapsKelurahanKampung"],
                    }
                    dispatcher.utter_message(json_message=response_text)
                    return [] 
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": "Maaf, Kaboo tidak dapat menemukan lokasi kantor kelurahan kampung tersebut."
                }
            )
        return []

class ActionGetContactKampung(Action):
    def name(self) -> Text:
        return "action_get_contact_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if kampung_name:
            for kampung in kampungs_data:
                if kampung["name"].lower() == kampung_name.lower():
                    dispatcher.utter_message(text=kampung["contactKampung"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, Kaboo tidak dapat menemukan informasi tentang kampung tersebut.")
        return []


# SITUS
class ActionGetInformGeneralSitus(Action):
    def name(self) -> Text:
        return "action_get_inform_general_situs"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        
        situs_name = next(tracker.get_latest_entity_values("situs"), None)

        if situs_name:
            for situs in situss_data:
                if situs["name"].lower() == situs_name.lower():
                    dispatcher.utter_message(text=situs["informGeneralSitus"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, Kaboo tidak dapat menemukan informasi tentang situs tersebut.")
        return []
    

class ActionGetLokasiSitus(Action):
    def name(self) -> Text:
        return "action_get_lokasi_situs"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        situs_name = next(tracker.get_latest_entity_values("situs"), None)

        if situs_name:
            for situs in situss_data:
                if situs["name"].lower() == situs_name.lower():
                    response_text = {
                        "status": "success",
                        "situs": situs_name,
                        "text": situs["lokasiSitus"],
                        "maps": situs["maps"],
                    }
                    dispatcher.utter_message(json_message=response_text)
                    return [] 
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": "Maaf, Kaboo tidak dapat menemukan lokasi situs tersebut."
                }
            )
        return []
    
class ActionGetSitusLokasiKampung(Action):
    def name(self) -> Text:
        return "action_get_situs_lokasi_kampung"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kampung_name = next(tracker.get_latest_entity_values("kampung"), None)

        if not kampung_name:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": "Silakan sebutkan nama kampung agar saya bisa memberikan informasi situs yang ada!"
                }
            )
            return []

        kampung_name = kampung_name.lower()

        # Filter situs berdasarkan kampung
        situs_di_kampung = [
            item for item in situss_data 
            if item.get("kampung", "").lower() == kampung_name
        ]

        if situs_di_kampung:
            response_text = {
                "status": "success",
                "kampung": kampung_name,
                "text_upper": f"Berikut adalah situs yang ada di {kampung_name}:\n\n",
                "list": [
                    {
                        "name": situs["name"],
                        "desc": situs["informGeneralSitus"],
                    }
                    for situs in situs_di_kampung
                ],
                "text_under": f"Sobat KLK dapat mengunjungi situs tersebut untuk mengetahui sejarah dan peninggalan yang ada di {kampung_name}!"
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": f"Maaf, Kaboo tidak menemukan situs yang ada di {kampung_name}. Coba tanyakan kampung lainnya!"
                }
            )

        return []
    
class ActionGetKategoriLayananKesehatan(Action):
    def name(self) -> Text:
        return "action_get_kategori_layanan_kesehatan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kategori_name = next(tracker.get_latest_entity_values("kategori"), None)

        if not kategori_name:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": "Silakan sebutkan kategori layanan kesehatan yang ingin Anda cari (contoh: klinik, puskesmas, atau rumah sakit)!"
                }
            )
            return []

        layanan_kesehatan_by_kategori = [
            item for item in kesehatans_data 
            if kategori_name.lower() == item.get("kategori", "").lower()
        ]

        if layanan_kesehatan_by_kategori:
            response_text = {
                "status": "success",
                "kategori": kategori_name,
                "text_upper": f"Berikut adalah daftar {kategori_name} yang tersedia di sekitar Kampung Lingkar Kampus:\n\n",
                "listLayananKesehatan": [
                    {
                        "name": kesehatan["name"],
                        "operationalHour": kesehatan["operationalHour"],
                        "lokasiKesehatan": kesehatan["lokasiKesehatan"]
                    }
                    for kesehatan in layanan_kesehatan_by_kategori
                ],
                "text_under": f"Kaboo tunggu kedatangan Sobat KLK di {kategori_name} yang ada di sekitar Kampung Lingkar Kampus!"
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": f"Maaf, Kaboo tidak menemukan layanan kesehatan dengan kategori {kategori_name}. Silakan coba kategori lain seperti klinik, puskesmas, atau rumah sakit!"
                }
            )

        return []    
    
class ActionGetJenisGejalaLayananKesehatan(Action):
    def name(self) -> Text:
        return "action_get_jenis_gejala_layanan_kesehatan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        gejala = next(tracker.get_latest_entity_values("gejala"), None)

        if not gejala:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": "Silakan sebutkan gejala yang Anda alami agar Kaboo bisa memberikan rekomendasi layanan kesehatan yang sesuai!"
                }
            )
            return []

        gejala = gejala.lower()

        # Dapatkan jenis gejala dari mapping
        jenis_gejala = GEJALA_MAPPING.get(gejala)
        if not jenis_gejala:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": f"Maaf, Kaboo tidak mengenali gejala {gejala}. Silakan coba gejala lain seperti batuk, flu, demam, pusing, maag, sakit kepala, sakit gigi, sakit tenggorokan, atau sakit perut!"
                }
            )
            return []

        layanan_kesehatan_sesuai = [
            item for item in kesehatans_data 
            if jenis_gejala in item["gejala"]
        ]

        if layanan_kesehatan_sesuai:
            response_text = {
                "status": "success",
                "gejala": gejala,
                "text_upper": f"Untuk gejala {gejala} yang termasuk kategori {jenis_gejala}, berikut adalah layanan kesehatan yang tersedia di sekitar Kampung Lingkar Kampus:\n\n",
                "listLayananKesehatan": [
                    {
                        "name": kesehatan["name"],
                        "operationalHour": kesehatan["operationalHour"],
                        "lokasiKesehatan": kesehatan["lokasiKesehatan"]
                    }
                    for kesehatan in layanan_kesehatan_sesuai
                ],
                "text_under": f"Kaboo harap Sobat KLK segera mendapat penanganan tepat untuk gejala {gejala} yang Sobat KLK alami!"
            }
            dispatcher.utter_message(json_message=response_text)
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": f"Maaf, Kaboo tidak menemukan layanan kesehatan yang menangani gejala {gejala}. Silakan coba gejala lain!"
                }
            )

        return []
    
class ActionGetLokasiLayananKesehatan(Action):
    def name(self) -> Text:
        return "action_get_lokasi_layanan_kesehatan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kesehatan_name = next(tracker.get_latest_entity_values("kesehatan"), None)

        if kesehatan_name:
            for kesehatan in kesehatans_data:
                if kesehatan["name"].lower() == kesehatan_name.lower():
                    response_text = {
                        "status": "success",
                        "kesehatan": kesehatan_name,
                        "text": kesehatan["lokasiKesehatan"],
                        "maps": kesehatan["maps"],
                    }
                    dispatcher.utter_message(json_message=response_text)
                    return [] 
        else:
            dispatcher.utter_message(
                json_message={
                    "status": "error", 
                    "message": "Maaf, Kaboo tidak dapat menemukan lokasi layanan kesehatan tersebut."
                }
            )
        return []
    
class ActionGetJamOperasionalLayananKesehatan(Action):
    def name(self) -> Text:
        return "action_get_jam_operasional_layanan_kesehatan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        
        kesehatan_name = next(tracker.get_latest_entity_values("kesehatan"), None)

        if kesehatan_name:
            for kesehatan in kesehatans_data:
                if kesehatan["name"].lower() == kesehatan_name.lower():
                    dispatcher.utter_message(text=kesehatan["operationalHour"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, Kaboo tidak dapat menemukan informasi tentang jam operasional layanan kesehatan tersebut.")
        return []
    
class ActionGetContactLayananKesehatan(Action):
    def name(self) -> Text:
        return "action_get_contact_layanan_kesehatan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
        kesehatan_name = next(tracker.get_latest_entity_values("kesehatan"), None)

        if kesehatan_name:
            for kesehatan in kesehatans_data:
                if kesehatan["name"].lower() == kesehatan_name.lower():
                    dispatcher.utter_message(text=kesehatan["contactKesehatan"])
                    return [] 
        else:
            dispatcher.utter_message(text="Maaf, Kaboo tidak dapat menemukan informasi tentang kontak layanan kesehatan tersebut.")
        return []