import time
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Listen for and print console messages
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    try:
        # Navigate to the frontend URL
        page.goto("http://localhost:5174", timeout=30000)

        # The app should automatically sign in anonymously and render the main layout.
        # Wait for a unique element from the main layout to ensure we've logged in.
        header_title = page.get_by_role("heading", name="LiveAgents")
        expect(header_title).to_be_visible(timeout=20000)
        print("Successfully loaded main layout after anonymous login.")

        # Since the backend is not running, the connection should fail.
        # We expect to see the "Disconnected" status.
        # The "Connecting" state might be too brief to catch reliably, so we'll wait for the final disconnected state.

        disconnected_badge = page.get_by_text("Disconnected")
        expect(disconnected_badge).to_be_visible(timeout=10000)
        print("Successfully saw 'Disconnected' status.")

        # Also check for the WifiOff icon
        expect(page.locator("svg.lucide-wifi-off")).to_be_visible()
        print("Successfully saw WifiOff icon.")

        # Navigate to the console page to check for the message
        page.get_by_role("link", name="Chat").click()
        expect(page).to_have_url("http://localhost:5174/console")

        # The chat should now show the disconnected message from our other change
        # I need to re-implement the chat message change first.
        # For now, I will just verify the header icon and text.

        # Take a screenshot of the disconnected state
        page.screenshot(path="jules-scratch/verification/disconnected_status.png")
        print("Successfully took screenshot of the page with disconnected status.")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="jules-scratch/verification/error.png")
        # Print page content for debugging
        print("\n--- Page HTML ---")
        try:
            print(page.content())
        except Exception as content_error:
            print(f"Could not get page content: {content_error}")
        print("--- End Page HTML ---")


    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)
