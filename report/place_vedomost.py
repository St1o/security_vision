"""Переносит ведомость в конец отчёта и пересчитывает номера листов.

Работает с ГОТОВЫМ файлом отчёта (в котором руками уже сделаны правки), а не пересобирает его из исходников:

    python report/place_vedomost.py --report Отчёт.docx --front Первые_листы.docx \
        --out-report Отчёт_с_ведомостью.docx --out-front Первые_5_листов.docx [--front-pages 5]

Что делается:
  1. Ведомость вынимается из файла с первыми листами и вставляется последним листом отчёта (отдельный раздел без рамки).
  2. Содержание получает номер front_pages+1 (раньше перед ним была ведомость, теперь её нет), номера страниц в оглавлении,
     «Лист» и «Листов» в штампе оглавления пересчитываются.
  3. В ведомости «Лист» и «Листов» равны общему числу листов (как в образце), число листов отчёта без приложений и приложения
     пересчитываются по фактической разбивке на страницы (LibreOffice).
Число страниц считается в LibreOffice; в Word оно может отличаться, тогда эти числа нужно поправить вручную.
"""
from __future__ import annotations

import argparse
import copy
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS14 = "http://schemas.microsoft.com/office/word/2010/wordml"


def pdf_pages(docx: Path) -> list[str]:
    out = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(docx)],
                   check=True, capture_output=True, timeout=300)
    text = subprocess.run(["pdftotext", "-layout", str(out / (docx.stem + ".pdf")), "-"],
                          capture_output=True, text=True).stdout
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def text_of(el) -> str:
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def style_name(doc, p) -> str:
    ps = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    if ps is None:
        return ""
    for s in doc.styles.element.findall(qn("w:style")):
        if s.get(qn("w:styleId")) == ps.get(qn("w:val")):
            nm = s.find(qn("w:name"))
            return nm.get(qn("w:val")).lower() if nm is not None else ""
    return ""


def shift_toc(doc, delta: int) -> int:
    """Номера страниц в оглавлении сдвигаются на delta."""
    n = 0
    for p in doc.element.body.iter(qn("w:p")):
        if style_name(doc, p).startswith("toc"):
            ts = list(p.iter(qn("w:t")))
            if ts and re.fullmatch(r"\d+", ts[-1].text or ""):      # табуляция лежит отдельным элементом w:tab
                ts[-1].text = str(int(ts[-1].text) + delta)
                n += 1
    return n


def strip_word_ids(el) -> None:
    """Идентификаторы правок Word (w14:paraId, rsid) в переносимом фрагменте не нужны."""
    for e in el.iter():
        for a in list(e.attrib):
            if a.startswith("{" + NS14 + "}") or a.startswith("{" + W + "}rsid"):
                del e.attrib[a]


def set_cell_text(tc, text: str) -> None:
    ts = list(tc.iter(qn("w:t")))
    if ts:
        ts[0].text = text
        for t in ts[1:]:
            t.text = ""


def build(args) -> None:
    report = Document(args.report)
    front_pages = args.front_pages

    # 1. содержание: номер листа и номера страниц в оглавлении
    sect0 = report.sections[0]._sectPr
    pg = sect0.find(qn("w:pgNumType"))
    old_start = int(pg.get(qn("w:start"))) if pg is not None else 1
    new_start = front_pages + 1
    pg.set(qn("w:start"), str(new_start))
    changed = shift_toc(report, new_start - old_start)
    print(f"содержание: {old_start} -> {new_start}, номеров в оглавлении сдвинуто: {changed}")

    tmp = Path(tempfile.mkdtemp()) / "step1.docx"
    report.save(str(tmp))
    pages = pdf_pages(tmp)
    n_pdf = len(pages)
    k = next(i for i, p in enumerate(pages) if i > 1 and re.search(r"Приложение А\s*\n", p)) + 1   # номер pdf-страницы
    report_sheets = k - 1                       # от содержания до конца перечня источников
    appendix_sheets = n_pdf - report_sheets
    total = front_pages + n_pdf + 1             # первые листы + отчёт + ведомость
    print(f"страниц отчёта {n_pdf}, без приложений {report_sheets}, приложение {appendix_sheets}, всего листов {total}")

    # 2. штамп оглавления: «Лист» и «Листов»
    footer = report.sections[0].footer._element
    for t in footer.iter(qn("w:t")):
        if t.text == str(old_start):
            t.text = str(new_start)           # кэш поля PAGE
        elif re.fullmatch(r"\d{2,3}", t.text or ""):
            t.text = str(total)               # «Листов»

    # 3. ведомость из файла с первыми листами
    front = Document(args.front)
    table = next(t for t in front.tables if "Документация общая" in text_of(t._tbl))
    body = front.element.body
    els = list(body)
    idx = els.index(table._tbl)
    note = els[idx + 1] if els[idx + 1].tag == qn("w:p") else None
    tbl = copy.deepcopy(table._tbl)
    note_p = copy.deepcopy(note) if note is not None else None
    for frag in (tbl, note_p):
        if frag is not None:
            strip_word_ids(frag)
            for rs in list(frag.iter(qn("w:rStyle"))):     # стиль «ac» в отчёте отсутствует
                rs.getparent().remove(rs)
            # комментарии автора образца остаются в его файле: ссылки на них в отчёте без части comments.xml недопустимы
            for tag in ("w:commentRangeStart", "w:commentRangeEnd"):
                for e in list(frag.iter(qn(tag))):
                    e.getparent().remove(e)
            for e in list(frag.iter(qn("w:commentReference"))):
                run = e.getparent()
                run.getparent().remove(run)

    # строки приложений: ТЗ убрано, остались листинги
    for tr in tbl.iter(qn("w:tr")):
        cells = [(tc, text_of(tc)) for tc in tr.findall(qn("w:tc"))]
        joined = " ".join(t for _, t in cells)
        if "Приложение А-Техническое" in joined:
            for tc, t in cells:
                if t.startswith("Приложение А-"):
                    set_cell_text(tc, "Приложение А-Листинг кода")
                elif re.fullmatch(r"\d+", t.strip()) and t.strip() not in ("3",):
                    set_cell_text(tc, str(appendix_sheets))
        elif "Приложение Б-" in joined:
            for tc, t in cells:
                set_cell_text(tc, "")
        elif "Отчет по производственной" in joined:
            for tc, t in cells:
                if t.endswith("*"):
                    set_cell_text(tc, f"{report_sheets}*")
    # штамп ведомости: «Лист» и «Листов» равны общему числу листов
    for tr in tbl.iter(qn("w:tr")):
        tcs = tr.findall(qn("w:tc"))
        texts = [text_of(tc) for tc in tcs]
        if texts and texts[0].startswith("Разраб"):
            for tc, t in zip(tcs[1:], texts[1:]):
                if t.strip() in ("6", "33", "71", "72", "1"):
                    set_cell_text(tc, str(total))

    # 4. новый раздел в конце отчёта: без рамки, поля как у первых листов
    new_sec = report.add_section(WD_SECTION.NEW_PAGE)
    new_sec.footer.is_linked_to_previous = False      # свой (пустой) колонтитул, а не рамка с малым штампом
    new_sec.header.is_linked_to_previous = False
    sp = new_sec._sectPr
    for old in sp.findall(qn("w:pgNumType")):
        sp.remove(old)
    mar = sp.find(qn("w:pgMar"))
    for k_, v in (("top", 567), ("right", 567), ("bottom", 567), ("left", 1134), ("header", 708), ("footer", 708)):
        mar.set(qn("w:" + k_), str(v))
    sp.addprevious(tbl)
    if note_p is not None:
        sp.addprevious(note_p)
    report.save(args.out_report)
    print("отчёт:", args.out_report)

    # 5. первые листы без ведомости
    front = Document(args.front)
    body = front.element.body
    els = list(body)
    t_el = next(t._tbl for t in front.tables if "Документация общая" in text_of(t._tbl))
    i = els.index(t_el)
    # абзац с разрывом раздела перед таблицей: его свойства раздела переходят на весь документ
    br_par = next(e for e in reversed(els[:i]) if e.tag == qn("w:p") and e.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None)
    first_sect = br_par.find(qn("w:pPr") + "/" + qn("w:sectPr"))
    final_sect = body.find(qn("w:sectPr"))
    for e in els[i:]:
        if e is not final_sect:
            body.remove(e)
    new_final = copy.deepcopy(first_sect)
    body.remove(final_sect)
    body.append(new_final)
    br_par.getparent().remove(br_par)
    front.save(args.out_front)
    print("первые листы:", args.out_front)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--front", required=True)
    ap.add_argument("--out-report", required=True)
    ap.add_argument("--out-front", required=True)
    ap.add_argument("--front-pages", type=int, default=5, help="сколько листов идёт перед оглавлением")
    build(ap.parse_args())
