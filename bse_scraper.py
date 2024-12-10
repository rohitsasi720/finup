from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os

def setup_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    return chrome_options

async def get_bse_screenshot():
    screenshot_path = "bse_form_submission.png"
    
    # Set up Chrome options for headless operation
    chrome_options = setup_chrome_options()
    
    try:
        # Initialize the driver with headless options
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        driver.get("https://www.bseindia.com/corporates/ann.html")

        # Wait until the date picker appears
        date_picker_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "txtFromDt"))
        )
        date_picker_trigger.click()

        # Wait for the year dropdown and select "2024"
        year_dropdown_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-year"))
        )
        year_select = Select(year_dropdown_element)
        year_select.select_by_visible_text("2024")

        # Wait for the month dropdown and select "October"
        month_dropdown_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-month"))
        )
        month_select = Select(month_dropdown_element)
        month_select.select_by_visible_text("Oct")

        # Wait for and click the day "6"
        day_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='ui-datepicker-div']/table/tbody/tr[1]/td[7]/a"))
        )
        day_element.click()

        # Short pause for stability
        time.sleep(1)

        # Select "Company Update" from first dropdown
        category_dropdown_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ddlPeriod"))
        )
        select = Select(category_dropdown_element)
        select.select_by_visible_text("Company Update")

        time.sleep(1)

        # Select "Award of Order / Receipt of Order" from second dropdown
        sub_category_dropdown_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ddlsubcat"))
        )
        select = Select(sub_category_dropdown_element)
        select.select_by_visible_text("Award of Order / Receipt of Order")

        time.sleep(1)

        # Click submit button
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "submit"))
        )
        submit_button.click()

        # Wait for results to load
        time.sleep(3)

        # Take screenshot
        driver.save_screenshot(screenshot_path)
        
        return screenshot_path
        
    except Exception as e:
        raise Exception(f"Error during scraping: {str(e)}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    # For testing the script directly
    import asyncio
    asyncio.run(get_bse_screenshot()) 