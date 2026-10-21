.PHONY: all results test check paper clean

all: results test check paper

results:
	python -m ppath

test:
	pytest -q

check:
	python tools/check_paper.py

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode main.tex

clean:
	cd paper && latexmk -C
