#import "@preview/cmarker:0.1.10"
#import "@preview/mitex:0.2.7": mitex
#import "answer-content.typ": render-nodes

// Shared print layout for annual papers, answer sheets and solutions.
#let serif = sys.inputs.at("serif-font", default: "Noto Serif CJK SC")
#let sans = sys.inputs.at("sans-font", default: "Noto Sans CJK SC")
#let rule = 0.55pt + black

#let render(source, figures) = cmarker.render(
  source, math: mitex, raw-typst: false, smart-punctuation: false,
  set-document-title: false,
  scope: (image: (path, ..args) => {
    let size = figures.at(path)
    align(center, block(inset: (top: 3pt, bottom: 4pt),
      image(path, width: size.width * 1mm, height: size.height * 1mm, fit: "contain")))
  }),
)

#let identity() = {
  grid(columns: (20mm, 1fr), rows: (10mm, 10mm), stroke: rule,
    align: left + horizon, inset: 5pt,
    [考生姓名], [], [考生编号],
    grid(columns: (1fr,) * 15, stroke: (left: rule), ..range(15).map(_ => box(height: 7mm))),
  )
}

#let section-title(title, detail) = block(width: 100%, sticky: true, above: 10pt, below: 9pt)[
  #text(font: sans, size: 12pt, weight: "bold", title)
  #v(3pt)
  #text(size: 10pt, detail)
]

#let choice-grid(q, figures) = {
  let items = q.options.enumerate().map(((i, body)) => grid(
    columns: (5mm, 1fr), column-gutter: 0pt,
    text(font: "Libertinus Serif", weight: "bold")[#str.from-unicode(65 + i).],
    render(body, figures),
  ))
  grid(columns: (1fr,) * q.option_columns, column-gutter: 9mm, row-gutter: 9pt, ..items)
}

#let question(q, figures) = context {
  let content = grid(columns: (7mm, 1fr), column-gutter: 0pt,
    text(weight: "bold")[#q.number.],
    [
      #render(q.display_body, figures)
      #if q.options.len() > 0 {
        v(9pt)
        choice-grid(q, figures)
      }
    ],
  )
  let height = measure(block(width: 166mm, content)).height
  block(width: 100%, breakable: height > 224mm, above: 0pt,
    below: if q.number <= 40 { 20pt } else { 16pt }, content)
}

#let paper-heading(paper, answers: false) = {
  align(center)[
    #text(font: sans, size: 16pt, weight: "bold")[#paper.year 年全国硕士研究生招生考试]
    #v(5mm)
    #text(font: sans, size: 18pt, weight: "bold")[计算机学科专业基础综合]
    #v(4mm)
    #if answers {
      text(size: 12pt)[参考答案与解析]
    } else {
      text(size: 10.5pt)[科目代码：408 #h(8mm) 考试时间：180 分钟 #h(8mm) 满分：150 分]
    }
  ]
  v(5mm)
  line(length: 100%, stroke: .7pt)
  v(3mm)
}

#let answer-body(q, figures) = {
  if "nodes" in q { render-nodes(q.nodes, render) } else { render(q.body, figures) }
}

#let solutions(paper) = {
  paper-heading(paper, answers: true)
  section-title([一、单项选择题答案], [第 1—40 题，每小题 2 分，共 80 分。])
  for group in range(4) {
    table(columns: (1fr,) * 10, inset: 5pt, stroke: .45pt, align: center,
      ..range(group * 10, group * 10 + 10).map(i => text(weight: "bold")[#(i+1)]),
      ..paper.answers.slice(group * 10, group * 10 + 10).map(q => text(size: 11pt, q.choice)))
    v(4mm)
  }
  section-title([综合应用题分值], [第 41—47 题，共 70 分。])
  table(columns: (1fr,) * 7, inset: 5pt, stroke: .45pt, align: center,
    ..range(41, 48).map(n => [第 #n 题]), ..paper.essay_scores.map(s => [#s 分]))
  if paper.answers.slice(0, 40).any(q => q.body != "" or "nodes" in q) {
    pagebreak()
    heading(level: 1, outlined: true)[选择题解析]
    for q in paper.answers.slice(0, 40) {
      if q.body != "" or "nodes" in q {
        if "nodes" in q and q.number > 1 and calc.rem(q.number - 1, 8) == 0 {
          pagebreak()
          heading(level: 1, outlined: false)[选择题解析 · 第 #q.number—#(q.number + 7) 题]
        }
        block(breakable: false, above: 3pt, below: 14pt)[
          #block(sticky: true, below: 6pt, text(font: sans, weight: "bold")[#q.number. #h(2mm)答案：#q.choice])
          #v(5pt, weak: false)
          #answer-body(q, paper.figures)
        ]
        v(12pt, weak: false)
      }
    }
  }
  for q in paper.answers.slice(40) {
    pagebreak()
    if q.number == 41 {
      heading(level: 1, outlined: true)[综合应用题解析]
      text(size: 10pt)[第 41—47 题，共 70 分。]
      v(7pt)
    }
    heading(level: 2, outlined: true)[#q.number.（#paper.essay_scores.at(q.number - 41) 分）]
    v(10pt, weak: false)
    answer-body(q, paper.figures)
  }
}

#let answer-sheet(paper) = {
  align(center, text(font: sans, size: 17pt, weight: "bold")[#paper.year 年 408 · 模拟答题纸])
  v(8mm)
  identity()
  section-title([一、单项选择题], [第 1—40 题，每题 2 分，共 80 分。请清晰填涂，每题限选一项。])
  v(5mm)
  grid(columns: (1fr,) * 4, column-gutter: 7mm, row-gutter: 9mm,
    ..range(8).map(group => block(breakable: false)[
      #for i in range(5) {
        let n = group * 5 + i + 1
        grid(columns: (7mm, 1fr), align: horizon,
          text(font: "Libertinus Serif")[#if n < 10 { "0" }#n],
          grid(columns: (1fr,) * 4, column-gutter: 1.5mm,
            ..("A", "B", "C", "D").map(c => box(stroke: 0.45pt, width: 6mm, height: 4.5mm,
              align(center + horizon, text(font: "Libertinus Serif", size: 9pt, c))))),
        )
        v(4mm)
      }
    ]),
  )
  v(1fr)
  block(width: 100%, stroke: rule, inset: 5mm)[
    #text(font: sans, weight: "bold")[作答记录]
    #v(6mm)
    开始时间：#h(30mm) 结束时间：#h(25mm) 选择题得分：
    #v(7mm)
    订正日期：#h(30mm) 本次总分：
  ]
  for n in range(41, 48) {
    pagebreak()
    align(center, text(font: sans, size: 14pt, weight: "bold")[#paper.year 年 408 · 综合应用题答题区])
    v(5mm)
    grid(columns: (1fr, 1fr), [姓名：], align(right)[第 #n 题])
    v(5mm)
    block(width: 100%, height: 222mm, stroke: rule, inset: 6mm)[
      #text(font: sans, size: 12pt, weight: "bold")[#n.]
      #v(4mm)
      #text(size: 9pt, fill: luma(45%))[请标明小问序号，保留必要的分析与计算过程。]
    ]
  }
}

#let exam(paper) = {
  let mode = sys.inputs.at("mode", default: "paper")
  set document(title: paper.year + " 年 408 " + if mode == "paper" { "试题册" } else if mode == "answers" { "参考答案" } else { "答题纸" }, author: "eze-root")
  set page(paper: "a4", margin: (left: 22mm, right: 22mm, top: 19mm, bottom: 18mm),
    header: context {
      if counter(page).get().first() > 1 {
        set text(size: 8pt)
        grid(columns: (1fr, 1fr), [#paper.year 年 · 计算机学科专业基础综合], align(right)[408 · #if mode == "paper" { "试题册" } else if mode == "answers" { "参考答案" } else { "答题纸" }])
        v(2mm)
        line(length: 100%, stroke: 0.4pt)
      }
    },
    footer: context align(center, text(size: 9pt)[
      408 #h(5mm) 第 #counter(page).display() 页 #h(3mm) 共 #counter(page).final().first() 页
    ]),
  )
  set text(font: (serif, "New Computer Modern Math"), size: 12pt, lang: "zh", region: "CN", fill: black)
  set par(justify: false, leading: 0.72em, spacing: 8pt)
  set enum(indent: 0pt, body-indent: 0.5em)
  set list(indent: 0pt, body-indent: 0.5em)
  set table(stroke: 0.45pt, inset: 4pt)
  set raw(theme: none)
  set super(typographic: false, size: .7em, baseline: -.4em)
  set sub(typographic: false, size: .7em, baseline: .2em)
  show regex("([一-龥A-Za-z0-9]{1,4})?（[0-9]+分）"): it => box(it)
  show table: set text(size: 10.5pt)
  show raw: set text(font: ("DejaVu Sans Mono", serif), size: 9.5pt)
  show raw.where(block: true): set par(leading: if mode == "answers" { .65em } else { .4em })
  show raw.where(block: true): set block(breakable: mode == "answers")
  show raw.where(block: true): it => block(width: 100%, breakable: mode == "answers", inset: (left: 6pt, top: 5pt, bottom: 5pt),
    stroke: (left: 0.6pt + luma(65%)), it)
  if mode == "answer-sheet" {
    set text(size: 10.5pt)
    set par(leading: 0.6em, spacing: 5pt)
    answer-sheet(paper)
  } else if mode == "answers" {
    solutions(paper)
  } else {
    paper-heading(paper)
    section-title([一、单项选择题], [第 1—40 小题，每小题 2 分，共 80 分。下列每题给出的四个选项中，只有一项最符合题目要求。])
    for q in paper.questions {
      if q.number == 41 {
        pagebreak()
        section-title([二、综合应用题], [第 41—47 小题，共 70 分。请将答案写在配套答题纸的相应区域内。])
      } else if q.number > 41 {
        pagebreak()
      }
      if q.number == 38 {
        context {
          let tail = { for last in paper.questions.slice(37, 40) { question(last, paper.figures) } }
          let height = measure(block(width: 166mm, tail)).height
          block(breakable: height > 224mm, tail)
        }
      } else if q.number < 38 or q.number > 40 {
        question(q, paper.figures)
      }
    }

  }
}
