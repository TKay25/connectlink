try:
    with open(r'c:\Users\tzvakasikwa\OneDrive - CBZ Bank Limited\Documents\GitHub\connectlink\ConnectLink.py', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    print(f"File has {len(lines)} lines")
    for i in range(7659, 7690):
        line = lines[i].rstrip()
        indent = len(lines[i]) - len(lines[i].lstrip())
        print(f'Line {i+1}: indent={indent} | {line[:80]}')
except Exception as e:
    print(f"Error: {e}")
