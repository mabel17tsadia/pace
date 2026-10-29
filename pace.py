from datetime import datetime, timedelta


# Work out today's pace (Gentle, Steady or Ready) from last night's sleep and
# the last 30 minutes of heart rate, with a plain-English reason for each
def get_pace(person, daily, heart):
    # Last night's sleep (the newest daily row) compared with usual
    sleep = daily[-1]["sleep_min"]
    sleep_diff = sleep - person["usual_sleep_min"]

    # Average heart rate over the last 30 minutes of readings, compared with usual
    last_time = datetime.fromisoformat(heart[-1]["time"])
    recent = [h["bpm"] for h in heart
              if datetime.fromisoformat(h["time"]) >= last_time - timedelta(minutes=30)]
    heart_diff = sum(recent) / len(recent) - person["usual_resting_hr"]

    # The pace rule
    if sleep_diff <= -45 or heart_diff >= 15:
        level = "Gentle"
    elif sleep_diff >= 0 and abs(heart_diff) <= 5:
        level = "Ready"
    else:
        level = "Steady"

    # Sleep reason, e.g. "Slept 6 h 40 min, less than usual"
    hours, mins = divmod(sleep, 60)
    slept = f"Slept {hours} h {mins} min" if mins else f"Slept {hours} h"
    if sleep_diff <= -45:
        sleep_reason = f"{slept}, less than usual"
    elif sleep_diff < 0:
        sleep_reason = f"{slept}, a little less than usual"
    else:
        sleep_reason = f"{slept}, at least your usual"

    # Heart rate reason, e.g. "Heart rate a bit higher than usual"
    if heart_diff >= 15:
        heart_reason = "Heart rate higher than usual"
    elif heart_diff > 5:
        heart_reason = "Heart rate a bit higher than usual"
    elif heart_diff < -5:
        heart_reason = "Heart rate lower than usual"
    else:
        heart_reason = "Heart rate close to usual"

    return {"level": level, "sleep_reason": sleep_reason, "heart_reason": heart_reason}
