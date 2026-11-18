# GTA 6 Shorts şablonu

Onaylanan ilk örnek: `../gta6_heist/gta6_heists_have_begun.mp4` (jasontheween klibi). Bundan sonraki bütün GTA 6 Shorts videoları bu şablonla yapılır.

## Şablon ne yapar (başka hiçbir şeye dokunmaz)
Klibin kendi altyazıları, görüntüsü ve kurgusu aynen kalır.

1. **Hook (ilk ~2,3 sn)**
   - Yapay zekâ İngilizce erkek sesi hook cümlesini okur.
   - Klip arkada bulanık ve hafif karartılmış olarak oynar.
   - Hook yazısı kelime kelime "pop" efektiyle çıkar: son satır sarı, sayılar sarı, diğerleri beyaz ve siyah kenarlı.
   - Hook bitince yazı kaybolur, bulanıklık açılır, klibin sesi normale döner.
2. **Twitch etiketi**
   - Klip başlayınca alt-ortada Twitch logosu dönerek belirir.
   - Logonun arkasından mor çerçeveli koyu kutu açılır ve yayıncının adı kayarak gelir.
   - Video boyunca kalır.
3. **Kapanış (~4 sn)**
   - Klibin son anı bulanıklaşır ve kararır.
   - Kanal avatarı mor halkayla belirir.
   - Altında **MORE GTA 6 VIDEOS** yazısı çıkar.
   - İmleç **SUBSCRIBE** butonuna tıklar, buton **SUBSCRIBED** olur ve zil çalar.
   - Sonunda ekran siyaha kararır.
   - Geçiş, tıklama ve zil efektleri eklenir.

Çıktı: 1080x1920, 60 fps, H.264 + AAC 48 kHz. Hook sesi klipten biraz yüksek ayarlanır (~ −11,5 LUFS).

## En kolay yol: tek komut (`auto.py`)
```bash
python3 auto.py --list                          # bugünün en çok izlenen İngilizce GTA 6 klipleri
python3 auto.py https://clips.twitch.tv/...     # klibi indir → hazır Shorts (../gta6_clips/)
python3 auto.py URL --plan                      # önce sadece planı göster (kamera, kesit, hook, döküm)
```
`auto.py` şunları otomatik yapar:
- klibi indirir;
- konuşmayı yazıya döker;
- yayıncının kamerasını yüzünden bulur;
- uzun kliplerde en hareketli ~38 saniyeyi seçer;
- klipteki kelimelere göre hook yazar ("xQc vs GTA 6 police!" gibi);
- ünlü harfsiz isimleri ("xQc" gibi) harf harf okutur;
- videoyu üretir.

Her şey `cache/` klasöründe saklanır, aynı klip ikinci kez işlenmez. Her ayar elle değiştirilebilir: `--hook`, `--start/--end`, `--cam`, `--name`, `--badge-y`. Klip başına ~4–6 dakika sürer (4 CPU çekirdeği).

Ücretli hiçbir servis kullanılmaz (Higgsfield/vidIQ yok). Ses ve konuşma tanıma modelleri `models/` klasöründe; yoksa ilk çalıştırmada GitHub'dan indirilir.

## Yatay (ham Twitch) klipler için önce dikey düzen
Bana gönderilen jasontheween klibi zaten dikeydi (üstte kamera, altta oyun, altyazılı). Ham Twitch klipleri yataydır; onları önce `verticalize.py` aynı düzene getirir:
- Yayıncı kamerası üstte, oyun altta (ortadan kırpılmış).
- Ortadaki birleşme yerinde kelime kelime altyazı var: beyaz kalın yazı, o an söylenen kelime mor kutuda, küfürler yıldızlı.
- Altyazılar çevrimdışı konuşma tanıma modeliyle (sherpa-onnx Parakeet) çıkarılır. Model yoksa GitHub'dan indirilir (~480 MB).
- Ses −13 LUFS'a ayarlanır.

```bash
python3 verticalize.py HAM_KLIP.mp4 dikey.mp4 --cam 0,0,367,293 --start 14.4 --end 47.0
python3 make_short.py dikey.mp4 CIKTI.mp4 --name xqc --hook "xQc's first GTA 6 carjacking!" --hook-say "X-Q-C's first GTA 6 carjacking!"
```
- `--cam X,Y,W,H`: yayıncı kamerasının kaynaktaki dikdörtgeni (piksel).
- `--start/--end`: klibin en iyi kısmı. Hook ilk ~2,5 sn'yi kapattığı için önemli ilk sözden ~3,5 sn önce başlat.
- `--fix "yanlis=dogru"`: yanlış duyulan kelimeyi düzeltir; boş bırakılırsa kelimeyi siler.

## Kullanım
```bash
python3 make_short.py KLIP.mp4 CIKTI.mp4 --name jasontheween --hook "GTA 6 heists have begun!"
```
| Seçenek | Varsayılan | Açıklama |
|---|---|---|
| `--name` | (zorunlu) | Logonun yanında yazan Twitch adı |
| `--hook` | `GTA 6 heists have begun!` | Söylenen ve ekranda çıkan hook. Kısa tut (3–5 kelime). |
| `--hook-say` | — | Sesin okuyuşu farklıysa (ör. xQc → "X-Q-C") |
| `--cta` | `MORE GTA 6 VIDEOS` | Kapanıştaki yazı ("GTA" ve sayılar sarı olur) |
| `--avatar` | `assets/avatar.png` | Kapanıştaki kanal fotoğrafı (yuvarlak, şeffaf PNG) |
| `--badge-y` | `1640` | Etiketin dikey konumu. Klibin kendi yazılarını kapatırsa değiştir (küçük sayı yukarı taşır). |
| `--models` | `models/` | Kokoro ses modeli; yoksa ilk çalıştırmada indirilir (~350 MB) |
| `--keep` | — | Ara dosyaları bu klasörde sakla |

Dikey olmayan klipler 9:16'ya kırpılarak doldurulur. Render 4 CPU çekirdeğinde ~2,5 dakika sürer.

## Dosyalar
- `auto.py`: tek komutla URL'den hazır videoya (indirme, döküm, kamera bulma, kesit, hook)
- `verticalize.py`: yatay klibi dikey düzene getirir ve altyazı ekler
- `make_short.py`: şablonun tamamı (ses, yazı ve etiket animasyonu, kapanış, efektler, kodlama)
- `assets/twitch_logo.png`: Twitch logosu
- `assets/avatar.png`: kanal avatarı (netleştirilmiş, yuvarlak)
- `assets/Anton-Regular.ttf`, `assets/Oswald[wght].ttf`, `assets/Montserrat-ExtraBold.ttf`: fontlar (SIL Open Font License, google/fonts)

## Gerekenler
Python 3, ffmpeg ve şu paketler:
```bash
pip install skia-python kokoro-onnx soundfile scipy numpy sherpa-onnx yt-dlp "opencv-python-headless<5"
```
