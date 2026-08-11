"""The report: one Markdown file per flow, and the only file most readers open.

Two audiences, one document. A person skims the summary and the action list and
stops there, so those come first and are written in plain language. An agent needs
structured facts, so the document ends with a compact machine block instead of
forcing anything to parse prose.

Everything in between is ordered by how likely it is to be read: what to do, the
diagram for context, the numbers, then the detail behind each finding.
"""

import json

from . import benchmarks, catalog, ir, mermaid

BADGE = {"good": "✓", "warn": "!", "bad": "✗", "info": "·"}
SEV_BADGE = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def render(doc, report, embed_diagram=True, lang="tr"):
    o = []
    _header(o, doc, report)
    _summary(o, report)
    _actions(o, report)
    if embed_diagram:
        _diagram(o, doc)
    _entry_points(o, doc)
    _journey(o, doc, report)
    _metrics(o, report)
    _findings(o, report)
    _informational(o, report)
    _suppressed(o, report)
    _method(o, doc, report)
    _machine(o, doc, report)
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
    o.append(" · ".join(bits))
    if doc.get("description"):
        o.append("")
        o.append("> %s" % doc["description"])
    o.append("")


def _summary(o, report):
    m, findings = report["metrics"], report["findings"]
    o.append("## Özet")
    o.append("")
    o.append(report["headline"])
    o.append("")

    counts = {s: len([f for f in findings if f["severity"] == s])
              for s in ("high", "medium", "low")}
    o.append("| | | |")
    o.append("| --- | ---: | --- |")
    o.append("| %s **Yüksek öncelikli** | %d | kullanıcıyı doğrudan etkiliyor |"
             % (SEV_BADGE["high"], counts["high"]))
    o.append("| %s Orta | %d | dönüşüme mal oluyor |" % (SEV_BADGE["medium"], counts["medium"]))
    o.append("| %s Düşük | %d | cilalama |" % (SEV_BADGE["low"], counts["low"]))
    o.append("| | | |")
    o.append("| Ana yol | %d adım | kullanıcının geçtiği nokta sayısı |"
             % m["primary_path_steps"])
    o.append("| Çıkmaz | %d | kullanıcının takıldığı yol sayısı |" % m["failure_exits"])
    o.append("")


def _actions(o, report):
    findings = report["findings"]
    o.append("## Ne yapmalı")
    o.append("")
    if not findings:
        o.append("Bu akışta yapılacak bir şey çıkmadı. Kullanıcının kilitlendiği bir nokta, "
                 "hata dalı eksik bir ağ çağrısı ya da ulaşılamayan bir ekran yok.")
        o.append("")
        return
    o.append("Önem, güven ve efor sırasına dizilmiş hâli. Yukarıdan aşağı çalışmak en hızlı "
             "iyileşmeyi verir; her madde doğrudan bir iş kaydına dönüştürülebilir.")
    o.append("")
    o.append("| # | ne | nerede | efor | detay |")
    o.append("| ---: | --- | --- | --- | --- |")
    for i, f in enumerate(findings, 1):
        where = f["label"] or f["node"] or "akış geneli"
        src = "`%s`" % f["evidence"][0] if f["evidence"] else "—"
        o.append("| %d | %s %s | %s<br>%s | %s | [%s](#%s) |"
                 % (i, SEV_BADGE[f["severity"]], f["title"], _esc(where), src,
                    f["effort"], f["id"], _anchor(f["id"])))
    o.append("")


def _diagram(o, doc):
    o.append("## Akış")
    o.append("")
    o.append("```mermaid")
    o.append(mermaid.render(doc, annotated=False, with_source=False, header=False).rstrip())
    o.append("```")
    o.append("")
    o.append("*Düzenlenebilir sürüm: `%s.drawio` — [diagrams.net](https://app.diagrams.net) "
             "ile aç. İkinci sekmede notlu görünüm var.*" % doc["id"])
    o.append("")


def _entry_points(o, doc):
    starts = [n for n in doc["nodes"] if n["type"] == "start"]
    if len(starts) < 2:
        return
    o.append("## Giriş noktaları")
    o.append("")
    o.append("Bu akışa %d ayrı yerden giriliyor. Aşağıdaki «Ana yol» yalnızca bunlardan "
             "birini izler; diğerleri diyagramda görünür." % len(starts))
    o.append("")
    for n in starts:
        src = "  `%s`" % n["source"] if n.get("source") else ""
        o.append("- **%s**%s" % (n["label"], src))
    o.append("")


def _journey(o, doc, report):
    path = report["primary_path"]
    if not path:
        return
    idx = ir.index(doc)
    o.append("## Ana yol")
    o.append("")
    o.append("Kullanıcının hedefe ulaşmak için izlediği en uzun tam yolculuk — %d adım:"
             % report["metrics"]["primary_path_steps"])
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
    m = report["metrics"]
    o.append("## Ölçümler")
    o.append("")
    o.append("| | ölçüm | değer | yorum |")
    o.append("| :-: | --- | ---: | --- |")
    for b in report["benchmarks"]:
        if b["verdict"] == "info":
            continue
        o.append("| %s | %s | %s%s | %s |"
                 % (BADGE[b["verdict"]], b["label"], b["value"], b["unit"], b["note"]))
    o.append("")
    size = {b["key"]: b["value"] for b in report["benchmarks"] if b["verdict"] == "info"}
    if size:
        o.append("**Akış büyüklüğü:** " + " · ".join(
            "%d %s" % (size[k], label) for k, label in (
                ("nodes", "düğüm"), ("edges", "geçiş"), ("screens", "ekran"),
                ("api_calls", "ağ çağrısı"), ("decisions", "karar noktası"),
                ("error_branches", "hata dalı")) if k in size))
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
        o.append('<a id="%s"></a>' % _anchor(f["id"]))
        o.append("")
        o.append("### %s %s" % (SEV_BADGE[f["severity"]], f["title"]))
        o.append("")
        meta = ["`%s`" % f["id"],
                "**önem:** %s" % catalog.SEVERITY_LABEL[f["severity"]].lower(),
                "**güven:** %s" % catalog.CONFIDENCE_LABEL.get(f["confidence"], f["confidence"]),
                "**efor:** %s" % catalog.EFFORT_LABEL[f["effort"]]]
        if f["label"]:
            meta.insert(1, "**düğüm:** %s" % f["label"])
        if f["route"]:
            meta.append("**route:** `%s`" % f["route"])
        o.append(" · ".join(meta))
        o.append("")
        if f["what"]:
            o.append("**Ne oluyor**")
            o.append("")
            o.append(f["what"])
            o.append("")
        if f["impact"]:
            o.append("**Kullanıcı ne yaşıyor**")
            o.append("")
            o.append(f["impact"])
            o.append("")
        if f["fix"]:
            o.append("**Ne yapmalı**")
            o.append("")
            o.append(f["fix"])
            o.append("")
        if f["evidence"]:
            o.append("**Kanıt:** " + " · ".join("`%s`" % e for e in f["evidence"]))
            o.append("")
        o.append("<sub>Kabul edip susturmak için: `flowlint ignore %s`</sub>" % f["id"])
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
            i["label"], i["text"], "  `%s`" % i["source"] if i["source"] else ""))
    o.append("")


def _suppressed(o, report):
    muted = report.get("suppressed") or []
    if not muted:
        return
    o.append("## Kabul edilenler (%d)" % len(muted))
    o.append("")
    o.append("`.flowlintignore` dosyasında bastırılmış bulgular. Denetimi geçerler ama "
             "kaybolmazlar — bilinçli kabul edildikleri kayıt altında.")
    o.append("")
    o.append("| id | bulgu | düğüm |")
    o.append("| --- | --- | --- |")
    for f in muted:
        o.append("| `%s` | %s | %s |" % (f["id"], f["title"], _esc(f["label"] or f["node"])))
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


def _machine(o, doc, report):
    """Structured facts, so an agent does not have to parse the prose above."""
    payload = {
        "flow": doc["id"],
        "title": doc["title"],
        "ir_hash": ir.content_hash(doc),
        "app": {k: v for k, v in (doc.get("app") or {}).items() if v},
        "metrics": report["metrics"],
        "primary_path": report["primary_path"],
        "findings": [
            {"id": f["id"], "code": f["code"], "severity": f["severity"],
             "confidence": f["confidence"], "effort": f["effort"],
             "node": f["node"], "label": f["label"], "evidence": f["evidence"],
             "fix": f["fix"]}
            for f in report["findings"]
        ],
        "suppressed": [f["id"] for f in report.get("suppressed") or []],
    }
    o.append("## Makine okuması için")
    o.append("")
    o.append("<details><summary>Yapısal özet (JSON)</summary>")
    o.append("")
    o.append("```json")
    o.append(json.dumps(payload, ensure_ascii=False, indent=2))
    o.append("```")
    o.append("")
    o.append("</details>")
    o.append("")


# --------------------------------------------------------------------- helpers
def _esc(text):
    """Table cells: a pipe in a label would split the row."""
    return str(text).replace("|", "\\|")


def _anchor(finding_id):
    return finding_id.lower()
