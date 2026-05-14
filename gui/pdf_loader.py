"""
PDF Loader panel for loading proforma PDFs.
Provides visual file slots for each supplier with drag support.
"""

import os
import customtkinter as ctk
from tkinter import filedialog
from gui.styles import COLORS, FONTS, SUPPLIER_COLORS, DIMENSIONS


class PDFSlot(ctk.CTkFrame):
    """A single PDF loading slot for a supplier."""

    def __init__(self, parent, supplier_name: str, on_file_loaded=None, on_supplier_renamed=None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=DIMENSIONS["corner_radius"],
            border_width=2,
            border_color=COLORS["border"],
            **kwargs
        )

        self.supplier_name = supplier_name
        self.on_file_loaded = on_file_loaded
        self.on_supplier_renamed = on_supplier_renamed
        self.filepath = None
        self.supplier_color = SUPPLIER_COLORS.get(supplier_name, COLORS["accent"])

        self._setup_ui()

    def _setup_ui(self):
        """Build the slot UI."""
        # Supplier badge
        self.badge = ctk.CTkLabel(
            self,
            text=self.supplier_name,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="white",
            fg_color=self.supplier_color,
            corner_radius=6,
            height=28,
            width=120,
        )
        self.badge.pack(pady=(12, 6), padx=10)
        self.badge.bind("<Double-1>", self._edit_supplier_name)
        self.badge.configure(cursor="hand2")

        # Status icon
        self.status_label = ctk.CTkLabel(
            self,
            text="📄",
            font=ctk.CTkFont(size=32),
            text_color=COLORS["text_muted"],
        )
        self.status_label.pack(pady=(4, 2))

        # Filename label
        self.file_label = ctk.CTkLabel(
            self,
            text="Sin archivo",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLORS["text_muted"],
            wraplength=180,
        )
        self.file_label.pack(pady=(0, 4), padx=8)

        # Load button
        self.load_btn = ctk.CTkButton(
            self,
            text="📂 Cargar PDF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=self.supplier_color,
            hover_color=COLORS["primary_hover"],
            height=32,
            width=160,
            corner_radius=8,
            command=self._browse_file,
        )
        self.load_btn.pack(pady=(4, 12), padx=10)

    def _browse_file(self):
        """Open file dialog to select a PDF."""
        filepath = filedialog.askopenfilename(
            title=f"Seleccionar Proforma - {self.supplier_name}",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialdir=os.path.join(os.getcwd(), "input"),
        )
        if filepath:
            self.set_file(filepath)

    def set_file(self, filepath: str):
        """Set the loaded file path and update UI."""
        self.filepath = filepath
        filename = os.path.basename(filepath)

        self.file_label.configure(
            text=filename,
            text_color=COLORS["text_primary"],
        )
        self.status_label.configure(text="✅")
        self.configure(border_color=self.supplier_color)

        if self.on_file_loaded:
            self.on_file_loaded(self.supplier_name, filepath)

    def clear(self):
        """Clear the loaded file."""
        self.filepath = None
        self.file_label.configure(
            text="Sin archivo",
            text_color=COLORS["text_muted"],
        )
        self.status_label.configure(text="📄")
        self.configure(border_color=COLORS["border"])

    def get_filepath(self) -> str:
        """Return the loaded file path, or None."""
        return self.filepath

    def _edit_supplier_name(self, event):
        dialog = ctk.CTkInputDialog(text="Nuevo nombre para el proveedor:", title="Editar Proveedor")
        new_name = dialog.get_input()
        if new_name and new_name.strip() and new_name.strip() != self.supplier_name:
            old_name = self.supplier_name
            new_name = new_name.strip()
            self.supplier_name = new_name
            self.badge.configure(text=self.supplier_name)
            if self.on_supplier_renamed:
                self.on_supplier_renamed(old_name, new_name)


class PDFLoaderPanel(ctk.CTkFrame):
    """Panel containing PDF slots for all suppliers."""

    def __init__(self, parent, suppliers=None, on_files_changed=None, on_suppliers_changed=None, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs
        )

        self.suppliers = suppliers or ["MASTERTEC", "CONICO", "COMTECH"]
        self.on_files_changed = on_files_changed
        self.on_suppliers_changed = on_suppliers_changed
        self.slots = {}

        self._setup_ui()

    def _setup_ui(self):
        """Build the loader panel."""
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            title_frame,
            text="📋 Cargar Proformas",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Slots container
        slots_frame = ctk.CTkFrame(self, fg_color="transparent")
        slots_frame.pack(fill="x", pady=5)

        for i, supplier in enumerate(self.suppliers):
            slot = PDFSlot(
                slots_frame,
                supplier_name=supplier,
                on_file_loaded=self._on_file_loaded,
                on_supplier_renamed=self._on_supplier_renamed,
            )
            slot.pack(side="left", padx=8, fill="both", expand=True)
            self.slots[supplier] = slot

    def _on_supplier_renamed(self, old_name: str, new_name: str):
        if old_name in self.slots:
            slot = self.slots.pop(old_name)
            self.slots[new_name] = slot
            
        for i, s in enumerate(self.suppliers):
            if s == old_name:
                self.suppliers[i] = new_name
                
        if self.on_suppliers_changed:
            self.on_suppliers_changed(self.suppliers)

    def _on_file_loaded(self, supplier: str, filepath: str):
        """Called when a file is loaded in any slot."""
        if self.on_files_changed:
            self.on_files_changed(self.get_all_files())

    def get_all_files(self) -> dict:
        """Return dict of {supplier: filepath} for loaded files."""
        result = {}
        for supplier, slot in self.slots.items():
            fp = slot.get_filepath()
            if fp:
                result[supplier] = fp
        return result

    def clear_all(self):
        """Clear all slots."""
        for slot in self.slots.values():
            slot.clear()

    def update_suppliers(self, new_suppliers: list):
        """Update supplier names (does not rebuild slots, just labels)."""
        for i, supplier in enumerate(new_suppliers):
            if i < len(self.suppliers):
                old_name = self.suppliers[i]
                if old_name in self.slots:
                    slot = self.slots.pop(old_name)
                    slot.supplier_name = supplier
                    slot.badge.configure(text=supplier)
                    new_color = SUPPLIER_COLORS.get(supplier, COLORS["accent"])
                    slot.supplier_color = new_color
                    slot.badge.configure(fg_color=new_color)
                    slot.load_btn.configure(fg_color=new_color)
                    self.slots[supplier] = slot
        self.suppliers = new_suppliers[:3]
