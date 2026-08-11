"""Interpretation thresholds for metrics.

A bare number does not help anyone decide anything. "9 steps" means nothing until
you know that six is where flows start losing people. Every metric therefore ships
with a verdict and a one-line reason.

Thresholds are deliberately conservative and stated as rules of thumb, not laws --
they are here to prompt a conversation, not to end one.
"""

GOOD, WARN, BAD, INFO = "good", "warn", "bad", "info"

ICON = {GOOD: "✓", WARN: "!", BAD: "✗", INFO: "·"}
VERDICT_TR = {GOOD: "iyi", WARN: "dikkat", BAD: "sorunlu", INFO: "bilgi"}


def _band(value, good_max, warn_max):
    if value <= good_max:
        return GOOD
    if value <= warn_max:
        return WARN
    return BAD


RULES = {
    "primary_path_steps": {
        "label": "Ana yol adım sayısı",
        "band": lambda v: _band(v, 6, 9),
        "note": {
            GOOD: "makul uzunlukta",
            WARN: "6 adımın üzerinde — her ek adım terk oranını artırır",
            BAD:  "9 adımın üzerinde — akışı bölmeyi ya da adım birleştirmeyi düşün",
        },
    },
    "screens_on_primary_path": {
        "label": "Ana yoldaki ekran sayısı",
        "band": lambda v: _band(v, 4, 6),
        "note": {
            GOOD: "makul",
            WARN: "ekran sayısı artıyor — birleştirilebilir mi?",
            BAD:  "çok fazla ekran geçişi",
        },
    },
    "taps_on_primary_path": {
        "label": "Ana yoldaki etkileşim",
        "band": lambda v: _band(v, 8, 14),
        "note": {
            GOOD: "düşük etkileşim yükü",
            WARN: "etkileşim yükü artıyor",
            BAD:  "kullanıcı çok fazla dokunuş yapıyor",
        },
    },
    "required_fields": {
        "label": "Zorunlu form alanı (toplam)",
        "band": lambda v: _band(v, 6, 12),
        "note": {
            GOOD: "az sayıda zorunlu alan",
            WARN: "her zorunlu alan bir vazgeçme fırsatı — hepsi gerçekten zorunlu mu?",
            BAD:  "form yükü yüksek; alanları böl ya da ertele",
        },
    },
    "failure_exits": {
        "label": "Başarısızlıkla biten yol sayısı",
        "band": lambda v: _band(v, 0, 2),
        "note": {
            GOOD: "kullanıcının kilitlendiği yol yok",
            WARN: "kullanıcının hedefe ulaşamadan takıldığı yollar var",
            BAD:  "çok sayıda çıkmaz — akışın güvenilirliği düşük",
        },
    },
    "error_branch_coverage": {
        "label": "Hata dalı kapsamı",
        "band": lambda v: BAD if v < 50 else (WARN if v < 100 else GOOD),
        "unit": "%",
        "note": {
            GOOD: "ağ çağrılarının tamamının hata dalı modellenmiş",
            WARN: "bazı ağ çağrılarının başarısızlık yolu yok",
            BAD:  "ağ çağrılarının çoğunda hata dalı yok",
        },
    },
    "source_coverage": {
        "label": "Kaynak çapası kapsamı",
        "band": lambda v: BAD if v < 80 else (WARN if v < 100 else GOOD),
        "unit": "%",
        "note": {
            GOOD: "her düğüm koda kadar izlenebiliyor",
            WARN: "bazı düğümler doğrulanamıyor",
            BAD:  "düğümlerin önemli bir kısmı koda dayanmıyor — haritaya temkinli yaklaş",
        },
    },
}

# Reported without a verdict: descriptive, not judgeable out of context.
PLAIN = {
    "screens": "Ekran",
    "api_calls": "Ağ çağrısı",
    "decisions": "Karar noktası",
    "error_branches": "Modellenen hata dalı",
    "nodes": "Düğüm",
    "edges": "Geçiş",
}


def evaluate(metrics):
    """-> [{key, label, value, unit, verdict, note}] in report order."""
    out = []
    for key, rule in RULES.items():
        if key not in metrics:
            continue
        v = metrics[key]
        verdict = rule["band"](v)
        out.append({
            "key": key, "label": rule["label"], "value": v,
            "unit": rule.get("unit", ""), "verdict": verdict,
            "note": rule["note"][verdict],
        })
    for key, label in PLAIN.items():
        if key in metrics:
            out.append({"key": key, "label": label, "value": metrics[key],
                        "unit": "", "verdict": INFO, "note": ""})
    return out


def headline(metrics, findings):
    """One plain sentence describing the state of the flow."""
    high = [f for f in findings if f["severity"] == "high"]
    med = [f for f in findings if f["severity"] == "medium"]
    steps = metrics.get("primary_path_steps", 0)
    fails = metrics.get("failure_exits", 0)

    if not findings:
        return ("Bu akışta yapısal bir sorun bulunamadı. Ana yol %d adım ve "
                "kullanıcının kilitlendiği bir nokta yok." % steps)

    parts = []
    if high:
        parts.append("%d tanesi kullanıcıyı doğrudan etkileyen" % len(high))
    if med:
        parts.append("%d tanesi orta öncelikli" % len(med))
    detay = ", ".join(parts) if parts else "hepsi düşük öncelikli"

    cumle = "Bu akışta %d bulgu var; %s." % (len(findings), detay)
    if fails:
        cumle += (" Kullanıcının hedefe ulaşamadan takıldığı %d farklı yol tespit edildi."
                  % fails)
    cumle += " Ana yol %d adım." % steps
    return cumle
