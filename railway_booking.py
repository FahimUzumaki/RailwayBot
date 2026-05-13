#!/usr/bin/env python3
"""
Bangladesh Railway Auto Booking Script - FINAL (Ultra-Reliable Search Click)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import calendar
import sys
import os
import re

# Fix for Windows console emoji printing error ('charmap' codec can't encode character)
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RailwayBookingBot:
    def __init__(self, credentials, journey_details):
        self.credentials = credentials
        self.journey_details = journey_details
        self.driver = None

    # ---------------- DRIVER ---------------- #
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--remote-debugging-port=0")

        # ── Persist Chrome profile so login session / cookies survive restarts ──
        profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")
        os.makedirs(profile_dir, exist_ok=True)

        # Remove stale lock file that causes "Chrome crashed" on re-run
        lock_file = os.path.join(profile_dir, "SingletonLock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logger.info("🧹 Removed stale Chrome lock file")
            except Exception:
                pass

        chrome_options.add_argument(f"--user-data-dir={profile_dir}")
        chrome_options.add_argument("--profile-directory=Default")
        logger.info(f"📂 Using Chrome profile: {profile_dir}")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        logger.info("✅ Chrome ready!")


    def open_website(self):
        self.driver.get("https://eticket.railway.gov.bd/login")

    # ---------------- LOGIN ---------------- #
    def login(self):
        logger.info("Checking login status...")

        # ── If session cached, site redirects away from /login immediately ──
        time.sleep(1)
        if "login" not in self.driver.current_url.lower():
            logger.info("✅ Already logged in via cached session! Skipping CAPTCHA.")
            return True

        logger.info("No cached session — proceeding with login...")

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "mobile_number"))
            )

            self.driver.find_element(By.ID, "mobile_number").send_keys(self.credentials['mobile'])
            self.driver.find_element(By.ID, "password").send_keys(self.credentials['password'])

            print("\n🔍 Solve CAPTCHA quickly... Bot will auto-login after you solve it.")

            login_button = self.driver.find_element(By.CLASS_NAME, "login-form-submit-btn")

            for _ in range(200):  # 200 × 2s = 400s max wait
                try:
                    login_button.click()
                    time.sleep(2)

                    if "login" not in self.driver.current_url.lower():
                        logger.info("🎉 Login successful! Session saved for next run.")
                        return True

                except:
                    pass

                time.sleep(2)

            return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    # ---------------- AGREE POPUP ---------------- #
    def handle_agree_popup(self):
        logger.info("Checking for 'I AGREE' popup...")

        try:
            agree_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'AGREE')]"))
            )

            self.driver.execute_script("arguments[0].click();", agree_btn)
            logger.info("✅ Clicked I AGREE")
            time.sleep(2)

        except:
            logger.info("ℹ️ No popup found")

    # ---------------- LOGIN MODAL (popup on home page) ---------------- #
    def handle_login_modal(self):
        """Fill and submit the LOGIN modal that appears on the home page
        when the session has expired.  Waits up to 5 minutes for the user
        to solve the Cloudflare CAPTCHA and then clicks LOGIN."""
        try:
            # Check if the modal is open — look for the LOGIN heading inside a modal/dialog
            modal_heading = self.driver.execute_script("""
                let els = Array.from(document.querySelectorAll(
                    '.modal h3, .modal h4, .modal h2, .modal-title, ' +
                    'div[role="dialog"] h3, div[role="dialog"] h4, ' +
                    '.login-modal h3, .popup h3'
                ));
                for (let el of els) {
                    if ((el.innerText || '').toUpperCase().includes('LOGIN')) return true;
                }
                // Also check for a visible mobile-number input inside any overlay
                let inp = document.querySelector(
                    '.modal input[placeholder*="obile"], ' +
                    'div[role="dialog"] input[placeholder*="obile"], ' +
                    '.modal input[type="tel"], .modal input[type="text"]'
                );
                return inp !== null && inp.offsetWidth > 0;
            """)

            if not modal_heading:
                return False  # no modal, nothing to do

            logger.info("🔔 Login modal detected — filling credentials...")

            # Fill mobile number
            mobile_input = self.driver.execute_script("""
                return document.querySelector(
                    '.modal input[placeholder*="obile"], ' +
                    'div[role="dialog"] input[placeholder*="obile"], ' +
                    '.modal input[type="tel"], .modal input[type="text"]'
                );
            """)
            if mobile_input:
                self.driver.execute_script("arguments[0].value = '';", mobile_input)
                mobile_input.send_keys(self.credentials['mobile'])
                time.sleep(0.5)

            # Fill password
            pwd_input = self.driver.execute_script("""
                return document.querySelector(
                    '.modal input[type="password"], div[role="dialog"] input[type="password"]'
                );
            """)
            if pwd_input:
                self.driver.execute_script("arguments[0].value = '';", pwd_input)
                pwd_input.send_keys(self.credentials['password'])
                time.sleep(0.5)

            logger.info("⏳ Credentials filled. Waiting for CAPTCHA to be solved (up to 5 min)...")
            print("\n🔍 CAPTCHA appeared — please solve it in the browser!")

            # Wait for the LOGIN button to become enabled (after CAPTCHA solved)
            # then keep clicking it until the modal disappears
            for _ in range(150):  # 150 × 2s = 5 min max
                try:
                    login_btn = self.driver.execute_script("""
                        let btns = Array.from(document.querySelectorAll(
                            '.modal button, div[role="dialog"] button'
                        ));
                        for (let b of btns) {
                            let txt = (b.innerText || '').toUpperCase().trim();
                            if (txt === 'LOGIN' || txt === 'LOG IN') return b;
                        }
                        return null;
                    """)

                    if login_btn and not login_btn.get_attribute('disabled'):
                        self.driver.execute_script("arguments[0].click();", login_btn)
                        time.sleep(2)

                        # Check if modal is gone
                        still_open = self.driver.execute_script("""
                            let inp = document.querySelector(
                                '.modal input[type="tel"], .modal input[type="text"], '
                                + 'div[role="dialog"] input[type="tel"]'
                            );
                            return inp !== null && inp.offsetWidth > 0;
                        """)
                        if not still_open:
                            logger.info("🎉 Login modal closed — session established!")
                            time.sleep(2)
                            return True
                except Exception:
                    pass
                time.sleep(2)

            logger.warning("⚠️ Login modal still open after 5 min — proceeding anyway")
            return False

        except Exception as e:
            logger.warning(f"handle_login_modal error: {e}")
            return False

    # ---------------- DATE SELECTION ---------------- #
    def select_date(self):
        logger.info("Selecting date...")

        try:
            target_date = self.journey_details['date']  # YYYY-MM-DD
            year, month, day = target_date.split("-")
            month_name = calendar.month_name[int(month)]

            # Open calendar
            date_field = self.driver.find_element(By.ID, "doj")
            date_field.click()
            time.sleep(2)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-title"))
            )

            # Navigate month/year
            while True:
                title = self.driver.find_element(By.CLASS_NAME, "ui-datepicker-title").text
                if month_name in title and year in title:
                    break
                else:
                    self.driver.find_element(By.CLASS_NAME, "ui-datepicker-next").click()
                    time.sleep(1)

            # Click day
            day_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//a[text()='{int(day)}' and contains(@class,'ui-state-default')]"
                ))
            )
            day_element.click()
            logger.info(f"✅ Date selected: {target_date}")
            time.sleep(1)

        except Exception as e:
            logger.error(f"❌ Date selection error: {e}")

    # ---------------- BOOKING ---------------- #
    def fill_booking_form(self):
        logger.info("Filling booking form...")

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "dest_from"))
            )

            # FROM
            from_field = self.driver.find_element(By.ID, "dest_from")
            from_field.click()
            time.sleep(0.5)
            from_field.send_keys(self.journey_details['from'])
            time.sleep(1)
            from_field.send_keys(u'\ue015') # Down Arrow
            time.sleep(0.2)
            from_field.send_keys(u'\ue007') # Enter

            # TO
            to_field = self.driver.find_element(By.ID, "dest_to")
            to_field.click()
            time.sleep(0.5)
            to_field.send_keys(self.journey_details['to'])
            time.sleep(1)
            to_field.send_keys(u'\ue015') # Down Arrow
            time.sleep(0.2)
            to_field.send_keys(u'\ue007') # Enter

            # DATE
            self.select_date()

            # CLASS
            class_select_el = self.driver.find_element(By.ID, "choose_class")
            class_select = Select(class_select_el)
            
            # Debug available options
            options_info = [f"{opt.text} (value: {opt.get_attribute('value')})" for opt in class_select.options]
            logger.info("Available class options: " + " | ".join(options_info))
            
            try:
                class_select.select_by_value(self.journey_details['class'])
                logger.info(f"Selected class by value: {self.journey_details['class']}")
            except Exception as e:
                logger.warning(f"Failed to select class by value, trying visible text... ({e})")
                try:
                    class_select.select_by_visible_text(self.journey_details['class'])
                    logger.info(f"Selected class by visible text: {self.journey_details['class']}")
                except Exception as e2:
                    logger.warning(f"Could not select class at all. Defaulting to whatever is selected. ({e2})")

            time.sleep(2)

            # ---------------- RELIABLE SEARCH BUTTON CLICK ---------------- #
            logger.info("Clicking SEARCH TRAINS...")

            # Wait until button is clickable
            # Using type='submit' because 'SEARCH' is case-sensitive and text is 'Search Trains'
            search_btn = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )

            # Remove overlays / modals
            self.driver.execute_script("""
            let overlays = document.querySelectorAll('.overlay, .modal-backdrop, .loading');
            overlays.forEach(e => e.remove());
            """)
            time.sleep(0.5)

            # Scroll into view + JS click
            self.driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", search_btn)
            time.sleep(0.2)
            self.driver.execute_script("arguments[0].click();", search_btn)

            # Wait for results — also watch for a login modal appearing mid-flow
            logger.info("⏳ Waiting for Search Results (or login modal)...")
            deadline = time.time() + 400  # 400-second overall timeout
            while time.time() < deadline:
                # Check for login modal first
                if self.handle_login_modal():
                    # Modal was handled — re-submit the search
                    logger.info("🔄 Re-submitting search after login...")
                    time.sleep(2)
                    try:
                        search_btn2 = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                        )
                        self.driver.execute_script("arguments[0].click();", search_btn2)
                    except Exception:
                        pass

                # Check if results are already there
                try:
                    self.driver.find_element(By.CSS_SELECTOR,
                        ".book-now-btn, .single-train, app-train-card")
                    logger.info("✅ Search completed & train results loaded!")
                    return True
                except Exception:
                    pass

                time.sleep(2)

            logger.error("❌ Timed out waiting for train results.")
            return False

        except Exception as e:
            logger.error(f"❌ Booking form error: {e}")
            return False

    def select_train(self):
        train_name = self.journey_details.get('train_name', '').upper()
        seat_class = self.journey_details.get('class', 'S_CHAIR').upper()
        logger.info(f"Selecting train: {train_name} | Class: {seat_class}...")

        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".book-now-btn"))
            )
            time.sleep(1)

            # Find the correct train AND class combination
            result = self.driver.execute_script("""
                let trainName = arguments[0];          // e.g. 'PADMA EXPRESS'
                let seatClass = arguments[1];          // e.g. 'S_CHAIR'
                let seatClassAlt = seatClass.replace(/_/g, ' ').trim(); // 'S CHAIR'

                let allTrainCards = Array.from(document.querySelectorAll('app-single-trip'));
                let trainNames = [];
                let targetButton = null;

                for (let card of allTrainCards) {
                    let nameEl = card.querySelector('.trip-left-info h2');
                    if (!nameEl) continue;

                    let cardTrainName = (nameEl.innerText || '').trim().toUpperCase();
                    trainNames.push(cardTrainName);

                    if (cardTrainName.indexOf(trainName) === -1) continue;

                    // ── Use exact span.seat-class-name match to avoid hitting parent containers ──
                    let seatBlocks = Array.from(card.querySelectorAll('.single-seat-class'));
                    for (let block of seatBlocks) {
                        let nameSpan = block.querySelector('.seat-class-name');
                        if (!nameSpan) continue;

                        // Normalise: replace spaces/underscores so 'S CHAIR' == 'S_CHAIR'
                        let blockClass = (nameSpan.innerText || '').trim().toUpperCase().replace(/[ _]+/g, '_');
                        let target    = seatClass.replace(/[ _]+/g, '_');

                        if (blockClass !== target) continue;

                        // Found matching class block – grab its Book Now button
                        let btn = block.querySelector('.book-now-btn, button');
                        if (btn && !btn.disabled) {
                            targetButton = btn;
                            break;
                        }
                    }

                    if (targetButton) break;
                }

                return { trainBlocks: trainNames, btn: targetButton };
            """, train_name, seat_class)

            all_names = result.get('trainBlocks', [])
            target_btn = result.get('btn')

            logger.info(f"Trains found: {all_names}")

            if target_btn is None:
                logger.error(f"❌ '{train_name}' with class '{seat_class}' NOT FOUND!")
                logger.info(f"Available trains: {all_names}")
                input("Press Enter to manually select train and class...")
                return True

            self.driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", target_btn)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", target_btn)
            logger.info(f"✅ Clicked Book Now for {train_name} - {seat_class}!")
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Train selection error: {e}")
            return False

    def select_coach_class_block(self):
        """Click the correct class block tab (e.g. S_Chair / AC_B / Snigdha)
        on the seat layout page.  The blocks appear as clickable buttons/tabs
        near the top of the seat map page."""
        seat_class = self.journey_details.get('class', 'S_CHAIR').upper()  # e.g. "S_CHAIR"
        # Build alternative forms for matching:
        #   S_CHAIR  →  also try  S CHAIR  and  S_Chair  and  SCHAIR
        seat_class_space  = seat_class.replace('_', ' ').strip()   # "S CHAIR"
        seat_class_nound  = seat_class.replace('_', '').strip()    # "SCHAIR"

        logger.info(f"Selecting class block tab: {seat_class} …")

        result = self.driver.execute_script("""
            let seatClass    = arguments[0];  // 'S_CHAIR'
            let seatClassAlt = arguments[1];  // 'S CHAIR'

            // Normalise helper: collapse spaces/underscores for comparison
            function norm(s) { return s.toUpperCase().replace(/[\\s_]+/g, '_'); }

            let targetNorm = norm(seatClass);

            // ── Primary: look for span.seat-class-name with exact text match ──
            let spans = Array.from(document.querySelectorAll('.seat-class-name'));
            for (let span of spans) {
                let spanNorm = norm(span.innerText || '');
                if (spanNorm !== targetNorm) continue;

                // Click the parent single-seat-class block to activate it
                let block = span.closest('.single-seat-class') || span.parentElement;
                if (!block || block.offsetWidth === 0) continue;
                block.scrollIntoView({block:'nearest'});
                block.click();
                return (span.innerText || '').trim();
            }

            // ── Fallback: look for any visible button/tab whose SOLE text matches ──
            let btns = Array.from(document.querySelectorAll(
                'button[class*="seat"], button[class*="class"], ' +
                'li[role="tab"], .nav-item a, .coach-tab'
            ));
            for (let b of btns) {
                let bNorm = norm(b.innerText || '');
                if (bNorm !== targetNorm) continue;
                if (b.offsetWidth === 0) continue;
                b.scrollIntoView({block:'nearest'});
                b.click();
                return (b.innerText || '').trim();
            }

            return null;
        """, seat_class, seat_class_space)

        if result:
            logger.info(f"✅ Class block clicked: '{result}'")
            time.sleep(2)  # wait for seat map to refresh
        else:
            logger.warning(
                f"⚠️ Class block '{seat_class}' not found via JS. "
                "Seat layout may already be filtered or the selector needs updating."
            )

    def select_seats(self):
        logger.info("Auto-selecting passenger seats...")
        try:
            num_seats = self.journey_details.get('seats', 2)
            
            # Wait for seat layout to load
            time.sleep(1)
            logger.info("Waiting for seat layout page...")
            
            # Wait for the bogie dropdown to appear
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "select-bogie"))
                )
                logger.info("✅ Seat layout loaded!")
            except:
                logger.warning("Bogie dropdown not found, trying to proceed anyway")

            # ── NEW: click the correct class block tab (S_Chair / AC_B etc.) ──
            self.select_coach_class_block()
            time.sleep(1)

            clicked_total = 0

            # ── Try dropdown bogie selector (S_CHAIR layout) ──
            bogie_options = [None]  # default: scan once without switching
            try:
                bogie_select_el = self.driver.find_element(By.ID, "select-bogie")
                bogie_select = Select(bogie_select_el)
                bogie_options = bogie_select.options
                logger.info(f"Found {len(bogie_options)} bogie options (dropdown)")
            except:
                # ── Fallback: look for coach buttons visible on page (Snigdha/AC layout) ──
                coach_btns = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll(
                        '.coach-btn, .bogie-btn, button[class*="coach"], ' +
                        'button[class*="bogie"], .seat-coach button, ' +
                        '.layout-coach-list button, .coach-list-item'
                    )).filter(b => b.offsetWidth > 0 && !b.disabled);
                """)
                if coach_btns:
                    logger.info(f"Found {len(coach_btns)} coach buttons on page")
                    bogie_options = coach_btns  # iterate these instead
                else:
                    logger.warning("No bogie/coach selector found — scanning visible seats directly")

            for i, option in enumerate(bogie_options):
                if clicked_total >= num_seats:
                    break

                if option is not None:
                    # Dropdown option (Select element)
                    try:
                        val = option.get_attribute('value')
                        if val is not None:  # it's a <select> option
                            if not val.strip():
                                continue
                            option_text = option.text
                            # Extract number of seats
                            match = re.search(r'(\d+)\s*Seat', option_text, re.IGNORECASE)
                            if match:
                                seats_avail = int(match.group(1))
                                if seats_avail < num_seats:
                                    logger.info(f"Skipping {option_text} (needs {num_seats} seats)")
                                    continue
                            elif "0 Seat" in option_text or "0 seat" in option_text:
                                logger.info(f"Skipping empty bogie: {option_text}")
                                continue
                                
                            logger.info(f"Switching to bogie: {option_text}")
                            bogie_select = Select(self.driver.find_element(By.ID, "select-bogie"))
                            bogie_select.select_by_index(i)
                            time.sleep(1)
                        else:
                            # It's a WebElement coach button — click it
                            option_text = option.text.strip()
                            # Extract number of seats
                            match = re.search(r'(\d+)\s*Seat', option_text, re.IGNORECASE)
                            if match:
                                seats_avail = int(match.group(1))
                                if seats_avail < num_seats:
                                    logger.info(f"Skipping {option_text} (needs {num_seats} seats)")
                                    continue
                            elif "0 Seat" in option_text or "0 seat" in option_text:
                                logger.info(f"Skipping empty coach: {option_text}")
                                continue
                                
                            logger.info(f"Clicking coach: {option_text}")
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", option)
                            self.driver.execute_script("arguments[0].click();", option)
                            time.sleep(1)
                    except Exception:
                        # Raw WebElement (coach button)
                        try:
                            logger.info(f"Clicking coach button...")
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", option)
                            self.driver.execute_script("arguments[0].click();", option)
                            time.sleep(1)
                        except Exception as ce:
                            logger.warning(f"Coach button click failed: {ce}")
                            continue

                # ── Find available seat buttons — broad selector covers all class layouts ──
                seats = self.driver.execute_script("""
                    // Cast wide net: floor-based (S_CHAIR) + table-based + any seat grid
                    let candidates = Array.from(document.querySelectorAll(
                        '#floor-0 button, .seat_layout button, .col-md-6 button, ' +
                        '.seat-grid button, .berth-layout button, ' +
                        '.seat-map button, .seat-row button, ' +
                        'td button, .seat button, [class*="seat"] button'
                    ));
                    // Deduplicate
                    candidates = [...new Set(candidates)];
                    return candidates.filter(b => {
                        if (b.offsetWidth === 0 || b.offsetHeight === 0) return false;
                        if (b.disabled) return false;
                        let cls = (b.className || '').toLowerCase();
                        if (cls.includes('booked') || cls.includes('disabled') ||
                            cls.includes('unavailable') || cls.includes('sold')) return false;
                        let t = (b.innerText || '').trim();
                        // Seat labels are typically short (e.g. "A1", "12", "3B")
                        if (t.length > 12) return false;
                        let tl = t.toLowerCase();
                        if (tl.includes('purchase') || tl.includes('continue') ||
                            tl.includes('search') || tl.includes('login') ||
                            tl.includes('proceed') || tl.includes('book')) return false;
                        return true;
                    });
                """)

                logger.info(f"Found {len(seats)} available seats in this bogie")
                
                for seat in seats:
                    if clicked_total >= num_seats:
                        break
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", seat)
                        time.sleep(0.1)
                        self.driver.execute_script("arguments[0].click();", seat)
                        clicked_total += 1
                        logger.info(f"✅ Seat {clicked_total} clicked!")
                        time.sleep(0.1)
                    except Exception as se:
                        logger.warning(f"Seat click failed: {se}")
                        continue

            logger.info(f"Total seats selected: {clicked_total}/{num_seats}")
            
            if clicked_total > 0:
                # Click the Purchase/Continue button
                time.sleep(1)
                try:
                    purchase_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH,
                            "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PURCHASE') or "
                            "contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'CONTINUE') or "
                            "contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PROCEED')]"
                        ))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", purchase_btn)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", purchase_btn)
                    logger.info("✅ Purchase/Continue clicked! Proceeding to payment...")
                except Exception as pb:
                    logger.warning(f"Purchase button not auto-clicked: {pb}")

            return clicked_total >= num_seats

        except Exception as e:
            logger.warning(f"⚠️ Seat selection error: {e}")
            input("Manual seat selection needed → press Enter when done...")
            return True

    # ---------------- RUN ---------------- #
    def run(self):
        try:
            self.setup_driver()
            self.open_website()

            if not self.login():
                logger.error("Login failed")
                return

            self.handle_agree_popup()

            if not self.fill_booking_form():
                return

            if not self.select_train():
                return

            self.select_seats()
            logger.info("🎉 Done! Complete payment manually")

        finally:
            if self.driver:
                input("\nPress Enter to close...")
                self.driver.quit()


def main():
    credentials = {
        'mobile': '*',
        'password': '*'
    }

    journey_details = {
        'from': 'Dhaka',
        'to': "Rajshahi",
        'date': '2026-05-20',  
        'class': 'S_CHAIR',
        'train_name': 'PADMA EXPRESS',  
        'seats': 2
    }

    bot = RailwayBookingBot(credentials, journey_details)
    bot.run()


if __name__ == "__main__":
    main()