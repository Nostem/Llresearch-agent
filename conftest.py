# conftest.py — Project root marker for pytest
#
# Placing conftest.py here tells pytest that this directory is the root of the
# project. pytest will add this directory to sys.path automatically, which
# allows imports like `from agent.retriever import ...` to work correctly
# regardless of where pytest is invoked from.
