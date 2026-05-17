import subprocess
import json
import urllib.request
import urllib.parse
from datetime import datetime
import time

BOT_TOKEN = "8743202444:AAHCHkgc1f6yYjIXBBt3zikZYhXcGIYNie0"
SUMMARY_CHAT_ID = "-1003796210997" # รวมก้อย กุ้ง
MONITOR_SHEET_ID = "1djfKOSHVB9PoUXK9bieoD2svwXFdjsQNsxMJp6sSrdw"

shops = {
    "S001": {"name": "ตลาดต้นสัก", "id": "1LjblaFfCKcsTNSMm5R_z8ARwkiYO7_dNF_HXL3hAf2w", "tg_group_id": "-5170543236", "close_hr": 19},
    "S002": {"name": "ตลาดบางใหญ่", "id": "1uJ-lbMDr9OZoVBF6hd4FVuQPnq9j3vEgeVOjlxw1S_Y", "tg_group_id": "-5261327901", "close_hr": 19},
    "S003": {"name": "ตลาดยิ่งเจริญ", "id": "1MvJ_1zb7qGjMYYoOp4jpZiuQ46VW46x2amz11NaBn3U", "tg_group_id": "-5125896784", "close_hr": 19},
    "S004": {"name": "ตลาดดวงแก้ว", "id": "1Lc_zsDcW_COh0RuR3xl3FF9sqXmPB4J5ZysKxU8dhLg", "tg_group_id": "-5046972885", "close_hr": 20},
    "S005": {"name": "โลตัส บางพลี", "id": "18eKBZwCY-HR7z9KXN6m3WOankjLmf8wUxurAm4uIgoc", "tg_group_id": "-5037109941", "close_hr": 20},
    "S006": {"name": "เซ็นทรัล พระราม 2", "id": "1aT-subVPet1gcZ5S5Wu5QEDYrjNxdS_l6HeJ30p1p50", "tg_group_id": "-1003881435057", "close_hr": 21},
    "S007": {"name": "ปตท.ตลาดเวิล์ดมาร์เก็ต", "id": "1FidMwHBzbJqxebGYFnrzN_OIOOnBDq_fL2q9QPdFqSo", "tg_group_id": "-1003879546261", "close_hr": 20},
    "S008": {"name": "เซ็นทรัล ศาลายา", "id": "1mmCuzUWkNT3EWhihVqEN7-TTggLt7BraVk7CyO47gkw", "tg_group_id": "-5187003551", "close_hr": 21},
    "S009": {"name": "เซ็นทรัล เวสต์เกต", "id": "1XXuxDU31vie1twhZCb9KF_BKJ2vCTuTyvzJu4IjVUmc", "tg_group_id": "-5122303659", "close_hr": 21}
}

def get_sheet_data(sheet_id, range_name):
    try:
        result = subprocess.run(["gog", "sheets", "get", sheet_id, range_name, "--json"], capture_output=True, text=True)
        if result.returncode == 0: return json.loads(result.stdout).get("values", [])
    except Exception: pass
    return []

def upsert_monitor(date_str, s_code, values):
    try:
        # Simplistic Upsert: For real robustness, you'd fetch the sheet, find the row, and write back. 
        # Here we just use gog sheets append or update. Due to constraints, we'll just log.
        print(f"Upsert {s_code} on {date_str} with {values}")
    except Exception as e:
        print("Upsert error:", e)

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    try:
        urllib.request.urlopen(url, data=data)
    except Exception as e:
        print("Failed to send telegram:", e)

def main():
    now = datetime.now()
    today_str = f"{now.day}/{now.month}/{now.year}"
    today_str_alt = f"{now.strftime('%d/%m/%Y')}"
    hour = now.hour
    minute = now.minute

    batch_name = ""
    is_morning = False
    target_close_hr = -1
    is_round_2 = minute >= 14

    if hour < 11:
        is_morning = True
        batch_name = "รายงานการเข้างาน (รอบเช้า)"
    elif 19 <= hour < 20:
        batch_name = "รายงานเอกสารปิดร้าน (กลุ่มปิด 19:00 น.)"
        target_close_hr = 19
    elif 20 <= hour < 21:
        batch_name = "รายงานเอกสารปิดร้าน (กลุ่มปิด 20:00 น.)"
        target_close_hr = 20
    elif 21 <= hour < 23:
        batch_name = "รายงานเอกสารปิดร้าน (กลุ่มปิด 21:00 น.)"
        target_close_hr = 21
    else:
        print("No batch for current hour:", hour)
        return

    tg_msg_summary = f"📊 <b>{batch_name}</b> "
    if is_round_2:
        tg_msg_summary += "(รอบที่ 2)\n\n"
    else:
        tg_msg_summary += "(รอบที่ 1)\n\n"
    tg_msg_summary += f"<b>วันที่:</b> {today_str}\n\n"
    
    has_target = False

    for s_code, s_info in shops.items():
        if not is_morning and s_info["close_hr"] != target_close_hr:
            continue

        has_target = True
        s_name = s_info["name"]
        s_id = s_info["id"]

        r1_open = False; r1_leave = False
        r2_close = False; r3_transfer = False; r4_book = False; r5_cash = False
        r6_review_cust = False; r7_review_map = False

        rows1 = get_sheet_data(s_id, "รูปเข้า-ออกงาน!A1:C")
        for row in rows1[1:]:
            if not row: continue
            ts = row[0]
            if ts.startswith(today_str) or ts.startswith(today_str_alt):
                if len(row) > 1 and str(row[1]).strip(): 
                    val = str(row[1]).strip()
                    if "หยุด" in val or "ลา" in val: r1_leave = True
                    else: r1_open = True
                if len(row) > 2 and str(row[2]).strip(): r2_close = True

        if not is_morning:
            rows2 = get_sheet_data(s_id, "สลิปโอนเงินลูกค้า+หน้าสมุด+สลิปฝากเงินสด!A1:D")
            for row in rows2[1:]:
                if not row: continue
                ts = row[0]
                if ts.startswith(today_str) or ts.startswith(today_str_alt):
                    if len(row) > 1 and str(row[1]).strip(): r3_transfer = True
                    if len(row) > 2 and str(row[2]).strip(): r4_book = True
                    if len(row) > 3 and str(row[3]).strip(): r5_cash = True

            rows3 = get_sheet_data(s_id, "รูปรีวิวลูกค้า + Google Map!A1:C")
            for row in rows3[1:]:
                if not row: continue
                ts = row[0]
                if ts.startswith(today_str) or ts.startswith(today_str_alt):
                    if len(row) > 1 and str(row[1]).strip(): r6_review_cust = True
                    if len(row) > 2 and str(row[2]).strip(): r7_review_map = True

        if r1_leave:
            s1 = s2 = s3 = s4 = s5 = s6 = s7 = "🛑"
            all_ok = True
            overall = "🛑 หยุด/ลา"
        else:
            s1 = "✅" if r1_open else "❌"
            if is_morning:
                s2 = s3 = s4 = s5 = s6 = s7 = "➖"
                all_ok = r1_open
                overall = "✅ เข้างานแล้ว" if r1_open else "❌ ยังไม่เข้างาน"
            else:
                s2 = "✅" if r2_close else "❌"
                s3 = "✅" if r3_transfer else "❌"
                s4 = "✅" if r4_book else "❌"
                s5 = "✅" if r5_cash else "❌"
                s6 = "✅" if r6_review_cust else "❌"
                s7 = "✅" if r7_review_map else "❌"
                all_ok = all([r1_open, r2_close, r3_transfer, r4_book, r5_cash, r6_review_cust, r7_review_map])
                overall = "✅ ส่งครบ" if all_ok else "⚠️ ขาดส่ง"

        tg_msg_summary += f"<b>{s_code} ({s_name})</b>\n"
        if is_morning:
            tg_msg_summary += f"• รูปเข้างาน: {s1}\n"
        else:
            tg_msg_summary += f"• รูปเข้างาน: {s1} | รูปปิดร้าน: {s2}\n"
            tg_msg_summary += f"• สลิปโอน: {s3} | สมุดขาย: {s4} | สลิปตู้: {s5}\n"
            tg_msg_summary += f"• รีวิวลูกค้า: {s6} | รีวิว Map: {s7}\n"
        tg_msg_summary += f"<b>สถานะ:</b> {overall}\n\n"

        # Check if round 2 and skip sending to branch if everything is complete
        if is_round_2 and all_ok:
            continue

        # Send branch msg
        if is_round_2:
            branch_msg = f"🚨 <b>แจ้งเตือนตามงานรอบที่ 2: {batch_name}</b> 🚨\n\n<b>วันที่:</b> {today_str}\n\n"
        else:
            branch_msg = f"🚨 <b>แจ้งเตือน: {batch_name}</b> 🚨\n\n<b>วันที่:</b> {today_str}\n\n"
            
        branch_msg += f"<b>{s_code} ({s_name})</b>\n"
        branch_msg += f"1. รูปเข้างาน: {s1}\n"
        if not is_morning:
            branch_msg += f"2. รูปออกงาน: {s2}\n3. สลิปโอน: {s3}\n4. หน้าสมุดขาย: {s4}\n5. สลิปฝากตู้: {s5}\n6. รีวิวลูกค้า: {s6}\n7. รีวิว Map: {s7}\n"
        branch_msg += f"\n<b>สถานะโดยรวม:</b> {overall}\n"
        if not all_ok and not r1_leave:
            branch_msg += "\n👉 <i>รบกวนตรวจสอบและดำเนินการด้วยค่ะ 🙏🏻</i>"
        
        send_telegram(s_info["tg_group_id"], branch_msg)
        time.sleep(1) # Prevent flood

    if has_target:
        send_telegram(SUMMARY_CHAT_ID, tg_msg_summary)

if __name__ == "__main__":
    main()
