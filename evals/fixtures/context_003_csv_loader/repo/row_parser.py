def parse_row(line):
    name, score = line.split(",")
    return {"name": name.strip(), "score": int(score)}
