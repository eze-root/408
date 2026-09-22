#import "@preview/cmarker:0.1.10"
#import "@preview/mitex:0.2.7": mitex

// Black-and-white study edition. It deliberately contains no official barcode.
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

#let choice-grid(options, figures) = context {
  let items = options.enumerate().map(((i, body)) => [
    #text(font: "Libertinus Serif", weight: "bold")[#str.from-unicode(65 + i).]
    #h(0.25em)#render(body, figures)
  ])
  let available = 159mm
  let widest = calc.max(..items.map(it => measure(it).width))
  let cols = if widest < available / 4 - 5mm { 4 } else if widest < available / 2 - 5mm { 2 } else { 1 }
  grid(columns: (1fr,) * cols, column-gutter: 5mm, row-gutter: 4pt, ..items)
}

#let question(q, figures) = context {
  let content = grid(columns: (7mm, 1fr), column-gutter: 0pt,
    text(weight: "bold")[#q.number.],
    [
      #render(q.body, figures)
      #if q.options.len() > 0 {
        v(4pt)
        choice-grid(q.options, figures)
      }
    ],
  )
  let height = measure(block(width: 166mm, content)).height
  block(width: 100%, breakable: height > 240mm, above: 0pt,
    below: if q.number <= 40 { 8pt } else { 10pt }, content)
}

#let cover(paper) = {
  align(right, text(size: 8.5pt)[#paper.edition · 供学习模拟使用])
  v(21mm)
  align(center)[
    #text(font: sans, size: 19pt, weight: "bold")[#paper.year 年全国硕士研究生招生考试]
    #v(9mm)
    #text(font: sans, size: 22pt, weight: "bold")[计算机学科专业基础综合]
    #v(7mm)
    #text(size: 13pt)[（科目代码：408）]
    #v(12mm)
    #text(size: 11pt)[考试时间：180 分钟 #h(12mm) 满分：150 分]
  ]
  v(13mm)
  line(length: 100%, stroke: 0.8pt)
  v(9mm)
  align(center, text(font: sans, size: 13pt, weight: "bold")[作答说明])
  v(5mm)
  enum(spacing: 8pt, indent: 1.4em, body-indent: 0.6em,
    [开始作答前，请在试题册和配套答题纸上填写姓名及考生编号。],
    [单项选择题共 40 小题，每小题 2 分，共 80 分。每题只选一项，在答题纸上填写或涂黑对应选项。],
    [综合应用题共 7 小题，共 70 分。请在答题纸对应题号的区域内写出推导过程、算法或结论。],
    [建议用黑色字迹签字笔作答，使用 2B 铅笔填涂选择题。模拟考试时独立完成，结束后再核对答案。],
  )
  v(10mm)
  identity()
  v(1fr)
  text(size: 8.5pt, fill: luma(35%))[
    #paper.note  本册为重新排版的学习资料，非官方原卷影印件。
  ]
  pagebreak()
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
    复盘日期：#h(30mm) 本次总分：
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
  set document(title: paper.year + " 年 408 " + if mode == "paper" { "试题册" } else { "答题纸" }, author: "eze-root")
  set page(paper: "a4", margin: (left: 22mm, right: 22mm, top: 19mm, bottom: 18mm),
    header: context {
      if counter(page).get().first() > 1 {
        set text(size: 8pt)
        grid(columns: (1fr, 1fr), [#paper.year 年 · 计算机学科专业基础综合], align(right)[408 · #paper.edition])
        v(2mm)
        line(length: 100%, stroke: 0.4pt)
      }
    },
    footer: context align(center, text(size: 9pt)[
      408 #h(5mm) 第 #counter(page).display() 页 #h(3mm) 共 #counter(page).final().first() 页
    ]),
  )
  set text(font: serif, size: 10.5pt, lang: "zh", region: "CN", fill: black)
  set par(justify: true, leading: 0.6em, spacing: 5pt)
  set enum(indent: 0pt, body-indent: 0.5em)
  set list(indent: 0pt, body-indent: 0.5em)
  set table(stroke: 0.45pt, inset: 4pt)
  set raw(theme: none)
  show table: set text(size: 9pt)
  show raw: set text(font: "DejaVu Sans Mono", size: 8.5pt)
  show raw.where(block: true): it => block(width: 100%, inset: (left: 6pt, top: 5pt, bottom: 5pt),
    stroke: (left: 0.6pt + luma(65%)), it)
  if mode == "answer-sheet" {
    answer-sheet(paper)
  } else {
    cover(paper)
    section-title([一、单项选择题], [第 1—40 小题，每小题 2 分，共 80 分。下列每题给出的四个选项中，只有一项最符合题目要求。])
    for q in paper.questions {
      if q.number == 41 {
        v(3mm)
        section-title([二、综合应用题], [第 41—47 小题，共 70 分。请将答案写在配套答题纸的相应区域内。])
      }
      question(q, paper.figures)
    }
    v(6mm)
    align(center, text(size: 9pt)[—— 试题结束 ——])
  }
}
