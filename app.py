from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import os
import requests as http_requests

app = Flask(__name__)
CORS(app)

# ══════════════════════════════════
# LAYER 2 — NLP
# ══════════════════════════════════
try:
    from nlp_model import nlp_classifier
    NLP_AVAILABLE = True
    print(f"[APP] Layer 2 NLP aktif! Akurasi: {nlp_classifier.accuracy:.2%}")
except Exception as e:
    NLP_AVAILABLE = False
    print(f"[APP] Layer 2 NLP tidak tersedia: {e}")

# ══════════════════════════════════
# LAYER 3 — GROQ LLM
# ══════════════════════════════════
GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
print(f"[APP] Layer 3 Groq LLM aktif! Key: {GROQ_API_KEY[:10]}...")

# ══════════════════════════════════
# LAYER 1 — RULE-BASED
# ══════════════════════════════════
EMERGENCY_KEYWORDS = [
    "sesak napas berat", "tidak sadar", "kejang", "stroke",
    "serangan jantung", "nyeri dada berat", "sulit bernapas",
    "pingsan", "muntah darah", "berak darah", "demam sangat tinggi",
    "40 derajat", "kaku leher", "lumpuh", "tidak bisa bicara"
]

RULES = {
    "sakit_kepala": {
        "keywords": ["sakit kepala", "kepala sakit", "kepala nyeri", "pusing kepala",
                     "kepala berdenyut", "migrain", "kepala berat", "nyeri kepala",
                     "kepala cenat cenut", "kepala cekot"],
        "responses": [
            "Sakit kepala bisa disebabkan dehidrasi, kurang tidur, atau stres. Coba minum 2 gelas air putih dan istirahat di tempat gelap yang tenang. Jika nyeri berlanjut lebih dari 6 jam, segera ke dokter.",
            "Ada beberapa penyebab sakit kepala: kurang minum air, terlalu lama di depan layar, atau kurang tidur. Istirahatkan mata, minum air, dan hindari suara bising.",
            "Kepala nyeri bisa jadi tanda tubuh butuh istirahat. Pastikan kamu cukup minum air minimal 8 gelas per hari dan tidur 7-8 jam."
        ],
        "follow_up": "Apakah sakit kepalanya disertai mual, demam, atau gangguan penglihatan?",
        "confidence": 0.95
    },
    "pusing": {
        "keywords": ["pusing", "vertigo", "kepala berputar", "sempoyongan",
                     "linglung", "kepala melayang", "oleng", "limbung"],
        "responses": [
            "Pusing bisa disebabkan tekanan darah rendah, dehidrasi, atau kurang makan. Duduk atau berbaring sejenak, minum air putih, dan makan sesuatu.",
            "Vertigo dan pusing sering terjadi karena gangguan keseimbangan. Istirahat, hindari gerakan mendadak, dan minum air yang cukup."
        ],
        "follow_up": "Apakah pusing muncul saat berdiri tiba-tiba atau terus-menerus?",
        "confidence": 0.92
    },
    "demam": {
        "keywords": ["demam", "panas tinggi", "suhu tinggi", "badan panas", "meriang",
                     "menggigil", "suhu badan naik", "febris", "badan hangat",
                     "38 derajat", "39 derajat", "panas badan"],
        "responses": [
            "Demam adalah respons alami tubuh melawan infeksi. Kompres air hangat di dahi, minum banyak air dan istirahat. Paracetamol 500mg bisa membantu turunkan demam.",
            "Saat demam, perbanyak minum cairan untuk mencegah dehidrasi. Jika demam lebih dari 39 derajat atau berlangsung lebih dari 3 hari, segera ke dokter.",
        ],
        "follow_up": "Berapa suhu tubuhmu sekarang dan sudah berapa hari demam?",
        "confidence": 0.95
    },
    "flu": {
        "keywords": ["flu", "influenza", "pilek", "hidung meler", "hidung tersumbat",
                     "bersin", "ingus", "hidung berair", "common cold", "masuk angin"],
        "responses": [
            "Flu biasanya disebabkan virus dan akan sembuh sendiri dalam 5-7 hari. Istirahat yang cukup, minum air hangat, konsumsi vitamin C.",
            "Untuk mengatasi flu: istirahat total, minum banyak cairan hangat, konsumsi buah kaya vitamin C. Gunakan masker agar tidak menular."
        ],
        "follow_up": "Apakah flunya disertai demam atau sakit tenggorokan?",
        "confidence": 0.90
    },
    "batuk": {
        "keywords": ["batuk", "batuk-batuk", "batuk kering", "batuk berdahak",
                     "batuk berdarah", "batuk tidak berhenti", "tenggorokan gatal",
                     "batuk terus", "susah berhenti batuk"],
        "responses": [
            "Batuk kering: minum air hangat dengan madu, hindari udara dingin dan debu. Batuk berdahak: minum banyak air agar dahak encer dan mudah keluar.",
            "Untuk meredakan batuk: minum teh jahe dengan madu, berkumur air garam hangat. Jika batuk lebih dari 2 minggu, segera periksa ke dokter."
        ],
        "follow_up": "Apakah batuknya kering atau berdahak? Sudah berapa lama?",
        "confidence": 0.92
    },
    "mual": {
        "keywords": ["mual", "mau muntah", "ingin muntah", "perut tidak enak",
                     "eneg", "mual-mual", "rasa ingin muntah", "sebah"],
        "responses": [
            "Mual bisa disebabkan maag, mabuk perjalanan, atau kehamilan. Makan sedikit tapi sering, hindari makanan pedas dan berlemak. Minum air jahe hangat bisa membantu.",
        ],
        "follow_up": "Apakah mualnya disertai muntah atau sakit perut?",
        "confidence": 0.90
    },
    "muntah": {
        "keywords": ["muntah", "muntah-muntah", "keluar semua", "memuntahkan", "muntah terus"],
        "responses": [
            "Saat muntah, yang paling penting adalah mencegah dehidrasi. Minum cairan sedikit demi sedikit seperti oralit atau air kelapa. Jika muntah lebih dari 6 jam atau ada darah, segera ke dokter."
        ],
        "follow_up": "Sudah berapa kali muntah dan apakah ada darah?",
        "confidence": 0.92
    },
    "diare": {
        "keywords": ["diare", "mencret", "BAB cair", "berak cair", "buang air besar terus",
                     "feses cair", "perut mulas buang air"],
        "responses": [
            "Diare menyebabkan banyak cairan keluar, segera minum oralit untuk mengganti elektrolit. Hindari makanan pedas dan berlemak. Jika lebih dari 3 hari atau ada darah, ke dokter.",
        ],
        "follow_up": "Sudah berapa kali BAB cair hari ini dan apakah ada lendir atau darah?",
        "confidence": 0.93
    },
    "sakit_perut": {
        "keywords": ["sakit perut", "perut sakit", "nyeri perut", "perut mulas",
                     "kram perut", "perut melilit", "maag", "lambung sakit",
                     "ulu hati sakit", "perut kembung", "begah"],
        "responses": [
            "Sakit perut bisa disebabkan maag, gas berlebih, atau infeksi. Untuk maag: makan teratur, hindari makanan asam dan pedas. Antasida bisa membantu meredakan nyeri lambung.",
        ],
        "follow_up": "Di bagian mana perut yang sakit dan sudah berapa lama?",
        "confidence": 0.91
    },
    "sesak_napas": {
        "keywords": ["sesak napas", "napas pendek", "susah napas", "napas berat",
                     "dada sesak", "asma", "napas berbunyi", "ngos-ngosan"],
        "responses": [
            "Sesak napas ringan: duduk tegak, tarik napas perlahan lewat hidung dan hembuskan lewat mulut.",
            "PERINGATAN: Jika sesak sangat berat, bibir membiru, atau tidak membaik dalam 10 menit, segera ke IGD!"
        ],
        "follow_up": "Seberapa berat sesaknya dan apakah kamu punya riwayat asma?",
        "confidence": 0.93
    },
    "gatal": {
        "keywords": ["gatal", "gatal-gatal", "bentol", "biduran", "alergi kulit",
                     "ruam", "ruam kulit", "kulit gatal", "kulit merah", "dermatitis", "eksim"],
        "responses": [
            "Gatal bisa disebabkan alergi, gigitan serangga, atau kulit kering. Jangan digaruk! Kompres dingin untuk mengurangi rasa gatal. Antihistamin oral bisa membantu.",
        ],
        "follow_up": "Apakah gatalnya disertai ruam atau bentol dan di bagian tubuh mana?",
        "confidence": 0.88
    },
    "stres": {
        "keywords": ["stres", "stress", "tertekan", "beban pikiran", "banyak pikiran",
                     "pikiran kacau", "tidak tenang", "gelisah", "resah", "khawatir"],
        "responses": [
            "Stres adalah respons normal tubuh. Coba teknik 4-7-8: hirup 4 detik, tahan 7 detik, hembuskan 8 detik. Lakukan 4 kali berturut-turut.",
        ],
        "follow_up": "Sudah berapa lama kamu merasakan stres ini?",
        "confidence": 0.88
    },
    "cemas": {
        "keywords": ["cemas", "anxious", "anxiety", "panik", "serangan panik",
                     "takut berlebihan", "was-was", "gugup berlebihan", "phobia"],
        "responses": [
            "Teknik grounding 5-4-3-2-1 bisa membantu: sebutkan 5 hal yang bisa kamu lihat, 4 yang bisa disentuh, 3 yang bisa didengar, 2 yang bisa dicium, 1 yang bisa dirasa.",
        ],
        "follow_up": "Apakah kecemasannya sampai mengganggu aktivitas sehari-hari?",
        "confidence": 0.88
    },
    "depresi": {
        "keywords": ["depresi", "sedih terus", "tidak semangat", "tidak ada motivasi",
                     "hampa", "putus asa", "tidak berguna", "mau menyerah"],
        "responses": [
            "Perasaan sedih dan hampa yang berkepanjangan perlu diperhatikan serius. Kamu tidak sendirian! Coba hubungi orang yang kamu percaya.",
        ],
        "follow_up": "Sudah berapa lama perasaan ini berlangsung?",
        "confidence": 0.85
    },
    "insomnia": {
        "keywords": ["susah tidur", "tidak bisa tidur", "insomnia", "tidur tidak nyenyak",
                     "sering terbangun", "begadang terus", "tidur terganggu"],
        "responses": [
            "Untuk tidur lebih baik: matikan semua layar 1 jam sebelum tidur, jaga suhu kamar 18-22 derajat, tidur dan bangun di jam yang sama setiap hari.",
        ],
        "follow_up": "Sudah berapa lama mengalami susah tidur?",
        "confidence": 0.88
    },
    "obat": {
        "keywords": ["obat", "paracetamol", "ibuprofen", "amoxicillin", "antasida",
                     "obat apa", "minum obat", "dosis obat", "efek samping obat"],
        "responses": [
            "Paracetamol: 500-1000mg per minum, maksimal 4x per hari, jarak minimal 4-6 jam. Ibuprofen: 200-400mg per minum, maksimal 3x per hari, selalu setelah makan.",
        ],
        "follow_up": "Obat apa yang ingin kamu tanyakan?",
        "confidence": 0.88
    },
    "vitamin": {
        "keywords": ["vitamin c", "vitamin d", "vitamin b", "vitamin e", "suplemen",
                     "multivitamin", "zinc", "omega 3", "probiotik"],
        "responses": [
            "Vitamin C: 500-1000mg per hari untuk imunitas. Vitamin D: 400-800 IU per hari atau paparan matahari pagi 15 menit. Zinc: 8-11mg per hari.",
        ],
        "follow_up": "Vitamin atau suplemen apa yang ingin kamu ketahui lebih lanjut?",
        "confidence": 0.87
    },
    "imunitas": {
        "keywords": ["imunitas", "imun", "daya tahan tubuh", "mudah sakit",
                     "sering sakit", "kekebalan tubuh", "meningkatkan imun"],
        "responses": [
            "Untuk meningkatkan imunitas: tidur 7-8 jam per malam, konsumsi buah dan sayur kaya antioksidan, olahraga 30 menit 5x per minggu.",
        ],
        "follow_up": "Apakah kamu sering sakit atau ingin meningkatkan imunitas secara umum?",
        "confidence": 0.88
    },
    "olahraga": {
        "keywords": ["olahraga", "latihan", "gym", "fitness", "lari", "jogging",
                     "bersepeda", "renang", "yoga", "peregangan", "stretching"],
        "responses": [
            "WHO merekomendasikan 150 menit olahraga intensitas sedang per minggu. Tambah latihan kekuatan 2x per minggu untuk kesehatan optimal.",
        ],
        "follow_up": "Apa tujuan olahragamu? Menurunkan berat badan, menjaga kesehatan, atau meningkatkan stamina?",
        "confidence": 0.85
    },
    "tidur": {
        "keywords": ["tidur", "kurang tidur", "kualitas tidur", "jam tidur",
                     "ngantuk", "mengantuk", "tidur siang"],
        "responses": [
            "Orang dewasa butuh 7-9 jam tidur per malam. Tidur kurang dari 6 jam terus-menerus meningkatkan risiko penyakit jantung dan diabetes.",
        ],
        "follow_up": "Berapa jam biasanya kamu tidur dan apakah kamu merasa segar saat bangun?",
        "confidence": 0.87
    },
    "nyeri_otot": {
        "keywords": ["nyeri otot", "otot sakit", "pegal", "pegal-pegal", "otot kaku",
                     "kram otot", "badan pegal", "badan sakit semua", "nyeri sendi",
                     "sendi sakit", "encok", "rematik", "asam urat"],
        "responses": [
            "Nyeri otot setelah olahraga normal dan akan membaik dalam 2-3 hari. Kompres hangat, pijat lembut, dan stretching ringan bisa membantu.",
        ],
        "follow_up": "Apakah nyerinya setelah aktivitas fisik atau tiba-tiba?",
        "confidence": 0.89
    },
    "gigi": {
        "keywords": ["sakit gigi", "gigi nyeri", "gusi berdarah", "gusi bengkak",
                     "sariawan", "mulut berbau", "bau mulut", "gigi berlubang"],
        "responses": [
            "Sakit gigi: kumur air garam hangat, kompres dingin dari luar pipi, paracetamol untuk nyeri sementara. Segera ke dokter gigi!",
        ],
        "follow_up": "Apakah sakit giginya disertai bengkak di pipi atau demam?",
        "confidence": 0.87
    },
    "nutrisi": {
        "keywords": ["makanan sehat", "nutrisi", "diet sehat", "gizi", "makan sehat",
                     "pola makan", "makanan bergizi", "kalori", "protein", "karbohidrat"],
        "responses": [
            "Pola makan sehat: isi setengah piring dengan sayur dan buah, seperempat protein, seperempat karbohidrat kompleks. Minum 8 gelas air per hari.",
        ],
        "follow_up": "Apakah ada kondisi kesehatan tertentu yang ingin kamu atur lewat pola makan?",
        "confidence": 0.85
    },
}

# ══════════════════════════════════
# FUNGSI LAYER 1, 2, 3
# ══════════════════════════════════

def check_emergency(text):
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def layer1_rule_based(text):
    if check_emergency(text):
        return (
            "PERINGATAN DARURAT: Gejala yang kamu sebutkan memerlukan penanganan medis SEGERA! "
            "Hubungi IGD rumah sakit terdekat atau telepon 119. Jangan tunda!",
            "Rule-Based (Emergency)", 1.0
        )
    normalized = normalize_text(text)
    best_match = None
    best_score = 0
    for topic, data in RULES.items():
        score = 0
        for keyword in data["keywords"]:
            if keyword in normalized:
                weight = len(keyword.split()) * 0.15
                score += data["confidence"] + weight
        if score > best_score:
            best_score = score
            best_match = topic
    if best_match and best_score > 0:
        import random
        data = RULES[best_match]
        response = random.choice(data["responses"])
        confidence = min(best_score, 1.0)
        follow_up = data.get("follow_up")
        if follow_up:
            response += f"\n\n{follow_up}"
        return response, f"Rule-Based ({confidence:.0%})", confidence
    return None, None, 0.0

def layer2_nlp(text):
    if not NLP_AVAILABLE:
        return None, None, 0.0
    try:
        category, confidence = nlp_classifier.predict(text, threshold=0.15)
        if category:
            response = nlp_classifier.get_response(category)
            if response:
                top3 = nlp_classifier.get_top_predictions(text)
                top3_str = " | ".join([f"{p['category']} {p['confidence']}%" for p in top3[:3]])
                response += f"\n\n📊 Analisis: {top3_str}"
                return response, f"NLP-TF-IDF ({confidence:.0%})", confidence
    except Exception as e:
        print(f"[NLP Error] {e}")
    return None, None, 0.0

def layer3_groq(text):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "Kamu adalah MedChat AI, asisten kesehatan berbahasa Indonesia. Berikan informasi kesehatan yang akurat, ramah, dan mudah dipahami. Maksimal 3-4 kalimat. Selalu ingatkan konsultasi ke dokter untuk kondisi serius. Jangan mendiagnosis penyakit secara pasti."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }
        response = http_requests.post(
            GROQ_URL,
            json=payload,
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            text_response = data["choices"][0]["message"]["content"]
            text_response += "\n\n⚕️ Catatan: Untuk kondisi serius, selalu konsultasikan ke dokter."
            return text_response, "Groq LLM (Llama3)", 0.99
        else:
            print(f"[Groq Error] Status: {response.status_code} | {response.text[:200]}")
            return None, None, 0.0
    except Exception as e:
        print(f"[Groq Error] {e}")
        return None, None, 0.0

# ══════════════════════════════════
# ROUTES
# ══════════════════════════════════

@app.route("/")
def index():
    return send_from_directory("static", "medchat-landing.html")

@app.route("/chat")
def chat_page():
    return send_from_directory("static", "medchat-chat.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"response": "Pesan tidak boleh kosong.", "layer": "Error"}), 400

    # Layer 1: Rule-Based
    response, layer, confidence = layer1_rule_based(user_message)

    # Layer 2: NLP
    if not response:
        response, layer, confidence = layer2_nlp(user_message)

    # Layer 3: Groq LLM
    if not response:
        response, layer, confidence = layer3_groq(user_message)

    # Fallback
    if not response:
        response = (
            "Maaf, saya belum bisa menjawab pertanyaan itu saat ini.\n\n"
            "Coba tanyakan seputar gejala umum, obat-obatan, kesehatan mental, atau nutrisi ya!\n"
            "Untuk kondisi serius, selalu konsultasikan ke dokter."
        )
        layer = "Fallback"
        confidence = 0.0

    return jsonify({
        "response": response,
        "layer": layer,
        "confidence": round(confidence * 100),
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "layer1": f"Rule-Based aktif ({len(RULES)} topik)",
        "layer2": f"NLP aktif (akurasi {nlp_classifier.accuracy:.2%})" if NLP_AVAILABLE else "NLP tidak tersedia",
        "layer3": "Groq LLM aktif",
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  MedChat AI — Layer 1 + 2 + 3 Aktif")
    print(f"  Layer 1: Rule-Based ({len(RULES)} topik)")
    if NLP_AVAILABLE:
        print(f"  Layer 2: NLP TF-IDF (akurasi {nlp_classifier.accuracy:.2%})")
    print(f"  Layer 3: Groq LLM aktif ({GROQ_MODEL})")
    print(f"  Server : http://127.0.0.1:{port}")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=port)
