from row_parser import parse_row


def load_scores(text):
    rows = []
    for line in text.splitlines():
        rows.append(parse_row(line))
    return rows
