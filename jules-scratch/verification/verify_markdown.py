from playwright.sync_api import sync_playwright, Page, expect
import re

def test_markdown_rendering(page: Page):
    """
    This test verifies that markdown is rendered correctly in the chat.
    """
    # 1. Arrange: Go to the application.
    page.goto("http://localhost:5173/")

    # Wait for the email input to be visible
    email_input = page.get_by_label("Email")
    expect(email_input).to_be_visible()

    # Log in
    email_input.fill("test@example.com")
    page.get_by_label("Password").fill("password")
    page.get_by_role("button", name="Sign In").click()

    # Wait for navigation to the main page
    expect(page).to_have_url(re.compile(".*live"))

    # 2. Act: Send a message with markdown.
    page.get_by_placeholder("Type a message...").fill("**Hello** *world*!")
    page.get_by_role("button", name="Send").click()

    # 3. Assert: Check that the markdown is rendered correctly.
    # Assuming the last message is the one we just sent
    expect(page.locator("strong").last).to_have_text("Hello")
    expect(page.locator("em").last).to_have_text("world")

    # 4. Screenshot: Capture the final result for visual verification.
    page.screenshot(path="jules-scratch/verification/verification.png")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        test_markdown_rendering(page)
    finally:
        browser.close()
