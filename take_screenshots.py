"""
Take MCP Inspector screenshots for mcp-clinical-reasoner LinkedIn post.
Runs 4 tools and saves screenshots to snip1..snip4_*.png
"""
import asyncio

from playwright.async_api import async_playwright

INSPECTOR_URL = "http://localhost:6274"
OUT = "/home/linuxdev1/PracticeApps/MyAIMLProjects2026/fhir-mcp-suite"


async def wait_for_result(page):
    """Wait until Tool Result heading appears."""
    await page.wait_for_selector("h4:has-text('Tool Result')", timeout=30000)
    await page.wait_for_timeout(500)


async def run_tool(page, tool_ref, input_fields: dict):
    """Click a tool, fill inputs, run it, wait for result."""
    await page.locator(f"[ref={tool_ref}]").click()
    await page.wait_for_timeout(400)
    for placeholder, value in input_fields.items():
        page.get_by_role("textbox").filter(has_text="").nth(0)
        # Use label-based selector
        await page.locator('input, textarea').filter(
            has=page.locator(f'[placeholder*="{placeholder}"]')
        ).fill(value)
    await page.get_by_role("button", name="Run Tool").click()
    await wait_for_result(page)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(INSPECTOR_URL, wait_until="networkidle")

        # --- Connect ---
        await page.get_by_role("button", name="Connect").click()
        await page.wait_for_selector("text=Connected", timeout=15000)
        await page.wait_for_timeout(500)

        # --- List Tools ---
        await page.get_by_role("button", name="List Tools").click()
        await page.wait_for_timeout(800)

        # ====== SHOT 1: lookup_drug(ibuprofen) ======
        # Click lookup_drug in list
        await page.locator("text=lookup_drug").first.click()
        await page.wait_for_timeout(400)
        name_box = page.get_by_role("textbox", name="name_or_rxcui*")
        await name_box.fill("ibuprofen")
        await page.get_by_role("button", name="Run Tool").click()
        await wait_for_result(page)
        # Scroll result into view
        await page.evaluate("document.querySelector('h4') && document.querySelector('h4').scrollIntoView()")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUT}/snip1_lookup_drug.png")
        print("✅ snip1_lookup_drug.png")

        # ====== SHOT 2: check_drug_interactions ======
        await page.locator("text=check_drug_interactions").first.click()
        await page.wait_for_timeout(400)
        drug_box = page.get_by_role("textbox", name="drug_names*")
        await drug_box.fill('["ibuprofen", "lisinopril", "metformin"]')
        await page.get_by_role("button", name="Run Tool").click()
        await wait_for_result(page)
        await page.evaluate("document.querySelector('h4') && document.querySelector('h4').scrollIntoView()")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUT}/snip2_check_drug_interactions.png")
        print("✅ snip2_check_drug_interactions.png")

        # ====== SHOT 3: check_dose ======
        await page.locator("text=check_dose").first.click()
        await page.wait_for_timeout(400)
        drug_field = page.get_by_role("textbox", name="drug*")
        await drug_field.fill("ibuprofen")
        dose_field = page.get_by_role("textbox", name="dose_mg*")
        await dose_field.fill("800")
        await page.get_by_role("button", name="Run Tool").click()
        await wait_for_result(page)
        await page.evaluate("document.querySelector('h4') && document.querySelector('h4').scrollIntoView()")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUT}/snip3_check_dose.png")
        print("✅ snip3_check_dose.png")

        # ====== SHOT 4: check_allergy_conflicts ======
        await page.locator("text=check_allergy_conflicts").first.click()
        await page.wait_for_timeout(400)
        allergen_field = page.get_by_role("textbox", name="allergens*")
        await allergen_field.fill('["nsaid"]')
        drug_name_field = page.get_by_role("textbox", name="drug_name*")
        await drug_name_field.fill("ibuprofen")
        await page.get_by_role("button", name="Run Tool").click()
        await wait_for_result(page)
        await page.evaluate("document.querySelector('h4') && document.querySelector('h4').scrollIntoView()")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUT}/snip4_check_allergy_conflicts.png")
        print("✅ snip4_check_allergy_conflicts.png")

        await browser.close()
        print("\nAll 4 screenshots saved.")


asyncio.run(main())
