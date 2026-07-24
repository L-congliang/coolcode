def build_summary(rows):
    text = ''
    for row in rows:
        text += f"{row['name']}: {row['score']}" + chr(10)
    return text
