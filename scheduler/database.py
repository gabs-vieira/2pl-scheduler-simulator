def create_database(operations):
    return {op.item: 0 for op in operations if op.item}
