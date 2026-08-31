from datetime import datetime, timedelta

def current_utc_time():
    return datetime.utcnow() + timedelta(hours=3)

def get_previous_quarter():
    current_time = current_utc_time()
    current_month = current_time.month
    current_quarter = (current_month - 1) // 3 + 1

    if current_quarter == 1:
        return 4
    else:
        return current_quarter - 1

def get_report_year():
    current_time = current_utc_time()
    current_month = current_time.month
    current_quarter = (current_month - 1) // 3 + 1

    if current_quarter == 1:
        return current_time.year - 1
    else:
        return current_time.year
    
def last_quarter():
    current_month = current_utc_time().strftime("%m")
    if (current_month == '01' or current_month == '02' or current_month == '03'):
        last_quarter_value = 4
    elif (current_month == '04' or current_month == '05' or current_month == '06'):
        last_quarter_value = 1
    elif (current_month == '07' or current_month == '08' or current_month == '09'):
        last_quarter_value = 2
    else:
        last_quarter_value = 3
    return last_quarter_value

def year_fourMounth_ago():
    months_to_subtract = 4
    new_date = current_utc_time() - timedelta(days=months_to_subtract * 30)
    year_4_months_ago = new_date.year
    return year_4_months_ago