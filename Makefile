

default: clear pdf

all: clear pdf output

clear:
	rm -rf output/*

pdf:
	# lualatex  -synctex=1 -interaction=nonstopmode -file-line-error --shell-escape glorybound
	latexmk -lualatex --shell-escape -interaction=nonstopmode glorybound

output: copy postprocess

copy:
	cp glorybound.pdf output/cards.pdf

postprocess:
	python postprocess.py
