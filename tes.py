from playwright.sync_api import sync_playwright

with sync_playwright() as p:
       browser = p.chromium.launch(headless=False)
       page = browser.new_page()
       page.goto("https://www.tokopedia.com")
       print("Judul halaman:", page.title())
       input("Tekan Enter di sini buat nutup browser...")
       browser.close()