with open('.dbenv', 'rb') as f:
    content = f.read().decode('utf-8', errors='ignore')
    lines = content.splitlines()
    for i, line in enumerate(lines):
        # We use repr() to see hidden characters
        # And we use pipes | to see spaces at ends
        print(f"Line {i+1:2}: |{line}|")
        if line.endswith(' '):
            print(f"  --> WARNING: Line {i+1} has a trailing space!")
        if line.startswith(' '):
            print(f"  --> WARNING: Line {i+1} has a leading space!")
