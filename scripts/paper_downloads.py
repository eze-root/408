"""Build the local per-year download bundle."""
import zipfile


def package_downloads(folder, years):
    target = folder / '408-2009-2026-papers-and-answers.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for year in years:
            for kind in ('paper', 'answers', 'answer-sheet'):
                path = folder / f'{year}-408-{kind}.pdf'
                archive.write(path, f'{year}/{path.name}')
    return target
