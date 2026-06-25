import os
import json
import random
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from supabase import create_client, Client

def otonom_avci_baslat():
    # Konfigürasyon
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

    if not all([GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        print("🚨 Hata: Çevresel değişkenler eksik! (GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY)")
        return

    genai.configure(api_key=GEMINI_API_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 1. OTONOM ARAMA MOTORU (Deep Hunter) - YENİ EKLENEN BÖLÜM
    arama_terimleri = [
        "İş Yeri Hekimliği meslek hastalıkları zor sorular",
        "İSG çıkmış sorular ve çözümleri klinik",
        "İş sağlığı ve güvenliği klinik tuzaklar ve ayrımlar",
        "4857 sayılı İş Kanunu istisnalar hap bilgi",
        "6331 sayılı kanun özet ve tuzak sorular",
        "İşyeri hekimliği odyometri ve solunum fonksiyon testleri değerlendirmesi"
    ]
    secilen_terim = random.choice(arama_terimleri)
    print(f"🕵🏻‍♂️ Deep Hunter Devrede! Aranıyor: '{secilen_terim}'")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # Arama motoru HTML sorgusu
        search_url = f"https://html.duckduckgo.com/html/?q={secilen_terim.replace(' ', '+')}"
        response = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # İlk mantıklı organik sonucu bul ve içine sız
        linkler = soup.find_all('a', class_='result__snippet')
        hedef_url = ""
        for a in linkler:
            href = a.get('href')
            if href and "http" in href and "google" not in href:
                hedef_url = href
                break
                
        if not hedef_url:
            print("⚠️ Arama sonucunda organik link bulunamadı, varsayılan (fallback) kaynağa geçiliyor.")
            hedef_url = "https://isg.yasar.edu.tr/isg-temel-bilgiler/"
            
        print(f"📡 Web taraması başlatıldı: {hedef_url}")
        
        # Kaynağın içine gir ve metni çek
        icerik_res = requests.get(hedef_url, headers=headers, timeout=15)
        icerik_soup = BeautifulSoup(icerik_res.text, 'html.parser')
        ham_metin = icerik_soup.get_text(separator=' ', strip=True)[:8000] # Token sınırını koruma
        
    except Exception as e:
        print(f"⚠️ Web çekim hatası: {e}. Fallback metin kullanılıyor.")
        hedef_url = "Otonom Arama Hatası - Fallback"
        ham_metin = "İş Yeri Hekimliğinde 4857 sayılı kanuna göre kadın işçiler gece postasında 7.5 saatten fazla çalıştırılamaz. Ancak turizm, sağlık ve güvenlik sektörlerinde bu süre çalışanın yazılı onayı ile esnetilebilir. Bu durum sınavlarda sıkça klinik/mevzuat tuzağı olarak sorulur."

    print("🧠 Gemini Filtresi Devrede: Çöp veri ayıklanıyor ve hap bilgi sentezleniyor...")

    # 2. GEMINI YAPAY ZEKA SENTEZİ VE DEĞERLENDİRMESİ
    prompt = f"""
    Sen usta bir İş Yeri Hekimliği (İSG) sınav mentorusun.
    Aşağıdaki ham web metnini oku, içindeki lüzumsuz ve sınavda çıkmayacak bilgileri ÇÖPE AT. 
    Bana sınav kazandıran tek bir 'Hap Bilgi' ve buna bağlı 'Ters Köşe' zor bir çoktan seçmeli soru sentezle.
    
    Ham Metin: {ham_metin}
    
    Yanıtını KESİNLİKLE aşağıdaki JSON formatında ver, JSON dışına hiçbir karakter ekleme:
    {{
        "konu_basligi": "Konunun kısa başlığı",
        "hap_bilgi": "Gereksiz detaylardan arındırılmış, hap gibi klinik/mevzuat bilgisi",
        "soru_metni": "Bu hap bilgiye dayanan zor, ters köşe bir soru",
        "a_sikki": "A şıkkı metni",
        "b_sikki": "B şıkkı metni",
        "c_sikki": "C şıkkı metni",
        "d_sikki": "D şıkkı metni",
        "e_sikki": "E şıkkı metni",
        "dogru_cevap": "Doğru şıkkın tam metni (örn: A şıkkının içindeki yazı)",
        "cozum_aciklamasi": "Neden doğru olduğunun ve diğerlerinin neden yanlış olduğunun taktiksel açıklaması"
    }}
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        ai_response = model.generate_content(prompt)
        temiz_json = ai_response.text.replace("```json", "").replace("```", "").strip()
        veri = json.loads(temiz_json)
        print(f"✅ Sentez Başarılı: {veri['konu_basligi']}")
    except Exception as e:
        print(f"🚨 Sentez Hatası: {e}")
        return

    # 3. VERİTABANI KAYIT BÖLÜMÜ (Supabase)
    try:
        modul_kayit = supabase.table("egitim_materyalleri").insert({
            "konu_basligi": veri["konu_basligi"],
            "hap_bilgi": veri["hap_bilgi"],
            "kaynak_url": hedef_url
        }).execute()
        
        eklenen_modul_id = modul_kayit.data[0]['id']
        
        supabase.table("soru_bankasi").insert({
            "bagli_modul_id": eklenen_modul_id,
            "soru_metni": veri["soru_metni"],
            "a_sikki": veri["a_sikki"],
            "b_sikki": veri["b_sikki"],
            "c_sikki": veri["c_sikki"],
            "d_sikki": veri["d_sikki"],
            "e_sikki": veri["e_sikki"],
            "dogru_cevap": veri["dogru_cevap"],
            "cozum_aciklamasi": veri["cozum_aciklamasi"],
            "is_osym_sorusu": False
        }).execute()
        
        print(f"💾 Veritabanı Kaydı Tamamlandı! Eklenen Modül ID: {eklenen_modul_id}")
    except Exception as e:
        print(f"🚨 Sistem Hatası (LLM veya Veritabanı): {e}")

if __name__ == "__main__":
    otonom_avci_baslat()
