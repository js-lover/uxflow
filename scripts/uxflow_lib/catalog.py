"""Findings catalogue: the human-facing text for every rule.

A finding is only useful if the reader can act on it without opening the code
first. So every rule carries four things:

    what   -- what the code actually does (mechanical, verifiable)
    impact -- what the user experiences because of it (concrete, not abstract)
    fix    -- what to change, phrased for the stack in question
    effort -- rough size, so the reader can triage

`{...}` placeholders are filled from the node at report time.
"""

# effort: S = under an hour, M = half a day, L = needs a design decision
# confidence: certain = the graph proves it; likely = strong signal, verify

CATALOG = {
    # ------------------------------------------------------------ structural
    "deadend": {
        "title": "Çıkmaz: bu ekrandan hiçbir yere gidilemiyor",
        "severity": "high", "confidence": "certain", "effort": "M",
        "what": "«{label}» düğümünden çıkan hiçbir geçiş yok. Akış burada bitiyor "
                "ama bu bir hedef (end) düğümü değil.",
        "impact": "Kullanıcı buraya geldiğinde uygulama onu terk ediyor. Yapabileceği "
                  "tek şey tarayıcıyı kapatmak ya da uygulamayı öldürmek. Bu, "
                  "oturumun sona erdiği yerdir.",
        "fix": "Bu ekrandan ileri giden en az bir yol ekle: tamamlama, yeniden dene, "
               "ya da güvenli bir çıkış (ana sayfaya dön). Kullanıcının buraya neden "
               "geldiğini düşün ve oradan devam edebileceği bir eylem sun.",
    },
    "only_exit_is_back": {
        "title": "Tek çıkış geriye doğru",
        "severity": "high", "confidence": "certain", "effort": "M",
        "what": "«{label}» ekranından çıkan tek geçiş bir geri/iptal hareketi. "
                "İleri giden hiçbir yol yok.",
        "impact": "Kullanıcı bu ekrana geliyor ama buradan hedefine ilerleyemiyor. "
                  "Ya ekran yanlış yerde, ya da tamamlama yolu hiç kodlanmamış.",
        "fix": "Bu ekranın akıştaki amacını netleştir. Bilgi ekranıysa devam butonu, "
               "ara adımsa sonraki adıma geçiş ekle.",
    },
    "unreachable": {
        "title": "Ulaşılamayan ekran",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "«{label}» düğümüne hiçbir giriş noktasından ulaşılamıyor.",
        "impact": "Ya ölü kod (bakım yükü, kafa karışıklığı), ya da bu ekrana götüren "
                  "bir geçiş silinmiş/bozulmuş. İkinci durumda kullanıcı erişmesi "
                  "gereken bir özelliğe erişemiyor.",
        "fix": "Ölü koddaysa sil. Erişilmesi gerekiyorsa eksik geçişi ekle. "
               "Sadece derin bağlantıyla erişiliyorsa akışa bir `start` düğümü olarak ekle.",
    },
    "orphan": {
        "title": "Bağlantısız ekran — yalnızca derin bağlantıyla erişilebilir",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "«{label}» düğümüne akış içinden hiçbir geçiş yok.",
        "impact": "Kullanıcı bu ekrana ancak elindeki bir bağlantıyla düşebilir. "
                  "Uygulama içinde gezinerek bulamaz.",
        "fix": "Kasıtlıysa (e-posta bağlantısı, bildirim hedefi) `start` düğümü yap ve "
               "not düş. Değilse, kullanıcının bulabileceği bir giriş noktası ekle.",
    },

    # ------------------------------------------------------------ error paths
    "no_error_branch": {
        "title": "Ağ çağrısının hata dalı yok",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "«{label}» bir ağ çağrısı ama başarısızlık durumu için modellenmiş "
                "hiçbir geçiş yok.",
        "impact": "İstek başarısız olduğunda (zaman aşımı, 500, çevrimdışı) kullanıcının "
                  "ne göreceği belirsiz. Pratikte genelde hiçbir şey görmez: ekran donar "
                  "ya da sessizce boş kalır. Kullanıcı ne olduğunu anlamaz, aynı işlemi "
                  "tekrarlar.",
        "fix": "Reddedilme durumunu yakala ve kullanıcıya göster: hata mesajı + yeniden "
               "dene. Zaman aşımını da ayrı düşün — bekleyen istek de bir başarısızlıktır.",
    },
    "external_no_return": {
        "title": "Dış servisten iptal/hata dönüşü modellenmemiş",
        "severity": "high", "confidence": "likely", "effort": "M",
        "what": "«{label}» kullanıcıyı uygulamadan çıkarıyor, ama geri dönüşte yalnızca "
                "başarı yolu var. İptal ya da hata dönüşü için bir geçiş yok.",
        "impact": "Kullanıcı dış ekranda (OAuth izni, 3-D Secure, ödeme sağlayıcısı) "
                  "«İptal» derse ya da hata alırsa nereye düştüğü belirsiz. Genelde "
                  "başlangıç ekranına hiçbir açıklama olmadan geri gelir ve neyin "
                  "yanlış gittiğini bilemez.",
        "fix": "Sağlayıcının iptal/hata dönüş parametresini oku (`error`, `error_description`, "
               "`denied`) ve kullanıcıya ne olduğunu söyleyen bir duruma yönlendir. "
               "Dönüş adresini bu durumları taşıyacak şekilde tasarla.",
    },
    # `error_state_no_recovery` was removed in v1.1. Its only reachable condition was
    # a self-loop, which `deadend` and `redirect_loop` already cover -- so it either
    # never fired or fired on legitimate retry paths. A rule that cannot be trusted
    # costs more than it earns.
    "redirect_loop": {
        "title": "Yönlendirme döngüsü riski",
        "severity": "high", "confidence": "likely", "effort": "M",
        "what": "Şu düğümler bir döngü oluşturuyor ve döngüde kullanıcının durumunu "
                "değiştiren bir adım yok: {cycle}.",
        "impact": "Hata kalıcıysa (örneğin oturum sürekli reddediliyorsa) kullanıcı bu "
                  "döngüde sıkışır: ekranlar arasında gidip gelir, hiçbir zaman ilerleyemez. "
                  "Kullanıcı için uygulamanın «donmuş» görünmesinin en yaygın sebebi budur.",
        "fix": "Döngüye bir sayaç ya da kesme koşulu ekle: N denemeden sonra kullanıcıya "
               "ne olduğunu açıklayan bir ekran göster ve alternatif sun.",
    },
    "waiting_no_resend": {
        "title": "Bant dışı bekleme, yeniden gönderim yok",
        "severity": "high", "confidence": "likely", "effort": "S",
        "what": "«{label}» durumunda kullanıcı uygulama dışından gelecek bir şeyi "
                "(e-posta bağlantısı, SMS kodu) bekliyor, ama bu ekrandan yeniden "
                "gönderim ya da yöntem değiştirme yolu yok.",
        "impact": "E-posta spam'e düştüyse ya da SMS gelmediyse kullanıcı tamamen "
                  "kilitlenir. Elinde tek seçenek olarak baştan başlamak kalır — ki "
                  "çoğu kişi bunu yapmaz, vazgeçer.",
        "fix": "«Tekrar gönder» ekle (bir bekleme süresiyle) ve alternatif yönteme "
               "geçiş sun. Ayrıca kullanıcıya nereye gönderildiğini göster ki "
               "yanlış adres girdiyse fark etsin.",
    },
    "decision_single_branch": {
        "title": "Karar noktasının tek dalı var",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "«{label}» bir karar düğümü ama ondan çıkan yalnızca bir ileri yol var.",
        "impact": "Ya alternatif dal modellenmemiş (harita eksik), ya da kodda gerçekten "
                  "yok — bu durumda koşul sağlanmadığında kullanıcı hiçbir yere gitmiyor.",
        "fix": "Koddaki `if/else`'i kontrol et. Else dalı yoksa ekle; varsa akışa işle.",
    },

    # ------------------------------------------------------------ friction
    "friction:no_error_state": {
        "title": "Hata kullanıcıya gösterilmiyor",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "«{label}» için bir hata yolu var ama kullanıcı arayüzünde bu hatayı "
                "gösteren hiçbir şey yok.",
        "impact": "Bir şey ters gittiğinde kullanıcı bunu öğrenemiyor. Boş ya da "
                  "değişmemiş bir ekranla kalıyor, aynı işlemi tekrarlıyor, aynı sonucu "
                  "alıyor. Sessiz terk edilmelerin en yaygın sebebi.",
        "fix": "Hata durumunu arayüze bağla. Yönlendirmeyle taşınan hatalarda "
               "(`?error=...`) hedef sayfanın bu parametreyi okuduğundan emin ol — "
               "bu adım sıklıkla atlanır.",
    },
    "friction:silent_failure": {
        "title": "Hata sessizce yutuluyor",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "«{label}» içindeki hata yakalama bloğu yalnızca log yazıyor; arayüzde "
                "hiçbir değişiklik olmuyor.",
        "impact": "Kullanıcı işlemin başarısız olduğunu asla öğrenmiyor. Daha kötüsü: "
                  "başarılı olduğunu sanabilir. Veri kaybı ve destek talebi üreten "
                  "hata sınıfı budur.",
        "fix": "`catch` bloğunda kullanıcıya görünür bir sonuç üret. Log yeterli değil — "
               "logu kullanıcı okumuyor.",
    },
    "friction:no_loading_state": {
        "title": "Bekleme durumu gösterilmiyor",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "«{label}» asenkron bir işlem başlatıyor ama bekleme sırasında arayüzde "
                "hiçbir gösterge yok.",
        "impact": "Kullanıcı bir şey olup olmadığını bilemiyor. Butona tekrar basıyor — "
                  "bu da çift gönderim, çift ödeme, çift kayıt üretebiliyor.",
        "fix": "İşlem süresince butonu devre dışı bırak ve bir gösterge (spinner, "
               "iskelet ekran) göster. Çift gönderimi ayrıca sunucu tarafında da engelle.",
    },
    "friction:no_empty_state": {
        "title": "Boş durum tasarlanmamış",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "«{label}» bir liste gösteriyor ama liste boşken ne olacağı tanımlı değil.",
        "impact": "Yeni kullanıcı ilk açtığında bomboş bir ekran görüyor. Uygulamanın "
                  "bozuk olduğunu düşünüyor. İlk izlenimin bozulduğu en yaygın nokta.",
        "fix": "Boş durum için içerik yaz: ne olduğunu açıkla ve buradan çıkacak "
               "eylemi (ilk kaydı oluştur) sun.",
    },
    "friction:no_back_affordance": {
        "title": "Geri dönüş yolu yok",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "«{label}» ekranında geri dönüş imkânı yok (geri butonu gizli, "
                "hareket kapalı ya da yığın temizlenmiş).",
        "impact": "Kullanıcı yanlışlıkla girdiği bir ekranda hapsoluyor. Mobilde bu, "
                  "uygulamayı kapatmakla sonuçlanır. Kullanıcının kontrol hissini "
                  "kaybettiği andır.",
        "fix": "Geri/iptal imkânı ekle. Yığını kasıtlı temizliyorsan (ödeme sonrası gibi) "
               "en azından açık bir «bitti» çıkışı sun.",
    },
    "friction:forced_signup": {
        "title": "Gereksiz zorunlu kayıt",
        "severity": "high", "confidence": "likely", "effort": "L",
        "what": "«{label}» kayıt zorunlu kılıyor, oysa arkasındaki servis misafir "
                "kullanıcıya da hizmet verebiliyor.",
        "impact": "Kullanıcı henüz değeri görmeden hesap açmaya zorlanıyor. Bu, "
                  "dönüşüm hunisindeki en pahalı adımdır — ölçülen düşüş genelde "
                  "burada en yüksektir.",
        "fix": "Misafir olarak devam etme yolu aç. Hesap oluşturmayı işlem *sonrasına* "
               "taşı ve alanları o an elindeki verilerle doldur.",
    },
    "friction:long_form": {
        "title": "Uzun form",
        "severity": "medium", "confidence": "certain", "effort": "M",
        "what": "«{label}» ekranında beşten fazla zorunlu alan var.",
        "impact": "Her zorunlu alan bir vazgeçme fırsatı. Uzun formlar özellikle "
                  "mobilde yüksek terk oranı üretir.",
        "fix": "Gerçekten zorunlu olanları ayır. Kalanları sonraya ertele ya da "
               "opsiyonel yap. Bilinen verileri (konum, ülke, önceki sipariş) "
               "önceden doldur.",
    },
    "friction:duplicate_input": {
        "title": "Zaten bilinen veri tekrar isteniyor",
        "severity": "medium", "confidence": "likely", "effort": "S",
        "what": "«{label}» ekranı, uygulamanın akışın daha önceki bir adımında "
                "topladığı veriyi tekrar soruyor.",
        "impact": "Kullanıcı «bunu az önce yazmıştım» diye düşünüyor. Uygulamanın "
                  "kendisini hatırlamadığı hissi güveni zedeliyor.",
        "fix": "Önceki adımdan taşı ve alanı önceden doldur; düzenlenebilir bırak.",
    },
    "friction:blocking_modal": {
        "title": "Engelleyici modal",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "«{label}» akışın üzerine kapatılamayan bir katman açıyor.",
        "impact": "Kullanıcı yapmak istediği işten koparılıyor ve geri dönemiyor. "
                  "Kritik yolda bu doğrudan dönüşüm kaybıdır.",
        "fix": "Kapatma yolu ekle (Escape, dışına tıklama, kapat butonu). Kritik "
               "akışın üzerinde gösterme — işlem sonrasına taşı.",
    },
    "friction:unskippable": {
        "title": "Atlanamayan ara ekran",
        "severity": "medium", "confidence": "certain", "effort": "S",
        "what": "«{label}» geçilemeyen bir ara adım.",
        "impact": "Ne yapmak istediğini bilen kullanıcı yavaşlatılıyor. Tekrar eden "
                  "kullanımda bu birikerek rahatsızlığa dönüşüyor.",
        "fix": "«Atla» ekle ya da yalnızca ilk kullanımda göster.",
    },
    "friction:destructive_no_confirm": {
        "title": "Geri alınamaz işlem, onay yok",
        "severity": "high", "confidence": "certain", "effort": "S",
        "what": "«{label}» geri alınamaz bir işlem yapıyor ve öncesinde onay adımı yok.",
        "impact": "Yanlış dokunuş veri kaybına yol açıyor. Kullanıcı için telafisi yok; "
                  "destek ekibi için telafisi pahalı.",
        "fix": "Onay adımı ekle — ya da daha iyisi, geri alma imkânı sun "
               "(yumuşak silme + «geri al» bildirimi).",
    },
    "friction:hidden_cta": {
        "title": "Ana eylem görünür alanın dışında",
        "severity": "medium", "confidence": "likely", "effort": "S",
        "what": "«{label}» ekranının birincil eylemi kaydırma gerektiriyor.",
        "impact": "Kullanıcı devam etmek için ne yapması gerektiğini göremiyor. "
                  "Özellikle küçük ekranlarda akış burada duruyor.",
        "fix": "Birincil eylemi sabit bir alt çubuğa al ya da içeriği kısaltarak "
               "görünür alana çıkar.",
    },
    "friction:permission_prompt": {
        "title": "Akışın ortasında izin isteği",
        "severity": "medium", "confidence": "certain", "effort": "M",
        "what": "«{label}» sırasında işletim sistemi izin diyaloğu çıkıyor.",
        "impact": "Bağlamı olmayan izin isteği yüksek oranda reddedilir. Reddedildiğinde "
                  "akışın nasıl devam edeceği çoğu zaman kodlanmamıştır.",
        "fix": "İzni istemeden önce neden gerektiğini açıkla. **Reddedilme dalını "
               "mutlaka modelle ve kodla** — bu adım neredeyse her zaman eksiktir.",
    },

    # ------------------------------------------------- flow shape / model quality
    "flow_too_deep": {
        "title": "Ana yol gereğinden uzun",
        "severity": "medium", "confidence": "certain", "effort": "L",
        "what": "Ana yol {steps} adım (eşik {threshold}).",
        "impact": "Her ek adım kullanıcı kaybı üretir. Uzun akışlar özellikle mobilde "
                  "ve ilk kullanımda belirgin şekilde daha düşük tamamlanma oranına sahiptir.",
        "fix": "Adımları birleştirmeyi dene: aynı ekranda toplanabilecek alanlar, "
               "sonraya ertelenebilecek kararlar, atlanabilecek onaylar.",
    },
    "missing_source": {
        "title": "Kaynak çapası olmayan düğüm",
        "severity": "low", "confidence": "certain", "effort": "S",
        "what": "«{label}» düğümünde `source` alanı yok.",
        "impact": "Bu düğümün koda dayandığı doğrulanamıyor. Haritanın geri kalanına "
                  "duyulan güveni de zayıflatır.",
        "fix": "Düğümün geldiği `dosya:satır` bilgisini ekle. Koda dayanmıyorsa "
               "(varsayım, gelecek plan) IR'dan çıkar ya da `note` ile açıkça belirt.",
    },
}

# Tags that describe reality but are not defects. They belong in the diagram and
# in the notes, never in the findings list -- listing them as problems buries the
# real ones.
INFORMATIONAL = {"external_handoff"}

INFO_TEXT = {
    "external_handoff": "Bu adımda kullanıcı uygulamadan çıkıp bir dış servise gidiyor. "
                        "Kendi başına bir sorun değil, ama dönüş yollarının (iptal, hata) "
                        "modellenmiş olması gerekir.",
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_LABEL = {"high": "Yüksek", "medium": "Orta", "low": "Düşük"}
CONFIDENCE_LABEL = {"certain": "kesin", "likely": "güçlü ihtimal"}
EFFORT_LABEL = {"S": "S (~1 saat)", "M": "M (~yarım gün)", "L": "L (tasarım kararı gerekir)"}


def entry(code):
    return CATALOG.get(code)
