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

# Gemini API Yapılandırması
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

# 2. ÖSYM Radarı ve İvedi Uyarı Sistemi
def check_osym_radar():
    radar_data = {
        "status": "NORMAL",
        "message": "13 Aralık 2026 İSG/2 Sınav Duyurusu İzleniyor.",
        "deadline": None
    }
    if supabase:
        try:
            response = supabase.table('osym_radar').select('*').order('created_at', desc=True).limit(1).execute()
            if response.data:
                veri = response.data[0]
                durum = veri.get("durum", "")
                mesaj = veri.get("mesaj", "")
                if "Kırmızı" in durum:
                    radar_data["status"] = "KIRMIZI_ALARM"
                radar_data["message"] = f"{durum} - {mesaj}"
        except Exception as e:
            radar_data["message"] = f"Supabase Bağlantı Hatası: {str(e)}"
    else:
        radar_data["message"] = "Supabase bağlantısı bekleniyor."
    return radar_data

radar_status = check_osym_radar()

if radar_status["status"] == "KIRMIZI_ALARM":
    st.error(f"🚨 KIRMIZI ALARM: {radar_status['message']}")
    st.warning("Tüm eğitim modülleri geçici olarak durduruldu. Lütfen öncelikle idari başvuru adımlarını tamamla!")
    st.info(
        "ÖSYM AİS Başvuru Adımları:\n"
        "1. osym.gov.tr (AİS) adresine giriş yap.\n"
        "2. Başvuru işlemleri tamamla ve ücreti yatır.\n"
        "3. Onay ekranını kontrol et ve süreci bitir."
    )
    st.stop()

# 3. Ana Arayüz
st.title("🏛️ İSG Mentor AI - v4.0")

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

st.markdown("---")
col1, col2, col3 = st.columns(3)

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

# Veritabanından Otonom Eğitim Verilerini Çekme
latest_module = None
latest_question = None
total_mods = 0

if supabase:
    try:
        mod_res = supabase.table("egitim_materyalleri").select("*").order("id", desc=False).execute()
        if mod_res.data and len(mod_res.data) > 0:
            total_mods = len(mod_res.data)
            gecerli_index = st.session_state.aktif_soru_index % total_mods
            latest_module = mod_res.data[gecerli_index]
            
            if st.session_state.aktif_soru_index < total_mods:
                soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
                if soru_res.data:
                    latest_question = soru_res.data[0]
            else:
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
                            text_resp = response.text.strip()
                            q_dict = {}

                            match_soru = re.search(r'SORU:\s*(.*?)(?=\nA:|\Z)', text_resp, re.DOTALL)
                            match_a = re.search(r'A:\s*(.*?)(?=\nB:|\Z)', text_resp, re.DOTALL)
                            match_b = re.search(r'B:\s*(.*?)(?=\nC:|\Z)', text_resp, re.DOTALL)
                            match_c = re.search(r'C:\s*(.*?)(?=\nD:|\Z)', text_resp, re.DOTALL)
                            match_d = re.search(r'D:\s*(.*?)(?=\nE:|\Z)', text_resp, re.DOTALL)
                            match_e = re.search(r'E:\s*(.*?)(?=\nCEVAP:|\Z)', text_resp, re.DOTALL)
                            match_cevap = re.search(r'CEVAP:\s*([A-E])', text_resp)
                            match_aciklama = re.search(r'ACIKLAMA:\s*(.*)', text_resp, re.DOTALL)

                            if match_soru: q_dict['soru_metni'] = match_soru.group(1).strip()
                            if match_a: q_dict['a_sikki'] = match_a.group(1).strip()
                            if match_b: q_dict['b_sikki'] = match_b.group(1).strip()
                            if match_c: q_dict['c_sikki'] = match_c.group(1).strip()
                            if match_d: q_dict['d_sikki'] = match_d.group(1).strip()
                            if match_e: q_dict['e_sikki'] = match_e.group(1).strip()

                            if match_cevap:
                                cevap_harf = match_cevap.group(1).strip()
                                harf_map = {"A": q_dict.get('a_sikki'), "B": q_dict.get('b_sikki'), "C": q_dict.get('c_sikki'), "D": q_dict.get('d_sikki'), "E": q_dict.get('e_sikki')}
                                q_dict['dogru_cevap'] = harf_map.get(cevap_harf, q_dict.get('a_sikki'))
    
                            if match_aciklama: q_dict['cozum_aciklamasi'] = match_aciklama.group(1).strip()
                            
                            q_dict['id'] = f"dinamik_{st.session_state.aktif_soru_index}"
                            if 'soru_metni' in q_dict and 'dogru_cevap' in q_dict:
                                st.session_state[state_key] = q_dict
                            else:
                                raise Exception("Parsing hatası")
                        except Exception as e:
                            soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
                            if soru_res.data:
                                st.session_state[state_key] = soru_res.data[0]
                    else:
                        soru_res = supabase.table("soru_bankasi").select("*").eq("bagli_modul_id", latest_module["id"]).limit(1).execute()
                        if soru_res.data:
                            st.session_state[state_key] = soru_res.data[0]
                latest_question = st.session_state.get(state_key)
    except Exception as e:
        pass

tab1, tab2, tab3, tab4 = st.tabs(["📚 Günlük Eğitim Programı", "🎯 Eksik Kapatma", "⚙️ İdari Takip & Radar", "🚀 Deep Hunter"])

with tab1:
    st.header("Günlük İlerleme ve Adaptif Notlar")
    
    if latest_module:
        st.success(f"📖 **Günün Konusu:** {latest_module['konu_basligi']}")
        st.info(latest_module['hap_bilgi'])
        if latest_module.get('kaynak_url'):
            st.caption(f"🔗 Kaynak: {latest_module['kaynak_url']}")
    else:
        st.write("GitHub Actions veya Deep Hunter tarafından çekilen veriler burada olacak.")

    # --- GERÇEK ZAMANLI DİNAMİK İLERLEME ÇUBUĞU ---
    st.subheader("Gerçek Zamanlı İlerleme")
    
    toplam_modul_sayisi = total_mods
    basarili_modul_sayisi = 0
    
    if supabase:
        try:
            il_res = supabase.table("kullanici_ilerleme").select("bagli_modul_id").eq("durum", "gecti").execute()
            if il_res.data:
                # set() kullanarak aynı konunun tekrarlanan çözümlerini filtreliyoruz
                basarili_modul_sayisi = len(set([row["bagli_modul_id"] for row in il_res.data]))
        except Exception:
            pass
            
    genel_oran = int((basarili_modul_sayisi / toplam_modul_sayisi) * 100) if toplam_modul_sayisi > 0 else 0
    if genel_oran > 100: genel_oran = 100
    
    st.write("📚 Kütüphane Tüketim Oranı (Genel Başarı)")
    st.progress(genel_oran)
    st.caption(f"Tamamlanan Benzersiz Konu: **{basarili_modul_sayisi}** / Toplam Cephane: **{toplam_modul_sayisi}**")

with tab2:
    st.header("Meydan Okuma (Ters Köşe Sorular)")
    st.write("Çelişkili 'Şüpheli' notlar veya 3-4 gün önce işlenen konulardan gelen ters köşe testler.")

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
            
            st.markdown("---")
            if st.button("Sıradaki Eğitime Geç ➡️", key=f"next_{latest_question['id']}"):
                st.session_state.aktif_soru_index += 1
                st.rerun()

    if supabase:
        st.success("Supabase hafıza bağlantısı aktif. Geçmiş veriler çekilmeye hazır.")
    else:
        st.warning("Supabase bağlantısı bekleniyor. (SUPABASE_URL ve SUPABASE_KEY çevresel değişkenleri eksik)")

with tab3:
    st.header("ÖSYM Radarı & Ağ Durumu")
    st.write("**Alan Adı Bağlantısı:** isg.mertuspatronus.com (Cloudflare üzerinden şifreli, VPS bağlantısı yok)")
    st.info(f"Mevcut Radar Durumu: {radar_status['message']}")

with tab4:
    st.header("Sınırsız Avcı (Deep Hunter) Kontrol Merkezi")
    st.write("Veritabanına internetten süzülmüş yepyeni İSG soruları ve klinik tuzaklar indirmek için avcıyı ateşle.")
    
    if st.button("🚀 Deep Hunter'ı Ateşle (Yeni Cephane Bul)", use_container_width=True):
        with st.spinner("🕵🏻‍♂️ Deep Hunter internetin derinliklerinde avlanıyor... Lütfen 10-15 saniye bekle."):
            try:
                import io
                from contextlib import redirect_stdout
                from egitim_avcisi import otonom_avci_baslat
                
                # Streamlit Cloud'un Terminal tuzaklarını kökünden çözen yapı (Direkt fonksiyon)
                f = io.StringIO()
                with redirect_stdout(f):
                    otonom_avci_baslat()
                
                avci_log = f.getvalue()
                
                if "Tamamlandı" in avci_log or "Başarılı" in avci_log:
                    st.success("✅ Operasyon Başarılı! Yeni cephane kütüphaneye yüklendi komutan.")
                    with st.expander("Avcı Raporunu Görüntüle"):
                        st.code(avci_log)
                    st.info("Taze mühimmatı görmek için 'Eksik Kapatma' sekmesindeki 'Sıradaki Eğitime Geç ➡️' butonunu kullanabilirsin.")
                else:
                    st.warning("⚠️ Avcı çalıştı ancak log raporunda bir aksilik görünüyor:")
                    with st.expander("Hata Detayı / Log"):
                        st.code(avci_log)
            except Exception as e:
                st.error(f"Sistem Hatası: {str(e)}")

# 4. Hekim - Mentor Sohbet Arayüzü (Hafıza Entegreli)
st.markdown("---")
st.subheader("🤖 İSG Mentor ile Konuş")

if "messages" not in st.session_state:
    st.session_state.messages = []
    if supabase:
        try:
            res = supabase.table("chat_history").select("*").order("created_at", desc=False).limit(10).execute()
            if res.data:
                for row in res.data:
                    st.session_state.messages.append({"role": row["role"], "content": row["content"]})
        except Exception:
            pass

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("6331 sayılı kanun veya klinik tuzaklar hakkında sor...")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    if supabase:
        try:
            supabase.table("chat_history").insert({"role": "user", "content": user_input}).execute()
        except Exception:
            pass

    if client_available:
        try:
            context = "Sen bir İş Yeri Hekimliği AI mentorusun. Sadece 6331 sayılı İSG kanunu ve tıbbi mevzuat çerçevesinde net, kısa ve profesyonel cevap ver.\n\nÖnceki Konuşmalar:\n"
            for m in st.session_state.messages[-5:]:
                context += f"{m['role'].capitalize()}: {m['content']}\n"
            context += f"\nGüncel Soru: {user_input}"

            calisan_model = None
            hata_mesaji = ""
            modeller_listesi = ["gemini-2.5-flash", "gemini-flash-latest"]

            for denenen_model in modeller_listesi:
                try:
                    model = genai.GenerativeModel(denenen_model)
                    response = model.generate_content(context)
                    calisan_model = denenen_model
                    break
                except Exception as e:
                    hata_mesaji = str(e)
                    continue

            if calisan_model:
                bot_reply = response.text
                st.chat_message("assistant").write(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                if supabase:
                    try:
                        supabase.table("chat_history").insert({"role": "assistant", "content": bot_reply}).execute()
                    except Exception:
                        pass
            else:
                st.chat_message("assistant").error(f"API Hatası: {hata_mesaji}")
        except Exception as e:
            st.chat_message("assistant").error(f"Sistem Hatası: {e}")
    else:
        st.chat_message("assistant").error("Sistem Uyarısı: GEMINI_API_KEY eksik.")
