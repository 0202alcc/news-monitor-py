from playwright.sync_api import sync_playwright

class PageLoader:
    def load(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
            return html
