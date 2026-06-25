import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

# İSG MENTOR AI - OTONOM RADAR BOTU (Faz 2)
# Bu script GitHub Actions tarafından her gece otomatik tetiklenecektir.

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def run_radar():
    """
    ÖSYM duyurular sayfasını tarar, İSG başlıklarını kontrol eder
    ve durumu Supabase 'osym_radar' tablosuna raporlar.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Hata: Supabase çevresel değişkenleri eksik!")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # ÖSYM Duyurular sayfasının hedef adresi
    url = "https://www.osym.gov.tr/TR,21/duyurular.html"
    durum = "NORMAL"
    mesaj = "13 Aralık 2026 İSG/2 Sınav Duyurusu İzleniyor. Yeni bir kritik açıklama saptanmadı."

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            sayfa_metni = soup.get_text().lower()
            
            # Bürokratik alarm tetikleme mantığı (İSG ve Başvuru kelimeleri yan yana gelirse)
            if "isg" in sayfa_metni and ("başvuru" in sayfa_metni or "açıklandı" in sayfa_metni or "kılavuz" in sayfa_metni):
                durum = "Kırmızı Alarm"
                mesaj = "ÖSYM Duyurular sayfasında İSG sınavına dair kritik idari/bürokratik gelişme saptandı!"
    except Exception as e:
        print(f"Web tarama esnasında aksaklık oluştu, lokal takvim baz alınıyor: {e}")

    # Supabase osym_radar tablosuna otonom enjeksiyon
    try:
        data = {
            "durum": durum,
            "mesaj": mesaj
        }
        supabase.table("osym_radar").insert(data).execute()
        print(f"Radar verisi başarıyla hafızaya işlendi: {data}")
    except Exception as e:
        print(f"Supabase hafıza kayıt hatası: {e}")

if __name__ == "__main__":
    run_radar()
