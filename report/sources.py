"""Реестр источников для отчёта (оформление по ГОСТ Р 7.0.100–2018).

В тексте на источник ссылаются как [@ключ] или [@ключ1 @ключ2]; номера в квадратных скобках
расставляются по порядку первого упоминания, список формируется автоматически.
Источники, на которые нет ссылок в тексте, в список не попадают.

ВАЖНО: перед сдачей каждую ссылку нужно открыть и сверить. Пометка CHECK означает, что сведения
получены из вторичных источников или по памяти и требуют проверки по первоисточнику.
"""
D = "дата обращения: 21.10.2026"
EL = "Текст: электронный"
PR = "Текст: непосредственный"

SOURCES: dict[str, str] = {
    # --- нормативные акты и стандарты ---
    "tk": f"Трудовой кодекс Российской Федерации от 30.12.2001 № 197-ФЗ (ст. 212, 214, 221) // КонсультантПлюс : справочная правовая система. – URL: https://www.consultant.ru/law/podborki/tk_obespechenie_siz/ ({D}). – {EL}.",
    "pot883": f"Об утверждении Правил по охране труда при строительстве, реконструкции и ремонте : приказ Минтруда России от 11.12.2020 № 883н (ред. от 29.04.2025) : зарег. в Минюсте России 24.12.2020 № 61787. – URL: https://legalacts.ru/doc/prikaz-mintruda-rossii-ot-11122020-n-883n-ob-utverzhdenii/ ({D}). – {EL}.",
    "siz_orders": f"Какие приказы сейчас регулируют выдачу СИЗ: № 997н или новые № 766 и № 767? // Контур : [сайт]. – URL: https://kontur.ru/qa/25758 ({D}). – {EL}.",
    "siz_ppt": f"Можно ли продлевать срок носки СИЗ, если они еще пригодны? // ППТ : [сайт]. – URL: https://ppt.ru/obzory/onlinegit/mozhno-li-prodlevat-srok-noski-siz-esli-oni-eshche-prigodny ({D}). – {EL}.",
    "pot782": f"Об утверждении Правил по охране труда при работе на высоте : приказ Минтруда России от 16.11.2020 № 782н : зарег. в Минюсте России 15.12.2020 № 61477. – URL: https://www.nstu.ru/static_files/63200/Mintrud_Pr_782_16.11.2020.pdf ({D}). – {EL}.",
    "gost_helmet": f"ГОСТ 12.4.087-84. Система стандартов безопасности труда. Строительство. Каски строительные. Технические условия. – Введ. 1985-01-01. – URL: https://www.gostinfo.ru/catalog/Details/?id=4157940 ({D}). – {EL}.",
    # CHECK: название и ссылка на ГОСТ 12.4.281-2021 получены из каталогов, сверить с текстом стандарта
    "gost_hv": f"ГОСТ 12.4.281-2021. Одежда специальная повышенной видимости. Технические требования и методы испытаний (взамен ГОСТ 12.4.281-2014). – Введ. 2022-10-01. – URL: https://www.normacs.info/projects/8357 ({D}). – {EL}.",
    # CHECK: точное название сверить
    "iso20471": f"ГОСТ Р ИСО 20471-2015. Одежда повышенной видимости. Методы испытаний и технические требования (идентичен ISO 20471:2013). – URL: https://cn.gostinfo.ru/catalog/Details/?id=6102235 ({D}). – {EL}.",
    # CHECK: реквизиты приведены по памяти
    "trts019": f"О безопасности средств индивидуальной защиты : технический регламент Таможенного союза ТР ТС 019/2011 : утв. решением Комиссии Таможенного союза от 09.12.2011 № 878. – {PR}.",
    "pp2464": f"О порядке обучения по охране труда и проверки знания требований охраны труда : постановление Правительства Российской Федерации от 24.12.2021 № 2464. – URL: https://normativ.kontur.ru/document/1/506934-postanovlenie-pravitelstva-rf-ot-24-12-2021-n-2464 ({D}). – {EL}.",
    # CHECK: размеры штрафов сверить с действующей редакцией КоАП РФ
    "koap": f"Штраф по ст. 5.27.1 КоАП РФ за нарушение требований охраны труда // Витвет : [сайт]. – URL: https://vitvet.com/articles/koap/sostavy/shtraf-5-27-1-koap-ohrana-truda/ ({D}). – {EL}.",
    "fz152": f"О персональных данных : федеральный закон от 27.07.2006 № 152-ФЗ (ст. 11). – URL: https://legalacts.ru/doc/152_FZ-o-personalnyh-dannyh/glava-2/statja-11/ ({D}). – {EL}.",
    # --- статистика ---
    # CHECK: вторичные источники (новостные сайты со ссылкой на Роструд), сверить с данными Роструда
    "rostrud2023": f"Производственный травматизм в России по данным Роструда за 2023 год // Бизон : [сайт]. – URL: https://bizon.ru/news/print/id/693088/format/smoothbox ({D}). – {EL}.",
    "rostrud2024": f"Производственный травматизм в России в 2024 году // BFM.ru : [сайт]. – URL: https://www.bfm.ru/news/529599 ({D}). – {EL}.",
    "antimalware": f"Видеоаналитика в промышленной безопасности: тренды и сценарии применения в 2026 году // Anti-Malware.ru : [сайт]. – URL: https://www.anti-malware.ru/analytics/Technology_Analysis/Industrial-Safety-Video-Analytics ({D}). – {EL}.",
    # --- история ---
    "cctv_clarion": f"The History of CCTV // Clarion UK : [сайт]. – URL: https://clarionuk.com/resources/cctv-history/ ({D}). – {EL}.",
    "cctv_wiki": f"Closed-circuit television // Wikipedia. – URL: https://en.wikipedia.org/wiki/Closed-circuit_television ({D}). – {EL}.",
    "viola": f"Viola P., Jones M. Rapid object detection using a boosted cascade of simple features // Proceedings of the 2001 IEEE Computer Society Conference on Computer Vision and Pattern Recognition. – 2001. – Vol. 1. – P. 511–518. – {PR}.",
    "dalal": f"Dalal N., Triggs B. Histograms of oriented gradients for human detection // Proceedings of the 2005 IEEE Computer Society Conference on Computer Vision and Pattern Recognition. – 2005. – Vol. 1. – P. 886–893. – {PR}.",
    "alexnet": f"Krizhevsky A., Sutskever I., Hinton G. E. ImageNet classification with deep convolutional neural networks // Advances in Neural Information Processing Systems. – 2012. – Vol. 25. – P. 1097–1105. – {PR}.",
    "rcnn": f"Girshick R., Donahue J., Darrell T., Malik J. Rich feature hierarchies for accurate object detection and semantic segmentation // Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. – 2014. – P. 580–587. – {PR}.",
    "yolo": f"Redmon J., Divvala S., Girshick R., Farhadi A. You Only Look Once: Unified, Real-Time Object Detection // Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. – 2016. – P. 779–788. – URL: https://openaccess.thecvf.com/content_cvpr_2016/html/Redmon_You_Only_Look_CVPR_2016_paper.html ({D}). – {EL}.",
    "coco": f"Lin T.-Y., Maire M., Belongie S. et al. Microsoft COCO: Common Objects in Context // Computer Vision – ECCV 2014. – 2014. – P. 740–755. – {PR}.",
    # CHECK: список авторов приведён по памяти
    "shrestha": f"Shrestha K., Shrestha P. P., Bajracharya D., Yfantis E. A. Hard-Hat Detection for Construction Safety Visualization // Journal of Construction Engineering. – 2015. – Art. 721380. – DOI: 10.1155/2015/721380. – {EL}.",
    "fang": f"Fang Q., Li H., Luo X., Ding L., Luo H., Rose T. M., An W. Detecting non-hardhat-use by a deep learning method from far-field surveillance videos // Automation in Construction. – 2018. – Vol. 85. – P. 1–9. – {PR}.",
    # CHECK: список авторов приведён по памяти
    "wu": f"Wu J., Cai N., Chen W., Wang H., Wang G. Automatic detection of hardhats worn by construction personnel: A deep learning approach and benchmark dataset // Automation in Construction. – 2019. – Vol. 106. – Art. 102894. – URL: https://workzonesafety.org/publication/automatic-detection-of-hardhats-worn-by-construction-personnel-a-deep-learning-approach-and-benchmark-dataset ({D}). – {EL}.",
    # CHECK: список авторов приведён по памяти
    "wang2020": f"Wang L., Xie L., Yang P., Deng Q., Du S., Xu L. Hardhat-Wearing Detection Based on a Lightweight Convolutional Neural Network with Multi-Scale Features and a Top-Down Module // Sensors. – 2020. – Vol. 20, № 7. – Art. 1868. – DOI: 10.3390/s20071868. – URL: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7180748/ ({D}). – {EL}.",
    # CHECK: полный список авторов и выходные данные
    "wojcik": f"Wójcik B. et al. A deep learning method for hard-hat-wearing detection based on head center localization // Bulletin of the Polish Academy of Sciences: Technical Sciences. – 2023. – URL: https://iitis.pl/en/node/3630 ({D}). – {EL}.",
    "sh17": f"Ahmad H. M., Rahimi A. SH17: A dataset for human safety and personal protective equipment detection in manufacturing industry // Journal of Safety Science and Resilience. – 2025. – Vol. 6, № 2. – P. 175–185. – DOI: 10.1016/j.jnlssr.2024.09.002. – URL: https://arxiv.org/abs/2407.04590 ({D}). – {EL}.",
    # --- рынок ---
    "axxon_docs": f"Equipment detector VL (детектор СИЗ) : документация AxxonSoft. – URL: https://docs.axxonsoft.com/confluence/x/1h6NDw ({D}). – {EL}.",
    "axxon_co": f"AxxonSoft: About company : [сайт]. – URL: https://www.axxonsoft.com/company ({D}). – {EL}.",
    "visionlabs": f"О компании VisionLabs : [сайт]. – URL: https://test.visionlabs.ru/about-us ({D}). – {EL}.",
    "visionlabs_atomdata": f"VisionLabs и «Атомдата» разработали сервис облачной видеоаналитики для промышленности // ComNews. – 2021. – 3 дек. – URL: https://www.comnews.ru/digital-economy/content/217763/2021-12-03/2021-w48/visionlabs-i-atomdata-razrabotali-servis-oblachnoy-videoanalitiki-dlya-promyshlennosti ({D}). – {EL}.",
    "vizor_cb": f"VizorLabs: company profile // CB Insights. – URL: https://www.cbinsights.com/company/vizorlabs ({D}). – {EL}.",
    "vizor_ms": f"Vizor Labs: видеоаналитика для промышленной безопасности // Microsoft : [сайт]. – URL: https://news.microsoft.com/ru-ru/features/vizorlabs/ ({D}). – {EL}.",
    "nornikel": f"Кольский дивизион «Норникеля» начал использовать систему видеоконтроля СИЗ // ComNews. – 2021. – 11 окт. – URL: https://www.comnews.ru/content/216854/2021-10-11/2021-w41/kolskiy-divizion-nornikelya-nachal-ispolzovat-sistemu-videokontrolya-siz ({D}). – {EL}.",
    "intenseye": f"Intenseye: About : [сайт]. – URL: https://intenseye.com/about ({D}). – {EL}.",
    "intenseye_tc": f"Intenseye raises $4M to boost workplace safety through computer vision // TechCrunch. – 2021. – 11 Feb. – URL: https://techcrunch.com/2021/02/11/intenseye-raises-4m-to-boost-workplace-safety-through-computer-vision/ ({D}). – {EL}.",
    # CHECK: обзор опубликован конкурирующим вендором, цифры считать заявленными, а не независимо проверенными
    "voxel": f"Intenseye vs Protex AI vs Spot AI // Voxel : [сайт]. – URL: https://www.voxelai.com/industry-insights/intenseye-vs-protex-ai-vs-spot-ai ({D}). – {EL}.",
    "intenseye_bi": f"Intenseye: company profile // Built In NYC. – URL: https://www.builtinnyc.com/company/intenseye ({D}). – {EL}.",
    "protex": f"Protex AI: 24/7 PPE Usage Detection : [сайт]. – URL: https://protex.ai/ppe-detection ({D}). – {EL}.",
    "protex_cb": f"Newmetrix alternatives and competitors // CB Insights. – URL: https://www.cbinsights.com/company/newmetrix/alternatives-competitors ({D}). – {EL}.",
    "viact": f"Intenseye vs viAct // PeerSpot. – URL: https://www.peerspot.com/products/comparisons/intenseye_vs_viact ({D}). – {EL}.",
    "everguard": f"Compare Everguard vs Intenseye // CB Insights. – URL: https://www.cbinsights.com/compare/everguard-vs-intenseye ({D}). – {EL}.",
    "oracle_nm": f"Oracle Acquisitions: Newmetrix : [сайт]. – URL: https://www.oracle.com/corporate/acquisitions/newmetrix ({D}). – {EL}.",
    "enr_nm": f"Oracle buys Newmetrix to integrate AI tech into cloud platform // Engineering News-Record. – URL: https://www.enr.com/articles/55605-oracle-buys-newmetrix-to-integrate-ai-tech-into-cloud-platform ({D}). – {EL}.",
    # --- модель и инструменты ---
    "yolo11": f"Ultralytics YOLO11 : документация. – URL: https://docs.ultralytics.com/models/yolo11 ({D}). – {EL}.",
    "rf_css": f"Construction Site Safety Computer Vision Model / Roboflow Universe Projects // Roboflow Universe. – URL: https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety ({D}). – {EL}.",
    "colab": f"Google Colaboratory : [сайт]. – URL: https://colab.research.google.com ({D}). – {EL}.",
    "opencv": f"OpenCV documentation : [сайт]. – URL: https://docs.opencv.org/ ({D}). – {EL}.",
    "pyside": f"Qt for Python (PySide6) : документация. – URL: https://doc.qt.io/qtforpython-6/ ({D}). – {EL}.",
    "sqlite": f"SQLite Documentation : [сайт]. – URL: https://www.sqlite.org/docs.html ({D}). – {EL}.",
    "pydocx": f"python-docx documentation : [сайт]. – URL: https://python-docx.readthedocs.io/ ({D}). – {EL}.",
    "openvino": f"OpenVINO documentation : [сайт]. – URL: https://docs.openvino.ai/ ({D}). – {EL}.",
}
