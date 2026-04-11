"""
Input Bar — Multi-line text input for user queries.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QPushButton, QFrame, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from odus.ui.theme import (
    Colors, Fonts, FontSizes, Layout,
)

class InputBar(QFrame):
    """
    Unified input pill at the bottom of the window.
    """

    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputBar")
        self.setFixedHeight(Layout.INPUT_HEIGHT + 20)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(0)

        # Pill container
        pill = QFrame()
        pill.setObjectName("InputPill")
        pill.setFixedHeight(Layout.INPUT_HEIGHT)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(16, 0, 8, 0)
        pill_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Odus something...")
        self.input_field.setFrame(False)
        self.input_field.setObjectName("InputField")
        self.input_field.returnPressed.connect(self._on_submit)

        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(34, 34)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.clicked.connect(self._on_submit)

        pill_layout.addWidget(self.input_field)
        pill_layout.addWidget(self.send_btn)

        layout.addWidget(pill)

        self._apply_style()

    def _on_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.submitted.emit(text)
            self.input_field.clear()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#InputBar {{
                background-color: {Colors.BG_PRIMARY};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
            QFrame#InputPill {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 25px;
                border: 1px solid {Colors.BORDER};
            }}
            QLineEdit#InputField {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.MD}px;
                font-family: {Fonts.BODY};
                border: none;
            }}
            QPushButton#SendBtn {{
                background-color: {Colors.ACCENT};
                color: #000000;
                border-radius: 17px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton#SendBtn:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
        """)
