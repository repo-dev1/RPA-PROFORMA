"""
PDF Parser for supplier proformas.
Extracts product data from MASTERTEC, CONICO, COMTECH, and SEVASA PDFs.
"""

import pdfplumber
import re
import os
import logging

# Suppress noisy warnings from pdfminer about fonts
logging.getLogger("pdfminer").setLevel(logging.ERROR)



class ProformaParser:
    """Parses PDF proformas from different suppliers and extracts product data."""

    # Known supplier identifiers (searched in the PDF text, case-insensitive)
    KNOWN_SUPPLIERS = ["MASTERTEC", "COMTECH", "CONICO", "SEVASA"]

    def __init__(self):
        self.results = []  # List of parsed items

    def detect_supplier(self, text: str) -> str:
        """Detect the supplier from the PDF text content."""
        text_upper = text.upper()
        for supplier in self.KNOWN_SUPPLIERS:
            if supplier in text_upper:
                return supplier
        return "DESCONOCIDO"

    def parse_pdf(self, filepath: str) -> dict:
        """
        Parse a single PDF proforma.
        Returns: {
            'proveedor': str,
            'num_proforma': str,
            'fecha': str,
            'items': [{'descripcion': str, 'cantidad': int/float, 'precio_unitario': float, 'precio_total': float}]
        }
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        with pdfplumber.open(filepath) as pdf:
            # Combine all pages text
            full_text = ""
            all_tables = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
                tables = page.extract_tables()
                all_tables.extend(tables)

            supplier = self.detect_supplier(full_text)

            # Extract metadata
            num_proforma = self._extract_proforma_number(full_text, supplier)
            fecha = self._extract_fecha(full_text)

            # Extract items based on supplier
            if supplier == "MASTERTEC":
                items = self._parse_mastertec(full_text, all_tables)
            elif supplier == "COMTECH":
                items = self._parse_comtech(full_text, all_tables)
            elif supplier == "CONICO":
                items = self._parse_conico(full_text, all_tables)
            elif supplier == "SEVASA":
                items = self._parse_sevasa(full_text, all_tables)
            else:
                items = self._parse_generic(full_text, all_tables)

            return {
                'proveedor': supplier,
                'num_proforma': num_proforma,
                'fecha': fecha,
                'items': items,
                'archivo': os.path.basename(filepath)
            }

    def _extract_proforma_number(self, text: str, supplier: str) -> str:
        """Extract proforma/quote number from text."""
        patterns = [
            r'(?:N[°º.]?\s*(?:PROFORMA|Proforma)|Proforma\s*#?:?|COTIZACI[ÓO]N\s*#?:?|N[°º]:?)\s*[:\s]*([A-Z0-9-]+\d+)',
            r'(?:id_cot|cotizacion)[=/](\d+)',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    def _extract_fecha(self, text: str) -> str:
        """Extract date from text."""
        patterns = [
            r'FECHA:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Fecha:\s*(\d{1,2}/\d{1,2}/\d{2,4})',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    def _clean_price(self, price_str) -> float:
        """Clean a price string and return float."""
        if price_str is None:
            return 0.0
        s = str(price_str).strip()
        # Take only the first line (multi-line cells may have junk appended)
        s = s.split('\n')[0].strip()
        s = re.sub(r'[Cc]\$\s*', '', s)
        # Remove ALL spaces within the number (handles "8 ,234.60" format)
        s = s.replace(' ', '')
        s = s.replace(',', '')
        s = s.strip()
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    def _clean_garbled_text(self, text: str) -> str:
        """Clean garbled text where pdfplumber separates characters with spaces.
        
        Example: '8GB 51 2 S S D P R O S L I' -> '8GB 512SSD PRO SLI'
        
        Strategy: find sequences of single characters (or digits) separated by
        spaces and join them together. A 'garbled segment' is 2+ consecutive
        single-char tokens.
        """
        if not text:
            return text

        tokens = text.split(' ')
        result = []
        garbled_buffer = []

        for token in tokens:
            if len(token) <= 1 and token != '':
                # Single character — likely part of garbled text
                garbled_buffer.append(token)
            else:
                # Multi-char token — flush any garbled buffer first
                if len(garbled_buffer) >= 2:
                    # Join garbled characters together
                    result.append(''.join(garbled_buffer))
                elif garbled_buffer:
                    # Too few single chars to be garbled, keep as-is
                    result.extend(garbled_buffer)
                garbled_buffer = []
                if token:
                    result.append(token)

        # Flush remaining buffer
        if len(garbled_buffer) >= 2:
            result.append(''.join(garbled_buffer))
        elif garbled_buffer:
            result.extend(garbled_buffer)

        return ' '.join(result)

    # ─────────────────────────────────────────────
    # MASTERTEC Parser
    # ─────────────────────────────────────────────
    def _parse_mastertec(self, text: str, tables: list) -> list:
        """Parse MASTERTEC proforma items."""
        items = []

        # Try table extraction first
        if tables:
            for table in tables:
                for row in table:
                    if row is None:
                        continue
                    # Table format: [CÓDIGO, UND, PRODUCTO, None, CANT, P/UNIT., TOTAL]
                    # Sometimes rows are merged with \n
                    row_str = [str(c) if c else "" for c in row]
                    joined = " ".join(row_str).upper()

                    # Skip header and footer rows
                    if any(skip in joined for skip in ["CÓDIGO", "CODIGO", "SUB-TOTAL", "DESCUENTO",
                                                        "TOTAL:", "GARANTÍA", "GARANTIA", "ENTREGA",
                                                        "PAGO", "VÁLIDA", "VALIDA", "CONTRIBUYENTES",
                                                        "NOMBRE DE", "BANPRO", "BANCENTRO", "BAC"]):
                        continue

                    # Handle multi-line cells (items separated by \n)
                    codes = row_str[0].split('\n') if len(row_str) > 0 else []
                    products = row_str[2].split('\n') if len(row_str) > 2 else []
                    quantities = row_str[4].split('\n') if len(row_str) > 4 else []
                    unit_prices = row_str[5].split('\n') if len(row_str) > 5 else []
                    total_prices = row_str[6].split('\n') if len(row_str) > 6 else []

                    # Filter out footer text from products
                    clean_products = []
                    clean_quantities = []
                    clean_unit_prices = []
                    clean_total_prices = []

                    for i, prod in enumerate(products):
                        prod_upper = prod.strip().upper()
                        if any(skip in prod_upper for skip in ["CONTRIBUYENTES", "NOMBRE DE",
                                                                "BANPRO", "BANCENTRO", "BAC", "CK A"]):
                            continue
                        if prod.strip():
                            clean_products.append(prod.strip())
                            clean_quantities.append(quantities[i].strip() if i < len(quantities) else "1")
                            clean_unit_prices.append(unit_prices[i].strip() if i < len(unit_prices) else "0")
                            clean_total_prices.append(total_prices[i].strip() if i < len(total_prices) else "0")

                    for i, prod in enumerate(clean_products):
                        if not prod:
                            continue
                        cant = self._clean_price(clean_quantities[i]) if i < len(clean_quantities) else 1
                        precio_u = self._clean_price(clean_unit_prices[i]) if i < len(clean_unit_prices) else 0
                        precio_t = self._clean_price(clean_total_prices[i]) if i < len(clean_total_prices) else 0

                        if cant == 0:
                            cant = 1
                        if precio_u > 0:
                            items.append({
                                'descripcion': prod,
                                'cantidad': int(cant) if cant == int(cant) else cant,
                                'precio_unitario': precio_u,
                                'precio_total': precio_t if precio_t > 0 else precio_u * cant
                            })

        # Fallback: regex on raw text
        if not items:
            pattern = re.compile(
                r'^\d+\s+(?:Unidad|UND)?\s*(.*?)\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$',
                re.IGNORECASE | re.MULTILINE
            )
            for m in pattern.finditer(text):
                desc = m.group(1).strip()
                cant = int(m.group(2))
                precio_u = self._clean_price(m.group(3))
                precio_t = self._clean_price(m.group(4))
                if desc and precio_u > 0:
                    items.append({
                        'descripcion': desc,
                        'cantidad': cant,
                        'precio_unitario': precio_u,
                        'precio_total': precio_t
                    })

        return items

    # ─────────────────────────────────────────────
    # COMTECH Parser
    # ─────────────────────────────────────────────
    def _parse_comtech(self, text: str, tables: list) -> list:
        """Parse COMTECH proforma items."""
        items = []

        # Try table extraction first
        if tables:
            for table in tables:
                for row in table:
                    if row is None:
                        continue
                    row_str = [str(c) if c else "" for c in row]
                    joined = " ".join(row_str).upper()

                    # Skip headers and footers
                    if any(skip in joined for skip in ["CÓDIGO", "CODIGO", "DESCRIPCIÓN", "DESCRIPCION",
                                                        "SUB-TOTAL", "CONDICIONES", "FORMA DE PAGO",
                                                        "VIGENCIA", "GARANTÍA", "GARANTIA", "MONTO EN LETRAS"]):
                        continue

                    # Table format: [Código, Descripción, Cant., Precio Un., Total(C$), Entrega]
                    if len(row_str) >= 5:
                        codigo = row_str[0].strip()
                        desc = row_str[1].strip() if row_str[1] else ""
                        cant_str = row_str[2].strip() if row_str[2] else ""
                        precio_u_str = row_str[3].strip() if row_str[3] else ""
                        precio_t_str = row_str[4].strip() if row_str[4] else ""

                        # Clean multiline descriptions
                        desc = desc.replace('\n', ' ').strip()

                        if not desc or not codigo:
                            continue

                        cant = self._clean_price(cant_str)
                        precio_u = self._clean_price(precio_u_str)
                        precio_t = self._clean_price(precio_t_str)

                        if cant == 0:
                            cant = 1
                        if precio_u > 0:
                            items.append({
                                'descripcion': desc,
                                'cantidad': int(cant) if cant == int(cant) else cant,
                                'precio_unitario': precio_u,
                                'precio_total': precio_t if precio_t > 0 else precio_u * cant
                            })

        # Fallback: regex
        if not items:
            pattern = re.compile(
                r'^([\w-]+)\s+(.*?)\s+(\d+)\s+C\$\s*([\d,]+\.\d{2})',
                re.IGNORECASE | re.MULTILINE
            )
            for m in pattern.finditer(text):
                desc = m.group(2).strip()
                cant = int(m.group(3))
                precio_u = self._clean_price(m.group(4))
                if desc and precio_u > 0:
                    items.append({
                        'descripcion': desc,
                        'cantidad': cant,
                        'precio_unitario': precio_u,
                        'precio_total': precio_u * cant
                    })

        return items

    # ─────────────────────────────────────────────
    # CONICO Parser
    # ─────────────────────────────────────────────
    def _parse_conico(self, text: str, tables: list) -> list:
        """Parse CONICO proforma items."""
        items = []

        # Try table extraction first (some CONICO PDFs have tables)
        if tables:
            for table in tables:
                for row in table:
                    if row is None:
                        continue
                    row_str = [str(c) if c else "" for c in row]
                    joined = " ".join(row_str).upper()

                    # Skip headers and footers
                    if any(skip in joined for skip in ["ITEM", "DESCRIPCION", "SUB-TOTAL", "SUBTOTAL",
                                                        "OBSERVACIONES", "CONDICIONES", "GARANTIA",
                                                        "OFERTA VALIDA", "TIEMPO DE ENTREGA",
                                                        "ELABORAR CK", "SE NOS RETIENE",
                                                        "DESCUENTO APLICADO", "LOS PRECIOS ESTAN"]):
                        continue

                    # Try to find item data in the row
                    # Look for cells with C$ prices
                    desc = ""
                    cant = 1.0
                    precio_u = 0.0
                    precio_t = 0.0
                    prices_found = []

                    for cell in row_str:
                        cell = cell.strip()
                        if not cell:
                            continue
                        # Check if cell contains a C$ price
                        price_match = re.search(r'C\$\s*([\d,]+\.\d{2})', cell)
                        if price_match:
                            prices_found.append(self._clean_price(price_match.group(1)))
                        elif re.match(r'^\d+\.?\d*$', cell):
                            cant = float(cell)
                        elif not re.match(r'^[\d.,\s]+$', cell) and len(cell) > 3:
                            # Clean multiline descriptions
                            desc = cell.replace('\n', ' ').strip()

                    if desc and len(prices_found) >= 1:
                        precio_u = prices_found[0]
                        precio_t = prices_found[-1] if len(prices_found) > 1 else precio_u * cant
                        items.append({
                            'descripcion': desc,
                            'cantidad': int(cant) if cant == int(cant) else cant,
                            'precio_unitario': precio_u,
                            'precio_total': precio_t
                        })

        # Text-based parsing (primary method for CONICO)
        if not items:
            lines = text.split('\n')
            in_items = False
            # Buffer to accumulate multi-line descriptions
            pending_desc = ""

            for line in lines:
                line_stripped = line.strip()
                upper = line_stripped.upper()

                # Detect start of items section
                if "ITEM" in upper and "DESCRIPCION" in upper:
                    in_items = True
                    continue

                # Detect end of items section
                if in_items and ("SUB-TOTAL" in upper or "SUBTOTAL" in upper or
                                  "OBSERVACIONES" in upper or "OFERTA VALIDA" in upper):
                    in_items = False
                    continue

                if not in_items:
                    continue

                # Skip empty lines
                if not line_stripped:
                    continue

                # CONICO line format:
                # DESCRIPCION CANT PRECIO TOTAL
                # e.g.: EQUIPO HP DT 400 G9 SFF... 1.00 C$32,739.40 C$32,739.40
                # Also handle: LAPTOP MSI... 1.00 C$66,289.06 C$66,289.06
                m = re.match(
                    r'^(.*?)\s+(\d+\.?\d*)\s+C\$([\d,]+\.\d{2})\s+C\$([\d,]+\.\d{2})$',
                    line_stripped
                )
                # Also try: line starts directly with quantity + prices (desc on previous line)
                # e.g.: "1.00 C$66,289.06 C$66,289.06"
                if not m:
                    m2 = re.match(
                        r'^(\d+\.?\d*)\s+C\$([\d,]+\.\d{2})\s+C\$([\d,]+\.\d{2})$',
                        line_stripped
                    )
                    if m2:
                        # Use pending_desc as the description
                        desc = pending_desc.strip() if pending_desc else ""
                        pending_desc = ""
                        cant = float(m2.group(1))
                        precio_u = self._clean_price(m2.group(2))
                        precio_t = self._clean_price(m2.group(3))

                        if desc and precio_u > 0:
                            items.append({
                                'descripcion': desc,
                                'cantidad': int(cant) if cant == int(cant) else cant,
                                'precio_unitario': precio_u,
                                'precio_total': precio_t if precio_t > 0 else precio_u * cant
                            })
                        continue

                if m:
                    desc = m.group(1).strip()
                    # Prepend any pending multi-line description
                    if pending_desc:
                        desc = pending_desc + " " + desc
                        pending_desc = ""
                    cant = float(m.group(2))
                    precio_u = self._clean_price(m.group(3))
                    precio_t = self._clean_price(m.group(4))

                    if desc and precio_u > 0:
                        items.append({
                            'descripcion': desc,
                            'cantidad': int(cant) if cant == int(cant) else cant,
                            'precio_unitario': precio_u,
                            'precio_total': precio_t if precio_t > 0 else precio_u * cant
                        })
                        pending_desc = ""  # Reset after successful item
                else:
                    # Line without prices could be a continuation of description
                    # or a trailing model number after the price line (e.g. "B14WEK")
                    skip_words_desc = ["OBSERVACIONES", "OFERTA", "TIEMPO", "ELABORAR",
                                       "SE NOS", "T/C", "LOS PRECIOS", "GARANTIA",
                                       "SUB-TOTAL", "SUBTOTAL", "CONDICIONES",
                                       "DESCUENTO", "NETO", "ELABORAR CK"]
                    if line_stripped and not any(skip in upper for skip in skip_words_desc):
                        # If we just added an item and this line looks like a model/part suffix,
                        # append it to the last item's description
                        if items and not pending_desc and len(line_stripped) < 30 and not re.search(r'C\$', line_stripped):
                            items[-1]['descripcion'] += " " + line_stripped
                        else:
                            pending_desc = (pending_desc + " " + line_stripped).strip() if pending_desc else line_stripped

        return items

    # ─────────────────────────────────────────────
    # SEVASA Parser (generic/similar to CONICO)
    # ─────────────────────────────────────────────
    def _parse_sevasa(self, text: str, tables: list) -> list:
        """Parse SEVASA proforma items with dedicated parser."""
        items = []

        # Summary/footer patterns to skip
        summary_patterns = [
            'SUB TOTAL', 'SUB-TOTAL', 'SUBTOTAL', 'TOTAL C$', 'TOTAL C',
            'IVA ', 'IVA%', 'IVA1', 'FORMA DE PAGO', 'FORMA PAGO',
            'CONDICIONES', 'ELABORAR CK', 'ELABORAR CH',
            'CK A NOMBRE', 'CHEQUE A NOMBRE', 'PAGOS SOLO',
            'SOMOS EXENTOS', 'SOMOS GRANDES', 'NOS RETIENEN',
            'SE NOS RETIENE', 'TIEMPO DE ENTREGA', 'CONTADO',
            'CREDITO', 'TRANSFERENCIA', 'DESCUENTO APLICADO',
            'MONTO EN LETRAS', 'LOS PRECIOS', 'PRECIOS EXPRESADOS',
            'GARANTIA', 'GARANTÍA', 'VIGENCIA', 'OFERTA VALIDA',
            'TERMINOS', 'TÉRMINOS', 'OBSERVACIONES',
            'CONCEPTO', 'COTIZACION EN', 'GRAN TOTAL', 'TOTAL IMPUESTO',
            'NUMERO DE REGISTROS', 'PAG.NO', 'PAG NO',
        ]

        # ── Attempt 1: Text-based parsing with C$ prices ──
        lines = text.split('\n')
        for line in lines:
            line_stripped = line.strip()
            upper = line_stripped.upper()

            # Skip summary/footer lines
            if any(pat in upper for pat in summary_patterns):
                continue

            # Look for lines with C$ prices:
            # Format: CANT DESCRIPTION C$ PRICE C$ PRICE
            m = re.match(
                r'^(\d+)\s+(.*?)\s+C\$\s*([\d,]+\.\d{2})\s+C\$\s*([\d,]+\.\d{2})$',
                line_stripped
            )
            if m:
                cant = int(m.group(1))
                desc = m.group(2).strip()
                precio_u = self._clean_price(m.group(3))
                precio_t = self._clean_price(m.group(4))
                desc_upper = desc.upper()
                if any(pat in desc_upper for pat in summary_patterns):
                    continue
                if desc and precio_u > 0:
                    items.append({
                        'descripcion': desc,
                        'cantidad': cant,
                        'precio_unitario': precio_u,
                        'precio_total': precio_t
                    })

        if items:
            return items

        # ── Attempt 1b: Text-based parsing WITHOUT C$ prefix (SEVASA format) ──
        # Format: CODE DESCRIPTION QUANTITY PRICE TOTAL
        # e.g.: 4945 COMPUTADORA DELL CI5-14500 8GB 512SSD PRO SLI 1.00 36,074.94 36,074.94
        # Note: pdfplumber may garble text with spaces between chars
        in_items = False
        for line in lines:
            line_stripped = line.strip()
            upper = line_stripped.upper()

            # Detect header row to know where items start
            if ('CODIGO' in upper or 'CÓDIGO' in upper) and ('NOMBRE' in upper or 'PRECIO' in upper):
                in_items = True
                continue

            # Skip summary/footer lines — stop parsing items
            if any(pat in upper for pat in summary_patterns):
                if in_items:
                    in_items = False
                continue

            if not in_items or not line_stripped:
                continue

            # Match: CODE DESCRIPTION QUANTITY UNIT_PRICE TOTAL_PRICE
            # The code is numeric, quantity is like 1.00, prices are like 36,074.94
            m = re.match(
                r'^(\d{2,})\s+(.*?)\s+(\d+\.?\d*)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$',
                line_stripped
            )
            if m:
                desc = m.group(2).strip()
                cant = self._clean_price(m.group(3))
                precio_u = self._clean_price(m.group(4))
                precio_t = self._clean_price(m.group(5))

                # Clean garbled text: remove single-char spacing artifacts
                # e.g. "8GB 51 2 S S D P R O S L I" -> "8GB 512SSD PRO SLI"
                desc = self._clean_garbled_text(desc)

                desc_upper = desc.upper()
                if any(pat in desc_upper for pat in summary_patterns):
                    continue

                if desc and precio_u > 0:
                    if cant == 0:
                        cant = 1
                    items.append({
                        'descripcion': desc,
                        'cantidad': int(cant) if cant == int(cant) else cant,
                        'precio_unitario': precio_u,
                        'precio_total': precio_t if precio_t > 0 else precio_u * cant
                    })

        if items:
            return items

        # ── Attempt 2: Structured table parsing ──
        # SEVASA table format: Código | Nombre | U/M | Unidades | Precio | Total
        if tables:
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Try to find header row and identify column indices
                header_row_idx = -1
                col_nombre = -1
                col_unidades = -1
                col_precio = -1
                col_total = -1
                col_codigo = -1

                for ri, row in enumerate(table):
                    if row is None:
                        continue
                    row_upper = [str(c).upper().strip() if c else "" for c in row]
                    joined = " ".join(row_upper)

                    # Look for header row with column names
                    has_nombre = any('NOMBRE' in cell or 'DESCRIPCI' in cell for cell in row_upper)
                    has_precio = any('PRECIO' in cell or 'P.UNIT' in cell or 'P. UNIT' in cell for cell in row_upper)
                    has_unidades = any('UNIDAD' in cell or 'CANT' in cell for cell in row_upper)

                    if has_nombre and has_precio:
                        header_row_idx = ri
                        for ci, cell in enumerate(row_upper):
                            if 'CODIGO' in cell or 'CÓDIGO' in cell:
                                col_codigo = ci
                            elif 'NOMBRE' in cell or 'DESCRIPCI' in cell:
                                col_nombre = ci
                            elif 'UNIDAD' in cell or 'CANT' in cell:
                                col_unidades = ci
                            elif 'PRECIO' in cell and 'TOTAL' not in cell:
                                col_precio = ci
                            elif 'TOTAL' in cell:
                                col_total = ci
                            elif 'P.UNIT' in cell or 'P. UNIT' in cell:
                                col_precio = ci
                            elif 'P.TOTAL' in cell or 'P. TOTAL' in cell:
                                col_total = ci
                        break

                if header_row_idx < 0:
                    continue

                # If we couldn't find precio but found total, try to infer
                # In SEVASA format: Código(0) | Nombre(1) | U/M(2) | Unidades(3) | Precio(4) | Total(5)
                if col_precio < 0 and col_total >= 0:
                    col_precio = col_total - 1

                # Parse data rows after header
                for ri in range(header_row_idx + 1, len(table)):
                    row = table[ri]
                    if row is None:
                        continue

                    row_str = [str(c).strip() if c else "" for c in row]
                    joined_upper = " ".join(row_str).upper()

                    # Skip empty rows
                    if all(c == "" for c in row_str):
                        continue

                    # Skip summary/footer rows
                    if any(pat in joined_upper for pat in summary_patterns):
                        continue

                    # Extract description
                    desc = row_str[col_nombre] if col_nombre >= 0 and col_nombre < len(row_str) else ""
                    desc = desc.replace('\n', ' ').strip()

                    # Skip if description is empty or a summary word
                    if not desc or len(desc) < 3:
                        continue
                    desc_upper = desc.upper()
                    if any(pat in desc_upper for pat in summary_patterns):
                        continue

                    # Extract quantity
                    cant = 1
                    if col_unidades >= 0 and col_unidades < len(row_str):
                        cant_val = self._clean_price(row_str[col_unidades])
                        if cant_val > 0:
                            cant = cant_val

                    # Extract unit price
                    precio_u = 0.0
                    if col_precio >= 0 and col_precio < len(row_str):
                        precio_u = self._clean_price(row_str[col_precio])

                    # Extract total price
                    precio_t = 0.0
                    if col_total >= 0 and col_total < len(row_str):
                        precio_t = self._clean_price(row_str[col_total])

                    if precio_u > 0:
                        items.append({
                            'descripcion': desc,
                            'cantidad': int(cant) if cant == int(cant) else cant,
                            'precio_unitario': precio_u,
                            'precio_total': precio_t if precio_t > 0 else precio_u * cant
                        })

        if items:
            return items

        # ── Attempt 3: Generic table fallback ──
        if tables:
            for table in tables:
                for row in table:
                    if row is None:
                        continue
                    row_str = [str(c).split('\n')[0].strip() if c else "" for c in row]
                    joined = " ".join(row_str).upper()

                    # Skip headers
                    if any(skip in joined for skip in ["CANT.", "DESCRIPCI", "P. UNIT", "P.TOTAL",
                                                        "CÓDIGO", "CODIGO", "NOMBRE"]):
                        continue

                    # Skip empty rows
                    if all(c == "" for c in row_str):
                        continue

                    # Check for summary/footer patterns in the row
                    if any(pat in joined for pat in summary_patterns):
                        continue

                    # Look for rows that have prices (actual product rows)
                    prices = []
                    desc_parts = []
                    cant = 1

                    for i, cell in enumerate(row_str):
                        cell = cell.strip()
                        if not cell:
                            continue
                        price_val = self._clean_price(cell)
                        if price_val > 10:
                            prices.append(price_val)
                        elif re.match(r'^\d+$', cell):
                            cant = int(cell)
                        elif not re.match(r'^[\d.,\s]+$', cell):
                            desc_upper = cell.upper()
                            if desc_upper in ('TOTAL', 'SUBTOTAL', 'SUB-TOTAL', 'SUB TOTAL',
                                              'IVA', 'DESCUENTO', 'MONEDA', 'NETO'):
                                continue
                            if any(desc_upper.startswith(pat) or pat in desc_upper
                                   for pat in summary_patterns):
                                continue
                            if len(cell) > 2:
                                desc_parts.append(cell)

                    desc = " ".join(desc_parts).strip()

                    if desc and len(prices) >= 1:
                        items.append({
                            'descripcion': desc,
                            'cantidad': cant,
                            'precio_unitario': prices[0],
                            'precio_total': prices[-1] if len(prices) > 1 else prices[0] * cant
                        })

        return items

    # ─────────────────────────────────────────────
    # Generic Parser (fallback)
    # ─────────────────────────────────────────────
    def _parse_generic(self, text: str, tables: list) -> list:
        """Generic parser that tries to extract items from any proforma format."""
        items = []

        # Try tables first
        if tables:
            for table in tables:
                for row in table:
                    if row is None:
                        continue
                    # Clean each cell: take only the first line to avoid footer
                    # text (like SUBTOTAL, IVA) leaking into data cells
                    row_str = []
                    for c in row:
                        if c:
                            first_line = str(c).split('\n')[0].strip()
                            row_str.append(first_line)
                        else:
                            row_str.append("")

                    joined = " ".join(row_str).upper()

                    # Skip obvious non-data rows (only if ALL content is header/footer)
                    skip_words = ["CÓDIGO", "CODIGO", "DESCRIPCIÓN", "DESCRIPCION",
                                  "SUB-TOTAL", "SUBTOTAL", "SUB TOTAL", "CONDICIONES",
                                  "GARANTÍA", "GARANTIA", "TERMINOS"]
                    # Only skip if the row starts with or is primarily a header
                    # Don't skip rows that have a product code in the first cell
                    first_cell = row_str[0].upper().strip() if row_str else ""
                    is_header = any(skip in joined for skip in skip_words)
                    has_product_code = bool(first_cell and re.match(r'^[A-Z0-9]{3,}', first_cell)
                                           and not any(skip in first_cell for skip in skip_words))

                    if is_header and not has_product_code:
                        continue

                    # Skip rows where all cells are empty
                    if all(c == "" for c in row_str):
                        continue

                    # Try to find price-like values in the row
                    prices = []
                    desc_parts = []
                    cant = 1

                    for cell in row_str:
                        cell = cell.strip()
                        if not cell:
                            continue
                        price_val = self._clean_price(cell)
                        if price_val > 10:  # Likely a price
                            prices.append(price_val)
                        elif re.match(r'^\d+$', cell):
                            cant = int(cell)
                        elif not re.match(r'^[\d.,\s]+$', cell):
                            desc_parts.append(cell)

                    desc = " ".join(desc_parts).strip()
                    # Filter out rows where description is a summary/footer line
                    desc_upper = desc.upper()
                    # Exact matches for common summary words
                    if desc_upper in ('TOTAL', 'SUBTOTAL', 'SUB-TOTAL', 'SUB TOTAL', 'IVA',
                                      'DESCUENTO', 'MONEDA', 'CORDOBAS', 'NETO'):
                        continue
                    # Substring/starts-with matching for summary lines
                    summary_patterns = [
                        'SUB TOTAL', 'SUB-TOTAL', 'SUBTOTAL', 'TOTAL C$', 'TOTAL C',
                        'IVA ', 'IVA%', 'IVA1', 'FORMA DE PAGO', 'FORMA PAGO',
                        'CONDICIONES', 'ELABORAR CK', 'ELABORAR CH',
                        'CK A NOMBRE', 'CHEQUE A NOMBRE', 'PAGOS SOLO',
                        'SOMOS EXENTOS', 'SOMOS GRANDES', 'NOS RETIENEN',
                        'SE NOS RETIENE', 'TIEMPO DE ENTREGA', 'CONTADO',
                        'CREDITO', 'TRANSFERENCIA', 'DESCUENTO APLICADO',
                        'MONTO EN LETRAS', 'LOS PRECIOS', 'PRECIOS EXPRESADOS',
                        'GARANTIA', 'GARANTÍA', 'VIGENCIA', 'OFERTA VALIDA',
                        'TERMINOS', 'TÉRMINOS', 'OBSERVACIONES',
                    ]
                    if any(desc_upper.startswith(pat) or pat in desc_upper
                           for pat in summary_patterns):
                        continue
                    if desc and len(prices) >= 1:
                        items.append({
                            'descripcion': desc,
                            'cantidad': cant,
                            'precio_unitario': prices[0],
                            'precio_total': prices[-1] if len(prices) > 1 else prices[0] * cant
                        })

        # Fallback: regex for C$ prices in text
        if not items:
            pattern = re.compile(
                r'(.*?)\s+(\d+)\s+C\$\s*([\d,]+\.\d{2})',
                re.MULTILINE
            )
            for m in pattern.finditer(text):
                desc = m.group(1).strip()
                cant = int(m.group(2))
                precio = self._clean_price(m.group(3))
                if desc and precio > 0 and len(desc) > 3:
                    items.append({
                        'descripcion': desc,
                        'cantidad': cant,
                        'precio_unitario': precio,
                        'precio_total': precio * cant
                    })

        return items


def parse_multiple_pdfs(filepaths: list) -> dict:
    """
    Parse multiple PDF proformas and return structured data.
    
    Returns: {
        'proformas': [
            {'proveedor': str, 'num_proforma': str, 'fecha': str, 'items': [...], 'archivo': str}
        ],
        'all_items': [
            {'proveedor': str, 'descripcion': str, 'cantidad': int, 'precio_unitario': float}
        ]
    }
    """
    parser = ProformaParser()
    proformas = []
    all_items = []

    for filepath in filepaths:
        if not filepath:
            continue
        try:
            result = parser.parse_pdf(filepath)
            proformas.append(result)
            for item in result['items']:
                all_items.append({
                    'proveedor': result['proveedor'],
                    'descripcion': item['descripcion'],
                    'cantidad': item['cantidad'],
                    'precio_unitario': item['precio_unitario'],
                    'precio_total': item.get('precio_total', item['precio_unitario'] * item['cantidad'])
                })
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            import traceback
            traceback.print_exc()

    return {
        'proformas': proformas,
        'all_items': all_items
    }

def detect_supplier_from_pdf(filepath: str) -> str:
    """Fast detection of supplier by reading only the first page."""
    import pdfplumber
    import os
    if not os.path.exists(filepath):
        return "DESCONOCIDO"
    try:
        with pdfplumber.open(filepath) as pdf:
            if not pdf.pages:
                return "DESCONOCIDO"
            text = pdf.pages[0].extract_text() or ""
            parser = ProformaParser()
            return parser.detect_supplier(text)
    except Exception:
        return "DESCONOCIDO"
