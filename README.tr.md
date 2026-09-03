<p align="center">
  <img src="frontend/public/favicon.svg" alt="" width="72">
</p>

<h1 align="center">KNSB Motor Designer</h1>

<p align="center">
  Amatör / üniversite roketçiliği için katı yakıtlı roket motoru tasarımı ve iç balistik simülasyonu.<br>
  <em><a href="https://github.com/asebyrm">PARS Rocketry Team</a> tarafından</em> ·
  <a href="README.md">English</a>
</p>

---

> ## ⚠️ Sorumluluk Reddi
>
> Bu bir **mühendislik tasarım aracıdır, sertifikasyon aracı değildir.** Tüm simülasyon
> çıktıları tahmindir; gerçek bir motor statik ateşleme ile doğrulanmalıdır. Katı yakıtlı
> motorlar yerel mevzuata tabidir — uygun gözetim ve altyapı olmadan test yapmayın. Her dışa
> aktarım **UÇUŞ SERTİFİKALI DEĞİLDİR — amatör araştırma motoru, yalnızca simülasyon verisi**
> notunu taşır.
>
> Bu proje **yakıt üretimi, karıştırma, döküm veya ateşleyici hakkında hiçbir bilgi
> içermez.** Kapsamı geometri, iç balistik, yapısal / termal kontroller ve dışa aktarımdır.

---

## Ne yapar

- **İleri tasarım** — geometri ve yakıt parametrelerini gir; oda basıncı, itki, `Kn`, kütle
  debisi, toplam impuls ve yanma süresi eğrilerini al. Grain kesiti web slider'ı ile canlı
  gerilir.
- **Hızlı irtifa tahmini (ters tasarım)** — roket kütlesi, gövde çapı ve hedef irtifa gir;
  1-DOF çözücü **üç** motor önerir (en hafif / en düşük tepe basıncı / hedefe en yakın), her
  biri belirsizlik bandıyla. Çözülemeyen görevde boş dönmez — bağlayıcı kısıtı ve tek tıkla
  uygulanabilir sayısal öneriyi verir.
- **Önce güvenlik** — 3D baskı case'ler için çevresel gerilme emniyet katsayısı (FDM/SLS
  faktörü), gerektiğinde kalın cidar Lamé modeli, zorunlu ablatif liner ve ısıl soğurma
  tahmini, erozif yanma (`J`) ve `L*` kontrolleri. `FoS < 2` olan tasarım **GÜVENSİZ** olarak
  işaretlenir ve risk açıkça kabul edilene dek `.eng` / `.rse` dışa aktarımı kilitlenir.
- **Etkileşimli motor kesiti** — ölçekli, ölçülü boyuna çizim; girdi ölçüleri tıklanıp
  düzenlenir ve simülasyonu yeniden çalıştırır, türetilmiş ölçüler ayrı gösterilir, sığmayan
  geometri kırmızıya döner. SVG olarak indirilir; parça listesi (BOM) toplam kütlesi `.eng`
  başlığıyla birebir eşleşir.
- **Dışa aktarım** — `.eng` (RASP), `.rse` (zamana bağlı kütle + CG içeren RockSim XML), CSV,
  JSON, PDF rapor, ölçülü SVG, nozzle kontur CSV'si.
- **Hesap (opsiyonel)** — her şey giriş yapmadan çalışır (tasarım `localStorage`'da tutulur).
  Yalnızca kaydetmek, paylaşmak (`/d/{slug}`) ve fork'lamak için giriş gerekir. Yönetim paneli
  kullanım istatistiklerini ve çalışma zamanı sağlığını gösterir.
- **İki dilli** — tam Türkçe ve İngilizce; her alanın, sonucun ve uyarının yanında bağlamsal
  `?` yardımı.

Yakıt: **KNSB** (potasyum nitrat / sorbitol), ince ve granüler oksitleyici varyantları; KNDX
hazır bir YAML olarak gelir. Case'ler: PLA, PETG, ABS, PA12, PA6-CF, PC + referans Al-6061-T6.
Grain'ler: BATES (çok segmentli), tüp, uç yanan.

## Hızlı başlangıç (Docker)

```bash
git clone https://github.com/asebyrm/knsb-motor-designer && cd knsb-motor-designer
cp .env.example .env
python3 -c "import secrets;print('SECRET_KEY='+secrets.token_urlsafe(48))" >> .env
# .env düzenle: DOMAIN, ACME_EMAIL, POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec api alembic upgrade head
```

`https://<alan-adınız>` adresini açın. İlk kayıt olan hesap admin olur. Ayrıntılı anlatım:
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Genişletme

| Eklemek için… | Yap… | Çekirdek kod değişikliği |
| --- | --- | --- |
| yakıt | `backend/data/propellants/` altına YAML koy | yok |
| case / liner malzemesi | `backend/data/materials/*.yaml` içine bir satır | yok |
| grain geometrisi | `GrainGeometry`'den türet, `@register_grain("anahtar")` ekle | yok |

[`CONTRIBUTING.md`](CONTRIBUTING.md) dosyasına bakın.

## Lisans

[AGPL-3.0-or-later](LICENSE). Değiştirilmiş bir sürümü ağ servisi olarak çalıştırmak,
değişikliklerinizi aynı lisansla yayımlamanızı gerektirir.

## Künye

İç balistik yöntemi **Richard Nakka** ve **Sutton, *Rocket Propulsion Elements***'i takip
eder; RASP `.eng` biçimi thrustcurve.org'a göredir. Bölüm 13.1 referans vakası **İTÜ PARS
Roket Takımı** iç balistik raporundandır.
