with open(r'c:\Users\tzvakasikwa\OneDrive - CBZ Bank Limited\Documents\GitHub\connectlink\ConnectLink.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
for i in range(7595, 7610):
    print(f'Line {i+1}: indent={len(lines[i])-len(lines[i].lstrip())} | {lines[i].rstrip()[:80]}')
print('---')
for i in range(7665, 7690):
    print(f'Line {i+1}: indent={len(lines[i])-len(lines[i].lstrip())} | {lines[i].rstrip()[:80]}')
print('---')
for i in range(8075, 8110):
    print(f'Line {i+1}: indent={len(lines[i])-len(lines[i].lstrip())} | {lines[i].rstrip()[:80]}')
