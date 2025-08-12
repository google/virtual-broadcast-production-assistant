import time
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Go to the login page first
    page.goto("http://localhost:5173/")

    # Wait for the "Connected" badge to appear in the header.
    # This confirms that anonymous authentication and WebSocket connection have succeeded.
    header_status_badge = page.locator('.sm\\:flex .badge:has-text("Connected")')
    expect(header_status_badge).to_be_visible(timeout=15000) # 15 seconds timeout

    # Navigate to the status page
    page.goto("http://localhost:5173/status")

    # Check that the connection is still "Connected" on the status page
    header_status_badge_on_status_page = page.locator('.sm\\:flex .badge:has-text("Connected")')
    expect(header_status_badge_on_status_page).to_be_visible()

    # Also check the main status display on the status page
    main_status_badge = page.locator('.p-6 .badge:has-text("connected")')
    expect(main_status_badge).to_be_visible()

    # Take a screenshot of the status page
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
