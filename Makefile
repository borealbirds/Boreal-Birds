.PHONY: all build-docs check-integrity clean help

# Default target run when typing 'make'
all: build-docs

## build-docs: Validate the repository, regenerate API references, and compile the Quarto site.
build-docs: check-integrity clean
	@echo "Running quartodoc build..."
	quartodoc build --config docs/_quarto.yml
	@echo "Compiling Quarto website..."
	quarto render docs

## check-integrity: Validate local modules, content references, and paired media assets.
check-integrity:
	python src/check_repo_integrity.py

## clean: Remove auto-generated quartodoc API reference files.
clean:
	@echo "Clearing docs/reference/..."
	rm -rf docs/reference

## help: Show available commands.
help:
	@echo "Available commands:"
	@sed -n 's/^##//p' $(MAKEFILE_LIST) | column -t -s ':' | sed -e 's/^/ /'
