"""Title block unique bandeau bas + logo PNG compatible AutoCAD."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple

from .sanitize import sanitize_layer_name, sanitize_text
from .symbols import add_potech_p_mark


def _rect(layout, x0, y0, x1, y1, layer):
    layout.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], dxfattribs={"layer": layer})


def _is_black_layer(layout: object, layer_name: str) -> bool:
    try:
        layer = layout.doc.layers.get(layer_name)
        return abs(int(layer.dxf.color)) == 7
    except Exception:
        return False


def _titleblock_text_color(layout: object, layer_name: str) -> int:
    return 256 if _is_black_layer(layout, layer_name) else 7


def _extract_qty_and_clean_designation(designation: object) -> Tuple[str, Optional[int]]:
    value = str(designation or "").strip()
    match = re.search(r"\(\s*x\s*(\d+)\s*\)", value, flags=re.IGNORECASE)
    if not match:
        return value, None
    qty = None
    try:
        qty = int(match.group(1))
    except Exception:
        qty = None
    cleaned = re.sub(r"\(\s*x\s*\d+\s*\)", "", value, flags=re.IGNORECASE).strip()
    return cleaned, qty


def add_logo(layout: object, logo_path: Optional[str], target_rect: Tuple[float, float, float, float]) -> bool:
    """Ajoute le vrai logo PNG via IMAGE/IMAGEDEF."""
    x0, y0, x1, y1 = target_rect
    w = max(1.0, float(x1) - float(x0))
    h = max(1.0, float(y1) - float(y0))

    layer_tb = sanitize_layer_name("TITLEBLOCK", fallback="TITLEBLOCK")

    candidate_paths = []
    if logo_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.abspath(os.path.join(script_dir, ".."))
        workspace_parent = os.path.abspath(os.path.join(project_dir, ".."))

        candidate_paths.append(logo_path)
        candidate_paths.append(os.path.join(os.getcwd(), logo_path))
        candidate_paths.append(os.path.join(project_dir, logo_path))
        candidate_paths.append(os.path.join(workspace_parent, logo_path))

    resolved_logo = None
    for path in candidate_paths:
        if path and os.path.isfile(path):
            resolved_logo = path
            break

    if resolved_logo and os.path.isfile(resolved_logo):
        try:
            px_size = (1000, 400)
            try:
                pil_mod = __import__("PIL.Image", fromlist=["Image"])
                with pil_mod.open(resolved_logo) as img:
                    px_size = tuple(img.size)
            except Exception:
                pass

            abs_path = os.path.abspath(resolved_logo)
            image_def = layout.doc.add_image_def(filename=abs_path, size_in_pixel=px_size)
            layout.add_image(
                image_def,
                insert=(x0, y0),
                size_in_units=(w, h),
                dxfattribs={"layer": layer_tb},
            )
            return True
        except Exception:
            pass
    return False


def draw_embedded_logo(layout: object, target_rect: Tuple[float, float, float, float], text_style: str = "Standard") -> None:
    """Dessine un logo vectoriel minimal directement dans le DXF.

    Sert de secours si l'entité IMAGE n'est pas affichée par le lecteur DXF.
    """
    x0, y0, x1, y1 = target_rect
    w = max(1.0, float(x1) - float(x0))
    h = max(1.0, float(y1) - float(y0))

    layer_tb = sanitize_layer_name("TITLEBLOCK", fallback="TITLEBLOCK")
    layer_txt = sanitize_layer_name("TEXT", fallback="TEXT")

    cx = x0 + w * 0.48
    cy = y0 + h * 0.63
    radius = min(w, h) * 0.22
    color_logo = 5

    try:
        # Monogramme simple, toujours visible dans le DXF.
        p_main = layout.add_text(
            "P",
            dxfattribs={"layer": layer_tb, "height": h * 0.78, "style": text_style, "color": color_logo},
        )
        try:
            from ezdxf.enums import TextEntityAlignment

            p_main.set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)
        except Exception:
            p_main.set_placement((cx, cy))
    except Exception:
        pass

    # Deux anneaux/contours pour rappeler le logo fourni.
    for center, r in [((cx - radius * 0.35, cy + radius * 0.18), radius), ((cx + radius * 0.32, cy + radius * 0.10), radius * 0.92)]:
        try:
            layout.add_circle(center, r, dxfattribs={"layer": layer_tb, "color": color_logo})
        except Exception:
            pass

    try:
        txt = layout.add_text(
            "INGENIERIE",
            dxfattribs={"layer": layer_txt, "height": max(1.5, h * 0.12), "style": text_style, "color": 7},
        )
        try:
            from ezdxf.enums import TextEntityAlignment

            txt.set_placement((x0 + w * 0.5, y0 + h * 0.12), align=TextEntityAlignment.MIDDLE_CENTER)
        except Exception:
            txt.set_placement((x0 + w * 0.5, y0 + h * 0.12))
    except Exception:
        pass


def add_title_block(
    layout: object,
    paper_w: float = 420.0,
    paper_h: float = 297.0,
    margin: float = 10.0,
    metadata: Optional[Dict[str, Any]] = None,
    logo_path: Optional[str] = None,
    text_height: float = 3.0,
    titleblock_height: float = 48.0,
    titleblock_width: Optional[float] = None,
    use_external_logo_image: bool = False,
) -> bool:
    """Ajoute le cartouche unique (pas de légende séparée)."""
    metadata = metadata or {}

    layer_tb = sanitize_layer_name("TITLEBLOCK", fallback="TITLEBLOCK")
    layer_txt = sanitize_layer_name("TEXT", fallback="TEXT")
    layer_sym = sanitize_layer_name("SYMBOLS", fallback="SYMBOLS")

    for layer_name, color in ((layer_tb, 7), (layer_txt, 7), (layer_sym, 7)):
        if layer_name not in layout.doc.layers:
            layout.doc.layers.new(layer_name, dxfattribs={"color": color})

    try:
        from ezdxf.enums import TextEntityAlignment
    except Exception:
        TextEntityAlignment = None

    # Cartouche = même zone que le viewport : de margin à paper_w-margin.
    available_width = max(1.0, float(paper_w) - 2.0 * float(margin))
    if titleblock_width is None:
        block_width = available_width
    else:
        block_width = min(max(80.0, float(titleblock_width)), available_width)

    x_left = float(margin)
    x_right = x_left + block_width
    y_bottom = float(margin)
    y_top = float(margin) + float(titleblock_height)

    try:
        _rect(layout, x_left, y_bottom, x_right, y_top, layer_tb)
    except Exception:
        return False

    uniform_text_h = max(2.4, float(text_height))
    logo_width = 44.0
    col_y_split = y_bottom + max(16.0, float(titleblock_height) * 0.46)

    try:
        layout.add_line((x_left + logo_width, y_bottom), (x_left + logo_width, y_top), dxfattribs={"layer": layer_tb})
        layout.add_line((x_left, col_y_split), (x_right, col_y_split), dxfattribs={"layer": layer_tb})
    except Exception:
        pass

    content_x = x_left + logo_width + 2.0
    content_width = x_right - content_x - 2.0
    top_cols = 5
    col_width = content_width / float(top_cols)

    def _txt(value, x, y, h=text_height, align=None):
        text_color = _titleblock_text_color(layout, layer_txt)
        t = layout.add_text(
            sanitize_text(str(value), fallback="-"),
            dxfattribs={"layer": layer_txt, "height": float(h), "style": "Standard", "color": text_color},
        )
        if TextEntityAlignment and align is not None:
            t.set_placement((x, y), align=align)
        else:
            t.set_placement((x, y))

    def _fit_text_height(value, max_width, preferred=None, min_height=1.2):
        safe_value = sanitize_text(str(value), fallback="-")
        pref = uniform_text_h if preferred is None else float(preferred)
        if max_width <= 0:
            return max(min_height, pref)
        # Approximation DXF largeur de texte mono-ligne.
        estimated = max(1, len(safe_value)) * 0.62 * pref
        if estimated <= max_width:
            return max(min_height, pref)
        fitted = float(max_width) / (max(1, len(safe_value)) * 0.62)
        return max(min_height, min(pref, fitted))

    def _txt_bold(value, x, y, h=text_height, align=None, color=None):
        text_color = _titleblock_text_color(layout, layer_txt) if color is None else int(color)
        safe_value = sanitize_text(str(value), fallback="-")
        offsets = [(0.0, 0.0), (0.18, 0.0), (0.0, 0.18), (0.18, 0.18)]
        for dx, dy in offsets:
            t = layout.add_text(
                safe_value,
                dxfattribs={"layer": layer_txt, "height": float(h), "style": "Standard", "color": text_color},
            )
            if TextEntityAlignment and align is not None:
                t.set_placement((x + dx, y + dy), align=align)
            else:
                t.set_placement((x + dx, y + dy))

    logo_case_cx = x_left + logo_width * 0.5
    logo_top_rect = (
        x_left + 1.5,
        col_y_split + 1.5,
        x_left + logo_width - 1.5,
        y_top - 1.5,
    )
    # DXF portable multi-postes: par défaut on évite IMAGE (chemin externe),
    # et on dessine un logo vectoriel intégré dans le fichier.
    inserted_logo = False
    if use_external_logo_image:
        inserted_logo = add_logo(layout, logo_path=logo_path, target_rect=logo_top_rect)
    if not inserted_logo:
        add_potech_p_mark(
            layout,
            logo_top_rect,
            layer=layer_sym,
            color=7,
            source_logo_path=logo_path,
        )

    _txt(
        "CREATEUR",
        logo_case_cx,
        y_bottom + (col_y_split - y_bottom) * 0.68,
        h=_fit_text_height("CREATEUR", logo_width - 6.0, preferred=uniform_text_h),
        align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None,
    )
    _txt(
        "PASCAL OLIVARES",
        logo_case_cx,
        y_bottom + (col_y_split - y_bottom) * 0.34,
        h=_fit_text_height("PASCAL OLIVARES", logo_width - 6.0, preferred=uniform_text_h),
        align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None,
    )

    designation_raw = metadata.get("part_name", metadata.get("designation", metadata.get("reference", "")))
    designation, qty_from_designation = _extract_qty_and_clean_designation(designation_raw)
    qty_value = metadata.get("quantity", metadata.get("qty", 1))
    if qty_from_designation is not None:
        qty_value = qty_from_designation

    # ---------------------------------------------------------------
    # LIGNE DU HAUT : DATE | PROJET | CORPS DE MEUBLE | DESIGNATION (fusionnee cols 3+4)
    # ---------------------------------------------------------------
    top_fields = [
        ("DATE",           metadata.get("date", ""),                                          0),
        ("PROJET",         metadata.get("project_name", ""),                                   1),
        ("CORPS DE MEUBLE",metadata.get("corps_meuble", metadata.get("body", "caisson")),      2),
    ]
    for label, value, idx in top_fields:
        cx = content_x + col_width * idx + col_width * 0.5
        _txt(label, cx, y_top - 6.0,  h=_fit_text_height(label, col_width - 6.0), align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)
        _txt(value, cx, y_top - 15.0, h=_fit_text_height(value, col_width - 6.0), align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)

    # DESIGNATION fusionnee : occupe cols 3 + 4 (centre sur les 2 colonnes)
    desig_cx = content_x + col_width * 3.0 + col_width  # centre des 2 colonnes
    _txt("DESIGNATION",  desig_cx, y_top - 6.0,  h=_fit_text_height("DESIGNATION", (2.0 * col_width) - 6.0), align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)
    _txt(designation,    desig_cx, y_top - 15.0, h=_fit_text_height(designation, (2.0 * col_width) - 6.0), align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)

    # ---------------------------------------------------------------
    # SEPARATEURS VERTICAUX
    # Haut (col_y_split -> y_top)  : cols 1, 2, 3   (col 4 absent = fusion DESIGNATION)
    # Bas  (y_bottom -> col_y_split): cols 1, 2, 3, 4 (tous presents)
    # ---------------------------------------------------------------
    try:
        for idx in range(1, top_cols):
            x_sep = content_x + col_width * idx
            if idx < top_cols - 1:
                # Colonne presente sur toute la hauteur
                layout.add_line((x_sep, y_bottom), (x_sep, y_top), dxfattribs={"layer": layer_tb})
            else:
                # Derniere colonne : trait uniquement en bas (DESIGNATION fusionnee en haut)
                layout.add_line((x_sep, y_bottom), (x_sep, col_y_split), dxfattribs={"layer": layer_tb})
    except Exception:
        pass

    # ---------------------------------------------------------------
    # LIGNE DU BAS : ECHELLE | FEUILLET | QUANTITE | CLIENT/VER | triangles
    # ---------------------------------------------------------------
    def _field(label, value, col_idx):
        cx = content_x + col_width * col_idx + col_width * 0.5
        _txt(label, cx, col_y_split - (col_y_split - y_bottom) * 0.30,
               h=_fit_text_height(label, col_width - 6.0),
             align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)
        _txt(str(value), cx, y_bottom + (col_y_split - y_bottom) * 0.40,
               h=_fit_text_height(str(value), col_width - 6.0),
             align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)

    scale_val = metadata.get("scale", "1:1")
    _field("ECHELLE", scale_val, 0)

    sheet_index = int(metadata.get("sheet_index", 1))
    total_sheets = int(metadata.get("total_sheets", 1))
    _field("FEUILLET", f"{sheet_index}/{total_sheets}", 1)

    _field("QUANTITE", qty_value, 2)

    info_text = f"CLIENT: {metadata.get('client', '')}  VER: {metadata.get('version', '')}"
    info_cx = content_x + col_width * 3.0 + col_width * 0.5
    _txt(info_text, info_cx, y_bottom + (col_y_split - y_bottom) * 0.5,
            h=_fit_text_height(info_text, col_width - 8.0, preferred=min(uniform_text_h, 2.6), min_height=1.0),
         align=TextEntityAlignment.MIDDLE_CENTER if TextEntityAlignment else None)

    # ---------------------------------------------------------------
    # CASE TRIANGLES : col 4 (seule cellule, separateur deja trace ci-dessus)
    # Triangles empiles verticalement, pointe vers le bas
    # ---------------------------------------------------------------
    tri_cell_x0 = content_x + col_width * 4.0
    tri_cell_h = col_y_split - y_bottom
    tri_s = 2.0
    tri_cx = tri_cell_x0 + 4.0
    txt_x  = tri_cx + tri_s + 2.5
    small_h = min(uniform_text_h, 2.2)

    tri_y_top = y_bottom + tri_cell_h * 0.72
    layout.add_lwpolyline(
        [(tri_cx, tri_y_top - tri_s), (tri_cx - tri_s, tri_y_top + tri_s),
         (tri_cx + tri_s, tri_y_top + tri_s), (tri_cx, tri_y_top - tri_s)],
        dxfattribs={"layer": layer_sym, "color": 7},
    )
    _txt("corps de meuble inferieur", txt_x, tri_y_top, h=small_h,
         align=TextEntityAlignment.MIDDLE_LEFT if TextEntityAlignment else None)

    tri_y_bot = y_bottom + tri_cell_h * 0.28
    layout.add_solid(
        [(tri_cx, tri_y_bot - tri_s), (tri_cx - tri_s, tri_y_bot + tri_s),
         (tri_cx + tri_s, tri_y_bot + tri_s)],
        dxfattribs={"layer": layer_sym, "color": 7},
    )
    layout.add_lwpolyline(
        [(tri_cx, tri_y_bot - tri_s), (tri_cx - tri_s, tri_y_bot + tri_s),
         (tri_cx + tri_s, tri_y_bot + tri_s), (tri_cx, tri_y_bot - tri_s)],
        dxfattribs={"layer": layer_sym, "color": 7},
    )
    _txt("avant du corps de meuble", txt_x, tri_y_bot, h=small_h,
         align=TextEntityAlignment.MIDDLE_LEFT if TextEntityAlignment else None)

    return True


# Backward compatibility alias
def add_cartouche(*args, **kwargs):
    return add_title_block(*args, **kwargs)
