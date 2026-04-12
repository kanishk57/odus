import os
import sys
from PyQt6.QtWidgets import QApplication
from odus.ui_v2.sidebar_window import SidebarWindowV2
from odus.ui_v2.chat_window import ChatWindowV2

def main():
    app = QApplication(sys.argv)
    
    ui_type = os.getenv("ODUS_UI_TYPE", "window")
    
    if ui_type == "sidebar":
        window = SidebarWindowV2()
    else:
        window = ChatWindowV2()
        
    window.show()
    
    # Add some dummy messages
    window.chat_history.add_message("Hello! I am Odus, your shadow console companion.", is_ai=True)
    window.chat_history.add_message("This is a demonstration of the new sidebar UI designed with Editorial Obsidian system.", is_ai=True)
    window.chat_history.add_message("It features full text wrapping and a professional, minimal look.", is_ai=True)
    window.chat_history.add_message("Note: You can right-click the mascot trigger to see the context menu or use the power button in the header to quit.", is_ai=True)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
