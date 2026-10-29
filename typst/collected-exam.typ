// Standalone renderer for the paired, unverified source edition.
// Content is data, never evaluated as Typst code.
#let serif = sys.inputs.at("serif-font", default: "Songti SC")
#let sans = sys.inputs.at("sans-font", default: "Heiti SC")
#let mono = "DejaVu Sans Mono"

#let render(nodes) = {
  for n in nodes {
    if n.kind == "text" { text(n.value) }
    else if n.kind == "p" { block(above: 3pt, below: 4pt, render(n.children)) }
    else if n.kind == "group" { render(n.children) }
    else if n.kind == "strong" { strong(render(n.children)) }
    else if n.kind == "em" { emph(render(n.children)) }
    else if n.kind == "sup" { super(typographic: false, size: .7em, baseline: -.4em, render(n.children)) }
    else if n.kind == "sub" { sub(typographic: false, size: .7em, baseline: .2em, render(n.children)) }
    else if n.kind == "overline" { overline(render(n.children)) }
    else if n.kind == "br" { linebreak() }
    else if n.kind == "fraction" {
      math.equation(block: false, math.frac(render(n.top), render(n.bottom)))
    }
    else if n.kind == "matrix" {
      math.equation(block: false, math.mat(delim: "[", ..n.rows.map(row => row.map(render))))
    }
    else if n.kind == "code" {
      if n.block {
        block(width: 100%, breakable: true, inset: (left: 5pt, top: 4pt, bottom: 4pt),
          stroke: (left: .6pt + luma(65%)), {
            set text(font: (mono, serif), size: 8pt)
            raw(n.value, block: true, lang: n.lang)
          })
      } else { text(font: (mono, serif), size: 9pt, raw(n.value)) }
    }
    else if n.kind == "image" {
      align(center, block(breakable: false, above: 4pt, below: 5pt,
        image(n.path, width: n.width * 1mm, height: n.height * 1mm, fit: "contain")))
    }
    else if n.kind == "table" {
      block(above: 5pt, below: 6pt, {
        set text(size: 8.8pt)
        table(columns: (1fr,) * n.columns, stroke: .4pt, inset: 3.5pt,
          ..n.cells.map(c => table.cell(x: c.x, y: c.y, colspan: c.colspan, rowspan: c.rowspan,
            fill: if c.header { luma(94%) } else { none },
            render(c.children))))
      })
    }
    else if n.kind == "list" {
      if n.ordered { enum(..n.items.map(render)) } else { list(..n.items.map(render)) }
    }
    else if n.kind == "heading" {
      block(sticky: true, above: 6pt, below: 3pt, text(weight: "bold", render(n.children)))
    }
    else { panic("Unknown node: " + n.kind) }
  }
}

#let section(body) = block(sticky: true, above: 9pt, below: 8pt,
  text(font: sans, size: 13pt, weight: "bold", body))

#let cover(paper, answers) = {
  text(font: sans, size: 10pt)[408 / 对照整理版 / 2026-10-29]
  v(28mm)
  text(font: sans, size: 30pt, weight: "bold")[#paper.year]
  v(8mm)
  text(font: sans, size: 22pt, weight: "bold")[计算机学科专业基础综合]
  v(7mm)
  text(font: sans, size: 18pt)[#if answers { "参考答案册" } else { "试题册" }]
  v(12mm)
  line(length: 100%, stroke: .8pt)
  v(8mm)
  [40 道单项选择题 · 7 道综合应用题]
  parbreak()
  [180 分钟 · 150 分 · A4 打印]
  v(1fr)
  pagebreak()
}

#let question(q) = context {
  let content = [
    #block(sticky: true, below: 3pt, text(font: sans, weight: "bold")[#q.number. #h(1mm)（#q.score 分）])
    #render(q.stem)
    #if q.options.len() > 0 {
      let columns = q.option_columns
      grid(columns: (1fr,) * columns, column-gutter: 5mm, row-gutter: 4pt,
        ..q.options.map(o => grid(columns: (5mm, 1fr), strong(o.label + "."), render(o.content))))
    }
  ]
  let height = measure(block(width: 166mm, content)).height
  block(width: 100%, breakable: height > 225mm, below: 12pt, content)
}

#let answers-body(paper) = {
  section([一、选择题答案])
  v(5mm)
  for group in range(4) {
    table(columns: (1fr,) * 10, inset: 5pt, stroke: .4pt, align: center,
      ..range(group * 10, group * 10 + 10).map(i => text(weight: "bold")[#(i+1)]),
      ..paper.questions.slice(group * 10, group * 10 + 10).map(q => text(size: 12pt, q.answer_choice)))
    v(4mm)
  }
  v(9mm)
  [选择题的完整解析未包含在采集来源中；此处未补写或推测解析。]
  pagebreak()
  section([二、综合应用题参考解答])
  for q in paper.questions.filter(q => q.number >= 41) {
    block(sticky: true, above: 9pt, below: 6pt,
      text(font: sans, size: 12pt, weight: "bold")[第 #q.number 题（#q.score 分） · #q.subject])
    render(q.answer)
    v(6pt)
  }
}

#let exam(paper) = {
  let answers = sys.inputs.at("mode", default: "questions") == "answers"
  set document(title: str(paper.year) + " 年 408 " + if answers { "参考答案册" } else { "试题册" }, author: "408 资料整理")
  set page(paper: "a4", margin: (left: 22mm, right: 22mm, top: 20mm, bottom: 19mm),
    header: context if counter(page).get().first() > 1 {
      set text(size: 8pt)
      grid(columns: (1fr, 1fr), [#paper.year 年 408 · 对照整理版],
        align(right)[#if answers { "参考答案册" } else { "试题册" }])
      v(2mm)
      line(length: 100%, stroke: .4pt)
    },
    footer: context align(center, text(size: 8.5pt)[第 #counter(page).display() 页 / 共 #counter(page).final().first() 页]),
  )
  set text(font: (serif, "New Computer Modern Math"), size: 10.5pt, lang: "zh", fill: black)
  set par(justify: true, leading: .55em, spacing: 5pt)
  set enum(indent: 1em, body-indent: .5em)
  set list(indent: 1em, body-indent: .5em)
  set raw(theme: none)
  cover(paper, answers)
  if answers { answers-body(paper) }
  else {
    section([一、单项选择题])
    [第 1—40 题，每题 2 分，共 80 分。每题只有一项最符合题目要求。]
    v(5pt)
    for q in paper.questions {
      if q.number == 41 { section([二、综合应用题（共 70 分）]) }
      question(q)
    }
  }
}
