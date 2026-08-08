
import streamlit as st
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

st.set_page_config(
    page_title="سامانه کمی انتخاب اسید برای Acid Fracturing",
    page_icon="🧪",
    layout="wide",
)

st.markdown("""
<style>
html, body, [class*="css"] {direction: rtl; text-align: right;}
div[data-testid="stMetricValue"] {direction: ltr;}
div[data-testid="stDataFrame"] {direction: rtl;}
.evidence {
    padding: 0.65rem 0.85rem;
    border-radius: 10px;
    background: rgba(128,128,128,0.08);
    margin: 0.35rem 0 0.8rem 0;
    font-size: 0.90rem;
}
.resultbox {
    padding: 1rem;
    border: 1px solid rgba(49,130,206,0.35);
    border-radius: 12px;
    margin: 0.5rem 0 1rem 0;
}
</style>
""", unsafe_allow_html=True)


ACIDS = {
    "HCl معمولی": "Straight HCl",
    "اسید ژله‌ای": "Gelled Acid",
    "اسید امولسیونی": "Emulsified Acid",
    "اسید کف‌دار": "Foamed Acid",
    "اسید خودانحرافی": "Self-Diverting Acid",
    "اسید خودزا / خودتولیدشونده": "Self-Generating Acid",
    "اسید کلاته‌کننده / GLDA": "Chelating / GLDA",
    "اسید غشایی جداساز (ISM)": "Isolation Membrane Acid",
}

DESCRIPTIONS = {
    "HCl معمولی": "کم‌ویسکوز، ارزان و بسیار واکنش‌پذیر؛ مناسب‌تر برای دماهای پایین‌تر و اهداف نفوذ کوتاه‌تر.",
    "اسید ژله‌ای": "با افزایش ویسکوزیته، انتقال جرم و هرزروی را کاهش می‌دهد و نفوذ را افزایش می‌دهد؛ پایداری پلیمر در دمای بالا محدودکننده است.",
    "اسید امولسیونی": "سامانه تأخیری آب‌درنفت؛ نفوذ زیاد، واکنش کندتر و خوردگی کمتر از HCl مستقیم، ولی نیازمند پایداری امولسیون.",
    "اسید کف‌دار": "برای کنترل leakoff، diversion و کمک به flowback؛ به‌ویژه در مخازن کم‌فشار/حساس به آب.",
    "اسید خودانحرافی": "برای مخازن ناهمگن و زون‌های با پذیرندگی متفاوت؛ با افزایش ویسکوزیته درجا جریان را منحرف می‌کند.",
    "اسید خودزا / خودتولیدشونده": "اسید را به‌تدریج در دمای مخزن تولید می‌کند و برای مخازن فوق‌داغ و نیاز به نفوذ عمیق جذاب است.",
    "اسید کلاته‌کننده / GLDA": "کندواکنش‌تر و کم‌خورنده‌تر با پایداری حرارتی بالا؛ برای دما و محدودیت خوردگی بالا مناسب‌تر.",
    "اسید غشایی جداساز (ISM)": "کم‌ویسکوز ولی تأخیری؛ در مطالعه موجود تحت closure pressure حدود 10–30 MPa عملکرد هدایت خوبی نشان داده است.",
}

BASE = 45.0


@dataclass
class Eval:
    scores: Dict[str, float] = field(default_factory=lambda: {a: BASE for a in ACIDS})
    reasons: Dict[str, List[Tuple[float, str]]] = field(default_factory=lambda: {a: [] for a in ACIDS})
    warnings: List[str] = field(default_factory=list)
    derived: Dict[str, str] = field(default_factory=dict)

    def add(self, acid, delta, reason):
        self.scores[acid] += delta
        self.reasons[acid].append((delta, reason))

    def warn(self, text):
        if text not in self.warnings:
            self.warnings.append(text)


def clamp(x):
    return round(max(0, min(100, x)), 1)


def lerp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y1
    t = (x - x0) / (x1 - x0)
    t = max(0.0, min(1.0, t))
    return y0 + t * (y1 - y0)


def temp_band(t):
    if t < 80: return "پایین (<80°C)"
    if t < 120: return "متوسط (80–120°C)"
    if t < 160: return "بالا (120–160°C)"
    return "فوق‌بالا (≥160°C)"


def stress_band(s):
    # Liu et al. review: 0–6.9 low, 6.9–27.6 medium-low, 27.6–60 high, >60 ultra-high
    if s <= 6.9: return "کم (≤6.9 MPa)"
    if s <= 27.6: return "متوسط (6.9–27.6 MPa)"
    if s <= 60: return "بالا (27.6–60 MPa)"
    return "فوق‌بالا (>60 MPa)"


def leakoff_band(cl_x1e3):
    # Engineering bins calibrated around literature cases near 0.9–1.9 ×10^-3 m/min^0.5
    if cl_x1e3 < 1.0: return "کم (<1.0×10⁻³ m/min^0.5)"
    if cl_x1e3 <= 2.0: return "متوسط (1–2×10⁻³ m/min^0.5)"
    return "زیاد (>2×10⁻³ m/min^0.5)"


def hetero_band(ratio):
    if ratio < 3: return "کم (Kmax/Kmin <3)"
    if ratio < 10: return "متوسط (3–10)"
    if ratio <= 20: return "زیاد (10–20)"
    return "بسیار زیاد (>20)"


def spacing_band(m):
    if m <= 0:
        return "نامشخص"
    if m < 10: return "شبکه متراکم (<10 m)"
    if m <= 23: return "متوسط (10–23 m)"
    return "شبکه بازتر (>23 m)"


def penetration_band(m):
    # Case-based calibration from Aljawad et al. modeling:
    # straight ~36.6 m; gelled ~73.2 m; emulsified ~97.5 m
    if m <= 40: return "کوتاه (≤40 m)"
    if m <= 75: return "متوسط (40–75 m)"
    return "عمیق (>75 m)"


def corrosion_limit(material):
    if material == "کویل‌تیوبینگ":
        return 0.02
    if material == "آلیاژ مقاوم به خوردگی (CRA)":
        return 0.03
    return 0.05


def sludge_risk(api, asph):
    if api <= 22 and asph >= 4:
        return "بسیار زیاد؛ ریسک rigid-film emulsion / sludge"
    if api <= 27 and asph >= 3:
        return "زیاد؛ محدوده مستعد acid-induced asphaltene sludge"
    if api <= 30 and asph >= 2:
        return "متوسط"
    return "کم‌تر"


def evaluate(x):
    e = Eval()

    calcite = x["calcite"]
    dolomite = x["dolomite"]
    insol = x["insolubles"]
    carbonate = calcite + dolomite

    # 1 Mineralogy
    if carbonate < 50:
        for a in ACIDS:
            e.add(a, -25, "کربناته بودن سازند پایین است؛ این ابزار برای acid fracturing کربناته کالیبره شده است.")
        e.warn("مجموع کلسیت و دولومیت کمتر از 50% است؛ اعتبار توصیه برای acid fracturing کربناته پایین می‌آید.")
    else:
        if calcite >= 60:
            e.add("HCl معمولی", 8, f"کلسیت {calcite:.0f}% است و واکنش‌پذیری با HCl بالاست.")
            e.add("اسید امولسیونی", 9, "در سنگ‌آهک، retardation می‌تواند مصرف زودهنگام را کنترل کند.")
            e.add("اسید غشایی جداساز (ISM)", 8, "ISM در limestone کاهش نرخ واکنش بیشتری نسبت به dolomite نشان داده است.")
        if dolomite >= 50:
            e.add("اسید خودزا / خودتولیدشونده", 8, f"دولومیت {dolomite:.0f}% است؛ سامانه‌های تأخیری در مخازن عمیق/داغ ارزش بیشتری دارند.")
            e.add("اسید امولسیونی", 7, "تأخیر واکنش برای دولومیت عمیق مناسب است.")
            e.add("اسید کلاته‌کننده / GLDA", 6, "سیستم‌های کلاته‌کننده برای کربناته‌ها و دمای بالا قابل بررسی‌اند.")
        if 25 <= calcite <= 75 and 25 <= dolomite <= 75:
            e.add("اسید خودانحرافی", 7, "کانی‌شناسی مختلط می‌تواند ناهمگنی واکنش‌پذیری ایجاد کند؛ diversion مفید است.")
        if insol >= 10:
            e.add("اسید خودانحرافی", 4, "بخش نامحلول قابل‌توجه می‌تواند توزیع جریان/حکاکی را ناهمگن‌تر کند.")

    # 2 Temperature — continuous
    t = x["temperature"]
    if t < 80:
        e.add("HCl معمولی", 15, "دما زیر 80°C است؛ شدت مشکل مصرف فوق‌سریع HCl کمتر است.")
        e.add("اسید ژله‌ای", 5, "پایداری پلیمر در این بازه مناسب‌تر است.")
        e.add("اسید خودزا / خودتولیدشونده", -10, "برای دماهای پایین، مزیت فعال‌سازی حرارتی self-generating کمتر است.")
    elif t < 120:
        e.add("اسید ژله‌ای", 13, "دما در بازه مناسب بسیاری از gelled-acid systems قرار دارد.")
        e.add("اسید امولسیونی", 10, "retardation برای کنترل واکنش در این دما مفید است.")
        e.add("اسید خودانحرافی", 7, "بسیاری از VES/polymer diverting systems در این بازه کاربردپذیرند.")
        e.add("اسید کف‌دار", 7, "کف می‌تواند هم reaction rate و هم fluid loss را کنترل کند.")
    elif t < 135:
        e.add("اسید ژله‌ای", 8, "نزدیک حد بالای عمومی پایداری بسیاری از سیستم‌های پلیمری است؛ فرمولاسیون باید تست شود.")
        e.add("اسید امولسیونی", 14, "دمای بالا مزیت retardation امولسیون را پررنگ می‌کند.")
        e.add("اسید کلاته‌کننده / GLDA", 12, "GLDA برای شرایط دمای بالا گزینه قابل‌توجهی است.")
        e.add("HCl معمولی", -8, "مصرف HCl در این دما سریع‌تر می‌شود.")
    elif t < 160:
        e.add("اسید امولسیونی", 16, "در دمای 135–160°C، سامانه‌های تأخیری اولویت بیشتری می‌گیرند.")
        e.add("اسید کلاته‌کننده / GLDA", 15, "GLDA پایداری حرارتی تا حدود 177°C در منابع گزارش شده است.")
        e.add("اسید خودزا / خودتولیدشونده", 13, "self-generated acid برای انتقال واکنش به اعماق بیشتر مناسب می‌شود.")
        e.add("اسید ژله‌ای", -8, "بالاتر از حدود 135°C، بسیاری از polymer-based gelled systems با محدودیت پایداری مواجه‌اند.")
        e.add("HCl معمولی", -15, "ریسک مصرف سریع و خوردگی HCl زیاد می‌شود.")
    elif t <= 180:
        e.add("اسید خودزا / خودتولیدشونده", 23, "برای precursorهای self-generating، دماهای اوج حدود 160 و 180°C گزارش شده است.")
        e.add("اسید کلاته‌کننده / GLDA", 17, "GLDA تا حدود 177°C پایداری حرارتی گزارش‌شده دارد.")
        e.add("اسید امولسیونی", 11, "امولسیون همچنان retardation قوی دارد ولی پایداری فرمولاسیون باید HPHT تست شود.")
        e.add("اسید ژله‌ای", -16, "ریسک افت خواص پلیمر در این دما زیاد است.")
        e.add("HCl معمولی", -23, "HCl مستقیم در دمای فوق‌بالا شدیداً مستعد مصرف زودهنگام و خوردگی است.")
        e.add("اسید غشایی جداساز (ISM)", 2, "ISM ذاتاً retardant است، ولی مطالعه اصلی موجود دمای 90°C را تست کرده؛ extrapolation به 160–180°C محدود است.")
        e.warn("برای ISM در این دما شواهد مستقیم مقاله‌ای محدود است؛ قبل از توصیه میدانی تست HPHT ضروری است.")
    else:
        e.add("اسید خودزا / خودتولیدشونده", 18, "در دماهای بالاتر از 180°C تنها سامانه‌های بسیار مقاوم/فعال‌شونده ارزش بررسی دارند.")
        e.add("اسید کلاته‌کننده / GLDA", 10, "GLDA گزینه کم‌خورنده‌تر است، اما بالاتر از محدوده 177°C باید فرمولاسیون اختصاصی تست شود.")
        e.add("HCl معمولی", -28, "دمای بسیار بالا برای HCl مستقیم نامطلوب است.")
        e.add("اسید ژله‌ای", -24, "پایداری عمومی polymer gelled acid در این دما کافی نیست.")
        e.warn("دمای بالاتر از 180°C خارج از محدوده مستقیم بخش مهمی از داده‌های مبناست؛ نتیجه باید آزمایشگاهی اعتبارسنجی شود.")

    # 3 Permeability
    k = x["permeability"]
    if k < 1:
        e.add("اسید امولسیونی", 8, f"تراوایی {k:g} mD است؛ در مخزن بسیار tight طول مؤثر تحریک اهمیت بالایی دارد.")
        e.add("اسید خودزا / خودتولیدشونده", 9, "برای tight carbonate، رساندن اسید زنده به فاصله بیشتر مزیت دارد.")
        e.add("اسید ژله‌ای", 6, "کنترل leakoff در تراوایی پایین مفید است.")
    elif k <= 10:
        e.add("اسید ژله‌ای", 5, "تراوایی در بازه کم تا متوسط است.")
        e.add("اسید امولسیونی", 5, "نفوذ و placement بهتر می‌تواند مؤثر باشد.")
        e.add("اسید خودانحرافی", 4, "اگر contrast بین لایه‌ها بالا باشد diversion اهمیت پیدا می‌کند.")
    else:
        e.add("HCl معمولی", 3, "در تراوایی بالاتر، در صورت نبود محدودیت دما/leakoff، سیستم ساده‌تر قابل بررسی است.")
        e.add("اسید خودانحرافی", 5, "در زون‌های پرتراوا، کنترل preferential intake مهم می‌شود.")

    # 4 Closure stress — literature bins
    s = x["closure_stress"]
    if s <= 6.9:
        e.add("HCl معمولی", 6, "closure stress در محدوده پایین مقاله مروری است؛ نگهداری شکاف آسان‌تر است.")
    elif s <= 27.6:
        e.add("اسید غشایی جداساز (ISM)", 14 if s >= 10 else 8, "ISM در آزمایش‌های 10–30 MPa هدایت و retention خوبی نشان داده است.")
        e.add("اسید امولسیونی", 6, "etching کنترل‌شده می‌تواند به حفظ کانال کمک کند.")
        e.add("اسید خودزا / خودتولیدشونده", 6, "حکاکی ناهمگن‌تر و کنترل‌شده می‌تواند مفید باشد.")
    elif s <= 60:
        e.add("اسید غشایی جداساز (ISM)", 3, "بالای 30 MPa، خود مقاله ISM افت سریع‌تر هدایت را گزارش کرده است.")
        e.add("اسید خودزا / خودتولیدشونده", 7, "در تنش بالا، ایجاد الگوی حکاکی پایدارتر اهمیت بیشتری دارد.")
        e.add("HCl معمولی", -9, "conductivity حاصل از HCl می‌تواند به closure stress حساس باشد.")
        e.warn("closure stress در محدوده «بالا» (27.6–60 MPa) قرار دارد؛ تست conductivity تحت تنش الزامی است.")
    else:
        for a in ACIDS:
            e.add(a, -4, "closure stress فوق‌بالا است؛ نوع اسید به تنهایی مسئله مکانیکی حفظ هدایت را حل نمی‌کند.")
        e.add("اسید خودزا / خودتولیدشونده", 5, "سامانه‌های کنترل‌شده‌تر برای ایجاد channel etching قابل بررسی‌اند.")
        e.warn("closure stress >60 MPa است؛ مقاله مروری آن را ultra-high طبقه‌بندی می‌کند. گزینه‌های hybrid/proppant باید کنار acid fracturing بررسی شوند.")

    # 5 Heterogeneity: permeability contrast + fracture spacing
    ratio = max(1.0, x["perm_contrast"])
    spacing = x["fracture_spacing"]
    if ratio < 3:
        e.add("HCl معمولی", 4, "permeability contrast پایین است؛ نیاز به diversion کمتر است.")
    elif ratio < 10:
        e.add("اسید خودانحرافی", 13, f"Kmax/Kmin={ratio:.1f}؛ در محدوده‌ای است که سیستم‌های self-diverting عملکرد مناسبی گزارش کرده‌اند.")
        e.add("اسید کف‌دار", 9, "foam می‌تواند mobility control و diversion ایجاد کند.")
    elif ratio <= 20:
        e.add("اسید خودانحرافی", 18, f"contrast={ratio:.1f} بالا است؛ diversion عامل کلیدی می‌شود.")
        e.add("اسید کف‌دار", 14, "foamed/VES systems تا contrast نزدیک 10 عملکرد خوب داشته‌اند، ولی با افزایش contrast کار دشوارتر می‌شود.")
        e.add("HCl معمولی", -12, "HCl کم‌ویسکوز preferential intake بالایی خواهد داشت.")
    else:
        e.add("اسید خودانحرافی", 12, "contrast بسیار زیاد است؛ self-diversion لازم است اما ممکن است به‌تنهایی کافی نباشد.")
        e.add("اسید کف‌دار", 4, "یک مطالعه foamed-VES در contrast حدود 20.1 نتوانست diversion مؤثر ایجاد کند.")
        e.add("HCl معمولی", -18, "در contrast بسیار زیاد، HCl مستقیم توزیع ضعیفی خواهد داشت.")
        e.warn("Kmax/Kmin >20 است؛ شواهد مقاله‌ای نشان می‌دهد حتی بعضی foamed-VES systems در این contrast ممکن است ناکافی باشند.")

    if spacing > 0:
        if spacing < 10:
            e.add("اسید کف‌دار", 8, "فاصله شکستگی طبیعی کم است؛ leakoff به شبکه طبیعی می‌تواند زیاد شود.")
            e.add("اسید خودانحرافی", 8, "شبکه شکستگی متراکم نیاز به placement/diversion بیشتر دارد.")
            e.add("HCl معمولی", -7, "spacing کم می‌تواند penetration در main fracture را کاهش دهد.")
        elif spacing <= 23:
            e.add("اسید خودانحرافی", 4, "spacing در محدوده مدل‌شده 30–75 ft قرار دارد؛ اثر شکستگی طبیعی بر leakoff قابل‌توجه است.")
        else:
            e.add("HCl معمولی", 2, "شبکه شکستگی بازتر، leakoff ناشی از تعداد زیاد تقاطع‌ها را کاهش می‌دهد.")

    # 6 Leakoff coefficient
    cl = x["leakoff_x1e3"]
    if cl < 1.0:
        e.add("HCl معمولی", 4, "leakoff coefficient پایین است.")
        e.add("اسید غشایی جداساز (ISM)", 3, "کم‌ویسکوز بودن در leakoff پایین مسئله اصلی نیست.")
    elif cl <= 2.0:
        e.add("اسید ژله‌ای", 8, "leakoff در محدوده متوسط است؛ viscosity control مفید است.")
        e.add("اسید کف‌دار", 9, "foam برای fluid-loss control طراحی می‌شود.")
        e.add("اسید امولسیونی", 7, "امولسیون نسبت به straight acid leakoff کمتری ایجاد می‌کند.")
    else:
        e.add("اسید کف‌دار", 18, f"C_L≈{cl:.2f}×10⁻³ m/min^0.5؛ leakoff بالا است و foam امتیاز زیادی می‌گیرد.")
        e.add("اسید ژله‌ای", 13, "ویسکوزیته بالاتر برای کنترل leakoff شدید مفید است.")
        e.add("اسید خودانحرافی", 13, "diversion برای جلوگیری از مصرف در thief zones مهم است.")
        e.add("اسید امولسیونی", 10, "سامانه تأخیری و ویسکوزتر از HCl می‌تواند leakoff را کاهش دهد.")
        e.add("HCl معمولی", -15, "leakoff بالا می‌تواند طول etched fracture حاصل از straight acid را محدود کند.")

    # 7 Required penetration
    p = x["target_penetration_m"]
    if p <= 40:
        e.add("HCl معمولی", 13, f"هدف نفوذ {p:.0f} m است؛ نزدیک مقدار ~36.6 m straight-acid در مطالعه مدل‌سازی.")
    elif p <= 75:
        e.add("اسید ژله‌ای", 14, f"هدف نفوذ {p:.0f} m است؛ نزدیک بازه ~73 m gelled-acid در مطالعه مدل‌سازی.")
        e.add("اسید امولسیونی", 8, "emulsified acid حاشیه نفوذ بیشتری فراهم می‌کند.")
        e.add("HCl معمولی", -7, "هدف از penetration گزارش‌شده برای straight acid در مطالعه مبنا بیشتر است.")
    else:
        e.add("اسید امولسیونی", 20, f"هدف نفوذ {p:.0f} m است؛ مطالعه مدل‌سازی تا ~97.5 m برای emulsified acid نشان داده است.")
        e.add("اسید خودزا / خودتولیدشونده", 19, "آزادسازی تدریجی H+ برای هدف نفوذ عمیق مناسب است.")
        e.add("اسید غشایی جداساز (ISM)", 10, "retardation کم‌ویسکوز پتانسیل penetration بیشتر دارد، ولی عدد مستقیم معادل در مقاله ISM ارائه نشده است.")
        e.add("اسید ژله‌ای", 9, "gelled acid نسبت به HCl نفوذ بیشتری دارد.")
        e.add("HCl معمولی", -18, "هدف نفوذ عمیق با straight acid ناسازگارتر است.")

    # 8 Flowback pressure margin (physics-based heuristic)
    pres = x["reservoir_pressure_mpa"]
    tvd = x["tvd_m"]
    rho = x["spent_density_kgm3"]
    hydro = rho * 9.80665 * tvd / 1e6
    margin = pres - hydro
    e.derived["Hydrostatic pressure"] = f"{hydro:.2f} MPa"
    e.derived["Flowback pressure margin"] = f"{margin:.2f} MPa"

    if margin <= 0:
        e.add("اسید کف‌دار", 22, f"حاشیه فشار flowback={margin:.1f} MPa است؛ ستون سیال از فشار مخزن سنگین‌تر/برابر است.")
        e.add("اسید ژله‌ای", -5, "cleanup سیال ویسکوز در حاشیه فشار منفی دشوارتر است.")
        e.warn("حاشیه فشار flowback ≤0 MPa است؛ بدون energizing/gas lift احتمال cleanup ضعیف بالاست.")
    elif margin <= 5:
        e.add("اسید کف‌دار", 14, f"حاشیه فشار flowback فقط {margin:.1f} MPa است؛ وضعیت مرزی محسوب می‌شود.")
    else:
        e.add("HCl معمولی", 2, f"حاشیه فشار flowback {margin:.1f} MPa است؛ انرژی طبیعی بیشتری برای cleanup وجود دارد.")

    # 9 Corrosion coupon loss
    material = x["material"]
    loss = x["corrosion_loss"]
    limit = corrosion_limit(material)
    e.derived["Corrosion acceptance limit"] = f"≤{limit:.2f} lb/ft² ({material})"
    if loss <= min(0.02, limit):
        e.add("HCl معمولی", 4, "corrosion loss در محدوده بسیار خوب/محافظه‌کارانه است.")
    elif loss <= limit:
        e.add("اسید امولسیونی", 5, "خوردگی قابل‌قبول است ولی margin محدود است؛ سامانه کم‌خورنده‌تر ارزش دارد.")
        e.add("اسید کلاته‌کننده / GLDA", 6, "GLDA برای کاهش corrosion risk امتیاز می‌گیرد.")
    else:
        e.add("اسید کلاته‌کننده / GLDA", 18, f"corrosion loss={loss:.3f} lb/ft² بالاتر از limit={limit:.2f} است.")
        e.add("اسید خودزا / خودتولیدشونده", 14, "اسیدیته کمتر در سطح می‌تواند خوردگی تجهیزات را کاهش دهد.")
        e.add("اسید امولسیونی", 11, "فاز خارجی نفتی تماس مستقیم اسید با فلز را کم می‌کند.")
        e.add("HCl معمولی", -20, "corrosion loss از حد پذیرش انتخاب‌شده بیشتر است.")
        e.warn("نتیجه corrosion coupon از حد پذیرش بالاتر است؛ فرمولاسیون/CI باید قبل از اجرا اصلاح شود.")

    # 10 Sludge / fluid sensitivity
    api = x["api_gravity"]
    asph = x["asphaltene_wt"]
    srisk = sludge_risk(api, asph)
    e.derived["Acid-induced sludge risk"] = srisk

    if api <= 27 and asph >= 3:
        e.add("HCl معمولی", -17, f"API={api:.1f} و asphaltene={asph:.1f} wt% در محدوده پرریسک sludge مقاله SPE قرار دارد.")
        e.add("اسید کلاته‌کننده / GLDA", 11, "کاهش شدت اسیدی و کنترل یون‌های فلزی می‌تواند برای crude حساس مفید باشد.")
        e.add("اسید خودزا / خودتولیدشونده", 7, "آزادسازی تدریجی اسید تماس ناگهانی اسید قوی با crude را کاهش می‌دهد.")
        e.warn("ریسک acid-induced asphaltene sludge بالاست؛ bottle test، iron control و anti-sludge package الزامی است.")
    elif api <= 30 and asph >= 2:
        e.add("HCl معمولی", -6, "ریسک sludge متوسط است.")
        e.add("اسید کلاته‌کننده / GLDA", 5, "سامانه کم‌خورنده‌تر/کم‌شدت‌تر قابل بررسی است.")

    if x["water_sensitive"]:
        e.add("اسید کف‌دار", 15, "سازند water-sensitive است؛ کاهش liquid loading و flowback بهتر مزیت دارد.")
        e.add("اسید امولسیونی", 4, "فاز خارجی نفتی می‌تواند تماس مستقیم فاز آبی را کاهش دهد.")
    if x["polymer_sensitive"]:
        e.add("اسید ژله‌ای", -14, "نگرانی از polymer residue وجود دارد.")
        e.add("اسید غشایی جداساز (ISM)", 11, "ISM بدون تکیه بر افزایش شدید ویسکوزیته polymeric retardation می‌دهد.")
        e.add("اسید امولسیونی", 7, "عدم اتکا به gel polymer رایج، ریسک residue را کاهش می‌دهد.")
        e.add("اسید خودزا / خودتولیدشونده", 7, "به polymer gel متکی نیست.")

    e.scores = {a: clamp(v) for a, v in e.scores.items()}
    return e


def confidence(ranking):
    if len(ranking) < 2:
        return "نامشخص"
    best = ranking[0][1]
    gap = ranking[0][1] - ranking[1][1]
    if best < 55: return "پایین"
    if gap >= 12: return "بالا"
    if gap >= 6: return "متوسط"
    return "پایین تا متوسط"


def top_reasons(items, positive=True, n=5):
    filt = [x for x in items if (x[0] > 0 if positive else x[0] < 0)]
    return sorted(filt, key=lambda z: abs(z[0]), reverse=True)[:n]


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.title("🧪 سامانه کمی انتخاب اولیه اسید برای لایه‌شکافی اسیدی")
st.caption(
    "نسخه 2 — ورودی‌های عددی، بازه‌های مقاله‌محور، و تفکیک صریح بین داده مستقیم مقاله و آستانه‌های مهندسی."
)

with st.expander("📚 بازه‌های علمی استفاده‌شده در نسخه 2", expanded=False):
    st.markdown("""
**داده مستقیم/نزدیک به مستقیم از مقالات ارسالی:**

- **Closure stress:** مقاله مروری Liu et al. محدوده‌ها را تقریباً به صورت  
  `≤6.9 MPa` کم، `6.9–27.6 MPa` متوسط، `27.6–60 MPa` بالا و `>60 MPa` فوق‌بالا تقسیم می‌کند.
- **ISM:** در Gou et al. (2024)، بهترین retention هدایت در حدود `10–30 MPa` گزارش شد؛ در `≥30 MPa` افت هدایت سریع‌تر می‌شود.
- **نفوذ اسید:** در مطالعه مدل‌سازی Aljawad et al.، برای یک کیس مشخص، straight acid حدود `120 ft ≈ 36.6 m`، gelled acid حدود `240 ft ≈ 73.2 m` و emulsified acid تا حدود `320 ft ≈ 97.5 m` پیشروی داشت.
- **ناهمگنی:** در مرور self-diverting acid، یک سامانه تا permeability contrast حدود `8.8` توان diversion داشت؛ یک foamed-VES در contrast نزدیک `10` توزیع مناسب داشت ولی در حدود `20.1` ناکارآمد شد.
- **شکستگی طبیعی:** در مدل Ugursal et al. فاصله‌های `30، 50 و 75 ft` (تقریباً `9.1، 15.2 و 22.9 m`) بررسی شدند؛ spacing کمتر، leakoff بیشتر و penetration کمتر در main fracture ایجاد کرد.
- **Self-generating acid:** precursorهای بررسی‌شده peak temperature حدود `160°C` و `180°C` داشتند.
- **GLDA:** پایداری حرارتی تا حدود `350°F ≈ 177°C` در منابع گزارش شده است.
- **Sludge:** مقاله SPE 19410 ریسک شدیدتر sludge را عمدتاً برای crude با `API ≤27` و `asphaltene ≥3 wt%` گزارش می‌کند؛ برای rigid-film emulsion، حدود `API ≤22` و `asphaltene ≥4 wt%`.
- **Foam:** در مقاله foamed acid، quality بالای حدود `52%` به‌عنوان foam و حدود `50–60%` برای retardation قابل‌توجه گزارش شده است.

**بازه‌های مهندسی/heuristic در کد:**

- طبقه‌بندی leakoff به `<1`، `1–2` و `>2 ×10⁻³ m/min^0.5` بر اساس کیس‌های مقاله‌ای نزدیک به `0.9–1.9 ×10⁻³` ساخته شده و استاندارد جهانی نیست.
- حاشیه فشار flowback به `≤0`، `0–5` و `>5 MPa` یک معیار فیزیکی/مهندسی برای screening است، نه cutoff استاندارد مقاله‌ای.
- وزن‌های امتیازدهی همچنان heuristic هستند؛ هدف آن‌ها تبدیل شواهد مقاله‌ای به Decision Support Tool است.
""")

# ------------------------------------------------------------
# Form
# ------------------------------------------------------------
with st.form("quant_form"):
    st.subheader("ورودی‌های کمی مخزن و عملیات")

    left, right = st.columns(2)

    with left:
        st.markdown("### 1) کانی‌شناسی کربناته (%)")
        calcite = st.number_input("کلسیت (%)", 0.0, 100.0, 70.0, 1.0)
        dolomite = st.number_input("دولومیت (%)", 0.0, 100.0, 25.0, 1.0)
        insolubles = st.number_input("کانی‌های نامحلول/سایر (%)", 0.0, 100.0, 5.0, 1.0)
        st.markdown('<div class="evidence">راهنما: مجموع کلسیت+دولومیت هرچه بیشتر باشد، اعتبار انتخاب acid-fracturing کربناته بیشتر است.</div>', unsafe_allow_html=True)

        st.markdown("### 3) تراوایی ماتریس")
        permeability = st.number_input("Permeability (mD)", min_value=0.001, max_value=10000.0, value=1.0, step=0.1, format="%.3f")
        st.markdown('<div class="evidence">کد به‌صورت پیوسته کار می‌کند؛ برای screening، <1 mD بسیار tight، 1–10 mD کم تا متوسط، و >10 mD بالاتر در نظر گرفته شده است (بازه مهندسی، نه استاندارد جهانی).</div>', unsafe_allow_html=True)

        st.markdown("### 5) ناهمگنی / شکستگی طبیعی")
        perm_contrast = st.number_input("نسبت تراوایی Kmax / Kmin", min_value=1.0, max_value=1000.0, value=5.0, step=0.5)
        fracture_spacing = st.number_input("فاصله متوسط شکستگی طبیعی (m) — اگر نامشخص است 0", min_value=0.0, max_value=500.0, value=15.0, step=1.0)
        st.markdown('<div class="evidence">شواهد: self-diverting تا contrast≈8.8 در یک تست؛ foamed-VES نزدیک 10 خوب و در ≈20.1 ناکافی. مدل شکستگی طبیعی spacing≈9.1، 15.2 و 22.9 m را بررسی کرده است.</div>', unsafe_allow_html=True)

        st.markdown("### 7) هدف نفوذ اسید زنده در شکاف")
        target_penetration_m = st.number_input("Target live-acid penetration (m)", min_value=5.0, max_value=500.0, value=70.0, step=5.0)
        st.markdown('<div class="evidence">کالیبراسیون یک مطالعه مدل‌سازی: HCl≈36.6 m، gelled≈73.2 m، emulsified≈97.5 m. این اعداد case-specific هستند.</div>', unsafe_allow_html=True)

        st.markdown("### 9) خوردگی تجهیزات")
        material = st.selectbox("جنس/کاربرد تجهیز", ["فولاد کربنی", "آلیاژ مقاوم به خوردگی (CRA)", "کویل‌تیوبینگ"])
        corrosion_loss = st.number_input("Corrosion loss از coupon test (lb/ft²)", min_value=0.0, max_value=1.0, value=0.03, step=0.005, format="%.3f")
        st.markdown('<div class="evidence">حدهای متداول صنعت: carbon steel ≤0.05 lb/ft²، CRA ≤0.03، و coiled tubing معمولاً ≤0.02 lb/ft² تحت شرایط تست طراحی.</div>', unsafe_allow_html=True)

    with right:
        st.markdown("### 2) دمای مخزن")
        temperature = st.number_input("Reservoir temperature (°C)", min_value=20.0, max_value=250.0, value=120.0, step=5.0)
        st.markdown('<div class="evidence">نقاط مهم: بسیاری از polymer-based gelled/diverting systems بالاتر از ~135°C محدود می‌شوند؛ self-generated precursorها در 160–180°C بررسی شده‌اند؛ GLDA تا ~177°C پایداری گزارش‌شده دارد.</div>', unsafe_allow_html=True)

        st.markdown("### 4) تنش بسته‌شدگی")
        closure_stress = st.number_input("Closure stress (MPa)", min_value=0.0, max_value=150.0, value=30.0, step=1.0)
        st.markdown('<div class="evidence">بازه مقاله‌ای: ≤6.9 کم | 6.9–27.6 متوسط | 27.6–60 بالا | >60 MPa فوق‌بالا. ISM در 10–30 MPa مزیت هدایت نشان داده است.</div>', unsafe_allow_html=True)

        st.markdown("### 6) ضریب هرزروی اسید")
        leakoff_x1e3 = st.number_input("C_L  (×10⁻³ m/min^0.5)", min_value=0.0, max_value=20.0, value=1.5, step=0.1)
        st.markdown('<div class="evidence">کیس‌های مقاله‌ای حدود 0.9–1.9×10⁻³ m/min^0.5 دیده می‌شوند. در این اپ: <1 کم، 1–2 متوسط، >2 زیاد (بازه screening، نه cutoff جهانی).</div>', unsafe_allow_html=True)

        st.markdown("### 8) توان طبیعی Flowback")
        reservoir_pressure_mpa = st.number_input("Reservoir pressure (MPa)", min_value=0.1, max_value=250.0, value=40.0, step=1.0)
        tvd_m = st.number_input("TVD (m)", min_value=100.0, max_value=12000.0, value=3000.0, step=100.0)
        spent_density_kgm3 = st.number_input("چگالی تقریبی سیال مصرف‌شده (kg/m³)", min_value=700.0, max_value=1600.0, value=1050.0, step=10.0)
        st.markdown('<div class="evidence">اپ از ΔP = P_res − ρgTVD استفاده می‌کند. ΔP≤0 ضعیف، 0–5 MPa مرزی و >5 MPa مناسب‌تر در نظر گرفته شده است (heuristic فیزیکی).</div>', unsafe_allow_html=True)

        st.markdown("### 10) حساسیت نفت/سازند")
        api_gravity = st.number_input("API gravity نفت", min_value=5.0, max_value=60.0, value=30.0, step=0.5)
        asphaltene_wt = st.number_input("Asphaltene (wt%)", min_value=0.0, max_value=30.0, value=2.0, step=0.5)
        water_sensitive = st.checkbox("سازند نسبت به آب / water blocking حساس است")
        polymer_sensitive = st.checkbox("باقی‌مانده پلیمر/ژل برای سازند نگران‌کننده است")
        st.markdown('<div class="evidence">SPE 19410: ریسک sludge شدیدتر عمدتاً در API≤27 و asphaltene≥3 wt%؛ rigid-film emulsion در حدود API≤22 و asphaltene≥4 wt%.</div>', unsafe_allow_html=True)

    submitted = st.form_submit_button("محاسبه پیشنهاد اسید", use_container_width=True)


if submitted:
    if calcite + dolomite + insolubles > 105:
        st.warning("جمع درصدهای کانی‌شناسی بیش از 105% است؛ ورودی‌ها را بررسی کن.")

    inputs = {
        "calcite": calcite,
        "dolomite": dolomite,
        "insolubles": insolubles,
        "temperature": temperature,
        "permeability": permeability,
        "closure_stress": closure_stress,
        "perm_contrast": perm_contrast,
        "fracture_spacing": fracture_spacing,
        "leakoff_x1e3": leakoff_x1e3,
        "target_penetration_m": target_penetration_m,
        "reservoir_pressure_mpa": reservoir_pressure_mpa,
        "tvd_m": tvd_m,
        "spent_density_kgm3": spent_density_kgm3,
        "material": material,
        "corrosion_loss": corrosion_loss,
        "api_gravity": api_gravity,
        "asphaltene_wt": asphaltene_wt,
        "water_sensitive": water_sensitive,
        "polymer_sensitive": polymer_sensitive,
    }

    result = evaluate(inputs)
    ranking = sorted(result.scores.items(), key=lambda z: z[1], reverse=True)
    best, best_score = ranking[0]

    hydro = spent_density_kgm3 * 9.80665 * tvd_m / 1e6
    margin = reservoir_pressure_mpa - hydro

    st.divider()
    st.subheader("نتیجه")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("پیشنهاد اول", best)
    c2.metric("امتیاز", f"{best_score:.0f}/100")
    c3.metric("اعتماد نسبی", confidence(ranking))
    c4.metric("Flowback ΔP", f"{margin:.1f} MPa")

    st.markdown(f'<div class="resultbox"><b>{best}</b><br>{DESCRIPTIONS[best]}</div>', unsafe_allow_html=True)

    st.subheader("طبقه‌بندی عددی ورودی‌ها")
    summary = pd.DataFrame([
        ["Temperature", f"{temperature:.1f} °C", temp_band(temperature)],
        ["Permeability", f"{permeability:.3f} mD", "ورودی پیوسته"],
        ["Closure stress", f"{closure_stress:.1f} MPa", stress_band(closure_stress)],
        ["Permeability contrast", f"{perm_contrast:.1f}", hetero_band(perm_contrast)],
        ["Natural-fracture spacing", f"{fracture_spacing:.1f} m", spacing_band(fracture_spacing)],
        ["Leakoff coefficient", f"{leakoff_x1e3:.2f}×10⁻³ m/min^0.5", leakoff_band(leakoff_x1e3)],
        ["Target penetration", f"{target_penetration_m:.1f} m", penetration_band(target_penetration_m)],
        ["Flowback hydrostatic pressure", f"{hydro:.2f} MPa", f"ΔP={margin:.2f} MPa"],
        ["Corrosion loss", f"{corrosion_loss:.3f} lb/ft²", result.derived["Corrosion acceptance limit"]],
        ["Sludge risk", f"API={api_gravity:.1f}, Asph={asphaltene_wt:.1f} wt%", result.derived["Acid-induced sludge risk"]],
    ], columns=["پارامتر", "مقدار", "تفسیر/بازه"])
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("چرا پیشنهاد اول انتخاب شد؟")
    pos = top_reasons(result.reasons[best], True, 6)
    neg = top_reasons(result.reasons[best], False, 4)
    for d, r in pos:
        st.write(f"• {r} **(+{d:g})**")
    if neg:
        st.markdown("**محدودیت‌های همین گزینه:**")
        for d, r in neg:
            st.write(f"• {r} **({d:g})**")

    st.subheader("رتبه‌بندی کامل")
    df = pd.DataFrame([
        {"نوع اسید": a, "English": ACIDS[a], "امتیاز": s}
        for a, s in ranking
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.bar_chart(df.set_index("نوع اسید")["امتیاز"])

    st.subheader("سه گزینه برتر")
    for i, (acid, score) in enumerate(ranking[:3], 1):
        with st.expander(f"{i}) {acid} — {score:.0f}/100", expanded=(i == 1)):
            st.write(DESCRIPTIONS[acid])
            for d, r in top_reasons(result.reasons[acid], True, 5):
                st.write(f"• {r} (+{d:g})")
            negs = top_reasons(result.reasons[acid], False, 3)
            if negs:
                st.markdown("**محدودیت‌ها:**")
                for d, r in negs:
                    st.write(f"• {r} ({d:g})")

    if result.warnings:
        st.subheader("⚠️ هشدارهای مهندسی")
        for w in result.warnings:
            st.warning(w)

    st.info(
        "این سامانه برای screening و Decision Support است. انتخاب نهایی باید با تست‌های acid–oil compatibility، "
        "reaction kinetics/coreflood، corrosion coupon در شرایط HPHT، و fracture conductivity تحت closure stress "
        "برای 2–3 گزینه برتر اعتبارسنجی شود."
    )

    report_lines = [
        "Acid Fracturing Acid Selector V2",
        "=" * 60,
        f"Best acid: {best}",
        f"Score: {best_score:.1f}/100",
        f"Confidence: {confidence(ranking)}",
        "",
        "INPUTS",
        f"Calcite: {calcite:.1f}%",
        f"Dolomite: {dolomite:.1f}%",
        f"Insolubles: {insolubles:.1f}%",
        f"Temperature: {temperature:.1f} C",
        f"Permeability: {permeability:.3f} mD",
        f"Closure stress: {closure_stress:.1f} MPa",
        f"Kmax/Kmin: {perm_contrast:.1f}",
        f"Natural fracture spacing: {fracture_spacing:.1f} m",
        f"Leakoff coefficient: {leakoff_x1e3:.2f}e-3 m/min^0.5",
        f"Target penetration: {target_penetration_m:.1f} m",
        f"Reservoir pressure: {reservoir_pressure_mpa:.1f} MPa",
        f"TVD: {tvd_m:.0f} m",
        f"Spent-fluid density: {spent_density_kgm3:.0f} kg/m3",
        f"Hydrostatic pressure: {hydro:.2f} MPa",
        f"Flowback margin: {margin:.2f} MPa",
        f"Material: {material}",
        f"Corrosion loss: {corrosion_loss:.3f} lb/ft2",
        f"API gravity: {api_gravity:.1f}",
        f"Asphaltene: {asphaltene_wt:.1f} wt%",
        "",
        "RANKING",
    ]
    for i, (a, s) in enumerate(ranking, 1):
        report_lines.append(f"{i}. {a}: {s:.1f}")
    if result.warnings:
        report_lines += ["", "WARNINGS"] + [f"- {w}" for w in result.warnings]

    st.download_button(
        "دانلود گزارش متنی",
        data="\n".join(report_lines).encode("utf-8"),
        file_name="acid_selection_v2_report.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.divider()
st.caption(
    "V2: داده‌های کمی مقاله‌ای + cutoffهای screening. آستانه‌هایی که استاندارد جهانی ندارند داخل برنامه صریحاً با برچسب heuristic معرفی شده‌اند."
)
