"""
Input Bar (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QPushButton, QFrame, QLineEdit, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from odus.ui_v2.theme import (
    Colors, Fonts, FontSizes, Radii, Spacing
)

class InputBarV2(QFrame):
    """
    Minimalist, professional input field for the sidebar.
    """

    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputBar")
        
        # Main layout for the input area
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        self._layout.setSpacing(0)

        # Input container (The Surface)
        self.input_container = QFrame()
        self.input_container.setObjectName("InputContainer")
        container_layout = QHBoxLayout(self.input_container)
        container_layout.setContentsMargins(12, 8, 12, 8)
        container_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Message...")
        self.input_field.setFrame(False)
        self.input_field.setObjectName("InputField")
        self.input_field.returnPressed.connect(self._on_submit)

        self.send_btn = QPushButton("→")
        self.send_btn.setFixedSize(28, 28)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.clicked.connect(self._on_submit)

        container_layout.addWidget(self.input_field)
        container_layout.addWidget(self.send_btn)

        self._layout.addWidget(self.input_container)

        self._apply_style()

    def _on_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.submitted.emit(text)
            self.input_field.clear()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#InputBar {{
                background-color: transparent;
            }}
            QFrame#InputContainer {{
                background-color: {Colors.BG_LEVEL_1};
                border-radius: {Radii.MD}px;
                border: 1px solid {Colors.BORDER_GHOST};
            }}
            QFrame#InputContainer:focus-within {{
                background-color: {Colors.BG_LEVEL_2};
                border: 1px solid {Colors.PRIMARY};
            }}
            QLineEdit#InputField {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.MD}px;
                font-family: '{Fonts.BODY}';
                border: none;
                selection-background-color: {Colors.PRIMARY};
            }}
            QPushButton#SendBtn {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton#SendBtn:hover {{
                color: {Colors.PRIMARY};
            }}
        """)
