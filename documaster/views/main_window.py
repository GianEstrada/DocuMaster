from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QDate, QSettings
from PyQt6.QtWidgets import (
    QDateEdit, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from documaster.models.orden_salida import ClausulaSchema, OrdenSalidaSchema
from documaster.services.document_service import DocumentService
from documaster.services.persistence_service import PersistenceService


DEFAULT_CLAUSES = [
    ("OBJETO", "El ARRENDADOR otorga en arrendamiento al ARRENDATARIO los bienes descritos en el desglose superior por el periodo especificado."),
    ("PRECIO Y PAGO", "El ARRENDATARIO se obliga a pagar la cantidad total descrita en la presente orden/factura, incluyendo el 16% de IVA correspondiente."),
    ("RESPONSABILIDAD", "El ARRENDATARIO será responsable del buen uso de los Baños y Casetas portátiles. Cualquier daño por negligencia será facturado adicionalmente."),
]


class ClauseEditor(QWidget):
    def __init__(self, title: str, content: str, remove_callback):
        super().__init__()
        self.title_edit = QLineEdit(title)
        self.content_edit = QTextEdit(content)
        remove = QPushButton("Eliminar")
        remove.clicked.connect(lambda: remove_callback(self))
        layout = QFormLayout(self)
        layout.addRow("Título:", self.title_edit)
        layout.addRow("Contenido:", self.content_edit)
        layout.addRow(remove)

    def value(self, number: int) -> ClausulaSchema:
        return ClausulaSchema(
            numero=number,
            titulo=self.title_edit.text(),
            contenido=self.content_edit.toPlainText(),
        )


class MainWindow(QMainWindow):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.document_service = DocumentService(root)
        self.persistence = PersistenceService(root)
        self.settings = QSettings("DocuMaster", "DocuMaster")
        self.clause_editors: list[ClauseEditor] = []
        self.setWindowTitle("DocuMaster")
        self.resize(1000, 760)
        self.build_ui()
        self.recalculate()

    def text_field(self, value: str = "") -> QLineEdit:
        field = QLineEdit(value)
        return field

    def build_ui(self):
        tabs = QTabWidget()
        tabs.addTab(self.general_tab(), "Datos generales")
        tabs.addTab(self.landlord_tab(), "Arrendador")
        tabs.addTab(self.client_tab(), "Arrendatario")
        tabs.addTab(self.rental_tab(), "Arrendamiento y costos")
        tabs.addTab(self.clauses_tab(), "Cláusulas editables")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(tabs)
        self.preview_button = QPushButton("Validar y generar contrato PDF")
        self.preview_button.clicked.connect(self.generate)
        layout.addWidget(self.preview_button)
        self.setCentralWidget(container)

    def landlord_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.landlord_name = self.text_field(
            self.settings.value("landlord/name", "NOMBRE DEL ARRENDADOR", type=str)
        )
        self.landlord_rfc = self.text_field(
            self.settings.value("landlord/rfc", "XAXX010101000", type=str)
        )
        self.landlord_name.editingFinished.connect(self.save_landlord_settings)
        self.landlord_rfc.editingFinished.connect(self.save_landlord_settings)
        form.addRow("Razón social / nombre:", self.landlord_name)
        form.addRow("RFC:", self.landlord_rfc)
        note = QLabel("Estos dos datos se guardan localmente para la próxima apertura.")
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    def save_landlord_settings(self):
        self.settings.setValue("landlord/name", self.landlord_name.text().strip())
        self.settings.setValue("landlord/rfc", self.landlord_rfc.text().strip().upper())
        self.settings.sync()

    def general_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.folio = self.text_field("05-001")
        self.fecha_emision = QDateEdit(QDate.currentDate())
        self.fecha_emision.setCalendarPopup(True)
        self.lugar = self.text_field("Allende, Nuevo León")
        form.addRow("Folio:", self.folio)
        form.addRow("Fecha de emisión:", self.fecha_emision)
        form.addRow("Lugar:", self.lugar)
        return tab

    def client_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.client_name = self.text_field("RAZÓN SOCIAL DEL CLIENTE")
        self.representative = self.text_field("NOMBRE DEL REPRESENTANTE")
        self.address = self.text_field("DOMICILIO FISCAL")
        self.client_rfc = self.text_field("XAXX010101000")
        form.addRow("Cliente / razón social:", self.client_name)
        form.addRow("Representante:", self.representative)
        form.addRow("Domicilio fiscal:", self.address)
        form.addRow("RFC cliente:", self.client_rfc)
        return tab

    def rental_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.product = self.text_field("Arrendamiento de Baño Portátil Estándar con Mantenimiento")
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 100000)
        self.quantity.setValue(2)
        self.unit_price = QDoubleSpinBox()
        self.unit_price.setRange(0.01, 100000000)
        self.unit_price.setDecimals(2)
        self.unit_price.setValue(1500)
        self.months = QDoubleSpinBox()
        self.months.setRange(0.01, 120)
        self.months.setDecimals(2)
        self.months.setValue(3)
        self.start_date = QDateEdit(QDate(2026, 9, 10))
        self.end_date = QDateEdit(QDate(2026, 12, 9))
        self.start_date.setCalendarPopup(True)
        self.end_date.setCalendarPopup(True)
        self.subtotal_label = QLabel()
        self.iva_label = QLabel()
        self.total_label = QLabel()
        form.addRow("Producto / descripción:", self.product)
        form.addRow("Cantidad:", self.quantity)
        form.addRow("Precio unitario mensual:", self.unit_price)
        form.addRow("Meses:", self.months)
        form.addRow("Fecha inicial:", self.start_date)
        form.addRow("Fecha final:", self.end_date)
        form.addRow("Subtotal:", self.subtotal_label)
        form.addRow("IVA (16% NL):", self.iva_label)
        form.addRow("TOTAL A PAGAR:", self.total_label)
        for widget in (self.quantity, self.unit_price, self.months):
            widget.valueChanged.connect(self.recalculate)
        return tab

    def clauses_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        self.clauses_layout = QVBoxLayout()
        scroll_content = QWidget()
        scroll_content.setLayout(self.clauses_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        outer.addWidget(scroll)
        add = QPushButton("Agregar cláusula")
        add.clicked.connect(lambda: self.add_clause("NUEVA CLÁUSULA", "Escriba aquí el contenido de la cláusula."))
        outer.addWidget(add)
        for title, content in DEFAULT_CLAUSES:
            self.add_clause(title, content)
        return tab

    def add_clause(self, title: str, content: str):
        editor = ClauseEditor(title, content, self.remove_clause)
        self.clause_editors.append(editor)
        self.clauses_layout.addWidget(editor)

    def remove_clause(self, editor: ClauseEditor):
        if len(self.clause_editors) == 1:
            QMessageBox.warning(self, "Cláusulas", "Debe conservar al menos una cláusula.")
            return
        self.clause_editors.remove(editor)
        editor.deleteLater()

    def recalculate(self):
        subtotal = Decimal(self.quantity.value()) * Decimal(str(self.unit_price.value())) * Decimal(str(self.months.value()))
        iva = subtotal * Decimal("0.16")
        self.subtotal_label.setText(f"${subtotal:,.2f} MXN")
        self.iva_label.setText(f"${iva:,.2f} MXN")
        self.total_label.setText(f"${subtotal + iva:,.2f} MXN")

    def build_order(self) -> OrdenSalidaSchema:
        clauses = [editor.value(number) for number, editor in enumerate(self.clause_editors, start=1)]
        return OrdenSalidaSchema(
            folio=self.folio.text(),
            fecha_emision=self.qdate_to_date(self.fecha_emision),
            lugar=self.lugar.text(),
            arrendador_nombre=self.landlord_name.text(),
            arrendador_rfc=self.landlord_rfc.text(),
            cliente_razon_social=self.client_name.text(),
            representante=self.representative.text(),
            domicilio_fiscal=self.address.text(),
            cliente_rfc=self.client_rfc.text(),
            producto=self.product.text(),
            cantidad=self.quantity.value(),
            precio_unitario=Decimal(str(self.unit_price.value())),
            tiempo_arrendamiento=Decimal(str(self.months.value())),
            fecha_inicio=self.qdate_to_date(self.start_date),
            fecha_fin=self.qdate_to_date(self.end_date),
            clausulas=clauses,
        )

    @staticmethod
    def qdate_to_date(widget: QDateEdit) -> date:
        value = widget.date()
        return date(value.year(), value.month(), value.day())

    def generate(self):
        try:
            self.save_landlord_settings()
            order = self.build_order()
            html = self.document_service.render(order)
            pdf_path = self.root / "storage" / "expedientes" / str(order.fecha_emision.year) / order.folio / "contrato_factura.pdf"
            engine = self.document_service.create_pdf(html, pdf_path)
            self.persistence.save(order, html, pdf_path)
            QMessageBox.information(self, "Documento generado", f"PDF creado con {engine}:\n{pdf_path}")
        except Exception as error:
            QMessageBox.critical(self, "No se pudo generar", str(error))
