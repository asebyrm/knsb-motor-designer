# Glossary (TR / EN)

> Generated from `locales/{en,tr}.json` by `scripts/gen_glossary.py`. Do not edit by hand.

## Parameters

| Key | EN | TR |
| --- | --- | --- |
| `aft_gap` — Aft gap / Arka boşluk | Space between the grain and the nozzle entry. Keeps the last segment off the nozzle. | Grain ile nozzle girişi arasındaki boşluk. Son segmenti nozzle'dan uzak tutar. |
| `ambient_pressure` — Ambient pressure / Ortam basıncı | Outside air pressure where the motor fires. Sea level is 1.013 bar; lower it for high-altitude launches. | Motorun ateşlendiği yerdeki dış hava basıncı. Deniz seviyesi 1,013 bar'dır; yüksek irtifa için düşür. |
| `body_diameter` — Body diameter / Gövde çapı | Airframe outer diameter. It sets the frontal area used for drag. | Gövde dış çapı. Sürükleme için kullanılan alnı belirler. |
| `bolt_diameter` — Fastener Ø / Vida Ø | Diameter of the shear fasteners retaining the bulkhead and nozzle. Bigger bolts mean fewer of them. | Bulkhead ve nozzle'ı tutan kesme vidalarının çapı. Büyük vida daha az sayıda gerekir. |
| `bolt_shear_strength` — Fastener shear strength / Vida kesme dayanımı | Shear strength of the fastener material. ~200 MPa is a class-4.8 steel bolt. | Vida malzemesinin kesme dayanımı. ~200 MPa 4.8 sınıfı çelik vidadır. |
| `bulkhead_material` — Bulkhead material / Bulkhead malzemesi | Material of the forward closure disc. It carries the full pressure blow-out force. | Ön kapak diskinin malzemesi. Tüm basınç fırlatma kuvvetini taşır. |
| `bulkhead_thickness` — Bulkhead thickness / Bulkhead kalınlığı | Thickness of the forward closure. It sets how many fasteners you need to hold it in. | Ön kapağın kalınlığı. Onu tutmak için kaç vida gerektiğini belirler. |
| `c_star_efficiency` — c* efficiency / c* verimi | Real performance versus the theoretical value. If you have not static-fired, 0.90–0.95 is a reasonable estimate. | Gerçek performansın teorik değere oranı. Statik ateşleme yapmadıysan 0,90–0,95 makul bir tahmindir. |
| `case_inner_diameter` — Case inner Ø / Case iç Ø | Bore of the case tube. The liner sits inside this, then the grain inside the liner. | Case borusunun iç çapı. Liner bunun içine, grain de liner'ın içine oturur. |
| `case_length` — Case length / Case boyu | Internal length of the case. Leave blank to let it be fitted to the grain stack plus the nozzle seat. | Case'in iç boyu. Boş bırakırsan grain yığını artı nozzle oturağına göre hesaplanır. |
| `case_material` — Case material / Case malzemesi | The 3D-printed (or aluminium) chamber material. Its tensile strength and layer-adhesion factor decide the factor of safety. | 3D baskı (veya alüminyum) yanma odası malzemesi. Çekme dayanımı ve katman yapışma faktörü emniyet katsayısını belirler. |
| `case_wall_thickness` — Case wall thickness / Case cidar kalınlığı | Wall thickness of the case tube. Thicker walls raise the factor of safety but add mass. | Case borusunun cidar kalınlığı. Kalın cidar emniyet katsayısını yükseltir ama kütle ekler. |
| `convergence_half_angle` — Convergent half-angle / Yakınsak yarım açı | Cone angle feeding into the throat. It only affects the nozzle length, not performance; 30–45° is typical. | Boğaza giren koninin açısı. Yalnızca nozzle boyunu etkiler, performansı değil; 30–45° tipiktir. |
| `core_diameter` — Core Ø / Çekirdek Ø | Diameter of the central bore. A wider core lowers pressure and thrust but shortens burn time. | Merkezî deliğin çapı. Geniş çekirdek basıncı ve itkiyi düşürür ama yanma süresini kısaltır. |
| `density_factor` — Cast density factor / Döküm yoğunluğu faktörü | How close your cast grain gets to the ideal density. 0.95 is typical for hand-poured KNSB; lower it if your grains have voids. | Döktüğün grain'in ideal yoğunluğa ne kadar yaklaştığı. Elde dökülen KNSB için 0,95 tipiktir; boşluklu döküyorsan düşür. |
| `designer` — Designer / Tasarımcı | Your name or handle; recorded in the .eng/.rse comment and the report. | Adın veya rumuzun; .eng/.rse yorumuna ve rapora yazılır. |
| `divergence_half_angle` — Divergent half-angle / Iraksak yarım açı | Cone angle of the diverging section. 12–15° is normal; larger angles lose thrust to divergence. | Iraksayan bölümün koni açısı. 12–15° normaldir; büyük açılar ıraksama kaybı verir. |
| `drag_coefficient` — Drag coefficient Cd / Sürükleme katsayısı Cd | Overall drag coefficient of the rocket. 0.55 is a rough default; a clean rocket is nearer 0.4. | Roketin toplam sürükleme katsayısı. 0,55 kaba bir varsayılandır; temiz bir roket 0,4'e yakındır. |
| `dry_mass` — Rocket mass (without motor) / Roket kütlesi (motor hariç) | Loaded rocket mass without the motor’s propellant. Heavier rockets fly lower. | Motorun yakıtı hariç dolu roket kütlesi. Ağır roketler daha alçak uçar. |
| `erosion_coefficient` — Erosion coefficient K / Erozyon katsayısı K | Recession rate constant for the graphite throat. Realistic values are 0.02–0.1 mm/s; above 0.3 the model warns you. | Grafit boğaz için aşınma hızı sabiti. Gerçekçi değerler 0,02–0,1 mm/s'dir; 0,3 üzeri model uyarır. |
| `erosion_enabled` — Model throat erosion / Boğaz erozyonunu modelle | Whether the throat is allowed to widen during the burn. Leave off unless you have measured erosion — it is never a way to “fix” over-pressure. | Boğazın yanma sırasında genişlemesine izin verilip verilmeyeceği. Ölçmediysen kapalı tut — asla aşırı basıncı “düzeltmenin” yolu değildir. |
| `erosion_exponent` — Erosion exponent m / Erozyon üssü m | Pressure sensitivity of throat erosion. 0.8 is a common value. | Boğaz erozyonunun basınca duyarlılığı. 0,8 yaygın bir değerdir. |
| `expansion_ratio` — Expansion ratio (Ae/At) / Genişleme oranı (Ae/At) | Exit area divided by throat area. Use “Optimum expansion” to match sea level; too large and the flow separates. | Çıkış alanının boğaz alanına oranı. Deniz seviyesine göre ayarlamak için “Optimum genişleme”yi kullan; çok büyükse akış ayrılır. |
| `forward_gap` — Forward ullage gap / Ön boşluk (ullage) | Empty space between the bulkhead and the grain. A few millimetres is enough for ignition volume. | Bulkhead ile grain arasındaki boş hacim. Ateşleme hacmi için birkaç milimetre yeterlidir. |
| `grain_type` — Grain geometry / Grain geometrisi | How the propellant burns. BATES is neutral and recommended; a tube is progressive and pushes pressure up during the burn. | Yakıtın nasıl yandığı. BATES nötrdür ve önerilir; tüp progresiftir ve yanma boyunca basıncı yükseltir. |
| `launch_altitude` — Launch altitude / Fırlatma rakımı | Elevation of the launch site above sea level. Thinner air means less drag and a higher apogee. | Fırlatma sahasının deniz seviyesinden yüksekliği. İnce hava daha az sürükleme ve daha yüksek irtifa demektir. |
| `liner_material` — Liner material / Liner malzemesi | The ablative sleeve that protects the case from the flame. KNSB burns at ~1600 K — a plastic case will not survive without one. | Case'i alevden koruyan ablatif kovan. KNSB ~1600 K'de yanar — plastik case linersiz dayanmaz. |
| `liner_thickness` — Liner thickness / Liner kalınlığı | Thickness of that ablative layer. It must survive the whole burn plus a margin; long burns need more. | O ablatif katmanın kalınlığı. Tüm yanma boyunca artı pay ile dayanmalı; uzun yanmalar daha fazlasını ister. |
| `max_accel_g` — Max acceleration / Maks. ivme | Acceleration limit you are willing to accept, e.g. for airframe or electronics. Default 15 g. | Kabul ettiğin ivme sınırı, örn. gövde veya elektronik için. Varsayılan 15 g. |
| `meop_bar` — MEOP (case pressure limit) / MEOP (case basınç sınırı) | The maximum pressure your case can take. The peak (erosionless) chamber pressure must stay below this. | Case'inin dayanabileceği maksimum basınç. Tepe (erozyonsuz) oda basıncı bunun altında kalmalı. |
| `name` — Motor name / Motor adı | A label for this motor. It appears in exports and reports. | Bu motora bir etiket. Dışa aktarımlarda ve raporda görünür. |
| `nozzle_efficiency` — Nozzle efficiency / Nozzle verimi | Lump factor for friction and non-ideal flow in the nozzle. 0.95 is a common default. | Nozzle'daki sürtünme ve ideal olmayan akış için toplu katsayı. 0,95 yaygın bir varsayılandır. |
| `outer_diameter` — Grain outer Ø / Grain dış Ø | Outside diameter of the propellant grain. It has to fit inside the liner, and it sets how much propellant you have. | Yakıt grain'inin dış çapı. Liner'ın içine sığmalı ve ne kadar yakıtın olduğunu belirler. |
| `prefix` — Name prefix / Ad öneki | A short team code put before the class designation, e.g. PARS in PARS-J240. | Sınıf tanımının önüne konan kısa takım kodu, örn. PARS-J240'daki PARS. |
| `print_method` — Print method / Baskı yöntemi | How the case is made. FDM layers are weak across the print direction (factor 0.5); SLS is closer to isotropic (0.9). | Case'in nasıl üretildiği. FDM katmanları baskı yönüne dik zayıftır (faktör 0,5); SLS izotropa daha yakındır (0,9). |
| `propellant_id` — Propellant / Yakıt | The sugar propellant formulation. KNSB is potassium nitrate / sorbitol; changing it changes burn rate, c* and flame temperature. | Şeker-nitrat yakıt bileşimi. KNSB, potasyum nitrat / sorbitol karışımıdır; değiştirmek yanma hızını, c*'ı ve alev sıcaklığını değiştirir. |
| `rail_length` — Rail length / Rampa uzunluğu | Length of the launch rail or tower. A longer rail gives more speed before the rocket is unguided. | Fırlatma rampasının uzunluğu. Uzun rampa, roket güdümsüz kalmadan önce daha fazla hız verir. |
| `segment_count` — Segment count / Segment sayısı | Number of BATES segments stacked in the case. More segments means more burn area and higher thrust. | Case içine dizilen BATES segment sayısı. Daha fazla segment daha fazla yanma alanı ve daha yüksek itki demektir. |
| `segment_length` — Segment length / Segment boyu | Length of one BATES segment. Use “Make neutral” to get the length that keeps burn area constant. | Bir BATES segmentinin boyu. Yanma alanını sabit tutan boyu bulmak için “Nötr yap”ı kullan. |
| `segment_spacing` — Inter-segment gap / Segmentler arası boşluk | Small gap left between segments for the spacers/retainers. It barely affects ballistics, only the total stack length. | Segmentler arasına ara parça için bırakılan küçük boşluk. Balistiği neredeyse etkilemez, yalnızca toplam boyu. |
| `target_apogee` — Target apogee / Hedef irtifa | The altitude you want to reach. The solver looks for motors that get within a band of this. | Ulaşmak istediğin irtifa. Çözücü buna bir bant içinde yaklaşan motorları arar. |
| `throat_diameter` — Throat Ø / Boğaz Ø | The narrowest point of the nozzle. Making it smaller raises chamber pressure and thrust; too small and the case can burst. | Nozzle'ın en dar noktası. Küçültmek oda basıncını ve itkiyi yükseltir; çok küçükse case patlayabilir. |
| `throat_length` — Throat length / Boğaz boyu | Length of the straight throat section. Mostly a manufacturing choice; keep it short. | Düz boğaz bölümünün uzunluğu. Çoğunlukla üretim tercihidir; kısa tut. |

## Result metrics

| Key | EN | TR |
| --- | --- | --- |
| `average_thrust` — Average thrust / Ortalama itki | Total impulse divided by burn time. Combined with the class letter it gives the designation (e.g. J240). | Toplam impulsun yanma süresine bölümü. Sınıf harfiyle birlikte tanımı verir (örn. J240). |
| `burn_time` — Burn time / Yanma süresi | Time from ignition to when thrust drops back to 5 % of the peak. | Ateşlemeden itkinin tepe değerinin %5'ine düştüğü ana kadar geçen süre. |
| `cg_burnout` — CG at burnout / Yanma sonu CG | Centre of gravity from the forward face at burnout. | Yanma sonunda ön yüzden ağırlık merkezi. |
| `cg_initial` — CG at ignition / Ateşlemede CG | Centre of gravity from the forward face at ignition. | Ateşlemede ön yüzden ağırlık merkezi. |
| `designation` — Designation / Motor tanımı | NAR-style class letter plus rounded average thrust, e.g. J240. | NAR tarzı sınıf harfi artı yuvarlanmış ortalama itki, örn. J240. |
| `fos` — Min. factor of safety / Min. emniyet katsayısı | Case allowable stress divided by the stress at MEOP. Below 2.0 is not considered safe. | Case izin verilen gerilmenin MEOP'taki gerilmeye oranı. 2,0'ın altı güvenli sayılmaz. |
| `inert_mass` — Inert mass / Boş kütle | Motor mass once all the propellant is gone. | Tüm yakıt bittiğinde motor kütlesi. |
| `kn` — Klemmung Kn | Burning surface area divided by throat area. Larger Kn means higher chamber pressure and thrust; 150–400 is typical for KNSB. | Yanan yüzey alanının boğaz alanına oranı. Büyük Kn daha yüksek oda basıncı ve itki demektir; KNSB için 150–400 tipiktir. |
| `lstar` — L* | Chamber free volume divided by throat area. For KNSB roughly 250–1000 mm is normal. | Oda serbest hacminin boğaz alanına oranı. KNSB için kabaca 250–1000 mm normaldir. |
| `mass_ratio` — Mass ratio / Kütle oranı | Loaded mass divided by burnt-out mass. Higher is better for the rocket. | Dolu kütlenin yanma sonu kütlesine oranı. Roket için yüksek olması iyidir. |
| `min_j` — Min. J (port/throat) / Min. J (port/boğaz) | Smallest port-area / throat-area ratio during the burn. Below 2 the gas scrubs the grain and pressure gets unpredictable. | Yanma boyunca en küçük port alanı / boğaz alanı oranı. 2'nin altında gaz grain'i aşındırır ve basınç öngörülemez olur. |
| `motor_mass` — Motor mass / Motor kütlesi | Loaded mass of the motor alone. | Yalnızca motorun dolu kütlesi. |
| `peak_pressure` — Peak pressure (no erosion) / Tepe basınç (erozyonsuz) | Highest chamber pressure on the erosionless curve. This is what the case must survive (MEOP). | Erozyonsuz eğrideki en yüksek oda basıncı. Case'in dayanması gereken budur (MEOP). |
| `peak_thrust` — Peak thrust / Tepe itki | The highest instantaneous thrust during the burn. | Yanma boyunca ulaşılan en yüksek anlık itki. |
| `propellant_mass` — Propellant mass / Yakıt kütlesi | Mass of propellant actually consumed. | Gerçekte tüketilen yakıt kütlesi. |
| `specific_impulse` — Specific impulse / Özgül impuls | Impulse per unit weight of propellant burned — an efficiency number, in seconds. | Yanan yakıtın birim ağırlığı başına impuls — saniye cinsinden bir verim sayısı. |
| `thrust_to_weight` — Thrust / weight / İtki / ağırlık | Average thrust divided by lift-off weight. It should comfortably exceed 1, ideally 5+ off the rail. | Ortalama itkinin kalkış ağırlığına oranı. 1'i rahatça geçmeli, rampada ideali 5+. |
| `total_impulse` — Total impulse / Toplam impuls | Area under the thrust curve — the total ‘push’. It sets the motor class letter. | İtki eğrisinin altındaki alan — toplam “itiş”. Motor sınıf harfini belirler. |
| `total_length` — Total length / Toplam boy | Bulkhead face to nozzle exit — the value written into the .eng header. | Bulkhead yüzünden nozzle çıkışına — .eng başlığına yazılan değer. |
| `total_mass` — Motor total mass / Motor toplam kütlesi | Loaded motor mass at ignition, including case, nozzle and bulkhead. | Ateşlemede dolu motor kütlesi; case, nozzle ve bulkhead dâhil. |

## Derived measures

| Key | EN | TR |
| --- | --- | --- |
| `cg` — cg | Mass-weighted centre of the whole assembly; it moves as propellant burns. | Tüm yerleşimin kütle ağırlıklı merkezi; yakıt yandıkça hareket eder. |
| `exit_diameter` — exit_diameter | Nozzle exit Ø = throat Ø × √(expansion ratio). | Nozzle çıkış Ø = boğaz Ø × √(genişleme oranı). |
| `free_volume` — free_volume | Gas volume in the chamber = bore volume + convergent volume − remaining propellant. | Odadaki gaz hacmi = borusal hacim + yakınsak hacim − kalan yakıt. |
| `grain_length` — grain_length | Total axial length of the propellant stack including inter-segment gaps. | Segment arası boşluklar dâhil yakıt yığınının toplam eksenel boyu. |
| `lstar` — lstar | L* = chamber free volume / throat area. | L* = oda serbest hacmi / boğaz alanı. |
| `port_diameter` — port_diameter | Diameter of the smallest flow passage through the grain at this burn position. | Bu yanma konumunda grain içindeki en dar akış geçişinin çapı. |
| `total_length` — total_length | Sum of bulkhead + grain stack + gaps + nozzle. This goes into the .eng header. | Bulkhead + grain yığını + boşluklar + nozzle toplamı. .eng başlığına gider. |
| `ullage` — ullage | Empty (gas) volume before ignition. | Ateşlemeden önceki boş (gaz) hacim. |
| `web` — web | Web = (outer Ø − core Ø) / 2. It is how far the flame front travels, so it sets the burn time. | Web = (dış Ø − çekirdek Ø) / 2. Alev cephesinin katettiği mesafedir, yanma süresini bu belirler. |

## Warnings — what to do

| Key | EN | TR |
| --- | --- | --- |
| `WARN_ACCEL_LIMIT_EXCEEDED` — WARN_ACCEL_LIMIT_EXCEEDED | Peak acceleration exceeds your limit. Widen the throat for a softer thrust curve or raise the limit. | Tepe ivme sınırını aşıyor. Daha yumuşak itki eğrisi için boğazı genişlet ya da sınırı yükselt. |
| `WARN_APOGEE_UNCERTAINTY` — WARN_APOGEE_UNCERTAINTY | This apogee is a 1-DOF estimate; real flights typically scatter ±15–25 %. Verify in OpenRocket. | Bu irtifa 1-DOF tahminidir; gerçek uçuşlar tipik olarak ±%15–25 saçılır. OpenRocket ile doğrula. |
| `WARN_BULKHEAD_FASTENERS` — WARN_BULKHEAD_FASTENERS | A lot of shear bolts are needed to hold the closures. Use a larger bolt Ø or lower the pressure. | Kapakları tutmak için çok sayıda kesme vidası gerekiyor. Daha büyük vida Ø kullan veya basıncı düşür. |
| `WARN_BURN_TIME_EXCEEDED_LIMIT` — WARN_BURN_TIME_EXCEEDED_LIMIT | The burn ran past the simulation time limit. Check the geometry for an unrealistically thick web. | Yanma simülasyon süre sınırını aştı. Geometride gerçekçi olmayan kalın web olup olmadığını kontrol et. |
| `WARN_CONVERGENCE_NOT_REACHED` — WARN_CONVERGENCE_NOT_REACHED | The time step did not fully converge. The totals may be off by more than 0.1 %. | Zaman adımı tam yakınsamadı. Toplamlar %0,1'den fazla sapabilir. |
| `WARN_ENDBURNER_THERMAL_SOAK` — WARN_ENDBURNER_THERMAL_SOAK | An end-burner heats one spot of the case for the whole burn. Add liner thickness or keep the burn short. | Uç yanan grain case'in tek noktasını tüm yanma boyunca ısıtır. Liner kalınlığını artır veya yanmayı kısa tut. |
| `WARN_EROSIVE_BURNING` — WARN_EROSIVE_BURNING | Port-to-throat ratio drops below 2, so gas velocity scrubs the grain. Widen the core or the port. | Port/boğaz oranı 2'nin altına düşüyor, gaz hızı grain'i aşındırıyor. Çekirdeği veya portu genişlet. |
| `WARN_EROSIVE_BURNING_CRITICAL` — WARN_EROSIVE_BURNING_CRITICAL | Port-to-throat ratio drops below 1.5 — pressure is likely to spike. Widen the core significantly; the design is unsafe as-is. | Port/boğaz oranı 1,5'in altına düşüyor — basınç sıçraması olası. Çekirdeği belirgin biçimde genişlet; tasarım bu hâliyle güvensiz. |
| `WARN_EXPANSION_RATIO_SUBOPTIMAL` — WARN_EXPANSION_RATIO_SUBOPTIMAL | The expansion ratio is far from optimal for this pressure and altitude. Use “Optimum expansion”. | Genişleme oranı bu basınç ve irtifa için optimumdan uzak. “Optimum genişleme”yi kullan. |
| `WARN_EXTRAPOLATED_BURN_RATE` — WARN_EXTRAPOLATED_BURN_RATE | Chamber pressure went outside the measured burn-rate table. Treat the numbers as rough; keep the pressure inside 1–11 MPa if you can. | Oda basıncı ölçülmüş yanma hızı tablosunun dışına çıktı. Sayıları kaba kabul et; mümkünse basıncı 1–11 MPa arasında tut. |
| `WARN_FIT_GRAIN_DIAMETER` — WARN_FIT_GRAIN_DIAMETER | The grain does not fit inside the liner bore. Reduce the grain outer Ø or the liner thickness. | Grain liner deliğine sığmıyor. Grain dış Ø'yu veya liner kalınlığını azalt. |
| `WARN_FIT_GRAIN_LENGTH` — WARN_FIT_GRAIN_LENGTH | The grain stack is longer than the space in the case. Shorten a segment, drop one, or lengthen the case. | Grain yığını case'teki yerden uzun. Bir segmenti kısalt, birini çıkar ya da case'i uzat. |
| `WARN_FIT_LINER_STACK` — WARN_FIT_LINER_STACK | The liner is too thick for the case bore. Reduce the liner thickness. | Liner case deliği için çok kalın. Liner kalınlığını azalt. |
| `WARN_FIT_PORT_NONPOSITIVE` — WARN_FIT_PORT_NONPOSITIVE | The grain has no open port. Add a core Ø. | Grain'in açık portu yok. Bir çekirdek Ø ekle. |
| `WARN_FIT_THROAT_VS_CASE` — WARN_FIT_THROAT_VS_CASE | The throat Ø is larger than the case bore — geometrically impossible. Reduce the throat Ø. | Boğaz Ø case deliğinden büyük — geometrik olarak imkânsız. Boğaz Ø'yu azalt. |
| `WARN_FLOW_SEPARATION` — WARN_FLOW_SEPARATION | The nozzle is over-expanded for this pressure and the flow will separate. Reduce the expansion ratio. | Nozzle bu basınç için aşırı genişlemiş ve akış ayrılacak. Genişleme oranını düşür. |
| `WARN_GRAIN_CORE_TOO_LARGE` — WARN_GRAIN_CORE_TOO_LARGE | The core is a big fraction of the outer Ø, leaving a thin web and lots of leftover sliver. Shrink the core. | Çekirdek dış Ø'nun büyük bir kısmı; ince web ve çok artık sliver bırakır. Çekirdeği küçült. |
| `WARN_LINER_THIN` — WARN_LINER_THIN | The liner is thinner than recommended for this burn time. Increase it toward the suggested value. | Liner bu yanma süresi için önerilenden ince. Önerilen değere doğru artır. |
| `WARN_LONG_BURN_THERMAL` — WARN_LONG_BURN_THERMAL | Burn time is over 3 s, so heat soak into the case is significant. Increase the liner thickness. | Yanma süresi 3 s'yi aşıyor, case'e ısı geçişi belirgin. Liner kalınlığını artır. |
| `WARN_LOW_FOS` — WARN_LOW_FOS | Case factor of safety is below 2. Thicken the wall or lower the peak pressure before flying. | Case emniyet katsayısı 2'nin altında. Uçmadan önce cidarı kalınlaştır veya tepe basıncı düşür. |
| `WARN_LSTAR_OUT_OF_RANGE` — WARN_LSTAR_OUT_OF_RANGE | Characteristic length L* is outside the usual KNSB range. Resize the chamber free volume or the throat. | Karakteristik uzunluk L* KNSB'nin olağan aralığı dışında. Oda serbest hacmini veya boğazı yeniden boyutlandır. |
| `WARN_MARGINAL_FOS` — WARN_MARGINAL_FOS | Case factor of safety is between 2 and 3 — acceptable but tight. Consider a thicker wall. | Case emniyet katsayısı 2 ile 3 arasında — kabul edilir ama sınırda. Daha kalın cidar düşün. |
| `WARN_MEOP_EXCEEDED` — WARN_MEOP_EXCEEDED | Peak chamber pressure exceeds the case limit. Enlarge the throat, thicken the wall, or lower Kn. | Tepe oda basıncı case sınırını aşıyor. Boğazı büyüt, cidarı kalınlaştır veya Kn'yi düşür. |
| `WARN_MISSION_INFEASIBLE` — WARN_MISSION_INFEASIBLE | No motor in the search space met every constraint. See the binding constraint and suggested change. | Arama uzayındaki hiçbir motor tüm kısıtları sağlamadı. Bağlayıcı kısıta ve önerilen değişikliğe bak. |
| `WARN_NOZZLE_OVEREXPANDED` — WARN_NOZZLE_OVEREXPANDED | Exit pressure is well below ambient. Reduce the expansion ratio toward the optimum shown. | Çıkış basıncı ortamın epey altında. Genişleme oranını gösterilen optimuma doğru düşür. |
| `WARN_NOZZLE_UNDEREXPANDED` — WARN_NOZZLE_UNDEREXPANDED | Exit pressure is well above ambient; you are leaving thrust on the table. Increase the expansion ratio. | Çıkış basıncı ortamın epey üstünde; itki kaybediyorsun. Genişleme oranını artır. |
| `WARN_NO_EQUILIBRIUM_PRESSURE` — WARN_NO_EQUILIBRIUM_PRESSURE | The solver could not find a stable operating pressure. Increase the throat Ø or reduce the burning area. | Çözücü kararlı bir çalışma basıncı bulamadı. Boğaz Ø'yu büyüt veya yanma alanını azalt. |
| `WARN_NO_LINER` — WARN_NO_LINER | There is no liner. KNSB flame is ~1600 K — a plastic case needs an ablative liner. Add one. | Liner yok. KNSB alevi ~1600 K — plastik case ablatif liner ister. Ekle. |
| `WARN_PRESSURE_SOLVER_FALLBACK` — WARN_PRESSURE_SOLVER_FALLBACK | The pressure was found by root-finding rather than the closed form. The result is still valid; just noting the method. | Basınç kapalı form yerine kök bulma ile hesaplandı. Sonuç geçerli; yalnızca yöntemi belirtiyoruz. |
| `WARN_PRINT_DIRECTION_WEAK` — WARN_PRINT_DIRECTION_WEAK | FDM layer adhesion is weak across the print direction. Print the case hoop-wise or switch to SLS. | FDM katman yapışması baskı yönüne dik zayıftır. Case'i çevresel yönde bas veya SLS'e geç. |
| `WARN_PROGRESSIVE_GEOMETRY` — WARN_PROGRESSIVE_GEOMETRY | This geometry’s burn area grows during the burn, so pressure climbs. Switch to a multi-segment BATES for a flat curve. | Bu geometrinin yanma alanı yanma boyunca büyür, basınç tırmanır. Düz eğri için çok segmentli BATES'e geç. |
| `WARN_QUASI_STEADY_INVALID` — WARN_QUASI_STEADY_INVALID | The chamber fills slowly compared with the burn time, so the quasi-steady model is shaky. Use a smaller chamber or bigger throat. | Oda yanma süresine göre yavaş doluyor, quasi-steady model zayıf. Daha küçük oda veya daha büyük boğaz kullan. |
| `WARN_RAIL_EXIT_VELOCITY_LOW` — WARN_RAIL_EXIT_VELOCITY_LOW | Speed leaving the rail is below 20 m/s, so the rocket may be unstable. Use a longer rail or a punchier motor. | Rampadan çıkış hızı 20 m/s altında, roket stabil olmayabilir. Daha uzun rampa veya daha güçlü motor kullan. |
| `WARN_SLIVER_FRACTION_HIGH` — WARN_SLIVER_FRACTION_HIGH | A noticeable amount of propellant is left unburned at web-out. Rebalance the segment length or core Ø. | Web bitiminde kayda değer yakıt yanmadan kalıyor. Segment boyunu veya çekirdek Ø'yu yeniden dengele. |
| `WARN_SOLVER_BEST_EFFORT` — WARN_SOLVER_BEST_EFFORT | Result is the best found within the time budget, not a proven optimum. | Sonuç süre bütçesi içinde bulunan en iyisidir, kanıtlanmış optimum değil. |
| `WARN_SOLVER_TIMEOUT` — WARN_SOLVER_TIMEOUT | The solver hit its time budget and returned the best it found. Increase the time budget for a better search. | Çözücü süre bütçesine ulaştı ve bulduğu en iyisini döndürdü. Daha iyi arama için süreyi artır. |
| `WARN_THERMAL_LIMIT` — WARN_THERMAL_LIMIT | The case inner surface is predicted to pass its service temperature. Add liner thickness or shorten the burn. | Case iç yüzeyinin servis sıcaklığını aşacağı tahmin ediliyor. Liner kalınlığını artır veya yanmayı kısalt. |
| `WARN_THICK_WALL_MODEL` — WARN_THICK_WALL_MODEL | The wall is thick relative to the bore, so the thick-wall (Lamé) stress model is used. No action needed. | Cidar iç çapa göre kalın, bu yüzden kalın cidar (Lamé) gerilme modeli kullanılıyor. Bir şey yapmana gerek yok. |
| `WARN_THRUST_TO_WEIGHT_LOW` — WARN_THRUST_TO_WEIGHT_LOW | Thrust-to-weight is marginal. The rocket will accelerate slowly off the rail — use a stronger motor. | İtki-ağırlık oranı sınırda. Roket rampada yavaş hızlanır — daha güçlü motor kullan. |
| `WARN_UNCALIBRATED_DEFAULTS` — WARN_UNCALIBRATED_DEFAULTS | You are using default c* efficiency and density factor. Enter values from a static fire for accuracy. | Varsayılan c* verimi ve yoğunluk faktörü kullanıyorsun. Doğruluk için statik ateşleme değerlerini gir. |
| `WARN_UNREALISTIC_EROSION` — WARN_UNREALISTIC_EROSION | The erosion coefficient is far higher than graphite really erodes. Lower K below 0.3 mm/s or turn erosion off. | Erozyon katsayısı grafitin gerçekte aşındığından çok yüksek. K'yı 0,3 mm/s altına indir veya erozyonu kapat. |

## Action buttons

| Key | EN | TR |
| --- | --- | --- |
| `apply_suggestion` — Apply suggestion / Öneriyi uygula | Apply the suggested value and re-run the search. | Önerilen değeri uygular ve aramayı yeniden çalıştırır. |
| `estimate_from_altitude` — Estimate from altitude / İrtifadan hesapla | Runs the 1-DOF solver and proposes three motors for your target altitude. | 1-DOF çözücüyü çalıştırır ve hedef irtifan için üç motor önerir. |
| `make_neutral` — Make neutral / Nötr yap | Sets the segment length so the burning area stays constant through the burn (a flat pressure curve). | Segment boyunu, yanan alanı yanma boyunca sabit tutacak şekilde ayarlar (düz basınç eğrisi). |
| `make_neutral_disabled` — None | Only available for BATES grains. | Yalnızca BATES grain'lerde kullanılabilir. |
| `optimum_expansion` — Optimum expansion / Optimum genişleme | Sets the expansion ratio so the exhaust is fully expanded to the ambient pressure you entered. | Genişleme oranını, egzozun girdiğin ortam basıncına tam genişleyeceği şekilde ayarlar. |
| `run_mission` — Calculate / Hesapla | Search for BATES motors that reach the target apogee within your constraints. | Kısıtların içinde hedef irtifaya ulaşan BATES motorlarını arar. |
| `toggle_units` — None | Switch every field and result between metric and imperial units. | Tüm alanları ve sonuçları metrik ile imperial arasında değiştirir. |

