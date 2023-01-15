.PHONY: default full clean build watch render sass

default: build

clean:
	rm -rf output/*
	rm -rf build/*

sass: 
	sass styles/main.scss build/styles/main.css
 
watch: 
	sass --watch styles:build/styles

build: clean sass
	pipenv run python build.py

render: clean sass
	pipenv run python build.py --render
