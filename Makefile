

default: clear preprocess pdf

full: clear preprocess-full pdf output
 
clear:
	rm -rf output/*
	rm -f glorybound.pdf
	rm -f latex/glorybound.pdf
	rm -f latex/glorybound.tex
	find . -name '*.aux' -type f -delete
	find . -name '*.fls' -type f -delete

preprocess:
	pipenv run python main.py > latex/glorybound.tex

preprocess-full:
	pipenv run python main.py -all > latex/glorybound.tex

pdf:
	# lualatex  -synctex=1 -interaction=nonstopmode -file-line-error --shell-escape glorybound
	latexmk -lualatex --shell-escape -interaction=nonstopmode latex/glorybound
	cp glorybound.pdf latex/glorybound.pdf

output: copy postprocess

copy:
	mkdir -p output
	cp glorybound.pdf output/cards.pdf

postprocess:
	pipenv run python postprocess.py
