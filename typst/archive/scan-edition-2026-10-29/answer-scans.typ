#import "exam-template.typ": render, paper-heading, section-title, serif, sans

#let correction(source, gutter: 6pt) = {
  for part in read(source).split("\n\n") {
    render(part, (:))
    v(gutter, weak: false)
  }
}

#let answer-scans(paper) = {
  let scans = paper.answer_scans
  set document(title: paper.year + " 年 408 答案与解析", author: "eze-root")
  set page(paper: "a4", margin: (x: 22mm, top: 19mm, bottom: 18mm),
    footer: context align(center, text(size: 9pt)[#paper.year 年 408 · 答案与解析 #h(5mm) #counter(page).display() / #counter(page).final().first()]))
  set text(font: (serif, "New Computer Modern Math"), size: 12pt, lang: "zh", region: "CN")
  set par(leading: .65em, spacing: 8pt)
  set raw(theme: none)
  show raw: set text(font: ("DejaVu Sans Mono", serif), size: 9.5pt)
  show raw.where(block: true): set par(leading: .35em)
  show heading.where(level: 2): set text(font: sans, size: 12pt)
  paper-heading(paper, answers: true)
  heading(level: 1, outlined: true)[选择题答案速查]
  text(size: 10pt)[第 1—40 题，每题 2 分，共 80 分。]
  v(4mm)
  for group in range(4) {
    table(columns: (1fr,) * 10, inset: 5pt, stroke: .45pt, align: center,
      ..range(group * 10, group * 10 + 10).map(i => text(weight: "bold")[#(i+1)]),
      ..scans.choice_key.clusters().slice(group * 10, group * 10 + 10).map(key => text(size: 11pt, key)))
    v(3mm)
  }
  section-title([综合应用题分值], [第 41—47 题，共 70 分。])
  table(columns: (1fr,) * 7, inset: 5pt, stroke: .45pt, align: center,
    ..range(41, 48).map(n => [第 #n 题]),
    ..paper.essay_scores.map(score => [#score 分]))
  v(5mm)
  text(size: 10.5pt)[本册配套本网站 #paper.year 年试题册。后附逐题解析；PDF 书签可跳转到选择题、综合应用题。]
  if scans.notes.len() > 0 {
    section-title([本版整理], [])
    set text(size: 10pt)
    for note in scans.notes { block(below: 5pt, note) }
  }
  // Source images retain their original placement. All edits are native text
  // overlays, documented in scan-reviews.json, rather than destructive edits.
  pagebreak()
  set page(margin: (left: 12pt, right: 12pt, top: 8pt, bottom: 26pt))
  for (i, page) in scans.pages.enumerate() {
    if i > 0 { pagebreak() }
    context {
      let factor = (210mm - 24pt) / (page.width * 1pt)
      let r = page.image_rect
      block(width: 100%, height: page.height * factor * 1pt)[
        #place(top + left, dx: r.at(0)*factor*1pt, dy: r.at(1)*factor*1pt,
          image(page.path, width: (r.at(2)-r.at(0))*factor*1pt, height: (r.at(3)-r.at(1))*factor*1pt))
        #for patch in scans.patches.filter(p => p.page == page.source_page) {
          let rect = patch.rect
          let w = (rect.at(2)-rect.at(0))*factor*1pt
          let h = (rect.at(3)-rect.at(1))*factor*1pt
          let content = {
            set text(size: patch.at("font_size", default: 11)*factor*1pt)
            set par(leading: .45em, spacing: 6pt)
            if "markdown" in patch {
              show raw.where(block: true): set text(size: 11pt)
              show raw.where(block: true): set par(leading: .55em)
              correction(patch.markdown)
            }
            else if patch.at("code", default: false) { text(font: "DejaVu Sans Mono", patch.text) }
            else { patch.text }
          }
          assert(measure(block(width: w, content)).height <= h, message: "Answer correction exceeds its allotted region")
          place(top + left, dx: rect.at(0)*factor*1pt, dy: rect.at(1)*factor*1pt,
            block(width: w, height: h, fill: rgb(patch.at("fill", default: "ffffff")), content))
        }
      ]
    }
  }
  for source in scans.supplements {
    pagebreak()
    set page(margin: (x: 22mm, top: 19mm, bottom: 18mm))
    correction(source, gutter: 10pt)
  }
}
