"""Export laporan QC ke CSV dan Excel (.xlsx)."""

import csv
import io
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HEADERS = [
    "Kode Produksi",
    "Tanggal Produksi",
    "Nama Produk",
    "Part Number",
    "Line",
    "Shift",
    "Metode",
    "Total Produksi",
    "Diperiksa",
    "Lolos",
    "Cacat",
    "Defect Rate (%)",
    "Kategori Kecacatan",
    "Inspector",
    "Status",
]

FIELD_MAP = [
    "kode_produksi",
    "tanggal",
    "produk",
    "part_number",
    "line",
    "shift",
    "metode",
    "total_produksi",
    "diperiksa",
    "lolos",
    "cacat",
    "defect_rate",
    "kategori",
    "inspector",
    "status",
]


def _filename(extension, dari, sampai):
    return f"laporan-qc-{dari:%Y%m%d}-{sampai:%Y%m%d}.{extension}"


def _stringify(value):
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y %H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", ",")
    return value


def export_csv(rows, dari, sampai, meta=None):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{_filename("csv", dari, sampai)}"'
    )
    response.write("\ufeff")  # BOM agar Excel membaca UTF-8 dengan benar
    writer = csv.writer(response, delimiter=";")

    if meta:
        writer.writerow([f"Laporan Quality Control - {settings.APP_NAME}"])
        writer.writerow(["Periode", f"{dari:%d-%m-%Y} s.d. {sampai:%d-%m-%Y}"])
        if meta.get("filter_text"):
            writer.writerow(["Filter", meta["filter_text"]])
        writer.writerow([])

    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow([_stringify(row.get(field, "")) for field in FIELD_MAP])
    return response


def export_xlsx(rows, dari, sampai, meta=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Laporan QC"

    title_font = Font(bold=True, size=14)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E79")
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    sheet["A1"] = f"Laporan Quality Control - {settings.APP_NAME}"
    sheet["A1"].font = title_font
    sheet["A2"] = "Periode"
    sheet["B2"] = f"{dari:%d-%m-%Y} s.d. {sampai:%d-%m-%Y}"
    if meta and meta.get("filter_text"):
        sheet["A3"] = "Filter"
        sheet["B3"] = meta["filter_text"]
    start_row = 5

    for column, header in enumerate(HEADERS, start=1):
        cell = sheet.cell(row=start_row, column=column, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = border

    numeric_fields = ("total_produksi", "diperiksa", "lolos", "cacat")

    for index, row in enumerate(rows, start=start_row + 1):
        for column, field in enumerate(FIELD_MAP, start=1):
            value = row.get(field, "")
            if field == "defect_rate":
                # Simpan sebagai angka agar bisa dihitung ulang di Excel.
                cell = sheet.cell(
                    row=index, column=column, value=round(float(value or 0), 2)
                )
                cell.number_format = "0.00"
                cell.alignment = Alignment(horizontal="right")
            elif field in numeric_fields:
                cell = sheet.cell(row=index, column=column, value=int(value or 0))
                cell.number_format = "#,##0"
                cell.alignment = Alignment(horizontal="right")
            else:
                cell = sheet.cell(row=index, column=column, value=_stringify(value))
            cell.border = border

    widths = [20, 16, 26, 16, 8, 8, 18, 14, 12, 10, 10, 14, 34, 18, 10]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = sheet.cell(row=start_row + 1, column=1)
    sheet.auto_filter.ref = (
        f"A{start_row}:{get_column_letter(len(HEADERS))}{start_row + len(rows)}"
    )

    # Sheet ringkasan
    totals = summary_rows(rows)
    recap = workbook.create_sheet("Ringkasan")
    recap["A1"] = "Ringkasan Kualitas"
    recap["A1"].font = title_font
    recap_rows = [
        ("Total produksi", totals["total_production"]),
        ("Total diperiksa", totals["diperiksa"]),
        ("Produk lolos", totals["lolos"]),
        ("Produk cacat", totals["cacat"]),
        ("Defect rate (%)", round(totals["defect_rate"], 2)),
        ("Jumlah sesi", len(rows)),
    ]
    for index, (label, value) in enumerate(recap_rows, start=3):
        recap.cell(row=index, column=1, value=label).font = Font(bold=True)
        recap.cell(row=index, column=2, value=value)
    recap.column_dimensions["A"].width = 24
    recap.column_dimensions["B"].width = 18

    buffer = io.BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{_filename("xlsx", dari, sampai)}"'
    )
    return response


def summary_rows(rows):
    inspected = sum(row["diperiksa"] for row in rows)
    failed = sum(row["cacat"] for row in rows)
    return {
        "total_production": sum(row["total_produksi"] for row in rows),
        "diperiksa": inspected,
        "lolos": sum(row["lolos"] for row in rows),
        "cacat": failed,
        "defect_rate": (failed / inspected * 100) if inspected else 0,
    }
