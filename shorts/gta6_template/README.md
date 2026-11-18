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

## Kullanım
```bash
python3 make_short.py KLIP.mp4 CIKTI.mp4 --name jasontheween --hook "GTA 6 heists have begun!"
```
| Seçenek | Varsayılan | Açıklama |
|---|---|---|
| `--name` | (zorunlu) | Logonun yanında yazan Twitch adı |
| `--hook` | `GTA 6 heists have begun!` | Söylenen ve ekranda çıkan hook. Kısa tut (3–5 kelime). |
| `--cta` | `MORE GTA 6 VIDEOS` | Kapanıştaki yazı ("GTA" ve sayılar sarı olur) |
| `--avatar` | `assets/avatar.png` | Kapanıştaki kanal fotoğrafı (yuvarlak, şeffaf PNG) |
| `--badge-y` | `1640` | Etiketin dikey konumu. Klibin kendi yazılarını kapatırsa değiştir (küçük sayı yukarı taşır). |
| `--models` | `models/` | Kokoro ses modeli; yoksa ilk çalıştırmada indirilir (~350 MB) |
| `--keep` | — | Ara dosyaları bu klasörde sakla |

Dikey olmayan klipler 9:16'ya kırpılarak doldurulur. Render 4 CPU çekirdeğinde ~2,5 dakika sürer.

## Dosyalar
- `make_short.py`: şablonun tamamı (ses, yazı ve etiket animasyonu, kapanış, efektler, kodlama)
- `assets/twitch_logo.png`: Twitch logosu
- `assets/avatar.png`: kanal avatarı (netleştirilmiş, yuvarlak)
- `assets/Anton-Regular.ttf`, `assets/Oswald[wght].ttf`: fontlar (SIL Open Font License, google/fonts)

## Gerekenler
Python 3, ffmpeg ve şu paketler:
```bash
pip install skia-python kokoro-onnx soundfile scipy numpy
```
