###################################################
# RCB Ticket Monitor 2026
#
# A Python script that uses Selenium to monitor the RCB ticket page for availability.
# When the "Buy Tickets" button appears:
# - This script triggers a loud alarm to wake you up and alert you to the change.
# - Optionally, it can also send a push notification to your phone via ntfy.sh.
#
#  Pre-requisites:
# 1. Python 3.x installed on your system.
# 2. Chrome browser installed.
# 3. Selenium and webdriver-manager libraries installed (pip3 install selenium webdriver-manager).
#
# Usage:
# 1. Update the TICKET_URL and BUTTON_XPATH variables in the script to match the target page and button you want to monitor. Defaults are set for the RCB ticket 2026 page.
# 2. Ensure your computer's volume is turned up for the alarm to be effective.
# 3. If you're using the ntfy notification feature, make sure to set up your ntfy topic and have the app installed on your phone to receive push notifications. Instructions for ntfy setup can be found at https://docs.ntfy.sh/subscribe/phone/.
# 4. Run the script: python3 rcb-tickets.py. If using macOS, use caffeine to prevent sleep: caffeinate -i python3 rcb-tickets.py
# 5. The script will continuously check the specified page for the button's availability and will alert you when it changes to "BUY TICKETS".
# 6. To stop the script, simply press Ctrl+C in the terminal.
##############################################
import time
import random
import logging
import subprocess
import urllib.request
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
    def __init__(self, url, target_xpath, ntfy_topic=None):
        self.url = url
        self.target_xpath = target_xpath
        self.ntfy_topic = ntfy_topic
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
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except WebDriverException as e:
            logging.error("❌ CRITICAL: Could not launch Chrome.")
            logging.error("This usually means one of two things:")
            logging.error("1. Chrome browser is not installed or not found.")
            logging.error("2. ChromeDriver could not be downloaded via webdriver-manager.")
            logging.error(f"   (Selenium error: {e})")
            raise Exception("Failed to start Selenium-controlled Chrome session.")

    def _apply_jitter(self, base_interval, attempt):
        """Randomized cooldown to mimic human behavior and avoid rate limits."""
        total_sleep = base_interval + random.uniform(0.5, 2.5)
        logging.info(f"Check #{attempt} | Cooldown for {total_sleep:.2f}s...")
        time.sleep(total_sleep)

    def _trigger_local_alarm(self):
        """Plays a loud alarm depending on the operating system."""
        logging.info("🚨 TICKETS ARE LIVE! Waking you up! 🚨")
        sys_os = platform.system()
        try:
            logging.info("Playing alarm for 60 seconds...")
            if sys_os == "Darwin": # macOS
                subprocess.run(['osascript', '-e', 'set volume output volume 100'])
                subprocess.Popen(['say', 'Wake up! Wake up! Wake up! Tickets are live! Go get them now!'])
                for _ in range(120):
                    subprocess.Popen(['afplay', '/System/Library/Sounds/Sosumi.aiff'])
                    time.sleep(0.5)
            elif sys_os == "Windows":
                import winsound
                for _ in range(60):
                    winsound.Beep(1000, 1000)
                    time.sleep(0.1)
            elif sys_os == "Linux":
                for _ in range(60):
                    print('\a') # Terminal bell
                    try:
                        subprocess.Popen(['aplay', '/usr/share/sounds/alsa/Front_Center.wav'], stderr=subprocess.DEVNULL)
                    except FileNotFoundError:
                        try:
                            subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'], stderr=subprocess.DEVNULL)
                        except FileNotFoundError:
                            pass
                    time.sleep(1)
            else:
                for _ in range(60):
                    print('\a')
                    time.sleep(1)
        except Exception as e:
            logging.warning(f"Could not play alarm sound: {e}")

    def _trigger_ntfy_notification(self):
        """Sends a push notification to your phone via ntfy.sh."""
        if not self.ntfy_topic:
            return
        
        url = f"https://ntfy.sh/{self.ntfy_topic}"
        headers = {
            "Title": "RCB Tickets are LIVE!",
            "Priority": "urgent",
            "Tags": "ticket,rotating_light"
        }
        data = f"Tickets for {self.url} are available now! Go buy them!".encode('utf-8')
        
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            urllib.request.urlopen(req)
            logging.info(f"Sent ntfy.sh push notification to topic: {self.ntfy_topic}")
        except Exception as e:
            logging.error(f"Failed to send ntfy notification: {e}")

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
                    self._trigger_ntfy_notification()
                    self._trigger_local_alarm()
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
    
    # ntfy.sh Topic (Optional)
    # Download the ntfy app, create a unique topic name, and paste it below.
    # e.g., "rcb-tickets-alert-123"
    NTFY_TOPIC = "rcb-tickets-alert-suresh-reddy" # Change this to your unique topic!
    # =========================================================================

    notifier = TicketNotifier(url=TICKET_URL, target_xpath=BUTTON_XPATH, ntfy_topic=NTFY_TOPIC)

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
