from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Rule-Based responses ──
rules = {
    "kepala"  : "Sakit kepala bisa disebabkan dehidrasi, kurang tidur, atau stres. Coba minum 2 gelas air dan istirahat di tempat tenang. Jika berlanjut lebih dari 6 jam atau disertai demam tinggi, segera ke dokter ya!",
    "pusing"  : "Pusing bisa tanda dehidrasi atau tekanan darah rendah. Istirahat dan minum air putih. Hindari berdiri terlalu cepat.",
    "demam"   : "Demam adalah respons alami tubuh melawan infeksi. Kompres dengan air hangat, minum banyak air. Jika suhu > 39°C atau berlangsung > 3 hari, segera ke dokter.",
    "batuk"   : "Batuk bisa karena iritasi atau infeksi. Minum air hangat dengan madu dan jahe. Hindari udara dingin dan debu.",
    "pilek"   : "Pilek biasanya disebabkan virus. Istirahat cukup, minum air hangat, dan konsumsi vitamin C. Biasanya sembuh dalam 5-7 hari.",
    "mual"    : "Mual bisa disebabkan maag atau dehidrasi. Makan sedikit tapi sering, hindari makanan pedas dan berlemak. Minum air putih pelan-pelan.",
    "perut"   : "Sakit perut bisa banyak penyebabnya. Jika ringan, coba istirahat dan hindari makanan berat. Jika sangat nyeri atau disertai diare lebih dari 2 hari, periksa ke dokter.",
    "diare"   : "Perbanyak minum air putih atau oralit untuk mencegah dehidrasi. Hindari makanan berminyak. Jika lebih dari 3 hari atau ada darah, segera ke dokter.",
    "imun"    : "Untuk meningkatkan imunitas: tidur 7-8 jam per malam, konsumsi buah kaya vitamin C (jeruk, mangga), olahraga ringan 30 menit/hari, dan kelola stres dengan baik.",
    "stres"   : "Coba teknik pernapasan 4-7-8: hirup 4 detik, tahan 7 detik, hembuskan 8 detik. Olahraga ringan, meditasi, dan berbicara dengan orang terpercaya juga sangat membantu.",
    "cemas"   : "Rasa cemas itu wajar, tapi perlu dikelola. Coba tarik napas dalam, tuliskan kekhawatiranmu di jurnal, dan batasi konsumsi berita negatif. Jika terasa berat, jangan ragu konsultasi ke psikolog.",
    "tidur"   : "Untuk tidur lebih baik: matikan layar 1 jam sebelum tidur, jaga suhu kamar sejuk, tidur di jam yang sama setiap hari, dan hindari kafein setelah jam 3 sore.",
    "obat"    : "Paracetamol untuk orang dewasa: 500mg-1000mg per minum, maksimal 4x sehari dengan jarak 4-6 jam. Selalu konsumsi setelah makan agar tidak mengiritasi lambung.",
    "vitamin" : "Vitamin C 500-1000mg/hari baik untuk imunitas. Vitamin D penting untuk tulang, bisa didapat dari sinar matahari pagi. Konsultasikan ke dokter untuk suplemen yang tepat.",
    "berat"   : "Untuk menjaga berat badan ideal: perbanyak sayur dan protein, kurangi gula dan karbohidrat olahan, minum air putih sebelum makan, dan olahraga rutin minimal 3x seminggu.",
    "olahraga": "Olahraga ringan seperti jalan kaki 30 menit/hari sudah sangat bermanfaat. Lakukan minimal 3-5x seminggu. Jangan lupa pemanasan sebelum dan pendinginan sesudah olahraga.",
}

def rule_based(text):
    text_lower = text.lower()
    for keyword, response in rules.items():
        if keyword in text_lower:
            return response, "Rule-Based"
    return None, None

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
    response, layer = rule_based(user_message)

    # Fallback jika tidak ada keyword
    if not response:
        response = (
            "Maaf, saya belum memiliki informasi spesifik untuk pertanyaan itu. "
            "Coba tanyakan seputar gejala umum (kepala, demam, batuk), obat-obatan, "
            "nutrisi, atau tips kesehatan ya! Untuk kondisi serius, selalu konsultasikan ke dokter."
        )
        layer = "Rule-Based (Fallback)"

    return jsonify({
        "response": response,
        "layer"   : layer
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print(f"  MedChat AI - Server Berjalan di port {port}!")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=port)
