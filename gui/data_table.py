"""
Editable data table widget for the comparative quote application.
Uses tkinter Treeview with in-place editing support.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from gui.styles import COLORS, FONTS


class EditableTable(tk.Frame):
    """
    A Treeview-based editable table for displaying and editing proforma data.
    Supports in-place cell editing via double-click.
    """

    def __init__(self, parent, suppliers=None, on_data_changed=None, on_suppliers_changed=None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)

        self.suppliers = suppliers or ["MASTERTEC", "CONICO", "COMTECH"]
        self.on_data_changed = on_data_changed
        self.on_suppliers_changed = on_suppliers_changed
        self._edit_widget = None
        self._editing_item = None
        self._editing_column = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the table UI."""
        # Define columns
        self.columns = ["#", "Descripción"] + self.suppliers + ["Cantidad"]
        col_ids = [f"col{i}" for i in range(len(self.columns))]

        # Style the Treeview
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Proforma.Treeview",
                         background=COLORS["table_row_even"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["table_row_even"],
                         borderwidth=0,
                         font=("Segoe UI", 10),
                         rowheight=35)

        style.configure("Proforma.Treeview.Heading",
                         background=COLORS["table_header"],
                         foreground="white",
                         font=("Segoe UI", 10, "bold"),
                         borderwidth=1,
                         relief="flat")

        style.map("Proforma.Treeview",
                   background=[("selected", COLORS["table_selected"])],
                   foreground=[("selected", "white")])

        style.map("Proforma.Treeview.Heading",
                   background=[("active", COLORS["primary_hover"])])

        # Create Treeview
        self.tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            style="Proforma.Treeview",
            selectmode="browse",
        )

        # Configure columns
        col_widths = {
            0: 40,    # #
            1: 350,   # Descripción
        }
        # Supplier columns
        for i in range(2, 2 + len(self.suppliers)):
            col_widths[i] = 120
        col_widths[len(self.columns) - 1] = 80  # Cantidad

        for i, (col_id, col_name) in enumerate(zip(col_ids, self.columns)):
            width = col_widths.get(i, 120)
            anchor = "w" if i == 1 else "center"
            self.tree.heading(col_id, text=col_name, anchor="center")
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=50)

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Bind double-click for editing
        self.tree.bind("<Double-1>", self._on_double_click)

        # Alternating row colors
        self.tree.tag_configure("even", background=COLORS["table_row_even"])
        self.tree.tag_configure("odd", background=COLORS["table_row_odd"])
        self.tree.tag_configure("empty_price", foreground=COLORS["text_muted"])

    def _on_double_click(self, event):
        """Handle double-click to start in-place editing."""
        region = self.tree.identify_region(event.x, event.y)
        
        if region == "heading":
            column = self.tree.identify_column(event.x)
            if not column:
                return
            col_idx = int(column.replace("#", "")) - 1
            
            # Check if it's a supplier column
            if 2 <= col_idx < 2 + len(self.suppliers):
                supplier_idx = col_idx - 2
                current_name = self.suppliers[supplier_idx]
                
                dialog = ctk.CTkInputDialog(text="Nuevo nombre para el proveedor:", title="Editar Proveedor")
                new_name = dialog.get_input()
                
                if new_name and new_name.strip() and new_name.strip() != current_name:
                    new_name = new_name.strip()
                    self.suppliers[supplier_idx] = new_name
                    
                    # Update column heading
                    col_ids = self.tree.cget("columns") if isinstance(self.tree.cget("columns"), (list, tuple)) else self.tree["columns"]
                    col_id = col_ids[col_idx]
                    self.tree.heading(col_id, text=new_name)
                    
                    # Notify parent
                    if self.on_suppliers_changed:
                        self.on_suppliers_changed(self.suppliers)
            return

        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if not item_id or not column:
            return

        col_idx = int(column.replace("#", "")) - 1

        # Don't allow editing the # column
        if col_idx == 0:
            return

        # Get cell bounds
        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return

        x, y, w, h = bbox

        # Get current value
        col_id = self.tree.cget("columns")[col_idx] if isinstance(self.tree.cget("columns"), (list, tuple)) else self.tree["columns"][col_idx]
        current_values = self.tree.item(item_id, "values")
        current_value = current_values[col_idx] if col_idx < len(current_values) else ""

        # Remove any existing edit widget
        self._cancel_edit()

        # Create entry widget
        self._editing_item = item_id
        self._editing_column = col_idx

        self._edit_widget = tk.Entry(
            self.tree,
            font=("Segoe UI", 10),
            bg=COLORS["bg_input"],
            fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            relief="solid",
            borderwidth=2,
            highlightthickness=0,
        )
        self._edit_widget.insert(0, str(current_value) if current_value and str(current_value) != "-" else "")
        self._edit_widget.select_range(0, tk.END)

        self._edit_widget.place(x=x, y=y, width=w, height=h)
        self._edit_widget.focus_set()

        self._edit_widget.bind("<Return>", self._commit_edit)
        self._edit_widget.bind("<Escape>", lambda e: self._cancel_edit())
        self._edit_widget.bind("<FocusOut>", self._commit_edit)
        self._edit_widget.bind("<Tab>", self._on_tab_edit)

    def _commit_edit(self, event=None):
        """Commit the current edit."""
        if not self._edit_widget or not self._editing_item:
            return

        new_value = self._edit_widget.get().strip()
        item_id = self._editing_item
        col_idx = self._editing_column

        # Get current values
        current_values = list(self.tree.item(item_id, "values"))

        # For price/quantity columns, try to parse as number
        if col_idx >= 2:  # Supplier columns or Cantidad
            try:
                if new_value == "" or new_value == "-":
                    new_value = "-"
                else:
                    new_value = str(float(new_value.replace(",", "")))
            except ValueError:
                pass  # Keep as string

        # Update the value
        if col_idx < len(current_values):
            current_values[col_idx] = new_value
        else:
            while len(current_values) <= col_idx:
                current_values.append("")
            current_values[col_idx] = new_value

        self.tree.item(item_id, values=current_values)
        self._cancel_edit()
        self._renumber_rows()

        if self.on_data_changed:
            self.on_data_changed()

    def _on_tab_edit(self, event):
        """Handle tab to move to next cell."""
        self._commit_edit()
        # Could implement moving to next cell here
        return "break"

    def _cancel_edit(self):
        """Cancel/destroy the current edit widget."""
        if self._edit_widget:
            self._edit_widget.destroy()
            self._edit_widget = None
            self._editing_item = None
            self._editing_column = None

    def load_data(self, items_data: list):
        """
        Load data into the table.
        
        Args:
            items_data: List of dicts with keys:
                - descripcion (str)
                - precios: dict {supplier_name: precio_unitario}
                - cantidad (int/float)
        """
        # Clear existing data
        self.tree.delete(*self.tree.get_children())

        for idx, item in enumerate(items_data):
            values = [idx + 1]  # Row number
            values.append(item.get('descripcion', ''))

            # Add price for each supplier
            precios = item.get('precios', {})
            for supplier in self.suppliers:
                price = precios.get(supplier, None)
                if price is not None and price > 0:
                    values.append(f"{price:.2f}")
                else:
                    values.append("-")

            values.append(item.get('cantidad', ''))

            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=values, tags=(tag,))

    def get_data(self) -> list:
        """
        Get all data from the table.
        
        Returns:
            List of dicts with keys: descripcion, precios, cantidad
        """
        items = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")

            desc = str(values[1]) if len(values) > 1 else ""
            precios = {}
            for i, supplier in enumerate(self.suppliers):
                col_idx = 2 + i
                if col_idx < len(values):
                    val = str(values[col_idx])
                    if val and val != "-" and val != "0" and val != "0.0":
                        try:
                            precios[supplier] = float(val.replace(",", ""))
                        except ValueError:
                            pass

            cant_idx = 2 + len(self.suppliers)
            cantidad = 0
            if cant_idx < len(values):
                try:
                    cantidad = int(float(str(values[cant_idx]).replace(",", "")))
                except (ValueError, TypeError):
                    cantidad = 0

            if desc:  # Only include rows with a description
                items.append({
                    'descripcion': desc,
                    'precios': precios,
                    'cantidad': cantidad,
                })

        return items

    def add_row(self, descripcion="", precios=None, cantidad=0):
        """Add a new row to the table."""
        precios = precios or {}
        idx = len(self.tree.get_children())

        values = [idx + 1, descripcion]
        for supplier in self.suppliers:
            price = precios.get(supplier, None)
            if price is not None and price > 0:
                values.append(f"{price:.2f}")
            else:
                values.append("-")
        values.append(cantidad if cantidad else "")

        tag = "even" if idx % 2 == 0 else "odd"
        self.tree.insert("", "end", values=values, tags=(tag,))

    def delete_selected_row(self):
        """Delete the currently selected row."""
        selected = self.tree.selection()
        if selected:
            self.tree.delete(selected[0])
            self._renumber_rows()
            if self.on_data_changed:
                self.on_data_changed()

    def clear_all(self):
        """Clear all rows from the table."""
        self.tree.delete(*self.tree.get_children())
        if self.on_data_changed:
            self.on_data_changed()

    def _renumber_rows(self):
        """Renumber all rows after a deletion."""
        for idx, item_id in enumerate(self.tree.get_children()):
            values = list(self.tree.item(item_id, "values"))
            values[0] = idx + 1
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.item(item_id, values=values, tags=(tag,))

    def update_suppliers(self, new_suppliers: list):
        """Update the supplier columns."""
        self.suppliers = new_suppliers[:3]
        # Update column headings
        col_ids = self.tree["columns"]
        for i, supplier in enumerate(self.suppliers):
            if 2 + i < len(col_ids):
                self.tree.heading(col_ids[2 + i], text=supplier)
