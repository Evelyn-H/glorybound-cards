import subprocess
import asyncio

# https://www.delftstack.com/howto/python/parallel-for-loops-python/#use-the-asyncio-module-to-parallelize-the-for-loop-in-python
def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)
    return wrapped


paths={}
cards=[]

with open("page-numbers-cards.log") as file:
    for line in file:
        path, card, page = line.strip().split(" - ")
        page = int(page)
        print(path, card, page, sep=" ! ")

        cards.append((path, card, page))

        if path not in paths:
            paths[path] = (page, page)
        start = paths[path][0]
        end = page
        paths[path] = (start, end)

print(paths)


@background
def process_path(path, pages):
    start, end = pages
    subprocess.run(f"mkdir -p \"output/{path}\"", shell=True)
    subprocess.run(f"pdfjam glorybound.pdf {start}-{end} --fitpaper true -o \"output/{path}/{path}.pdf\"", shell=True)

# make pdfs per path
for path, pages in paths.items():
    process_path(path, pages)


@background
def process_card(path, card, page):
    print(f"Converting {path} - {card} to png")
    subprocess.run(f"pdftoppm -png glorybound.pdf -f {page} -singlefile -r 600 \"output/{path}/{card}\"", shell=True)
    # make the white corners transparent instead
    # https://legacy.imagemagick.org/discourse-server/viewtopic.php?t=31341
    subprocess.run(f"convert \"output/{path}/{card}.png\" -alpha set -bordercolor white -border 1  -fill none -fuzz 90% -draw \"color 0,0 floodfill\" -shave 1x1 \"output/{path}/{card}.png\"", shell=True)

    # make image with bleed area for printing
    print(f"Adding bleed to {path} - {card}")
    subprocess.run(f"mkdir -p \"output/{path}/print\"", shell=True)
    subprocess.run(f"convert \"output/{path}/{card}.png\" -resize 50% -gravity center -extent 825x1125 bleed-overlay.png -composite \"output/{path}/print/{card}.png\"", shell=True)

# make images per card
for path, card, page in cards:
    process_card(path, card, page)
   
