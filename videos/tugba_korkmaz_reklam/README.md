# Tuğba Korkmaz · Konya Gayrimenkul Reklam Filmi (30 sn)

- **Video:** `tugba_korkmaz_konya_reklam.mp4` (1080x1920 dikey, 30 fps, 0:30, H.264 + AAC)
- **Tarz:** 2D düz renkli animasyon, çöp adam karakterler (Tuğba Hanım turuncu ceketli, topuz saçlı figür). Renkler: lacivert, turuncu, krem.
- **Seslendirme:** Türkçe kadın sesi (Higgsfield `seed_audio`, ses "Elena"), dosya `voice_raw.wav`. Sahneler ve altyazılar cümle aralarındaki duraklamalara göre senkronlandı (`timing.json`).
- **Müzik ve efektler:** özgün, `audio.py` ile üretildi: 112 bpm hafif kurumsal pluck müziği, sahne geçişlerinde whoosh, harita iğnelerinde "pop", telefon titreşimi, tapu damgası, kapanışta "ding". Ses müziğin yaklaşık 11 dB üstünde.

## Metin
> Konya'da fabrikanı büyütecek bir arsa mı arıyorsun, yoksa ailene yeni bir yuva mı? Organize Sanayi'de doğru parsel, Meram'da huzurlu bir ev, Selçuklu'da değerli bir daire. Her şey tek bir telefonla başlar. Tuğba Korkmaz önce seni dinler: ihtiyacını, bütçeni, hedefini. Sonra sana uygun seçenekleri bulur, yerinde gösterir, pazarlıktan tapuya kadar yanında olur. Sanayide de konutta da, Konya'da doğru adres: Tuğba Korkmaz.

## Sahneler
| Süre | Sahne |
|---|---|
| 0:00 | Kanca: dar gelen fabrikadan kutular fırlıyor, baretli çöp adam ve büyük arsa hayali. "FABRİKAN DAR MI GELDİ?" |
| 0:03 | Apartman önünde sıkışmış aile, ev hayali. "YA DA YENİ BİR YUVA?" |
| 0:05 | Konya panoraması: Organize Sanayi, Meram, Selçuklu iğneleri, arkada Mevlana kubbesi |
| 0:10 | Çalan telefon: "Her şey tek bir telefonla başlar" |
| 0:12 | Masada dinleme: ihtiyaç, bütçe, hedef balonları sesle eş zamanlı |
| 0:16 | Adım adım: uygun seçenekler, yerinde gösterim, pazarlık, tapu (damga). Altta Tuğba Hanım müşteriyle yürüyor |
| 0:21 | Gün batımında Konya silueti, "Sanayide de konutta da", isim kartı (30. saniyeye kadar) |

## Teslim öncesi kontrol
- Son kartta yalnızca isim, "Gayrimenkul Danışmanı", "Konya · Sanayi & Konut" yazıyor. Telefon, logo veya ofis adı yok. Gelirse son karta eklenebilir.
- "TK" baş harfleri geçici logo olarak kullanıldı.
- Metindeki hizmet adımları (yerinde gösterim, pazarlık, tapuya kadar eşlik) genel ifadeler. Tuğba Hanım'ın gerçek hizmetiyle uyuştuğunu teyit edin.

## Yeniden üretim
```bash
python3 audio.py voice_raw.wav timing.json mix.wav
python3 render.py timing.json mix.wav tugba_korkmaz_konya_reklam.mp4
```
