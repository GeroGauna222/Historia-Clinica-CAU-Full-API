from datetime import date
from decimal import Decimal
import io
import zipfile

from app.routes.facturacion_routes import (
    INITIAL_PRACTICAS_SEED,
    _build_export_matrix,
    _format_date_ar,
    _generate_xlsx_bytes,
    _normalize_iva,
    _serialize_registro,
)


def test_swiss_medical_catalog_seed_count():
    smg_practices = [p for p in INITIAL_PRACTICAS_SEED if p[0] == "swiss_medical"]
    assert len(smg_practices) == 22

    # Check some key codes
    codes = {p[2]: p for p in smg_practices}
    assert "25040112" in codes  # Hosp de Dia Jornada Simple mensual
    assert Decimal(str(codes["25040112"][4])) == Decimal("631882.70")
    assert "42011200" in codes  # Traumatologia
    assert "25010230" in codes  # Postural


def test_normalize_iva():
    assert _normalize_iva("ADHERENTE") == "ADHERENTE"
    assert _normalize_iva("adherente") == "ADHERENTE"
    assert _normalize_iva("OBLIGATORIO") == "OBLIGATORIO"
    assert _normalize_iva(None) == "OBLIGATORIO"
    assert _normalize_iva("") == "OBLIGATORIO"


def test_format_date_ar():
    assert _format_date_ar("2026-09-07") == "07/09/2026"
    assert _format_date_ar(date(2026, 9, 15)) == "15/09/2026"
    assert _format_date_ar("") == ""


def test_serialize_registro_swiss_fields():
    raw_row = {
        "id": 10,
        "financiador": "swiss_medical",
        "fecha_realizacion": "2026-09-01",
        "paciente_id": 5,
        "paciente_nombre": "COSTA MIGUEL",
        "nro_afiliado": "7025863000096",
        "iva": "OBLIGATORIO",
        "cud": "SI",
        "cantidad": 1,
        "es_asistencia_adicional": 1,
        "practica_id": 4,
        "practica_codigo": "25040112",
        "practica_descripcion": "REHABILITACION - HOSP DE DIA JORNADA SIMPLE ( MENSUAL)",
        "importe": Decimal("0.00"),
        "gastos": None,
        "autorizacion": "200649",
    }
    ser = _serialize_registro(raw_row)
    assert ser["iva"] == "OBLIGATORIO"
    assert ser["es_asistencia_adicional"] is True
    assert ser["importe"] == 0.0


def test_build_export_matrix_discapacidad():
    registros = [
        {
            "id": 1,
            "financiador": "swiss_medical",
            "fecha_realizacion": "2026-09-01",
            "paciente_nombre": "COSTA MIGUEL",
            "nro_afiliado": "7025863000096",
            "iva": "OBLIGATORIO",
            "cud": "SI",
            "cantidad": 1,
            "es_asistencia_adicional": False,
            "practica_codigo": "25040112",
            "practica_descripcion": "REHABILITACION - HOSP DE DIA",
            "importe": Decimal("631882.70"),
            "autorizacion": "200649",
        },
        {
            "id": 2,
            "financiador": "swiss_medical",
            "fecha_realizacion": "2026-09-11",
            "paciente_nombre": "COSTA MIGUEL",
            "nro_afiliado": "7025863000096",
            "iva": "OBLIGATORIO",
            "cud": "SI",
            "cantidad": 1,
            "es_asistencia_adicional": True,  # Additional attendance with *
            "practica_codigo": "25040112",
            "practica_descripcion": "REHABILITACION - HOSP DE DIA",
            "importe": Decimal("0.00"),
            "autorizacion": "200649",
        },
        {
            "id": 3,
            "financiador": "swiss_medical",
            "fecha_realizacion": "2026-09-23",
            "paciente_nombre": "SANCHEZ OSVALDO",
            "nro_afiliado": "7016575",
            "iva": "ADHERENTE",
            "cud": "NO",
            "cantidad": 1,
            "es_asistencia_adicional": False,
            "practica_codigo": "43330102",
            "practica_descripcion": "HOSPITAL DE DIA",
            "importe": Decimal("12071.46"),
            "autorizacion": "5919203",
        },
    ]

    matrix = _build_export_matrix(
        "swiss_medical",
        registros,
        periodo_label="Septiembre 2026",
        subtipo="discapacidad",
    )

    # In discapacidad: only CUD=SI (Costa Miguel rows)
    assert len(matrix) == 4  # Title + Header + 2 data rows
    assert matrix[0][0][0] == "PRESTACIONES CAU 2026"
    assert matrix[1][0][0] == "FECHA"
    assert matrix[1][9][0] == "VALOR"

    # Row 1 (Costa Miguel first date): value is numeric
    row1_valor = matrix[2][9]
    assert row1_valor[0] == 631882.70
    assert row1_valor[1] == "num"

    # Row 2 (Costa Miguel additional attendance): value is '*'
    row2_valor = matrix[3][9]
    assert row2_valor[0] == "*"
    assert row2_valor[1] == "str"


def test_build_export_matrix_sin_discapacidad():
    registros = [
        {
            "id": 1,
            "financiador": "swiss_medical",
            "fecha_realizacion": "2026-09-11",
            "paciente_nombre": "SANCHEZ OSVALDO",
            "nro_afiliado": "7016575",
            "iva": "ADHERENTE",
            "cud": "NO",
            "cantidad": 1,
            "es_asistencia_adicional": False,
            "practica_codigo": "43330102",
            "practica_descripcion": "HOSPITAL DE DIA JORNADA SIMPLE",
            "importe": Decimal("12071.46"),
            "autorizacion": "5919203",
        },
        {
            "id": 2,
            "financiador": "swiss_medical",
            "fecha_realizacion": "2026-09-23",
            "paciente_nombre": "CAHUANA SOTO",
            "nro_afiliado": "1379697040018",
            "iva": "OBLIGATORIO",
            "cud": "NO",
            "cantidad": 1,
            "es_asistencia_adicional": False,
            "practica_codigo": "42011200",
            "practica_descripcion": "TRAUMATOLOGIA",
            "importe": Decimal("8720.09"),
            "autorizacion": "531270159",
        },
        {
            "id": 3,
            "financiador": "swiss_medical",
            "fecha_realizacion": "2026-09-07",
            "paciente_nombre": "CASSATARO JULIANA",
            "nro_afiliado": "1378717011009",
            "iva": "OBLIGATORIO",
            "cud": "NO",
            "cantidad": 1,
            "es_asistencia_adicional": False,
            "practica_codigo": "25010230",
            "practica_descripcion": "TECNICAS DE CORRECCION POSTURAL",
            "importe": Decimal("9899.46"),
            "autorizacion": "527885893",
        },
    ]

    matrix = _build_export_matrix(
        "swiss_medical",
        registros,
        periodo_label="Septiembre 2026",
        subtipo="sin_discapacidad",
    )

    # Should contain:
    # Block 1: PRESTACIONES CAU (Sanchez)
    # Blank row
    # Block 2: CONSULTAS (Cahuana)
    # Blank row
    # Block 3: PARCTICAS (Cassataro)
    titles = [row[0][0] for row in matrix if len(row) > 0 and row[0][1] == "title"]
    assert "PRESTACIONES CAU 2026" in titles
    assert "CONSULTAS " in titles
    assert "PARCTICAS" in titles

    # All rows have 10 cells
    for row in matrix:
        assert len(row) == 10

    # Generate XLSX bytes
    xlsx_buf = _generate_xlsx_bytes(matrix, sheet_name="Swiss Sept 2026")
    assert isinstance(xlsx_buf, io.BytesIO)
    with zipfile.ZipFile(xlsx_buf, "r") as zf:
        assert "xl/worksheets/sheet1.xml" in zf.namelist()
        sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "SANCHEZ OSVALDO" in sheet_xml
        assert "CAHUANA SOTO" in sheet_xml
        assert "CASSATARO JULIANA" in sheet_xml
