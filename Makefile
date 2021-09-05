

default: clear pdf

clear:
	rm -f frames/*

pdf:
	# lualatex  -synctex=1 -interaction=nonstopmode -file-line-error --shell-escape glorybound
	latexmk -lualatex --shell-escape -interaction=nonstopmode glorybound
