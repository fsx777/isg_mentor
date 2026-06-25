import streamlit as st
import datetime
import os
import google.generativeai as genai
from supabase import create_client, Client

# İŞ YERİ HEKİMLİĞİ AI AJANI - PROTOKOL v4.0 (TAM OTONOM İSG MENTORU)
# Faz 3: Gemini API entegreli Python kod iskeleti + Görsel Dashboard ve Metrikler

# 1. Sayfa ve Arayüz Ayarları (Dış bulut barındırması için)
st.set_page_config(
    page_title="İSG Mentor AI | ÖSYM Radar",
    page_icon="🏛️",
    layout="wide"
)

# Gemini API Yapılandırması (Klasik google-generativeai kütüphanesi ile güncellendi)
# Streamlit dış bulutunda (Community Cloud) st.secrets kullanılacak.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client_available = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        client_available = True
    except Exception as e:
        pass

# Supabase (Hafıza) Yapılandırması
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# 2. ÖSYM Radarı ve İvedi Uyarı Sistemi (Bürokratik Takip)
def check_osym_radar():
    """
    Supabase üzerinden güncellenen ÖSYM takvimini çeker.
    """
    radar_data = {
        "status": "NORMAL",
        "message": "13 Aralık 2026 İSG/2 Sınav Duyurusu İzleniyor.",
        "deadline": None
    }

    if supabase:
        try:
            # osym_radar tablosundan en son eklenen kaydı çek
            response = supabase.table('osym_radar').select('*').order('created_at', desc=True).limit(1).execute()
            if response.data:
                veri = response.data[0]
                durum = veri.get("durum", "")
                mesaj = veri.get("mesaj", "")

                # Eğer durum "Kırmızı" ise sistemi kilitler
                if "Kırmızı" in durum:
                    radar_data["status"] = "KIRMIZI_ALARM"

                radar_data["message"] = f"{durum} - {mesaj}"
        except Exception as e:
            radar_data["message"] = f"Supabase Bağlantı Hatası: {str(e)}"
    else:
        radar_data["message"] = "Supabase bağlantısı bekleniyor."

    return radar_data

radar_status = check_osym_radar()

# KIRMIZI ALARM KONTROLÜ - Eğer aktifse tüm eğitim modülleri arka plana atılır!
if radar_status["status"] == "KIRMIZI_ALARM":
    st.error(f"🚨 KIRMIZI ALARM: {radar_status['message']}")
    st.warning("Tüm eğitim modülleri geçici olarak durduruldu. Lütfen öncelikle idari başvuru adımlarını tamamla!")
    st.info(
        "ÖSYM AİS Başvuru Adımları:\n"
        "1. osym.gov.tr (AİS) adresine giriş yap.\n"
        "2. Başvuru işlemleri tamamla ve ücreti yatır.\n"
        "3. Onay ekranını kontrol et ve süreci bitir."
    )
    st.stop() # Kodun geri kalanını çalıştırmaz, arayüzü kilitler.

# 3. Ana Arayüz (Kırmızı Alarm yoksa çalışır)
st.title("🏛️ İSG Mentor AI - v4.0")

# 📡 ÖSYM Otonom Radar Modülü
try:
    radar_sorgu = supabase.table("osym_radar").select("*").order("id", desc=True).limit(1).execute()
    if radar_sorgu.data:
        son_radar = radar_sorgu.data[0]
        if son_radar["durum"] == "Kırmızı Alarm":
            st.error(f"🚨 **ÖSYM RADAR ALARMI:** {son_radar['mesaj']}")
        else:
            st.info(f"📡 **ÖSYM Radarı Aktif:** {son_radar['mesaj']}")
except Exception as e:
    st.warning("📡 ÖSYM Radarına şu an ulaşılamıyor.")

# --- DASHBOARD METRİKLERİ (Yeni Eklenen Görsel Modül) ---
st.markdown("---")
col1, col2, col3 = st.columns(3)

# Sınava kalan gün (CSGB'nin dünkü 13 Aralık 2026 duyurusu baz alınarak dinamik hesaplanır)
exam_date = datetime.date(2026, 12, 13)
today = datetime.date.today()
days_left = (exam_date - today).days if (exam_date - today).days > 0 else 0

with col1:
    st.metric(label="🗓️ İSG/2 Sınavına Kalan", value=f"{days_left} Gün", delta="-1 Gün")
with col2:
    st.metric(label="🎯 Günlük Hedef Tamamlama", value="%75", delta="%15 Artış")
with col3:
    radar_color = "🟢 Yeşil (Güvenli)" if radar_status["status"] == "NORMAL" else "🔴 Kırmızı Alarm"
    st.metric(label="📡 ÖSYM Radar Durumu", value=radar_color, delta="Sistem Aktif", delta_color="normal")
st.markdown("---")

# Veritabanından Otonom Eğitim Verilerini Çekme (FAZ 8)
latest_module = None
latest_question = None
if supabase:
    try:
        mod_res = supabase.table("egitim_materyalleri").select("*").order("id", desc=True).limit(1).execute()
        if mod_res.data:
            latest_module = mod_res.data[0]
            soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
            if soru_res.data:
                latest_question = soru_res.data[0]
    except Exception as e:
        pass

# Sekmeler: Eğitim, Eksik Kapatma, İdari Süreçler
tab1, tab2, tab3 = st.tabs(["📚 Günlük Eğitim Programı", "🎯 Eksik Kapatma", "⚙️ İdari Takip & Radar"])

with tab1:
    st.header("Günlük İlerleme ve Adaptif Notlar")
    
    # Yeni Eklenen Otonom Hap Bilgi Ekranı
    if latest_module:
        st.success(f"📖 **Günün Konusu:** {latest_module['konu_basligi']}")
        st.info(latest_module['hap_bilgi'])
        if latest_module.get('kaynak_url'):
            st.caption(f"🔗 Kaynak: {latest_module['kaynak_url']}")
    else:
        st.write("GitHub Actions tarafından taranıp, 6331 ve 4857 mevzuat filtresinden geçen temiz veriler burada olacak.")

    # --- İLERLEME ÇUBUKLARI (Mevcut Görsel Yapı Korunmuştur) ---
    st.subheader("Modül İlerlemeleri")
    st.write("6331 Sayılı Kanun ve Mevzuat")
    st.progress(65)
    st.write("İş Yeri Hekimliği Klinik Tuzaklar")
    st.progress(40)

with tab2:
    st.header("Meydan Okuma (Ters Köşe Sorular)")
    st.write("Çelişkili 'Şüpheli' notlar veya 3-4 gün önce işlenen konulardan gelen ters köşe testler.")

    # Yeni Eklenen Otonom Ters Köşe Soru Ekranı
    if latest_question:
        with st.expander("🧠 Otonom Botun Günlük Ters Köşe Sorusu", expanded=True):
            st.write(f"**Soru:** {latest_question['soru_metni']}")
            st.write(f"A) {latest_question['a_sikki']}")
            st.write(f"B) {latest_question['b_sikki']}")
            st.write(f"C) {latest_question['c_sikki']}")
            st.write(f"D) {latest_question['d_sikki']}")
            st.write(f"E) {latest_question['e_sikki']}")
            
            st.markdown("---")
            cevap_goster = st.checkbox("Cevabı ve Açıklamayı Göster")
            if cevap_goster:
                st.success(f"**Doğru Cevap:** {latest_question['dogru_cevap']}")
                st.info(f"**Neden?** {latest_question['cozum_aciklamasi']}")

    # --- MEYDAN OKUMA KARTLARI (Mevcut Görsel Yapı Korunmuştur) ---
    with st.expander("⚠️ Şüpheli Not: Gece Çalışma Süreleri ve Kadın İşçiler"):
        st.warning("Bu bilgi son taramada çelişkili bulundu. Lütfen mevzuatı doğrula.")
        st.write("**Gelen Veri:** Kadın işçiler gece postasında 7.5 saatten fazla çalıştırılamaz. (Turizm sektörü hariç)")
        st.write("**Görev:** Gemini ile bu bilginin 4857 sayılı kanundaki istisnalarını tartış.")

    with st.expander("🧠 Ters Köşe Soru: İSG Kurul Toplantı Periyotları"):
        st.info("3 gün önce öğrendiğin konunun kalıcılık testi.")
        st.write("**Soru:** Çok tehlikeli sınıfta yer alan ve 150 çalışanı olan bir iş yerinde İSG kurulu en az hangi sıklıkta toplanmalıdır?")
        st.write("Cevabını aşağıdaki sohbet alanından mentora ilet.")

    if supabase:
        st.success("Supabase hafıza bağlantısı aktif. Geçmiş veriler çekilmeye hazır.")
    else:
        st.warning("Supabase bağlantısı bekleniyor. (SUPABASE_URL ve SUPABASE_KEY çevresel değişkenleri eksik)")

with tab3:
    st.header("ÖSYM Radarı & Ağ Durumu")
    st.write("**Alan Adı Bağlantısı:** isg.mertuspatronus.com (Cloudflare üzerinden şifreli, VPS bağlantısı yok)")
    st.info(f"Mevcut Radar Durumu: {radar_status['message']}")

# 4. Hekim - Mentor Sohbet Arayüzü (Hafıza Entegreli)
st.markdown("---")
st.subheader("🤖 İSG Mentor ile Konuş")

# Hafıza başlatma (Session State) ve Supabase'den geçmişi çekme
if "messages" not in st.session_state:
    st.session_state.messages = []
    if supabase:
        try:
            # Önceki sohbetleri veritabanından çek (Son 10 mesaj)
            res = supabase.table("chat_history").select("*").order("created_at", desc=False).limit(10).execute()
            if res.data:
                for row in res.data:
                    st.session_state.messages.append({"role": row["role"], "content": row["content"]})
        except Exception:
            pass

# Ekrandaki eski mesajları çiz
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("6331 sayılı kanun veya klinik tuzaklar hakkında sor...")

if user_input:
    # Kullanıcı mesajını ekrana bas ve hafızaya al
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Veritabanına kaydet
    if supabase:
        try:
            supabase.table("chat_history").insert({"role": "user", "content": user_input}).execute()
        except Exception:
            pass

    if client_available:
        try:
            # Geçmiş konuşmaları bağlam (context) olarak Gemini'ye sunmak için birleştir
            context = "Sen bir İş Yeri Hekimliği AI mentorusun. Sadece 6331 sayılı İSG kanunu ve tıbbi mevzuat çerçevesinde net, kısa ve profesyonel cevap ver.\n\nÖnceki Konuşmalar:\n"
            for m in st.session_state.messages[-5:]: # Son 5 mesajı bağlama ekle ki konuyu hatırlasın
                context += f"{m['role'].capitalize()}: {m['content']}\n"
            context += f"\nGüncel Soru: {user_input}"

            # Yeni nesil açık motorlar ile fallback döngüsü
            calisan_model = None
            hata_mesaji = ""
            modeller_listesi = ["gemini-2.5-flash", "gemini-flash-latest"]

            for denenen_model in modeller_listesi:
                try:
                    model = genai.GenerativeModel(denenen_model)
                    response = model.generate_content(context)
                    calisan_model = denenen_model
                    break  # Cevap alındıysa döngüyü kır
                except Exception as e:
                    hata_mesaji = str(e)
                    continue

            if calisan_model:
                bot_reply = response.text
                st.chat_message("assistant").write(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})

                # Asistan cevabını veritabanına kaydet
                if supabase:
                    try:
                        supabase.table("chat_history").insert({"role": "assistant", "content": bot_reply}).execute()
                    except Exception:
                        pass
            else:
                st.chat_message("assistant").error(f"API Hatası (Yeni Nesil Motorlar): {hata_mesaji}")

        except Exception as e:
            st.chat_message("assistant").error(f"Sistem Hatası: {e}")
    else:
        st.chat_message("assistant").error("Sistem Uyarısı: GEMINI_API_KEY çevresel değişkeni bulunamadı. Lütfen dış bulut ayarlarından veya terminalden anahtarı tanımla.")
