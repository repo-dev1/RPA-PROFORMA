"""
Main application window for the RPA Proforma Comparativo tool.
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from gui.styles import COLORS, DIMENSIONS
from gui.pdf_loader import PDFLoaderPanel
from gui.data_table import EditableTable
from core.pdf_parser import parse_multiple_pdfs
from core.comparativo_gen import generate_comparativo
from core.orden_gen import generate_orden_compra


class ProformaApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("ACONIC - Cuadro Comparativo de Proformas")
        self.geometry(f"{DIMENSIONS['window_width']}x{DIMENSIONS['window_height']}")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.suppliers = ["MASTERTEC", "CONICO", "COMTECH"]
        self.parsed_data = None

        self._setup_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _setup_ui(self):
        # ── Header ───────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["primary_dark"], height=60, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="✈  ACONIC S.A  —  Cuadro Comparativo de Proformas",
                     font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                     text_color="white").pack(side="left", padx=20)

        # ── Tabview ──────────────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(self, fg_color=COLORS["bg_dark"],
                                       segmented_button_fg_color=COLORS["primary"],
                                       segmented_button_selected_color=COLORS["accent"],
                                       segmented_button_unselected_color=COLORS["surface"])
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_load = self.tabview.add("📂 Cargar Proformas")
        self.tab_compare = self.tabview.add("📊 Cuadro Comparativo")
        self.tab_order = self.tabview.add("🛒 Orden de Compra")

        self._setup_load_tab()
        self._setup_compare_tab()
        self._setup_order_tab()

    # ── TAB 1: Cargar Proformas ──────────────────────────────────────────
    def _setup_load_tab(self):
        tab = self.tab_load

        # PDF Loader
        self.pdf_loader = PDFLoaderPanel(tab, suppliers=self.suppliers, on_suppliers_changed=self._on_loader_suppliers_changed)
        self.pdf_loader.pack(fill="x", padx=10, pady=10)

        # Extract button
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.btn_extract = ctk.CTkButton(btn_frame, text="⚡ Extraer Datos de PDFs",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            height=45, corner_radius=10, command=self._extract_data)
        self.btn_extract.pack(pady=5)

        # Log area
        self.log_frame = ctk.CTkFrame(tab, fg_color=COLORS["surface"], corner_radius=10)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkLabel(self.log_frame, text="📝 Log de Extracción",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(10, 5))

        self.log_text = ctk.CTkTextbox(self.log_frame, fg_color=COLORS["bg_card"],
                                        text_color=COLORS["text_primary"],
                                        font=ctk.CTkFont(family="Consolas", size=10),
                                        corner_radius=8, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.insert("end", "Esperando carga de proformas...\n")
        self.log_text.configure(state="disabled")

    def _on_loader_suppliers_changed(self, new_suppliers):
        self._on_table_suppliers_changed(new_suppliers)
        if hasattr(self, 'data_table'):
            self.data_table.update_suppliers(new_suppliers)

    # ── TAB 2: Cuadro Comparativo ────────────────────────────────────────
    def _setup_compare_tab(self):
        tab = self.tab_compare

        # Top bar: Title input + buttons
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Título:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=(0, 8))

        self.title_entry = ctk.CTkEntry(top, placeholder_text="Ej: ACUMULADORES/ÚTILES IT",
                                         width=350, height=36, corner_radius=8,
                                         fg_color=COLORS["bg_input"],
                                         text_color=COLORS["text_primary"])
        self.title_entry.pack(side="left", padx=(0, 15))

        # Action buttons
        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(side="right")

        ctk.CTkButton(btns, text="➕ Agregar Fila", width=130, height=34,
                      fg_color=COLORS["success"], hover_color="#059669",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._add_row).pack(side="left", padx=3)

        ctk.CTkButton(btns, text="🗑 Eliminar Fila", width=130, height=34,
                      fg_color=COLORS["error"], hover_color="#DC2626",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._delete_row).pack(side="left", padx=3)

        ctk.CTkButton(btns, text="🧹 Limpiar", width=100, height=34,
                      fg_color=COLORS["surface"], hover_color=COLORS["surface_hover"],
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._clear_table).pack(side="left", padx=3)

        # ── Generate buttons (pack BOTTOM FIRST so they're always visible) ──
        gen_frame = ctk.CTkFrame(tab, fg_color=COLORS["surface"], corner_radius=10)
        gen_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

        ctk.CTkButton(gen_frame, text="📊 Generar Cuadro Comparativo",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      height=48, corner_radius=10, width=320,
                      command=self._generate_comparativo).pack(side="left", padx=(15, 8), pady=10)

        ctk.CTkButton(gen_frame, text="📂 Abrir Archivo",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                      height=48, corner_radius=10, width=160,
                      command=lambda: self._open_file("comparativo")).pack(side="left", padx=5, pady=10)

        self.compare_status = ctk.CTkLabel(gen_frame, text="",
                                            font=ctk.CTkFont(size=11),
                                            text_color=COLORS["text_secondary"])
        self.compare_status.pack(side="left", padx=15)

        # ── Data table (fills remaining space) ──
        self.data_table = EditableTable(tab, suppliers=self.suppliers, on_suppliers_changed=self._on_table_suppliers_changed)
        self.data_table.pack(fill="both", expand=True, padx=10, pady=5)

    def _on_table_suppliers_changed(self, new_suppliers):
        self.suppliers = new_suppliers
        if hasattr(self, 'oc_supplier_dropdown'):
            self.oc_supplier_dropdown.configure(values=self.suppliers)
            if self.oc_supplier_var.get() not in self.suppliers:
                self.oc_supplier_var.set(self.suppliers[0])

    # ── TAB 3: Orden de Compra ───────────────────────────────────────────
    def _setup_order_tab(self):
        tab = self.tab_order

        # Fields
        fields_frame = ctk.CTkFrame(tab, fg_color=COLORS["surface"], corner_radius=10)
        fields_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(fields_frame, text="🛒 Datos de la Orden de Compra",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS["text_primary"]).grid(row=0, column=0, columnspan=4,
                                                              padx=15, pady=(15, 10), sticky="w")

        labels = ["Proveedor:", "Solicitante:", "Área:", "Tipo de Compra:", "Autoriza:"]
        self.oc_entries = {}

        defaults = {
            "Solicitante:": "David Garcia",
            "Área:": "Informatica",
            "Tipo de Compra:": "Equipos de computo",
            "Autoriza:": "Ivette Medina",
        }

        for i, label in enumerate(labels):
            r, c = divmod(i, 2)
            ctk.CTkLabel(fields_frame, text=label,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=COLORS["text_secondary"]).grid(
                row=r + 1, column=c * 2, padx=(15, 5), pady=5, sticky="e")

            if label == "Proveedor:":
                self.oc_supplier_var = ctk.StringVar(value=self.suppliers[0])
                self.oc_supplier_dropdown = ctk.CTkOptionMenu(fields_frame, values=self.suppliers,
                                            variable=self.oc_supplier_var,
                                            width=200, height=34,
                                            fg_color=COLORS["bg_input"],
                                            command=self._on_oc_supplier_changed)
                widget = self.oc_supplier_dropdown
            else:
                widget = ctk.CTkEntry(fields_frame, width=200, height=34,
                                       fg_color=COLORS["bg_input"],
                                       text_color=COLORS["text_primary"],
                                       corner_radius=8)
                if label in defaults:
                    widget.insert(0, defaults[label])
                self.oc_entries[label] = widget

            widget.grid(row=r + 1, column=c * 2 + 1, padx=(0, 15), pady=5, sticky="w")

        # ── Generate buttons (pack BOTTOM FIRST so they're always visible) ──
        gen_frame = ctk.CTkFrame(tab, fg_color=COLORS["surface"], corner_radius=10)
        gen_frame.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

        ctk.CTkButton(gen_frame, text="🛒 Generar Orden de Compra",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#7C3AED", hover_color="#6D28D9",
                      height=48, corner_radius=10, width=280,
                      command=self._generate_orden).pack(side="left", padx=(15, 8), pady=10)

        ctk.CTkButton(gen_frame, text="📂 Abrir Archivo",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                      height=48, corner_radius=10, width=160,
                      command=lambda: self._open_file("orden")).pack(side="left", padx=5, pady=10)

        self.order_status = ctk.CTkLabel(gen_frame, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color=COLORS["text_secondary"])
        self.order_status.pack(side="left", padx=15)

        # OC Items table
        self.oc_table = EditableTable(tab, suppliers=[])
        # Reconfigure for OC layout (just Descripcion, Cantidad, Precio)
        self._setup_oc_table(tab)

    def _setup_oc_table(self, tab):
        """Create a simpler table for OC items."""
        import tkinter as tk
        from tkinter import ttk

        table_frame = tk.Frame(tab, bg=COLORS["bg_dark"])
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        style = ttk.Style()
        style.configure("OC.Treeview", background=COLORS["table_row_even"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["table_row_even"],
                         font=("Segoe UI", 10), rowheight=32)
        style.configure("OC.Treeview.Heading", background=COLORS["table_header"],
                         foreground="white", font=("Segoe UI", 10, "bold"))

        cols = ("num", "desc", "cant", "precio")
        self.oc_tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                     style="OC.Treeview", selectmode="browse")

        self.oc_tree.heading("num", text="#")
        self.oc_tree.heading("desc", text="Descripción")
        self.oc_tree.heading("cant", text="Cantidad")
        self.oc_tree.heading("precio", text="Precio Unitario")

        self.oc_tree.column("num", width=40, anchor="center")
        self.oc_tree.column("desc", width=450, anchor="w")
        self.oc_tree.column("cant", width=80, anchor="center")
        self.oc_tree.column("precio", width=120, anchor="center")

        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.oc_tree.yview)
        self.oc_tree.configure(yscrollcommand=v_scroll.set)

        self.oc_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

    # ── Actions ──────────────────────────────────────────────────────────
    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _extract_data(self):
        """Extract data from loaded PDFs."""
        files = self.pdf_loader.get_all_files()  # {slot_name: filepath}
        if not files:
            messagebox.showwarning("Sin archivos", "Por favor carga al menos un PDF de proforma.")
            return

        self._log(f"\n{'='*50}")
        self._log(f"Iniciando extracción de {len(files)} proforma(s)...")

        # Build reverse mapping: filepath -> slot_name (user-defined supplier name)
        filepath_to_slot = {fp: name for name, fp in files.items()}
        filepaths = list(files.values())

        try:
            result = parse_multiple_pdfs(filepaths)
            self.parsed_data = result

            # Override detected supplier names with the slot names the user defined
            for p in result['proformas']:
                full_path = os.path.join(os.getcwd(), p['archivo']) if not os.path.isabs(p['archivo']) else p['archivo']
                # Match by basename since parse_multiple_pdfs stores basename
                for fp, slot_name in filepath_to_slot.items():
                    if os.path.basename(fp) == p['archivo']:
                        p['proveedor'] = slot_name
                        break

            # Also override supplier names in all_items
            for item in result['all_items']:
                for p in result['proformas']:
                    # Match items to their proforma by checking if the item came from this proforma
                    for pi in p['items']:
                        if (pi['descripcion'] == item['descripcion'] and
                            pi['precio_unitario'] == item['precio_unitario']):
                            item['proveedor'] = p['proveedor']
                            break

            # Use slot names as the supplier columns (preserving user-defined order)
            self.suppliers = list(files.keys())
            while len(self.suppliers) < 3:
                for s in ["MASTERTEC", "CONICO", "COMTECH"]:
                    if s not in self.suppliers:
                        self.suppliers.append(s)
                        break
            self.data_table.update_suppliers(self.suppliers[:3])

            # Log results
            for p in result['proformas']:
                self._log(f"\n✅ {p['proveedor']} ({p['archivo']})")
                self._log(f"   Proforma #: {p['num_proforma']} | Fecha: {p['fecha']}")
                for item in p['items']:
                    self._log(f"   • {item['descripcion'][:60]}")
                    self._log(f"     Cant: {item['cantidad']} | P.U: C${item['precio_unitario']:,.2f}")

            # Build table data — group similar items across suppliers
            table_items = []

            def _normalize(desc: str) -> set:
                """Extract meaningful keywords from a description for matching."""
                import re as _re
                text = desc.upper().strip()
                # Remove common noise: model suffixes like #ABC-123, parenthesized text
                text = _re.sub(r'#\S+', '', text)
                text = _re.sub(r'\([^)]*\)', '', text)
                # Split on spaces, slashes, commas
                tokens = _re.split(r'[\s/,\-]+', text)
                # Keep tokens that are meaningful (length > 1, not pure punctuation)
                stop_words = {'DE', 'A', 'Y', 'EL', 'LA', 'LOS', 'LAS', 'EN', 'CON',
                              'P', 'PARA', 'UN', 'UNA', 'DEL', 'AL', 'POR', 'SU',
                              'C$', 'CS', 'UND', 'UNIDAD'}
                keywords = set()
                for t in tokens:
                    t = t.strip('.,;:!?()[]{}')
                    if len(t) > 1 and t not in stop_words:
                        keywords.add(t)
                return keywords

            def _similarity(kw1: set, kw2: set) -> float:
                """Jaccard-like similarity between two keyword sets."""
                if not kw1 or not kw2:
                    return 0.0
                intersection = kw1 & kw2
                union = kw1 | kw2
                return len(intersection) / len(union)

            SIMILARITY_THRESHOLD = 0.45  # 45% keyword overlap to be considered same product

            for item in result['all_items']:
                item_kw = _normalize(item['descripcion'])

                # Find best matching existing row
                best_match = None
                best_score = 0.0
                for t in table_items:
                    # Don't match if this supplier already has a price in that row
                    if item['proveedor'] in t['precios']:
                        continue
                    score = _similarity(item_kw, t['_keywords'])
                    if score > best_score:
                        best_score = score
                        best_match = t

                if best_match and best_score >= SIMILARITY_THRESHOLD:
                    # Merge into existing row
                    best_match['precios'][item['proveedor']] = item['precio_unitario']
                    best_match['cantidad'] = max(best_match['cantidad'], item['cantidad'])
                    # Keep the longest description as the canonical name
                    if len(item['descripcion']) > len(best_match['descripcion']):
                        best_match['descripcion'] = item['descripcion']
                else:
                    table_items.append({
                        'descripcion': item['descripcion'],
                        'precios': {item['proveedor']: item['precio_unitario']},
                        'cantidad': item['cantidad'],
                        '_keywords': item_kw,
                    })

            # Clean up internal keys before passing to table
            for t in table_items:
                t.pop('_keywords', None)

            self.data_table.load_data(table_items)
            self._log(f"\n📊 {len(table_items)} artículo(s) cargados en la tabla.")
            self._log("Cambia a la pestaña '📊 Cuadro Comparativo' para revisar y generar.")

            # Switch to compare tab
            self.tabview.set("📊 Cuadro Comparativo")

        except Exception as e:
            self._log(f"\n❌ Error: {e}")
            import traceback
            self._log(traceback.format_exc())
            messagebox.showerror("Error", f"Error al extraer datos:\n{e}")

    def _add_row(self):
        self.data_table.add_row()

    def _delete_row(self):
        self.data_table.delete_selected_row()

    def _clear_table(self):
        if messagebox.askyesno("Confirmar", "¿Limpiar toda la tabla?"):
            self.data_table.clear_all()

    def _generate_comparativo(self):
        """Generate the comparative Excel file."""
        items = self.data_table.get_data()
        if not items:
            messagebox.showwarning("Sin datos", "La tabla está vacía. Agrega artículos primero.")
            return

        title = self.title_entry.get().strip() or "PRODUCTOS VARIOS"
        logo_path = os.path.join(os.getcwd(), "templates", "logo_aconic.png")
        out_dir = os.environ.get('PROFORMA_OUTPUT_DIR', os.path.join(os.getcwd(), 'output'))
        output_path = os.path.join(out_dir, "Cuadro_Comparativo.xlsx")

        try:
            result_path = generate_comparativo(
                items_data=items,
                suppliers=self.suppliers[:3],
                title=title,
                output_path=output_path,
                logo_path=logo_path if os.path.exists(logo_path) else None,
            )
            self.last_comparativo_path = result_path
            self.compare_status.configure(
                text=f"✅ Generado: {os.path.basename(result_path)}",
                text_color=COLORS["success"])
            messagebox.showinfo("Éxito", f"Cuadro comparativo generado:\n{result_path}")

            # Also populate OC table
            self._populate_oc_table()

        except Exception as e:
            self.compare_status.configure(text=f"❌ Error: {e}", text_color=COLORS["error"])
            messagebox.showerror("Error", f"Error al generar:\n{e}")
            import traceback
            traceback.print_exc()

    def _populate_oc_table(self):
        """Populate the OC table with data from the selected supplier."""
        self.oc_tree.delete(*self.oc_tree.get_children())
        items = self.data_table.get_data()
        supplier = self.oc_supplier_var.get()

        idx = 0
        for item in items:
            price = item['precios'].get(supplier, 0)
            if price > 0:
                idx += 1
                self.oc_tree.insert("", "end", values=(
                    idx,
                    item['descripcion'],
                    item['cantidad'],
                    f"{price:,.2f}"
                ))

    def _on_oc_supplier_changed(self, value):
        self._populate_oc_table()

    def _generate_orden(self):
        """Generate the purchase order Excel file."""
        supplier = self.oc_supplier_var.get()
        items_data = self.data_table.get_data()

        # Filter items for selected supplier
        oc_items = []
        for item in items_data:
            price = item['precios'].get(supplier, 0)
            if price > 0:
                oc_items.append({
                    'descripcion': item['descripcion'],
                    'cantidad': item['cantidad'],
                    'precio_unitario': price,
                })

        if not oc_items:
            messagebox.showwarning("Sin datos",
                                    f"No hay artículos con precios de {supplier}.")
            return

        solicitante = self.oc_entries.get("Solicitante:", None)
        area = self.oc_entries.get("Área:", None)
        tipo = self.oc_entries.get("Tipo de Compra:", None)
        autoriza = self.oc_entries.get("Autoriza:", None)

        logo_path = os.path.join(os.getcwd(), "templates", "logo_aconic.png")
        out_dir = os.environ.get('PROFORMA_OUTPUT_DIR', os.path.join(os.getcwd(), 'output'))
        output_path = os.path.join(out_dir, f"Orden_Compra_{supplier}.xlsx")

        try:
            result_path = generate_orden_compra(
                items_data=oc_items,
                supplier=supplier,
                solicitante=solicitante.get() if solicitante else "David Garcia",
                area=area.get() if area else "Informatica",
                tipo_compra=tipo.get() if tipo else "Equipos de computo",
                autoriza=autoriza.get() if autoriza else "Ivette Medina",
                output_path=output_path,
                logo_path=logo_path if os.path.exists(logo_path) else None,
            )
            self.last_orden_path = result_path
            self.order_status.configure(
                text=f"✅ Generado: {os.path.basename(result_path)}",
                text_color=COLORS["success"])
            messagebox.showinfo("Éxito", f"Orden de compra generada:\n{result_path}")

        except Exception as e:
            self.order_status.configure(text=f"❌ Error: {e}", text_color=COLORS["error"])
            messagebox.showerror("Error", f"Error al generar:\n{e}")

    def _open_file(self, file_type: str):
        """Open the generated file."""
        path = None
        if file_type == "comparativo":
            path = getattr(self, 'last_comparativo_path', None)
        elif file_type == "orden":
            path = getattr(self, 'last_orden_path', None)

        if path and os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showinfo("Sin archivo", "Primero genera el archivo.")
