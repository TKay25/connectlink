from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    print('chromium at', p.chromium.executable_path)
    b = p.chromium.launch()
    pg = b.new_page()
    pg.set_content('<html><body><div id="x">hi</div></body></html>')
    print('text =', pg.inner_text('#x'))
    b.close()
print('PLAYWRIGHT_OK')
