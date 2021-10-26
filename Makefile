

default: clear pdf

all: clear pdf output

clear:
	rm -rf output/*
	rm -f glorybound.pdf
	# rm -f latex/glorybound.pdf

pdf:
	# lualatex  -synctex=1 -interaction=nonstopmode -file-line-error --shell-escape glorybound
	latexmk -lualatex --shell-escape -interaction=nonstopmode latex/glorybound
	cp glorybound.pdf latex/glorybound.pdf

output: copy postprocess

copy:
	mkdir -p output
	cp glorybound.pdf output/cards.pdf

postprocess:
	python3 postprocess.py
