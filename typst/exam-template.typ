#import "@preview/cmarker:0.1.10"
#import "@preview/mitex:0.2.7": mitex

#let exam(year: "", source: "") = {
  set document(
    title: year + " 年全国硕士研究生招生考试计算机学科专业基础试题",
    author: "408 学习小组",
  )
  set page(
    paper: "a4",
    margin: (x: 22mm, top: 20mm, bottom: 18mm),
    numbering: "1 / 1",
    header: context {
      if counter(page).get().first() > 1 {
        text(size: 8.5pt, fill: rgb("666666"))[
          #year 年 408 计算机学科专业基础 · 试题卷
        ]
      }
    },
    footer: context align(center)[
      #text(size: 8.5pt, fill: rgb("777777"))[
        第 #counter(page).display() 页
      ]
    ],
  )
  set text(
    font: ("Songti SC", "STSong"),
    size: 10.5pt,
    lang: "zh",
    region: "CN",
  )
  set par(justify: true, leading: 0.72em)
  set heading(numbering: none)
  set list(indent: 1.25em, body-indent: 0.55em)
  set enum(indent: 1.25em, body-indent: 0.55em)

  show heading.where(level: 1): it => {
    v(1.15em)
    text(size: 13pt, weight: "bold")[#it.body]
    v(0.45em)
  }
  show heading.where(level: 2): it => {
    v(0.9em)
    text(size: 11.5pt, weight: "bold")[#it.body]
    v(0.3em)
  }
  show image: it => align(center, block(inset: (top: 4pt, bottom: 6pt), it))
  show table: it => align(center, it)
  show raw.where(block: true): it => block(
    width: 100%,
    fill: rgb("F7F7F7"),
    inset: 8pt,
    radius: 2pt,
    it,
  )

  align(center)[
    #text(size: 15pt, weight: "bold")[#year 年全国硕士研究生招生考试]
    #v(7pt)
    #text(size: 18pt, weight: "bold")[计算机学科专业基础试题]
    #v(8pt)
    #text(size: 10.5pt)[科目代码：408]
  ]
  v(12pt)
  line(length: 100%, stroke: 0.8pt)
  v(8pt)
  align(center)[
    #text(size: 9.5pt)[考试时间 180 分钟　满分 150 分]
  ]
  v(8pt)

  cmarker.render(
    source,
    math: mitex,
    h1-level: 1,
    set-document-title: false,
    smart-punctuation: false,
    raw-typst: false,
    scope: (image: (path, ..args) => image(path, width: 72%, ..args)),
  )
}
