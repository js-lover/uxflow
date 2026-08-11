# Guest checkout — UX raporu

**Uygulama:** Example Shop · **Stack:** `nextjs` · **Commit:** `a1b2c3d` · **Akış:** `checkout`

> From cart to order confirmation for a user who is not signed in.

## Özet

Bu akışta 12 bulgu var; 7 tanesi kullanıcıyı doğrudan etkileyen, 5 tanesi orta öncelikli. Kullanıcının hedefe ulaşamadan takıldığı 2 farklı yol tespit edildi. Ana yol 8 adım.

| | | |
| --- | ---: | --- |
| 🔴 **Yüksek öncelikli** | 7 | kullanıcıyı doğrudan etkiliyor |
| 🟠 Orta | 5 | dönüşüme mal oluyor |
| 🟡 Düşük | 0 | cilalama |
| | | |
| Ana yol | 8 adım | kullanıcının geçtiği nokta sayısı |
| Çıkmaz | 2 | kullanıcının takıldığı yol sayısı |

## Ne yapmalı

Önem, güven ve efor sırasına dizilmiş hâli. Yukarıdan aşağı çalışmak en hızlı iyileşmeyi verir; her madde doğrudan bir iş kaydına dönüştürülebilir.

| # | ne | nerede | efor | detay |
| ---: | --- | --- | --- | --- |
| 1 | 🔴 Ağ çağrısının hata dalı yok | POST /api/orders<br>`src/app/api/orders/route.ts:11` | S | [UXF-NOERR-F6BC](#uxf-noerr-f6bc) |
| 2 | 🔴 Çıkmaz: bu ekrandan hiçbir yere gidilemiyor | Payment declined<br>`src/app/checkout/declined/page.tsx:9` | M | [UXF-DEAD-6370](#uxf-dead-6370) |
| 3 | 🔴 Geri dönüş yolu yok | Payment declined<br>`src/app/checkout/declined/page.tsx:9` | S | [UXF-NOBAC-CAD8](#uxf-nobac-cad8) |
| 4 | 🔴 Geri dönüş yolu yok | Payment<br>`src/app/checkout/payment/page.tsx:24` | S | [UXF-NOBAC-279B](#uxf-nobac-279b) |
| 5 | 🔴 Çıkmaz: bu ekrandan hiçbir yere gidilemiyor | Quote failed<br>`src/app/checkout/address/page.tsx:88` | M | [UXF-DEAD-7409](#uxf-dead-7409) |
| 6 | 🔴 Hata sessizce yutuluyor | Quote failed<br>`src/app/checkout/address/page.tsx:88` | S | [UXF-SILEN-64E4](#uxf-silen-64e4) |
| 7 | 🔴 Gereksiz zorunlu kayıt | Create an account<br>`src/app/signup/page.tsx:12` | L | [UXF-FORCE-7DE0](#uxf-force-7de0) |
| 8 | 🟠 Ana yol gereğinden uzun | Guest checkout<br>— | L | [UXF-DEEP-2678](#uxf-deep-2678) |
| 9 | 🟠 Engelleyici modal | Newsletter offer<br>`src/components/PromoModal.tsx:20` | S | [UXF-BLOCK-A675](#uxf-block-a675) |
| 10 | 🟠 Atlanamayan ara ekran | Newsletter offer<br>`src/components/PromoModal.tsx:20` | S | [UXF-UNSKI-2022](#uxf-unski-2022) |
| 11 | 🟠 Uzun form | Create an account<br>`src/app/signup/page.tsx:12` | M | [UXF-LONGF-CB43](#uxf-longf-cb43) |
| 12 | 🟠 Zaten bilinen veri tekrar isteniyor | Shipping address<br>`src/app/checkout/address/page.tsx:30` | S | [UXF-DUPLI-BF5E](#uxf-dupli-bf5e) |

## Akış

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}, 'theme': 'base'}}%%
flowchart TD
    subgraph lane_user["User"]
    direction TD
    start(["Taps Checkout in cart"])
    done(["Order placed"])
    end
    subgraph lane_ui["App UI"]
    direction TD
    cart["Cart"]
    auth_gate{"Signed in?"}
    signup["Create an account"]
    address["Shipping address"]
    shipping_error("Quote failed")
    payment["Payment"]
    declined["Payment declined"]
    confirm["Order confirmed"]
    promo_modal["Newsletter offer"]
    end
    subgraph lane_api["Backend"]
    direction TD
    shipping_api[/"POST /api/shipping/quote"/]
    psp[["3-D Secure #40;bank page#41;"]]
    charge[/"POST /api/orders"/]
    orders_db[("orders table")]
    end

    start ==> cart
    cart ==>|"Checkout"| auth_gate
    auth_gate ==>|"yes"| address
    auth_gate -.->|"no"| signup
    signup -.->|"account created"| address
    address ==>|"Continue"| shipping_api
    shipping_api ==>|"200"| payment
    shipping_api -.->|"5xx / timeout"| shipping_error
    payment -.->|"after 4s"| promo_modal
    promo_modal -.->|"dismiss"| payment
    payment ==>|"Pay"| psp
    psp ==>|"authorised"| charge
    psp -.->|"rejected"| declined
    charge -->|"insert"| orders_db
    charge ==>|"201"| confirm
    confirm ==> done
    payment -.->|"back"| address

    classDef happy fill:#E7F5EA,stroke:#2E7D32,color:#14532D,stroke-width:2px;
    classDef error fill:#FDEAEA,stroke:#C62828,color:#7F1D1D,stroke-width:2px;
    classDef edge fill:#FFF6E0,stroke:#B8860B,color:#78350F,stroke-width:2px;
    classDef neutral fill:#F4F4F5,stroke:#71717A,color:#27272A,stroke-width:2px;
    classDef deadend fill:#FCE4EC,stroke:#AD1457,color:#831843,stroke-width:2px;
    classDef orphan fill:#EDE9FE,stroke:#6D28D9,color:#4C1D95,stroke-width:2px;
    classDef unreachable fill:#E0E7FF,stroke:#3730A3,color:#312E81,stroke-width:2px;
    class shipping_error,declined deadend;
    class signup,promo_modal edge;
    class start,cart,auth_gate,address,shipping_api,payment,psp,charge,confirm,done happy;
    class orders_db neutral;
```

*Düzenlenebilir sürüm: `checkout.drawio` — [diagrams.net](https://app.diagrams.net) ile aç. İkinci sekmede notlu görünüm var.*

## Ana yol

Kullanıcının hedefe ulaşmak için izlediği en uzun tam yolculuk — 8 adım:

- *başlangıç* — Taps Checkout in cart
1. **Cart**  — 1 dokunuş
2. **Signed in?**
3. **Shipping address**  — 2 dokunuş, 6 zorunlu alan
4. **POST /api/shipping/quote**  — bekleme
5. **Payment**  — 2 dokunuş, 4 zorunlu alan
6. **3-D Secure (bank page)**
7. **POST /api/orders**
8. **Order confirmed**
- *hedef* — Order placed

## Ölçümler

| | ölçüm | değer | yorum |
| :-: | --- | ---: | --- |
| ! | Ana yol adım sayısı | 8 | 6 adımın üzerinde — her ek adım terk oranını artırır |
| ✓ | Ana yoldaki ekran sayısı | 4 | makul |
| ✓ | Ana yoldaki etkileşim | 5 | düşük etkileşim yükü |
| ✗ | Zorunlu form alanı (toplam) | 14 | form yükü yüksek; alanları böl ya da ertele |
| ! | Başarısızlıkla biten yol sayısı | 2 | kullanıcının hedefe ulaşamadan takıldığı yollar var |
| ! | Hata dalı kapsamı | 50% | bazı ağ çağrılarının başarısızlık yolu yok |
| ✓ | Kaynak çapası kapsamı | 100% | her düğüm koda kadar izlenebiliyor |

**Akış büyüklüğü:** 15 düğüm · 17 geçiş · 7 ekran · 2 ağ çağrısı · 1 karar noktası · 2 hata dalı

## Bulgular (12)

<a id="uxf-noerr-f6bc"></a>

### 🔴 Ağ çağrısının hata dalı yok

`UXF-NOERR-F6BC` · **düğüm:** POST /api/orders · **önem:** yüksek · **güven:** kesin · **efor:** S (~1 saat)

**Ne oluyor**

«POST /api/orders» bir ağ çağrısı ama başarısızlık durumu için modellenmiş hiçbir geçiş yok.

**Kullanıcı ne yaşıyor**

İstek başarısız olduğunda (zaman aşımı, 500, çevrimdışı) kullanıcının ne göreceği belirsiz. Pratikte genelde hiçbir şey görmez: ekran donar ya da sessizce boş kalır. Kullanıcı ne olduğunu anlamaz, aynı işlemi tekrarlar.

**Ne yapmalı**

Reddedilme durumunu yakala ve kullanıcıya göster: hata mesajı + yeniden dene. Zaman aşımını da ayrı düşün — bekleyen istek de bir başarısızlıktır.

**Kanıt:** `src/app/api/orders/route.ts:11`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-NOERR-F6BC`</sub>

<a id="uxf-dead-6370"></a>

### 🔴 Çıkmaz: bu ekrandan hiçbir yere gidilemiyor

`UXF-DEAD-6370` · **düğüm:** Payment declined · **önem:** yüksek · **güven:** kesin · **efor:** M (~yarım gün) · **route:** `/checkout/declined`

**Ne oluyor**

«Payment declined» düğümünden çıkan hiçbir geçiş yok. Akış burada bitiyor ama bu bir hedef (end) düğümü değil.

**Kullanıcı ne yaşıyor**

Kullanıcı buraya geldiğinde uygulama onu terk ediyor. Yapabileceği tek şey tarayıcıyı kapatmak ya da uygulamayı öldürmek. Bu, oturumun sona erdiği yerdir.

**Ne yapmalı**

Bu ekrandan ileri giden en az bir yol ekle: tamamlama, yeniden dene, ya da güvenli bir çıkış (ana sayfaya dön). Kullanıcının buraya neden geldiğini düşün ve oradan devam edebileceği bir eylem sun.

**Kanıt:** `src/app/checkout/declined/page.tsx:9`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-DEAD-6370`</sub>

<a id="uxf-nobac-cad8"></a>

### 🔴 Geri dönüş yolu yok

`UXF-NOBAC-CAD8` · **düğüm:** Payment declined · **önem:** yüksek · **güven:** kesin · **efor:** S (~1 saat) · **route:** `/checkout/declined`

**Ne oluyor**

«Payment declined» ekranında geri dönüş imkânı yok (geri butonu gizli, hareket kapalı ya da yığın temizlenmiş).

**Kullanıcı ne yaşıyor**

Kullanıcı yanlışlıkla girdiği bir ekranda hapsoluyor. Mobilde bu, uygulamayı kapatmakla sonuçlanır. Kullanıcının kontrol hissini kaybettiği andır.

**Ne yapmalı**

Geri/iptal imkânı ekle. Yığını kasıtlı temizliyorsan (ödeme sonrası gibi) en azından açık bir «bitti» çıkışı sun.

**Kanıt:** `src/app/checkout/declined/page.tsx:9`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-NOBAC-CAD8`</sub>

<a id="uxf-nobac-279b"></a>

### 🔴 Geri dönüş yolu yok

`UXF-NOBAC-279B` · **düğüm:** Payment · **önem:** yüksek · **güven:** kesin · **efor:** S (~1 saat) · **route:** `/checkout/payment`

**Ne oluyor**

«Payment» ekranında geri dönüş imkânı yok (geri butonu gizli, hareket kapalı ya da yığın temizlenmiş).

**Kullanıcı ne yaşıyor**

Kullanıcı yanlışlıkla girdiği bir ekranda hapsoluyor. Mobilde bu, uygulamayı kapatmakla sonuçlanır. Kullanıcının kontrol hissini kaybettiği andır.

**Ne yapmalı**

Geri/iptal imkânı ekle. Yığını kasıtlı temizliyorsan (ödeme sonrası gibi) en azından açık bir «bitti» çıkışı sun.

**Kanıt:** `src/app/checkout/payment/page.tsx:24`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-NOBAC-279B`</sub>

<a id="uxf-dead-7409"></a>

### 🔴 Çıkmaz: bu ekrandan hiçbir yere gidilemiyor

`UXF-DEAD-7409` · **düğüm:** Quote failed · **önem:** yüksek · **güven:** kesin · **efor:** M (~yarım gün)

**Ne oluyor**

«Quote failed» düğümünden çıkan hiçbir geçiş yok. Akış burada bitiyor ama bu bir hedef (end) düğümü değil.

**Kullanıcı ne yaşıyor**

Kullanıcı buraya geldiğinde uygulama onu terk ediyor. Yapabileceği tek şey tarayıcıyı kapatmak ya da uygulamayı öldürmek. Bu, oturumun sona erdiği yerdir.

**Ne yapmalı**

Bu ekrandan ileri giden en az bir yol ekle: tamamlama, yeniden dene, ya da güvenli bir çıkış (ana sayfaya dön). Kullanıcının buraya neden geldiğini düşün ve oradan devam edebileceği bir eylem sun.

**Kanıt:** `src/app/checkout/address/page.tsx:88`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-DEAD-7409`</sub>

<a id="uxf-silen-64e4"></a>

### 🔴 Hata sessizce yutuluyor

`UXF-SILEN-64E4` · **düğüm:** Quote failed · **önem:** yüksek · **güven:** kesin · **efor:** S (~1 saat)

**Ne oluyor**

«Quote failed» içindeki hata yakalama bloğu yalnızca log yazıyor; arayüzde hiçbir değişiklik olmuyor.

**Kullanıcı ne yaşıyor**

Kullanıcı işlemin başarısız olduğunu asla öğrenmiyor. Daha kötüsü: başarılı olduğunu sanabilir. Veri kaybı ve destek talebi üreten hata sınıfı budur.

**Ne yapmalı**

`catch` bloğunda kullanıcıya görünür bir sonuç üret. Log yeterli değil — logu kullanıcı okumuyor.

**Kanıt:** `src/app/checkout/address/page.tsx:88`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-SILEN-64E4`</sub>

<a id="uxf-force-7de0"></a>

### 🔴 Gereksiz zorunlu kayıt

`UXF-FORCE-7DE0` · **düğüm:** Create an account · **önem:** yüksek · **güven:** güçlü ihtimal · **efor:** L (tasarım kararı gerekir) · **route:** `/signup`

**Ne oluyor**

«Create an account» kayıt zorunlu kılıyor, oysa arkasındaki servis misafir kullanıcıya da hizmet verebiliyor.

**Kullanıcı ne yaşıyor**

Kullanıcı henüz değeri görmeden hesap açmaya zorlanıyor. Bu, dönüşüm hunisindeki en pahalı adımdır — ölçülen düşüş genelde burada en yüksektir.

**Ne yapmalı**

Misafir olarak devam etme yolu aç. Hesap oluşturmayı işlem *sonrasına* taşı ve alanları o an elindeki verilerle doldur.

**Kanıt:** `src/app/signup/page.tsx:12`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-FORCE-7DE0`</sub>

<a id="uxf-deep-2678"></a>

### 🟠 Ana yol gereğinden uzun

`UXF-DEEP-2678` · **düğüm:** Guest checkout · **önem:** orta · **güven:** kesin · **efor:** L (tasarım kararı gerekir)

**Ne oluyor**

Ana yol 8 adım (eşik 6).

**Kullanıcı ne yaşıyor**

Her ek adım kullanıcı kaybı üretir. Uzun akışlar özellikle mobilde ve ilk kullanımda belirgin şekilde daha düşük tamamlanma oranına sahiptir.

**Ne yapmalı**

Adımları birleştirmeyi dene: aynı ekranda toplanabilecek alanlar, sonraya ertelenebilecek kararlar, atlanabilecek onaylar.

<sub>Kabul edip susturmak için: `flowlint ignore UXF-DEEP-2678`</sub>

<a id="uxf-block-a675"></a>

### 🟠 Engelleyici modal

`UXF-BLOCK-A675` · **düğüm:** Newsletter offer · **önem:** orta · **güven:** kesin · **efor:** S (~1 saat)

**Ne oluyor**

«Newsletter offer» akışın üzerine kapatılamayan bir katman açıyor.

**Kullanıcı ne yaşıyor**

Kullanıcı yapmak istediği işten koparılıyor ve geri dönemiyor. Kritik yolda bu doğrudan dönüşüm kaybıdır.

**Ne yapmalı**

Kapatma yolu ekle (Escape, dışına tıklama, kapat butonu). Kritik akışın üzerinde gösterme — işlem sonrasına taşı.

**Kanıt:** `src/components/PromoModal.tsx:20`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-BLOCK-A675`</sub>

<a id="uxf-unski-2022"></a>

### 🟠 Atlanamayan ara ekran

`UXF-UNSKI-2022` · **düğüm:** Newsletter offer · **önem:** orta · **güven:** kesin · **efor:** S (~1 saat)

**Ne oluyor**

«Newsletter offer» geçilemeyen bir ara adım.

**Kullanıcı ne yaşıyor**

Ne yapmak istediğini bilen kullanıcı yavaşlatılıyor. Tekrar eden kullanımda bu birikerek rahatsızlığa dönüşüyor.

**Ne yapmalı**

«Atla» ekle ya da yalnızca ilk kullanımda göster.

**Kanıt:** `src/components/PromoModal.tsx:20`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-UNSKI-2022`</sub>

<a id="uxf-longf-cb43"></a>

### 🟠 Uzun form

`UXF-LONGF-CB43` · **düğüm:** Create an account · **önem:** orta · **güven:** kesin · **efor:** M (~yarım gün) · **route:** `/signup`

**Ne oluyor**

«Create an account» ekranında beşten fazla zorunlu alan var.

**Kullanıcı ne yaşıyor**

Her zorunlu alan bir vazgeçme fırsatı. Uzun formlar özellikle mobilde yüksek terk oranı üretir.

**Ne yapmalı**

Gerçekten zorunlu olanları ayır. Kalanları sonraya ertele ya da opsiyonel yap. Bilinen verileri (konum, ülke, önceki sipariş) önceden doldur.

**Kanıt:** `src/app/signup/page.tsx:12`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-LONGF-CB43`</sub>

<a id="uxf-dupli-bf5e"></a>

### 🟠 Zaten bilinen veri tekrar isteniyor

`UXF-DUPLI-BF5E` · **düğüm:** Shipping address · **önem:** orta · **güven:** güçlü ihtimal · **efor:** S (~1 saat) · **route:** `/checkout/address`

**Ne oluyor**

«Shipping address» ekranı, uygulamanın akışın daha önceki bir adımında topladığı veriyi tekrar soruyor.

**Kullanıcı ne yaşıyor**

Kullanıcı «bunu az önce yazmıştım» diye düşünüyor. Uygulamanın kendisini hatırlamadığı hissi güveni zedeliyor.

**Ne yapmalı**

Önceki adımdan taşı ve alanı önceden doldur; düzenlenebilir bırak.

**Kanıt:** `src/app/checkout/address/page.tsx:30`

<sub>Kabul edip susturmak için: `flowlint ignore UXF-DUPLI-BF5E`</sub>

## Bilgi notları

Sorun değil, ama akışı okurken bilinmesi gerekenler.

- **3-D Secure (bank page)** — Bu adımda kullanıcı uygulamadan çıkıp bir dış servise gidiyor. Kendi başına bir sorun değil, ama dönüş yollarının (iptal, hata) modellenmiş olması gerekir.  `src/lib/psp/redirect.ts:15`

## Yöntem

Bu rapor `checkout.flow.json` dosyasından üretildi; o dosya da kod tabanı okunarak çıkarıldı.

- **Kapsam:** 15 düğüm, 17 geçiş, `a1b2c3d` commit'i
- **İzlenebilirlik:** düğümlerin %100'i bir `dosya:satır` çapası taşıyor
- **Bulgular yalnızca grafikten türetilir.** Uydurma yok: her bulgu ya grafiğin yapısından ya da koda dayanan bir etiketten gelir.
- **Bilinmeyen:** gerçek kullanıcı davranışı bu analizin dışındadır. Kodun izin verdiği yollar çıkarılır, insanların hangisini seçtiği değil. Analytics'in yerine geçmez, onunla birlikte okunur.

## Makine okuması için

<details><summary>Yapısal özet (JSON)</summary>

```json
{
  "flow": "checkout",
  "title": "Guest checkout",
  "ir_hash": "ac3604074e5deec3",
  "app": {
    "name": "Example Shop",
    "stack": "nextjs",
    "commit": "a1b2c3d"
  },
  "metrics": {
    "nodes": 15,
    "edges": 17,
    "screens": 7,
    "api_calls": 2,
    "decisions": 1,
    "primary_path_steps": 8,
    "screens_on_primary_path": 4,
    "total_taps": 9,
    "taps_on_primary_path": 5,
    "required_fields": 14,
    "friction_tags": 8,
    "unreachable_nodes": 0,
    "error_branches": 2,
    "error_branch_coverage": 50,
    "source_coverage": 100,
    "failure_exits": 2
  },
  "primary_path": [
    "start",
    "cart",
    "auth-gate",
    "address",
    "shipping-api",
    "payment",
    "psp",
    "charge",
    "confirm",
    "done"
  ],
  "findings": [
    {
      "id": "UXF-NOERR-F6BC",
      "code": "no_error_branch",
      "severity": "high",
      "confidence": "certain",
      "effort": "S",
      "node": "charge",
      "label": "POST /api/orders",
      "evidence": [
        "src/app/api/orders/route.ts:11"
      ],
      "fix": "Reddedilme durumunu yakala ve kullanıcıya göster: hata mesajı + yeniden dene. Zaman aşımını da ayrı düşün — bekleyen istek de bir başarısızlıktır."
    },
    {
      "id": "UXF-DEAD-6370",
      "code": "deadend",
      "severity": "high",
      "confidence": "certain",
      "effort": "M",
      "node": "declined",
      "label": "Payment declined",
      "evidence": [
        "src/app/checkout/declined/page.tsx:9"
      ],
      "fix": "Bu ekrandan ileri giden en az bir yol ekle: tamamlama, yeniden dene, ya da güvenli bir çıkış (ana sayfaya dön). Kullanıcının buraya neden geldiğini düşün ve oradan devam edebileceği bir eylem sun."
    },
    {
      "id": "UXF-NOBAC-CAD8",
      "code": "friction:no_back_affordance",
      "severity": "high",
      "confidence": "certain",
      "effort": "S",
      "node": "declined",
      "label": "Payment declined",
      "evidence": [
        "src/app/checkout/declined/page.tsx:9"
      ],
      "fix": "Geri/iptal imkânı ekle. Yığını kasıtlı temizliyorsan (ödeme sonrası gibi) en azından açık bir «bitti» çıkışı sun."
    },
    {
      "id": "UXF-NOBAC-279B",
      "code": "friction:no_back_affordance",
      "severity": "high",
      "confidence": "certain",
      "effort": "S",
      "node": "payment",
      "label": "Payment",
      "evidence": [
        "src/app/checkout/payment/page.tsx:24"
      ],
      "fix": "Geri/iptal imkânı ekle. Yığını kasıtlı temizliyorsan (ödeme sonrası gibi) en azından açık bir «bitti» çıkışı sun."
    },
    {
      "id": "UXF-DEAD-7409",
      "code": "deadend",
      "severity": "high",
      "confidence": "certain",
      "effort": "M",
      "node": "shipping-error",
      "label": "Quote failed",
      "evidence": [
        "src/app/checkout/address/page.tsx:88"
      ],
      "fix": "Bu ekrandan ileri giden en az bir yol ekle: tamamlama, yeniden dene, ya da güvenli bir çıkış (ana sayfaya dön). Kullanıcının buraya neden geldiğini düşün ve oradan devam edebileceği bir eylem sun."
    },
    {
      "id": "UXF-SILEN-64E4",
      "code": "friction:silent_failure",
      "severity": "high",
      "confidence": "certain",
      "effort": "S",
      "node": "shipping-error",
      "label": "Quote failed",
      "evidence": [
        "src/app/checkout/address/page.tsx:88"
      ],
      "fix": "`catch` bloğunda kullanıcıya görünür bir sonuç üret. Log yeterli değil — logu kullanıcı okumuyor."
    },
    {
      "id": "UXF-FORCE-7DE0",
      "code": "friction:forced_signup",
      "severity": "high",
      "confidence": "likely",
      "effort": "L",
      "node": "signup",
      "label": "Create an account",
      "evidence": [
        "src/app/signup/page.tsx:12"
      ],
      "fix": "Misafir olarak devam etme yolu aç. Hesap oluşturmayı işlem *sonrasına* taşı ve alanları o an elindeki verilerle doldur."
    },
    {
      "id": "UXF-DEEP-2678",
      "code": "flow_too_deep",
      "severity": "medium",
      "confidence": "certain",
      "effort": "L",
      "node": "",
      "label": "Guest checkout",
      "evidence": [],
      "fix": "Adımları birleştirmeyi dene: aynı ekranda toplanabilecek alanlar, sonraya ertelenebilecek kararlar, atlanabilecek onaylar."
    },
    {
      "id": "UXF-BLOCK-A675",
      "code": "friction:blocking_modal",
      "severity": "medium",
      "confidence": "certain",
      "effort": "S",
      "node": "promo-modal",
      "label": "Newsletter offer",
      "evidence": [
        "src/components/PromoModal.tsx:20"
      ],
      "fix": "Kapatma yolu ekle (Escape, dışına tıklama, kapat butonu). Kritik akışın üzerinde gösterme — işlem sonrasına taşı."
    },
    {
      "id": "UXF-UNSKI-2022",
      "code": "friction:unskippable",
      "severity": "medium",
      "confidence": "certain",
      "effort": "S",
      "node": "promo-modal",
      "label": "Newsletter offer",
      "evidence": [
        "src/components/PromoModal.tsx:20"
      ],
      "fix": "«Atla» ekle ya da yalnızca ilk kullanımda göster."
    },
    {
      "id": "UXF-LONGF-CB43",
      "code": "friction:long_form",
      "severity": "medium",
      "confidence": "certain",
      "effort": "M",
      "node": "signup",
      "label": "Create an account",
      "evidence": [
        "src/app/signup/page.tsx:12"
      ],
      "fix": "Gerçekten zorunlu olanları ayır. Kalanları sonraya ertele ya da opsiyonel yap. Bilinen verileri (konum, ülke, önceki sipariş) önceden doldur."
    },
    {
      "id": "UXF-DUPLI-BF5E",
      "code": "friction:duplicate_input",
      "severity": "medium",
      "confidence": "likely",
      "effort": "S",
      "node": "address",
      "label": "Shipping address",
      "evidence": [
        "src/app/checkout/address/page.tsx:30"
      ],
      "fix": "Önceki adımdan taşı ve alanı önceden doldur; düzenlenebilir bırak."
    }
  ],
  "suppressed": []
}
```

</details>
