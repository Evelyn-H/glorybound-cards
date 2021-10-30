

default: clear pdf

all: clear pdf output

clear:
	rm -rf output/*
	rm -f glorybound1.pdf
	rm -f latex/glorybound1.pdf

pdf:
	# lualatex  -synctex=1 -interaction=nonstopmode -file-line-error --shell-escape glorybound
	latexmk -lualatex --shell-escape -interaction=nonstopmode latex/glorybound1
	cp glorybound1.pdf latex/glorybound1.pdf

output: copy postprocess

copy:
	mkdir -p output
	cp glorybound.pdf output/cards.pdf

postprocess:
	python3 postprocess.py
