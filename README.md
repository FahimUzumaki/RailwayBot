# Bangladesh Railway Booking Bot

An ultra-reliable and fast automated ticket booking bot for the Bangladesh Railway E-Ticketing Website. Built with Selenium and Python, it automatically signs into your cached session (bypassing CAPTCHAs), searches for your requested trains, handles smart seat capacity checking, and automates seat selection seamlessly.

## Features Let you Do Stuff Like

- **Session Persistence**: Keep a local Chrome profile (`chrome_profile`) to bypass CAPTCHA. Log in once, and subsequent runs log in automatically!
- **Dynamic Train Search**: Wait, filter, and correctly select the exact `train_name` you specify.
- **Smart Seat Capacity Processing**: Skips empty bogies and dropdown bugs instantly. It reliably calculates real numbers so it only wastes time navigating coach layouts that have enough capacity to cover your group.
- **Intelligent Recovery**: Can recover search requests from random log-out modals. Drops UI overlays to confidently hit search buttons.

## Requirements

1. Python 3.8+
2. Required packages:
   ```bash
   pip install selenium webdriver-manager
   ```

## Setup Instructions

1. Install dependencies from the terminal:
   ```bash
   pip install selenium webdriver-manager
   ```
2. Open `railway_booking.py` in your favorite editor.
3. Scroll to the bottom to the `main()` function and set your login and journey details:

```python
    credentials = {
        'mobile': '01XXXXXXXXX',
        'password': 'YourPassword'
    }

    journey_details = {
        'from': 'Dhaka',
        'to': "Cox's Bazar",
        'date': '2026-05-01',  
        'class': 'S_CHAIR',  # You can use S_CHAIR, SNIGDHA, AC_B, etc.
        'train_name': 'COXS BAZAR EXPRESS',  
        'seats': 2
    }
```

## Running the Bot

Run the script from your terminal:
```bash
python railway_booking.py
```

The first time you run it, you may need to fill in the CAPTCHA manually. After you log in successfully, the Chrome session saves locally. On subsequent runs, it reads your session and skips CAPTCHA verification, instantly automating search and seat grabbing. When it completes, the ticket selection stops at the Purchase summary page for your manual payment verification. 

Good luck and happy travels! 🚄
