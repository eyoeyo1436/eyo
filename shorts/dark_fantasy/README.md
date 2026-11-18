# Dark Fantasy — 15 saniyelik dikey video

- **Video:** `dark_fantasy_15s.mp4` (1080x1920, 30 fps, tam 15,0 sn, H.264 + AAC 48 kHz, −14 LUFS)
- **Kapak:** `cover.png`

## Referans videonun stil analizi
Yüklenen referans (720x1280, ~16 sn) 6 sahneden oluşuyor; her sahne ~2,7 sn sürüyor ve yumuşak geçişlerle bağlanıyor. Stilin öğeleri:

| Öğe | Referansta | Bu videoda |
|---|---|---|
| Teknik | 90'ların sonu / 2000'lerin başı 3D render havası (Bryce/Poser), airbrush fantastik poster | Blender Cycles ile gerçek 3D, prosedürel malzemeler |
| Palet | Doymuş kraliyet mavisi, ultramarin ve mor; altın, neon camgöbeği, asit yeşili, kırmızı vurgular; simsiyah gölgeler | Aynı palet, "Standard" ton haritası (90'lar render'ı gibi düz ve canlı renkler) |
| Doku | Her yüzeyde fraktal gürültülü, aşırı keskinleştirilmiş, "crunchy" dokular | Fraktal noise/voronoi malzemeler + çift unsharp mask |
| Malzeme | Parlak, plastiğimsi yüzeyler; damalı mermer; yıldız desenli kumaş | Coat'lu parlak malzemeler, damalı mermer zemin, yıldızlı cüppe |
| Işık | Parlayan büyü (kitaplar, çatlaklar, mumlar, avizeler), ışıltı ve bloom | Emissive büyü öğeleri, mum ışıkları, bloom, 4 köşeli parıldayan yıldızlar |
| Kompozisyon | Merkezde kaçış noktalı derin perspektif, yavaş ileri kamera | Her sahnede ileri/yukarı kamera hareketi |
| Kurgu | ~2,7 sn sahneler, yumuşak geçiş, siyahtan açılış | ~2,8 sn sahneler, ışıltılı geçişler, siyahtan açılış ve siyaha kapanış |

## Sahneler (özgün hikâye; referanstaki sahneler kopyalanmadı)
| Zaman | Sahne |
|---|---|
| 0:00 | Girdaplı mavi galaksi, kraterli dev ay, uçan kaya adasında sivri kuleli kale |
| 0:02.8 | Kaleye uzanan, camgöbeği büyü çatlaklarıyla parlayan taş patika, iki ay |
| 0:05.7 | Gotik taht salonu: damalı mermer, mum sıraları, havada süzülen mumlar, yeşil ateşli mangallar, avize, tahtta büyücü |
| 0:08.5 | Yıldızlı cüppeli, uzun sakallı büyücü; gözleri parlıyor, etrafında ışıldayan büyü kitapları dönüyor |
| 0:11.3 | Ejderhanın hazinesi: altın yığını, taçlı kafatası, karanlıkta açılan kırmızı gözler ve sonunda ejderhanın dev gözü |

## Ses
Tamamen özgün ve sentezlenmiş (`music.py`), re minör: müzik kutusu arpejleri, koro, org, arp, kalp atışı timpani, geçişlerde ışıltı glissandoları ve ters zil kabarmaları, ejderhanın gözü açılırken hırıltı ve vuruş.

## Dosyalar ve yeniden üretim
| Dosya | Görevi |
|---|---|
| `scenes3d.py` | Blender sahne kurucu (malzemeler, set parçaları, kamera) ve Cycles render |
| `post.py` | 15→30 fps hareket enterpolasyonu, büyütme, keskinleştirme, doygunluk, bloom, parçacıklar, geçişler, kodlama |
| `music.py` | Özgün müzik ve ses efektleri |

```bash
pip install bpy==5.3.0 numpy scipy soundfile pillow   # ve ffmpeg
for s in sky path hall sorcerer; do python3 scenes3d.py $s 1 99 FRAMES --res 540x960 --samples 8 --step 2; done
python3 scenes3d.py hoard 1 114 FRAMES --res 540x960 --samples 8 --step 2
python3 music.py music.wav
python3 post.py FRAMES WORK music.wav dark_fantasy_15s.mp4 --workers 4
```
Render, 4 CPU çekirdeğinde (GPU yok) kare başına ~7-11 sn sürdü.
