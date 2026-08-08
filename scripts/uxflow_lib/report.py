"""The report: one Markdown file per flow, and the only file most readers open.

Structure is deliberate. Summary and priority list come first because that is all
most people will read; the diagram follows so the findings have context; the
detailed findings come last, each one written so it can be pasted into an issue
tracker as-is.
"""

from . import benchmarks, catalog, ir, mermaid

BADGE = {"good": "✓", "warn": "!", "bad": "✗", "info": "·"}


def render(doc, report, embed_diagram=True, lang="tr"):
    o = []
    _header(o, doc, report)
    _summary(o, report)
    _priorities(o, report)
    if embed_diagram:
        _diagram(o, doc)
    _journey(o, doc, report)
    _metrics(o, report)
    _findings(o, report)
    _informational(o, report)
    _suppressed(o, report)
    _method(o, doc, report)
    return "\n".join(o).rstrip() + "\n"


# ------------------------------------------------------------------- sections
def _header(o, doc, report):
    o.append("# %s — UX raporu" % doc["title"])
    o.append("")
    app = doc.get("app") or {}
    bits = []
    if app.get("name"):
        bits.append("**Uygulama:** %s" % app["name"])
    if app.get("stack"):
        bits.append("**Stack:** `%s`" % app["stack"])
    if app.get("commit"):
        bits.append("**Commit:** `%s`" % app["commit"])
    bits.append("**Akış:** `%s`" % doc["id"])
    bits.append("**IR özeti:** `%s`" % ir.content_hash(doc))
    o.append(" · ".join(bits))
    if doc.get("description"):
        o.append("")
        o.append("> %s" % doc["description"])
    o.append("")


def _summary(o, report):
    o.append("## Özet")
    o.append("")
    o.append(report["headline"])
    o.append("")
    m = report["metrics"]
    worst = [b for b in report["benchmarks"] if b["verdict"] == "bad"]
    if worst:
        o.append("Dikkat çeken ölçümler: " +
                 ", ".join("%s (%s%s)" % (w["label"].lower(), w["value"], w["unit"])
                           for w in worst) + ".")
        o.append("")


def _priorities(o, report):
    findings = report["findings"]
    if not findings:
        return
    o.append("## Öncelik sırası")
    o.append("")
    o.append("Bulguların önem, güven ve efor sırasına göre dizilmiş hâli. "
             "Yukarıdan aşağı çalışmak en hızlı iyileşmeyi verir.")
    o.append("")
    for i, f in enumerate(findings, 1):
        where = f["label"] or f["node"] or "akış geneli"
        o.append("%d. **%s** — %s  " % (i, f["title"], where))
        o.append("   `%s` · %s öncelik · %s%s"
                 % (f["id"], catalog.SEVERITY_LABEL[f["severity"]].lower(),
                    catalog.EFFORT_LABEL[f["effort"]],
                    " · `%s`" % f["evidence"][0] if f["evidence"] else ""))
    o.append("")


def _diagram(o, doc):
    o.append("## Akış")
    o.append("")
    o.append("<!-- uxflow tarafından üretildi; elle düzenleme, IR'ı değiştirip yeniden üret. -->")
    o.append("```mermaid")
    o.append(mermaid.render(doc, annotated=False, with_source=False).rstrip())
    o.append("```")
    o.append("")
    o.append("*Düzenlenebilir sürüm: `%s.drawio` — [diagrams.net](https://app.diagrams.net) "
             "ile aç. İkinci sekmede notlu görünüm var.*" % doc["id"])
    o.append("")


def _journey(o, doc, report):
    path = report["primary_path"]
    if not path:
        return
    idx = ir.index(doc)
    o.append("## Ana yol")
    o.append("")
    o.append("Kullanıcının hedefe ulaşmak için izlediği en uzun tam yolculuk — "
             "%d adım:" % report["metrics"]["primary_path_steps"])
    o.append("")
    step = 0
    for nid in path:
        node = idx.get(nid)
        if not node:
            continue
        if node["type"] in ("start", "end"):
            o.append("- *%s* — %s" % (
                "başlangıç" if node["type"] == "start" else "hedef", node["label"]))
            continue
        step += 1
        ann = node.get("annotations") or {}
        extra = []
        if ann.get("taps"):
            extra.append("%d dokunuş" % ann["taps"])
        if ann.get("required_fields"):
            extra.append("%d zorunlu alan" % ann["required_fields"])
        if ann.get("wait"):
            extra.append("bekleme")
        suffix = "  — %s" % ", ".join(extra) if extra else ""
        o.append("%d. **%s**%s" % (step, node["label"], suffix))
    o.append("")


def _metrics(o, report):
    o.append("## Ölçümler")
    o.append("")
    o.append("| | ölçüm | değer | yorum |")
    o.append("| :-: | --- | ---: | --- |")
    for b in report["benchmarks"]:
        icon = BADGE[b["verdict"]]
        note = b["note"] or ""
        o.append("| %s | %s | %s%s | %s |" % (icon, b["label"], b["value"], b["unit"], note))
    o.append("")


def _findings(o, report):
    findings = report["findings"]
    o.append("## Bulgular (%d)" % len(findings))
    o.append("")
    if not findings:
        o.append("Yapısal bir sorun bulunamadı.")
        o.append("")
        return

    for f in findings:
        o.append("### %s · %s" % (f["id"], f["title"]))
        o.append("")
        meta = "**Önem:** %s · **Güven:** %s · **Efor:** %s" % (
            catalog.SEVERITY_LABEL[f["severity"]].lower(),
            catalog.CONFIDENCE_LABEL.get(f["confidence"], f["confidence"]),
            catalog.EFFORT_LABEL[f["effort"]])
        if f["route"]:
            meta += " · **Route:** `%s`" % f["route"]
        o.append(meta)
        o.append("")
        if f["what"]:
            o.append("**Ne oluyor**  ")
            o.append(f["what"])
            o.append("")
        if f["impact"]:
            o.append("**Kullanıcı ne yaşıyor**  ")
            o.append(f["impact"])
            o.append("")
        if f["fix"]:
            o.append("**Ne yapmalı**  ")
            o.append(f["fix"])
            o.append("")
        if f["evidence"]:
            o.append("**Kanıt**")
            for ev in f["evidence"]:
                o.append("- `%s`" % ev)
            o.append("")
        o.append("<sub>Kabul edip susturmak için: `uxflow ignore %s`</sub>" % f["id"])
        o.append("")


def _informational(o, report):
    info = report.get("info") or []
    if not info:
        return
    o.append("## Bilgi notları")
    o.append("")
    o.append("Sorun değil, ama akışı okurken bilinmesi gerekenler.")
    o.append("")
    for i in info:
        o.append("- **%s** — %s%s" % (
            i["label"], i["text"],
            "  `%s`" % i["source"] if i["source"] else ""))
    o.append("")


def _suppressed(o, report):
    muted = report.get("suppressed") or []
    if not muted:
        return
    o.append("## Kabul edilenler (%d)" % len(muted))
    o.append("")
    o.append("`.uxflowignore` dosyasında bastırılmış bulgular. Denetimi geçerler ama "
             "kaybolmazlar — bilinçli kabul edildikleri kayıt altında.")
    o.append("")
    o.append("| id | bulgu | düğüm |")
    o.append("| --- | --- | --- |")
    for f in muted:
        o.append("| `%s` | %s | %s |" % (f["id"], f["title"], f["label"] or f["node"]))
    o.append("")


def _method(o, doc, report):
    m = report["metrics"]
    app = doc.get("app") or {}
    o.append("## Yöntem")
    o.append("")
    o.append("Bu rapor `%s.flow.json` dosyasından üretildi; o dosya da kod tabanı "
             "okunarak çıkarıldı." % doc["id"])
    o.append("")
    o.append("- **Kapsam:** %d düğüm, %d geçiş%s"
             % (m["nodes"], m["edges"],
                ", `%s` commit'i" % app["commit"] if app.get("commit") else ""))
    o.append("- **İzlenebilirlik:** düğümlerin %%%d'i bir `dosya:satır` çapası taşıyor"
             % m["source_coverage"])
    o.append("- **Bulgular yalnızca grafikten türetilir.** Uydurma yok: her bulgu ya "
             "grafiğin yapısından ya da koda dayanan bir etiketten gelir.")
    o.append("- **Bilinmeyen:** gerçek kullanıcı davranışı bu analizin dışındadır. "
             "Kodun izin verdiği yollar çıkarılır, insanların hangisini seçtiği değil. "
             "Analytics'in yerine geçmez, onunla birlikte okunur.")
    if m["source_coverage"] < 100:
        o.append("- **Dikkat:** bazı düğümler koda kadar izlenemiyor; bu bölümlere "
                 "temkinli yaklaş.")
    o.append("")
