def create_database(operations):
    """Every data item that shows up in the history becomes a variable starting at 0."""
    return {op.item: 0 for op in operations if op.item}
