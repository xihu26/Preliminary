import csv
import requests
from google import genai
from google.genai import types
import smtplib
import statistics
from email.mime.text import MIMEText
from email.header import Header
# Configuration
GMAIL_ADDRESS = "lunababoody@gmail.com"       # Gmail account sending emails from
GMAIL_APP_PASSWORD = "wrdv dmpw iacf gohf"    # Gmail App Passwords
TEST_MODE = True                              # True = send everything to me
TEST_RECIPIENT = "lunacarly7@gmail.com"  
client = genai.Client(api_key="AQ.Ab8RN6LZvgIFJIxeI3RJrgCN1-B82f9Fhl27hmGEnqtnavjwTg")
def main():

    # Fetch the CSV data from the Google Sheets URL
    response = requests.get("https://docs.google.com/spreadsheets/d/18mr5ZyoyYDuuJ0TB4hncKw2CWUxBAjtIupadEoVNz_c/export?format=csv&gid=1745609522")
    reader = csv.DictReader(response.text.splitlines())

    brands = []

    for row in reader:
        brands.append({
            "brand": row["brandname"],
            "revenue": int(row["revenue"]),
            "order": int(row["Order"]),
            "boss": row["Boss Gmail"],
        })

    # Performance analysis of the brands
    revenues = [b["revenue"] for b in brands]
    orders = [b["order"] for b in brands]

    avg_revenue, std_revenue = statistics.mean(revenues), statistics.pstdev(revenues) or 1
    avg_orders, std_orders = statistics.mean(orders), statistics.pstdev(orders) or 1

    # Method to calculate z-score to compare the brands to each other
    def zscore(value, mean, std):
        return (value - mean) / std

    for b in brands:
        rev_z = zscore(b["revenue"], avg_revenue, std_revenue)
        ord_z = zscore(b["order"], avg_orders, std_orders)
        b["rev_z"], b["ord_z"] = rev_z, ord_z

        if rev_z >= 0.25 and ord_z >= 0.25:
            status = "doing well"
        elif rev_z <= -0.25 and ord_z <= -0.25:
            status = "needs improvement"
        elif rev_z <= -0.5 and ord_z > -0.25:
            status = "needs improvement (pricing/revenue per booking is weak)"
        elif ord_z <= -0.5 and rev_z > -0.25:
            status = "needs improvement (low demand/bookings)"
        else:
            status = "steady / on track"

        b["status"] = status

    #AI personalized email generation

    SYSTEM_PROMPT = """You are a performance analyst writing a short weekly email
    to a hotel partner. Tone: warm, professional, specific — not generic.
    Rules:
    - Max 120 words.
    - Open with a one-line headline of how last week went.
    - State revenue and orders vs. the group average in plain language.
    - Give exactly ONE concrete, actionable suggestion based on the status.
    - Do not invent numbers that weren't provided.
    - Sign off as "The Performance Team"."""

    def generate_summary(b):
        user_prompt = f"""Hotel: {b['brand']}
    Status: {b['status']}
    Revenue: £{b['revenue']:,.2f} (group average: £{avg_revenue:,.2f}, z-score: {b['rev_z']:.2f})
    Orders: {b['order']} (group average: {avg_orders:.1f}, z-score: {b['ord_z']:.2f})"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
            config=types.GenerateContentConfig(temperature=0.4),
        )
        return response.text.strip()

    def connect_smtp():
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30)
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        return server

    def send_email(server, to_addr, subject, body):
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_addr
        server.send_message(msg)

    #Automated sending and reports
    sent, failed = 0, 0
    status_counts = {}

    server = connect_smtp()

    for b in brands:
        recipient = TEST_RECIPIENT if TEST_MODE else b["boss"]
        subject = f"Weekly Performance Report – {b['brand']}"
        status_counts[b["status"]] = status_counts.get(b["status"], 0) + 1

        try:
            body = generate_summary(b)
            send_email(server, recipient, subject, body)
            sent += 1
            print(f"[OK] {b['brand']} -> {recipient} ({b['status']})")
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPException, OSError) as e:
            # Connection dropped mid-batch; reconnect once and retry this email
            try:
                server = connect_smtp()
                send_email(server, recipient, subject, body)
                sent += 1
                print(f"[OK] {b['brand']} -> {recipient} ({b['status']}) [after reconnect]")
            except Exception as e2:
                failed += 1
                print(f"[FAILED] {b['brand']} -> {recipient}: {e2}")
        except Exception as e:
            failed += 1
            print(f"[FAILED] {b['brand']} -> {recipient}: {e}")

    server.quit()

    print("\n--- RUN REPORT ---")
    print(f"Total hotels processed: {len(brands)}")
    print(f"Emails sent: {sent} | Failed: {failed}")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")


        