// Native Typst layout for editable answer text, formulas, tables and figures.
#import "@preview/mitex:0.2.7": mitex
#let render-nodes(nodes, md) = {
  let render(children) = render-nodes(children, md)
  for n in nodes {
    if n.kind == "text" { text(n.value) }
    else if n.kind == "markdown" {
      md(n.value, (:)); v(7pt, weak: false)
    }
    else if n.kind == "math" { mitex(n.value, block: n.at("block", default: false)) }
    else if n.kind == "p" { block(render(n.children)); v(7pt, weak: false) }
    else if n.kind == "group" { render(n.children) }
    else if n.kind == "strong" { strong(render(n.children)) }
    else if n.kind == "em" { emph(render(n.children)) }
    else if n.kind == "sup" { super(typographic: false, render(n.children)) }
    else if n.kind == "sub" { sub(typographic: false, render(n.children)) }
    else if n.kind == "overline" { overline(render(n.children)) }
    else if n.kind == "br" { linebreak() }
    else if n.kind == "fraction" { math.equation(math.frac(render(n.top), render(n.bottom))) }
    else if n.kind == "matrix" { align(center, math.equation(math.mat(delim: "[", ..n.rows.map(row => row.map(render))))) }
    else if n.kind == "code" {
      if n.block {
        block(width: 100%, breakable: true, above: 8pt, below: 12pt,
          raw(n.value, block: true, lang: n.lang))
      } else { raw(n.value, block: false) }
    }
    else if n.kind == "image" {
      align(center, block(breakable: false, above: 8pt, below: 10pt,
        image(n.path, width: n.width * 1mm, height: n.height * 1mm, fit: "contain")))
    }
    else if n.kind == "table" {
      block(above: 8pt, below: 12pt, {
        set text(size: n.at("font_size", default: 10) * 1pt)
        set par(leading: .4em, spacing: 3pt)
        table(columns: (1fr,) * n.columns, stroke: .45pt, inset: 4pt,
          ..n.cells.map(c => table.cell(x: c.x, y: c.y, colspan: c.colspan, rowspan: c.rowspan,
            fill: if c.header { luma(95%) } else { none }, render(c.children))))
      })
    }
    else if n.kind == "list" {
      set list(spacing: 7pt)
      set enum(spacing: 7pt)
      if n.ordered { enum(..n.items.map(render)) } else { list(..n.items.map(render)) }
    }
    else if n.kind == "heading" {
      block(sticky: true, above: 10pt, below: 8pt, strong(render(n.children)))
    }
    else { panic("Unknown answer node: " + n.kind) }
  }
}
