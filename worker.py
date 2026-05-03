import time
import traceback
from datetime import datetime

from app.bot import run as generate_numbers
from services.result_checker import run_result_check

def main():
    print("🚀 Worker started...")

    while True:
        try:
            print(f"\n⏰ Cycle started at {datetime.utcnow()}")

            # 🎟️ Generate weekly System 8 numbers
            print("🎯 Generating numbers...")
            generate_numbers()

            # 📊 Check results
            print("📊 Checking results...")
            run_result_check()

            print("✅ Cycle completed")

        except Exception as e:
            print("❌ Error occurred:")
            traceback.print_exc()

        # ⏳ Sleep 24 hours
        print("😴 Sleeping for 24 hours...")
        time.sleep(86400)


if __name__ == "__main__":
    main()