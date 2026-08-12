# flowlint banner — görsel üretim prompt'u

> **Durum: üretildi.** `docs/banner.png` (1774×887) README'nin başında,
> `docs/social-card.png` (1280×640) GitHub sosyal önizlemesi için hazır.
> Bu doküman banner'ı yeniden üretmek ya da bir varyant çıkarmak istediğinde
> kullanılmak üzere duruyor.

Hedef: `README.md`'nin en üstüne konacak yatay banner.

**Teknik:** 2560×640 px (2560 genişlik, 4:1) — GitHub içerik sütunu ~1000 px
genişliğinde render eder, retina için 2× üretip küçültmek gerekir.
**Arka plan:** açık nötr (`#FAFAF9` – `#F4F4F5`). GitHub'ın koyu temasında da
okunur kalır; şeffaf PNG kullanma, koyu temada metin kaybolur.

---

## Ana prompt (kopyala-yapıştır)

> A wide horizontal banner, 2560×640, for a developer tool called **flowlint**.
>
> **Concept.** The tool is a linter for user flows: it reads an app's source code,
> draws the flow the code actually implements, and marks the places a user gets
> stuck. Show a flow diagram in the act of being inspected — most of it healthy,
> one branch flagged.
>
> **Composition.** Left third: the wordmark `flowlint` in a clean geometric
> sans-serif, lowercase, tight letter-spacing, near-black `#18181B`. Directly under
> it, smaller and in `#52525B`: `a linter for your user flows`. Right two thirds: a
> simplified top-to-bottom flowchart — six to eight rounded rectangles connected by
> orthogonal (right-angled) connectors, never curves. One node is a diamond
> (a decision) with two branches leaving it.
>
> **The point of the image.** Most nodes and connectors are calm green. One branch
> — a short path ending in a node with no way out — is drawn in crimson with a
> dashed connector and a slightly heavier stroke. That single red dead end is the
> focal point; everything else recedes. Do not make the diagram look broken
> overall; the story is "one problem found in an otherwise fine flow".
>
> **Palette** (exactly these, they are the tool's own):
> background `#FAFAF9`, healthy nodes fill `#E7F5EA` stroke `#2E7D32`,
> the flagged node fill `#FDEAEA` stroke `#C62828`,
> one amber accent node fill `#FFF6E0` stroke `#B8860B`,
> neutral connectors `#71717A`, text `#18181B` and `#52525B`.
>
> **Style.** Flat vector. Crisp 2px strokes, generous whitespace, subtle 8px corner
> radii. Technical-diagram aesthetic, like a well-made architecture doc. No
> gradients, no drop shadows, no glow, no 3D, no perspective, no isometric view.
>
> **Do not include:** photorealism, human figures, hands, laptops, monitors, robots,
> brains, magnifying glasses, gears, rockets, clouds, circuit-board motifs, neon,
> dark tech backgrounds, stock-illustration characters, lorem-ipsum text blocks, or
> any readable body copy beyond the two lines specified.

---

## Neden bu tercihler

- **Dikdörtgen + ortogonal bağlantı:** aracın gerçek çıktısı böyle görünüyor.
  Banner'ın ürünle aynı dili konuşması gerekiyor.
- **Tek kırmızı dal:** aracın vaadi "her şeyi kırmızıya boyamak" değil, *bir* gerçek
  sorunu bulmak. Görselin de bunu söylemesi lazım.
- **Aracın kendi paleti:** `scripts/flowlint_lib/theme.py` içindeki renkler. Banner
  ile üretilen diyagramlar yan yana geldiğinde aynı ürüne ait görünüyorlar.
- **Yasak listesi:** dişli, roket, beyin, büyüteç — geliştirici aracı görsellerinin
  klişeleri. Ne olduğunu anlatmıyorlar, sadece "bu bir yazılım" diyorlar.

---

## Varyantlar

**Koyu tema ayrı dosya istersen** — aynı prompt, şu değişikliklerle:
arka plan `#0D1117`, metin `#E6EDF3` ve `#8B949E`, düğüm dolguları koyulaştırılmış
(`#0F2E16` yeşil, `#3B1113` kırmızı), kenar renkleri aynı kalır. README'de:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/banner-dark.png">
  <img src="docs/banner.png" alt="flowlint — a linter for your user flows">
</picture>
```

**Sosyal medya kartı** (Show HN, Twitter): 1280×640 (2:1). Aynı kompozisyon ama
wordmark daha büyük ve diyagram dört düğüme indirilmiş — küçük boyutta okunması
için. GitHub'da Settings → Social preview alanına yüklenir.

---

## Kabul kriteri

Banner'ı 400 px genişliğe küçült ve bak:

- [ ] `flowlint` kelimesi hâlâ okunuyor mu?
- [ ] Kırmızı dal ilk bakışta göze çarpıyor mu?
- [ ] Diyagram bir akış şeması gibi mi duruyor, yoksa soyut bir desen mi?
- [ ] GitHub'ın koyu temasında arka plan çirkin bir beyaz blok gibi durmuyor mu?

Dördü de evetse hazır. Değilse kompozisyonu sadeleştir — düğüm sayısını azaltmak
neredeyse her zaman işe yarar.

---

## Üretim sonrası — yapılanlar

README'nin ilk satırları artık şu (H1 başlık kaldırıldı, wordmark zaten banner'da;
metindeki "A linter for your app's user flows" satırı da kaldırıldı, banner onu
söylüyor):

```markdown
<p align="center">
  <img src="docs/banner.png" width="100%" alt="flowlint — a linter for your user flows. …">
</p>
```

**Dosya boyutu.** Üretilen PNG 784 KB geldi; düz renkli vektör görünümlü bir görsel
için bu çok. 64 renge indirip yeniden sıkıştırınca **68 KB**'a düştü, ölçülen fark
%0.7 (RMSE). README görselleri her sayfa açılışında indiriliyor, bu adım atlanmamalı:

```bash
convert banner-raw.png -strip -colors 64 -define png:compression-level=9 docs/banner.png
```

**Sosyal kart** aynı görselden türetildi — 1280×640, arka plan rengiyle dolgulanmış:

```bash
convert docs/banner.png -resize 1280x -gravity center -background '#FAFAF9' \
        -extent 1280x640 -strip -colors 64 docs/social-card.png
```

GitHub'da Settings → General → Social preview alanına yüklenir. Bu görsel bağlantı
paylaşıldığında Slack, X ve LinkedIn önizlemelerinde görünen şey.

**Not:** üretilen banner 2:1 oldu, prompt'ta istenen 4:1 değil. README genişliğinde
biraz uzun duruyor ama kompozisyon dengeli ve 400 px'te dört kriteri de geçiyor.
Daha yassı bir varyant istersen kompozisyonu yeniden kurmak gerekir — kırpmak
diyagramı bozar.
