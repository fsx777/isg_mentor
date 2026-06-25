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

# Hafıza başlatma: İnsiyatifli Devam ve Karma Modu için İndeks
if "aktif_soru_index" not in st.session_state:
    st.session_state.aktif_soru_index = 0

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

# --- DASHBOARD METRİKLERİ (Mevcut Görsel Yapı Korunmuştur) ---
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

# Veritabanından Otonom Eğitim Verilerini Çekme (FAZ 9: Gerçek Zamanlı Dinamik Soru Motoru)
latest_module = None
latest_question = None
if supabase:
    try:
        # Tüm modülleri çek
        mod_res = supabase.table("egitim_materyalleri").select("*").order("id", desc=False).execute()
        if mod_res.data and len(mod_res.data) > 0:
            total_mods = len(mod_res.data)
            # İndeks modül sayısını aşarsa başa döner
            gecerli_index = st.session_state.aktif_soru_index % total_mods
            latest_module = mod_res.data[gecerli_index]
            
            # Eğer konular bitmediyse (ilk tur) veritabanındaki orijinal soruyu getir
            if st.session_state.aktif_soru_index < total_mods:
                soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
                if soru_res.data:
                    latest_question = soru_res.data[0]
            else:
                # Karma Mod: Aynı konu için Gemini ile yepyeni ters köşe soru sentezle
                state_key = f"dinamik_soru_{st.session_state.aktif_soru_index}"
                if state_key not in st.session_state:
                    if client_available:
                        prompt = f"""Sen zorlayıcı bir İSG mentorusun. Aşağıdaki bilgiye dayanarak, daha önce sorulmamış, farklı bir klinik/mevzuat tuzağı içeren ÇOKTAN SEÇMELİ yepyeni bir soru üret. 
                        Bilgi: {latest_module['hap_bilgi']}
                        SADECE aşağıdaki formatta yanıt ver, ekstra metin ekleme:
                        SORU: [Soru Metni]
                        A: [A şıkkı]
                        B: [B şıkkı]
                        C: [C şıkkı]
                        D: [D şıkkı]
                        E: [E şıkkı]
                        CEVAP: [Sadece Doğru Şıkkın Harfi, örn: C]
                        ACIKLAMA: [Neden doğru olduğunun kısa açıklaması]"""
                        
                        try:
                            model = genai.GenerativeModel("gemini-2.5-flash")
                            response = model.generate_content(prompt)
                            lines = response.text.strip().split('\n')
                            q_dict = {}
                            for line in lines:
                                if line.startswith("SORU:"): q_dict['soru_metni'] = line.replace("SORU:", "").strip()
                                elif line.startswith("A:"): q_dict['a_sikki'] = line.replace("A:", "").strip()
                                elif line.startswith("B:"): q_dict['b_sikki'] = line.replace("B:", "").strip()
                                elif line.startswith("C:"): q_dict['c_sikki'] = line.replace("C:", "").strip()
                                elif line.startswith("D:"): q_dict['d_sikki'] = line.replace("D:", "").strip()
                                elif line.startswith("E:"): q_dict['e_sikki'] = line.replace("E:", "").strip()
                                elif line.startswith("CEVAP:"):
                                    cevap_harf = line.replace("CEVAP:", "").strip()
                                    harf_map = {"A": q_dict.get('a_sikki'), "B": q_dict.get('b_sikki'), "C": q_dict.get('c_sikki'), "D": q_dict.get('d_sikki'), "E": q_dict.get('e_sikki')}
                                    q_dict['dogru_cevap'] = harf_map.get(cevap_harf, q_dict.get('a_sikki'))
                                elif line.startswith("ACIKLAMA:"): q_dict['cozum_aciklamasi'] = line.replace("ACIKLAMA:", "").strip()
                            
                            q_dict['id'] = f"dinamik_{st.session_state.aktif_soru_index}"
                            # Eğer parsing başarılıysa kaydet
                            if 'soru_metni' in q_dict and 'dogru_cevap' in q_dict:
                                st.session_state[state_key] = q_dict
                            else:
                                raise Exception("Parsing hatası")
                        except Exception as e:
                            # Yapay zeka hata verirse orjinal soruyu yedek olarak getir
                            soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
                            if soru_res.data:
                                st.session_state[state_key] = soru_res.data[0]
                    else:
                        # API yoksa orjinal soruyu kullan
                        soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
                        if soru_res.data:
                            st.session_state[state_key] = soru_res.data[0]
                
                latest_question = st.session_state.get(state_key)
    except Exception as e:
        pass

# Sekmeler: Eğitim, Eksik Kapatma, İdari Süreçler
tab1, tab2, tab3 = st.tabs(["📚 Günlük Eğitim Programı", "🎯 Eksik Kapatma", "⚙️ İdari Takip & Radar"])

with tab1:
    st.header("Günlük İlerleme ve Adaptif Notlar")
    
    # Otonom Hap Bilgi Ekranı
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

    # FAZ 9: Adaptif Döngü ve İnteraktif Test Ekranı
    if latest_question:
        with st.expander("🧠 Otonom Botun Günlük Ters Köşe Sorusu", expanded=True):
            st.write(f"**Soru:** {latest_question['soru_metni']}")
            
            secenekler = [
                latest_question.get('a_sikki', 'A'),
                latest_question.get('b_sikki', 'B'),
                latest_question.get('c_sikki', 'C'),
                latest_question.get('d_sikki', 'D'),
                latest_question.get('e_sikki', 'E')
            ]
            
            # Dinamik key eklendi: Yeni soruya geçildiğinde şık seçimi sıfırlansın diye
            kullanici_cevabi = st.radio("Cevabını Seç:", secenekler, index=None, key=f"radio_{latest_question['id']}")
            
            if st.button("Cevapla ve Değerlendir", key=f"btn_{latest_question['id']}"):
                if kullanici_cevabi:
                    if kullanici_cevabi == latest_question['dogru_cevap']:
                        st.success("✅ Tebrikler! Doğru cevap.")
                        st.info(f"**Açıklama:** {latest_question['cozum_aciklamasi']}")
                        durum = "gecti"
                        skor = 100
                    else:
                        st.error("❌ Yanlış cevap.")
                        st.warning(f"**Doğru Cevap:** {latest_question['dogru_cevap']}")
                        st.info(f"**Neden?** {latest_question['cozum_aciklamasi']}")
                        durum = "tekrar_gerekli"
                        skor = 0
                    
                    # Supabase kullanici_ilerleme tablosuna Adaptif Kayıt
                    if supabase:
                        try:
                            supabase.table("kullanici_ilerleme").insert({
                                "bagli_modul_id": latest_module['id'],
                                "okundu_mu": True,
                                "son_sinav_skoru": skor,
                                "durum": durum
                            }).execute()
                        except Exception as e:
                            st.warning("Veritabanına kaydedilirken bir hata oluştu.")
                else:
                    st.warning("Lütfen bir şık seç!")
            
            # İnsiyatifli Devam Butonu
            st.markdown("---")
            if st.button("Sıradaki Eğitime Geç ➡️", key=f"next_{latest_question['id']}"):
                st.session_state.aktif_soru_index += 1
                st.rerun()

    # --- MEY उद्यम OKUMA KARTLARI (Mevcut Görsel Yapı Korunmuştur) ---
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
