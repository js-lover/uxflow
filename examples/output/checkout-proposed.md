# Guest checkout (proposed) — UX raporu

**Uygulama:** Example Shop · **Stack:** `nextjs` · **Commit:** `proposal` · **Akış:** `checkout-proposed`

> Same goal, with the forced signup removed, the failure branches modelled, and the promo interstitial moved off the critical path.

## Özet

Bu akışta 2 bulgu var; 1 tanesi orta öncelikli. Ana yol 7 adım.

| | | |
| --- | ---: | --- |
| 🔴 **Yüksek öncelikli** | 0 | kullanıcıyı doğrudan etkiliyor |
| 🟠 Orta | 1 | dönüşüme mal oluyor |
| 🟡 Düşük | 1 | cilalama |
| | | |
| Ana yol | 7 adım | kullanıcının geçtiği nokta sayısı |
| Çıkmaz | 0 | kullanıcının takıldığı yol sayısı |

## Ne yapmalı

Önem, güven ve efor sırasına dizilmiş hâli. Yukarıdan aşağı çalışmak en hızlı iyileşmeyi verir; her madde doğrudan bir iş kaydına dönüştürülebilir.

| # | ne | nerede | efor | detay |
| ---: | --- | --- | --- | --- |
| 1 | 🟠 Ana yol gereğinden uzun | Guest checkout (proposed)<br>— | L | [UXF-DEEP-2678](#uxf-deep-2678) |
| 2 | 🟡 Haritanın bir kısmı doğrulanamıyor | Guest checkout (proposed)<br>— | S | [UXF-SRC-255A](#uxf-src-255a) |

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
    address["Contact + shipping"]
    shipping_error("Quote unavailable")
    payment["Payment"]
    charge_error("Order could not be created")
    declined["Payment declined"]
    confirm["Order confirmed"]
    end
    subgraph lane_api["Backend"]
    direction TD
    shipping_api[/"POST /api/shipping/quote"/]
    psp[["3-D Secure #40;bank page#41;"]]
    charge[/"POST /api/orders"/]
    orders_db[("orders table")]
    end

    start ==> cart
    cart ==>|"Checkout"| address
    address ==>|"Continue"| shipping_api
    shipping_api ==>|"200"| payment
    shipping_api -.->|"5xx / timeout"| shipping_error
    shipping_error -.->|"Retry"| shipping_api
    shipping_error -.->|"flat rate"| payment
    payment ==>|"Pay"| psp
    payment -.->|"back"| address
    psp ==>|"authorised"| charge
    psp -.->|"rejected"| declined
    declined -.->|"Try another card"| payment
    charge -->|"insert"| orders_db
    charge ==>|"201"| confirm
    charge -.->|"5xx"| charge_error
    charge_error -.->|"Retry"| charge
    confirm ==> done

    classDef happy fill:#E7F5EA,stroke:#2E7D32,color:#14532D,stroke-width:2px;
    classDef error fill:#FDEAEA,stroke:#C62828,color:#7F1D1D,stroke-width:2px;
    classDef edge fill:#FFF6E0,stroke:#B8860B,color:#78350F,stroke-width:2px;
    classDef neutral fill:#F4F4F5,stroke:#71717A,color:#27272A,stroke-width:2px;
    classDef deadend fill:#FCE4EC,stroke:#AD1457,color:#831843,stroke-width:2px;
    classDef orphan fill:#EDE9FE,stroke:#6D28D9,color:#4C1D95,stroke-width:2px;
    classDef unreachable fill:#E0E7FF,stroke:#3730A3,color:#312E81,stroke-width:2px;
    class shipping_error,charge_error,declined error;
    class start,cart,address,shipping_api,payment,psp,charge,confirm,done happy;
    class orders_db neutral;
```

*Düzenlenebilir sürüm: `checkout-proposed.drawio` — [diagrams.net](https://app.diagrams.net) ile aç. İkinci sekmede notlu görünüm var.*

## Ana yol

Kullanıcının hedefe ulaşmak için izlediği en uzun tam yolculuk — 7 adım:

- *başlangıç* — Taps Checkout in cart
1. **Cart**  — 1 dokunuş
2. **Contact + shipping**  — 1 dokunuş, 5 zorunlu alan
3. **POST /api/shipping/quote**  — bekleme
4. **Payment**  — 2 dokunuş, 4 zorunlu alan
5. **3-D Secure (bank page)**
6. **POST /api/orders**
7. **Order confirmed**
- *hedef* — Order placed

## Ölçümler

| | ölçüm | değer | yorum |
| :-: | --- | ---: | --- |
| ! | Ana yol adım sayısı | 7 | 6 adımın üzerinde — her ek adım terk oranını artırır |
| ✓ | Ana yoldaki ekran sayısı | 4 | makul |
| ✓ | Ana yoldaki etkileşim | 4 | düşük etkileşim yükü |
| ! | Zorunlu form alanı (toplam) | 9 | her zorunlu alan bir vazgeçme fırsatı — hepsi gerçekten zorunlu mu? |
| ✓ | Başarısızlıkla biten yol sayısı | 0 | kullanıcının kilitlendiği yol yok |
| ✓ | Hata dalı kapsamı | 100% | ağ çağrılarının tamamının hata dalı modellenmiş |
| ✗ | Kaynak çapası kapsamı | 0% | düğümlerin önemli bir kısmı koda dayanmıyor — haritaya temkinli yaklaş |

**Akış büyüklüğü:** 13 düğüm · 17 geçiş · 5 ekran · 2 ağ çağrısı · 0 karar noktası · 6 hata dalı

## Bulgular (2)

<a id="uxf-deep-2678"></a>

### 🟠 Ana yol gereğinden uzun

`UXF-DEEP-2678` · **düğüm:** Guest checkout (proposed) · **önem:** orta · **güven:** kesin · **efor:** L (tasarım kararı gerekir)

**Ne oluyor**

Ana yol 7 adım (eşik 6).

**Kullanıcı ne yaşıyor**

Her ek adım kullanıcı kaybı üretir. Uzun akışlar özellikle mobilde ve ilk kullanımda belirgin şekilde daha düşük tamamlanma oranına sahiptir.

**Ne yapmalı**

Adımları birleştirmeyi dene: aynı ekranda toplanabilecek alanlar, sonraya ertelenebilecek kararlar, atlanabilecek onaylar.

<sub>Kabul edip susturmak için: `flowlint ignore UXF-DEEP-2678`</sub>

<a id="uxf-src-255a"></a>

### 🟡 Haritanın bir kısmı doğrulanamıyor

`UXF-SRC-255A` · **düğüm:** Guest checkout (proposed) · **önem:** düşük · **güven:** kesin · **efor:** S (~1 saat)

**Ne oluyor**

11 düğümde `source` alanı yok: Cart, Contact + shipping, POST /api/shipping/quote, Quote unavailable, Payment, 3-D Secure (bank page) ve 5 tane daha.

**Kullanıcı ne yaşıyor**

Bu düğümlerin koda dayandığı doğrulanamıyor. Okuyucu haritanın hangi kısmının gerçek, hangi kısmının varsayım olduğunu ayırt edemeyince tamamına duyduğu güven zayıflar.

**Ne yapmalı**

Her düğüme geldiği `dosya:satır` bilgisini ekle. Bu akış henüz yazılmamış bir tasarımsa (örneğin bir `-proposed` dosyası) bu bulgu beklenendir; `flowlint ignore` ile gerekçesiyle birlikte kabul et.

<sub>Kabul edip susturmak için: `flowlint ignore UXF-SRC-255A`</sub>

## Bilgi notları

Sorun değil, ama akışı okurken bilinmesi gerekenler.

- **3-D Secure (bank page)** — Bu adımda kullanıcı uygulamadan çıkıp bir dış servise gidiyor. Kendi başına bir sorun değil, ama dönüş yollarının (iptal, hata) modellenmiş olması gerekir.

## Yöntem

Bu rapor `checkout-proposed.flow.json` dosyasından üretildi; o dosya da kod tabanı okunarak çıkarıldı.

- **Kapsam:** 13 düğüm, 17 geçiş, `proposal` commit'i
- **İzlenebilirlik:** düğümlerin %0'i bir `dosya:satır` çapası taşıyor
- **Bulgular yalnızca grafikten türetilir.** Uydurma yok: her bulgu ya grafiğin yapısından ya da koda dayanan bir etiketten gelir.
- **Bilinmeyen:** gerçek kullanıcı davranışı bu analizin dışındadır. Kodun izin verdiği yollar çıkarılır, insanların hangisini seçtiği değil. Analytics'in yerine geçmez, onunla birlikte okunur.
- **Dikkat:** bazı düğümler koda kadar izlenemiyor; bu bölümlere temkinli yaklaş.

## Makine okuması için

<details><summary>Yapısal özet (JSON)</summary>

```json
{
  "flow": "checkout-proposed",
  "title": "Guest checkout (proposed)",
  "ir_hash": "b87d703e6164b5fc",
  "app": {
    "name": "Example Shop",
    "stack": "nextjs",
    "commit": "proposal"
  },
  "metrics": {
    "nodes": 13,
    "edges": 17,
    "screens": 5,
    "api_calls": 2,
    "decisions": 0,
    "primary_path_steps": 7,
    "screens_on_primary_path": 4,
    "total_taps": 5,
    "taps_on_primary_path": 4,
    "required_fields": 9,
    "friction_tags": 0,
    "unreachable_nodes": 0,
    "error_branches": 6,
    "error_branch_coverage": 100,
    "source_coverage": 0,
    "failure_exits": 0
  },
  "primary_path": [
    "start",
    "cart",
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
      "id": "UXF-DEEP-2678",
      "code": "flow_too_deep",
      "severity": "medium",
      "confidence": "certain",
      "effort": "L",
      "node": "",
      "label": "Guest checkout (proposed)",
      "evidence": [],
      "fix": "Adımları birleştirmeyi dene: aynı ekranda toplanabilecek alanlar, sonraya ertelenebilecek kararlar, atlanabilecek onaylar."
    },
    {
      "id": "UXF-SRC-255A",
      "code": "missing_source",
      "severity": "low",
      "confidence": "certain",
      "effort": "S",
      "node": "",
      "label": "Guest checkout (proposed)",
      "evidence": [],
      "fix": "Her düğüme geldiği `dosya:satır` bilgisini ekle. Bu akış henüz yazılmamış bir tasarımsa (örneğin bir `-proposed` dosyası) bu bulgu beklenendir; `flowlint ignore` ile gerekçesiyle birlikte kabul et."
    }
  ],
  "suppressed": []
}
```

</details>

# Flow diff -- Guest checkout (proposed)

`checkout` (before, hash ac3604074e5deec3) → `checkout-proposed` (after, hash b87d703e6164b5fc)

## What changed

| | count |
| --- | ---: |
| Nodes added | 1 |
| Nodes removed | 3 |
| Nodes changed | 6 |
| Nodes unchanged | 6 |

## Metric delta

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| primary path steps | 8 | 7 | -1 |
| screens on primary path | 4 | 4 | ±0 |
| taps on primary path | 5 | 4 | -1 |
| required fields | 14 | 9 | -5 |
| screens | 7 | 5 | -2 |
| api calls | 2 | 2 | ±0 |
| error branches | 2 | 6 | +4 |
| friction tags | 8 | 0 | -8 |
| high-severity findings | 7 | 0 | -7 |
| medium-severity findings | 5 | 1 | -4 |
| low-severity findings | 0 | 1 | +1 |

## Findings resolved

- `deadend` on `declined`
- `deadend` on `shipping-error`
- `friction:blocking_modal` on `promo-modal`
- `friction:duplicate_input` on `address`
- `friction:forced_signup` on `signup`
- `friction:long_form` on `signup`
- `friction:no_back_affordance` on `declined`
- `friction:no_back_affordance` on `payment`
- `friction:silent_failure` on `shipping-error`
- `friction:unskippable` on `promo-modal`
- `no_error_branch` on `charge`

## Findings introduced

- `missing_source` on `(flow)`

## Added

- **Order could not be created** (`charge-error`)

## Removed

- **Signed in?** (`auth-gate`)
- **Create an account** (`signup`)
- **Newsletter offer** (`promo-modal`)

## Changed

- **Contact + shipping** (`address`) — label, annotations
  - `label`: 'Shipping address' → 'Contact + shipping'
- **POST /api/shipping/quote** (`shipping-api`) — annotations
- **Quote unavailable** (`shipping-error`) — label, annotations
  - `label`: 'Quote failed' → 'Quote unavailable'
- **Payment** (`payment`) — annotations
- **Payment declined** (`declined`) — annotations
- **Order confirmed** (`confirm`) — annotations

