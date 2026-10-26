"""Большой штамп (форма 2 по ГОСТ 2.104) для страницы оглавления.

Рамка страницы и малый штамп берутся из колонтитула образца (группа фигур). Здесь рамка сохраняется,
а штамп из группы заменяется большим: 8 строк по 5 мм, как в ведомости отчёта (слева подписи, справа
обозначение, наименование темы, «Лит. / Лист / Листов» и организация). Шрифт ячеек – Arial, курсив, обозначение работы – 20 пт
(Правила оформления письменных работ, п. 5.1).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}
DECL = " ".join(f'xmlns:{k}="{v}"' for k, v in NS.items() if k in ("w", "wps", "a"))

# система координат группы фигур образца: ширина 20028, высота 20151 условных единиц
UX = 109.4            # единиц на мм по горизонтали
UY = 69.33            # единиц на мм по вертикали
X_LEFT, X_RIGHT = 10, 19990
Y_BOTTOM = 19989
ROW = 5 * UY          # высота строки штампа, 5 мм
Y_TOP = Y_BOTTOM - 8 * ROW

# вертикали левого блока (как у малого штампа образца): Изм, Лист, № докум., Подпись, Дата = 10+10+25+15+10 мм
COL = [X_LEFT, 1093, 2186, 4919, 6557, 7650]
X_TITLE_R = int(7650 + 63 * UX)           # конец ячейки наименования
X_LIT = X_TITLE_R + int(15 * UX)           # конец ячейки «Лит.»
X_LIST = X_LIT + int(15 * UX)              # конец ячейки «Лист»

THICK, THIN = 25400, 12700


@dataclass
class StampData:
    designation: str = "ПП.990000.000 ПЗ"
    title: str = "Система компьютерного зрения для мониторинга средств индивидуальной защиты"
    developer: str = "Гридасов А.Ю."
    supervisor: str = "Сафарьян О. А."
    controller: str = ""
    approver: str = "Сафарьян О. А."
    organisation: tuple[str, ...] = ("ДГТУ", "Группа ВКБ32")
    sheets_total: int = 0
    first_page: int = 7


def y(k: float) -> int:
    return round(Y_TOP + k * ROW)


class _Ids:
    def __init__(self, start: int):
        self.n = start

    def next(self) -> int:
        self.n += 1
        return self.n


def _line(ids: _Ids, x1, y1, x2, y2, width) -> str:
    n = ids.next()
    return (
        f'<wps:wsp {DECL}><wps:cNvPr id="{n}" name="Line {n}"/><wps:cNvCnPr><a:cxnSpLocks noChangeShapeType="1"/></wps:cNvCnPr>'
        f'<wps:spPr bwMode="auto"><a:xfrm><a:off x="{min(x1, x2)}" y="{min(y1, y2)}"/>'
        f'<a:ext cx="{max(abs(x2 - x1), 1)}" cy="{max(abs(y2 - y1), 1)}"/></a:xfrm>'
        f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom><a:noFill/><a:ln w="{width}"><a:solidFill>'
        f'<a:srgbClr val="000000"/></a:solidFill><a:round/></a:ln><a:effectLst/></wps:spPr><wps:bodyPr/></wps:wsp>'
    )


def _run(text: str, size_hp: int, italic: bool = True) -> str:
    rpr = (
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
        f'{"<w:i/>" if italic else ""}<w:sz w:val="{size_hp}"/><w:szCs w:val="{size_hp}"/></w:rPr>'
    )
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{_esc(text)}</w:t></w:r>"


def _page_field(size_hp: int, cached: str) -> str:
    rpr = (
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
        f'<w:i/><w:sz w:val="{size_hp}"/><w:szCs w:val="{size_hp}"/></w:rPr>'
    )
    return (
        f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r>{rpr}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
        f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r>{rpr}<w:t>{cached}</w:t></w:r>'
        f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>'
    )


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _box(ids: _Ids, x1, y1, x2, y2, paragraphs: list[str], anchor="ctr") -> str:
    n = ids.next()
    return (
        f'<wps:wsp {DECL}><wps:cNvPr id="{n}" name="Rectangle {n}"/><wps:cNvSpPr><a:spLocks noChangeArrowheads="1"/></wps:cNvSpPr>'
        f'<wps:spPr bwMode="auto"><a:xfrm><a:off x="{x1}" y="{y1}"/><a:ext cx="{x2 - x1}" cy="{y2 - y1}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></wps:spPr>'
        f'<wps:txbx><w:txbxContent>{"".join(paragraphs)}</w:txbxContent></wps:txbx>'
        f'<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="12700" tIns="0" rIns="12700" bIns="0" anchor="{anchor}" '
        'anchorCtr="0" upright="1"/></wps:wsp>'
    )


def _par(runs: str, jc="center", line=240) -> str:
    return (f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="{line}" w:lineRule="auto"/>'
            f'<w:jc w:val="{jc}"/></w:pPr>{runs}</w:p>')


def stamp_shapes(data: StampData) -> list[etree._Element]:
    ids = _Ids(300)
    xml: list[str] = []
    L = lambda *a: xml.append(_line(ids, *a))  # noqa: E731
    B = lambda x1, y1, x2, y2, paras, **kw: xml.append(_box(ids, x1, y1, x2, y2, paras, **kw))  # noqa: E731
    cell = lambda text, size=18, jc="center": [_par(_run(text, size), jc)]  # noqa: E731

    xl, xr, xm = COL[0], X_RIGHT, COL[5]
    # горизонтали
    L(xl, y(0), xr, y(0), THICK)                    # верх штампа
    L(xl, y(1), xm, y(1), THIN)
    L(xl, y(2), xr, y(2), THICK)                    # над строкой «Изм. Лист …» и под обозначением
    L(xl, y(3), xm, y(3), THICK)
    for k in (4, 5, 6, 7):
        L(xl, y(k), xm, y(k), THIN)
    L(X_TITLE_R, y(3), xr, y(3), THIN)              # под заголовками «Лит. Лист Листов»
    L(X_TITLE_R, y(4), xr, y(4), THICK)             # над ячейкой организации
    # вертикали
    L(xm, y(0), xm, y(8), THICK)                    # граница левого и правого блоков
    L(COL[1], y(2), COL[1], y(3), THIN)             # Изм | Лист: только в строке заголовков
    for x in COL[2:5]:
        L(x, y(2), x, y(8), THIN)
    L(X_TITLE_R, y(2), X_TITLE_R, y(8), THICK)      # наименование | Лит.
    for x in (X_LIT, X_LIST):
        L(x, y(2), x, y(4), THIN)

    # заголовки левого блока
    for (a, b), text in zip(zip(COL[:-1], COL[1:]), ("Изм.", "Лист", "№ докум.", "Подпись", "Дата")):
        B(a, y(2), b, y(3), cell(text))
    # роли и фамилии
    rows = [(3, "Разраб.", data.developer), (4, "Руков.пр", data.supervisor),
            (6, "Н. контр.", data.controller), (7, "Утв.", data.approver)]
    for k, role, name in rows:
        B(COL[0], y(k), COL[2], y(k + 1), cell(role, jc="left"))
        if name:
            B(COL[2], y(k), COL[3], y(k + 1), cell(name, jc="left"))
    # обозначение
    B(xm, y(0), xr, y(2), [_par(_run(data.designation, 40), "center")])
    # наименование
    B(xm, y(2), X_TITLE_R, y(8), [_par(_run(data.title, 22), "center")])
    # Лит. / Лист / Листов
    for (a, b), text in zip(((X_TITLE_R, X_LIT), (X_LIT, X_LIST), (X_LIST, xr)), ("Лит.", "Лист", "Листов")):
        B(a, y(2), b, y(3), cell(text))
    B(X_LIT, y(3), X_LIST, y(4), [_par(_page_field(20, str(data.first_page)), "right")])  # номер страницы – по правому краю
    B(X_LIST, y(3), xr, y(4), cell(str(data.sheets_total or ""), 20))
    # организация
    B(X_TITLE_R, y(4), xr, y(8), [_par(_run(line, 26), "center") for line in data.organisation])
    return [etree.fromstring(s) for s in xml]


def build_toc_footer(source_footer, target_footer, data: StampData) -> None:
    """Заполняет target_footer (w:ftr): рамка из source_footer + большой штамп."""
    src = source_footer._element if hasattr(source_footer, "_element") else source_footer
    tgt = target_footer._element if hasattr(target_footer, "_element") else target_footer

    holder = next(p for p in src.findall("w:p", NS) if p.find(".//mc:AlternateContent", NS) is not None)
    paragraph = copy.deepcopy(holder)
    ac = paragraph.find(".//mc:AlternateContent", NS)
    drawing = ac.find("mc:Choice/w:drawing", NS)
    ac.getparent().replace(ac, drawing)  # запасной вариант VML не нужен

    group = drawing.find(".//wpg:wgp", NS)
    kids = list(group)
    for extra in kids[3:]:               # cNvGrpSpPr, grpSpPr и рамка остаются, штамп образца удаляется
        group.remove(extra)
    for shape in stamp_shapes(data):
        group.append(shape)
    drawing.find(".//wp:docPr", NS).set("id", "215")

    for attr in list(paragraph.attrib):
        del paragraph.attrib[attr]       # w14:paraId и rsid не нужны в новой части
    for child in list(tgt):
        tgt.remove(child)
    tgt.append(paragraph)
