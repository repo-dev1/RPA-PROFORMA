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

        # CONICO format is typically text-based, parse line by line
        lines = text.split('\n')
        in_items = False

        for line in lines:
            line_stripped = line.strip()
            upper = line_stripped.upper()

            # Detect start of items section
            if "ITEM" in upper and "DESCRIPCION" in upper:
                in_items = True
                continue

            # Detect end of items section
            if in_items and ("SUB-TOTAL" in upper or "OBSERVACIONES" in upper):
                in_items = False
                continue

            if not in_items:
                continue

            # CONICO line format:
            # DESCRIPCION CANT PRECIO TOTAL
            # e.g.: EQUIPO HP DT 400 G9 SFF I5-13500/16GB/512GB/W11P#9L8V5LA#ABM 1.00 C$32,739.40 C$32,739.40
            m = re.match(
                r'^(.*?)\s+(\d+\.?\d*)\s+C\$([\d,]+\.\d{2})\s+C\$([\d,]+\.\d{2})$',
                line_stripped
            )
            if m:
                desc = m.group(1).strip()
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

        return items

    # ─────────────────────────────────────────────
    # SEVASA Parser (generic/similar to CONICO)
    # ─────────────────────────────────────────────
    def _parse_sevasa(self, text: str, tables: list) -> list:
        """Parse SEVASA proforma items. Uses generic approach."""
        return self._parse_generic(text, tables)

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
                                  "SUB-TOTAL", "SUBTOTAL", "CONDICIONES",
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
                    # Filter out rows where description is just a summary word
                    desc_upper = desc.upper()
                    if desc_upper in ('TOTAL', 'SUBTOTAL', 'SUB-TOTAL', 'IVA',
                                      'DESCUENTO', 'MONEDA', 'CORDOBAS'):
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
