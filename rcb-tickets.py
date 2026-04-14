###################################################
# RCB Ticket Monitor 2026
# A Python script that uses Selenium to monitor the RCB ticket page for availability.
# When the "Buy Tickets" button is no longer marked as "SOLD OUT", it triggers a loud alarm on macOS to wake you up and alert you to the change.
#  Pre-requisites:
# 1. Python 3.x installed on your system.
# 2. Selenium library installed (pip install selenium).
# 3. Chrome browser installed.
# 4. ChromeDriver installed and added to your system's PATH (https://sites.google.com/a/chromium.org/chromedriver/downloads).
# Usage:
# 1. Update the TICKET_URL and BUTTON_XPATH variables in the script to match the target page and button you want to monitor.
# 2. Run the script: python3 rcb-tickets.py (OR) To prevent mac from sleeping, execute caffeinate -i python3 rcb-tickets.py in the terminal. This will keep your Mac awake while the script is running.
# 3. The script will continuously check the specified page for the button's availability and will alert you when it changes from "SOLD OUT" to "BUY TICKETS".
# 4. To stop the script, simply press Ctrl+C in the terminal.
# Note: This script is designed for macOS due to its use of native audio commands. If you're using a different operating system, you may need to modify the _trigger_mac_alarm method to use an appropriate method for playing sounds on your platform.
##############################################
import time
import random
import logging
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure beautifully aligned terminal output
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-7s :: %(message)s',
    datefmt='%H:%M:%S'
)

class TicketNotifier:
    """
    Monitors a website for ticket availability and sounds an alarm
    when a specific button is no longer marked as 'SOLD OUT'.
    """
    def __init__(self, url, target_xpath):
        self.url = url
        self.target_xpath = target_xpath
        self.driver = self._setup_driver()

    def _setup_driver(self):
        """Starts a new, clean Chrome instance."""
        options = webdriver.ChromeOptions()

        # To run with a visible browser window, comment out the next line.
        options.add_argument("--headless=new")

        # --- Settings to make headless mode look more like a real browser ---
        # 1. Set a common user agent, as some sites block default headless agents.
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')
        
        # 2. Set a realistic window size. Headless can default to a small size,
        #    breaking responsive websites and causing XPaths to fail.
        options.add_argument("--window-size=1920,1080")
        # -----------------------------------------------------------------

        # This argument is for non-headless mode to open a maximized window.
        options.add_argument("--start-maximized")

        try:
            # A bit of logic to log the mode we are running in.
            is_headless = any("--headless" in arg for arg in options.arguments)
            if is_headless:
                logging.info("Launching Chrome in HEADLESS mode...")
            else:
                logging.info("Launching a new Chrome browser window...")
            
            driver = webdriver.Chrome(options=options)
            return driver
        except WebDriverException as e:
            logging.error("❌ CRITICAL: Could not launch Chrome.")
            logging.error("This usually means one of two things:")
            logging.error("1. ChromeDriver is not installed or not in your system's PATH.")
            logging.error("2. The Chrome browser itself is not found.")
            logging.error(f"   (Selenium error: {e})")
            raise Exception("Failed to start Selenium-controlled Chrome session.")

    def _apply_jitter(self, base_interval, attempt):
        """Randomized cooldown to mimic human behavior and avoid rate limits."""
        total_sleep = base_interval + random.uniform(0.5, 2.5)
        logging.info(f"Check #{attempt} | Cooldown for {total_sleep:.2f}s...")
        time.sleep(total_sleep)

    def _trigger_mac_alarm(self):
        """Hijacks macOS native audio to blare a loud, continuous alarm."""
        logging.info("🚨 TICKETS ARE LIVE! Waking you up! 🚨")
        try:
            # Force volume to maximum
            subprocess.run(['osascript', '-e', 'set volume output volume 100'])
            
            # Announce the alert loudly
            subprocess.Popen(['say', 'Wake up! Wake up! Wake up! Tickets are live! Go get them now!'])
            
            # Loop a sound for 180 seconds to make sure you wake up
            logging.info("Playing alarm for 180 seconds...")
            for _ in range(360):
                # 'Sosumi' is a short, sharp, and classic alert sound
                subprocess.Popen(['afplay', '/System/Library/Sounds/Sosumi.aiff'])
                time.sleep(0.5) # Play the sound twice a second

        except FileNotFoundError:
            logging.warning("Could not play alarm sound. 'osascript', 'say', or 'afplay' not found on this system.")


    def monitor(self, base_refresh_interval=60.0):
        """Main monitoring loop."""
        logging.info(f"Deploying monitor for URL: {self.url}")
        self.driver.get(self.url)

        attempt = 1
        while True:
            try:
                # Wait for the button element to be present on the page
                button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.target_xpath))
                )

                button_text = button.text.strip().upper()

                if "BUY TICKETS" in button_text and button_text != "":
                    logging.info(f"✅ Tickets are live! Button text is now: '{button.text}'")
                    self._trigger_mac_alarm()
                    break  # Exit loop on success
                else:
                    status = button_text if button_text else "EMPTY"
                    logging.info(f"Check #{attempt} | Status: [{status}]. Refreshing...")
                    self._apply_jitter(base_refresh_interval, attempt)
                    self.driver.refresh()

            except TimeoutException:
                logging.warning(f"Check #{attempt} | Target button not found on page. Layout may have changed. Refreshing...")
                self._apply_jitter(base_refresh_interval, attempt)
                try:
                    self.driver.refresh()
                except WebDriverException as e:
                    logging.error(f"Browser connection lost while refreshing: {e}. Retrying...")
                    time.sleep(10)

            except WebDriverException as e:
                logging.error(f"A browser error occurred: {e}. Retrying after 10s...")
                time.sleep(10)

            attempt += 1

    def close(self):
        """Closes the browser window."""
        if self.driver:
            logging.info("Closing the browser window.")
            self.driver.quit()

if __name__ == "__main__":
    # =========================================================================
    # ✅ --- CONFIGURATION --- ✅
    # =========================================================================
    # The URL of the page you want to monitor
    TICKET_URL = "https://shop.royalchallengers.com/ticket"

    # The XPath to the button you want to check.
    # This should be specific enough to uniquely identify the button.
    BUTTON_XPATH = "//div[@align-self='center']/button[contains(@class, 'chakra-button')]"
    # =========================================================================

    notifier = TicketNotifier(url=TICKET_URL, target_xpath=BUTTON_XPATH)

    try:
        notifier.monitor(base_refresh_interval=60.0)
        logging.info("✅ Monitoring complete. The ticket button is live!")
        input("\n[ ACTION REQUIRED ] Press Enter to close the browser and exit the script.\n")
    except KeyboardInterrupt:
        logging.info("\nScript terminated manually by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        notifier.close()
