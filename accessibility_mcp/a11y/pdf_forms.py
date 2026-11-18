"""AcroForm real ligado a tags Form e ParentTree, com fonte incorporada e aparencias."""
from __future__ import annotations

import io
from typing import Any

from fontTools.ttLib import TTFont  # type: ignore[import-untyped]
from PIL import ImageFont
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    ContentStream,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from .document_controls import field_label
from .document_schema import Block


def _dict(**values: Any) -> DictionaryObject:
    return DictionaryObject({NameObject('/' + key): value for key, value in values.items()})


def _numbers(values: Any) -> ArrayObject:
    return ArrayObject([FloatObject(value) for value in values])


def structure_nodes(root: Any) -> list[Any]:
    result, seen = [], set()

    def walk(node: Any) -> None:
        node = node.get_object() if hasattr(node, 'get_object') else node
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict) and id(node) not in seen:
            seen.add(id(node))
            if node.get('/S'):
                result.append(node)
            if '/K' in node:
                walk(node['/K'])
    walk(root)
    return result


def prepare_lists(writer: Any) -> None:
    """Chromium liga Link direto a LI em sumarios; conserva o link dentro de LBody."""
    for item in structure_nodes(writer.root_object['/StructTreeRoot']):
        if item.get('/S') != '/LI':
            continue
        children = item.get('/K', ArrayObject())
        children = children if isinstance(children, list) else [children]
        wrong = [child for child in children if isinstance(child.get_object(), dict) and child.get_object().get('/S') not in ('/Lbl','/LBody')]
        if not wrong:
            continue
        body = _dict(Type=NameObject('/StructElem'), S=NameObject('/LBody'), P=item.indirect_reference, K=ArrayObject(wrong))
        body_ref = writer._add_object(body)
        for child in wrong:
            child.get_object()[NameObject('/P')] = body_ref
        item[NameObject('/K')] = ArrayObject([child for child in children if child not in wrong] + [body_ref])


def _rectangles(page: Any, writer: Any, targets: set[int]) -> dict[int, list[float]]:
    """Limites da pintura marcada pelo Chromium, na pagina PDF efetiva (inclui paginacao)."""
    matrix = [1., 0., 0., 1., 0., 0.]
    stack, marks = [], []
    path_points: list[tuple[float, float]] = []
    points: dict[int, list[tuple[float, float]]] = {key: [] for key in targets}
    for args, op in ContentStream(page['/Contents'], writer).operations:
        if op == b'q':
            stack.append(matrix[:])
        elif op == b'Q' and stack:
            matrix = stack.pop()
        elif op == b'cm':
            a, b, c, d, e, f = matrix
            g, h, i, j, k, l = (float(v) for v in args)
            matrix = [a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*l+e, b*k+d*l+f]
        elif op in (b'BDC', b'BMC'):
            marks.append(int(args[1]['/MCID']) if op == b'BDC' and isinstance(args[1], dict) and '/MCID' in args[1] else None)
        elif op == b'EMC' and marks:
            marks.pop()
        if op in (b're', b'm', b'l', b'c', b'v', b'y'):
            coords = [float(value) for value in args]
            if op == b're':
                x, y, width, height = coords
                coords = [x, y, x+width, y+height]
            a, b, c, d, e, f = matrix
            for x, y in zip(coords[::2], coords[1::2]):
                path_points.append((a*x+c*y+e, b*x+d*y+f))
        if op in (b'f', b'F', b'f*', b'S', b's', b'B', b'B*', b'b', b'b*', b'n'):
            if op != b'n' and marks and marks[-1] in targets:
                points[marks[-1]].extend(path_points)
            # re W n apenas recorta: nao e a area pintada de um campo.
            path_points.clear()
    result = {}
    for key, values in points.items():
        if values:
            xs, ys = zip(*values)
            result[key] = [min(xs), min(ys), max(xs), max(ys)]
    return result


def _font(writer: Any) -> Any:
    # Aileron e distribuida com Pillow sob licenca aberta; nao copia fontes do Windows.
    bundled_font = ImageFont.load_default(size=11)
    assert isinstance(bundled_font, ImageFont.FreeTypeFont)
    resource = bundled_font.path
    assert isinstance(resource, io.BytesIO)
    data = resource.getvalue()
    font = TTFont(io.BytesIO(data))
    units = font['head'].unitsPerEm
    scale = 1000 / units
    cmap = font.getBestCmap()
    widths = []
    unicode_pairs = []
    for code in range(32, 256):
        try:
            char = bytes([code]).decode('cp1252')
        except UnicodeDecodeError:
            char = '?'
        glyph = cmap.get(ord(char), '.notdef')
        widths.append(font['hmtx'].metrics[glyph][0] * scale)
        unicode_pairs.append(f'<{code:02X}> <{ord(char):04X}>')
    program = DecodedStreamObject()
    program.set_data(data)
    program[NameObject('/Length1')] = NumberObject(len(data))
    descriptor = _dict(Type=NameObject('/FontDescriptor'), FontName=NameObject('/Aileron-Regular'), Flags=NumberObject(32),
                       FontBBox=_numbers([getattr(font['head'], key)*scale for key in ('xMin','yMin','xMax','yMax')]),
                       ItalicAngle=NumberObject(0), Ascent=FloatObject(font['hhea'].ascent*scale), Descent=FloatObject(font['hhea'].descent*scale),
                       CapHeight=FloatObject(font['hhea'].ascent*scale), StemV=NumberObject(80), FontFile2=writer._add_object(program))
    mapping = DecodedStreamObject()
    chunks = []
    for index in range(0, len(unicode_pairs), 80):
        chunk = unicode_pairs[index:index+80]
        chunks.append(f'{len(chunk)} beginbfchar\n' + '\n'.join(chunk) + '\nendbfchar')
    mapping.set_data(('/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /AileronUnicode def\n/CMapType 2 def\n1 begincodespacerange\n<00> <FF>\nendcodespacerange\n'+'\n'.join(chunks)+'\nendcmap\nCMapName currentdict /CMap defineresource pop\nend end').encode('ascii'))
    return writer._add_object(_dict(Type=NameObject('/Font'), Subtype=NameObject('/TrueType'), BaseFont=NameObject('/Aileron-Regular'),
                                    FirstChar=NumberObject(32), LastChar=NumberObject(255), Widths=_numbers(widths),
                                    FontDescriptor=writer._add_object(descriptor), Encoding=NameObject('/WinAnsiEncoding'), ToUnicode=writer._add_object(mapping)))


def _appearance(writer: Any, width: float, height: float, font: Any, value: str = '', checked: bool = False) -> Any:
    stream = DecodedStreamObject()
    content = f'q 1 1 1 rg 0 0 {width} {height} re f 0 0 0 RG 1 w 0.5 0.5 {width-1} {height-1} re S\n'
    if checked:
        content += f'2 w 3 {height/2} m {width/2} 3 l {width-3} {height-3} l S\n'
    if value:
        font_metrics = ImageFont.load_default(size=11)
        lines = value.splitlines() or ['']
        if any(font_metrics.getlength(line) > width-8 for line in lines) or len(lines)*14 > height-4:
            raise ValueError('O valor inicial do campo nao cabe na area; reduza o valor ou use multiline.')
        for index, line in enumerate(lines):
            try:
                encoded = line.encode('cp1252').hex()
            except UnicodeEncodeError as exc:
                raise ValueError('A aparencia inicial de campos PDF suporta caracteres Windows-1252; o texto do documento aceita Unicode.') from exc
            content += f'BT /Fform 11 Tf 0 g 4 {height-14-index*14} Td <{encoded}> Tj ET\n'
    content += 'Q'
    stream.set_data(content.encode('ascii'))
    stream.update(_dict(Type=NameObject('/XObject'), Subtype=NameObject('/Form'), BBox=_numbers([0,0,width,height]),
                        Resources=_dict(Font=_dict(Fform=font))))
    return writer._add_object(stream)


def add_forms(writer: Any, fields: list[Block], portuguese: bool) -> None:
    if not fields:
        return
    root = writer.root_object['/StructTreeRoot']
    tags = [node for node in structure_nodes(root) if node['/S'] == '/Form']
    if len(tags) != len(fields):
        raise ValueError('A estrutura impressa de campos diverge dos controles solicitados.')
    parent_values: dict[int, Any] = {}

    def collect(tree: Any) -> None:
        tree = tree.get_object()
        values = tree.get('/Nums', [])
        for key, val in zip(values[::2], values[1::2]):
            parent_values[int(key)] = val
        for child in tree.get('/Kids', []):
            collect(child)
    collect(root['/ParentTree'])
    next_key = max(parent_values, default=-1) + 1
    font = _font(writer)
    canonical_fields = ArrayObject()
    acro = _dict(Fields=canonical_fields, NeedAppearances=BooleanObject(False), DA=TextStringObject('/Fform 11 Tf 0 g'), DR=_dict(Font=_dict(Fform=font)))
    writer.root_object[NameObject('/AcroForm')] = writer._add_object(acro)
    for block, tag in zip(fields, tags):
        page_ref = tag['/Pg'].indirect_reference
        page = next(page for page in writer.pages if page.indirect_reference == page_ref)
        old_k = tag.get('/K')
        if not isinstance(old_k, int):
            raise TypeError('Campo impresso sem identificador de pintura reconhecido.')
        rects = _rectangles(page, writer, {int(old_k)})
        if int(old_k) not in rects:
            raise ValueError('Nao foi possivel localizar a area do campo na pagina PDF.')
        rect = rects[int(old_k)]
        width, height = rect[2]-rect[0], rect[3]-rect[1]
        expected_height = 20 if block.field_type == 'checkbox' else 76 if block.multiline else 30
        if abs(height-expected_height) > 1 or width <= 0 or width > float(page.mediabox.width):
            raise ValueError('A geometria medida do campo diverge do controle impresso; arquivo nao concluido.')
        label = field_label(block, portuguese)
        flags = (2 if block.required else 0) | (4096 if block.multiline else 0) | (131072 if block.field_type == 'choice' else 0)
        widget = _dict(Type=NameObject('/Annot'), Subtype=NameObject('/Widget'), FT=NameObject({'text':'/Tx','checkbox':'/Btn','choice':'/Ch'}[block.field_type]),
                       T=TextStringObject(block.field_name), TU=TextStringObject(label+'. '+block.help_text),
                       F=NumberObject(4), Ff=NumberObject(flags), Rect=_numbers(rect), P=page_ref, StructParent=NumberObject(next_key),
                       DA=TextStringObject('/Fform 11 Tf 0 g'))
        if block.field_type == 'checkbox':
            state = NameObject('/Yes' if block.checked else '/Off')
            widget.update(_dict(V=state, DV=state, AS=state, AP=_dict(N=_dict(Off=_appearance(writer,width,height,font), Yes=_appearance(writer,width,height,font,checked=True)))))
        else:
            widget.update(_dict(V=TextStringObject(block.value), DV=TextStringObject(block.value), AP=_dict(N=_appearance(writer,width,height,font,block.value))))
            if block.field_type == 'choice':
                widget[NameObject('/Opt')] = ArrayObject([TextStringObject(option) for option in block.options])
        ref = writer._add_object(widget)
        page.setdefault(NameObject('/Annots'), ArrayObject()).append(ref)
        canonical_fields.append(ref)
        tag[NameObject('/K')] = ArrayObject([old_k, _dict(Type=NameObject('/OBJR'), Obj=ref, Pg=page_ref)])
        tag[NameObject('/Alt')] = TextStringObject(label+'. '+block.help_text)
        tag[NameObject('/A')] = _dict(O=NameObject('/PrintField'), Role=NameObject('/cb' if block.field_type == 'checkbox' else '/tv'), Desc=TextStringObject(label+'. '+block.help_text))
        parent_values[next_key] = tag.indirect_reference
        next_key += 1
    nums = ArrayObject()
    for key, val in sorted(parent_values.items()):
        nums.extend([NumberObject(key), val])
    root[NameObject('/ParentTree')] = writer._add_object(_dict(Nums=nums))
    root[NameObject('/ParentTreeNextKey')] = NumberObject(next_key)
